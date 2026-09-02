"""
Integration Progress System: levels, thresholds, grace period and penalties.
"""
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("LOS_OFFLINE", "1")

from src.integration_progress import IntegrationProgress  # noqa: E402


class IntegrationProgressTest(unittest.TestCase):
    def test_initial_state(self):
        integration = IntegrationProgress()
        self.assertEqual(integration.integration_level, 0.0)
        self.assertEqual(integration.crisis_threshold, 0.3)
        self.assertEqual(integration.high_integration_threshold, 0.7)

    def test_integration_accumulates_and_caps(self):
        integration = IntegrationProgress()
        integration.add_integration(0.3, "Synthetic Biology")
        self.assertAlmostEqual(integration.integration_level, 0.3)
        integration.add_integration(0.4, "Neural Interface")
        self.assertAlmostEqual(integration.integration_level, 0.7)
        integration.add_integration(0.6, "Consciousness Upload")
        self.assertEqual(integration.integration_level, 1.0)
        self.assertEqual(len(integration.integration_events), 3)
        self.assertEqual(integration.integration_events[0]["source"], "Synthetic Biology")

    def test_filter_risk_modifier_by_level_after_grace_period(self):
        integration = IntegrationProgress()
        self.assertEqual(integration.get_filter_risk_modifier(40), 1.2)
        integration.add_integration(0.2, "Partial")
        self.assertEqual(integration.get_filter_risk_modifier(40), 1.2)
        integration.add_integration(0.3, "Medium")
        self.assertEqual(integration.get_filter_risk_modifier(40), 1.0)
        integration.add_integration(0.3, "High")
        self.assertEqual(integration.get_filter_risk_modifier(40), 0.7)

    def test_grace_period_suppresses_every_penalty(self):
        integration = IntegrationProgress()
        for generation in (1, 15, 30):
            self.assertEqual(integration.get_filter_risk_modifier(generation), 1.0)
            self.assertEqual(integration.get_support_penalty(generation), 0.0)
            self.assertEqual(integration.get_research_efficiency(generation), 1.0)
        self.assertEqual(integration.get_support_penalty(31), -10.0)
        self.assertEqual(integration.get_research_efficiency(31), 0.85)

    def test_tier5_unlocks_at_forty_percent(self):
        integration = IntegrationProgress()
        self.assertFalse(integration.can_research_tier5())
        integration.add_integration(0.4, "Test")
        self.assertTrue(integration.can_research_tier5())

    def test_status_labels(self):
        integration = IntegrationProgress()
        self.assertEqual(integration.get_integration_status(10)["status"], "CRISIS (GRACE PERIOD)")
        self.assertEqual(integration.get_integration_status(40)["status"], "CRISIS")
        integration.add_integration(0.5, "Test")
        self.assertEqual(integration.get_integration_status(40)["status"], "TRANSITIONING")
        integration.add_integration(0.3, "Test 2")
        status = integration.get_integration_status(40)
        self.assertEqual(status["status"], "INTEGRATED")
        self.assertEqual(status["milestone_count"], 2)
        self.assertIn("High integration benefits", integration.get_display_message(40))

    def test_round_trip(self):
        integration = IntegrationProgress()
        integration.add_integration(0.45, "Test")
        restored = IntegrationProgress.from_dict(integration.to_dict())
        self.assertAlmostEqual(restored.integration_level, 0.45)
        self.assertEqual(restored.integration_events, integration.integration_events)


if __name__ == "__main__":
    unittest.main()
