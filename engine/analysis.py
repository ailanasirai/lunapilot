"""Pure analysis helpers built on top of the engine output (no Streamlit here, so they can be unit tested).

All functions take the dict returned by engine.geometry.analyze_site.
sun_mask / earth_mask are minimum elevations in degrees. 0 means a flat horizon.
"""
import numpy as np
import pandas as pd


def longest_run(flags):
    """Length of the longest run of True values."""
    best = cur = 0
    for f in flags:
        cur = cur + 1 if f else 0
        best = max(best, cur)
    return best


def _arrays(res):
    sun = np.asarray(res["sun_elevation_deg"], dtype=float)
    earth = np.asarray(res["earth_elevation_deg"], dtype=float)
    if len(sun) == 0 or len(sun) != len(earth):
        raise ValueError("Elevation lists must be non-empty and the same length")
    return sun, earth


def fractions(res, sun_mask=0.0, earth_mask=0.0):
    """Share of time the Sun / Earth are above their masks, plus the longest dark period."""
    sun, earth = _arrays(res)
    sun_up = sun > sun_mask
    earth_up = earth > earth_mask
    return {
        "sunlit_fraction": float(sun_up.mean()),
        "earth_visible_fraction": float(earth_up.mean()),
        "both_fraction": float((sun_up & earth_up).mean()),
        "longest_dark_hours": longest_run(~sun_up) * res["step_minutes"] / 60,
    }


def scores(m, w_power=0.5):
    """Power, comms and overall score (0 to 100). Overall = w x power + (1 - w) x comms."""
    power = m["sunlit_fraction"] * 100
    comms = m["earth_visible_fraction"] * 100
    return power, comms, w_power * power + (1 - w_power) * comms


def monthly_table(res, sun_mask=0.0, earth_mask=0.0):
    """Percent of time above the masks for each calendar month present in the data."""
    sun, earth = _arrays(res)
    t = pd.to_datetime(res["time"])
    df = pd.DataFrame({"month": t.month, "sun": sun > sun_mask, "earth": earth > earth_mask})
    g = df.groupby("month").mean() * 100
    g.columns = ["Sunlit %", "Earth visible %"]
    return g


def best_window(res, days, w_power=0.5, sun_mask=0.0, earth_mask=0.0):
    """Best contiguous window of `days` days by the weighted score. Returns start, end and percentages."""
    sun, earth = _arrays(res)
    n = max(1, int(days * 24 * 60 // res["step_minutes"]))
    if len(sun) < n:
        raise ValueError("The window is longer than the available data")
    t = pd.to_datetime(res["time"])
    s_roll = pd.Series((sun > sun_mask).astype(float)).rolling(n).mean()
    e_roll = pd.Series((earth > earth_mask).astype(float)).rolling(n).mean()
    score = w_power * s_roll + (1 - w_power) * e_roll
    i = int(score.idxmax())
    a = i - n + 1
    return {
        "start": t[a],
        "end": t[i],
        "power": float(s_roll[i] * 100),
        "comms": float(e_roll[i] * 100),
        "overall": float(score[i] * 100),
    }