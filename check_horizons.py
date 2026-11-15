import json
import urllib.parse
import urllib.request

from engine.geometry import analyze_site, load_sites

START, STOP = "2029-07-01", "2029-07-02"


def horizons_elevation(body, lon, lat, t0, t1):
    lon = lon - 360 if lon > 180 else lon
    params = {
        "format": "json",
        "COMMAND": f"'{body}'",
        "OBJ_DATA": "'NO'",
        "MAKE_EPHEM": "'YES'",
        "EPHEM_TYPE": "'OBSERVER'",
        "CENTER": "'coord@301'",
        "COORD_TYPE": "'GEODETIC'",
        "SITE_COORD": f"'{lon},{lat},0'",
        "START_TIME": f"'{t0} 00:00'",
        "STOP_TIME": f"'{t1} 00:00'",
        "STEP_SIZE": "'60 min'",
        "QUANTITIES": "'4'",
        "ANG_FORMAT": "'DEG'",
        "CSV_FORMAT": "'YES'",
    }
    url = "https://ssd.jpl.nasa.gov/api/horizons.api?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=60) as resp:
        text = json.load(resp)["result"]
    if "$$SOE" not in text:
        raise RuntimeError(text[:600])
    rows = text.split("$$SOE")[1].split("$$EOE")[0].strip().splitlines()
    out = []
    for row in rows:
        nums = []
        for f in row.split(",")[1:]:
            try:
                nums.append(float(f.strip()))
            except ValueError:
                pass
        out.append(nums[-1])  # elevation is the last number on the row
    return out


for s in load_sites():
    r = analyze_site(s["id"], START, STOP, 60)
    print(s["name"], "first engine times:", r["time"][:2])
    for body, key in (("10", "sun_elevation_deg"), ("399", "earth_elevation_deg")):
        ref = horizons_elevation(body, s["longitude"], s["latitude"], START, STOP)
        ours = r[key]
        k = min(len(ref), len(ours))
        diffs = [abs(a - b) for a, b in zip(ours[:k], ref[:k])]
        label = "Sun  " if body == "10" else "Earth"
        print(f"  {label} max diff {max(diffs):.3f} deg, mean {sum(diffs) / k:.3f} deg (n={k})")
        print("    ours   ", [round(x, 2) for x in ours[:4]])
        print("    horizons", [round(x, 2) for x in ref[:4]])