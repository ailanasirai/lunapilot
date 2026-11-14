import calendar
from engine.geometry import analyze_site, load_sites

print(load_sites())
for sid in ["connecting_ridge", "peak_near_shackleton", "nobile_rim_2"]:
    print(sid)
    for m in range(1, 13):
        last = calendar.monthrange(2029, m)[1]
        r = analyze_site(sid, f"2029-{m:02d}-01", f"2029-{m:02d}-{last}", 60)
        mt = r["metrics"]
        print(f"  2029-{m:02d}  sun {mt['sunlit_fraction']:.2f}  earth {mt['earth_visible_fraction']:.2f}  both {mt['both_fraction']:.2f}  dark_h {mt['longest_dark_hours']:.0f}")