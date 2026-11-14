import numpy as np
from engine.geometry import analyze_site, load_sites

print(load_sites())
for sid in ["connecting_ridge", "peak_near_shackleton", "nobile_rim_2"]:
    r = analyze_site(sid, "2029-03-01", "2029-03-31", 60)
    sun = np.array(r["sun_elevation_deg"])
    earth = np.array(r["earth_elevation_deg"])
    print(sid)
    print("  sun   min/max:", round(sun.min(), 2), round(sun.max(), 2))
    print("  earth min/max:", round(earth.min(), 2), round(earth.max(), 2))
    print("  metrics:", r["metrics"])