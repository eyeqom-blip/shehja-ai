import os, json, time, uuid, urllib.request

_TG_MENU_SET = False

CHEAT_SHEET = (
    "🤖 <b>Shehja SR — Dev Cheat Code Sheet</b>\n\n"
    "📊 /stats — Live Users, Chats, Msgs, DB &amp; Uptime\n"
    "🛠️ /heal — Jarvis Self-Healer Bug Report\n"
    "🧹 /clearad — App ka Popup Hide karein\n"
    "📖 /help — Yeh Cheat Code Sheet dubara dekhein\n\n"
    "📢 <b>Update / Download Popup Bhejne Ke Liye:</b>\n"
    "<code>/ad New Update! | Naya version live hai | https://shehja.sarahics.in</code>\n\n"
    "⏰ <b>Auto Reports:</b>\n"
    "• Subah 9:00 AM IST daily user report\n"
    "• Critical error par instant Self-Healer alert"
)

def register_telegram_menu():
    global _TG_MENU_SET
    if _TG_MENU_SET:
        return
    tok = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not tok:
        return
    try:
        cmds = [
            {"command": "stats", "description": "Live users, chats, DB & uptime"},
            {"command": "heal", "description": "Jarvis Self-Healer bug report"},
            {"command": "ad", "description": "Popup: /ad Title | Msg | Link"},
            {"command": "clearad", "description": "Hide active popup in app"},
            {"command": "help", "description": "Full Cheat Code Sheet"},
        ]
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{tok}/setMyCommands",
            data=json.dumps({"commands": cmds}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=6) as resp:
            if resp.status == 200:
                _TG_MENU_SET = True
    except Exception:
        pass

def collect_stats(db_exec, use_pg, start_time, cfg, get_heal_stats):
    u_cnt = (db_exec("SELECT COUNT(*) FROM users", fetch="one") or [0])[0]
    u_24 = (db_exec("SELECT COUNT(*) FROM users WHERE created_at >= ?", (int(time.time()) - 86400,), fetch="one") or [0])[0]
    c_cnt = (db_exec("SELECT COUNT(*) FROM user_chats", fetch="one") or [0])[0]
    m_cnt = (db_exec("SELECT COUNT(*) FROM user_messages", fetch="one") or [0])[0]
    p_cnt = (db_exec("SELECT COUNT(*) FROM push_subscriptions", fetch="one") or [0])[0]
    ad_r = db_exec("SELECT title FROM announcements WHERE active = 1 ORDER BY created_at DESC LIMIT 1", fetch="one")
    hs = get_heal_stats()
    return {
        "users": int(u_cnt), "new_users_24h": int(u_24), "chats": int(c_cnt), "messages": int(m_cnt),
        "push_subs": int(p_cnt), "active_ad": (ad_r[0] if ad_r else "None"),
        "db": ("neon" if use_pg else "sqlite"), "uptime_sec": int(time.time() - start_time),
        "model": cfg.get("model", ""), "healed_24h": hs["healed_24h"], "total_healed": hs["total_healed"], "last_bug": hs["last_bug"],
    }

def format_stats(st, prefix="📊 <b>Shehja SR Live Stats</b>"):
    hrs, mins = st["uptime_sec"] // 3600, (st["uptime_sec"] % 3600) // 60
    return (
        f"{prefix}\n🌐 <b>shehja.sarahics.in</b>\n"
        f"👥 Users: <b>{st['users']}</b> (+{st['new_users_24h']} last 24h)\n"
        f"💬 Chats: <b>{st['chats']}</b> | ✉️ Msgs: <b>{st['messages']}</b>\n"
        f"🔔 Push Alerts: <b>{st['push_subs']}</b> | 📢 Popup: <b>{st['active_ad']}</b>\n"
        f"🛠️ Healed Bugs (24h/All): <b>{st['healed_24h']}/{st['total_healed']}</b>\n"
        f"🗄️ DB: <b>{st['db'].upper()}</b> | 🤖 <code>{st['model']}</code> | ⏱️ {hrs}h {mins}m"
    )

def poll_tg(db_exec, send_tg, stats_fn, get_heal_stats):
    tok, cid = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip(), os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not tok or not cid:
        return
    register_telegram_menu()
    try:
        row = db_exec("SELECT value FROM config WHERE key = 'tg_offset'", fetch="one")
        offset = int(row[0]) if row and str(row[0]).isdigit() else 0
        url = f"https://api.telegram.org/bot{tok}/getUpdates?offset={offset}&limit=10&timeout=0"
        with urllib.request.urlopen(urllib.request.Request(url), timeout=6) as resp:
            d = json.loads(resp.read().decode("utf-8"))
        max_id = offset
        for upd in (d.get("result") or []):
            uid = int(upd.get("update_id", 0))
            if uid >= max_id: max_id = uid + 1
            msg = upd.get("message") or {}
            if str(msg.get("chat", {}).get("id", "")) != cid: continue
            txt = (msg.get("text") or "").strip()
            if txt.startswith("/announce ") or txt.startswith("/ad "):
                parts = [x.strip() for x in txt.split(" ", 1)[1].split("|")]
                title = parts[0] if len(parts) > 0 and parts[0] else "New Update!"
                body, link = (parts[1] if len(parts) > 1 else ""), (parts[2] if len(parts) > 2 else "")
                db_exec("UPDATE announcements SET active = 0")
                db_exec("INSERT INTO announcements (id, title, body, link_url, link_label, active, created_at) VALUES (?, ?, ?, ?, ?, 1, ?)", (uuid.uuid4().hex[:12], title, body, link, "Download / Open", int(time.time())))
                send_tg(f"✅ <b>App Popup Live!</b>\n<b>{title}</b>\n{body}\n{link}")
            elif txt in ("/clear", "/clearad"):
                db_exec("UPDATE announcements SET active = 0")
                send_tg("🧹 App startup popup cleared!")
            elif txt == "/stats":
                send_tg(format_stats(stats_fn()))
            elif txt == "/heal":
                hs = get_heal_stats()
                lines = "\n".join(f"• <code>{x['kind']}</code>: {x['detail']}" for x in hs["recent"]) or "• No bugs detected — 100% clean!"
                send_tg(f"🛠️ <b>Jarvis Self-Healer</b>\n24h: <b>{hs['healed_24h']}</b> | All: <b>{hs['total_healed']}</b>\n{lines}")
            elif txt in ("/start", "/help", "/menu"):
                send_tg(CHEAT_SHEET)
        if max_id > offset:
            db_exec("INSERT INTO config (key, value) VALUES ('tg_offset', ?) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", (str(max_id),))
    except Exception:
        pass
