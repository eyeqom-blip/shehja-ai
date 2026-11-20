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

FAITH_DEVA_GREET = {
    "hindu": "नमस्ते",
    "muslim": "अस्सलामु अलैकुम",
    "sikh": "सत श्री अकाल जी",
    "christian": "पीस एंड ब्लेसिंग्स",
    "jain": "जय जिनेंद्र",
    "maharashtrian": "नमस्कार",
    "vaishnav": "जय श्री कृष्ण",
    "swaminarayan": "जय स्वामिनारायण",
    "sindhi": "जय झूलेलाल",
    "universal": "नमस्ते",
}

FAITH_SIGNALS = [
    ("muslim", re.compile(r"(assalamu\s*alaikum|as[-\s]?salamu\s*alaykum|walaikum\s*assalam|wa\s*alaikum|walaykum|salam\s*alaikum|अस्सलाम|सलाम|वालेकुम|अल्लाह|इंशाअल्लाह|अल्हम्दुलिल्लाह|અસ્સલામ|વાલેકુમ|અલ્લાહ|\b(sallam|allah|inshallah|alhamdulillah|mashallah|subhanallah|namaz|roza|sehri|iftar|zakat|quran|hadith|sunnah|hafez|aalima|halal|qibla|dua|islamic|muslim)\b)", re.I)),
    ("jain", re.compile(r"(जय\s*जिनेंद्र|જય\s*જિનેન્દ્ર|मिच्छामि|पयुर्षण|नवकार|\b(jai\s*jinendra|jay\s*jinendra|michhami\s*dukkhadam|paryushan|navkar|mahavir|tirthankar|agam|pachkhan|ahimsa|jain)\b)", re.I)),
    ("sikh", re.compile(r"(सत\s*श्री\s*अकाल|वाहेगुरु|વાહેગુરુ|\b(sat\s*sri\s*akal|waheguru|gurbani|gurdwara|gurudwara|dasvandh|ardas|kirat\s*karo|vand\s*chhako|giani\s*ji|sikh)\b)", re.I)),
    ("christian", re.compile(r"(प्रभु\s*की\s*स्तुति|हालेलुयाह|\b(praise\s*the\s*lord|hallelujah|jesus|christ|bible|church|pastor|amen|tithe|christian)\b)", re.I)),
    ("swaminarayan", re.compile(r"(जय\s*स्वामिनारायण|જય\s*સ્વામિનારાयण|\b(jay\s*swaminarayan|jai\s*swaminarayan|swaminarayan|vachanamrut|shikshapatri|baps|ghanshyam|mahant\s*swami)\b)", re.I)),
    ("vaishnav", re.compile(r"(जय\s*श्री\s*कृष्ण|જય\s*શ્રી\s*કૃષ્ણ|\b(jai\s*shri\s*krishna|jai\s*shree\s*krishna|pushtimarg|thakorji|thakurji|shrinathji|vaishnav|vallabhacharya)\b)", re.I)),
    ("sindhi", re.compile(r"(जय\s*झूलेलाल|જય\s*ઝૂલેલાલ|\b(jai\s*jhulelal|jhulelal|bera\s*paar|cheti\s*chand|chaliha|sindhi|dal\s*pakwan|sai\s*bhaji)\b)", re.I)),
    ("maharashtrian", re.compile(r"(राम\s*कृष्ण\s*हरी|\b(ram\s*krishna\s*hari|jai\s*maharashtra|ganpati\s*bappa|vitthal|pandharpur|abhang|kay\s*mhanta|marathi)\b)", re.I)),
    ("hindu", re.compile(r"(प्रणाम|नमस्ते|ओम\s*शांति|भगवान|ईश्वर|પ્રણામ|નમસ્તે|ભગવાન|\b(pranam|pranaam|namaste|om\s*shanti|har\s*har\s*mahadev|jai\s*shree\s*ram|jai\s*shri\s*ram|radhe\s*radhe|bhagwan|ishwar|sanatan|kundli|panchang|shastri|hindu)\b)", re.I)),
]

_ISL = r"(assalamu\s*alaikum|as[-\s]?salamu\s*alaykum|wa?\s*alaikum(\s*assalam)?|walaykum(\s*assalam)?|salam\s*alaikum|अस्सलामु?\s*अलैकुम|अस्सलाम\s*वालेकुम|वालेकुम\s*अस्सलाम|અસ્સલામુ?\s*અલૈકુમ|વાલેકુમ\s*અસ્સલામ|अल्लाह|इंशाअल्लाह|\b(allah|inshallah|alhamdulillah|halal)\b)"
_HIN = r"(प्रणाम|नमस्ते|नमस्कार|ओम\s*शांति|जय\s*जिनेंद्र|सत\s*श्री\s*अकाल(\s*जी)?|भगवान|ईश्वर|परमात्मा|कल्याण\s*हो|\b(pranam|pranaam|namaste|namaskar|om\s*shanti|jai\s*jinendra|jay\s*jinendra|sat\s*sri\s*akal(\s*ji)?|jai\s*shri\s*krishna|jay\s*swaminarayan|jai\s*jhulelal|ram\s*krishna\s*hari|praise\s*the\s*lord|hallelujah|kalyan\s*ho|aashirwad|bhagwan|ishwar|parmatma)\b)"

FORBIDDEN_PATTERNS = {
    "muslim": re.compile(_HIN, re.I),
    "jain": re.compile(_ISL + r"|सत\s*श्री\s*अकाल|प्रणाम|प्रभु\s*की\s*स्तुति|\b(sat\s*sri\s*akal(\s*ji)?|praise\s*the\s*lord|hallelujah|pranam|pranaam)\b", re.I),
    "sikh": re.compile(_ISL + r"|जय\s*जिनेंद्र|प्रणाम|ओम\s*शांति|\b(jai\s*jinendra|praise\s*the\s*lord|hallelujah|pranam|pranaam|om\s*shanti)\b", re.I),
    "christian": re.compile(_ISL + r"|जय\s*जिनेंद्र|सत\s*श्री\s*अकाल|प्रणाम|नमस्ते|भगवान|\b(jai\s*jinendra|sat\s*sri\s*akal(\s*ji)?|pranam|pranaam|namaste|om\s*shanti|bhagwan)\b", re.I),
    "hindu": re.compile(_ISL + r"|जय\s*जिनेंद्र|सत\s*श्री\s*अकाल|\b(sat\s*sri\s*akal(\s*ji)?|jai\s*jinendra|praise\s*the\s*lord|hallelujah)\b", re.I),
    "vaishnav": re.compile(_ISL + r"|जय\s*जिनेंद्र|सत\s*श्री\s*अकाल|\b(sat\s*sri\s*akal(\s*ji)?|jai\s*jinendra|praise\s*the\s*lord|hallelujah)\b", re.I),
    "swaminarayan": re.compile(_ISL + r"|जय\s*जिनेंद्र|सत\s*श्री\s*अकाल|\b(sat\s*sri\s*akal(\s*ji)?|jai\s*jinendra|praise\s*the\s*lord|hallelujah)\b", re.I),
    "maharashtrian": re.compile(_ISL + r"|जय\s*जिनेंद्र|सत\s*श्री\s*अकाल|\b(sat\s*sri\s*akal(\s*ji)?|jai\s*jinendra|praise\s*the\s*lord|hallelujah)\b", re.I),
    "sindhi": re.compile(_ISL + r"|जय\s*जिनेंद्र|सत\s*श्री\s*अकाल|\b(sat\s*sri\s*akal(\s*ji)?|jai\s*jinendra|praise\s*the\s*lord|hallelujah)\b", re.I),
}

def detect_user_faith_signal(text):
    t = (text or "").strip()
    for fkey, pat in FAITH_SIGNALS:
        if pat.search(t):
            return fkey
    return "universal"

def _sanitize_text_for_faith(text, faith, persona=""):
    if not text:
        return text
    out = text
    if faith != "universal":
        greet = FAITH_GREETINGS.get(faith, "Hello")
        dgreet = FAITH_DEVA_GREET.get(faith, "नमस्ते")
        pat = FORBIDDEN_PATTERNS.get(faith)
        if pat:
            if faith == "muslim":
                out = re.sub(r"\b(pranam|pranaam|namaste|namaskar|jai\s*jinendra|jay\s*jinendra|sat\s*sri\s*akal(\s*ji)?|jai\s*shri\s*krishna|jay\s*swaminarayan|jai\s*jhulelal|ram\s*krishna\s*hari|praise\s*the\s*lord)\b", "Assalamu Alaikum", out, flags=re.I)
                out = re.sub(r"(प्रणाम|नमस्ते|नमस्कार|जय\s*जिनेंद्र|सत\s*श्री\s*अकाल(\s*जी)?|ओम\s*शांति)", "अस्सलामु अलैकुम", out)
                out = re.sub(r"\bom\s*shanti\b", "Sukoon aur Salamati", out, flags=re.I)
                out = re.sub(r"\b(kalyan\s*ho|aashirwad)\b", "Allah barkat de", out, flags=re.I)
                out = re.sub(r"\b(bhagwan|ishwar|parmatma)\b", "Allah", out, flags=re.I)
                out = re.sub(r"(भगवान|ईश्वर|परमात्मा)", "अल्लाह", out)
            else:
                def _rep(m):
                    w = m.group(0)
                    return dgreet if any("\u0900" <= ch <= "\u097f" for ch in w) else greet
                out = pat.sub(_rep, out)
    if persona == "shehja":
        out = re.sub(r"\b(mera\s+beta|meri\s+beti|beta|beti)\b", "dost", out, flags=re.I)
        out = re.sub(r"(मेरा\s+बेटा|मेरी\s+बेटी|बेटा|बेटी)", "दोस्त", out)
        out = re.sub(r"(મારા\s+બેટા|બેટા)", "દોસ્ત", out)
    return out

def sanitize_spoken_for_faith(spoken, faith, persona=""):
    return _sanitize_text_for_faith(spoken, faith, persona)

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
            c = _sanitize_text_for_faith(mc["content"], effective_faith, persona)
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
        notes.append(f"- ANTI-BAIT LOCK: User deliberately used '{detected}' terms/greeting (even in Hindi/voice). NEVER answer with 'Walaikum Assalam'/'Pranam' or mirror their faith! Reply strictly in {effective_faith.upper()} ('{greet}') ONLY.")
    elif is_universal and effective_faith != "universal":
        notes.append(f"- UNIVERSAL DYNAMIC MATCH: User spoke in {effective_faith.upper()} context — reply warmly in {effective_faith.upper()} etiquette ('{greet}').")
    if persona == "shastri" and effective_faith == "muslim":
        notes.append("- ADAB LOCK: As Hafez/Aalima, speak with dignity and hikmah. NEVER call user 'yaar'.")
    if persona == "shehja":
        notes.append("- DOST LOCK: Address user strictly as 'dost'/'yaar' or by name. NEVER use 'beta', 'बेटा', 'beti', or 'બેટા'.")

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
    if persona == "shehja" and re.search(r"(\bbeta\b|बेटा|બેટા)", reply, re.I):
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
                f"You are JARVIS AUDITOR. Fix this draft reply strictly.\n"
                f"1. Faith MUST be {faith.upper()} (Greeting: '{greet}'). Remove ALL other-religion words (like Walaikum Assalam, Pranam, Namaste, Allah, Bhagwan if wrong faith).\n"
                f"2. Character: {char_name}. {'Shehja MUST address user ONLY as dost/yaar, NEVER beta/बेटा.' if persona == 'shehja' else ''}\n"
                f"3. Keep English [SPOKEN]...[/SPOKEN] tag exact (never translate tag to Hindi).\n"
                f"Output ONLY the corrected final reply."
            )
            fixed = llm_rewrite_fn(sys_aud, f"User said: {user_text}\n\nDraft:\n{reply}")
            if fixed and len(fixed.strip()) > 10:
                reply = fixed.strip()
        except Exception:
            pass

    reply = _sanitize_text_for_faith(reply, faith, persona)
    if group_mode:
        tutor_name = fp["names"].get("ansh", "Ansh")
        if tutor_name != "Ansh":
            reply = re.sub(r"\bAnsh\b", tutor_name, reply)
    else:
        reply = re.sub(r"(?im)^.*(hamare baaki ke dost|hum sab yahin hain).*\n?", "", reply).strip()
    if persona == "shastri" and faith == "muslim":
        reply = re.sub(r"\byaar\b", "dost", reply, flags=re.I)
    return reply
