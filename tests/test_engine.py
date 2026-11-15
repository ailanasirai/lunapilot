import sys
import unittest
from pathlib import Path

# Add project root to sys.path so running `python tests/test_engine.py` finds `engine`
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from engine.geometry import analyze_site, load_sites


class TestLunaPilotEngine(unittest.TestCase):
    """Unit tests covering Aila's 5 required engine checks."""

    def test_1_nobile_rim_2_elevation_bounds(self):
        """1. Nobile Rim 2 on a fixed date has Sun and Earth elevation within [-90, 90]."""
        result = analyze_site("nobile_rim_2", "2029-07-01", "2029-07-02", step_minutes=60)
        for sun_deg in result["sun_elevation_deg"]:
            self.assertGreaterEqual(sun_deg, -90.0)
            self.assertLessEqual(sun_deg, 90.0)
        for earth_deg in result["earth_elevation_deg"]:
            self.assertGreaterEqual(earth_deg, -90.0)
            self.assertLessEqual(earth_deg, 90.0)

    def test_2_all_sites_load_without_error(self):
        """2. All sites in data/sites.json load cleanly and run without error."""
        sites = load_sites()
        self.assertGreaterEqual(len(sites), 5)
        for site in sites:
            self.assertIn("id", site)
            self.assertIn("name", site)
            self.assertIn("latitude", site)
            self.assertIn("longitude", site)
            res = analyze_site(site["id"], "2029-07-01T00:00:00", "2029-07-01T02:00:00", step_minutes=60)
            self.assertEqual(res["site_id"], site["id"])

    def test_3_date_outside_1900_to_2050_raises_error(self):
        """3. Dates outside the 1900 to 2050 kernel range raise a clear ValueError."""
        with self.assertRaises(ValueError):
            analyze_site("connecting_ridge", "1899-01-01", "1899-01-02")
        with self.assertRaises(ValueError):
            analyze_site("connecting_ridge", "2051-01-01", "2051-01-02")

    def test_4_start_after_end_raises_error(self):
        """4. Start date after end date raises a clear ValueError."""
        with self.assertRaises(ValueError):
            analyze_site("connecting_ridge", "2029-07-10", "2029-07-01")

    def test_5_output_list_lengths_match_step_size(self):
        """5. Output lists have the same length and match the step size."""
        # 24 hours at 30-minute steps = 48 intervals + 1 inclusive endpoint = 49 points
        result = analyze_site("connecting_ridge", "2029-07-01T00:00:00", "2029-07-02T00:00:00", step_minutes=30)
        expected_len = 49
        self.assertEqual(len(result["time"]), expected_len)
        self.assertEqual(len(result["sun_elevation_deg"]), expected_len)
        self.assertEqual(len(result["earth_elevation_deg"]), expected_len)


if __name__ == "__main__":
    unittest.main(verbosity=2)
