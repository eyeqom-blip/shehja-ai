import asyncio
import base64
import hashlib
import hmac
import http.cookies
import json
import os
import random
import re
import smtplib
import sqlite3
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from email.message import EmailMessage
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from exporters import ICON_SVG, LAYOUTS, build_pptx_bytes, build_xlsx_bytes, make_sr_png
from personas import build_system_prompt, detect_tts_config
from vedic import TAROT_DECK, compute_gun_milan, compute_kundli, compute_numerology, get_today_panchang, render_kundli_svg, render_loshu_svg

try:
    import edge_tts
except Exception:
    edge_tts = None

START_TIME = int(time.time())
PORT = int(os.environ.get("PORT", 8080))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "shehja.db")
INDEX_PATH = os.path.join(BASE_DIR, "static", "index.html")
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
USE_PG = bool(DATABASE_URL)
if USE_PG:
    import pg8000.dbapi

_PPT_CACHE = {}
_XLSX_CACHE = {}
_IMG_CACHE = {}
FALLBACK_MODELS = ["gemini-3.5-flash-lite", "gemini-3.6-flash", "gemini-3.1-flash-lite", "gemini-3.5-flash-lite"]


def db_connect():
    if USE_PG:
        u = urllib.parse.urlparse(DATABASE_URL)
        return pg8000.dbapi.connect(
            user=urllib.parse.unquote(u.username or ""),
            password=urllib.parse.unquote(u.password or ""),
            host=u.hostname,
            port=u.port or 5432,
            database=(u.path or "/neondb").lstrip("/"),
            ssl_context=ssl.create_default_context(),
            timeout=15,
        )
    return sqlite3.connect(DB_PATH)


def db_exec(sql, params=(), fetch=None):
    q = sql.replace("?", "%s") if USE_PG else sql
    last_ex = None
    for attempt in range(2):
        conn = None
        try:
            conn = db_connect()
            cur = conn.cursor()
            cur.execute(q, params)
            res = cur.fetchone() if fetch == "one" else (cur.fetchall() if fetch == "all" else None)
            conn.commit()
            return res
        except Exception as e:
            last_ex = e
            if attempt == 0:
                time.sleep(0.8)
                continue
            raise last_ex
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

def hash_secret(plain):
    salt = os.urandom(16).hex()
    dk = hashlib.pbkdf2_hmac("sha256", plain.encode("utf-8"), salt.encode("utf-8"), 100000).hex()
    return f"{salt}${dk}"


def verify_secret(plain, stored):
    try:
        salt, dk = stored.split("$", 1)
        chk = hashlib.pbkdf2_hmac("sha256", plain.encode("utf-8"), salt.encode("utf-8"), 100000).hex()
        return hmac.compare_digest(chk, dk)
    except Exception:
        return False


def init_db():
    stmts = [
        "CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT NOT NULL)",
        "CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, pass_hash TEXT NOT NULL, sec_q TEXT NOT NULL, sec_a_hash TEXT NOT NULL, created_at BIGINT NOT NULL)",
        "CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, user_id TEXT NOT NULL, created_at BIGINT NOT NULL)",
        "CREATE TABLE IF NOT EXISTS otps (email TEXT PRIMARY KEY, otp_hash TEXT NOT NULL, expires_at BIGINT NOT NULL)",
        "CREATE TABLE IF NOT EXISTS user_chats (id TEXT PRIMARY KEY, user_id TEXT NOT NULL, title TEXT NOT NULL, updated_at BIGINT NOT NULL)",
        "CREATE TABLE IF NOT EXISTS user_messages (id TEXT PRIMARY KEY, chat_id TEXT NOT NULL, seq INTEGER NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL, created_at BIGINT NOT NULL)",
        "CREATE TABLE IF NOT EXISTS kitchen_profiles (user_id TEXT PRIMARY KEY, profile_json TEXT NOT NULL, updated_at BIGINT NOT NULL)",
    ]
    for s in stmts:
        db_exec(s)
    env_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""
    def_prov = os.environ.get("AI_PROVIDER") or ("gemini" if os.environ.get("GEMINI_API_KEY") else ("openai" if os.environ.get("OPENAI_API_KEY") else "demo"))
    defaults = {
        "provider": def_prov, "model": os.environ.get("AI_MODEL", "gemini-3.5-flash-lite"),
        "api_key": env_key, "admin_pin": os.environ.get("SHEHJA_PIN", "1234"),
        "custom_prompt": os.environ.get("CUSTOM_PROMPT", ""),
    }
    for k, v in defaults.items():
        db_exec("INSERT INTO config (key, value) VALUES (?, ?) ON CONFLICT (key) DO NOTHING", (k, v))


def get_indian_season():
    m = time.gmtime(time.time() + 19800).tm_mon
    if m in (11, 12, 1, 2):
        return "Sardi (Winter) — Fresh & Best: Methi, Palak, Sarson, Bathua, Matar, Gajar, Gobhi, Mooli, Chukandar, Hare Pyaz, Amla, Tamatar, Aloo"
    if m in (3, 4, 5, 6):
        return "Garmi (Summer) — Fresh & Best: Bhindi, Lauki, Tori (Turai), Karela, Tinda, Parwal, Kheera, Kachcha Aam, Pudina, Neembu"
    return "Barish (Monsoon) — Best: Bhindi, Tori, Karela, Arbi, Bhutta (Corn), Kundru, Lauki (Avoid/Careful with leafy greens like Palak & Patta Gobhi)"


def default_kitchen():
    return {
        "diet": "Pure Veg",
        "members": 4,
        "occasion": "Regular Family",
        "appliances": ["Gas Chulha", "Pressure Cooker", "Mixer / Grinder"],
        "likes": "",
        "health": "",
        "history": [],
        "grocery": [],
    }


def get_kitchen_profile(user_id):
    if not user_id:
        return default_kitchen()
    row = db_exec("SELECT profile_json FROM kitchen_profiles WHERE user_id = ?", (user_id,), fetch="one")
    if not row:
        return default_kitchen()
    try:
        d = json.loads(row[0])
        base = default_kitchen()
        base.update(d)
        return base
    except Exception:
        return default_kitchen()


def save_kitchen_profile(user_id, prof):
    if not user_id:
        return
    db_exec(
        "INSERT INTO kitchen_profiles (user_id, profile_json, updated_at) VALUES (?, ?, ?) "
        "ON CONFLICT (user_id) DO UPDATE SET profile_json = EXCLUDED.profile_json, updated_at = EXCLUDED.updated_at",
        (user_id, json.dumps(prof), int(time.time())),
    )


def get_config():
    rows = db_exec("SELECT key, value FROM config", fetch="all") or []
    cfg = {k: v for k, v in rows}
    return {
        "provider": cfg.get("provider", "demo"), "model": cfg.get("model", "gemini-3.5-flash-lite"),
        "api_key": cfg.get("api_key", ""), "admin_pin": cfg.get("admin_pin") or os.environ.get("SHEHJA_PIN", "1234"),
        "custom_prompt": cfg.get("custom_prompt", ""),
    }


def save_config(provider, model, api_key, new_pin="", custom_prompt=None):
    for k, v in [("provider", provider), ("model", model)]:
        db_exec("INSERT INTO config (key, value) VALUES (?, ?) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", (k, v))
    if api_key:
        db_exec("INSERT INTO config (key, value) VALUES ('api_key', ?) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", (api_key,))
    if new_pin:
        db_exec("INSERT INTO config (key, value) VALUES ('admin_pin', ?) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", (new_pin,))
    if custom_prompt is not None:
        db_exec("INSERT INTO config (key, value) VALUES ('custom_prompt', ?) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", (custom_prompt,))


def smtp_configured():
    return bool(os.environ.get("SMTP_EMAIL") and os.environ.get("SMTP_PASS"))


def send_otp_email(to_email, otp_code):
    sender, pw = os.environ.get("SMTP_EMAIL", "").strip(), os.environ.get("SMTP_PASS", "").strip()
    if not sender or not pw:
        raise RuntimeError("Email OTP setup nahi hai. Security Question option use karein!")
    msg = EmailMessage()
    msg["Subject"] = f"Shehja SR — Password Reset OTP: {otp_code}"
    msg["From"] = f"Shehja SR <{sender}>"
    msg["To"] = to_email
    msg.set_content(f"Namaste!\n\nAapka Password Reset OTP hai: {otp_code}\nYeh 10 minute tak valid hai.")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as smtp:
        smtp.login(sender, pw)
        smtp.send_message(msg)


async def _tts_async(text, voice, rate, pitch):
    comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    buf = bytearray()
    async for chunk in comm.stream():
        if chunk["type"] == "audio":
            buf.extend(chunk["data"])
    return bytes(buf)


def _pad_wav_silence(wav_bytes, ms=280):
    try:
        if not wav_bytes.startswith(b"RIFF"):
            return wav_bytes
        idx = wav_bytes.find(b"data")
        if idx == -1 or idx + 8 > len(wav_bytes):
            return wav_bytes
        sr = int.from_bytes(wav_bytes[24:28], "little") or 24000
        ch = int.from_bytes(wav_bytes[22:24], "little") or 1
        bps = int.from_bytes(wav_bytes[34:36], "little") or 16
        pad_len = int(sr * ch * (bps // 8) * (ms / 1000.0))
        pad = b"\x00" * (pad_len - (pad_len % 2))
        old_data_sz = int.from_bytes(wav_bytes[idx + 4:idx + 8], "little")
        new_data_sz = old_data_sz + len(pad)
        out = bytearray(wav_bytes)
        out[idx + 4:idx + 8] = new_data_sz.to_bytes(4, "little")
        out.extend(pad)
        out[4:8] = (len(out) - 8).to_bytes(4, "little")
        return bytes(out)
    except Exception:
        return wav_bytes


def roman_hinglish_to_spoken(cfg, text):
    # Clean markdown / newlines into smooth punctuation first
    t = re.sub(r"[\.]{2,}|…", ", ", text)
    t = re.sub(r"\s*\n+\s*", "। ", t).strip()
    if any("\u0900" <= c <= "\u097f" or "\u0a80" <= c <= "\u0aff" for c in t):
        return t
    hindi_markers = ("hai", "hain", "hoon", "ho", "kya", "nahi", "nhi", "aap", "tum", "main", "mein", "kar", "raha", "rahi", "bhai", "yaar", "beta", "chinta", "batao", "samajh", "kaise", "kaisa", "kaisi", "accha", "acha", "theek", "bahut", "dil", "mann", "haan", "ji", "sun", "suno", "mat", "karo")
    words = re.findall(r"[a-zA-Z]+", t.lower())
    if not any(w in hindi_markers for w in words):
        return t
    if cfg.get("provider") == "gemini" and cfg.get("api_key"):
        try:
            prompt = (
                "Rewrite this Hinglish reply into smooth, natural, expressive spoken Hindi in Devanagari script "
                "so it sounds like a caring human speaking aloud. "
                "Rules: Use commas ',' for soft breaths and Hindi purna viram '।' at every sentence end (or '?'/'!'). "
                "NEVER use '...' or ellipses or symbols. Keep natural warmth intact. Return ONLY the spoken Devanagari text:\n\n" + t[:1800]
            )
            url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent?key=" + urllib.parse.quote(cfg["api_key"], safe="")
            payload = {"contents": [{"role": "user", "parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.25}}
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=8) as resp:
                d = json.loads(resp.read().decode("utf-8"))
            out = d["candidates"][0]["content"]["parts"][0]["text"].strip()
            out = re.sub(r"[\.]{2,}|…", ", ", out)
            if out and out[-1] not in ("।", ".", "?", "!"):
                out += "।"
            if out:
                return out
        except Exception:
            pass
    return t


def synth_sarvam_audio(text, persona_key, tone="auto", spoken_override=None):
    key = os.environ.get("SARVAM_API_KEY", "").strip()
    if not key:
        return None, None
    if spoken_override:
        clean = spoken_override.strip()
    else:
        clean = re.sub(r"\[BLACKBOARD\][\s\S]*?\[/BLACKBOARD\]", " blackboard par likh diya hai। ", text)
        clean = re.sub(r"```[\s\S]*?```", " code screen par hai। ", clean)
        clean = re.sub(r"[*_#`>]", "", clean)
        clean = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", clean).strip()
        if not clean:
            return None, None
        clean = roman_hinglish_to_spoken(get_config(), clean)
    clean = re.sub(r"[\.]{2,}|…", ", ", clean or "").strip()
    if not clean:
        return None, None
    if clean[-1] not in ("।", ".", "?", "!"):
        clean += "।"

    lang = "gu-IN" if any("\u0a80" <= c <= "\u0aff" for c in clean) else "hi-IN"
    if not any("\u0900" <= c <= "\u097f" or "\u0a80" <= c <= "\u0aff" for c in clean):
        lang = "en-IN"

    low = text.lower()
    is_emotional = any(w in low for w in ("sorry", "sad", "udaas", "dukhi", "akela", "chinta", "tension", "beta", "himmat", "pyaar", "dil", "fikar", "ro", "mushkil"))
    is_happy = any(w in low for w in ("mubarak", "congrats", "awesome", "great", "wah", "haha", "mazaa", "khush", "shabaash"))

    if tone in ("priya", "simran", "ritu", "kavya") and persona_key == "shehja":
        sp3 = tone
    elif persona_key == "shehja":
        sp3 = "simran" if is_emotional else ("kavya" if is_happy else "priya")
    elif persona_key in ("vadil", "shastri"):
        sp3 = "ashutosh"
    elif persona_key == "rayan":
        sp3 = "kabir"
    else:
        sp3 = "shubh"

    if persona_key == "sweety" and tone == "auto":
        sp3 = "priya"
    if tone in ("soft", "calm", "simran") or is_emotional or persona_key in ("vadil", "shastri"):
        pace, temp = 0.90, 0.62
    elif tone in ("energy", "kavya") or is_happy:
        pace, temp = 1.01, 0.72
    elif tone == "teacher" or persona_key == "ansh":
        pace, temp = 0.95, 0.58
    else:
        pace, temp = 0.96, 0.65

    sp2 = "anushka" if persona_key == "shehja" else "karun"
    attempts = [
        ({"text": clean[:2400], "target_language_code": lang, "model": "bulbul:v3", "speaker": sp3, "pace": pace, "temperature": temp, "speech_sample_rate": 22050, "output_audio_codec": "mp3", "enable_preprocessing": True}, "audio/mpeg"),
        ({"text": clean[:2400], "target_language_code": lang, "model": "bulbul:v3", "speaker": sp3, "pace": pace, "temperature": temp, "speech_sample_rate": 22050, "enable_preprocessing": True}, "audio/wav"),
        ({"inputs": [clean[:500]], "target_language_code": lang, "model": "bulbul:v2", "speaker": sp2, "pace": pace, "loudness": 1.2, "speech_sample_rate": 22050, "enable_preprocessing": True}, "audio/wav"),
    ]
    last_err = None
    for pl, mime in attempts:
        req = urllib.request.Request(
            "https://api.sarvam.ai/text-to-speech",
            data=json.dumps(pl).encode("utf-8"),
            headers={"api-subscription-key": key, "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                d = json.loads(resp.read().decode("utf-8"))
            raw_b = base64.b64decode(d["audios"][0])
            if mime == "audio/wav":
                raw_b = _pad_wav_silence(raw_b, 260)
            return raw_b, mime
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code == 400:
                continue
            raise
    if last_err:
        raise last_err
    return None, None

def synth_neural_mp3(text, persona_key, tone="auto"):
    if edge_tts is None:
        return None
    clean = re.sub(r"\[BLACKBOARD\][\s\S]*?\[/BLACKBOARD\]", " blackboard par likh diya hai. ", text)
    clean = re.sub(r"```[\s\S]*?```", " code screen par hai. ", clean)
    clean = re.sub(r"[*_#`>]", "", clean)
    clean = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", clean).strip()
    if not clean:
        return None
    voice, rate, pitch = detect_tts_config(persona_key, clean, tone)
    return asyncio.run(_tts_async(clean[:2500], voice, rate, pitch))


def call_demo(user_text, persona="shehja"):
    time.sleep(0.25)
    q = user_text.lower()
    if any(w in q for w in ("contact", "mail", "email", "owner", "kisne banaya")):
        return "Kisi bhi zaroori help ya query ke liye aap **`rayan@sarahics.in`** par mail kar sakte hain."
    if persona == "vadil":
        return f"Aao beta, aaram se baitho. Maine suna tumne jo kaha (*\"{user_text}\"*). Zindagi mein har mushkil waqt guzar jata hai, himmat mat haaro — main hoon na tumhare saath."
    if persona == "ansh":
        return f"Chalo is topic ko bilkul basic se samajhte hain!\n\n[BLACKBOARD]\nTopic: {user_text[:40]}\n1. Core Definition & Law\n2. Formula & Steps\n3. Solved Board Example\n[/BLACKBOARD]\n\n*(Abhi demo mode chal raha hai — live API key lagate hi full syllabus answers aayenge.)*"
    return f"Haan ji, main sun rahi hoon! 🌸 Aapne kaha: *\"{user_text}\"*. Abhi demo mode chal raha hai, lekin dost ki tarah main hamesha baat karne ke liye ready hoon!"


def call_gemini(history, model, api_key, system_text, use_search=False, temp=0.65):
    if not api_key:
        raise ValueError("API key configured nahi hai.")
    primary = model or "gemini-3.5-flash-lite"
    models_to_try = [primary] + [m for m in FALLBACK_MODELS if m != primary]
    contents = []
    for m in history:
        parts = []
        txt = (m.get("content") or "").strip()
        if txt:
            parts.append({"text": txt})
        if m.get("image"):
            parts.append({"inlineData": {"mimeType": m.get("mime") or "image/jpeg", "data": m["image"]}})
        if not parts:
            parts.append({"text": "Is photo ki har detail dhyaan se padh kar samjhao."})
        contents.append({"role": "model" if m.get("role") == "assistant" else "user", "parts": parts})

    def do_req(mdl, with_tools):
        url = "https://generativelanguage.googleapis.com/v1beta/models/" + urllib.parse.quote(mdl, safe="") + ":generateContent?key=" + urllib.parse.quote(api_key, safe="")
        payload = {"systemInstruction": {"parts": [{"text": system_text}]}, "contents": contents, "generationConfig": {"temperature": temp}}
        if with_tools:
            payload["tools"] = [{"google_search": {}}]
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=25) as resp:
            return json.loads(resp.read().decode("utf-8"))

    data, last_err = None, "API error"
    for mdl in models_to_try:
        try:
            data = do_req(mdl, use_search)
            break
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            try:
                last_err = json.loads(err_body).get("error", {}).get("message", err_body)
            except Exception:
                last_err = err_body or str(e)
            if use_search and e.code in (400, 403, 429):
                try:
                    data = do_req(mdl, False)
                    break
                except Exception:
                    pass
            if e.code in (400, 403, 404, 429, 500, 503):
                continue
            raise RuntimeError(last_err)
        except (TimeoutError, urllib.error.URLError, OSError) as e:
            last_err = str(e)
            continue

    if data is None:
        raise RuntimeError(last_err)
    cand = (data.get("candidates") or [{}])[0]
    parts = cand.get("content", {}).get("parts") or []
    reply = "\n".join(p.get("text", "") for p in parts if p.get("text")).strip() or "Maaf kijiye, iska jawab nahi mil paya."
    chunks = cand.get("groundingMetadata", {}).get("groundingChunks") or []
    sources, seen = [], set()
    for ch in chunks:
        web = ch.get("web") or {}
        uri, title = web.get("uri"), web.get("title") or web.get("uri")
        if uri and uri not in seen:
            seen.add(uri)
            sources.append(f"- [{title}]({uri})")
        if len(sources) >= 3:
            break
    if sources:
        reply += "\n\n**🌐 Sources:**\n" + "\n".join(sources)
    return reply



def call_openai(history, model, api_key, system_text, temp=0.65):
    if not api_key:
        raise ValueError("OpenAI API Key missing hai.")
    model = model or "gpt-6-luna"
    msgs = [{"role": "system", "content": system_text}]
    for m in history:
        role = "assistant" if m.get("role") == "assistant" else "user"
        txt = (m.get("content") or "").strip()
        if m.get("image") and role == "user":
            arr = ([{"type": "text", "text": txt}] if txt else []) + [{"type": "image_url", "image_url": {"url": f"data:{m.get('mime') or 'image/jpeg'};base64,{m['image']}"}}]
            msgs.append({"role": role, "content": arr})
        else:
            msgs.append({"role": role, "content": txt or "Hello"})
    req = urllib.request.Request("https://api.openai.com/v1/chat/completions", data=json.dumps({"model": model, "messages": msgs, "temperature": temp}).encode("utf-8"), headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}, method="POST")
    with urllib.request.urlopen(req, timeout=75) as resp:
        return json.loads(resp.read().decode("utf-8"))["choices"][0]["message"]["content"]


def call_llm_json(cfg, prompt, sys_txt, temp=0.85):
    hist = [{"role": "user", "content": prompt}]
    raw = call_gemini(hist, cfg["model"], cfg["api_key"], sys_txt, False, temp=temp) if cfg["provider"] == "gemini" else call_openai(hist, cfg["model"], cfg["api_key"], sys_txt, temp=temp)
    m = re.search(r"\{[\s\S]*\}", raw)
    if not m:
        raise RuntimeError("Structured output parse nahi ho paya. Dubara try karein.")
    return json.loads(m.group(0))


MANIFEST_JSON = json.dumps({
    "id": "/?sr=v5", "name": "Shehja — SR", "short_name": "SR", "start_url": "/?sr=v5", "display": "standalone",
    "background_color": "#060913", "theme_color": "#10a37f",
    "icons": [
        {"src": "/icon-192.png?v=5", "sizes": "192x192", "type": "image/png", "purpose": "any"},
        {"src": "/icon-512.png?v=5", "sizes": "512x512", "type": "image/png", "purpose": "any"},
        {"src": "/icon.svg?v=5", "sizes": "any", "type": "image/svg+xml"},
    ],
})
SW_JS = "self.addEventListener('fetch', function(e) {});"


class ShehjaHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def get_session_user(self):
        c = http.cookies.SimpleCookie()
        try:
            c.load(self.headers.get("Cookie", ""))
        except Exception:
            return None
        tok = c["shehja_token"].value if "shehja_token" in c else ""
        if not tok:
            return None
        row = db_exec("SELECT u.id, u.name, u.email FROM sessions s JOIN users u ON s.user_id = u.id WHERE s.token = ?", (tok,), fetch="one")
        return {"id": row[0], "name": row[1], "email": row[2]} if row else None

    def send_bytes(self, status, ctype, body, extra_headers=None):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        if extra_headers:
            for k, v in extra_headers.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, status, data, extra_headers=None):
        self.send_bytes(status, "application/json; charset=utf-8", json.dumps(data).encode("utf-8"), extra_headers)

    def read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length).decode("utf-8") if length else "{}")

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path == "/":
            with open(INDEX_PATH, "rb") as f:
                self.send_bytes(200, "text/html; charset=utf-8", f.read(), {"Cache-Control": "no-store"})
        elif path == "/manifest.json":
            self.send_bytes(200, "application/manifest+json; charset=utf-8", MANIFEST_JSON.encode("utf-8"), {"Cache-Control": "no-store"})
        elif path == "/icon.svg":
            self.send_bytes(200, "image/svg+xml; charset=utf-8", ICON_SVG.encode("utf-8"), {"Cache-Control": "no-store"})
        elif path == "/icon-192.png":
            self.send_bytes(200, "image/png", make_sr_png(192), {"Cache-Control": "no-store"})
        elif path == "/icon-512.png":
            self.send_bytes(200, "image/png", make_sr_png(512), {"Cache-Control": "no-store"})
        elif path == "/sw.js":
            self.send_bytes(200, "application/javascript; charset=utf-8", SW_JS.encode("utf-8"))
        elif path == "/api/auth/me":
            u = self.get_session_user()
            last_topic = ""
            if u:
                r = db_exec("SELECT title FROM user_chats WHERE user_id = ? ORDER BY updated_at DESC LIMIT 1", (u["id"],), fetch="one")
                if r:
                    last_topic = r[0]
            self.send_json(200, {"user": u, "last_topic": last_topic, "smtp_enabled": smtp_configured()})
        elif path == "/api/chats":
            u = self.get_session_user()
            if not u:
                self.send_json(200, [])
                return
            rows = db_exec("SELECT id, title FROM user_chats WHERE user_id = ? ORDER BY updated_at DESC LIMIT 40", (u["id"],), fetch="all") or []
            self.send_json(200, [{"id": r[0], "title": r[1]} for r in rows])
        elif path.startswith("/api/chats/"):
            u = self.get_session_user()
            cid = urllib.parse.unquote(path[len("/api/chats/"):])
            if not u or not db_exec("SELECT id FROM user_chats WHERE id = ? AND user_id = ?", (cid, u["id"]), fetch="one"):
                self.send_json(404, {"error": "Not found"})
                return
            rows = db_exec("SELECT role, content FROM user_messages WHERE chat_id = ? ORDER BY seq ASC", (cid,), fetch="all") or []
            self.send_json(200, [{"role": r[0], "content": r[1]} for r in rows])
        elif path == "/health":
            try:
                db_exec("SELECT 1", fetch="one")
                self.send_json(200, {"status": "ok", "db": "neon" if USE_PG else "sqlite", "uptime_sec": int(time.time() - START_TIME)})
            except Exception as e:
                self.send_json(500, {"status": "error", "error": str(e)})
        elif path == "/api/admin/backup":
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            pin = (qs.get("pin") or [""])[0].strip()
            cfg = get_config()
            if pin != cfg["admin_pin"]:
                self.send_json(403, {"error": "Wrong PIN"})
                return
            users = db_exec("SELECT id, name, email, sec_q, created_at FROM users", fetch="all") or []
            chats = db_exec("SELECT id, user_id, title, updated_at FROM user_chats", fetch="all") or []
            msgs = db_exec("SELECT id, chat_id, seq, role, content, created_at FROM user_messages", fetch="all") or []
            bk = json.dumps({"users": users, "chats": chats, "messages": msgs}, default=str).encode("utf-8")
            self.send_bytes(200, "application/json", bk, {"Content-Disposition": 'attachment; filename="shehja_backup.json"'})
        elif path == "/api/kitchen":
            u = self.get_session_user()
            self.send_json(200, get_kitchen_profile(u["id"] if u else None))
        elif path == "/api/panchang":
            self.send_json(200, get_today_panchang())
        elif path == "/api/settings":
            cfg = get_config()
            self.send_json(200, {"provider": cfg["provider"], "model": cfg["model"], "has_key": bool(cfg["api_key"]), "custom_prompt": cfg["custom_prompt"]})
        elif path.startswith("/api/ppt/"):
            item = _PPT_CACHE.get(urllib.parse.unquote(path[len("/api/ppt/"):]))
            if not item:
                self.send_json(404, {"error": "Expired"})
                return
            self.send_bytes(200, "application/vnd.openxmlformats-officedocument.presentationml.presentation", item[1], {"Content-Disposition": f'attachment; filename="{item[0]}"'})
        elif path.startswith("/api/xlsx/"):
            item = _XLSX_CACHE.get(urllib.parse.unquote(path[len("/api/xlsx/"):]))
            if not item:
                self.send_json(404, {"error": "Expired"})
                return
            self.send_bytes(200, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", item[1], {"Content-Disposition": f'attachment; filename="{item[0]}"'})
        elif path.startswith("/api/img/"):
            item = _IMG_CACHE.get(urllib.parse.unquote(path[len("/api/img/"):]))
            if not item:
                self.send_json(404, {"error": "Expired"})
                return
            self.send_bytes(200, item[0], item[1])
        else:
            self.send_json(404, {"error": "Not found"})

    def do_DELETE(self):
        path = urllib.parse.urlparse(self.path).path
        if path.startswith("/api/chats/"):
            u = self.get_session_user()
            if not u:
                self.send_json(401, {"error": "Unauthorized"})
                return
            cid = urllib.parse.unquote(path[len("/api/chats/"):])
            if db_exec("SELECT id FROM user_chats WHERE id = ? AND user_id = ?", (cid, u["id"]), fetch="one"):
                db_exec("DELETE FROM user_messages WHERE chat_id = ?", (cid,))
                db_exec("DELETE FROM user_chats WHERE id = ?", (cid,))
            self.send_json(200, {"ok": True})
            return
        self.send_json(404, {"error": "Not found"})

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path

        if path == "/api/auth/signup":
            d = self.read_json()
            name, email, pw = (d.get("name") or "").strip(), (d.get("email") or "").strip().lower(), d.get("password") or ""
            sec_q, sec_a = (d.get("sec_q") or "").strip(), (d.get("sec_a") or "").strip().lower()
            if not name or "@" not in email or len(pw) < 6 or not sec_a:
                self.send_json(400, {"error": "Naam, Email, 6+ char Password aur Secret Answer zaroori hai!"})
                return
            if db_exec("SELECT id FROM users WHERE email = ?", (email,), fetch="one"):
                self.send_json(400, {"error": "Email pehle se registered hai. Sign In karein!"})
                return
            uid, tok, now = uuid.uuid4().hex, uuid.uuid4().hex + uuid.uuid4().hex, int(time.time())
            db_exec("INSERT INTO users (id, name, email, pass_hash, sec_q, sec_a_hash, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)", (uid, name, email, hash_secret(pw), sec_q, hash_secret(sec_a), now))
            db_exec("INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)", (tok, uid, now))
            self.send_json(200, {"user": {"id": uid, "name": name, "email": email}}, {"Set-Cookie": f"shehja_token={tok}; Path=/; HttpOnly; SameSite=Lax; Max-Age=2592000"})
            return

        if path == "/api/auth/login":
            d = self.read_json()
            email, pw = (d.get("email") or "").strip().lower(), d.get("password") or ""
            row = db_exec("SELECT id, name, email, pass_hash FROM users WHERE email = ?", (email,), fetch="one")
            if not row or not verify_secret(pw, row[3]):
                self.send_json(401, {"error": "Email ya Password galat hai!"})
                return
            tok = uuid.uuid4().hex + uuid.uuid4().hex
            db_exec("INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)", (tok, row[0], int(time.time())))
            self.send_json(200, {"user": {"id": row[0], "name": row[1], "email": row[2]}}, {"Set-Cookie": f"shehja_token={tok}; Path=/; HttpOnly; SameSite=Lax; Max-Age=2592000"})
            return

        if path == "/api/auth/logout":
            c = http.cookies.SimpleCookie()
            try:
                c.load(self.headers.get("Cookie", ""))
                if "shehja_token" in c:
                    db_exec("DELETE FROM sessions WHERE token = ?", (c["shehja_token"].value,))
            except Exception:
                pass
            self.send_json(200, {"ok": True}, {"Set-Cookie": "shehja_token=; Path=/; HttpOnly; Max-Age=0"})
            return

        if path == "/api/auth/forgot-question":
            email = (self.read_json().get("email") or "").strip().lower()
            row = db_exec("SELECT sec_q FROM users WHERE email = ?", (email,), fetch="one")
            if not row:
                self.send_json(404, {"error": "Email registered nahi hai!"})
                return
            self.send_json(200, {"sec_q": row[0]})
            return

        if path == "/api/auth/reset-question":
            d = self.read_json()
            email, ans, pw = (d.get("email") or "").strip().lower(), (d.get("sec_a") or "").strip().lower(), d.get("new_password") or ""
            if len(pw) < 6:
                self.send_json(400, {"error": "Password min 6 chars ka hona chahiye!"})
                return
            row = db_exec("SELECT id, sec_a_hash FROM users WHERE email = ?", (email,), fetch="one")
            if not row or not verify_secret(ans, row[1]):
                self.send_json(403, {"error": "Secret Answer galat hai!"})
                return
            db_exec("UPDATE users SET pass_hash = ? WHERE id = ?", (hash_secret(pw), row[0]))
            self.send_json(200, {"ok": True})
            return

        if path == "/api/auth/send-otp":
            email = (self.read_json().get("email") or "").strip().lower()
            if not db_exec("SELECT id FROM users WHERE email = ?", (email,), fetch="one"):
                self.send_json(404, {"error": "Email registered nahi hai!"})
                return
            otp = str(random.randint(100000, 999999))
            try:
                send_otp_email(email, otp)
            except Exception as e:
                self.send_json(400, {"error": str(e)})
                return
            db_exec("INSERT INTO otps (email, otp_hash, expires_at) VALUES (?, ?, ?) ON CONFLICT (email) DO UPDATE SET otp_hash = EXCLUDED.otp_hash, expires_at = EXCLUDED.expires_at", (email, hash_secret(otp), int(time.time()) + 600))
            self.send_json(200, {"ok": True})
            return

        if path == "/api/auth/reset-otp":
            d = self.read_json()
            email, otp, pw = (d.get("email") or "").strip().lower(), (d.get("otp") or "").strip(), d.get("new_password") or ""
            if len(pw) < 6:
                self.send_json(400, {"error": "Password min 6 chars ka hona chahiye!"})
                return
            row = db_exec("SELECT otp_hash, expires_at FROM otps WHERE email = ?", (email,), fetch="one")
            if not row or int(time.time()) > int(row[1]) or not verify_secret(otp, row[0]):
                self.send_json(403, {"error": "OTP galat ya expire ho gaya hai!"})
                return
            db_exec("UPDATE users SET pass_hash = ? WHERE email = ?", (hash_secret(pw), email))
            db_exec("DELETE FROM otps WHERE email = ?", (email,))
            self.send_json(200, {"ok": True})
            return

        if path == "/api/numerology":
            try:
                d = self.read_json()
                nu = compute_numerology(
                    d.get("dob", "2000-01-01"), d.get("name", ""),
                    d.get("mother_name", ""), d.get("gender", "Male"),
                    d.get("extra_num", ""), d.get("prashna_num", ""),
                )
                svg = render_loshu_svg(nu["counts"])
                cfg = get_config()
                if cfg["provider"] == "demo":
                    reading = f"Pranam {nu['name']}! Aapka Mulank **{nu['mulank']}**, Bhagyank **{nu['bhagyank']}**, Kua **{nu['kua']}** aur Naam Ank **{nu['naam_ank']}** hai. Lucky Numbers: **{nu['lucky_numbers']}**. *(Demo Mode)*"
                else:
                    sys_txt = build_system_prompt("shastri", None, False, cfg["custom_prompt"])
                    q_txt = (
                        f"Complete Vedic & Lo Shu Numerology Report:\n"
                        f"- Naam: {nu['name']} (Chaldean Total: {nu['chaldean_raw']} -> {nu['naam_ank']}), Maa ka Naam Ank: {nu['matri_ank']}\n"
                        f"- Birth Date: {nu['dob']} ({nu['gender']})\n"
                        f"- Mulank (Driver): {nu['mulank']} ({nu['ruler']}), Bhagyank (Conductor): {nu['bhagyank']}, Kua Number: {nu['kua']}\n"
                        f"- Active Lo Shu Rajyogs/Planes: {', '.join(nu['active_planes']) or 'Mixed'}\n"
                        f"- Strong/Repeated Numbers: {', '.join(nu['strong']) or 'Balanced'}\n"
                        f"- Missing Numbers: {nu['missing']}\n"
                        f"- Lucky Days: {nu['lucky_day']}, Lucky Colors: {nu['lucky_color']}, Lucky Numbers: {nu['lucky_numbers']}\n"
                        f"- Mobile/Vehicle Number Check ({nu['extra_num'] or 'None'}): {nu['extra_status'] or 'N/A'}\n"
                        f"- Prashna Number (1-108): {nu['prashna_num'] or 'N/A'} (Reduced: {nu['prashna_red']}) | Question: {d.get('question') or 'General Life Guidance'}\n\n"
                        "Shastri Ji (Master Numerologist), is exact ank-jyotish aur Lo Shu Grid ke aadhar par Personality, Career/Business, Name Spelling Harmony, Missing Number ke Simple Remedies/Upay, Mobile/Vehicle check (agar diya ho), aur Prashna/Future Guidance warm Hinglish mein vistaar se batayein."
                    )
                    reading = call_gemini([{"role": "user", "content": q_txt}], cfg["model"], cfg["api_key"], sys_txt, False) if cfg["provider"] == "gemini" else call_openai([{"role": "user", "content": q_txt}], cfg["model"], cfg["api_key"], sys_txt)
                self.send_json(200, {"num": nu, "svg": svg, "reading": reading})
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        if path == "/api/tarot":
            try:
                d = self.read_json()
                question = (d.get("question") or "Mera aane wala samay kaisa rahega?").strip()
                picks = random.sample(TAROT_DECK, 3)
                cards = [
                    {"pos": "1. Past / Jad", "name": picks[0][0], "meaning": picks[0][1]},
                    {"pos": "2. Present / Abhi", "name": picks[1][0], "meaning": picks[1][1]},
                    {"pos": "3. Future & Salah", "name": picks[2][0], "meaning": picks[2][1]},
                ]
                cfg = get_config()
                if cfg["provider"] == "demo":
                    reading = f"Aapke 3 Tarot Cards: **{cards[0]['name']}**, **{cards[1]['name']}**, aur **{cards[2]['name']}**. *(Demo Mode)*"
                else:
                    sys_txt = build_system_prompt("shastri", None, False, cfg["custom_prompt"])
                    q_txt = (
                        f"3-Card Tarot Reading for Question: '{question}'\n"
                        f"- {cards[0]['pos']}: {cards[0]['name']} ({cards[0]['meaning']})\n"
                        f"- {cards[1]['pos']}: {cards[1]['name']} ({cards[1]['meaning']})\n"
                        f"- {cards[2]['pos']}: {cards[2]['name']} ({cards[2]['meaning']})\n\n"
                        "Shastri Ji, in 3 Tarot cards ke aadhar par user ke sawaal ka heartfelt, clear aur sakaratmak (positive) guidance Hinglish mein samjhayein."
                    )
                    reading = call_gemini([{"role": "user", "content": q_txt}], cfg["model"], cfg["api_key"], sys_txt, False) if cfg["provider"] == "gemini" else call_openai([{"role": "user", "content": q_txt}], cfg["model"], cfg["api_key"], sys_txt)
                self.send_json(200, {"question": question, "cards": cards, "reading": reading})
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        if path == "/api/kundli":
            try:
                d = self.read_json()
                k = compute_kundli(
                    d.get("dob", "2000-01-01"), d.get("tob", "12:00"),
                    d.get("city", "Ahmedabad"), d.get("name", ""),
                    d.get("mother_name", ""), d.get("dharma", "Sanatan / Hindu"),
                )
                svg = render_kundli_svg(k)
                cfg = get_config()
                if cfg["provider"] == "demo":
                    reading = f"Pranam {k['name']}! Aapka Lagna **{k['lagna']}**, Chandra Rashi **{k['moon_rashi']}**, aur Nakshatra **{k['nakshatra']}** hai. Mulank **{k['mulank']}** aur Bhagyank **{k['bhagyank']}** hai. *(Demo Mode — API key lagane par poori Kundli faladesh aayegi!)*"
                else:
                    sys_txt = build_system_prompt("shastri", None, False, cfg["custom_prompt"])
                    q_txt = (
                        f"Jatak Details (Exact Calculated Vedic Chart):\n"
                        f"- Naam: {k['name']} (Naam Ank: {k['naam_ank']}), Maa ka Naam: {k['mother_name'] or 'N/A'} (Matri Ank: {k['matri_ank']})\n"
                        f"- Dharma/Parampara: {k['dharma']}\n"
                        f"- Birth: {k['dob']} at {k['tob']} in {k['city']} ({k['vaar']})\n"
                        f"- Tithi: {k['tithi']}, Lagna: {k['lagna']}, Chandra Rashi: {k['moon_rashi']}, Surya Rashi: {k['sun_rashi']}\n"
                        f"- Nakshatra: {k['nakshatra']} (Naam Akshar: {k['nak_akshar']}, Lord: {k['nak_lord']})\n"
                        f"- Current Dasha: {k['cur_dasha']}, Manglik: {k['manglik']}, Shani: {k['sade_sati']}\n"
                        f"- Mulank: {k['mulank']}, Bhagyank: {k['bhagyank']}\n"
                        f"- Planet Houses: {json.dumps(k['planets'])}\n\n"
                        f"Shastri Ji, upar diye exact grah-nakshatra ke aadhar par {k['dharma']} parampara ke anusaar "
                        "Jatak ki **poori Janam Kundli Faladesh** (Swabhav & Personality, Career & Finance, Education, Marriage & Family, Health, aur Positive Upay/Mantra/Daan/Lucky Color) warm Hinglish mein vistaar se batayein."
                    )
                    reading = call_gemini([{"role": "user", "content": q_txt}], cfg["model"], cfg["api_key"], sys_txt, False) if cfg["provider"] == "gemini" else call_openai([{"role": "user", "content": q_txt}], cfg["model"], cfg["api_key"], sys_txt)
                self.send_json(200, {"kundli": k, "svg": svg, "reading": reading})
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        if path == "/api/milan":
            try:
                d = self.read_json()
                k1 = compute_kundli(d.get("dob1", "2000-01-01"), d.get("tob1", "12:00"), d.get("city1", "Ahmedabad"), d.get("name1", "Var"))
                k2 = compute_kundli(d.get("dob2", "2001-01-01"), d.get("tob2", "12:00"), d.get("city2", "Ahmedabad"), d.get("name2", "Vadhu"))
                gm = compute_gun_milan(k1, k2)
                cfg = get_config()
                if cfg["provider"] == "demo":
                    reading = f"Gun Milan Score: **{gm['total']} / 36**. *(Demo Mode)*"
                else:
                    sys_txt = build_system_prompt("shastri", None, False, cfg["custom_prompt"])
                    q_txt = (
                        f"Kundli Milan Report:\n"
                        f"- {k1['name']}: Rashi {k1['moon_rashi']}, Nakshatra {k1['nakshatra']}, Manglik: {k1['manglik']}\n"
                        f"- {k2['name']}: Rashi {k2['moon_rashi']}, Nakshatra {k2['nakshatra']}, Manglik: {k2['manglik']}\n"
                        f"- Ashtakoot Gun Score: {gm['total']} / 36 (Varna {gm['varna']}, Vashya {gm['vashya']}, Tara {gm['tara']}, Yoni {gm['yoni']}, Maitri {gm['maitri']}, Gana {gm['gana']}, Bhakoot {gm['bhakoot']}, Nadi {gm['nadi']})\n\n"
                        "Shastri Ji, is 36-Gun Milan aur Manglik stithi ka santulit aur sakaratmak vishleshan Hinglish mein karein."
                    )
                    reading = call_gemini([{"role": "user", "content": q_txt}], cfg["model"], cfg["api_key"], sys_txt, False) if cfg["provider"] == "gemini" else call_openai([{"role": "user", "content": q_txt}], cfg["model"], cfg["api_key"], sys_txt)
                self.send_json(200, {"milan": gm, "k1": k1, "k2": k2, "reading": reading})
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        if path == "/api/settings":
            d = self.read_json()
            cfg = get_config()
            if str(d.get("pin") or "").strip() != cfg["admin_pin"]:
                self.send_json(403, {"error": "Galat Secret Admin Password!"})
                return
            save_config(d.get("provider", "demo"), d.get("model", "gemini-3.5-flash-lite"), d.get("api_key", ""), str(d.get("new_pin") or "").strip(), d.get("custom_prompt"))
            self.send_json(200, {"ok": True})
            return

        if path == "/api/tts":
            try:
                d = self.read_json()
                txt, per, tn = d.get("text") or "", d.get("persona", "shehja"), d.get("tone", "auto")
                aud, mime, s_err = None, None, "no_key"
                if os.environ.get("SARVAM_API_KEY", "").strip():
                    try:
                        aud, mime = synth_sarvam_audio(txt, per, tn)
                        s_err = "ok"
                    except urllib.error.HTTPError as he:
                        s_err = f"http_{he.code}_" + he.read().decode("utf-8", errors="ignore")[:100]
                    except Exception as ex:
                        s_err = str(ex)[:100]
                if aud:
                    self.send_bytes(200, mime, aud, {"X-TTS-Engine": "sarvam-bulbul-v3"})
                    return
                mp3 = synth_neural_mp3(txt, per, tn)
                if not mp3:
                    self.send_json(503, {"error": "TTS fallback"})
                    return
                self.send_bytes(200, "audio/mpeg", mp3, {"X-TTS-Engine": "edge-tts", "X-Sarvam-Status": s_err.replace("\n", " ")})
            except Exception:
                self.send_json(503, {"error": "TTS fallback"})
            return

        if path == "/api/image":
            try:
                d = self.read_json()
                prompt = (d.get("prompt") or "").strip()
                size = d.get("size", "1024x1024")
                w, h = (size.split("x") if "x" in size else ("1024", "1024"))
                seed = random.randint(1, 999999)
                url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width={w}&height={h}&seed={seed}&nologo=true"
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=45) as resp:
                    img_bytes = resp.read()
                    ctype = resp.headers.get("Content-Type", "image/jpeg")
                iid = uuid.uuid4().hex[:12]
                if len(_IMG_CACHE) >= 15:
                    _IMG_CACHE.pop(next(iter(_IMG_CACHE)))
                _IMG_CACHE[iid] = (ctype, img_bytes)
                self.send_json(200, {"url": f"/api/img/{iid}"})
            except Exception as e:
                self.send_json(500, {"error": f"Image generate nahi ho payi: {e}"})
            return

        if path == "/api/xlsx":
            try:
                d = self.read_json()
                topic = (d.get("topic") or "").strip()
                cfg = get_config()
                if cfg["provider"] == "demo":
                    x_data = {"title": topic[:24] or "Data", "headers": ["Item", "Category", "Value", "Notes"], "rows": [["Sample A", "Core", 85, "Good"], ["Sample B", "Test", 92, "Best"]]}
                else:
                    p = f'Create a neat Excel table for: "{topic}". Return ONLY JSON: {{"title":"SheetTitle","headers":["Col1","Col2","Col3"],"rows":[["v1",10,"note"]]}}'
                    x_data = call_llm_json(cfg, p, "Output ONLY strict valid JSON for a spreadsheet.", temp=0.4)
                raw = build_xlsx_bytes(x_data.get("title", "Sheet1"), x_data.get("headers", ["A"]), x_data.get("rows", []))
                xid = uuid.uuid4().hex[:12]
                fname = (re.sub(r"[^a-zA-Z0-9_-]+", "_", topic)[:28] or "Shehja_Sheet") + ".xlsx"
                if len(_XLSX_CACHE) >= 20:
                    _XLSX_CACHE.pop(next(iter(_XLSX_CACHE)))
                _XLSX_CACHE[xid] = (fname, raw)
                self.send_json(200, {"xlsx_id": xid, "filename": fname, "sheet": x_data})
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        if path == "/api/ppt":
            try:
                d = self.read_json()
                topic = (d.get("topic") or "").strip()
                cfg = get_config()
                if cfg["provider"] == "demo":
                    lays = random.sample(LAYOUTS, 3)
                    ppt_data = {"title": topic.title(), "subtitle": f"{d.get('style')} ({d.get('lang')})", "slides": [{"layout": lays[0], "heading": f"Intro: {topic}", "bullets": ["Definition & overview", "Core importance", "Key scope", "Real example"], "takeaway": "Strong base."}, {"layout": lays[1], "heading": "Details", "bullets": ["Step 1", "Step 2", "Step 3", "Step 4"], "takeaway": "Clear flow."}]}
                else:
                    cnt = max(3, min(12, int(d.get("count", 8)) - 2))
                    ang = random.choice(["visual storytelling", "analytical breakdown", "future-focused", "step-by-step practical"])
                    p = f'Design a UNIQUE {d.get("style")} presentation on "{topic}". Angle: {ang}. Language: {d.get("lang")}. Content slides: {cnt}. Pick varied "layout" from ["grid","split","highlight","timeline","classic"]. Return ONLY JSON: {{"title":"...","subtitle":"...","slides":[{{"layout":"grid","heading":"...","bullets":["..."],"takeaway":"..."}}]}}'
                    ppt_data = call_llm_json(cfg, p, "Expert educator & presentation designer. Output ONLY strict JSON.", temp=0.9)
                raw, used_theme = build_pptx_bytes(ppt_data, d.get("theme", "auto"))
                pid = uuid.uuid4().hex[:12]
                fname = (re.sub(r"[^a-zA-Z0-9_-]+", "_", topic)[:28] or "Shehja_PPT") + "_SR.pptx"
                if len(_PPT_CACHE) >= 20:
                    _PPT_CACHE.pop(next(iter(_PPT_CACHE)))
                _PPT_CACHE[pid] = (fname, raw)
                self.send_json(200, {"ppt_id": pid, "filename": fname, "used_theme": used_theme, "ppt": ppt_data})
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        if path == "/api/creator":
            try:
                d = self.read_json()
                topic, kind, style, lang = (d.get("topic") or "").strip(), d.get("kind", "reel_30s"), d.get("style", "AI Style"), d.get("lang", "Hindi")
                cfg = get_config()
                if cfg["provider"] == "demo":
                    c_data = {"title": topic or "Creator Studio", "caption": "Demo script & lyrics", "scenes": [{"heading": "Scene 1", "narration": f"Namaste dosto! Aaj hum baat karenge {topic} ke baare mein."}, {"heading": "Scene 2", "narration": "Yeh bilkul simple aur interesting topic hai."}]}
                else:
                    p = f'Create a {kind} ({style}) creative script/song in {lang} on "{topic}". For songs, write catchy rhyming verse/chorus lines in scenes. Return ONLY JSON: {{"title":"Title","caption":"Full lyrics or social caption with hashtags","scenes":[{{"heading":"Scene/Verse 1","narration":"Spoken or sung lines (15-25 words)"}}]}} (4 to 6 scenes).'
                    c_data = call_llm_json(cfg, p, "Creative Director, Lyricist & Video Scriptwriter. Output ONLY valid JSON.", temp=0.9)
                self.send_json(200, c_data)
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        if path == "/api/chat":
            try:
                d = self.read_json()
                history = d.get("history") or []
                if not history:
                    self.send_json(400, {"error": "Message khali hai"})
                    return
                cfg = get_config()
                persona = d.get("persona", "shehja")
                live_mode = bool(d.get("live_mode", False))
                tone = d.get("tone", "auto")
                u = self.get_session_user()
                kitchen_ctx = get_kitchen_profile(u["id"]) if (u and persona == "sweety") else (d.get("kitchen") if persona == "sweety" else None)
                if kitchen_ctx is not None:
                    if isinstance(d.get("kitchen"), dict):
                        if d["kitchen"].get("members"):
                            kitchen_ctx["members"] = d["kitchen"]["members"]
                        if d["kitchen"].get("occasion"):
                            kitchen_ctx["occasion"] = d["kitchen"]["occasion"]
                    kitchen_ctx["season"] = get_indian_season()
                sys_txt = build_system_prompt(persona, d.get("edu"), bool(d.get("group_mode")), cfg["custom_prompt"], kitchen_ctx=kitchen_ctx)
                if live_mode:
                    sys_txt += "\n\nLIVE TALK SYNC RULE: Keep reply warm, natural, and crisp (2-4 sentences). At the VERY END, add [SPOKEN]your exact reply converted to smooth spoken Devanagari Hindi with soft commas and '।' (no '...', no emojis)[/SPOKEN] so voice plays instantly."
                last_txt = history[-1].get("content", "")
                if cfg["provider"] == "demo":
                    reply = call_demo(last_txt, persona)
                elif cfg["provider"] == "gemini":
                    reply = call_gemini(history, cfg["model"], cfg["api_key"], sys_txt, bool(d.get("use_search", False)))
                else:
                    reply = call_openai(history, cfg["model"], cfg["api_key"], sys_txt)

                spoken_txt = None
                m_sp = re.search(r"\[SPOKEN\]([\s\S]*?)\[/SPOKEN\]", reply)
                if m_sp:
                    spoken_txt = m_sp.group(1).strip()
                    reply = re.sub(r"\s*\[SPOKEN\][\s\S]*?\[/SPOKEN\]", "", reply).strip()

                kitchen_updates = {}
                if persona == "sweety":
                    m_ck = re.search(r"\[COOKED\]([\s\S]*?)\[/COOKED\]", reply)
                    if m_ck:
                        dish = m_ck.group(1).strip()
                        reply = re.sub(r"\s*\[COOKED\][\s\S]*?\[/COOKED\]", "", reply).strip()
                        if dish:
                            today_s = time.strftime("%d %b")
                            kitchen_updates["cooked"] = {"date": today_s, "dish": dish}
                            if u and kitchen_ctx is not None:
                                kitchen_ctx["history"] = ([{"date": today_s, "dish": dish}] + (kitchen_ctx.get("history") or []))[:30]
                    m_gr = re.search(r"\[GROCERY\]([\s\S]*?)\[/GROCERY\]", reply)
                    if m_gr:
                        items = [x.strip() for x in re.split(r"[,\n]+", m_gr.group(1)) if x.strip()]
                        reply = re.sub(r"\s*\[GROCERY\][\s\S]*?\[/GROCERY\]", "", reply).strip()
                        if items:
                            kitchen_updates["grocery"] = items
                            if u and kitchen_ctx is not None:
                                existing = {g.get("item","").lower() for g in (kitchen_ctx.get("grocery") or [])}
                                for it in items:
                                    if it.lower() not in existing:
                                        kitchen_ctx.setdefault("grocery", []).append({"item": it, "done": False})
                    if u and kitchen_updates and kitchen_ctx is not None:
                        save_kitchen_profile(u["id"], kitchen_ctx)

                cid = d.get("chat_id")
                if u:
                    now = int(time.time())
                    if not cid:
                        cid = "c_" + uuid.uuid4().hex[:12]
                        db_exec("INSERT INTO user_chats (id, user_id, title, updated_at) VALUES (?, ?, ?, ?)", (cid, u["id"], (last_txt or "Chat")[:38], now))
                    else:
                        db_exec("UPDATE user_chats SET updated_at = ? WHERE id = ? AND user_id = ?", (now, cid, u["id"]))
                    cnt_row = db_exec("SELECT COALESCE(MAX(seq), 0) FROM user_messages WHERE chat_id = ?", (cid,), fetch="one")
                    seq = int(cnt_row[0]) if cnt_row else 0
                    db_exec("INSERT INTO user_messages (id, chat_id, seq, role, content, created_at) VALUES (?, ?, ?, 'user', ?, ?)", (uuid.uuid4().hex, cid, seq + 1, last_txt, now))
                    db_exec("INSERT INTO user_messages (id, chat_id, seq, role, content, created_at) VALUES (?, ?, ?, 'assistant', ?, ?)", (uuid.uuid4().hex, cid, seq + 2, reply, now))

                audio_b64, audio_mime = "", ""
                if live_mode:
                    try:
                        aud, am = synth_sarvam_audio(reply, persona, tone, spoken_override=spoken_txt)
                        if not aud:
                            aud = synth_neural_mp3(spoken_txt or reply, persona, tone)
                            am = "audio/mpeg"
                        if aud:
                            audio_b64 = base64.b64encode(aud).decode("ascii")
                            audio_mime = am or "audio/mpeg"
                    except Exception:
                        pass

                self.send_json(200, {"reply": reply, "chat_id": cid, "audio_b64": audio_b64, "audio_mime": audio_mime, "kitchen_updates": kitchen_updates})
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        self.send_json(404, {"error": "Not found"})


if __name__ == "__main__":
    init_db()
    print(f"Shehja SR Studio Server ({'Neon PG' if USE_PG else 'SQLite'}) chal raha hai: http://localhost:{PORT}")
    ThreadingHTTPServer(("0.0.0.0", PORT), ShehjaHandler).serve_forever()
