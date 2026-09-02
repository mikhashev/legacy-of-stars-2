"""
Phase 3 mechanics: events, Fermi evidence sources, Genesis, dead flags wired, mirror contact, view_state.
"""
import json
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

RANDOM = "src.legacy_of_stars_v3.random.random"
GENESIS_RANDOM = "src.genesis_project.random.random"


def make_program(seed=1):
    return ContactProgram(seed=seed, offline=True)


def make_living(system, strategy="LB", stage=CivilizationStage.DIGITAL, civ_type="biological_pure"):
    system.has_civilization = True
    system.is_extinct = False
    system.has_swan_song = False
    system.true_strategy = strategy
    system.civilization_stage = stage
    system.civilization_type = civ_type
    system.deception_level = 0.0
    return system


def quiet_galaxy(program):
    """Remove every civilization so random rolls cannot trigger contacts or attacks."""
    for system in program.star_systems.values():
        system.has_civilization = False
        system.true_strategy = None
        system.is_extinct = False
        system.has_swan_song = False


def research_all(program, *tech_ids):
    for tech_id in tech_ids:
        program.research_points = 100000
        needs_doctrine = program.research_tech(tech_id)
        assert program.technologies[tech_id].researched, f"{tech_id}: {program.message}"
        if needs_doctrine:
            program.choose_doctrine(tech_id, 0)


class EventsTest(unittest.TestCase):
    def test_generation_emits_events_and_drain_clears(self):
        p = make_program(seed=1)
        quiet_galaxy(p)
        with mock.patch(RANDOM, return_value=0.99):
            p.advance_generation()
        events = p.drain_events()
        self.assertTrue(events)
        self.assertEqual(events[0].kind, "generation_start")
        self.assertEqual(p.drain_events(), [])

    def test_info_attack_emits_event_and_evidence(self):
        p = make_program(seed=1)
        name = next(iter(p.star_systems))
        p.public_support = 100
        p.funding = 100
        p.process_information_attack(name)
        self.assertEqual(p.fermi_evidence["dark_forest_evidence"], 1)
        self.assertEqual(p.stats["info_attacks"], 1)
        kinds = [e.kind for e in p.drain_events()]
        self.assertIn("info_attack", kinds)
        self.assertIn("fermi_evidence", kinds)
        self.assertFalse(p.game_over)

    def test_defunding_sets_game_over_reason(self):
        p = make_program(seed=1)
        quiet_galaxy(p)
        p.public_support = 5
        with mock.patch(RANDOM, return_value=0.99):
            p.advance_generation()
        self.assertTrue(p.game_over)
        self.assertIn("defunded", p.game_over_reason)
        self.assertTrue(any(e.kind == "game_over" for e in p.drain_events()))


class ResponseEvidenceTest(unittest.TestCase):
    def test_first_and_repeat_responses(self):
        p = make_program(seed=2)
        quiet_galaxy(p)
        system = make_living(next(iter(p.star_systems.values())), "LB")
        system.pending_responses.append(("Hello Earth", p.generation + 1))
        with mock.patch(RANDOM, return_value=0.99):
            p.advance_generation()
        self.assertEqual(p.fermi_evidence["cooperation_evidence"], 2)
        self.assertEqual(system.received_messages, ["Hello Earth"])
        self.assertTrue(any(e.kind == "response_received" for e in p.drain_events()))
        system.pending_responses.append(("Again", p.generation + 1))
        with mock.patch(RANDOM, return_value=0.99):
            p.advance_generation()
        self.assertEqual(p.fermi_evidence["cooperation_evidence"], 3)
        self.assertEqual(p.stats["responses_received"], 2)
        # a third reply from the same civilization is welcome but no longer counts as new evidence
        system.pending_responses.append(("And again", p.generation + 1))
        with mock.patch(RANDOM, return_value=0.99):
            p.advance_generation()
        self.assertEqual(p.fermi_evidence["cooperation_evidence"], 3)
        self.assertEqual(len(system.received_messages), 3)

    def test_hostile_civilization_launches_only_one_fleet(self):
        p = make_program(seed=2)
        quiet_galaxy(p)
        hostile = make_living(next(iter(p.star_systems.values())), "LA")
        p.action_points = 3
        p.send_message(hostile.name, "Hello")
        p.send_message(hostile.name, "Hello again")
        p.send_message(hostile.name, "Anyone there?")
        self.assertEqual(len(p.pending_attack_warnings), 1)
        self.assertEqual(p.fermi_evidence["dark_forest_evidence"], 1)
        self.assertIn("No response detected", p.message)

    def test_contact_victory_after_three_responders(self):
        p = make_program(seed=2)
        quiet_galaxy(p)
        systems = list(p.star_systems.values())[:3]
        for s in systems:
            make_living(s, "LB")
            s.received_messages.append("hi")
        with mock.patch(RANDOM, return_value=0.99):
            p.advance_generation()
        self.assertTrue(p.victory)
        self.assertIn("First Contact Network", p.achievements)
        self.assertFalse(p.game_over)


class GenesisTest(unittest.TestCase):
    CHAIN = ("seti_at_home", "ai_pattern_recognition", "arecibo_telescope", "deep_space_network", "optical_seti",
             "breakthrough_listen", "solar_sail_technology", "laser_sail_propulsion", "kepler_database",
             "technosignature_catalog", "bio_engineering", "synthetic_biology", "genesis_bioprogramming")

    def _unlocked_program(self):
        p = make_program(seed=3)
        quiet_galaxy(p)
        p.generation = 10
        research_all(p, *self.CHAIN)
        return p

    def test_genesis_unlocks_via_technology_and_costs_an_action_point(self):
        p = self._unlocked_program()
        self.assertTrue(p.genesis.unlocked)
        self.assertIn("genesis_seed", [a.id for a in p.available_actions()])
        target = next(iter(p.star_systems.values()))
        p.research_points, p.funding, p.action_points = 1000, 80, 2
        ok, msg = p.genesis.seed_world(p, target)
        self.assertTrue(ok, msg)
        self.assertEqual(p.action_points, 1)
        self.assertEqual(p.research_points, 500)
        self.assertTrue(target.is_seeded)
        ok2, msg2 = p.genesis.seed_world(p, list(p.star_systems.values())[1])
        self.assertFalse(ok2)
        self.assertIn("one world per generation", msg2)

    def test_ally_outcome_creates_contact(self):
        p = self._unlocked_program()
        target = next(iter(p.star_systems.values()))
        p.research_points, p.funding, p.action_points = 1000, 80, 2
        p.genesis.seed_world(p, target)
        world = p.genesis.seeded_worlds[target.name]
        world.evolution_stage = 2
        world.seed_gen = p.generation - 40
        with mock.patch(GENESIS_RANDOM, return_value=0.9):
            p.genesis.advance_generation(p)
        self.assertTrue(target.has_civilization)
        self.assertEqual(target.true_strategy, "LB")
        self.assertEqual(len(target.received_messages), 1)
        self.assertEqual(p.fermi_evidence["cooperation_evidence"], 2)
        self.assertIn("Parents of the Stars", p.achievements)
        self.assertIn(target, p.contacted_systems())

    def test_hostile_outcome_schedules_attack(self):
        p = self._unlocked_program()
        target = next(iter(p.star_systems.values()))
        p.research_points, p.funding, p.action_points = 1000, 80, 2
        p.genesis.seed_world(p, target)
        world = p.genesis.seeded_worlds[target.name]
        world.evolution_stage = 2
        world.seed_gen = p.generation - 40
        with mock.patch(GENESIS_RANDOM, return_value=0.1):
            p.genesis.advance_generation(p)
        self.assertEqual(target.true_strategy, "LA")
        self.assertEqual(len(p.pending_attack_warnings), 1)
        self.assertEqual(p.pending_attack_warnings[0].attack_type, "genesis_fleet")
        self.assertEqual(p.fermi_evidence["dark_forest_evidence"], 3)  # +2 hostile creation, +1 launch
        self.assertEqual(p.genesis.to_dict()["worlds"][0]["outcome"], "hostile")


class ActionPointModifierTest(unittest.TestCase):
    def test_modifier_survives_recalculation(self):
        p = make_program(seed=4)
        before = p.max_action_points
        p.ap_modifier = -1
        p.calculate_ap()
        self.assertEqual(p.max_action_points, max(1, before - 1))

    def test_dual_program_choice_sets_modifier(self):
        p = make_program(seed=4)
        event = p.philosophical_events.events["expansion_instinct"]
        p.pending_philosophical_event = event
        p.handle_philosophical_event_choice(2)  # Dual Program: -1 AP
        self.assertEqual(p.ap_modifier, -1)
        self.assertIn("Humanity pursues both paths", p.message)
        self.assertEqual(p.fermi_evidence["great_filter_evidence"], 1)
        self.assertEqual(p.stats["events_resolved"], 1)


class TierFiveGateTest(unittest.TestCase):
    def test_tier5_locked_until_integration(self):
        p = make_program(seed=5)
        tech = p.technologies["hybrid_civilization"]
        self.assertIsNotNone(p.tech_lock_reason(tech))
        p.integration.integration_level = 0.4
        self.assertIsNone(p.tech_lock_reason(tech))

    def test_research_refuses_locked_tech(self):
        p = make_program(seed=5)
        p.generation = 30
        tech = p.technologies["hybrid_civilization"]
        for prereq in tech.prerequisites:
            p.technologies[prereq].researched = True
        p.research_points = 100000
        self.assertFalse(p.research_tech("hybrid_civilization"))
        self.assertIn("locked", p.message)
        self.assertFalse(tech.researched)

    def test_low_integration_reduces_research_income_after_grace(self):
        p = make_program(seed=5)
        quiet_galaxy(p)
        p.generation = 31
        p.research_points = 0
        p.public_support = 80
        funding = p.funding
        with mock.patch(RANDOM, return_value=0.99):
            p.advance_generation()
        passives = sum(t.passive_rp for t in p.technologies.values() if t.researched)
        expected = (20 + funding / 5 + passives) * 0.85  # 15% efficiency penalty
        self.assertAlmostEqual(p.research_points, expected, places=5)


class AttackResolutionTest(unittest.TestCase):
    def _attack(self, p, stage=CivilizationStage.INTERPLANETARY, attack_type="fleet", defense=1.0):
        quiet_galaxy(p)
        source = make_living(next(iter(p.star_systems.values())), "LA", stage)
        p.public_support = 100
        p.funding = 100
        warning = p._schedule_attack(source, p.generation, attack_type, announce=False)
        warning.defense_multiplier = defense
        p._resolve_attacks()
        return source

    def test_wow_silence_reduces_attack_damage(self):
        p = make_program(seed=6)
        self._attack(p)  # INTERPLANETARY (3) vs tech 1 -> gap 2 -> base 50 support (devastating, but backup below)
        # devastating without defenses -> annihilation
        self.assertTrue(p.game_over)

        p2 = make_program(seed=6)
        p2.has_backup_colonies = True
        self._attack(p2, stage=CivilizationStage.DIGITAL)  # gap 1 -> base 40
        self.assertAlmostEqual(p2.public_support, 60)

        p3 = make_program(seed=6)
        p3.wow_signal.stay_silent()
        self._attack(p3, stage=CivilizationStage.DIGITAL)
        self.assertAlmostEqual(p3.public_support, 100 - int(40 * 0.85))

    def test_von_neumann_bonus_only_for_probes(self):
        p = make_program(seed=6)
        p.von_neumann_defense_bonus = 0.7
        self._attack(p, stage=CivilizationStage.DIGITAL, attack_type="laser_sail_probe")
        self.assertAlmostEqual(p.public_support, 100 - int(40 * 0.7))
        p2 = make_program(seed=6)
        p2.von_neumann_defense_bonus = 0.7
        self._attack(p2, stage=CivilizationStage.DIGITAL, attack_type="fleet")
        self.assertAlmostEqual(p2.public_support, 60)

    def test_strong_defense_survives_devastating_attack(self):
        p = make_program(seed=7)
        self._attack(p, stage=CivilizationStage.INTERSTELLAR, defense=0.5)
        self.assertFalse(p.game_over)
        self.assertIn("Survivor", p.achievements)
        self.assertEqual(p.stats["attacks_survived"], 1)
        p2 = make_program(seed=7)
        self._attack(p2, stage=CivilizationStage.INTERSTELLAR, defense=1.0)
        self.assertTrue(p2.game_over)
        self.assertIn("annihilated", p2.game_over_reason)


class MirrorContactTest(unittest.TestCase):
    def test_friendly_mirror_adds_system_and_pending_reply(self):
        p = make_program(seed=8)
        before = len(p.star_systems)
        with mock.patch(RANDOM, return_value=0.1):
            text = p.resolve_mirror_contact()
        self.assertEqual(len(p.star_systems), before + 1)
        new = list(p.star_systems.values())[-1]
        self.assertEqual(new.true_strategy, "LB")
        self.assertEqual(len(new.pending_responses), 1)
        self.assertIn("catalogued", text)

    def test_hostile_mirror_schedules_attack(self):
        p = make_program(seed=8)
        with mock.patch(RANDOM, return_value=0.9):
            text = p.resolve_mirror_contact()
        self.assertEqual(p.pending_attack_warnings[0].attack_type, "mirror_fleet")
        self.assertIn("fleet", text.lower())

    def test_mirror_event_choice_triggers_contact(self):
        p = make_program(seed=8)
        event = p.philosophical_events.events["mirror_civilization"]
        p.pending_philosophical_event = event
        before = len(p.star_systems)
        with mock.patch(RANDOM, return_value=0.1):
            p.handle_philosophical_event_choice(0)  # Extend Contact
        self.assertEqual(len(p.star_systems), before + 1)
        self.assertIn("catalogued", p.message)


class SendMessageGatesTest(unittest.TestCase):
    def test_post_biological_gate(self):
        p = make_program(seed=9)
        system = make_living(next(iter(p.star_systems.values())), "LB", CivilizationStage.POST_BIOLOGICAL)
        ap = p.action_points
        p.send_message(system.name, "Hello")
        self.assertEqual(p.action_points, ap)
        self.assertIn("Post-Biological", p.message)
        p.can_contact_post_biological = True
        p.send_message(system.name, "Hello")
        self.assertEqual(p.action_points, ap - 1)
        self.assertEqual(p.stats["messages_sent"], 1)

    def test_laser_sails_transmission_bonus(self):
        p = make_program(seed=9)
        self.assertEqual(p._transmission_bonus(), 0.0)
        p.has_laser_sails = True
        self.assertEqual(p._transmission_bonus(), 0.10)


class RiskGrowthTest(unittest.TestCase):
    def test_self_destruct_risk_depends_on_integration(self):
        p = make_program(seed=11)
        p.generation = 40
        p.self_destruct_risk = 0.02
        p.integration.integration_level = 0.0
        self.assertAlmostEqual(p._next_self_destruct_risk(), 0.0215)
        p.integration.integration_level = 0.5
        self.assertAlmostEqual(p._next_self_destruct_risk(), 0.0205)
        p.integration.integration_level = 0.8
        self.assertAlmostEqual(p._next_self_destruct_risk(), 0.019)
        p.self_destruct_risk = 0.5
        self.assertAlmostEqual(p._next_self_destruct_risk(), p.RISK_CAP)
        p.self_destruct_risk = 0.0
        self.assertAlmostEqual(p._next_self_destruct_risk(), p.RISK_FLOOR)

    def test_no_floor_during_grace_period(self):
        p = make_program(seed=11)
        p.generation = 5
        p.self_destruct_risk = 0.0
        self.assertAlmostEqual(p._next_self_destruct_risk(), 0.0005)


class ViewStateTest(unittest.TestCase):
    def test_view_state_is_json_and_hides_secrets(self):
        p = make_program(seed=10)
        make_living(next(iter(p.star_systems.values())), "LA")
        state = p.view_state()
        text = json.dumps(state)
        for secret in ("true_strategy", "deception_level", "is_wow_source", "has_detected_earth", "LA\"", "LBA\""):
            self.assertNotIn(secret, text)
        self.assertEqual(len(state["systems"]), len(p.star_systems))
        self.assertIn("actions", state)
        self.assertEqual(state["fermi_evidence"]["goal"], 15)
        self.assertEqual(state["status"]["tech_level"], 1)
        self.assertIsNone(state["pending_event"])

    def test_view_state_reflects_threats_and_events(self):
        p = make_program(seed=10)
        quiet_galaxy(p)
        source = make_living(next(iter(p.star_systems.values())), "LA")
        p.send_message(source.name, "Hi")
        p.pending_philosophical_event = p.philosophical_events.events["expansion_instinct"]
        state = p.view_state()
        self.assertEqual(len(state["threats"]), 1)
        self.assertEqual(state["threats"][0]["source"], source.name)
        self.assertEqual(state["pending_event"]["id"], "expansion_instinct")
        self.assertEqual(len(state["pending_event"]["choices"]), 3)


if __name__ == "__main__":
    unittest.main()
