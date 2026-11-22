"""
Cross-check against a published number (experimental, branch terrain-lola).

Published reference: Glaser et al. (2014), Icarus 243, "Illumination conditions at the
lunar south pole using high resolution Digital Terrain Models from LOLA".
Their abstract reports, for the Connecting Ridge site CR1:
    sunlight 92.27% of the time at 2 m above ground, 95.65% at 10 m,
    longest continuous darkness typically 3 to 5 days.
CR1 location (89.4649 S, 222.1027 E) is taken from a related paper by the same group.
Their simulation period is NOT stated in the sources we could read, so we run several
years and show every one of them.

Our model: LOLA 20 m DEM + NASA JPL DE421 Sun position, Sun as a disk
(any part of the Sun above the horizon counts as sunlit).

Run from the project root:  python check_crosscheck.py
"""
from pathlib import Path

import numpy as np

from engine import terrain as T
from engine.geometry import _load_skyfield_environment

LBL = Path("data/terrain/LDEM_875S_20M.LBL")
CR1_LAT, CR1_LON = -89.4649, 222.1027
YEARS = list(range(2025, 2044))  # about one 18.6-year lunar cycle
STEP_MIN = 30
MAX_DISTANCE_M = 30000.0
SUN_RADIUS_DEG = 0.2666
HEIGHTS_M = (2.0, 10.0)
SHIFT_M = 100.0


def sun_series(lat, lon, year, env):
    ts, eph, pc, moon_frame = env
    n = int(round((366 if year % 4 == 0 else 365) * 24 * 60 / STEP_MIN))
    t0 = ts.utc(year, 1, 1).tt
    t = ts.tt_jd(t0 + np.arange(n) * STEP_MIN / 1440.0)
    observer = eph["moon"] + pc.build_latlon_degrees(moon_frame, lat, lon, elevation_m=0)
    alt, az, _ = observer.at(t).observe(eph["sun"]).apparent().altaz()
    return np.asarray(alt.degrees), np.asarray(az.degrees)


def sunlit(win, sun_alt, sun_az, height_m, disk, dr_px=0.0, dc_px=0.0):
    az, hz = T.horizon_profile(
        win["dem"], win["res_m"], win["row0"] + dr_px, win["col0"] + dc_px,
        win["north_rc"], win["east_rc"],
        max_distance_m=MAX_DISTANCE_M, observer_height_m=height_m,
    )
    limb = sun_alt + (SUN_RADIUS_DEG if disk else 0.0)
    return float((limb > T.horizon_at(sun_az, az, hz)).mean()) * 100.0


def longest_dark_days(win, sun_alt, sun_az, height_m):
    az, hz = T.horizon_profile(
        win["dem"], win["res_m"], win["row0"], win["col0"], win["north_rc"], win["east_rc"],
        max_distance_m=MAX_DISTANCE_M, observer_height_m=height_m,
    )
    dark = (sun_alt + SUN_RADIUS_DEG) <= T.horizon_at(sun_az, az, hz)
    best = run = 0
    for d in dark:
        run = run + 1 if d else 0
        best = max(best, run)
    return best * STEP_MIN / 1440.0


def main():
    print(f"CR1 ({CR1_LAT}, {CR1_LON}), LOLA 20 m DEM, Sun as a disk")
    win = T.load_site_window(LBL, CR1_LAT, CR1_LON, MAX_DISTANCE_M + SHIFT_M + 100)
    env = _load_skyfield_environment()

    acc = {h: [] for h in HEIGHTS_M}
    acc_point = {h: [] for h in HEIGHTS_M}
    dark_longest = {h: 0.0 for h in HEIGHTS_M}
    shift_vals = []
    step_px = SHIFT_M / win["res_m"]
    offs = [-step_px, 0.0, step_px]

    print("\nyear   sunlit 2 m   sunlit 10 m   (Sun as disk)")
    for year in YEARS:
        alt, az = sun_series(CR1_LAT, CR1_LON, year, env)
        row = []
        for h in HEIGHTS_M:
            v = sunlit(win, alt, az, h, True)
            acc[h].append(v)
            acc_point[h].append(sunlit(win, alt, az, h, False))
            dark_longest[h] = max(dark_longest[h], longest_dark_days(win, alt, az, h))
            row.append(v)
        print(f"{year}   {row[0]:8.1f}%   {row[1]:9.1f}%")
        if year in (2025, 2029, 2035):
            shift_vals += [sunlit(win, alt, az, 2.0, True, dr, dc) for dr in offs for dc in offs]

    print("\nAverage over", YEARS[0], "to", YEARS[-1])
    for h in HEIGHTS_M:
        print(f"  {h:4.0f} m: Sun as disk {np.mean(acc[h]):.1f}%   "
              f"Sun as point {np.mean(acc_point[h]):.1f}%   "
              f"longest dark run {dark_longest[h]:.1f} days")
    print(f"  Site shifted up to {SHIFT_M:.0f} m (2 m, disk, years 2025/2029/2035): "
          f"min {min(shift_vals):.1f}%  median {np.median(shift_vals):.1f}%  max {max(shift_vals):.1f}%")
    print("\nPublished (Glaser et al. 2014, CR1): 92.27% at 2 m, 95.65% at 10 m, "
          "longest dark 3 to 5 days")


if __name__ == "__main__":
    main()