"""
Builds data/horizons_lola.json for the app (experimental, branch terrain-lola).

One site only: the best-lit point within 1 km of the published Connecting Ridge CR1
coordinates, found on NASA's 5 m LOLA DEM (rule: highest sunlit share at 2 m,
see check_best_spot.py; no tuning towards the published number).

The app reads this small file, so the 5 m DEM is not needed at runtime.

Run from the project root:  python make_horizons_json.py
"""
import json
from pathlib import Path

import numpy as np

import check_5m as c5
from engine import terrain as T

TIF = Path("data/terrain/Site01_final_adj_5mpp_surf.tif")
OUT = Path("data/horizons_lola.json")
REACH_M = 7000.0
OBSERVER_HEIGHT_M = 2.0

SITE = {
    "id": "connecting_ridge_summit",
    "name": "Connecting Ridge (best-lit point)",
    "latitude": -89.4733,
    "longitude": 222.6912,
}


def main():
    win = c5.load_window_tif(TIF, SITE["latitude"], SITE["longitude"], REACH_M)
    az, hz = T.horizon_profile(
        win["dem"], win["res_m"], win["row0"], win["col0"],
        win["north_rc"], win["east_rc"],
        max_distance_m=REACH_M, observer_height_m=OBSERVER_HEIGHT_M,
    )
    print(f"{SITE['name']}  ({SITE['latitude']}, {SITE['longitude']})")
    print(f"  horizon: min {hz.min():.2f}  max {hz.max():.2f}  mean {hz.mean():.2f} deg")
    print("  " + "  ".join(f"{a}:{hz[a]:.2f}" for a in range(0, 360, 45)))

    out = {
        "_note": ("Terrain horizon elevation angle (degrees) for each azimuth 0..359 "
                  "(0 = north, 90 = east, clockwise, same as the engine). Computed from "
                  "NASA LRO LOLA 5 m topography. Preliminary."),
        "dem": "NASA PGDA Site01_final_adj_5mpp_surf.tif (LRO LOLA, 5 m/pixel, M. K. Barker)",
        "reach_m": REACH_M,
        "observer_height_m": OBSERVER_HEIGHT_M,
        "azimuth_step_deg": 1.0,
        "sites": {
            SITE["id"]: {
                "name": SITE["name"],
                "latitude": SITE["latitude"],
                "longitude": SITE["longitude"],
                "selection": ("Highest sunlit share at 2 m among spots within 1 km of the "
                              "published CR1 coordinates (89.4649 S, 222.1027 E)"),
                "cross_check": ("Reproduces Glaser et al. 2014 for CR1: 92.27% sunlit at 2 m, "
                                "95.65% at 10 m (ours 90 to 95% at the best-lit points). "
                                "Single site, single published source."),
                "horizon_deg": [round(float(v), 3) for v in hz],
            }
        },
    }
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"\nWrote {OUT}")


if __name__ == "__main__":
    main()