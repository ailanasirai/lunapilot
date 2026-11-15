import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
from engine.analysis import best_window, fractions, longest_run, monthly_table, scores


def make(sun, earth, step=60, start="2029-01-01"):
    n = len(sun)
    times = [t.isoformat() for t in pd.date_range(start, periods=n, freq=f"{step}min", tz="UTC")]
    return {"time": times, "sun_elevation_deg": sun, "earth_elevation_deg": earth, "step_minutes": step}


def test_longest_run():
    assert longest_run([True, True, False, True]) == 2
    assert longest_run([]) == 0


def test_fractions_flat_horizon():
    m = fractions(make([1, -1, 1, -1], [1, 1, 1, 1]))
    assert m["sunlit_fraction"] == 0.5
    assert m["earth_visible_fraction"] == 1.0
    assert m["both_fraction"] == 0.5


def test_fractions_with_mask():
    res = make([0.5, 1.5, 2.5, 3.5], [3, 3, 3, 3])
    assert fractions(res)["sunlit_fraction"] == 1.0
    assert fractions(res, sun_mask=2.0)["sunlit_fraction"] == 0.5
    assert fractions(res, earth_mask=5.0)["earth_visible_fraction"] == 0.0


def test_longest_dark_hours_uses_step():
    m = fractions(make([1, -1, -1, -1, 1], [1] * 5, step=30))
    assert m["longest_dark_hours"] == 1.5


def test_scores_formula_and_weight():
    m = {"sunlit_fraction": 0.5, "earth_visible_fraction": 0.25}
    assert scores(m, 0.5) == (50.0, 25.0, 37.5)
    assert scores(m, 1.0)[2] == 50.0


def test_bad_input():
    for bad in (make([], []), make([1, 2], [1])):
        try:
            fractions(bad)
            assert False
        except ValueError:
            pass


def test_monthly_table():
    sun = [1] * 31 * 24 + [-1] * 28 * 24
    res = make(sun, [1] * len(sun))
    g = monthly_table(res)
    assert g.loc[1, "Sunlit %"] == 100.0
    assert g.loc[2, "Sunlit %"] == 0.0


def test_best_window_finds_sunny_days():
    sun = [-1] * 24 * 5 + [1] * 24 * 3 + [-1] * 24 * 5
    res = make(sun, [1] * len(sun))
    b = best_window(res, 3)
    assert b["power"] == 100.0
    assert str(b["start"].date()) == "2029-01-06"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
