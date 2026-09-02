"""
Attack Early Warning System: warnings, defensive actions, resolution and diplomacy.
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

from src.attack_warning import ATTACK_TYPE_LABELS, AttackWarning  # noqa: E402
from src.legacy_of_stars_v3 import CivilizationStage, ContactProgram  # noqa: E402

RANDOM = "src.legacy_of_stars_v3.random.random"


class AttackWarningTest(unittest.TestCase):
    def setUp(self):
        self.p = ContactProgram(seed=31, offline=True)
        for system in self.p.star_systems.values():
            system.has_civilization = False
            system.true_strategy = None
        self.hostile = next(iter(self.p.star_systems.values()))
        self.hostile.has_civilization = True
        self.hostile.is_extinct = False
        self.hostile.true_strategy = "LA"
        self.hostile.civilization_stage = CivilizationStage.DIGITAL
        self.hostile.deception_level = 0.0
        self.hostile.distance = 10.0
        self.p.action_points = 3
        self.p.max_action_points = 3

    def test_message_creates_warning_with_preparation_time(self):
        self.p.send_message(self.hostile.name, "Hello!")
        self.assertEqual(len(self.p.pending_attack_warnings), 1)
        warning = self.p.pending_attack_warnings[0]
        self.assertIs(warning.source, self.hostile)
        self.assertEqual(warning.arrival_gen, self.p.attack_arrival_generation(self.hostile))
        self.assertGreaterEqual(warning.get_etas_remaining(self.p.generation), 2)
        self.assertEqual(warning.type_label, ATTACK_TYPE_LABELS["fleet"])
        self.assertIn("HOSTILE FLEET DETECTED", self.p.message)
        self.assertIn("defend", [a.id for a in self.p.available_actions()])

    def test_emergency_defense_requires_all_ap_and_halves_damage(self):
        self.p.send_message(self.hostile.name, "Hello!")  # 1 AP spent
        self.p.defend_emergency(0)
        self.assertIn("requires ALL action points", self.p.message)
        self.p.calculate_ap()
        self.p.defend_emergency(0)
        warning = self.p.pending_attack_warnings[0]
        self.assertIn("Emergency Defense Protocol", warning.defensive_actions_taken)
        self.assertAlmostEqual(warning.defense_multiplier, 0.5)
        self.assertEqual(warning.get_defense_percentage(), 50)
        self.assertEqual(self.p.action_points, 0)
        self.p.calculate_ap()
        self.p.defend_emergency(0)
        self.assertIn("already activated", self.p.message)

    def test_evacuation_costs_one_action_point_and_stacks(self):
        self.p.send_message(self.hostile.name, "Hello!")
        ap = self.p.action_points
        self.p.defend_evacuate(0)
        warning = self.p.pending_attack_warnings[0]
        self.assertEqual(self.p.action_points, ap - 1)
        self.assertAlmostEqual(warning.defense_multiplier, 0.7)
        self.p.calculate_ap()
        self.p.defend_emergency(0)
        self.assertAlmostEqual(warning.defense_multiplier, 0.35)
        self.assertEqual(warning.get_defense_percentage(), 65)

    def test_attack_resolves_on_arrival_and_warning_is_removed(self):
        self.p.send_message(self.hostile.name, "Hello!")
        warning = self.p.pending_attack_warnings[0]
        self.p.calculate_ap()
        self.p.defend_evacuate(0)
        self.p.public_support = 90
        self.p.funding = 90
        with mock.patch(RANDOM, return_value=0.99):
            while self.p.generation < warning.arrival_gen and not self.p.game_over:
                self.p.advance_generation()
        self.assertFalse(self.p.game_over)
        self.assertNotIn(warning, self.p.pending_attack_warnings)
        self.assertEqual(self.p.stats["attacks_landed"], 1)
        self.assertEqual(self.p.stats["attacks_survived"], 1)
        # DIGITAL (2) vs tech level 1 -> "advanced" attack: 40 support x 0.7 evacuation = 28
        self.assertLess(self.p.public_support, 90 - 20)
        texts = [e.text for e in self.p.drain_events()]
        self.assertTrue(any("ATTACK FROM" in t for t in texts))

    def test_diplomacy_can_turn_back_a_low_deception_trap(self):
        self.hostile.true_strategy = "LBA"
        self.hostile.deception_level = 0.3
        self.p.send_message(self.hostile.name, "Peace!")
        self.assertEqual(len(self.p.pending_attack_warnings), 1)
        self.p.calculate_ap()
        with mock.patch(RANDOM, return_value=0.0):
            self.p.defend_diplomacy(0)
        self.assertEqual(self.p.pending_attack_warnings, [])
        self.assertIn("DIPLOMATIC BREAKTHROUGH", self.p.message)
        self.assertEqual(self.p.fermi_evidence["cooperation_evidence"], 1)
        self.assertIn("Diplomatic Breakthrough", self.p.achievements)

    def test_diplomacy_never_works_on_a_pure_aggressor(self):
        self.p.send_message(self.hostile.name, "Peace!")
        self.p.calculate_ap()
        with mock.patch(RANDOM, return_value=0.0):
            self.p.defend_diplomacy(0)
        self.assertEqual(len(self.p.pending_attack_warnings), 1)
        self.assertIn("Unlikely to work", self.p.message)
        self.assertIn("Diplomatic Contact", self.p.pending_attack_warnings[0].defensive_actions_taken)

    def test_too_late_to_defend_after_arrival(self):
        warning = AttackWarning(self.hostile, self.p.generation, self.p.generation)
        self.p.pending_attack_warnings.append(warning)
        self.p.defend_evacuate(0)
        self.assertIn("Too late", self.p.message)
        self.p.defend_emergency(5)
        self.assertIn("Invalid warning index", self.p.message)


if __name__ == "__main__":
    unittest.main()
