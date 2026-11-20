import math
import random
import re
import struct
import zipfile
import zlib
from io import BytesIO
from xml.sax.saxutils import escape as xml_esc

_ICON_CACHE = {}

PPT_THEMES = {
    "royal": {"bg": "F8FAFC", "hero": "1E3A8A", "hdr": "1D4ED8", "card": "FFFFFF", "acc": "2563EB", "tx": "0F172A", "htx": "FFFFFF", "sub": "BFDBFE", "tk_bg": "EFF6FF", "tk_tx": "1E40AF"},
    "midnight": {"bg": "0F172A", "hero": "020617", "hdr": "1E293B", "card": "1E293B", "acc": "38BDF8", "tx": "F1F5F9", "htx": "FFFFFF", "sub": "94A3B8", "tk_bg": "0C4A6E", "tk_tx": "E0F2FE"},
    "emerald": {"bg": "0B1F1A", "hero": "064E3B", "hdr": "047857", "card": "112E26", "acc": "10A37F", "tx": "ECFDF5", "htx": "FFFFFF", "sub": "A7F3D0", "tk_bg": "065F46", "tk_tx": "D1FAE5"},
    "sunset": {"bg": "FFFBF5", "hero": "881337", "hdr": "BE123C", "card": "FFFFFF", "acc": "E11D48", "tx": "1C1917", "htx": "FFFFFF", "sub": "FECDD3", "tk_bg": "FFF1F2", "tk_tx": "9F1239"},
    "violet": {"bg": "130F26", "hero": "2E1065", "hdr": "5B21B6", "card": "1E1B3A", "acc": "A78BFA", "tx": "F5F3FF", "htx": "FFFFFF", "sub": "DDD6FE", "tk_bg": "4C1D95", "tk_tx": "EDE9FE"},
    "ocean": {"bg": "F0FDFA", "hero": "134E4A", "hdr": "0F766E", "card": "FFFFFF", "acc": "14B8A6", "tx": "0F172A", "htx": "FFFFFF", "sub": "99F6E4", "tk_bg": "CCFBF1", "tk_tx": "115E59"},
    "amber": {"bg": "FFFBEB", "hero": "78350F", "hdr": "B45309", "card": "FFFFFF", "acc": "F59E0B", "tx": "1C1917", "htx": "FFFFFF", "sub": "FDE68A", "tk_bg": "FEF3C7", "tk_tx": "92400E"},
    "slate": {"bg": "F1F5F9", "hero": "18181B", "hdr": "27272A", "card": "FFFFFF", "acc": "6366F1", "tx": "18181B", "htx": "FFFFFF", "sub": "C7D2FE", "tk_bg": "EEF2FF", "tk_tx": "3730A3"},
}
LAYOUTS = ["grid", "split", "highlight", "timeline", "classic"]

ICON_SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><defs><radialGradient id="bg" cx="50%" cy="50%" r="55%"><stop offset="0%" stop-color="#0f3d38"/><stop offset="100%" stop-color="#060913"/></radialGradient><linearGradient id="ring" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#10b981"/><stop offset="50%" stop-color="#06b6d4"/><stop offset="100%" stop-color="#f59e0b"/></linearGradient><linearGradient id="gold" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#fde047"/><stop offset="100%" stop-color="#f59e0b"/></linearGradient></defs><rect width="512" height="512" rx="115" fill="url(#bg)"/><circle cx="256" cy="256" r="212" fill="none" stroke="url(#ring)" stroke-width="14"/><circle cx="256" cy="44" r="12" fill="#34d399"/><circle cx="256" cy="468" r="12" fill="#f59e0b"/><circle cx="44" cy="256" r="12" fill="#10b981"/><circle cx="468" cy="256" r="12" fill="#fbbf24"/><text x="178" y="280" dominant-baseline="middle" text-anchor="middle" font-family="Arial Black,Arial,sans-serif" font-weight="900" font-size="195" fill="#fff">S</text><text x="334" y="280" dominant-baseline="middle" text-anchor="middle" font-family="Arial Black,Arial,sans-serif" font-weight="900" font-size="195" fill="url(#gold)">R</text><path d="M385 88 L395 118 L425 128 L395 138 L385 168 L375 138 L345 128 L375 118 Z" fill="#fef08a"/></svg>'


def _seg_dist(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    l2 = dx * dx + dy * dy
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / l2))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


def make_sr_png(size):
    if size in _ICON_CACHE:
        return _ICON_CACHE[size]
    s_segs = [(0.24, 0.36, 0.44, 0.36), (0.24, 0.36, 0.24, 0.50), (0.24, 0.50, 0.44, 0.50), (0.44, 0.50, 0.44, 0.65), (0.24, 0.65, 0.44, 0.65)]
    r_segs = [(0.55, 0.36, 0.55, 0.65), (0.55, 0.36, 0.74, 0.36), (0.74, 0.36, 0.74, 0.50), (0.55, 0.50, 0.74, 0.50), (0.63, 0.50, 0.76, 0.65)]
    nodes = [(0.50, 0.085), (0.50, 0.915), (0.085, 0.50), (0.915, 0.50)]
    raw = bytearray()
    inv = 1.0 / size
    for y in range(size):
        raw.append(0)
        py = (y + 0.5) * inv
        dyc = py - 0.5
        in_sr_y, in_star_y = 0.30 <= py <= 0.71, 0.14 <= py <= 0.34
        for x in range(size):
            px = (x + 0.5) * inv
            r = math.hypot(px - 0.5, dyc)
            glow = max(0.0, 1.0 - r * 2.1)
            br, bg, bb = int(7 + 10 * glow), int(11 + 52 * glow), int(20 + 48 * glow)
            ring_d = abs(r - 0.415)
            if ring_d < 0.032:
                ra = max(0.0, min(1.0, (0.014 - ring_d) * size + 0.5))
                if ra > 0.0:
                    t = max(0.0, min(1.0, px))
                    br, bg, bb = int(br * (1 - ra) + (16 + 229 * t) * ra), int(bg * (1 - ra) + (185 - 27 * t) * ra), int(bb * (1 - ra) + (129 - 118 * t) * ra)
            for nx, ny in nodes:
                nd = math.hypot(px - nx, py - ny)
                if nd < 0.032:
                    na = max(0.0, min(1.0, (0.022 - nd) * size + 0.5))
                    if na > 0.0:
                        br, bg, bb = int(br * (1 - na) + 56 * na), int(bg * (1 - na) + 239 * na), int(bb * (1 - na) + 200 * na)
            if in_sr_y and 0.19 <= px <= 0.49:
                sa = max(0.0, min(1.0, (0.036 - min(_seg_dist(px, py, *s) for s in s_segs)) * size + 0.5))
                if sa > 0.0:
                    br, bg, bb = int(br * (1 - sa) + 255 * sa), int(bg * (1 - sa) + 255 * sa), int(bb * (1 - sa) + 255 * sa)
            if in_sr_y and 0.50 <= px <= 0.81:
                ra = max(0.0, min(1.0, (0.036 - min(_seg_dist(px, py, *s) for s in r_segs)) * size + 0.5))
                if ra > 0.0:
                    br, bg, bb = int(br * (1 - ra) + 251 * ra), int(bg * (1 - ra) + 191 * ra), int(bb * (1 - ra) + 36 * ra)
            if in_star_y and 0.65 <= px <= 0.85:
                ux, uy = abs(px - 0.75), abs(py - 0.24)
                ka = max(0.0, min(1.0, (0.068 - min(ux * 3.2 + uy, uy * 3.2 + ux)) * size * 0.5 + 0.5))
                if ka > 0.0:
                    br, bg, bb = int(br * (1 - ka) + 254 * ka), int(bg * (1 - ka) + 240 * ka), int(bb * (1 - ka) + 138 * ka)
            raw.extend((br, bg, bb))

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(bytes(raw), 6)) + chunk(b"IEND", b"")
    _ICON_CACHE[size] = png
    return png


def _clean_xml(s):
    return xml_esc(re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", str(s or "")))


def _rect_sp(sp_id, name, x, y, cx, cy, fill_hex, paras=None, radius=False, border_hex=None):
    prst = "roundRect" if radius else "rect"
    ln = f'<a:ln w="12700"><a:solidFill><a:srgbClr val="{border_hex}"/></a:solidFill></a:ln>' if border_hex else "<a:ln><a:noFill/></a:ln>"
    fill = f'<a:solidFill><a:srgbClr val="{fill_hex}"/></a:solidFill>' if fill_hex else "<a:noFill/>"
    if paras:
        p_xml = []
        for text, sz, color, bold, align, bullet in paras:
            b_attr = ' b="1"' if bold else ' b="0"'
            al = f' algn="{align}"' if align else ""
            pfx = "•  " if bullet else ""
            spc = '<a:spcAft><a:spcPts val="700"/></a:spcAft>' if bullet else ""
            p_xml.append(f'<a:p><a:pPr{al}>{spc}</a:pPr><a:r><a:rPr lang="en-US" sz="{sz*100}"{b_attr} dirty="0"><a:solidFill><a:srgbClr val="{color}"/></a:solidFill><a:latin typeface="Calibri"/></a:rPr><a:t>{_clean_xml(pfx + text)}</a:t></a:r></a:p>')
        tx = '<p:txBody><a:bodyPr wrap="square" lIns="160000" tIns="100000" rIns="160000" bIns="100000" anchor="ctr"/><a:lstStyle/>' + "".join(p_xml) + "</p:txBody>"
    else:
        tx = '<p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:endParaRPr lang="en-US"/></a:p></p:txBody>'
    return f'<p:sp><p:nvSpPr><p:cNvPr id="{sp_id}" name="{_clean_xml(name)}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr><p:spPr><a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="{prst}"><a:avLst/></a:prstGeom>{fill}{ln}</p:spPr>{tx}</p:sp>'


def _wrap_slide(bg_hex, shapes):
    return f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:cSld><p:bg><p:bgPr><a:solidFill><a:srgbClr val="{bg_hex}"/></a:solidFill><a:effectLst/></p:bgPr></p:bg><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>{"".join(shapes)}</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>'


def _render_cover(title, subtitle, th, cs):
    if cs == 1:
        return _wrap_slide(th["hero"], [_rect_sp(2, "R", 7500000, 0, 4692000, 6858000, th["acc"]), _rect_sp(3, "B", 700000, 1200000, 3600000, 450000, th["acc"], [("SR • PRESENTATION", 12, "FFFFFF", True, "ctr", False)], radius=True), _rect_sp(4, "T", 700000, 1950000, 6300000, 2600000, None, [(title, 36, th["htx"], True, "l", False)]), _rect_sp(5, "S", 7850000, 2100000, 4000000, 2000000, None, [(subtitle, 20, "FFFFFF", True, "l", False)])])
    if cs == 2:
        return _wrap_slide(th["hero"], [_rect_sp(2, "TB", 0, 0, 12192000, 240000, th["acc"]), _rect_sp(3, "BB", 0, 6618000, 12192000, 240000, th["acc"]), _rect_sp(4, "B", 4200000, 1300000, 3792000, 460000, th["hdr"], [("PRESENTATION DECK • SR", 12, "FFFFFF", True, "ctr", False)], radius=True), _rect_sp(5, "T", 1000000, 2050000, 10192000, 2000000, None, [(title, 40, th["htx"], True, "ctr", False)]), _rect_sp(6, "S", 1400000, 4250000, 9392000, 1000000, None, [(subtitle, 19, th["sub"], False, "ctr", False)])])
    if cs == 3:
        return _wrap_slide(th["bg"], [_rect_sp(2, "F", 650000, 650000, 10892000, 5558000, th["hero"], radius=True, border_hex=th["acc"]), _rect_sp(3, "B", 1200000, 1250000, 3500000, 440000, th["acc"], [("SR SMART DECK", 12, "FFFFFF", True, "ctr", False)], radius=True), _rect_sp(4, "T", 1200000, 1950000, 9800000, 2100000, None, [(title, 38, th["htx"], True, "l", False)]), _rect_sp(5, "S", 1200000, 4250000, 9800000, 1000000, None, [(subtitle, 18, th["sub"], False, "l", False)])])
    return _wrap_slide(th["hero"], [_rect_sp(2, "Bar", 0, 0, 240000, 6858000, th["acc"]), _rect_sp(3, "B", 850000, 1200000, 3800000, 480000, th["acc"], [("SR PRESENTATION", 12, "FFFFFF", True, "ctr", False)], radius=True), _rect_sp(4, "T", 850000, 1950000, 10400000, 2100000, None, [(title, 40, th["htx"], True, "l", False)]), _rect_sp(5, "S", 850000, 4200000, 10200000, 1100000, None, [(subtitle, 20, th["sub"], False, "l", False)])])


def _render_slide(idx, sl, th, layout):
    heading = sl.get("heading") or f"Topic {idx}"
    bullets = [str(b).strip() for b in (sl.get("bullets") or []) if str(b).strip()] or ["Key concept overview."]
    takeaway = str(sl.get("takeaway") or "Core concept summary.").strip()
    if layout == "split":
        shapes = [_rect_sp(2, "Side", 0, 0, 4250000, 6858000, th["hero"]), _rect_sp(3, "Num", 450000, 550000, 820000, 480000, th["acc"], [(f"SLIDE {idx:02d}", 12, "FFFFFF", True, "ctr", False)], radius=True), _rect_sp(4, "Head", 450000, 1250000, 3400000, 2500000, None, [(heading, 26, th["htx"], True, "l", False)]), _rect_sp(5, "Take", 450000, 4450000, 3400000, 1850000, th["hdr"], [(f"💡 Key Point:\n{takeaway}", 13, "FFFFFF", False, "l", False)], radius=True)]
        for i, b in enumerate(bullets[:4]):
            shapes.append(_rect_sp(10 + i, f"B{i}", 4650000, 580000 + i * 1480000, 7000000, 1240000, th["card"], [(b, 16, th["tx"], False, "l", True)], radius=True, border_hex=th["acc"]))
        return _wrap_slide(th["bg"], shapes)
    if layout == "grid":
        shapes = [_rect_sp(2, "Hdr", 0, 0, 12192000, 1080000, th["hdr"]), _rect_sp(3, "Num", 480000, 260000, 660000, 540000, th["acc"], [(f"{idx:02d}", 17, "FFFFFF", True, "ctr", False)], radius=True), _rect_sp(4, "Head", 1300000, 180000, 10400000, 720000, None, [(heading, 25, "FFFFFF", True, "l", False)])]
        for i, b in enumerate(bullets[:4]):
            gx, gy = [(550000, 1340000), (6290000, 1340000), (550000, 3600000), (6290000, 3600000)][i]
            shapes.append(_rect_sp(10 + i, f"G{i}", gx, gy, 5350000, 2040000, th["card"], [(f"0{i+1}", 14, th["acc"], True, "l", False), (b, 16, th["tx"], False, "l", False)], radius=True, border_hex=th["acc"]))
        shapes.append(_rect_sp(20, "Take", 550000, 5880000, 11092000, 720000, th["tk_bg"], [(f"💡 {takeaway}", 14, th["tk_tx"], True, "l", False)], radius=True, border_hex=th["acc"]))
        return _wrap_slide(th["bg"], shapes)
    if layout == "highlight":
        return _wrap_slide(th["bg"], [_rect_sp(2, "Hdr", 0, 0, 12192000, 1080000, th["hdr"]), _rect_sp(3, "Num", 480000, 260000, 660000, 540000, th["acc"], [(f"{idx:02d}", 17, "FFFFFF", True, "ctr", False)], radius=True), _rect_sp(4, "Head", 1300000, 180000, 10400000, 720000, None, [(heading, 25, "FFFFFF", True, "l", False)]), _rect_sp(5, "Main", 550000, 1360000, 6900000, 5050000, th["card"], [(b, 17, th["tx"], False, "l", True) for b in bullets[:5]], radius=True, border_hex=th["acc"]), _rect_sp(6, "Spot", 7750000, 1360000, 3900000, 5050000, th["hero"], [("★ KEY INSIGHT", 14, th["sub"], True, "ctr", False), (takeaway, 18, th["htx"], True, "ctr", False)], radius=True, border_hex=th["acc"])])
    if layout == "timeline":
        shapes = [_rect_sp(2, "Hdr", 0, 0, 12192000, 1080000, th["hdr"]), _rect_sp(3, "Num", 480000, 260000, 660000, 540000, th["acc"], [(f"{idx:02d}", 17, "FFFFFF", True, "ctr", False)], radius=True), _rect_sp(4, "Head", 1300000, 180000, 10400000, 720000, None, [(heading, 25, "FFFFFF", True, "l", False)])]
        for i, b in enumerate(bullets[:4]):
            ry = 1340000 + i * 1100000
            shapes.append(_rect_sp(10 + i * 2, f"N{i}", 550000, ry, 920000, 900000, th["acc"], [(f"0{i+1}", 20, "FFFFFF", True, "ctr", False)], radius=True))
            shapes.append(_rect_sp(11 + i * 2, f"T{i}", 1640000, ry, 10000000, 900000, th["card"], [(b, 16, th["tx"], False, "l", False)], radius=True, border_hex=th["acc"]))
        shapes.append(_rect_sp(25, "Take", 550000, 5880000, 11092000, 720000, th["tk_bg"], [(f"💡 {takeaway}", 14, th["tk_tx"], True, "l", False)], radius=True, border_hex=th["acc"]))
        return _wrap_slide(th["bg"], shapes)
    return _wrap_slide(th["bg"], [_rect_sp(2, "Hdr", 0, 0, 12192000, 1120000, th["hdr"]), _rect_sp(3, "Num", 480000, 280000, 660000, 540000, th["acc"], [(f"{idx:02d}", 17, "FFFFFF", True, "ctr", False)], radius=True), _rect_sp(4, "Head", 1300000, 190000, 10400000, 740000, None, [(heading, 25, "FFFFFF", True, "l", False)]), _rect_sp(5, "Card", 550000, 1400000, 11092000, 4050000, th["card"], [(b, 18, th["tx"], False, "l", True) for b in bullets[:5]], radius=True, border_hex=th["acc"]), _rect_sp(6, "Take", 550000, 5680000, 11092000, 820000, th["tk_bg"], [(f"💡 Key Takeaway: {takeaway}", 15, th["tk_tx"], True, "l", False)], radius=True, border_hex=th["acc"])])


def build_pptx_bytes(ppt_data, theme_key="auto"):
    if theme_key == "auto" or theme_key not in PPT_THEMES:
        theme_key = random.choice(list(PPT_THEMES.keys()))
    th = PPT_THEMES[theme_key]
    title = ppt_data.get("title") or "Presentation"
    subtitle = ppt_data.get("subtitle") or "Prepared with Saifu AI (SR)"
    slides_xml = [_render_cover(title, subtitle, th, random.randint(0, 3))]
    shuffled = LAYOUTS[:]
    random.shuffle(shuffled)
    prev = None
    for idx, sl in enumerate(ppt_data.get("slides") or [], start=1):
        lay = sl.get("layout") if sl.get("layout") in LAYOUTS else shuffled[(idx - 1) % len(shuffled)]
        if lay == prev:
            lay = shuffled[idx % len(shuffled)]
        prev = lay
        sl["used_layout"] = lay
        slides_xml.append(_render_slide(idx, sl, th, lay))
    slides_xml.append(_wrap_slide(th["hero"], [_rect_sp(2, "Bar", 0, 0, 12192000, 180000, th["acc"]), _rect_sp(3, "TY", 1000000, 2100000, 10192000, 1400000, None, [("Thank You!", 48, th["htx"], True, "ctr", False)]), _rect_sp(4, "QA", 1000000, 3600000, 10192000, 800000, None, [("Questions & Discussion  •  " + title, 20, th["sub"], False, "ctr", False)])]))
    n = len(slides_xml)
    ct_s = "".join(f'<Override PartName="/ppt/slides/slide{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>' for i in range(1, n + 1))
    ct = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/><Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/><Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/><Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>' + ct_s + "</Types>"
    rrels = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/></Relationships>'
    sids = "".join(f'<p:sldId id="{255+i}" r:id="rId{i+2}"/>' for i in range(1, n + 1))
    pxml = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst><p:sldIdLst>{sids}</p:sldIdLst><p:sldSz cx="12192000" cy="6858000"/><p:notesSz cx="6858000" cy="9144000"/></p:presentation>'
    prels = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="theme/theme1.xml"/>' + "".join(f'<Relationship Id="rId{i+2}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide{i}.xml"/>' for i in range(1, n + 1)) + "</Relationships>"
    sm = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:cSld><p:bg><p:bgRef idx="1001"><a:schemeClr val="bg1"/></p:bgRef></p:bg><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/></p:spTree></p:cSld><p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/><p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst></p:sldMaster>'
    smr = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="../theme/theme1.xml"/></Relationships>'
    sl = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" type="blank" preserve="1"><p:cSld name="Blank"><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/></p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>'
    slr = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/></Relationships>'
    thm = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="SR"><a:themeElements><a:clrScheme name="SR"><a:dk1><a:sysClr val="windowText" lastClr="000000"/></a:dk1><a:lt1><a:sysClr val="window" lastClr="FFFFFF"/></a:lt1><a:dk2><a:srgbClr val="1E293B"/></a:dk2><a:lt2><a:srgbClr val="F8FAFC"/></a:lt2><a:accent1><a:srgbClr val="10A37F"/></a:accent1><a:accent2><a:srgbClr val="2563EB"/></a:accent2><a:accent3><a:srgbClr val="38BDF8"/></a:accent3><a:accent4><a:srgbClr val="F59E0B"/></a:accent4><a:accent5><a:srgbClr val="EC4899"/></a:accent5><a:accent6><a:srgbClr val="8B5CF6"/></a:accent6><a:hlink><a:srgbClr val="2563EB"/></a:hlink><a:folHlink><a:srgbClr val="7C3AED"/></a:folHlink></a:clrScheme><a:fontScheme name="SR"><a:majorFont><a:latin typeface="Calibri"/></a:majorFont><a:minorFont><a:latin typeface="Calibri"/></a:minorFont></a:fontScheme><a:fmtScheme name="SR"><a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:fillStyleLst><a:lnStyleLst><a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln><a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln><a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln></a:lnStyleLst><a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle><a:effectStyle><a:effectLst/></a:effectStyle><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst><a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:bgFillStyleLst></a:fmtScheme></a:themeElements></a:theme>'
    srel = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/></Relationships>'
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct); z.writestr("_rels/.rels", rrels); z.writestr("ppt/presentation.xml", pxml); z.writestr("ppt/_rels/presentation.xml.rels", prels)
        z.writestr("ppt/slideMasters/slideMaster1.xml", sm); z.writestr("ppt/slideMasters/_rels/slideMaster1.xml.rels", smr)
        z.writestr("ppt/slideLayouts/slideLayout1.xml", sl); z.writestr("ppt/slideLayouts/_rels/slideLayout1.xml.rels", slr); z.writestr("ppt/theme/theme1.xml", thm)
        for i, sx in enumerate(slides_xml, start=1):
            z.writestr(f"ppt/slides/slide{i}.xml", sx); z.writestr(f"ppt/slides/_rels/slide{i}.xml.rels", srel)
    return buf.getvalue(), theme_key


def _col_letter(n):
    s = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def build_xlsx_bytes(sheet_title, headers, rows):
    all_rows = [headers] + rows
    widths = [max([len(str(r[c] if c < len(r) else "")) for r in all_rows] + [10]) + 4 for c in range(len(headers))]
    cols_xml = "<cols>" + "".join(f'<col min="{i+1}" max="{i+1}" width="{min(42, w)}" customWidth="1"/>' for i, w in enumerate(widths)) + "</cols>"
    rows_xml = []
    for r_idx, row in enumerate(all_rows, start=1):
        cells = []
        style = ' s="1"' if r_idx == 1 else ' s="0"'
        for c_idx in range(len(headers)):
            val = row[c_idx] if c_idx < len(row) else ""
            ref = f"{_col_letter(c_idx+1)}{r_idx}"
            if r_idx > 1 and isinstance(val, (int, float)) and not isinstance(val, bool):
                cells.append(f'<c r="{ref}"{style}><v>{val}</v></c>')
            else:
                cells.append(f'<c r="{ref}"{style} t="inlineStr"><is><t>{_clean_xml(val)}</t></is></c>')
        rows_xml.append(f'<row r="{r_idx}">{"".join(cells)}</row>')
    sheet_xml = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">{cols_xml}<sheetData>{"".join(rows_xml)}</sheetData></worksheet>'
    styles_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font></fonts><fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF10A37F"/></patternFill></fill></fills><borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"/></cellXfs></styleSheet>'
    wb_xml = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="{_clean_xml(sheet_title[:28] or "Sheet1")}" sheetId="1" r:id="rId1"/></sheets></workbook>'
    wb_rels = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>'
    ct_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.worksheet+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>'
    root_rels = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>'
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct_xml); z.writestr("_rels/.rels", root_rels)
        z.writestr("xl/workbook.xml", wb_xml); z.writestr("xl/_rels/workbook.xml.rels", wb_rels)
        z.writestr("xl/styles.xml", styles_xml); z.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    return buf.getvalue()
