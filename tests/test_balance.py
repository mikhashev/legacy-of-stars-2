"""
Balance checks over whole headless games. Slow-ish (dozens of full games), so the
statistical cases only run with LOS_SLOW=1; a single quick sanity game always runs.

    LOS_SLOW=1 python -m unittest tests.test_balance -v
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

SLOW = os.getenv("LOS_SLOW") == "1"


class QuickBalanceTest(unittest.TestCase):
    def test_integration_player_survives_past_grace_period(self):
        result = run_headless(seed=2024, strategy="integration", max_gen=120)
        self.assertIsNone(result["exception"])
        self.assertGreater(result["generations"], 30)


@unittest.skipUnless(SLOW, "set LOS_SLOW=1 to run the statistical balance checks")
class StatisticalBalanceTest(unittest.TestCase):
    SEEDS = range(500, 512)

    def test_engaged_games_reach_a_victory(self):
        wins = 0
        for seed in self.SEEDS:
            result = run_headless(seed=seed, strategy="integration", max_gen=120)
            self.assertIsNone(result["exception"])
            if result["victory"] or result["philosophical_victory"]:
                wins += 1
        self.assertGreaterEqual(wins, len(self.SEEDS) // 2, f"only {wins} of {len(self.SEEDS)} engaged games won")

    def test_integration_players_outlive_neglectful_ones(self):
        integrated = [run_headless(seed=s, strategy="integration", max_gen=150)["generations"] for s in self.SEEDS]
        neglectful = [run_headless(seed=s, strategy="neglect", max_gen=150)["generations"] for s in self.SEEDS]
        self.assertGreater(sum(integrated) / len(integrated), sum(neglectful) / len(neglectful) + 20)
        self.assertLess(max(neglectful), 150, "a player who ignores integration should not survive to the cap")

    def test_no_game_ends_before_generation_20_by_itself(self):
        for seed in self.SEEDS:
            result = run_headless(seed=seed, strategy="cautious", max_gen=60)
            self.assertGreaterEqual(result["generations"], 20, result["end_reason"])


if __name__ == "__main__":
    unittest.main()
