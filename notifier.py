import os
import urllib.request
import urllib.request
import base64
import datetime
import json
import time
from vedic import compute_kundli

try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from pywebpush import WebPushException, webpush
    HAS_PUSH = True
except Exception:
    HAS_PUSH = False


def ensure_vapid_keys(db_exec):
    rows = db_exec("SELECT key, value FROM config WHERE key IN ('vapid_pub', 'vapid_priv')", fetch="all") or []
    kv = {k: v for k, v in rows}
    if kv.get("vapid_pub") and kv.get("vapid_priv"):
        return kv["vapid_pub"], kv["vapid_priv"]
    if not HAS_PUSH:
        return "", ""
    priv = ec.generate_private_key(ec.SECP256R1())
    priv_pem = priv.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode("utf-8")
    pub_bytes = priv.public_key().public_bytes(
        serialization.Encoding.X962,
        serialization.PublicFormat.UncompressedPoint,
    )
    pub_b64 = base64.urlsafe_b64encode(pub_bytes).decode("ascii").rstrip("=")
    db_exec("INSERT INTO config (key, value) VALUES ('vapid_pub', ?) ON CONFLICT (key) DO NOTHING", (pub_b64,))
    db_exec("INSERT INTO config (key, value) VALUES ('vapid_priv', ?) ON CONFLICT (key) DO NOTHING", (priv_pem,))
    return pub_b64, priv_pem


def _ist_now():
    return datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)


def _tomorrow_tithi_info():
    tmr = _ist_now() + datetime.timedelta(days=1)
    k = compute_kundli(tmr.strftime("%Y-%m-%d"), "08:00", "Ahmedabad")
    return k["tithi"], k["vaar"], tmr


def _today_tithi_info():
    now = _ist_now()
    k = compute_kundli(now.strftime("%Y-%m-%d"), "08:00", "Ahmedabad")
    return k["tithi"], k["vaar"], now


def _kitchen_maa_name(faith):
    return {
        "muslim": "Zarina", "jain": "Mahima", "maharashtrian": "Sai (Aai)",
        "vaishnav": "Yashoda", "swaminarayan": "Bhakti", "sindhi": "Geeta",
        "sikh": "Simran", "christian": "Maria",
    }.get(faith, "Sweety")


def _greet_prefix(faith):
    return {
        "muslim": "Assalamu Alaikum", "jain": "Jai Jinendra",
        "maharashtrian": "Namaskar", "vaishnav": "Jai Shri Krishna",
        "swaminarayan": "Jay Swaminarayan", "sindhi": "Jai Jhulelal",
        "sikh": "Sat Sri Akal ji", "christian": "Peace & Blessings",
    }.get(faith, "Namaste")



UNIQUE_THEMES = [
    "Gratitude & Shukr", "Inner Peace & Sukun", "Self-Belief & Himmat", "Patience & Sabr",
    "Kindness to Others", "Letting Go of Yesterday", "Small Daily Progress", "Family Love & Care",
    "Strength in Hard Times", "Calm Mind & Focus", "Hope for Tomorrow", "Honesty & Integrity",
    "Smiling Through Challenges", "Trusting Timing", "Health & Self-Care", "Forgiveness & Light Heart",
    "Discipline & Consistency", "Learning from Mistakes", "Silence & Clarity", "Turning Pain into Power",
    "Appreciating Little Things", "Courage to Restart", "Positive Energy", "Humble Confidence",
    "Protecting Your Peace", "Helping Someone Today", "Deep Breath & Calm", "Staying Grounded",
    "Joy in Today", "Never Giving Up"
]

BACKUP_THOUGHTS = [
    "Har nayi subah ek naya mauka hoti hai, kal ki chinta chhod kar aaj muskurane ki koshish karo.",
    "Chhote-chhote kadam hi ek din badi manzil tak le jaate hain, bas chalte rehna zaroori hai.",
    "Jab mann shant hota hai, toh mushkil se mushkil raasta bhi aasaan dikhne lagta hai.",
    "Apni tulna kisi aur se mat karo, har insaan ka waqt aur safar apna hota hai.",
    "Aaj kisi ek insaan ke chehre par muskaan laane ki wajah bano, din khud-ba-khud khoobsurat ho jayega.",
    "Jo cheez aapke control mein nahi hai uska bojh dil se utaar do, sukoon wahin se shuru hota hai.",
    "Har mushkil waqt humein andar se aur mazboot banane aata hai, himmat kabhi mat haarna.",
    "Subah ki pehli soch jitni saaf aur positive hogi, poora din utna hi halka aur behtar guzrega.",
    "Khud par bharosa rakho, aapke andar woh saari taqat hai jo aapko aage le ja sakti hai.",
    "Sabr aur shukr do aise pankh hain jo har toofan ke upar se udaan bharna sikha dete hain.",
    "Galtiyon se daro mat, har galti aane wali safalta ki ek nayi seekh hoti hai.",
    "Parivaar aur apno ke saath bitaye do pyaar bhare pal duniya ki har daulat se badhkar hote hain.",
]


def get_daily_unique_thought(db_exec):
    now = _ist_now()
    date_str = now.strftime("%Y-%m-%d")
    row = db_exec("SELECT thought FROM daily_thoughts WHERE date_str = ?", (date_str,), fetch="one")
    if row and row[0]:
        return row[0]

    recent = db_exec("SELECT thought FROM daily_thoughts ORDER BY date_str DESC LIMIT 30", fetch="all") or []
    recent_set = {r[0] for r in recent}
    doy = now.timetuple().tm_yday
    theme = UNIQUE_THEMES[(doy + now.year) % len(UNIQUE_THEMES)]

    thought = ""
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        r_key = db_exec("SELECT value FROM config WHERE key = 'api_key'", fetch="one")
        if r_key:
            api_key = r_key[0].strip()

    if api_key:
        try:
            avoid = " | ".join(list(recent_set)[:6])
            prompt = (
                f"Write ONE unique, heartwarming, soulful morning positive-vibes life thought in natural Hinglish (Roman script) "
                f"for date {date_str} on the theme '{theme}'. "
                f"Rules: Maximum 2 short sentences (20-30 words total). Deeply human, uplifting, non-preachy, NO emojis, NO hashtags, NO quotes around it. "
                f"Must be completely different from these recent thoughts: {avoid}"
            )
            url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent?key=" + api_key
            payload = {"contents": [{"role": "user", "parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.95}}
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                d = json.loads(resp.read().decode("utf-8"))
            cand = d["candidates"][0]["content"]["parts"][0]["text"].strip().strip('"').strip("'")
            if cand and cand not in recent_set:
                thought = cand
        except Exception:
            pass

    if not thought:
        thought = BACKUP_THOUGHTS[(doy + now.year) % len(BACKUP_THOUGHTS)]

    db_exec("INSERT INTO daily_thoughts (date_str, thought) VALUES (?, ?) ON CONFLICT (date_str) DO NOTHING", (date_str, thought))
    return thought


def build_caring_message(slot, faith, user_name, is_fasting=False, thought_txt=''):
    nm = (user_name or "Dost").split()[0]
    greet = _greet_prefix(faith)
    maa = _kitchen_maa_name(faith)
    tithi_today, vaar_today, _ = _today_tithi_info()
    tithi_tmr, _, _ = _tomorrow_tithi_info()

    ekadashi_today = "Ekadashi" in tithi_today
    ekadashi_tmr = "Ekadashi" in tithi_tmr
    jain_parv_today = any(x in tithi_today for x in ("Ashtami", "Chaturdashi", "Purnima", "Panchami"))
    jain_parv_tmr = any(x in tithi_tmr for x in ("Ashtami", "Chaturdashi", "Purnima"))

    if slot == "morning":
        th = thought_txt or BACKUP_THOUGHTS[_ist_now().timetuple().tm_yday % len(BACKUP_THOUGHTS)]
        return (
            "☀️ Good Morning • Saifu",
            f"{greet} {nm}! {th} — Saifu ✨",
        )

    if slot == "lunch":
        if is_fasting or (faith in ("hindu", "vaishnav", "swaminarayan", "maharashtrian") and ekadashi_today):
            if faith == "muslim":
                return ("🕌 Hafez / Buzurg", f"{greet} {nm}, aaj aapke Roze ki shiddat aur sabr ko salaam! Allah aapko sehat, sukoon aur behad barkat de. Ameen!")
            if faith == "jain":
                return ("🙏 Vadil & Muni Guide", f"{greet} {nm}, aapki Tapasya aur Atthai / Upvas ki dil se anumodna! Mann shant rakhein, aapko khoob aatmik shakti mile.")
            return ("🤍 Vadil", f"{greet} {nm}, aaj aapka vrat/upvas hai — dhairya aur shanti banaye rakhna, ishwar aapki har manokamna poori kare!")
        return (f"👩‍🍳 {maa} (Kitchen)", f"{greet} {nm}! Dopahar ho gayi hai, kaam ke chakkar mein bhool mat jana — khana khaya? Please time se kha lena!")

    if slot == "special_eve":
        if faith in ("hindu", "vaishnav", "swaminarayan", "maharashtrian", "sindhi") and ekadashi_tmr:
            return ("🤍 Vadil (Kal Special Din)", f"{greet} {nm} beta, yaad dilana tha ki kal Ekadashi ({tithi_tmr}) hai! Aaj shaam se hi saaf-suthri bhakti aur vrat ki taiyari rakhna.")
        if faith == "jain" and (jain_parv_tmr or is_fasting):
            return ("🙏 Vadil (Jain Parv & Tapasya)", f"{greet} {nm}, kal {tithi_tmr} hai (aur Paryushan/Atthai ke dino mein aapka sanyam behad sarahniya hai). Khoob shakti aur shanti mile!")
        if faith == "muslim" and ("Guruvaar" in vaar_today or is_fasting):
            return ("🕌 Hafez / Buzurg", f"{greet} {nm}, sabr aur shukr sabse badi taqat hai — aaj shaam duaon mein yaad rakhein, Allah sab aasaan farmayega.")
        return None

    if slot == "dinner":
        if is_fasting and faith == "muslim":
            return (f"🍲 {maa} & Buzurg", f"{greet} {nm}, Roze ke sabr ke baad Iftar aur raat ka halka healthy khana waqt par le lena — apni sehat ka khayal zaroor rakhna!")
        if is_fasting:
            return (f"👩‍🍳 {maa} (Kitchen)", f"{greet} {nm}, aaj aapka vrat/tapasya hai — shaam ko halka satvik falahar/paani le lena, zyada thakan mat lena!")
        return (f"👩‍🍳 {maa} (Kitchen)", f"{greet} {nm}! Raat ho gayi hai, dinner kiya? Please time se garma-garam khana kha lena aur aaram karna.")

    return None


def _current_slot(now):
    hm = now.hour * 60 + now.minute
    if 9 * 60 <= hm <= 9 * 60 + 25:
        return "morning"
    if 13 * 60 + 25 <= hm <= 13 * 60 + 50:
        return "lunch"
    if 18 * 60 + 25 <= hm <= 18 * 60 + 50:
        return "special_eve"
    if 20 * 60 <= hm <= 20 * 60 + 25:
        return "dinner"
    return None


def send_push_one(sub_json, title, body, vapid_priv):
    if not HAS_PUSH or not vapid_priv:
        return False, "no_push"
    try:
        sub = json.loads(sub_json) if isinstance(sub_json, str) else sub_json
        webpush(
            subscription_info=sub,
            data=json.dumps({"title": title, "body": body, "url": "/?sr=v5"}),
            vapid_private_key=vapid_priv,
            vapid_claims={"sub": "mailto:rayan@sarahics.in"},
            ttl=3600,
        )
        return True, "ok"
    except WebPushException as ex:
        if ex.response is not None and ex.response.status_code in (404, 410):
            return False, "gone"
        return False, str(ex)
    except Exception as ex:
        return False, str(ex)


def run_notification_tick(db_exec, force_slot=None):
    if not HAS_PUSH:
        return 0
    now = _ist_now()
    slot = force_slot or _current_slot(now)
    if not slot:
        return 0
    slot_key = f"{now.strftime('%Y-%m-%d')}_{slot}"
    if not force_slot:
        already = db_exec("SELECT slot_key FROM sent_notifications WHERE slot_key = ?", (slot_key,), fetch="one")
        if already:
            return 0
        db_exec("INSERT INTO sent_notifications (slot_key, sent_at) VALUES (?, ?) ON CONFLICT (slot_key) DO NOTHING", (slot_key, int(time.time())))

    _, vapid_priv = ensure_vapid_keys(db_exec)
    if not vapid_priv:
        return 0
    subs = db_exec("SELECT id, sub_json, faith, user_name, is_fasting FROM push_subscriptions", fetch="all") or []
    sent = 0
    thought_today = get_daily_unique_thought(db_exec) if slot == "morning" else ""
    for sid, sjson, faith, uname, fast in subs:
        msg = build_caring_message(slot, faith or "hindu", uname or "Dost", bool(fast), thought_txt=thought_today)
        if not msg:
            continue
        ok, status = send_push_one(sjson, msg[0], msg[1], vapid_priv)
        if ok:
            sent += 1
        elif status == "gone":
            db_exec("DELETE FROM push_subscriptions WHERE id = ?", (sid,))
    return sent


def tg_send(token, chat_id, text):
    if not token or not chat_id:
        return False
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": str(chat_id), "text": text, "parse_mode": "HTML"}
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status == 200
    except Exception:
        return False


def build_daily_stats_text(db_exec, uptime_sec=0):
    u_cnt = (db_exec("SELECT COUNT(*) FROM users", fetch="one") or [0])[0]
    c_cnt = (db_exec("SELECT COUNT(*) FROM user_chats", fetch="one") or [0])[0]
    m_cnt = (db_exec("SELECT COUNT(*) FROM user_messages", fetch="one") or [0])[0]
    p_cnt = (db_exec("SELECT COUNT(*) FROM push_subscriptions", fetch="one") or [0])[0]
    now_ist = _ist_now().strftime("%d %b %Y, %I:%M %p IST")
    return (
        f"📊 <b>Shehja SR — Daily Watchdog Report</b>\n"
        f"🕒 {now_ist}\n"
        f"👥 Total Registered Users: <b>{u_cnt}</b>\n"
        f"💬 Total Saved Chats: <b>{c_cnt}</b> ({m_cnt} msgs)\n"
        f"🔔 Daily Push Subscribers: <b>{p_cnt}</b>\n"
        f"⏱️ Server Uptime: <b>{uptime_sec // 60} mins</b>\n"
        f"✅ Status: Healthy & Online"
    )


def tg_poll_and_daily(db_exec, token, chat_id, uptime_sec=0):
    if not token or not chat_id:
        return
    # 1. Daily Morning Auto-Stats at 08:30 - 09:00 IST
    now = _ist_now()
    hm = now.hour * 60 + now.minute
    if 8 * 60 + 30 <= hm <= 9 * 60:
        skey = f"{now.strftime('%Y-%m-%d')}_tg_morning_stats"
        if not db_exec("SELECT slot_key FROM sent_notifications WHERE slot_key = ?", (skey,), fetch="one"):
            db_exec("INSERT INTO sent_notifications (slot_key, sent_at) VALUES (?, ?) ON CONFLICT (slot_key) DO NOTHING", (skey, int(time.time())))
            tg_send(token, chat_id, build_daily_stats_text(db_exec, uptime_sec))

    # 2. Poll incoming Telegram commands from Rayan (/stats, /announce Title | Msg | URL, /clear)
    try:
        off_row = db_exec("SELECT value FROM config WHERE key = 'tg_offset'", fetch="one")
        offset = int(off_row[0]) if off_row and off_row[0].isdigit() else 0
        url = f"https://api.telegram.org/bot{token}/getUpdates?offset={offset}&timeout=0"
        with urllib.request.urlopen(url, timeout=8) as r:
            res = json.loads(r.read().decode("utf-8"))
        max_id = offset
        for upd in res.get("result") or []:
            uid = int(upd.get("update_id", 0))
            if uid >= max_id:
                max_id = uid + 1
            msg = upd.get("message") or {}
            if str((msg.get("chat") or {}).get("id", "")) != str(chat_id):
                continue
            txt = (msg.get("text") or "").strip()
            if txt == "/stats":
                tg_send(token, chat_id, build_daily_stats_text(db_exec, uptime_sec))
            elif txt.startswith("/announce "):
                body = txt[len("/announce "):].strip()
                parts = [x.strip() for x in body.split("|")]
                title = parts[0] if len(parts) >= 1 and parts[0] else "📢 Naya Update!"
                amsg = parts[1] if len(parts) >= 2 else title
                alink = parts[2] if len(parts) >= 3 else ""
                db_exec("UPDATE announcements SET active = 0")
                db_exec(
                    "INSERT INTO announcements (id, title, message, link_url, link_label, active, created_at) VALUES (?, ?, ?, ?, ?, 1, ?)",
                    (f"ann_{int(time.time())}", title, amsg, alink, "Open / Download", int(time.time())),
                )
                tg_send(token, chat_id, f"✅ Announcement Live kar diya gaya hai:\n<b>{title}</b>\n{amsg}")
            elif txt == "/clear":
                db_exec("UPDATE announcements SET active = 0")
                tg_send(token, chat_id, "🧹 Active announcement/ad hata diya gaya hai.")
        if max_id > offset:
            db_exec("INSERT INTO config (key, value) VALUES ('tg_offset', ?) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", (str(max_id),))
    except Exception:
        pass
