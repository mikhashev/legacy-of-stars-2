"""
The star catalogue itself: `data/star_catalog.json` is data, and data can rot silently.

Every check here is about a property the engine and the front-end rely on rather than about
astronomy: names are the primary key (systems are stored by name), the load order is
nearest-first (discovery walks it that way), and the sky positions must be usable by the map's
J2000 conversion. The angular-separation check catches the copy-paste failure that data files
are actually prone to - two stars given the same coordinates - which would draw them on top of
each other on the map.
"""
import json
import math
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("LOS_OFFLINE", "1")

from src.legacy_of_stars_v3 import CATALOG_PATH, habitability_weight, load_star_catalog  # noqa: E402

# The catalogue T4 deepened: 53 stars within ~51 LY plus 41 more out to ~160 LY.
EXPECTED_COUNT = 94
FARTHEST_LY = 160.0
MIN_SEPARATION_DEG = 0.05


def angular_separation(a: dict, b: dict) -> float:
    """Great-circle angle between two catalogue entries, in degrees."""
    dec_a, dec_b = math.radians(a["dec"]), math.radians(b["dec"])
    delta_ra = math.radians(a["ra"] - b["ra"])
    cos_theta = (math.sin(dec_a) * math.sin(dec_b)
                 + math.cos(dec_a) * math.cos(dec_b) * math.cos(delta_ra))
    return math.degrees(math.acos(max(-1.0, min(1.0, cos_theta))))


class StarCatalogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(CATALOG_PATH, encoding="utf-8") as f:
            cls.raw = json.load(f)
        cls.stars = cls.raw["stars"]
        cls.loaded = load_star_catalog()

    def test_the_catalogue_has_the_expected_number_of_stars(self):
        self.assertEqual(len(self.stars), EXPECTED_COUNT)
        self.assertEqual(len(self.loaded), EXPECTED_COUNT)
        self.assertIn("~160 light-years", self.raw["_comment"])

    def test_names_are_unique(self):
        names = [s["name"] for s in self.stars]
        duplicates = {n for n in names if names.count(n) > 1}
        self.assertEqual(duplicates, set())

    def test_load_returns_them_nearest_first(self):
        distances = [s["distance"] for s in self.loaded]
        self.assertEqual(distances, sorted(distances))
        self.assertEqual(self.loaded[0]["name"], "Proxima Centauri")
        self.assertLessEqual(distances[-1], FARTHEST_LY)

    def test_every_entry_carries_a_usable_sky_position_and_type(self):
        for star in self.stars:
            self.assertTrue(star["name"].strip(), star)
            self.assertGreater(star["distance"], 0, star)
            self.assertLessEqual(star["distance"], FARTHEST_LY, star)
            self.assertTrue(0.0 <= star["ra"] < 360.0, star)
            self.assertTrue(-90.0 <= star["dec"] <= 90.0, star)
            self.assertTrue(star["spectral_type"].strip(), star)
            # The engine must be able to score the type; an unparsed one silently becomes 0.5.
            self.assertIn(habitability_weight(star["spectral_type"]), (0.0, 0.1, 0.5, 0.6, 1.0), star)

    def test_no_two_stars_share_a_sky_position(self):
        for i, a in enumerate(self.stars):
            for b in self.stars[i + 1:]:
                self.assertGreater(angular_separation(a, b), MIN_SEPARATION_DEG,
                                   f"{a['name']} and {b['name']} are on top of each other")

    def test_the_deep_field_exists_and_is_mostly_sun_like(self):
        """T4's point: enough far stars for 4-6 generation one-way delays, and worth talking to."""
        far = [s for s in self.stars if s["distance"] >= 60.0]
        self.assertGreaterEqual(len(far), 8)
        # The tier-3 reach is 100 LY, so that band must not be empty or the deepest tier of
        # the Detection tree would open onto nothing.
        self.assertTrue([s for s in self.stars if 80.0 <= s["distance"] <= 100.0])
        mid = [s for s in self.stars if 25.0 <= s["distance"] < 60.0]
        self.assertGreaterEqual(len(mid), 20)
        habitable = [s for s in mid if habitability_weight(s["spectral_type"]) >= 0.5]
        self.assertGreater(len(habitable) / len(mid), 0.7)


if __name__ == "__main__":
    unittest.main()
