import datetime
import math
from vedic import CITIES

KAABA_LAT = 21.4225
KAABA_LON = 39.8262


def _fmt_time(hours_float):
    h_total = hours_float % 24.0
    hh = int(h_total)
    mm = int(round((h_total - hh) * 60))
    if mm == 60:
        hh = (hh + 1) % 24
        mm = 0
    ampm = "AM" if hh < 12 else "PM"
    h12 = hh % 12
    if h12 == 0:
        h12 = 12
    return f"{h12:02d}:{mm:02d} {ampm}"


def compute_qibla(city="Ahmedabad"):
    lat, lon = CITIES.get((city or "").strip().lower(), (23.02, 72.57))
    lat1, lon1 = math.radians(lat), math.radians(lon)
    lat2, lon2 = math.radians(KAABA_LAT), math.radians(KAABA_LON)
    dlon = lon2 - lon1
    y = math.sin(dlon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    deg = (math.degrees(math.atan2(y, x)) + 360.0) % 360.0
    dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    d_label = dirs[int((deg + 11.25) // 22.5) % 16]
    return {"city": city or "Ahmedabad", "lat": lat, "lon": lon, "degrees": round(deg, 1), "direction": d_label}


def render_qibla_svg(deg):
    return (
        '<svg viewBox="0 0 240 240" width="210" height="210" style="background:#071a14;border:2px solid #10b981;border-radius:50%;display:block;margin:8px auto;">'
        '<circle cx="120" cy="120" r="105" fill="none" stroke="#1e4d3b" stroke-width="2"/>'
        '<text x="120" y="24" text-anchor="middle" fill="#94a3b8" font-size="13" font-weight="bold">N</text>'
        '<text x="220" y="125" text-anchor="middle" fill="#94a3b8" font-size="13" font-weight="bold">E</text>'
        '<text x="120" y="230" text-anchor="middle" fill="#94a3b8" font-size="13" font-weight="bold">S</text>'
        '<text x="20" y="125" text-anchor="middle" fill="#94a3b8" font-size="13" font-weight="bold">W</text>'
        f'<g transform="rotate({deg} 120 120)">'
        '<polygon points="120,34 130,120 120,108 110,120" fill="#fbbf24"/>'
        '<polygon points="120,206 127,120 120,132 113,120" fill="#475569"/>'
        '<circle cx="120" cy="34" r="6" fill="#10b981"/>'
        '</g>'
        '<circle cx="120" cy="120" r="8" fill="#10b981"/>'
        '</svg>'
    )


def compute_prayer_times(city="Ahmedabad", date_str=None):
    lat, lon = CITIES.get((city or "").strip().lower(), (23.02, 72.57))
    if date_str:
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
    else:
        dt = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)

    y, m, d = dt.year, dt.month, dt.day
    if m <= 2:
        y -= 1
        m += 12
    a = y // 100
    b = 2 - a + a // 4
    jd = int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + b - 1524.5 + (12.0 - 5.5) / 24.0

    D = jd - 2451545.0
    g = math.radians((357.529 + 0.98560028 * D) % 360.0)
    q = (280.459 + 0.98564736 * D) % 360.0
    L = math.radians((q + 1.915 * math.sin(g) + 0.020 * math.sin(2 * g)) % 360.0)
    e = math.radians(23.439 - 0.00000036 * D)
    ra = (math.degrees(math.atan2(math.cos(e) * math.sin(L), math.cos(L))) / 15.0) % 24.0
    decl = math.asin(math.sin(e) * math.sin(L))
    eot = (q / 15.0) - ra
    if eot > 12:
        eot -= 24
    elif eot < -12:
        eot += 24

    tz = 5.5
    dhuhr = 12.0 + tz - (lon / 15.0) - eot
    lat_r = math.radians(lat)

    def ha_for_alt(alt_deg):
        val = (math.sin(math.radians(alt_deg)) - math.sin(lat_r) * math.sin(decl)) / (math.cos(lat_r) * math.cos(decl))
        val = max(-0.999, min(0.999, val))
        return math.degrees(math.acos(val)) / 15.0

    ha_sun = ha_for_alt(-0.833)
    ha_18 = ha_for_alt(-18.0)

    asr_shafi_alt = math.degrees(math.atan(1.0 / (1.0 + math.tan(abs(lat_r - decl)))))
    asr_hanafi_alt = math.degrees(math.atan(1.0 / (2.0 + math.tan(abs(lat_r - decl)))))

    fajr = dhuhr - ha_18
    sunrise = dhuhr - ha_sun
    asr_shafi = dhuhr + ha_for_alt(asr_shafi_alt)
    asr_hanafi = dhuhr + ha_for_alt(asr_hanafi_alt)
    maghrib = dhuhr + ha_sun
    isha = dhuhr + ha_18

    return {
        "city": city or "Ahmedabad",
        "date": dt.strftime("%d %b %Y"),
        "sehri_ends": _fmt_time(fajr - 10.0 / 60.0),
        "fajr": _fmt_time(fajr),
        "sunrise": _fmt_time(sunrise),
        "dhuhr": _fmt_time(dhuhr),
        "asr_shafi": _fmt_time(asr_shafi),
        "asr_hanafi": _fmt_time(asr_hanafi),
        "maghrib_iftar": _fmt_time(maghrib),
        "isha": _fmt_time(isha),
    }


def compute_zakat(cash=0, gold_val=0, silver_val=0, business_val=0, debt=0, nisab=65000):
    total = max(0.0, float(cash) + float(gold_val) + float(silver_val) + float(business_val) - float(debt))
    eligible = total >= float(nisab)
    zakat = round(total * 0.025, 2) if eligible else 0.0
    return {"net_wealth": round(total, 2), "nisab": float(nisab), "eligible": eligible, "zakat_due": zakat}
