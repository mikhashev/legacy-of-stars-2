"""
Passive leakage (v1.1): the time-based leakage front, loudness, inverse-square detection
and information attacks that travel at the speed of light.
"""
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("LOS_OFFLINE", "1")

from src.legacy_of_stars_v3 import CivilizationStage, ContactProgram  # noqa: E402
from src.passive_leakage import BASE_DETECTION, PassiveLeakageSystem  # noqa: E402

RANDOM = "src.legacy_of_stars_v3.random.random"


class LeakageFrontTest(unittest.TestCase):
    def setUp(self):
        self.leakage = PassiveLeakageSystem()

    def test_front_expands_one_light_year_per_year_from_1935(self):
        self.assertEqual(self.leakage.leakage_front(1977), 42.0)
        self.assertEqual(self.leakage.leakage_front(2027), 92.0)
        self.assertEqual(self.leakage.leakage_front(1900), 0.0)

    def test_broadcast_radius_is_the_front_and_ignores_technology(self):
        self.assertEqual(self.leakage.leakage_front(1977), 42.0)

    def test_loudness_peaks_until_2000_then_falls_to_a_floor(self):
        self.assertEqual(self.leakage.loudness(1990), 1.0)
        self.assertEqual(self.leakage.loudness(2000), 1.0)
        self.assertAlmostEqual(self.leakage.loudness(2037.5), 0.7)
        self.assertAlmostEqual(self.leakage.loudness(2075), 0.4)
        self.assertAlmostEqual(self.leakage.loudness(2100), 0.4)


class DetectionProbabilityTest(unittest.TestCase):
    def setUp(self):
        self.leakage = PassiveLeakageSystem()

    def test_reference_distance_gives_the_base_chance(self):
        p = self.leakage.calculate_detection_probability(10.0, 1990, 1.0)
        self.assertAlmostEqual(p, BASE_DETECTION)
        self.assertAlmostEqual(self.leakage.calculate_detection_probability(10.0, 2100, 0.5),
                               BASE_DETECTION * 0.4 * 0.5)

    def test_inverse_square_falls_off_and_is_capped_nearby(self):
        near = self.leakage.calculate_detection_probability(10.0, 1990, 1.0)
        far = self.leakage.calculate_detection_probability(20.0, 1990, 1.0)
        closer = self.leakage.calculate_detection_probability(5.0, 1990, 1.0)
        self.assertAlmostEqual(far, near / 4)
        self.assertAlmostEqual(closer, near)  # capped at 1.0, nobody hears us louder than full

    def test_silence_means_no_detection(self):
        self.assertEqual(self.leakage.calculate_detection_probability(4.2, 1990, 0.0), 0.0)


class TravelTimeTest(unittest.TestCase):
    def test_travel_time_rounds_up(self):
        leakage = PassiveLeakageSystem()
        # 10 LY at 0.175c is 57.1 years: three generations, not two.
        self.assertEqual(leakage.calculate_travel_time(10.0, "laser_sail"), 3)
        self.assertEqual(leakage.calculate_travel_time(10.0, "fusion"), 4)
        self.assertEqual(leakage.calculate_travel_time(0.5, "laser_sail"), 1)
        with self.assertRaises(ValueError):
            leakage.calculate_travel_time(10.0, "fleet")


def hostile_program(distance: float, seed: int = 4):
    """A silent galaxy with a single hostile listener at a chosen distance."""
    p = ContactProgram(seed=seed, offline=True)
    for system in p.star_systems.values():
        system.has_civilization = False
        system.true_strategy = None
    target = next(iter(p.star_systems.values()))
    target.has_civilization = True
    target.is_extinct = False
    target.true_strategy = "LA"
    target.distance = distance
    target.civilization_stage = CivilizationStage.DIGITAL
    target.deception_level = 0.0
    p.public_support = 100
    p.funding = 100
    p.undiscovered = []  # no new systems to discover mid-test
    return p, target


class DelayedInformationAttackTest(unittest.TestCase):
    def test_information_attack_arrives_one_light_time_later(self):
        p, target = hostile_program(40.0)
        with mock.patch(RANDOM, return_value=0.0), \
                mock.patch.object(p.leakage_system, "determine_attack_type", return_value="information"):
            p.advance_generation()

        detection_gen = p.generation
        # Our leakage already reached them (front check); only their signal's 40 LY remain.
        round_trip = 2
        self.assertTrue(target.has_detected_earth)
        self.assertEqual(p.stats["passive_detections"], 1)
        # Nothing has happened to us yet: a signal cannot be seen coming.
        self.assertEqual(p.stats["info_attacks"], 0)
        self.assertEqual(p.pending_info_attacks, [[target.name, detection_gen + round_trip]])
        self.assertFalse(any(e.kind == "info_attack" for e in p.drain_events()))

        with mock.patch(RANDOM, return_value=0.99):
            while p.pending_info_attacks and p.generation < detection_gen + round_trip:
                p.advance_generation()
                if p.generation < detection_gen + round_trip:
                    self.assertEqual(p.stats["info_attacks"], 0)

        self.assertEqual(p.generation, detection_gen + round_trip)
        self.assertEqual(p.stats["info_attacks"], 1)
        self.assertEqual(p.pending_info_attacks, [])
        self.assertTrue(any(e.kind == "info_attack" for e in p.drain_events()))

    def test_physical_attacks_wait_for_our_leakage_to_reach_them(self):
        p, target = hostile_program(40.0)
        with mock.patch(RANDOM, return_value=0.0), \
                mock.patch.object(p.leakage_system, "determine_attack_type", return_value="laser_sail"):
            p.advance_generation()
        warning = p.pending_attack_warnings[0]
        # Our leakage already reached them; 228.6 years of flight is 10 generations.
        self.assertEqual(warning.arrival_gen, p.generation + 10)

    def test_pending_attacks_survive_a_save(self):
        p, target = hostile_program(40.0)
        p.pending_info_attacks.append([target.name, p.generation + 4])
        reloaded = ContactProgram.from_dict(p.to_dict(), offline=True)
        self.assertEqual(reloaded.pending_info_attacks, [[target.name, p.generation + 4]])
        self.assertEqual(ContactProgram.from_dict({}, offline=True).pending_info_attacks, [])


class FrontGatesDetectionTest(unittest.TestCase):
    def test_a_system_beyond_the_front_is_never_detected(self):
        p, target = hostile_program(100.0)  # front in 1977 is only 42 LY
        with mock.patch(RANDOM, return_value=0.0):
            p.advance_generation()
        self.assertFalse(target.has_detected_earth)
        self.assertEqual(p.stats["passive_detections"], 0)
        self.assertEqual(p.pending_info_attacks, [])


if __name__ == "__main__":
    unittest.main()
