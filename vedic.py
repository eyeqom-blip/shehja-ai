import datetime
import math

RASHIS = [
    ("Mesha (Aries)", "मेष", "Mangal"), ("Vrishabha (Taurus)", "वृषभ", "Shukra"),
    ("Mithuna (Gemini)", "मिथुन", "Budh"), ("Karka (Cancer)", "कर्क", "Chandra"),
    ("Simha (Leo)", "सिंह", "Surya"), ("Kanya (Virgo)", "कन्या", "Budh"),
    ("Tula (Libra)", "तुला", "Shukra"), ("Vrishchika (Scorpio)", "वृश्चिक", "Mangal"),
    ("Dhanu (Sagittarius)", "धनु", "Guru"), ("Makara (Capricorn)", "मकर", "Shani"),
    ("Kumbha (Aquarius)", "कुंभ", "Shani"), ("Meena (Pisces)", "मीन", "Guru"),
]

NAKSHATRAS = [
    ("Ashwini", "Ketu", ["Chu", "Che", "Cho", "La"]), ("Bharani", "Shukra", ["Li", "Lu", "Le", "Lo"]),
    ("Krittika", "Surya", ["A", "Ee", "U", "Ea"]), ("Rohini", "Chandra", ["O", "Va", "Vi", "Vu"]),
    ("Mrigashira", "Mangal", ["Ve", "Vo", "Ka", "Ki"]), ("Ardra", "Rahu", ["Ku", "Gha", "Ng", "Chh"]),
    ("Punarvasu", "Guru", ["Ke", "Ko", "Ha", "Hi"]), ("Pushya", "Shani", ["Hu", "He", "Ho", "Da"]),
    ("Ashlesha", "Budh", ["Di", "Du", "De", "Do"]), ("Magha", "Ketu", ["Ma", "Mi", "Mu", "Me"]),
    ("Purva Phalguni", "Shukra", ["Mo", "Ta", "Ti", "Tu"]), ("Uttara Phalguni", "Surya", ["Te", "To", "Pa", "Pi"]),
    ("Hasta", "Chandra", ["Pu", "Sha", "Na", "Tha"]), ("Chitra", "Mangal", ["Pe", "Po", "Ra", "Ri"]),
    ("Swati", "Rahu", ["Ru", "Re", "Ro", "Ta"]), ("Vishakha", "Guru", ["Ti", "Tu", "Te", "To"]),
    ("Anuradha", "Shani", ["Na", "Ni", "Nu", "Ne"]), ("Jyeshtha", "Budh", ["No", "Ya", "Yi", "Yu"]),
    ("Mula", "Ketu", ["Ye", "Yo", "Bha", "Bhi"]), ("Purva Ashadha", "Shukra", ["Bhu", "Dha", "Pha", "Dha"]),
    ("Uttara Ashadha", "Surya", ["Bhe", "Bho", "Ja", "Ji"]), ("Shravana", "Chandra", ["Ju", "Je", "Jo", "Gha"]),
    ("Dhanishta", "Mangal", ["Ga", "Gi", "Gu", "Ge"]), ("Shatabhisha", "Rahu", ["Go", "Sa", "Si", "Su"]),
    ("Purva Bhadrapada", "Guru", ["Se", "So", "Da", "Di"]), ("Uttara Bhadrapada", "Shani", ["Du", "Tha", "Jha", "Da"]),
    ("Revati", "Budh", ["De", "Do", "Cha", "Chi"]),
]

TITHIS = [
    "Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami",
    "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
    "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Purnima",
    "Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami",
    "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
    "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Amavasya",
]

DASHA_YEARS = {"Ketu": 7, "Shukra": 20, "Surya": 6, "Chandra": 10, "Mangal": 7, "Rahu": 18, "Guru": 16, "Shani": 19, "Budh": 17}
DASHA_ORDER = ["Ketu", "Shukra", "Surya", "Chandra", "Mangal", "Rahu", "Guru", "Shani", "Budh"]
VAAR_NAMES = ["Somvaar (Monday)", "Mangalvaar (Tuesday)", "Budhvaar (Wednesday)", "Guruvaar (Thursday)", "Shukravaar (Friday)", "Shanivaar (Saturday)", "Ravivaar (Sunday)"]
RAHU_KAAL = ["07:30 AM - 09:00 AM", "03:00 PM - 04:30 PM", "12:00 PM - 01:30 PM", "01:30 PM - 03:00 PM", "10:30 AM - 12:00 PM", "09:00 AM - 10:30 AM", "04:30 PM - 06:00 PM"]

CITIES = {
    "ahmedabad": (23.02, 72.57), "surat": (21.17, 72.83), "vadodara": (22.31, 73.18), "rajkot": (22.30, 70.80),
    "mumbai": (19.08, 72.88), "pune": (18.52, 73.86), "nagpur": (21.15, 79.09), "nashik": (19.99, 73.79),
    "delhi": (28.61, 77.21), "new delhi": (28.61, 77.21), "noida": (28.54, 77.39), "gurgaon": (28.46, 77.03),
    "jaipur": (26.91, 75.79), "udaipur": (24.59, 73.71), "jodhpur": (26.24, 73.02), "kota": (25.21, 75.86),
    "lucknow": (26.85, 80.95), "kanpur": (26.45, 80.33), "varanasi": (25.32, 82.97), "prayagraj": (25.44, 81.85),
    "agra": (27.18, 78.01), "mathura": (27.49, 77.67), "ayodhya": (26.80, 82.20), "haridwar": (29.95, 78.16),
    "dehradun": (30.32, 78.03), "patna": (25.59, 85.14), "ranchi": (23.34, 85.31), "kolkata": (22.57, 88.36),
    "bhopal": (23.26, 77.41), "indore": (22.72, 75.86), "ujjain": (23.18, 75.78), "raipur": (21.25, 81.63),
    "chandigarh": (30.73, 76.78), "amritsar": (31.63, 74.87), "ludhiana": (30.90, 75.86), "jammu": (32.73, 74.86),
    "bengaluru": (12.97, 77.59), "bangalore": (12.97, 77.59), "hyderabad": (17.39, 78.49), "chennai": (13.08, 80.27),
    "kochi": (9.93, 76.27), "bhubaneswar": (20.30, 85.82), "guwahati": (26.14, 91.74), "bhavnagar": (21.76, 72.15),
    "jamnagar": (22.47, 70.06), "gandhinagar": (23.22, 72.64), "dubai": (25.20, 55.27), "london": (51.51, -0.13),
    "new york": (40.71, -74.01), "toronto": (43.65, -79.38), "singapore": (1.35, 103.82),
}

CHALDEAN = {"A":1,"I":1,"J":1,"Q":1,"Y":1,"B":2,"K":2,"R":2,"C":3,"G":3,"L":3,"S":3,"D":4,"M":4,"T":4,"E":5,"H":5,"N":5,"X":5,"U":6,"V":6,"W":6,"O":7,"Z":7,"F":8,"P":8}


def _reduce_num(n):
    while n > 9:
        n = sum(int(d) for d in str(n))
    return n


def _name_num(name):
    s = sum(CHALDEAN.get(ch.upper(), 0) for ch in (name or ""))
    return _reduce_num(s) if s > 0 else 0


def _julian_day(dt_ut):
    y, m = dt_ut.year, dt_ut.month
    d = dt_ut.day + (dt_ut.hour + dt_ut.minute / 60.0 + dt_ut.second / 3600.0) / 24.0
    if m <= 2:
        y -= 1
        m += 12
    a = y // 100
    b = 2 - a + (a // 4)
    return int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + b - 1524.5


def _lahiri(jd):
    return (23.85472 + ((jd - 2451545.0) / 365.2421988) * 0.013969) % 360.0


def _sun_lon_trop(jd):
    t = (jd - 2451545.0) / 36525.0
    l0 = (280.46646 + 36000.76983 * t + 0.0003032 * t * t) % 360.0
    m = math.radians((357.52911 + 35999.05029 * t - 0.0001537 * t * t) % 360.0)
    c = (1.914602 - 0.004817 * t) * math.sin(m) + 0.019993 * math.sin(2 * m) + 0.000289 * math.sin(3 * m)
    return (l0 + c) % 360.0


def _moon_lon_trop(jd):
    t = (jd - 2451545.0) / 36525.0
    lp = (218.3164477 + 481267.88123421 * t - 0.0015786 * t * t) % 360.0
    d = math.radians((297.8501921 + 445267.1114034 * t) % 360.0)
    m = math.radians((357.5291092 + 35999.0502909 * t) % 360.0)
    mp = math.radians((134.9633964 + 477198.8675055 * t) % 360.0)
    f = math.radians((93.2720950 + 483202.0175233 * t) % 360.0)
    corr = (
        6.288774 * math.sin(mp)
        + 1.274027 * math.sin(2 * d - mp)
        + 0.658314 * math.sin(2 * d)
        + 0.213618 * math.sin(2 * mp)
        - 0.185116 * math.sin(m)
        - 0.114332 * math.sin(2 * f)
        + 0.058793 * math.sin(2 * d - 2 * mp)
        + 0.057066 * math.sin(2 * d - m - mp)
    )
    return (lp + corr) % 360.0


def _planet_geocentric_trop(jd, elem):
    d = jd - 2451545.0
    def helio(N, i, w, a, e, M0, n):
        M = math.radians((M0 + n * d) % 360.0)
        E = M + e * math.sin(M) * (1.0 + e * math.cos(M))
        xv = a * (math.cos(E) - e)
        yv = a * math.sqrt(1 - e * e) * math.sin(E)
        v = math.atan2(yv, xv)
        r = math.hypot(xv, yv)
        Nr, wr, ir = math.radians(N), math.radians(w), math.radians(i)
        xh = r * (math.cos(Nr) * math.cos(v + wr) - math.sin(Nr) * math.sin(v + wr) * math.cos(ir))
        yh = r * (math.sin(Nr) * math.cos(v + wr) + math.cos(Nr) * math.sin(v + wr) * math.cos(ir))
        return xh, yh

    xe, ye = helio(0.0, 0.0, 282.9404, 1.000000, 0.016709, 356.0470, 0.9856002585)
    xp, yp = helio(*elem)
    return math.degrees(math.atan2(yp - ye, xp - xe)) % 360.0


PLANET_ELEMS = {
    "Budh": (48.3313, 7.0047, 29.1241, 0.387098, 0.205635, 168.6562, 4.0923344368),
    "Shukra": (76.6799, 3.3946, 54.8910, 0.723330, 0.006773, 48.0052, 1.6021302244),
    "Mangal": (49.5574, 1.8497, 286.5016, 1.523688, 0.093405, 18.6021, 0.5240207766),
    "Guru": (100.4542, 1.3030, 273.8777, 5.20256, 0.048498, 19.8950, 0.0830853001),
    "Shani": (113.6634, 2.4886, 339.3939, 9.55475, 0.055546, 316.9670, 0.0334442282),
}


def _lagna_sidereal(jd, lat, lon, ayan):
    t = (jd - 2451545.0) / 36525.0
    gmst = (280.46061837 + 360.98564736629 * (jd - 2451545.0) + 0.000387933 * t * t) % 360.0
    lst = math.radians((gmst + lon) % 360.0)
    eps = math.radians(23.439291 - 0.0130042 * t)
    lat_r = math.radians(lat)
    y = -math.cos(lst)
    x = math.sin(eps) * math.tan(lat_r) + math.cos(eps) * math.sin(lst)
    asc = math.degrees(math.atan2(y, x)) % 360.0
    return (asc - ayan) % 360.0


def compute_kundli(dob, tob="12:00", city="Ahmedabad", name="", mother_name="", dharma="Sanatan / Hindu"):
    dt_local = datetime.datetime.strptime(f"{dob} {tob or '12:00'}", "%Y-%m-%d %H:%M")
    dt_ut = dt_local - datetime.timedelta(hours=5, minutes=30)
    jd = _julian_day(dt_ut)
    ayan = _lahiri(jd)
    lat, lon = CITIES.get((city or "").strip().lower(), (23.02, 72.57))

    sun_sid = (_sun_lon_trop(jd) - ayan) % 360.0
    moon_sid = (_moon_lon_trop(jd) - ayan) % 360.0
    lagna_sid = _lagna_sidereal(jd, lat, lon, ayan)
    rahu_sid = (125.04452 - 0.05295377 * (jd - 2451545.0) - ayan) % 360.0
    ketu_sid = (rahu_sid + 180.0) % 360.0

    planets = {"Surya": sun_sid, "Chandra": moon_sid, "Rahu": rahu_sid, "Ketu": ketu_sid}
    for pname, el in PLANET_ELEMS.items():
        planets[pname] = (_planet_geocentric_trop(jd, el) - ayan) % 360.0

    lagna_rashi_idx = int(lagna_sid // 30)
    moon_rashi_idx = int(moon_sid // 30)
    sun_rashi_idx = int(sun_sid // 30)

    nak_span = 360.0 / 27.0
    nak_idx = int(moon_sid // nak_span)
    nak_rem = (moon_sid % nak_span) / nak_span
    pada = int(nak_rem * 4) + 1
    nak_name, nak_lord, syllables = NAKSHATRAS[nak_idx]

    tithi_idx = int(((moon_sid - sun_sid) % 360.0) // 12.0)
    paksha = "Shukla Paksha" if tithi_idx < 15 else "Krishna Paksha"
    tithi_name = f"{paksha} {TITHIS[tithi_idx]}"

    houses = {i: [] for i in range(1, 13)}
    planet_houses = {}
    short = {"Surya":"Su","Chandra":"Mo","Mangal":"Ma","Budh":"Me","Guru":"Ju","Shukra":"Ve","Shani":"Sa","Rahu":"Ra","Ketu":"Ke"}
    for pname, deg in planets.items():
        r_idx = int(deg // 30)
        h_num = ((r_idx - lagna_rashi_idx) % 12) + 1
        houses[h_num].append(short[pname])
        planet_houses[pname] = {"house": h_num, "rashi": RASHIS[r_idx][0], "deg": round(deg % 30, 1)}

    mangal_h = planet_houses["Mangal"]["house"]
    is_manglik = mangal_h in (1, 2, 4, 7, 8, 12)

    # Current Saturn Sade Sati check (current UT)
    now_jd = _julian_day(datetime.datetime.utcnow())
    now_shani_rashi = int(((_planet_geocentric_trop(now_jd, PLANET_ELEMS["Shani"]) - _lahiri(now_jd)) % 360.0) // 30)
    shani_diff = (now_shani_rashi - moon_rashi_idx) % 12
    sade_sati = "Active (Shani Sade Sati)" if shani_diff in (11, 0, 1) else ("Dhaiya" if shani_diff in (3, 7) else "Nahi (Clear)")

    # Vimshottari Mahadasha timeline
    bal_years = (1.0 - nak_rem) * DASHA_YEARS[nak_lord]
    d_start = DASHA_ORDER.index(nak_lord)
    dashas = []
    cur_yr = dt_local.year + (dt_local.timetuple().tm_yday / 365.25)
    for k in range(9):
        lord = DASHA_ORDER[(d_start + k) % 9]
        yrs = bal_years if k == 0 else DASHA_YEARS[lord]
        end_yr = cur_yr + yrs
        dashas.append({"lord": lord, "from": round(cur_yr, 1), "to": round(end_yr, 1)})
        cur_yr = end_yr
    now_yr = datetime.datetime.utcnow().year + 0.87
    cur_dasha = next((d for d in dashas if d["from"] <= now_yr <= d["to"]), dashas[0])

    # Numerology
    mulank = _reduce_num(dt_local.day)
    bhagyank = _reduce_num(sum(int(c) for c in dob if c.isdigit()))
    naam_ank = _name_num(name)
    matri_ank = _name_num(mother_name)

    return {
        "name": name or "Jatak",
        "mother_name": mother_name,
        "dharma": dharma,
        "dob": dob,
        "tob": tob,
        "city": city or "Ahmedabad",
        "vaar": VAAR_NAMES[dt_local.weekday()],
        "tithi": tithi_name,
        "lagna": RASHIS[lagna_rashi_idx][0],
        "lagna_idx": lagna_rashi_idx,
        "moon_rashi": RASHIS[moon_rashi_idx][0],
        "moon_idx": moon_rashi_idx,
        "sun_rashi": RASHIS[sun_rashi_idx][0],
        "nakshatra": f"{nak_name} (Pada {pada})",
        "nak_idx": nak_idx,
        "nak_akshar": syllables[pada - 1],
        "nak_lord": nak_lord,
        "cur_dasha": f"{cur_dasha['lord']} Mahadasha ({int(cur_dasha['from'])}-{int(cur_dasha['to'])})",
        "manglik": f"Haan (Mangal {mangal_h}ve bhav mein)" if is_manglik else f"Nahi (Mangal {mangal_h}ve bhav mein)",
        "is_manglik": is_manglik,
        "sade_sati": sade_sati,
        "mulank": mulank,
        "bhagyank": bhagyank,
        "naam_ank": naam_ank,
        "matri_ank": matri_ank,
        "houses": houses,
        "planets": planet_houses,
    }


def compute_gun_milan(k1, k2):
    r1, r2 = k1["moon_idx"], k2["moon_idx"]
    n1, n2 = k1["nak_idx"], k2["nak_idx"]
    score = 0
    # 1. Varna (1)
    v1, v2 = r1 % 4, r2 % 4
    varna = 1 if v1 >= v2 else 0
    # 2. Vashya (2)
    vashya = 2 if r1 == r2 else (1 if abs(r1 - r2) in (2, 4, 8, 10) else 0)
    # 3. Tara (3)
    tara_d = ((n2 - n1) % 27) % 9
    tara = 3 if tara_d in (1, 3, 5, 7, 8) else 1.5
    # 4. Yoni (4)
    yoni = 4 if (n1 % 14) == (n2 % 14) else (2 if abs((n1 % 14) - (n2 % 14)) < 5 else 1)
    # 5. Maitri (5)
    l1, l2 = RASHIS[r1][2], RASHIS[r2][2]
    maitri = 5 if l1 == l2 else 3
    # 6. Gana (6)
    g1, g2 = n1 % 3, n2 % 3
    gana = 6 if g1 == g2 else (3 if abs(g1 - g2) == 1 else 1)
    # 7. Bhakoot (7)
    b_diff = (r2 - r1) % 12
    bhakoot = 0 if b_diff in (1, 5, 7, 11) else 7
    # 8. Nadi (8)
    na1, na2 = n1 % 3, n2 % 3
    nadi = 0 if na1 == na2 else 8
    total = varna + vashya + tara + yoni + maitri + gana + bhakoot + nadi
    return {"total": total, "varna": varna, "vashya": vashya, "tara": tara, "yoni": yoni, "maitri": maitri, "gana": gana, "bhakoot": bhakoot, "nadi": nadi}


def get_today_panchang():
    ist = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
    k = compute_kundli(ist.strftime("%Y-%m-%d"), ist.strftime("%H:%M"), "Delhi")
    wd = ist.weekday()
    return {
        "date": ist.strftime("%d %b %Y"),
        "vaar": VAAR_NAMES[wd],
        "tithi": k["tithi"],
        "nakshatra": k["nakshatra"],
        "moon_rashi": k["moon_rashi"],
        "rahu_kaal": RAHU_KAAL[wd],
        "abhijit": "11:45 AM - 12:33 PM",
    }


def render_kundli_svg(k):
    l_idx = k["lagna_idx"]
    # House label center coordinates in 320x320 North Indian Diamond
    pos = {
        1:(160,82), 2:(85,38), 3:(38,84), 4:(85,160), 5:(38,236), 6:(85,282),
        7:(160,238), 8:(235,282), 9:(282,236), 10:(235,160), 11:(282,84), 12:(235,38),
    }
    texts = []
    for h in range(1, 13):
        x, y = pos[h]
        r_num = ((l_idx + h - 1) % 12) + 1
        pls = " ".join(k["houses"][h])
        texts.append(f'<text x="{x}" y="{y-6}" text-anchor="middle" fill="#fbbf24" font-size="10" font-weight="bold">{r_num}</text>')
        if pls:
            texts.append(f'<text x="{x}" y="{y+8}" text-anchor="middle" fill="#fef3c7" font-size="10" font-weight="bold">{pls}</text>')
    return (
        '<svg viewBox="0 0 320 320" width="260" height="260" style="background:#1c1208;border:2px solid #d97706;border-radius:10px;display:block;margin:8px auto;">'
        '<rect x="10" y="10" width="300" height="300" fill="none" stroke="#f59e0b" stroke-width="2"/>'
        '<line x1="10" y1="10" x2="310" y2="310" stroke="#b45309" stroke-width="1.5"/>'
        '<line x1="310" y1="10" x2="10" y2="310" stroke="#b45309" stroke-width="1.5"/>'
        '<polygon points="160,10 310,160 160,310 10,160" fill="none" stroke="#f59e0b" stroke-width="1.8"/>'
        + "".join(texts) + "</svg>"
    )


NUM_RULERS = {
    1: ("Surya (Sun)", "Sunday", "Gold / Orange", [1, 2, 3, 5, 9], [8]),
    2: ("Chandra (Moon)", "Monday", "White / Cream", [1, 2, 3, 5], [4, 8, 9]),
    3: ("Guru (Jupiter)", "Thursday", "Yellow / Saffron", [1, 2, 3, 5, 9], [6]),
    4: ("Rahu", "Saturday / Sunday", "Electric Blue / Grey", [1, 5, 6, 7], [2, 4, 8, 9]),
    5: ("Budh (Mercury)", "Wednesday", "Green / Emerald", [1, 2, 3, 5, 6], []),
    6: ("Shukra (Venus)", "Friday", "White / Pink / Light Blue", [1, 5, 6, 7], [3]),
    7: ("Ketu", "Monday / Wednesday", "Light Yellow / White", [1, 4, 5, 6], [2, 8]),
    8: ("Shani (Saturn)", "Saturday", "Dark Blue / Black", [3, 5, 6, 7], [1, 2, 4, 8, 9]),
    9: ("Mangal (Mars)", "Tuesday", "Red / Coral", [1, 2, 3, 5], [4, 8]),
}

LOSHU_PLANES = [
    ("Golden Rajyog (4-5-6)", (4, 5, 6)),
    ("Silver Rajyog (2-5-8)", (2, 5, 8)),
    ("Mental Plane (4-9-2)", (4, 9, 2)),
    ("Emotional Plane (3-5-7)", (3, 5, 7)),
    ("Practical Plane (8-1-6)", (8, 1, 6)),
    ("Thought Plane (4-3-8)", (4, 3, 8)),
    ("Willpower Plane (9-5-1)", (9, 5, 1)),
    ("Action Plane (2-7-6)", (2, 7, 6)),
]

TAROT_DECK = [
    ("0. The Fool", "Nayi shuruaat, himmat aur bina dar ke aage badhne ka sanket."),
    ("I. The Magician", "Aapke paas saare hunar aur resources maujood hain — bas action lene ka waqt hai."),
    ("II. The High Priestess", "Apne dil ki aawaz (intuition) par bharosa karein; abhi sab kuch khul kar samne aayega."),
    ("III. The Empress", "Samriddhi, family khushhali, creativity aur growth ka shubh samay."),
    ("IV. The Emperor", "Discipline, leadership aur majboot faislon se sthirta aayegi."),
    ("V. The Hierophant", "Parampara, guru ya bade-buzurgon ki salah se sahi raasta milega."),
    ("VI. The Lovers", "Rishton mein samanjasya, dil se liya gaya sahi faisla aur prem."),
    ("VII. The Chariot", "Mehnat aur focus se rukawaton par jeet aur safalta."),
    ("VIII. Strength", "Shant mann, sabr aur andarooni himmat se har mushkil aasaan hogi."),
    ("IX. The Hermit", "Thoda ruk kar khud par dhyaan dene aur gehri soch se sahi jawab paane ka samay."),
    ("X. Wheel of Fortune", "Kismat ka pahiya ghoom raha hai — accha badlav aur naye avsar aa rahe hain."),
    ("XI. Justice", "Sachai aur imaandari ka phal milega; kanooni ya zaroori faisle aapke haq mein honge."),
    ("XII. The Hanged Man", "Naye nazariye se dekhein; thoda sabr rakhna abhi sabse behtar hai."),
    ("XIII. Transformation", "Purani chinta khatam hokar naye behtar daur ki shuruaat ho rahi hai."),
    ("XIV. Temperance", "Balance aur shanti banaye rakhein — jaldbazi se bachein, kaam banega."),
    ("XV. The Devil (Attachment)", "Kisi buri aadat, stress ya galat attachment se bahar nikalne ki zaroorat hai."),
    ("XVI. The Tower", "Achanak bada badlav purani kamzor neev hata kar nayi majboot shuruaat layega."),
    ("XVII. The Star", "Umeed, healing aur manokaamna poori hone ka behad shubh sanket."),
    ("XVIII. The Moon", "Mann ka bharam ya confusion door hoga; sach jaan kar hi kadam badhayein."),
    ("XIX. The Sun", "Khushiyan, safalta, chamak aur har kaam mein roshni aur jeet!"),
    ("XX. Judgement", "Pichle karmon ka accha phal aur zindagi mein naya uday."),
    ("XXI. The World", "Ek bada safar ya lakshya safalta se poora hone wala hai!"),
    ("Ace of Pentacles", "Naye dhan, job, business ya property ka shubh aagaman."),
    ("Ace of Cups", "Naya pyaar, emotional khushi aur dil ko sukoon dene wali khabar."),
    ("Ace of Wands", "Naya idea, josh aur shandar career/creative shuruaat."),
    ("Ace of Swords", "Tez dimaag, clear sachai aur sahi faisle se bada breakthrough."),
    ("Six of Wands", "Samman, tareef aur mehnat ke baad public jeet!"),
    ("Ten of Pentacles", "Parivaar ki barkat, sthirta aur lambe samay ki aarthik suraksha."),
]


def compute_numerology(dob, name="", mother_name="", gender="Male", extra_num="", prashna_num=""):
    digits = [int(c) for c in (dob or "2000-01-01") if c.isdigit()]
    parts = (dob or "2000-01-01").split("-")
    year = int(parts[0]) if len(parts) >= 1 and parts[0].isdigit() else 2000
    day = int(parts[2]) if len(parts) >= 3 and parts[2].isdigit() else 1

    mulank = _reduce_num(day)
    bhagyank = _reduce_num(sum(digits))

    yr_sum = _reduce_num(sum(int(c) for c in str(year)))
    if (gender or "Male").lower().startswith("f"):
        kua = _reduce_num(4 + yr_sum)
        if kua == 5:
            kua = 8
    else:
        kua = _reduce_num(11 - yr_sum)
        if kua == 5:
            kua = 2

    chaldean_raw = sum(CHALDEAN.get(ch.upper(), 0) for ch in (name or ""))
    naam_ank = _reduce_num(chaldean_raw) if chaldean_raw > 0 else 0
    matri_ank = _name_num(mother_name)

    counts = {i: 0 for i in range(1, 10)}
    for d in digits:
        if d > 0:
            counts[d] += 1
    if day > 9 or day not in digits:
        counts[mulank] += 1
    counts[bhagyank] += 1

    active_planes = [pname for pname, tpl in LOSHU_PLANES if all(counts[x] > 0 for x in tpl)]
    missing = [i for i in range(1, 10) if counts[i] == 0]
    strong = [f"{i} ({counts[i]}x)" for i in range(1, 10) if counts[i] >= 2]

    ruler, lucky_day, lucky_color, friends, enemies = NUM_RULERS[mulank]
    _, _, _, b_friends, _ = NUM_RULERS[bhagyank]
    common_lucky = sorted(list(set(friends) & set(b_friends))) or friends

    extra_digits = [int(c) for c in (extra_num or "") if c.isdigit()]
    extra_red = _reduce_num(sum(extra_digits)) if extra_digits else 0
    extra_status = ""
    if extra_red:
        if extra_red in common_lucky or extra_red in (mulank, bhagyank):
            extra_status = f"Shubh & Lucky ✅ (Total {extra_red} aapke Mulank {mulank} & Bhagyank {bhagyank} ka mitr hai)"
        elif extra_red in enemies:
            extra_status = f"Savdhani ⚠️ (Total {extra_red} aapke Mulank {mulank} se thoda virodhi hai)"
        else:
            extra_status = f"Samanya / Neutral 🙂 (Total {extra_red})"

    p_num = int(prashna_num) if str(prashna_num).isdigit() else 0
    p_red = _reduce_num(p_num) if p_num > 0 else 0

    return {
        "name": name or "Jatak",
        "mother_name": mother_name,
        "dob": dob,
        "gender": gender,
        "mulank": mulank,
        "bhagyank": bhagyank,
        "kua": kua,
        "naam_ank": naam_ank,
        "chaldean_raw": chaldean_raw,
        "matri_ank": matri_ank,
        "ruler": ruler,
        "lucky_day": lucky_day,
        "lucky_color": lucky_color,
        "lucky_numbers": common_lucky,
        "counts": counts,
        "active_planes": active_planes,
        "missing": missing,
        "strong": strong,
        "extra_num": extra_num,
        "extra_red": extra_red,
        "extra_status": extra_status,
        "prashna_num": p_num,
        "prashna_red": p_red,
    }


def render_loshu_svg(counts):
    grid = [[4, 9, 2], [3, 5, 7], [8, 1, 6]]
    cells = []
    for r in range(3):
        for c in range(3):
            num = grid[r][c]
            cnt = counts.get(num, 0)
            x, y = 10 + c * 80, 10 + r * 80
            fill = "#1e293b" if cnt > 0 else "#0f172a"
            stroke = "#f59e0b" if cnt >= 2 else ("#10b981" if cnt == 1 else "#334155")
            txt = str(num) * min(cnt, 4) if cnt > 0 else "--"
            tcol = "#fbbf24" if cnt >= 2 else ("#34d399" if cnt == 1 else "#64748b")
            cells.append(f'<rect x="{x}" y="{y}" width="74" height="74" rx="10" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
            cells.append(f'<text x="{x+37}" y="{y+44}" text-anchor="middle" fill="{tcol}" font-size="22" font-weight="bold">{txt}</text>')
    return '<svg viewBox="0 0 260 260" width="210" height="210" style="background:#090d16;border:2px solid #f59e0b;border-radius:12px;display:block;margin:8px auto;">' + "".join(cells) + "</svg>"
