"""
Core engine tests: the crash fixes and silent logic bugs from the v1.0 audit.
"""
import contextlib
import io
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("LOS_OFFLINE", "1")

from src.game_interface import GameInterface  # noqa: E402
from src.legacy_of_stars_v3 import CivilizationStage, ContactProgram  # noqa: E402

RANDOM = "src.legacy_of_stars_v3.random.random"


def make_program(seed=1):
    return ContactProgram(seed=seed, offline=True)


def research_chain(program, *tech_ids):
    """Research technologies in order with unlimited RP, choosing doctrine option 0 when asked."""
    for tech_id in tech_ids:
        program.research_points = 100000
        needs_doctrine = program.research_tech(tech_id)
        assert program.technologies[tech_id].researched, f"{tech_id}: {program.message}"
        if needs_doctrine:
            program.choose_doctrine(tech_id, 0)


class GracePeriodTest(unittest.TestCase):
    def test_no_integration_penalty_before_generation_30(self):
        p = make_program(seed=1)
        start = p.public_support
        with mock.patch(RANDOM, return_value=0.99):  # no random events
            for _ in range(5):
                p.advance_generation()
        self.assertFalse(p.game_over)
        # Only the natural 0.5/gen decay may apply; the -10/gen crisis penalty must not.
        self.assertGreaterEqual(p.public_support, start - 5 * 0.5 - 0.01)

    def test_penalty_applies_after_grace_period_when_integration_is_low(self):
        p = make_program(seed=1)
        p.generation = 31
        support = p.public_support = 80
        with mock.patch(RANDOM, return_value=0.99):
            p.advance_generation()
        self.assertLess(p.public_support, support - 9)


class ResearchEconomyTest(unittest.TestCase):
    def test_passive_rp_counted_once(self):
        p = make_program(seed=2)
        research_chain(p, "seti_at_home")
        p.research_points = 0
        funding_before = p.funding
        with mock.patch(RANDOM, return_value=0.99):
            p.advance_generation()
        passives = sum(t.passive_rp for t in p.technologies.values() if t.researched)
        self.assertGreaterEqual(passives, 15)  # SETI@Home is among them
        expected = 20 + funding_before / 5 + passives  # funding-based income + research infrastructure
        self.assertAlmostEqual(p.research_points, expected, places=5)

    def test_tech_level_follows_highest_researched_tier(self):
        p = make_program(seed=2)
        self.assertEqual(p.tech_level, 1)
        research_chain(p, "seti_at_home")
        self.assertEqual(p.tech_level, 2)
        with self.assertRaises(AttributeError):
            p.tech_level = 5

    def test_no_literal_backslash_n_in_research_messages(self):
        p = make_program(seed=2)
        p.generation = 40
        p.integration.integration_level = 1.0
        progress = True
        while progress:
            progress = False
            for tech in list(p.available_technologies()):
                p.research_points = 100000
                needs_doctrine = p.research_tech(tech.id)
                self.assertTrue(tech.researched, p.message)
                self.assertNotIn("\\" + "n", p.message, tech.id)
                if needs_doctrine:
                    p.choose_doctrine(tech.id, 0)
                progress = True
        self.assertTrue(all(t.researched for t in p.technologies.values()))


class DoctrineTest(unittest.TestCase):
    def test_all_doctrine_choices_have_options(self):
        p = make_program(seed=3)
        with_doctrine = [t for t in p.technologies.values() if t.doctrine_choice]
        self.assertTrue(with_doctrine)
        for tech in with_doctrine:
            options = tech.doctrine_choice.get("options")
            self.assertTrue(options, tech.id)
            for option in options:
                self.assertIn("name", option)
                self.assertIn("effects", option)
        self.assertIsNone(p.technologies["dark_forest_protocol"].doctrine_choice)

    def test_choose_doctrine_applies_option_effects(self):
        p = make_program(seed=3)
        p.generation = 10
        research_chain(p, "seti_at_home", "ai_pattern_recognition", "bio_engineering")
        p.research_points = 100000
        p.public_support = 80
        needs_doctrine = p.research_tech("genetic_pacification")
        self.assertTrue(needs_doctrine)
        evidence_before = p.fermi_evidence["great_filter_evidence"]
        p.choose_doctrine("genetic_pacification", 1)  # Mandatory Global Edit
        self.assertAlmostEqual(p.integration.integration_level, 0.5)
        self.assertEqual(p.fermi_evidence["great_filter_evidence"], evidence_before + 2)
        self.assertEqual(p.public_support, 55)
        self.assertIn("Mandatory Global Edit", p.active_doctrines)
        self.assertEqual(p.technologies["genetic_pacification"].chosen_doctrine, "Mandatory Global Edit")

    def test_consciousness_upload_integration_applied_once(self):
        p = make_program(seed=3)
        p.generation = 30
        p.integration.integration_level = 0.4  # Tier 5 requires 40% integration
        research_chain(p, "seti_at_home", "ai_pattern_recognition", "bio_engineering", "ai_strategic_advisor",
                       "neural_interface", "arecibo_telescope", "deep_space_network", "kepler_database",
                       "technosignature_catalog", "dyson_sphere_detection", "stellar_engineering",
                       "post_biological_transition")
        before = p.integration.integration_level
        research_chain(p, "consciousness_upload")
        self.assertAlmostEqual(p.integration.integration_level, min(1.0, before + 0.6))


class AttackTest(unittest.TestCase):
    def _hostile_program(self):
        p = make_program(seed=4)
        for system in p.star_systems.values():
            system.has_civilization = False
            system.true_strategy = None
        target = next(iter(p.star_systems.values()))
        target.has_civilization = True
        target.is_extinct = False
        target.true_strategy = "LA"
        target.distance = 10.0
        target.civilization_stage = CivilizationStage.DIGITAL
        target.deception_level = 0.0
        return p, target

    def test_passive_laser_sail_detection_creates_warning_once(self):
        p, target = self._hostile_program()
        with mock.patch(RANDOM, return_value=0.0), \
                mock.patch.object(p.leakage_system, "determine_attack_type", return_value="laser_sail"):
            p.advance_generation()
            self.assertEqual(len(p.pending_attack_warnings), 1)
            warning = p.pending_attack_warnings[0]
            self.assertEqual(warning.attack_type, "laser_sail_probe")
            self.assertIs(warning.source, target)
            self.assertTrue(target.has_detected_earth)
            self.assertGreater(warning.arrival_gen, p.generation)
            self.assertTrue(any("HOSTILE LAUNCH" in e.text for e in p.drain_events()))
            p.advance_generation()  # no second detection of the same system
            self.assertEqual(len(p.pending_attack_warnings), 1)

    def test_passive_fusion_detection_creates_warning(self):
        p, target = self._hostile_program()
        with mock.patch(RANDOM, return_value=0.0), \
                mock.patch.object(p.leakage_system, "determine_attack_type", return_value="fusion"):
            p.advance_generation()
        self.assertEqual(p.pending_attack_warnings[0].attack_type, "fusion_strike")

    def test_message_to_hostile_civ_schedules_attack(self):
        p, target = self._hostile_program()
        p.send_message(target.name, "Hello")
        self.assertEqual(len(p.pending_attack_warnings), 1)
        self.assertEqual(p.pending_attack_warnings[0].arrival_gen, p.attack_arrival_generation(target))
        # 10 LY: message out at c (10 years) + fleet back at 0.1c (100 years) = 110 years -> 5 generations
        self.assertEqual(p.pending_attack_warnings[0].arrival_gen, p.generation + 5)
        self.assertNotIn("TODO", p.message)

    def test_fleets_never_arrive_before_two_generations(self):
        p, target = self._hostile_program()
        target.distance = 1.0
        self.assertEqual(p.attack_arrival_generation(target), p.generation + 2)

    def test_early_warning_network_adds_preparation_time(self):
        p, target = self._hostile_program()
        p.warning_time_bonus = 2
        p.send_message(target.name, "Hello")
        self.assertEqual(p.pending_attack_warnings[0].arrival_gen, p.attack_arrival_generation(target) + 2)


class StarSystemTest(unittest.TestCase):
    def test_defaults(self):
        p = make_program(seed=5)
        for system in p.star_systems.values():
            self.assertFalse(system.is_seeded)
            self.assertFalse(system.has_detected_earth)
            self.assertFalse(system.is_wow_source)


class AlienReplyTest(unittest.TestCase):
    def test_offline_replies_are_templates_not_errors(self):
        p = make_program(seed=6)
        system = next(iter(p.star_systems.values()))
        system.has_civilization = True
        system.is_extinct = False
        system.civilization_stage = CivilizationStage.DIGITAL
        for strategy in ("LB", "LR", "LBA"):
            text = p._compose_alien_reply(system, strategy, "Hello")
            self.assertTrue(text)
            self.assertNotIn("AI Error", text)
            self.assertNotIn("{", text)


class InterfaceTest(unittest.TestCase):
    def _play(self, program, inputs):
        ui = GameInterface(program)
        out = io.StringIO()
        with mock.patch("builtins.input", side_effect=list(inputs)), contextlib.redirect_stdout(out):
            ui.play()
        return ui, out.getvalue()

    def test_minimal_session_advance_and_quit(self):
        p = make_program(seed=7)
        with mock.patch(RANDOM, return_value=0.99):
            ui, output = self._play(p, ["", "5", "5", "6", "y", ""])
        self.assertTrue(p.game_over)
        self.assertEqual(p.generation, 3)
        self.assertIn("Thank you for playing", output)

    def test_eof_ends_session_cleanly(self):
        p = make_program(seed=7)
        ui = GameInterface(p)
        with mock.patch("builtins.input", side_effect=EOFError), contextlib.redirect_stdout(io.StringIO()):
            ui.play()  # must not raise
        self.assertFalse(p.game_over)

    def test_philosophical_event_can_be_answered(self):
        p = make_program(seed=8)
        event = p.philosophical_events.events["expansion_instinct"]
        p.pending_philosophical_event = event
        ui = GameInterface(p)
        items = ui.build_menu()
        key = ui._current_keys["respond_event"]
        knowledge_before = p.knowledge_base
        with mock.patch("builtins.input", side_effect=["2"]), contextlib.redirect_stdout(io.StringIO()):
            ui.dispatch(key, items)
        self.assertIsNone(p.pending_philosophical_event)
        self.assertEqual(event.chosen_option, "Stay the Course")
        self.assertEqual(p.knowledge_base, knowledge_before + 15)

    def test_advance_is_blocked_while_event_pending(self):
        p = make_program(seed=8)
        p.pending_philosophical_event = p.philosophical_events.events["expansion_instinct"]
        ui = GameInterface(p)
        items = ui.build_menu()
        with contextlib.redirect_stdout(io.StringIO()):
            ui.dispatch("5", items)
        self.assertEqual(p.generation, 1)
        self.assertIn("philosophical", p.message.lower())

    def test_invalid_choice_lists_valid_keys(self):
        p = make_program(seed=8)
        ui = GameInterface(p)
        items = ui.build_menu()
        ui.dispatch("zzz", items)
        self.assertIn("Valid options", p.message)

    def test_doctrine_prompt_through_interface(self):
        p = make_program(seed=9)
        p.generation = 10
        research_chain(p, "seti_at_home", "ai_pattern_recognition", "bio_engineering")
        p.research_points = 100000
        ui = GameInterface(p)
        techs = p.available_technologies()
        index = next(i for i, t in enumerate(techs, 1) if t.id == "genetic_pacification")
        with mock.patch("builtins.input", side_effect=[str(index), "2"]), contextlib.redirect_stdout(io.StringIO()):
            ui.dispatch("4", ui.build_menu())
        self.assertEqual(p.technologies["genetic_pacification"].chosen_doctrine, "Mandatory Global Edit")

    def test_defensive_action_through_interface(self):
        p = make_program(seed=9)
        target = next(iter(p.star_systems.values()))
        target.has_civilization = True
        target.is_extinct = False
        target.true_strategy = "LA"
        target.civilization_stage = CivilizationStage.DIGITAL
        p.send_message(target.name, "Hello")
        ui = GameInterface(p)
        items = ui.build_menu()
        key = ui._current_keys["defend"]
        with mock.patch("builtins.input", side_effect=["1", "2"]), contextlib.redirect_stdout(io.StringIO()):
            ui.dispatch(key, items)
        self.assertIn("Evacuation", p.pending_attack_warnings[0].defensive_actions_taken)

    def test_opening_scenario_silent_and_reply(self):
        p = make_program(seed=10)
        ui = GameInterface(p)
        with mock.patch("builtins.input", side_effect=["2", ""]), contextlib.redirect_stdout(io.StringIO()):
            ui.run_opening_scenario()
        self.assertTrue(p.wow_signal.decided)
        self.assertFalse(p.wow_signal.wow_replied)
        self.assertEqual(p.wow_signal.attack_damage_reduction, 0.15)

        p2 = make_program(seed=10)
        rp = p2.research_points
        ui2 = GameInterface(p2)
        with mock.patch("builtins.input", side_effect=["x", "1", "3", ""]), contextlib.redirect_stdout(io.StringIO()):
            ui2.run_opening_scenario()
        self.assertTrue(p2.wow_signal.wow_replied)
        self.assertEqual(p2.research_points, rp + 100)
        self.assertTrue(p2.wow_signal.wow_reply_message)


if __name__ == "__main__":
    unittest.main()
