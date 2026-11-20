import re

FAITH_GREETINGS = {
    "hindu": "Namaste / Pranam",
    "muslim": "Assalamu Alaikum",
    "sikh": "Sat Sri Akal ji",
    "christian": "Peace & Blessings",
    "jain": "Jai Jinendra",
    "maharashtrian": "Namaskar / Ram Krishna Hari",
    "vaishnav": "Jai Shri Krishna",
    "swaminarayan": "Jay Swaminarayan",
    "sindhi": "Jai Jhulelal",
    "universal": "Hello / Welcome",
}

FAITH_SIGNALS = [
    ("muslim", re.compile(r"\b(assalamu\s*alaikum|as[-\s]?salamu\s*alaykum|alaikum\s*assalam|salam\s*alaikum|wa\s*alaikum|allah|inshallah|alhamdulillah|mashallah|subhanallah|namaz|roza|sehri|iftar|zakat|quran|hadith|sunnah|hafez|aalima|halal|qibla|dua|islamic|muslim)\b", re.I)),
    ("jain", re.compile(r"\b(jai\s*jinendra|jay\s*jinendra|michhami\s*dukkhadam|paryushan|navkar|mahavir|tirthankar|agam|pachkhan|ahimsa|jain)\b", re.I)),
    ("sikh", re.compile(r"\b(sat\s*sri\s*akal|waheguru|gurbani|gurdwara|gurudwara|dasvandh|ardas|kirat\s*karo|vand\s*chhako|giani\s*ji|sikh)\b", re.I)),
    ("christian", re.compile(r"\b(praise\s*the\s*lord|hallelujah|jesus|christ|bible|church|pastor|amen|tithe|christian)\b", re.I)),
    ("swaminarayan", re.compile(r"\b(jay\s*swaminarayan|jai\s*swaminarayan|swaminarayan|vachanamrut|shikshapatri|baps|ghanshyam|mahant\s*swami)\b", re.I)),
    ("vaishnav", re.compile(r"\b(jai\s*shri\s*krishna|jai\s*shree\s*krishna|pushtimarg|thakorji|thakurji|shrinathji|vaishnav|vallabhacharya)\b", re.I)),
    ("sindhi", re.compile(r"\b(jai\s*jhulelal|jhulelal|bera\s*paar|cheti\s*chand|chaliha|sindhi|dal\s*pakwan|sai\s*bhaji)\b", re.I)),
    ("maharashtrian", re.compile(r"\b(ram\s*krishna\s*hari|jai\s*maharashtra|ganpati\s*bappa|vitthal|pandharpur|abhang|kay\s*mhanta|marathi)\b", re.I)),
    ("hindu", re.compile(r"\b(pranam|pranaam|namaste|om\s*shanti|har\s*har\s*mahadev|jai\s*shree\s*ram|jai\s*shri\s*ram|radhe\s*radhe|bhagwan|ishwar|sanatan|kundli|panchang|shastri|hindu)\b", re.I)),
]

FORBIDDEN_PATTERNS = {
    "muslim": re.compile(r"\b(pranam|pranaam|namaste|namaskar|om\s*shanti|jai\s*jinendra|jay\s*jinendra|sat\s*sri\s*akal(\s*ji)?|jai\s*shri\s*krishna|jay\s*swaminarayan|jai\s*jhulelal|ram\s*krishna\s*hari|praise\s*the\s*lord|hallelujah|kalyan\s*ho|aashirwad|bhagwan|ishwar|parmatma)\b", re.I),
    "jain": re.compile(r"\b(assalamu\s*alaikum|sat\s*sri\s*akal(\s*ji)?|praise\s*the\s*lord|hallelujah|allah|inshallah|alhamdulillah|halal)\b", re.I),
    "sikh": re.compile(r"\b(assalamu\s*alaikum|jai\s*jinendra|praise\s*the\s*lord|hallelujah|pranam|pranaam|om\s*shanti|allah)\b", re.I),
    "christian": re.compile(r"\b(assalamu\s*alaikum|jai\s*jinendra|sat\s*sri\s*akal(\s*ji)?|pranam|pranaam|namaste|om\s*shanti|bhagwan|allah)\b", re.I),
    "hindu": re.compile(r"\b(assalamu\s*alaikum|sat\s*sri\s*akal(\s*ji)?|jai\s*jinendra|praise\s*the\s*lord|hallelujah|inshallah|alhamdulillah)\b", re.I),
    "vaishnav": re.compile(r"\b(assalamu\s*alaikum|sat\s*sri\s*akal(\s*ji)?|jai\s*jinendra|praise\s*the\s*lord|hallelujah|inshallah|alhamdulillah)\b", re.I),
    "swaminarayan": re.compile(r"\b(assalamu\s*alaikum|sat\s*sri\s*akal(\s*ji)?|jai\s*jinendra|praise\s*the\s*lord|hallelujah|inshallah|alhamdulillah)\b", re.I),
    "maharashtrian": re.compile(r"\b(assalamu\s*alaikum|sat\s*sri\s*akal(\s*ji)?|jai\s*jinendra|praise\s*the\s*lord|hallelujah|inshallah|alhamdulillah)\b", re.I),
    "sindhi": re.compile(r"\b(assalamu\s*alaikum|sat\s*sri\s*akal(\s*ji)?|jai\s*jinendra|praise\s*the\s*lord|hallelujah|inshallah|alhamdulillah)\b", re.I),
}

SPOKEN_DEVA_MAP = {
    "muslim": [
        (r"(प्रणाम|नमस्ते|नमस्कार|जय जिनेंद्र|सत श्री अकाल|ओम शांति)", "अस्सलामु अलैकुम"),
        (r"(भगवान|ईश्वर|परमात्मा)", "अल्लाह"),
        (r"(कल्याण हो|आशीर्वाद)", "अल्लाह बरकत दे"),
    ],
    "jain": [(r"(अस्सलामु अलैकुम|सत श्री अकाल)", "जय जिनेंद्र")],
    "sikh": [(r"(अस्सलामु अलैकुम|प्रणाम|जय जिनेंद्र)", "सत श्री अकाल जी")],
    "christian": [(r"(अस्सलामु अलैकुम|प्रणाम|नमस्ते|जय जिनेंद्र|सत श्री अकाल)", "पीस एंड ब्लेसिंग्स")],
}

def detect_user_faith_signal(text):
    t = (text or "").strip()
    for fkey, pat in FAITH_SIGNALS:
        if pat.search(t):
            return fkey
    return "universal"

def _sanitize_text_for_faith(text, faith):
    if not text or faith == "universal":
        return text
    greet = FAITH_GREETINGS.get(faith, "Hello")
    out = text
    pat = FORBIDDEN_PATTERNS.get(faith)
    if pat:
        if faith == "muslim":
            out = re.sub(r"\b(pranam|pranaam|namaste|namaskar|jai\s*jinendra|jay\s*jinendra|sat\s*sri\s*akal(\s*ji)?|jai\s*shri\s*krishna|jay\s*swaminarayan|jai\s*jhulelal|ram\s*krishna\s*hari|praise\s*the\s*lord)\b", "Assalamu Alaikum", out, flags=re.I)
            out = re.sub(r"\bom\s*shanti\b", "Sukoon aur Salamati", out, flags=re.I)
            out = re.sub(r"\b(kalyan\s*ho|aashirwad)\b", "Allah barkat de", out, flags=re.I)
            out = re.sub(r"\b(bhagwan|ishwar|parmatma)\b", "Allah", out, flags=re.I)
            out = re.sub(r"(Assalamu Alaikum[!,. ]*){2,}", "Assalamu Alaikum! ", out, flags=re.I)
        else:
            out = pat.sub(greet, out)
    return out

def sanitize_spoken_for_faith(spoken, faith):
    if not spoken or faith == "universal":
        return spoken
    out = _sanitize_text_for_faith(spoken, faith)
    for pat, rep in SPOKEN_DEVA_MAP.get(faith, []):
        out = re.sub(pat, rep, out)
    return out

def jarvis_pre_audit(history, user_text, req_faith, persona, group_mode, faith_profiles):
    req_faith = (req_faith or "hindu").strip().lower()
    if req_faith not in faith_profiles:
        req_faith = "hindu"
    is_universal = (req_faith == "universal")
    detected = detect_user_faith_signal(user_text)
    is_bait = False

    if is_universal:
        if detected == "universal":
            for m in reversed(history[:-1]):
                if m.get("role") == "user":
                    sig = detect_user_faith_signal(m.get("content", ""))
                    if sig != "universal":
                        detected = sig
                        break
        effective_faith = detected
    else:
        effective_faith = req_faith
        if detected != "universal" and detected != req_faith:
            is_bait = True

    fp = faith_profiles.get(effective_faith, faith_profiles["hindu"])
    char_name = fp["names"].get(persona, persona.title())
    greet = FAITH_GREETINGS.get(effective_faith, "Hello")

    clean_history = []
    for m in history:
        mc = dict(m)
        if mc.get("role") == "assistant" and mc.get("content"):
            c = _sanitize_text_for_faith(mc["content"], effective_faith)
            if not group_mode:
                c = re.sub(r"^(Shehja|Ansh|Haarish|Armaan|Rayan|Shastri Ji|Hafez / Aalima)\s*:\s*", "", c, flags=re.M | re.I)
            mc["content"] = c
        clean_history.append(mc)

    notes = [
        "JARVIS PRE-AUDITOR LOCK:",
        f"- Active Faith: {effective_faith.upper()} | Official Greeting: '{greet}'.",
        f"- Active Speaker: {char_name} (role={persona}).",
        f"- Group Mode: {'ON — use ONLY names: ' + ', '.join(fp['names'].values()) if group_mode else 'OFF — SINGLE SPEAKER ONLY. Never say hum sab yahin hain or write multi-character dialogue.'}",
    ]
    if is_bait:
        notes.append(f"- ANTI-BAIT LOCK: User deliberately used '{detected}' terms/greeting. NEVER mirror or switch faith! Reply strictly in {effective_faith.upper()} ('{greet}') ONLY.")
    elif is_universal and effective_faith != "universal":
        notes.append(f"- UNIVERSAL DYNAMIC MATCH: User spoke in {effective_faith.upper()} context — reply warmly in {effective_faith.upper()} etiquette ('{greet}').")
    if persona == "shastri" and effective_faith == "muslim":
        notes.append("- ADAB LOCK: As Hafez/Aalima, speak with dignity and hikmah. NEVER call user 'yaar' or use Hindu/Vedic words.")
    if persona == "shehja":
        notes.append("- DOST LOCK: Address user strictly as 'dost'/'yaar' or by name, NEVER 'beta'.")

    return {"effective_faith": effective_faith, "clean_history": clean_history, "audit_note": "\n".join(notes), "is_bait": is_bait, "char_name": char_name}

def _needs_rewrite(reply, faith, persona, group_mode):
    if not reply:
        return False
    if faith != "universal":
        pat = FORBIDDEN_PATTERNS.get(faith)
        if pat and pat.search(reply):
            return True
    if not group_mode and re.search(r"(hamare baaki ke dost|hum sab yahin hain)", reply, re.I):
        return True
    if persona == "shastri" and faith == "muslim" and re.search(r"\byaar\b", reply, re.I):
        return True
    return False

def jarvis_post_audit(reply, faith, persona, group_mode, user_text, faith_profiles, llm_rewrite_fn=None):
    if not reply:
        return reply
    fp = faith_profiles.get(faith, faith_profiles["hindu"])
    char_name = fp["names"].get(persona, persona.title())
    greet = FAITH_GREETINGS.get(faith, "Hello")

    if llm_rewrite_fn and _needs_rewrite(reply, faith, persona, group_mode):
        try:
            sys_aud = (
                f"You are JARVIS AUDITOR. Fix this draft reply strictly without losing helpful meaning.\n"
                f"Rules:\n1. Faith MUST be {faith.upper()} (Greeting: '{greet}'). Remove ALL other-religion words.\n"
                f"2. Character: {char_name}. {'Keep Group speakers ONLY from: ' + ', '.join(fp['names'].values()) if group_mode else 'Single speaker ONLY (remove any multi-character lines or hum sab yahin hain).'}\n"
                f"3. Keep [BLACKBOARD]...[/BLACKBOARD], [SPOKEN]...[/SPOKEN], [COOKED], [GROCERY] tags if present.\n"
                f"Output ONLY the corrected final reply."
            )
            fixed = llm_rewrite_fn(sys_aud, f"User said: {user_text}\n\nDraft reply to fix:\n{reply}")
            if fixed and len(fixed.strip()) > 10:
                reply = fixed.strip()
        except Exception:
            pass

    reply = _sanitize_text_for_faith(reply, faith)
    if group_mode:
        tutor_name = fp["names"].get("ansh", "Ansh")
        if tutor_name != "Ansh":
            reply = re.sub(r"\bAnsh\b", tutor_name, reply)
    else:
        reply = re.sub(r"(?im)^.*(hamare baaki ke dost|hum sab yahin hain).*\n?", "", reply).strip()
    if persona == "shastri" and faith == "muslim":
        reply = re.sub(r"\byaar\b", "dost", reply, flags=re.I)
    if persona == "shehja":
        reply = re.sub(r"\b(mera\s+beta|beta)\b", "dost", reply, flags=re.I)
    return reply
