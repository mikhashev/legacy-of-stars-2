"""
AI Strategic Advisor: unlock, once-per-generation rule, rule-based briefing and LLM path.
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

from src.ai_strategic_advisor import AIStrategicAdvisor  # noqa: E402
from src.legacy_of_stars_v3 import CivilizationStage, ContactProgram  # noqa: E402

RANDOM = "src.legacy_of_stars_v3.random.random"


def unlocked_program(seed=61):
    p = ContactProgram(seed=seed, offline=True)
    p.generation = 4
    for tech_id in ("seti_at_home", "ai_pattern_recognition", "ai_strategic_advisor"):
        p.research_points = 10000
        p.research_tech(tech_id)
        assert p.technologies[tech_id].researched, p.message
    return p


class AdvisorUnlockTest(unittest.TestCase):
    def test_locked_by_default(self):
        p = ContactProgram(seed=61, offline=True)
        self.assertFalse(p.ai_advisor_unlocked)
        self.assertNotIn("consult_advisor", [a.id for a in p.available_actions()])
        p.consult_advisor()
        self.assertIn("not yet unlocked", p.message.lower())

    def test_unlock_and_once_per_generation(self):
        p = unlocked_program()
        self.assertTrue(p.ai_advisor_unlocked)
        self.assertIn("consult_advisor", [a.id for a in p.available_actions()])
        p.consult_advisor()
        self.assertTrue(p.advisor_consulted_this_gen)
        self.assertIn("AI STRATEGIC BRIEFING", p.message)
        self.assertIn("THREAT ASSESSMENT", p.message)
        p.consult_advisor()
        self.assertIn("already consulted", p.message.lower())
        with mock.patch(RANDOM, return_value=0.99):
            p.advance_generation()
        self.assertFalse(p.advisor_consulted_this_gen)
        p.consult_advisor()
        self.assertTrue(p.advisor_consulted_this_gen)


class BriefingContentTest(unittest.TestCase):
    def _staged_program(self):
        p = unlocked_program(seed=62)
        systems = list(p.star_systems.values())
        for system in systems:
            system.has_civilization = False
            system.true_strategy = None
        friend, silent, hostile = systems[0], systems[1], systems[2]
        for system, strategy in ((friend, "LB"), (silent, "L"), (hostile, "LA")):
            system.has_civilization = True
            system.is_extinct = False
            system.true_strategy = strategy
            system.civilization_stage = CivilizationStage.DIGITAL
            system.knowledge = 40
        friend.received_messages.append("Friendly response")
        silent.messages_sent.append(("Anyone?", 1))
        p.action_points = 3
        p.send_message(hostile.name, "Hello")
        p.public_support = 25
        return p, friend, silent, hostile

    def test_context_and_rule_based_briefing(self):
        p, friend, silent, hostile = self._staged_program()
        context = p.ai_advisor._build_context(p)
        self.assertIn(f"Generation {p.generation}", context)
        self.assertIn("Public Support: 25%", context)
        self.assertIn("ACTIVE THREATS: 1", context)
        self.assertIn(friend.name, context)
        self.assertIn(silent.name, context)
        self.assertIn("VICTORY PROGRESS: 1/3 contacts", context)

        briefing = p.ai_advisor.analyze_game_state(p)
        for section in ("THREAT ASSESSMENT", "RESOURCE STATUS", "SYSTEM NOTES", "INTEGRATION", "RECOMMENDED ACTIONS", "VICTORY PROGRESS"):
            self.assertIn(section, briefing)
        self.assertIn(hostile.name, briefing)
        self.assertIn("CRITICAL: Public support", briefing)
        self.assertIn("grace period", briefing)

    def test_system_risk_assessments(self):
        p, friend, silent, hostile = self._staged_program()
        advisor = p.ai_advisor
        self.assertIn("Responded", advisor.get_system_risk_assessment(p, friend.name))
        self.assertIn("SUSPICIOUS", advisor.get_system_risk_assessment(p, silent.name))
        empty = list(p.star_systems.values())[3]
        empty.knowledge = 30
        self.assertIn("No civilization detected", advisor.get_system_risk_assessment(p, empty.name))
        unknown = list(p.star_systems.values())[4]
        unknown.knowledge = 0
        self.assertIn("Unknown", advisor.get_system_risk_assessment(p, unknown.name))
        self.assertEqual(advisor.get_system_risk_assessment(p, "Nowhere"), "System not found.")

    def test_llm_path_and_fallback(self):
        p = unlocked_program(seed=63)
        fake_ai = mock.Mock()
        fake_ai.is_available.return_value = True
        fake_ai.generate_text.return_value = "1. THREAT ASSESSMENT: all quiet."
        advisor = AIStrategicAdvisor(fake_ai)
        text = advisor.analyze_game_state(p)
        self.assertIn("all quiet", text)
        self.assertIn("AI STRATEGIC BRIEFING", text)
        fake_ai.generate_text.return_value = None
        fallback = advisor.analyze_game_state(p)
        self.assertIn("RECOMMENDED ACTIONS", fallback)
        fake_ai.generate_text.side_effect = RuntimeError("boom")
        self.assertIn("RECOMMENDED ACTIONS", advisor.analyze_game_state(p))


if __name__ == "__main__":
    unittest.main()
