"""
Best-spot search around CR1 (experimental, branch terrain-lola).

Idea: the published CR1 may be the true summit, a few hundred metres from the
coordinates we used. We scan a 1 km radius on the 5 m DEM, rank spots by sunlit share
(2 m height, Sun as a disk), then check the best spots over several years.

Run from the project root:  python check_best_spot.py
"""
from pathlib import Path

import numpy as np

import check_5m as c5
import check_crosscheck as cc
from engine import terrain as T
from engine.geometry import _load_skyfield_environment

TIF = Path("data/terrain/Site01_final_adj_5mpp_surf.tif")
LAT, LON = -89.4649, 222.1027
SPAN_M = 1000.0
GRID_STEP_M = 50.0
SCAN_REACH_M = 4000.0
FULL_REACH_M = 7000.0
SCAN_YEAR = 2027
CHECK_YEARS = [2025, 2029, 2033, 2037, 2041, 2043]
TOP_N = 5
MIN_SEPARATION_M = 150.0


def scan(win, alt, az):
    res = win["res_m"]
    limb = alt + cc.SUN_RADIUS_DEG
    offs = np.arange(-SPAN_M, SPAN_M + 1, GRID_STEP_M) / res
    rows = []
    for dr in offs:
        for dc in offs:
            if np.hypot(dr, dc) * res > SPAN_M:
                continue
            try:
                a, hz = T.horizon_profile(
                    win["dem"], res, win["row0"] + dr, win["col0"] + dc,
                    win["north_rc"], win["east_rc"], max_distance_m=SCAN_REACH_M,
                    az_step_deg=5.0, observer_height_m=2.0)
            except ValueError:
                continue
            pct = 100.0 * float((limb > T.horizon_at(az, a, hz)).mean())
            rows.append((pct, dr * res, dc * res))
    return rows


def pick_top(rows):
    rows = sorted(rows, reverse=True)
    chosen = []
    for pct, dr_m, dc_m in rows:
        if all(np.hypot(dr_m - c[1], dc_m - c[2]) >= MIN_SEPARATION_M for c in chosen):
            chosen.append((pct, dr_m, dc_m))
        if len(chosen) == TOP_N:
            break
    return chosen


def main():
    import rasterio
    from rasterio.crs import CRS
    from rasterio.warp import transform as warp_transform

    win = c5.load_window_tif(TIF, LAT, LON, SCAN_REACH_M + SPAN_M + 100)
    env = _load_skyfield_environment()
    alt, az = cc.sun_series(LAT, LON, SCAN_YEAR, env)
    print(f"Scanning {SPAN_M:.0f} m around CR1 ({LAT}, {LON}), year {SCAN_YEAR}, 2 m, Sun as disk ...")
    rows = scan(win, alt, az)
    pcts = np.array([r[0] for r in rows])
    print(f"  {len(rows)} spots. sunlit share: min {pcts.min():.1f}%  median {np.median(pcts):.1f}%  max {pcts.max():.1f}%")
    top = pick_top(rows)

    with rasterio.open(str(TIF)) as ds:
        crs = ds.crs
    geo = CRS.from_proj4(f"+proj=longlat +R={T.MOON_RADIUS_M} +no_defs")
    full = c5.load_window_tif(TIF, LAT, LON, FULL_REACH_M)

    print("\nBest spots, checked over several years (reach 7 km):")
    for i, (pct, dr_m, dc_m) in enumerate(top, 1):
        x = win["x"] + dc_m * 1.0
        y = win["y"] - dr_m * 1.0
        lons, lats = warp_transform(crs, geo, [x], [y])
        lat, lon = lats[0], lons[0] % 360.0
        row = full["row0"] + dr_m / full["res_m"]
        col = full["col0"] + dc_m / full["res_m"]
        h_site = float(T._bilinear(full["dem"], np.array([row]), np.array([col]))[0])
        res_h = {2.0: [], 10.0: []}
        dark = {2.0: 0.0, 10.0: 0.0}
        for year in CHECK_YEARS:
            a, z = cc.sun_series(lat, lon, year, env)
            for h in res_h:
                azp, hz = T.horizon_profile(
                    full["dem"], full["res_m"], row, col, full["north_rc"], full["east_rc"],
                    max_distance_m=FULL_REACH_M, observer_height_m=h)
                limb = a + cc.SUN_RADIUS_DEG
                dk = limb <= T.horizon_at(z, azp, hz)
                res_h[h].append(100.0 * (1.0 - float(dk.mean())))
                best = run = 0
                for d in dk:
                    run = run + 1 if d else 0
                    best = max(best, run)
                dark[h] = max(dark[h], best * cc.STEP_MIN / 1440.0)
        print(f" #{i} lat {lat:.4f} lon {lon:.4f}  offset from CR1: {np.hypot(dr_m, dc_m):.0f} m, "
              f"height vs CR1 {h_site - full['site_height_m']:+.0f} m")
        print(f"     2 m: {np.mean(res_h[2.0]):.1f}%  (dark run {dark[2.0]:.1f} d)    "
              f"10 m: {np.mean(res_h[10.0]):.1f}%  (dark run {dark[10.0]:.1f} d)")
    print("\nPublished CR1: 92.27% (2 m), 95.65% (10 m), longest dark 3 to 5 days")


if __name__ == "__main__":
    main()