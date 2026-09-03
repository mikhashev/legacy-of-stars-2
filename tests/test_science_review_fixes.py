"""Regressions for the issues found in the review of the scientific-accuracy changes."""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["LOS_OFFLINE"] = "1"

from src.legacy_of_stars_v3 import CivilizationStage, ContactProgram, habitability_weight  # noqa: E402
from src.genesis_project import STAGE_NAMES, SeededWorld  # noqa: E402


def program(seed=7):
    return ContactProgram(seed=seed, offline=True)


class WowSourceIsolationTest(unittest.TestCase):
    def test_messaging_the_source_before_gen_144_reveals_nothing_and_launches_nothing(self):
        p = program()
        p.wow_signal.reply("")
        source = p.wow_signal.wow_source_system
        source.has_civilization = True
        source._roll_civilization()
        source.timeline = None   # hand-written: static, so every frame reads these fields
        source.is_extinct = False
        source.true_strategy = "LA"
        source.civilization_stage = CivilizationStage.DIGITAL
        p.action_points = 2
        p.send_message(source.name, "hello")
        self.assertEqual(p.stats["attacks_scheduled"], 0)
        self.assertEqual(p.pending_attack_warnings, [])
        self.assertIn("Generation 144", p.message)
        self.assertEqual(p.action_points, 1)

    def test_source_is_never_an_ark_target(self):
        p = program()
        p.wow_signal.reply("")
        source = p.wow_signal.wow_source_system
        source.has_civilization = False
        source._clear_civilization()
        p.genesis.unlocked = True
        p.research_points, p.funding, p.action_points = 5000, 100, 3
        ok, msg = p.genesis.seed_world(p, source)
        self.assertFalse(ok)
        self.assertIn("1,800", msg)

    def test_hostile_answer_that_ends_the_game_ends_it_once(self):
        p = program()
        p.wow_signal.reply("")
        source = p.wow_signal.wow_source_system
        source.has_civilization = True
        source._roll_civilization()
        source.timeline = None   # hand-written: static, so every frame reads these fields
        source.is_extinct = False
        source.true_strategy = "LA"
        source.civilization_stage = CivilizationStage.DIGITAL
        p.generation = 143
        p.public_support, p.funding = 12, 100
        pick = lambda seq: "societal_manipulation" if "societal_manipulation" in seq else seq[0]
        with mock.patch("src.legacy_of_stars_v3.random.random", return_value=0.99), \
                mock.patch("src.legacy_of_stars_v3.random.choice", side_effect=pick):
            p.advance_generation()
        self.assertTrue(p.game_over)
        self.assertEqual(p.wow_signal.outcome, "hostile")
        self.assertTrue(source.has_detected_earth)
        self.assertEqual(sum(1 for e in p.drain_events() if e.kind == "game_over"), 1)

    def test_old_resolved_save_does_not_grow_a_source(self):
        p = program()
        data = p.to_dict()
        data["wow_signal"].update({"decided": True, "wow_replied": True, "outcome": "silence",
                                   "wow_source_name": None})
        restored = ContactProgram.from_dict(data, offline=True)
        self.assertIsNone(restored.wow_signal.wow_source_system)
        self.assertFalse(any(s.is_wow_source for s in restored.star_systems.values()))


class GenesisMigrationTest(unittest.TestCase):
    def test_v1_stage_indices_shift_past_in_transit(self):
        old = SeededWorld.from_dict({"system_name": "X", "seed_gen": 5, "evolution_stage": 2})
        self.assertEqual(old.stage_name, "Industrial")
        resolved = SeededWorld.from_dict({"system_name": "X", "seed_gen": 5, "evolution_stage": 3,
                                          "resolved": True})
        self.assertEqual(resolved.stage_name, STAGE_NAMES[-1])
        new = SeededWorld.from_dict({"system_name": "X", "seed_gen": 5, "arrival_gen": 9, "evolution_stage": 2})
        self.assertEqual(new.stage_name, "Self-sustaining")


class HabitabilityEdgeCasesTest(unittest.TestCase):
    def test_short_lived_and_substellar_types_are_ruled_out(self):
        for kind in ("B2V", "O9V", "L7.5", "T4.5", "Y0"):
            self.assertEqual(habitability_weight(kind), 0.0, kind)

    def test_unparseable_type_is_neutral(self):
        self.assertEqual(habitability_weight("Q9"), 0.5)
        self.assertEqual(habitability_weight(None), 1.0)

    def test_extinct_age_clamps_for_very_distant_systems(self):
        from src.legacy_of_stars_v3 import StarSystem
        for _ in range(50):
            StarSystem("Far", 6000.0, "G2V")  # must not raise


class MirrorSpawnTest(unittest.TestCase):
    def test_mirror_skips_evolved_stars_without_cataloguing_them(self):
        p = program()
        for name in ("Pollux", "Arcturus", "Vega"):
            p.star_systems.pop(name, None)
        p.undiscovered = ["Pollux", "Arcturus", "Vega"]
        before = p.stats["systems_discovered"]
        system = p._spawn_mirror_system()
        self.assertEqual(system.name, "Vega")
        self.assertEqual(p.undiscovered, ["Pollux", "Arcturus"])
        self.assertNotIn("Pollux", p.star_systems)
        self.assertEqual(p.stats["systems_discovered"], before + 1)


class StaleInfoAttackTest(unittest.TestCase):
    def test_info_attack_from_a_source_that_turned_friendly_is_discarded(self):
        p = program()
        target = next(iter(p.star_systems.values()))
        target.has_civilization = True
        target._roll_civilization()
        target.timeline = None   # hand-written: static, so every frame reads these fields
        target.is_extinct = False
        target.true_strategy = "LB"
        p.pending_info_attacks.append([target.name, p.generation])
        p._deliver_pending_info_attacks()
        self.assertEqual(p.stats["info_attacks"], 0)
        self.assertEqual(p.pending_info_attacks, [])


if __name__ == "__main__":
    unittest.main()
