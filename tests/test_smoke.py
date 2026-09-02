"""
Smoke test: complete headless games must finish without raising.

This is the acceptance test for the crash fixes; it exercises every subsystem
(messaging, attacks, research, doctrines, swan songs, philosophical events)
through scripts/auto_playtest.py.
"""
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for extra in (ROOT, ROOT / "scripts"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))
os.environ.setdefault("LOS_OFFLINE", "1")

from auto_playtest import run_headless  # noqa: E402


class SmokeTest(unittest.TestCase):
    def test_headless_games_complete_without_exceptions(self):
        for seed, strategy in ((1, "balanced"), (2, "aggressive"), (3, "cautious")):
            with self.subTest(seed=seed, strategy=strategy):
                result = run_headless(seed=seed, strategy=strategy, max_gen=80)
                self.assertIsNone(result["exception"])
                self.assertGreaterEqual(result["generations"], 2)
                self.assertTrue(result["end_reason"])


if __name__ == "__main__":
    unittest.main()
