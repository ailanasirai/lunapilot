"""
How much do the terrain results move when we change the assumptions?
(experimental, branch terrain-lola)

For each site inside the LOLA DEM it prints the sunlit share for:
  - observer height 0 m and 2 m
  - Sun as a point (centre of the Sun) and as a disk (any part of the Sun visible)
and then the spread when the site is shifted by up to 100 m in each direction
(site coordinates are only approximate region centres).

Run from the project root:  python check_sensitivity.py
"""
from pathlib import Path

import numpy as np

from engine import terrain as T
from engine.geometry import analyze_site, load_sites

LBL = Path("data/terrain/LDEM_875S_20M.LBL")
MAX_DISTANCE_M = 30000.0
START, END, STEP_MIN = "2029-07-01", "2029-07-31", 30
SUN_RADIUS_DEG = 0.2666  # angular radius of the Sun seen from about 1 AU
HEIGHTS_M = (0.0, 2.0)
SHIFT_M = 100.0


def sunlit_pct(win, series, dr_px=0.0, dc_px=0.0, height_m=0.0, disk=False):
    az, hz = T.horizon_profile(
        win["dem"], win["res_m"], win["row0"] + dr_px, win["col0"] + dc_px,
        win["north_rc"], win["east_rc"],
        max_distance_m=MAX_DISTANCE_M, observer_height_m=height_m,
    )
    sun = np.array(series["sun_elevation_deg"])
    sun_az = np.array(series["sun_azimuth_deg"])
    limb = sun + (SUN_RADIUS_DEG if disk else 0.0)
    return 100.0 * float((limb > T.horizon_at(sun_az, az, hz)).mean())


def report(site, win, series):
    flat = 100.0 * float((np.array(series["sun_elevation_deg"]) > 0).mean())
    print(f"  flat horizon (reference): {flat:.1f}% sunlit")
    print("  observer height   Sun as point   Sun as disk")
    for h in HEIGHTS_M:
        p = sunlit_pct(win, series, height_m=h, disk=False)
        d = sunlit_pct(win, series, height_m=h, disk=True)
        print(f"  {h:5.1f} m           {p:8.1f}%      {d:8.1f}%")

    step_px = SHIFT_M / win["res_m"]
    offsets = [-step_px, 0.0, step_px]
    vals = [
        sunlit_pct(win, series, dr, dc, height_m=2.0, disk=True)
        for dr in offsets for dc in offsets
    ]
    print(f"  site shifted up to {SHIFT_M:.0f} m (9 positions, 2 m height, Sun as disk):")
    print(f"    min {min(vals):.1f}%   median {float(np.median(vals)):.1f}%   max {max(vals):.1f}%")


def main():
    for site in load_sites():
        print(f"\n{site['name']} ({site['latitude']}, {site['longitude']})")
        try:
            win = T.load_site_window(
                LBL, site["latitude"], site["longitude"], MAX_DISTANCE_M + SHIFT_M + 100
            )
        except ValueError as e:
            print(f"  SKIPPED: {e}")
            continue
        series = analyze_site(site["id"], START, END, STEP_MIN)
        report(site, win, series)
    print(f"\nPeriod: {START} to {END}. Sun radius used: {SUN_RADIUS_DEG} deg.")


if __name__ == "__main__":
    main()