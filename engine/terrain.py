"""
Terrain horizon from LRO LOLA topography (LDEM, polar stereographic).

Two layers:
  1. Pure numpy core (horizon_profile, horizon_at): no file or map knowledge,
     easy to test with a synthetic terrain.
  2. File layer (load_site_window): reads the LOLA DEM with rasterio and
     converts a site latitude/longitude into pixel coordinates.

Azimuth convention matches Skyfield altaz(): 0 = north, 90 = east, clockwise.
"""
import re
from pathlib import Path

import numpy as np

MOON_RADIUS_M = 1737400.0


# ---------------------------------------------------------------- numpy core
def _bilinear(dem, rows, cols):
    """Bilinear sample of dem at float (rows, cols). Outside the array -> nan."""
    h, w = dem.shape
    r0 = np.floor(rows).astype(np.int64)
    c0 = np.floor(cols).astype(np.int64)
    valid = (r0 >= 0) & (r0 < h - 1) & (c0 >= 0) & (c0 < w - 1)
    r0c = np.clip(r0, 0, h - 2)
    c0c = np.clip(c0, 0, w - 2)
    fr = rows - r0c
    fc = cols - c0c
    top = dem[r0c, c0c] * (1 - fc) + dem[r0c, c0c + 1] * fc
    bot = dem[r0c + 1, c0c] * (1 - fc) + dem[r0c + 1, c0c + 1] * fc
    out = top * (1 - fr) + bot * fr
    return np.where(valid, out, np.nan)


def horizon_profile(
    dem,
    res_m,
    row0,
    col0,
    north_rc,
    east_rc,
    max_distance_m=30000.0,
    az_step_deg=1.0,
    observer_height_m=0.0,
    radius_m=MOON_RADIUS_M,
):
    """
    Horizon elevation angle (degrees) for every azimuth, seen from pixel
    (row0, col0) on a height grid `dem` (metres).

    north_rc / east_rc : unit vectors (d_row, d_col) of local north and east
                         in pixel space.
    Curvature of the Moon is included (drop = d^2 / 2R).
    Returns (azimuths_deg, horizon_deg).
    """
    h0 = _bilinear(dem, np.array([row0]), np.array([col0]))[0]
    if np.isnan(h0):
        raise ValueError("Site is outside the DEM window")
    h0 = h0 + observer_height_m

    az = np.arange(0.0, 360.0, az_step_deg)
    rad = np.radians(az)
    n_steps = int(max_distance_m // res_m)
    dist_m = np.arange(1, n_steps + 1) * res_m
    dist_px = dist_m / res_m

    n_r, n_c = north_rc
    e_r, e_c = east_rc
    dir_r = np.cos(rad)[:, None] * n_r + np.sin(rad)[:, None] * e_r
    dir_c = np.cos(rad)[:, None] * n_c + np.sin(rad)[:, None] * e_c

    rows = row0 + dir_r * dist_px[None, :]
    cols = col0 + dir_c * dist_px[None, :]
    height = _bilinear(dem, rows, cols)

    drop = dist_m**2 / (2.0 * radius_m)
    dz = height - h0 - drop[None, :]
    ang = np.degrees(np.arctan2(dz, dist_m[None, :]))
    ang = np.where(np.isnan(ang), -np.inf, ang)
    hz = ang.max(axis=1)
    if not np.all(np.isfinite(hz)):
        raise ValueError("Some directions have no terrain data (site too close to the DEM edge)")
    return az, hz


def horizon_at(azimuth_deg, profile_az, profile_hz):
    """Horizon elevation at arbitrary azimuths (linear interpolation, wraps at 360)."""
    az = np.asarray(azimuth_deg, dtype=float) % 360.0
    xs = np.append(profile_az, 360.0)
    ys = np.append(profile_hz, profile_hz[0])
    return np.interp(az, xs, ys)


# ---------------------------------------------------------------- file layer
def read_label_scaling(lbl_path):
    """Reads SCALING_FACTOR and OFFSET (height formula) from the PDS .LBL file."""
    text = Path(lbl_path).read_text(errors="ignore")
    sf = re.search(r"^\s*SCALING_FACTOR\s*=\s*([-+0-9.eE]+)", text, re.M)
    off = re.search(r"^\s*OFFSET\s*=\s*([-+0-9.eE]+)", text, re.M)
    if not sf or not off:
        raise RuntimeError(
            "Could not find SCALING_FACTOR / OFFSET in the .LBL file. "
            "Refusing to guess the height scale."
        )
    return float(sf.group(1)), float(off.group(1))


def load_site_window(lbl_path, lat, lon, max_distance_m=30000.0):
    """
    Reads a window of the LOLA DEM around (lat, lon) and returns a dict:
      dem        float32 grid of heights in metres (relative to the 1737.4 km sphere)
      res_m, row0, col0, north_rc, east_rc, x, y (map metres), site_height_m
    Raises ValueError if the site (or the needed window) is outside the DEM.
    """
    import rasterio
    from rasterio.crs import CRS
    from rasterio.warp import transform as warp_transform
    from rasterio.windows import Window

    scale, offset = read_label_scaling(lbl_path)

    with rasterio.open(str(lbl_path)) as ds:
        res_m = float(ds.res[0])
        geo = CRS.from_proj4(f"+proj=longlat +R={MOON_RADIUS_M} +no_defs")

        def to_xy(la, lo):
            xs, ys = warp_transform(geo, ds.crs, [lo], [la])
            return xs[0], ys[0]

        x0, y0 = to_xy(lat, lon)
        # local north / east directions, measured through the same map transform
        d = 0.001
        xn, yn = to_xy(lat + d, lon)
        xe, ye = to_xy(lat, lon + d)
        n_vec = np.array([xn - x0, yn - y0])
        e_vec = np.array([xe - x0, ye - y0])
        n_vec /= np.hypot(*n_vec)
        e_vec /= np.hypot(*e_vec)

        # map (x right, y up) -> pixel (row down, col right)
        north_rc = (-n_vec[1], n_vec[0])
        east_rc = (-e_vec[1], e_vec[0])

        t = ds.transform
        col_f = (x0 - t.c) / t.a
        row_f = (y0 - t.f) / t.e
        reach = int(np.ceil(max_distance_m / res_m)) + 3
        c_lo, c_hi = int(col_f) - reach, int(col_f) + reach
        r_lo, r_hi = int(row_f) - reach, int(row_f) + reach
        if c_lo < 0 or r_lo < 0 or c_hi >= ds.width or r_hi >= ds.height:
            raise ValueError(
                "Site is too close to the edge of (or outside) this DEM. "
                "A larger-area DEM file is needed for this site."
            )
        win = Window(c_lo, r_lo, c_hi - c_lo + 1, r_hi - r_lo + 1)
        raw = ds.read(1, window=win).astype(np.float64)

    dem = (raw * scale + offset - MOON_RADIUS_M).astype(np.float32)
    row0 = row_f - r_lo
    col0 = col_f - c_lo
    site_h = float(_bilinear(dem, np.array([row0]), np.array([col0]))[0])
    return {
        "dem": dem,
        "res_m": res_m,
        "row0": row0,
        "col0": col0,
        "north_rc": north_rc,
        "east_rc": east_rc,
        "x": x0,
        "y": y0,
        "site_height_m": site_h,
    }