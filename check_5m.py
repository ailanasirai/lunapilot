"""
Cross-check with NASA's improved 5 m LOLA DEMs (experimental, branch terrain-lola).

Data: PGDA "High-Resolution LOLA Topography for Lunar South Pole Sites" (M. K. Barker),
files data/terrain/Site01_final_adj_5mpp_surf.tif (Connecting Ridge region)
      data/terrain/Site07_final_adj_5mpp_surf.tif (Peak near Shackleton region)

Published reference for CR1 (Glaser et al. 2014, 20 m DTM): 92.27% sunlit at 2 m,
95.65% at 10 m, longest dark run typically 3 to 5 days.

Note: each 5 m tile covers only about 20 x 20 km, so terrain farther than the tile
edge is NOT seen. That can only make our sunlit share too high, never too low.

Run from the project root:  python check_5m.py
"""
from pathlib import Path

import numpy as np

import check_crosscheck as cc
import check_terrain as ct
from engine import terrain as T
from engine.geometry import _load_skyfield_environment

TERRAIN_DIR = Path("data/terrain")
CASES = [
    # name, tif, lat, lon, published (2 m, 10 m) or None
    ("Connecting Ridge CR1", "Site01_final_adj_5mpp_surf.tif", -89.4649, 222.1027, (92.27, 95.65)),
    ("Peak Near Shackleton (region centre)", "Site07_final_adj_5mpp_surf.tif", -89.017, 126.273, None),
]
REACH_TRIES_M = (9000.0, 7000.0, 5000.0, 3000.0)
YEARS = list(range(2025, 2044))


def load_window_tif(path, lat, lon, max_distance_m):
    import rasterio
    from rasterio.crs import CRS
    from rasterio.warp import transform as warp_transform
    from rasterio.windows import Window

    with rasterio.open(str(path)) as ds:
        if ds.crs is None:
            raise RuntimeError("This GeoTIFF has no map projection (CRS), cannot place the site.")
        res_m = float(ds.res[0])
        geo = CRS.from_proj4(f"+proj=longlat +R={T.MOON_RADIUS_M} +no_defs")

        def to_xy(la, lo):
            xs, ys = warp_transform(geo, ds.crs, [lo], [la])
            return xs[0], ys[0]

        x0, y0 = to_xy(lat, lon)
        d = 0.001
        xn, yn = to_xy(lat + d, lon)
        xe, ye = to_xy(lat, lon + d)
        n_vec = np.array([xn - x0, yn - y0])
        e_vec = np.array([xe - x0, ye - y0])
        n_vec /= np.hypot(*n_vec)
        e_vec /= np.hypot(*e_vec)
        north_rc = (-n_vec[1], n_vec[0])
        east_rc = (-e_vec[1], e_vec[0])

        t = ds.transform
        col_f = (x0 - t.c) / t.a
        row_f = (y0 - t.f) / t.e
        reach = int(np.ceil(max_distance_m / res_m)) + 3
        c_lo, c_hi = int(col_f) - reach, int(col_f) + reach
        r_lo, r_hi = int(row_f) - reach, int(row_f) + reach
        if c_lo < 0 or r_lo < 0 or c_hi >= ds.width or r_hi >= ds.height:
            raise ValueError("site too close to the tile edge for this reach")
        win = Window(c_lo, r_lo, c_hi - c_lo + 1, r_hi - r_lo + 1)
        raw = ds.read(1, window=win).astype(np.float64)
        if ds.nodata is not None:
            raw[raw == ds.nodata] = np.nan

    dem = raw.astype(np.float32)
    row0, col0 = row_f - r_lo, col_f - c_lo
    site_h = float(T._bilinear(dem, np.array([row0]), np.array([col0]))[0])
    return {"dem": dem, "res_m": res_m, "row0": row0, "col0": col0,
            "north_rc": north_rc, "east_rc": east_rc, "x": x0, "y": y0, "site_height_m": site_h}


def describe(path):
    import rasterio
    with rasterio.open(str(path)) as ds:
        print(f"  file {path.name}: {ds.width} x {ds.height} px, pixel {ds.res[0]} m, dtype {ds.dtypes[0]}, nodata {ds.nodata}")
        print(f"  bounds: {tuple(round(v) for v in ds.bounds)}")


def main():
    env = _load_skyfield_environment()
    for name, fname, lat, lon, published in CASES:
        print(f"\n{name} ({lat}, {lon})")
        path = TERRAIN_DIR / fname
        if not path.exists():
            print(f"  SKIPPED: {path} not found")
            continue
        describe(path)
        win, reach = None, None
        for r in REACH_TRIES_M:
            try:
                win = load_window_tif(path, lat, lon, r)
                reach = r
                break
            except ValueError:
                continue
        if win is None:
            print("  SKIPPED: this tile does not contain the site with enough room around it")
            continue
        print(f"  terrain used out to {reach / 1000:.0f} km around the site")
        ct.site_sanity({"latitude": lat}, win)

        cc.MAX_DISTANCE_M = reach
        res = {h: [] for h in (2.0, 10.0)}
        dark = {h: 0.0 for h in (2.0, 10.0)}
        for year in YEARS:
            alt, az = cc.sun_series(lat, lon, year, env)
            for h in res:
                res[h].append(cc.sunlit(win, alt, az, h, True))
                dark[h] = max(dark[h], cc.longest_dark_days(win, alt, az, h))
        for h in res:
            line = (f"  {h:4.0f} m: sunlit {np.mean(res[h]):.1f}% "
                    f"(years {min(res[h]):.1f} to {max(res[h]):.1f}), longest dark run {dark[h]:.1f} days")
            if published:
                line += f"   published {published[0 if h == 2.0 else 1]}%"
            print(line)
    print("\nPublished CR1 (Glaser et al. 2014): 92.27% at 2 m, 95.65% at 10 m, dark 3 to 5 days")


if __name__ == "__main__":
    main()