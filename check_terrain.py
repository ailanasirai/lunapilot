"""
LunaPilot terrain check (experimental, branch terrain-lola).

For each site that lies inside the LOLA DEM:
  1. sanity checks (map position, height range, is the site on high ground?)
  2. horizon profile (0-359 degrees) from the LOLA heights
  3. Sun and Earth visibility over a month: flat horizon vs LOLA horizon
Writes data/horizons_lola.json (small derived file, safe to commit).

Run from the project root:  python check_terrain.py
"""
import json
import math
from pathlib import Path

import numpy as np

from engine import terrain as T
from engine.geometry import analyze_site, load_sites

LBL = Path("data/terrain/LDEM_875S_20M.LBL")
OUT_JSON = Path("data/horizons_lola.json")
MAX_DISTANCE_M = 30000.0
OBSERVER_HEIGHT_M = 0.0  # same as the engine (elevation_m=0)
START, END = "2029-07-01", "2029-07-31"
STEP_MIN = 30


def site_sanity(site, win):
    """Prints checks that catch a wrong map orientation or wrong height scale."""
    dem = win["dem"]
    r0, c0 = win["row0"], win["col0"]
    res = win["res_m"]

    colat = math.radians(90.0 - abs(site["latitude"]))
    expected_rho = 2 * T.MOON_RADIUS_M * math.tan(colat / 2)
    rho = math.hypot(win["x"], win["y"])
    print(f"  map distance from pole: {rho:,.1f} m (expected {expected_rho:,.1f} m)")
    print(f"  DEM window heights: {float(np.nanmin(dem)):,.0f} to {float(np.nanmax(dem)):,.0f} m"
          f"   height at site: {win['site_height_m']:,.1f} m")

    # how high is the site compared with its 3 km neighbourhood?
    rad_px = int(3000 / res)
    ri, ci = int(round(r0)), int(round(c0))
    sub = dem[ri - rad_px: ri + rad_px + 1, ci - rad_px: ci + rad_px + 1]
    yy, xx = np.mgrid[-rad_px: rad_px + 1, -rad_px: rad_px + 1]
    ring = sub[(yy**2 + xx**2) <= rad_px**2]
    pct = 100.0 * float((ring < win["site_height_m"]).mean())
    print(f"  site is higher than {pct:.0f}% of the terrain within 3 km")


def summarize_site(site, win, series):
    """Horizon + flat-vs-terrain comparison. `series` holds the engine output."""
    az, hz = T.horizon_profile(
        win["dem"], win["res_m"], win["row0"], win["col0"],
        win["north_rc"], win["east_rc"],
        max_distance_m=MAX_DISTANCE_M, observer_height_m=OBSERVER_HEIGHT_M,
    )
    print(f"  horizon: max {hz.max():.2f} deg at azimuth {az[hz.argmax()]:.0f}, "
          f"mean {hz.mean():.2f}, min {hz.min():.2f}")
    print("  azimuth  horizon(deg): " + "  ".join(
        f"{int(a)}:{hz[int(a)]:.2f}" for a in range(0, 360, 45)))

    sun = np.array(series["sun_elevation_deg"])
    earth = np.array(series["earth_elevation_deg"])
    sun_az = np.array(series["sun_azimuth_deg"])
    earth_az = np.array(series["earth_azimuth_deg"])

    flat_sun = 100.0 * float((sun > 0).mean())
    flat_earth = 100.0 * float((earth > 0).mean())
    ter_sun = 100.0 * float((sun > T.horizon_at(sun_az, az, hz)).mean())
    ter_earth = 100.0 * float((earth > T.horizon_at(earth_az, az, hz)).mean())
    eng = series["metrics"]
    print(f"  engine check (flat): sunlit {100*eng['sunlit_fraction']:.1f}% "
          f"vs ours {flat_sun:.1f}%   earth {100*eng['earth_visible_fraction']:.1f}% vs ours {flat_earth:.1f}%")
    print(f"  {START} to {END}")
    print(f"    Sunlit        flat {flat_sun:6.1f}%   LOLA horizon {ter_sun:6.1f}%")
    print(f"    Earth visible flat {flat_earth:6.1f}%   LOLA horizon {ter_earth:6.1f}%")
    return az, hz


def main():
    if not LBL.exists():
        raise SystemExit(f"DEM label not found: {LBL}")
    out = {
        "_note": "Horizon elevation angle (deg) per azimuth (0=N, 90=E) from LRO LOLA LDEM_875S_20M. "
                 "Site coordinates are approximate region centres.",
        "dem": LBL.name,
        "max_distance_m": MAX_DISTANCE_M,
        "observer_height_m": OBSERVER_HEIGHT_M,
        "sites": {},
    }
    for site in load_sites():
        print(f"\n{site['name']} ({site['latitude']}, {site['longitude']})")
        try:
            win = T.load_site_window(LBL, site["latitude"], site["longitude"], MAX_DISTANCE_M)
        except ValueError as e:
            print(f"  SKIPPED: {e}")
            continue
        site_sanity(site, win)
        series = analyze_site(site["id"], START, END, STEP_MIN)
        az, hz = summarize_site(site, win, series)
        out["sites"][site["id"]] = {
            "latitude": site["latitude"],
            "longitude": site["longitude"],
            "azimuth_step_deg": 1.0,
            "horizon_deg": [round(float(v), 3) for v in hz],
        }
    OUT_JSON.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"\nWrote {OUT_JSON} ({len(out['sites'])} sites)")


if __name__ == "__main__":
    main()