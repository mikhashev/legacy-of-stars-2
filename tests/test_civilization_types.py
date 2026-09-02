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

from src.legacy_of_stars_v3 import CivilizationStage, StarSystem  # noqa: E402

LIVING_TYPES = {"biological_pure", "digital_ascended", "hybrid_integrated"}
STRATEGIES = {"L", "LB", "LR", "LA", "LBA"}


def sample_systems(count: int, seed: int = 42):
    random.seed(seed)
    return [StarSystem(f"Test-{i}", random.uniform(4, 50)) for i in range(count)]


class CivilizationTypeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.systems = sample_systems(4000)
        cls.civs = [s for s in cls.systems if s.has_civilization]
        cls.living = [s for s in cls.civs if not s.is_extinct]
        cls.extinct = [s for s in cls.civs if s.is_extinct]

    def test_galaxy_is_mostly_silent(self):
        fraction = len(self.civs) / len(self.systems)
        self.assertTrue(0.10 < fraction < 0.20, fraction)
        extinct_fraction = len(self.extinct) / len(self.civs)
        self.assertTrue(0.18 < extinct_fraction < 0.32, extinct_fraction)

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
            self.assertGreaterEqual(system.extinct_years_ago, 500)

    def test_type_distribution_follows_weights(self):
        counts = {name: 0 for name in LIVING_TYPES}
        for system in self.living:
            counts[system.civilization_type] += 1
        self.assertGreaterEqual(counts["biological_pure"], counts["digital_ascended"])
        self.assertGreaterEqual(counts["digital_ascended"], counts["hybrid_integrated"])

    def test_most_civilizations_are_older_than_humanity(self):
        older = sum(1 for s in self.living if s.civilization_age > 100)
        self.assertGreater(older / len(self.living), 0.6)


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
