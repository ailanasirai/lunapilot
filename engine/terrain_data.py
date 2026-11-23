"""
Terrain horizons for the app (experimental, branch terrain-lola).

Reads data/horizons_lola.json (small file made by make_horizons_json.py from NASA LRO LOLA
5 m topography) and applies it to an engine result, so the existing score functions work
unchanged:

    Sun above terrain   : sun_elevation + SUN_RADIUS_DEG - horizon(sun azimuth)   (Sun as a disk)
    Earth above terrain : earth_elevation - horizon(earth azimuth)                 (Earth centre)

A value above 0 means "visible". Sites without terrain data are returned unchanged.
"""
import json
from pathlib import Path

import numpy as np

SUN_RADIUS_DEG = 0.2666
HORIZONS_PATH = Path(__file__).resolve().parent.parent / "data" / "horizons_lola.json"

_cache = {}


def _load(path=HORIZONS_PATH):
    key = str(path)
    if key not in _cache:
        try:
            _cache[key] = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            _cache[key] = {"sites": {}}
    return _cache[key]


def has_terrain(site_id, path=HORIZONS_PATH):
    return site_id in _load(path).get("sites", {})


def terrain_meta(site_id, path=HORIZONS_PATH):
    """Short facts about a site's terrain data (for captions), or None."""
    data = _load(path)
    site = data.get("sites", {}).get(site_id)
    if site is None:
        return None
    return {
        "dem": data.get("dem", ""),
        "reach_m": data.get("reach_m"),
        "observer_height_m": data.get("observer_height_m"),
        "cross_check": site.get("cross_check", ""),
    }


def horizon_at(azimuth_deg, horizon_deg):
    """Horizon elevation at any azimuth (0 = north, clockwise), wrapping at 360."""
    hz = np.asarray(horizon_deg, dtype=float)
    az_grid = np.arange(len(hz)) * (360.0 / len(hz))
    az = np.mod(np.asarray(azimuth_deg, dtype=float), 360.0)
    return np.interp(az, np.append(az_grid, 360.0), np.append(hz, hz[0]))


def apply_terrain(res, site_id, path=HORIZONS_PATH):
    """Returns a copy of res whose elevations are measured above the terrain horizon.
    If the site has no terrain data (or the result has no azimuths) res is returned as is."""
    site = _load(path).get("sites", {}).get(site_id)
    if site is None or "sun_azimuth_deg" not in res or "earth_azimuth_deg" not in res:
        return res
    hz = site["horizon_deg"]
    sun = np.asarray(res["sun_elevation_deg"], dtype=float)
    earth = np.asarray(res["earth_elevation_deg"], dtype=float)
    out = dict(res)
    out["sun_elevation_deg"] = [float(v) for v in sun + SUN_RADIUS_DEG - horizon_at(res["sun_azimuth_deg"], hz)]
    out["earth_elevation_deg"] = [float(v) for v in earth - horizon_at(res["earth_azimuth_deg"], hz)]
    out["terrain_applied"] = True
    return out