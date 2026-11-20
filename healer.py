import time, threading

_LOCK = threading.Lock()
_HEAL_LOG = []
_TOTAL_HEALED = 0
_LAST_ALERT_TS = 0
VALID_PERSONAS = {"saifu", "ansh", "armaan", "rayan", "shastri", "sweety", "vadil"}
VALID_TONES = {"auto", "soft", "calm", "teacher", "energy"}

def record_heal(kind, detail):
    global _TOTAL_HEALED
    now = int(time.time())
    with _LOCK:
        _TOTAL_HEALED += 1
        _HEAL_LOG.append({"ts": now, "kind": kind, "detail": str(detail)[:130]})
        if len(_HEAL_LOG) > 50:
            del _HEAL_LOG[:-50]

def get_heal_stats():
    cutoff = int(time.time()) - 86400
    with _LOCK:
        h24 = sum(1 for x in _HEAL_LOG if x["ts"] >= cutoff)
        last = _HEAL_LOG[-1] if _HEAL_LOG else None
        return {
            "total_healed": _TOTAL_HEALED,
            "healed_24h": h24,
            "last_bug": (f"{last['kind']}: {last['detail']}" if last else "None (All Clean)"),
            "recent": list(reversed(_HEAL_LOG[-5:])),
        }

def maybe_alert_telegram(send_tg_fn, title, detail):
    global _LAST_ALERT_TS
    if not send_tg_fn:
        return
    now = time.time()
    with _LOCK:
        if now - _LAST_ALERT_TS < 900:
            return
        _LAST_ALERT_TS = now
    try:
        send_tg_fn(f"🛠️ <b>Saifu Self-Healer Alert</b>\n<b>{title}</b>\n<code>{str(detail)[:280]}</code>")
    except Exception:
        pass

def heal_chat_request(d, u, valid_faiths):
    if not isinstance(d, dict):
        record_heal("bad_payload", "Non-dict JSON")
        d = {}
    persona = str(d.get("persona") or "saifu").strip().lower()
    if persona not in VALID_PERSONAS:
        record_heal("bad_persona", f"{persona} -> saifu")
        persona = "saifu"
    faith = str(d.get("faith") or (u.get("faith") if isinstance(u, dict) else "") or "hindu").strip().lower()
    if faith not in valid_faiths:
        record_heal("bad_faith", f"{faith} -> hindu")
        faith = "hindu"
    tone = str(d.get("tone") or "auto").strip().lower()
    if tone not in VALID_TONES:
        tone = "auto"
    edu = d.get("edu") if isinstance(d.get("edu"), dict) else {}
    raw_hist = d.get("history") if isinstance(d.get("history"), list) else []
    healed_hist = []
    trimmed = raw_hist[-14:]
    if len(raw_hist) > 14:
        record_heal("hist_trim", f"{len(raw_hist)} -> 14 msgs")
    for idx, item in enumerate(trimmed):
        if not isinstance(item, dict):
            continue
        role = "assistant" if str(item.get("role") or "user").strip().lower() in ("assistant", "model") else "user"
        content = str(item.get("content") or "").replace("\x00", "").strip()
        if len(content) > 12000:
            content = content[:12000]
            record_heal("msg_truncate", "Oversized msg trimmed")
        is_last = (idx == len(trimmed) - 1)
        img = (item.get("image") or "") if is_last else ""
        if item.get("image") and not is_last:
            record_heal("old_img_strip", "Stripped old base64 img")
        if not content and not img:
            continue
        if not content and img:
            content = "Is photo ki har detail dhyaan se samjhao."
        healed_hist.append({"role": role, "content": content, "image": img, "mime": str(item.get("mime") or "image/jpeg")})
    return {"persona": persona, "faith": faith, "tone": tone, "edu": edu, "group_mode": bool(d.get("group_mode")), "use_search": bool(d.get("use_search")), "live_mode": bool(d.get("live_mode")), "history": healed_hist}

def heal_llm_call(primary_fn, fallback_fns=None, send_tg_fn=None):
    last_err = None
    for attempt in range(2):
        try:
            res = primary_fn()
            if res and str(res).strip():
                return str(res).strip()
            raise ValueError("Empty LLM reply")
        except Exception as e:
            last_err = e
            if attempt == 0:
                record_heal("llm_retry", str(e)[:75])
                time.sleep(0.6)
    for idx, fb_fn in enumerate(fallback_fns or []):
        try:
            res = fb_fn()
            if res and str(res).strip():
                record_heal("llm_fallback", f"Fallback #{idx+1} OK")
                return str(res).strip()
        except Exception as fe:
            last_err = fe
    record_heal("llm_fail", str(last_err)[:90])
    maybe_alert_telegram(send_tg_fn, "LLM Auto-Heal Failed", str(last_err))
    raise last_err
