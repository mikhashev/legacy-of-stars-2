"""
Galaxy generation: civilization types, strategies, ages and stages.
"""
import os
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("LOS_OFFLINE", "1")

from src.legacy_of_stars_v3 import (  # noqa: E402
    BASE_CIV_CHANCE, CivilizationStage, StarSystem, habitability_weight, load_star_catalog)

LIVING_TYPES = {"biological_pure", "digital_ascended", "hybrid_integrated"}
STRATEGIES = {"L", "LB", "LR", "LA", "LBA"}
CATALOG = load_star_catalog()


def sample_systems(count: int, seed: int = 42):
    """A sky with the same spread of spectral classes as the real catalog."""
    random.seed(seed)
    types = [star["spectral_type"] for star in CATALOG]
    return [StarSystem(f"Test-{i}", random.uniform(4, 50), types[i % len(types)]) for i in range(count)]


class CivilizationTypeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.systems = sample_systems(4000)
        cls.civs = [s for s in cls.systems if s.has_civilization]
        cls.living = [s for s in cls.civs if not s.is_extinct]
        cls.extinct = [s for s in cls.civs if s.is_extinct]

    def test_galaxy_is_mostly_silent(self):
        # T5 (2026-09-03) raised BASE_CIV_CHANCE 0.26 -> 0.32 and lowered the extinct-at-creation
        # share 0.25 -> 0.15 during calibration (docs/plans/civilization_timelines_plan.md §7);
        # see the calibration block in src/civ_timeline.py.
        fraction = len(self.civs) / len(self.systems)
        self.assertTrue(0.15 < fraction < 0.27, fraction)
        extinct_fraction = len(self.extinct) / len(self.civs)
        self.assertTrue(0.10 < extinct_fraction < 0.20, extinct_fraction)

    def test_every_civilization_has_a_valid_type(self):
        for system in self.civs:
            self.assertIn(system.civilization_type, LIVING_TYPES | {"failed_transition"}, system.name)
        for system in self.systems:
            if not system.has_civilization:
                self.assertIsNone(system.civilization_type)
                self.assertIsNone(system.true_strategy)

    def test_living_civilizations_have_strategies_and_types(self):
        for system in self.living:
            self.assertIn(system.true_strategy, STRATEGIES)
            self.assertIn(system.civilization_type, LIVING_TYPES)
            self.assertIsNotNone(system.civilization_stage)
            self.assertTrue(0.0 <= system.deception_level <= 1.0)

    def test_extinct_civilizations_mostly_failed_the_transition(self):
        failed = sum(1 for s in self.extinct if s.civilization_type == "failed_transition")
        share = failed / len(self.extinct)
        self.assertTrue(0.55 <= share <= 0.85, share)
        for system in self.extinct:
            self.assertIsNone(system.true_strategy)
            self.assertIsNone(system.civilization_stage)
            # Causality: we can't have seen a death whose light hasn't reached us yet.
            self.assertGreaterEqual(system.extinct_years_ago, max(50, int(system.distance)))
            self.assertLessEqual(system.extinct_years_ago, 5000)

    def test_type_distribution_follows_weights(self):
        counts = {name: 0 for name in LIVING_TYPES}
        for system in self.living:
            counts[system.civilization_type] += 1
        self.assertGreaterEqual(counts["biological_pure"], counts["digital_ascended"])
        self.assertGreaterEqual(counts["digital_ascended"], counts["hybrid_integrated"])

    def test_most_civilizations_are_older_than_humanity(self):
        older = sum(1 for s in self.living if s.civilization_age > 100)
        self.assertGreater(older / len(self.living), 0.6)


class HabitabilityWeightTest(unittest.TestCase):
    CASES = (
        ("G2V", 1.0), ("K5V", 1.0), ("M5.5V", 0.6), ("F5IV-V", 0.6), ("G8IV", 0.5),
        ("K0III", 0.0), ("DZ8", 0.0), ("A1V", 0.1), (None, 1.0),
        ("G2V? (candidate 2MASS 19281982-2640123)", 1.0),
    )

    def test_weights_by_spectral_class(self):
        for spectral_type, expected in self.CASES:
            self.assertAlmostEqual(habitability_weight(spectral_type), expected, msg=spectral_type)

    def test_every_catalog_star_has_a_known_weight(self):
        for star in CATALOG:
            self.assertIn(habitability_weight(star["spectral_type"]), (0.0, 0.1, 0.5, 0.6, 1.0), star)


class CatalogCivilizationCountTest(unittest.TestCase):
    """What BASE_CIV_CHANCE produces over the real catalogue, near field and whole sky.

    The per-star chance was calibrated on the original 53-star catalogue, where it averaged
    ~8 civilizations. T4 deepened the catalogue to 94 stars out to ~160 LY without touching
    the constant, so the density stayed unchanged through T4 and the totals simply followed the
    larger sky: ~16.2 over the whole catalogue, of which ~8.5 lie within 20 LY.

    T5 calibration (2026-09-03, plan §7) then raised BASE_CIV_CHANCE 0.26 -> 0.32 to bring the
    observed-frame sky-change rate up (see src/civ_timeline.py's calibration block), which raised
    both totals: ~19.8 over the whole catalogue, ~10.2 within 20 LY.
    """

    def test_full_catalog_averages_about_twenty_civilizations(self):
        random.seed(2026)
        runs = 300
        total = 0
        near = 0
        for _ in range(runs):
            for star in CATALOG:
                if StarSystem(star["name"], star["distance"], star["spectral_type"]).has_civilization:
                    total += 1
                    if star["distance"] <= 20.0:
                        near += 1
        mean = total / runs
        near_mean = near / runs
        self.assertTrue(18.0 <= mean <= 21.5, f"mean civilizations per catalog: {mean}")
        self.assertTrue(8.5 <= near_mean <= 12.0, f"mean civilizations within 20 LY: {near_mean}")

    def test_evolved_stars_never_host_anyone(self):
        random.seed(7)
        for spectral_type in ("K0III", "G8III", "DZ8"):
            for _ in range(50):
                self.assertFalse(StarSystem("X", 10.0, spectral_type).has_civilization)

    def test_base_chance_applies_to_a_perfect_star(self):
        self.assertAlmostEqual(BASE_CIV_CHANCE * habitability_weight("G2V"), BASE_CIV_CHANCE)


class AgeToStageTest(unittest.TestCase):
    def test_mapping(self):
        system = StarSystem("Probe", 10.0)
        expected = {
            25: CivilizationStage.PRE_RADIO,
            150: CivilizationStage.EARLY_RADIO,
            500: CivilizationStage.DIGITAL,
            5000: CivilizationStage.INTERPLANETARY,
            50000: CivilizationStage.INTERSTELLAR,
            500000: CivilizationStage.POST_BIOLOGICAL,
        }
        for age, stage in expected.items():
            self.assertEqual(system._age_to_stage(age), stage)

    def test_round_trip_generations(self):
        self.assertEqual(StarSystem("A", 4.2).get_round_trip_time(), 1)
        self.assertEqual(StarSystem("B", 12.5).get_round_trip_time(), 1)
        self.assertEqual(StarSystem("C", 12.6).get_round_trip_time(), 2)
        self.assertEqual(StarSystem("D", 50.0).get_round_trip_time(), 4)


if __name__ == "__main__":
    unittest.main()
