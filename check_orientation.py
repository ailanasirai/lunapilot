"""
Orientation test (experimental, branch terrain-lola).

Same 5 m terrain and same Sun positions, but the Sun azimuth is rotated or mirrored
in 8 ways. If one variant gives about 92% (Glaser et al. 2014, CR1, 2 m), then our
azimuth/direction convention is wrong and that variant shows the fix.

Run from the project root:  python check_orientation.py
"""
from pathlib import Path

import numpy as np

import check_crosscheck as cc
import check_5m as c5
from engine import terrain as T
from engine.geometry import _load_skyfield_environment

TIF = Path("data/terrain/Site01_final_adj_5mpp_surf.tif")
LAT, LON = -89.4649, 222.1027
REACH_M = 7000.0
YEAR = 2027

VARIANTS = {
    "as is": lambda a: a % 360,
    "+90": lambda a: (a + 90) % 360,
    "+180": lambda a: (a + 180) % 360,
    "+270": lambda a: (a + 270) % 360,
    "mirror": lambda a: (-a) % 360,
    "mirror +90": lambda a: (90 - a) % 360,
    "mirror +180": lambda a: (180 - a) % 360,
    "mirror +270": lambda a: (270 - a) % 360,
}


def main():
    win = c5.load_window_tif(TIF, LAT, LON, REACH_M)
    env = _load_skyfield_environment()
    alt, az = cc.sun_series(LAT, LON, YEAR, env)
    limb = alt + cc.SUN_RADIUS_DEG
    print(f"CR1, 5 m DEM, year {YEAR}, Sun as disk")
    print(f"Sun elevation range: {alt.min():.2f} to {alt.max():.2f} deg")
    print(f"flat horizon (0 deg): {100.0 * float((limb > 0).mean()):.1f}% sunlit\n")

    profiles = {}
    for h in (2.0, 10.0):
        profiles[h] = T.horizon_profile(
            win["dem"], win["res_m"], win["row0"], win["col0"],
            win["north_rc"], win["east_rc"], max_distance_m=REACH_M, observer_height_m=h,
        )
    az2, hz2 = profiles[2.0]
    print("horizon at 2 m (azimuth: degrees):")
    print("  " + "  ".join(f"{a}:{hz2[a]:.2f}" for a in range(0, 360, 30)))
    print(f"  min {hz2.min():.2f}  max {hz2.max():.2f}  mean {hz2.mean():.2f}\n")

    print("variant          2 m      10 m")
    for name, f in VARIANTS.items():
        out = []
        for h in (2.0, 10.0):
            a_, hz_ = profiles[h]
            out.append(100.0 * float((limb > T.horizon_at(f(az), a_, hz_)).mean()))
        print(f"{name:14s} {out[0]:6.1f}%  {out[1]:6.1f}%")
    print("\nPublished CR1: 92.27% (2 m), 95.65% (10 m)")


if __name__ == "__main__":
    main()