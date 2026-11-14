import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from skyfield.api import Loader, PlanetaryConstants

# Scorekeeper function in engine/metrics.py
from engine.metrics import compute_metrics

# Paths to data/sites.json and a local cache folder for space files
ROOT_DIR = Path(__file__).resolve().parent.parent
SITES_PATH = ROOT_DIR / "data" / "sites.json"
CACHE_DIR = Path.home() / ".lunapilot_cache"

NAIF = "https://naif.jpl.nasa.gov/pub/naif/generic_kernels"

# Each kernel is tried from several known NAIF locations; first success wins.
MOON_FRAME_KERNEL_URLS = [
    f"{NAIF}/fk/satellites/moon_080317.tf",
]
PCK_TEXT_URLS = [
    f"{NAIF}/pck/pck00011.tpc",
    f"{NAIF}/pck/pck00010.tpc",
    f"{NAIF}/pck/a_old_versions/pck00010.tpc",
    f"{NAIF}/pck/a_old_versions/pck00008.tpc",
    f"{NAIF}/pck/pck00008.tpc",
]
MOON_PCK_BINARY_URLS = [
    f"{NAIF}/pck/moon_pa_de421_1900-2050.bpc",
]


def load_sites() -> list[dict]:
    """Reads and returns all candidate landing sites from data/sites.json."""
    with open(SITES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_site_by_id(site_id: str) -> dict:
    """Finds a single landing site dictionary by its 'id' string."""
    for site in load_sites():
        if site["id"] == site_id:
            return site
    raise ValueError(f"Unknown site_id '{site_id}'. Check data/sites.json.")


def _load_first_available(loader, urls):
    """Returns the first URL in the list that loads/downloads successfully."""
    errors = []
    for url in urls:
        try:
            return loader(url)
        except OSError as e:  # 404s, network errors
            errors.append(f"  {url} -> {e}")
    raise RuntimeError("None of the kernel URLs worked:\n" + "\n".join(errors))


def _load_skyfield_environment():
    """
    Loads the planetary ephemeris (de421.bsp) and builds the Moon's body-fixed
    frame (MOON_ME_DE421) so an observer can sit at a lunar lat/lon.
    Everything is cached in CACHE_DIR so it only downloads once.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    loader = Loader(str(CACHE_DIR))

    ts = loader.timescale()
    eph = loader("de421.bsp")

    pc = PlanetaryConstants()
    pc.read_text(_load_first_available(loader, MOON_FRAME_KERNEL_URLS))
    pc.read_text(_load_first_available(loader, PCK_TEXT_URLS))
    pc.read_binary(_load_first_available(loader, MOON_PCK_BINARY_URLS))
    moon_frame = pc.build_frame_named("MOON_ME_DE421")

    return ts, eph, pc, moon_frame


def _parse_utc_datetime(date_str: str) -> datetime:
    """Converts an ISO date string (like '2029-03-01') into a UTC datetime object."""
    dt = datetime.fromisoformat(date_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def analyze_site(
    site_id: str,
    start: str,
    end: str,
    step_minutes: int = 30,
) -> dict:
    """
    Simulates Sun and Earth elevation angles at a lunar South Pole site
    over a date range and returns the full time series + survival metrics.
    """
    # 1. Look up the site's latitude and longitude
    site = get_site_by_id(site_id)

    # 2. Load Skyfield space data and the Moon's coordinate frame
    ts, eph, pc, moon_frame = _load_skyfield_environment()
    sun = eph["sun"]
    earth = eph["earth"]
    moon = eph["moon"]

    # 3. Build the list of UTC timestamps from start to end every 'step_minutes'
    start_dt = _parse_utc_datetime(start)
    end_dt = _parse_utc_datetime(end)
    if end_dt <= start_dt:
        raise ValueError("'end' date must be strictly after 'start' date.")

    dt_list = []
    current_dt = start_dt
    step_delta = timedelta(minutes=step_minutes)
    while current_dt <= end_dt:
        dt_list.append(current_dt)
        current_dt += step_delta

    t = ts.from_datetimes(dt_list)

    # 4. Place the observer on the Moon at the site's latitude & longitude
    observer = moon + pc.build_latlon_degrees(
        moon_frame,
        site["latitude"],
        site["longitude"],
        elevation_m=0,
    )

    # 5. Elevation of the Sun and Earth above the local horizon
    sun_alt, _, _ = observer.at(t).observe(sun).apparent().altaz()
    earth_alt, _, _ = observer.at(t).observe(earth).apparent().altaz()

    sun_elevation_deg = [round(float(deg), 4) for deg in sun_alt.degrees]
    earth_elevation_deg = [round(float(deg), 4) for deg in earth_alt.degrees]

    # 6. Compute the 4 survival scores
    metrics = compute_metrics(sun_elevation_deg, earth_elevation_deg, step_minutes)

    # 7. Data contract for the UI and AI copilot
    return {
        "site_id": site["id"],
        "start": start,
        "end": end,
        "step_minutes": step_minutes,
        "time": [dt.isoformat() for dt in dt_list],
        "sun_elevation_deg": sun_elevation_deg,
        "earth_elevation_deg": earth_elevation_deg,
        "metrics": metrics,
    }


# Quick sanity check: python -m engine.geometry
if __name__ == "__main__":
    result = analyze_site("connecting_ridge", "2029-03-01", "2029-03-31")
    sun_min = min(result["sun_elevation_deg"])
    sun_max = max(result["sun_elevation_deg"])
    print("Site:", result["site_id"])
    print("Total data points:", len(result["time"]))
    print("Sun min/max deg:", sun_min, "to", sun_max)
    print("Earth min/max deg:", min(result["earth_elevation_deg"]), "to", max(result["earth_elevation_deg"]))
    print("Metrics:", result["metrics"])
    assert -5 <= sun_min and sun_max <= 5, f"Sun range {sun_min}..{sun_max} is off, check the frame"
    print("Sanity check passed: Sun stays near the horizon")