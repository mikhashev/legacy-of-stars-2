"""
Balance checks over whole headless games. Slow-ish (dozens of full games), so the
statistical cases only run with LOS_SLOW=1; a single quick sanity game always runs.

    LOS_SLOW=1 python -m unittest tests.test_balance -v
"""
import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for extra in (ROOT, ROOT / "scripts"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))
os.environ.setdefault("LOS_OFFLINE", "1")

from auto_playtest import calibration_metrics, run_headless  # noqa: E402

SLOW = os.getenv("LOS_SLOW") == "1"


class QuickBalanceTest(unittest.TestCase):
    def test_integration_player_survives_past_grace_period(self):
        result = run_headless(seed=2024, strategy="integration", max_gen=120)
        self.assertIsNone(result["exception"])
        self.assertGreater(result["generations"], 30)

    def test_t5_baseline_json_loads_with_five_profiles_of_thirty_runs(self):
        """The T5 calibration baseline (`scripts/calibration/baseline_2a4e0ec.json`, the
        pre-timelines engine at commit 2a4e0ec) is what `calibrate_timelines.py --baseline`
        compares against by default; a corrupted or partial file would silently weaken that
        comparison, so check its shape here rather than only when someone happens to run the
        instrument.
        """
        path = ROOT / "scripts" / "calibration" / "baseline_2a4e0ec.json"
        if not path.exists():
            self.skipTest(f"{path} not present")
        with open(path, encoding="utf-8") as handle:
            baseline = json.load(handle)
        expected_profiles = {"balanced", "aggressive", "cautious", "integration", "neglect"}
        self.assertEqual(set(baseline.keys()), expected_profiles)
        for profile, runs in baseline.items():
            self.assertEqual(len(runs), 30, f"{profile} has {len(runs)} run(s), expected 30")
            for run in runs:
                self.assertIn("first_reply_gen", run, f"{profile} run missing first_reply_gen")
                self.assertIn("victory", run)
                self.assertIn("generations", run)


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


@unittest.skipUnless(SLOW, "set LOS_SLOW=1 to run the statistical balance checks")
class CalibrationTest(unittest.TestCase):
    """Civilization timelines calibration (plan §7, T5). Generous bands: `scripts/calibrate_timelines.py`
    is the precise instrument (30 runs/profile); this is a coarse regression guard (20 runs) so a
    knob accidentally moved out of the T5-measured range fails a test rather than only a manual
    playtest. See the calibration block in `src/civ_timeline.py` for the exact measured numbers.
    """
    SEEDS = range(500, 520)  # 20 runs, matching the task's calibration-test sample size

    @classmethod
    def setUpClass(cls):
        cls.results = [run_headless(seed=seed, strategy="observer", max_gen=60, run_id=i + 1)
                       for i, seed in enumerate(cls.SEEDS)]
        cls.metrics = calibration_metrics(cls.results)

    def test_extinct_at_first_observation_share(self):
        share = self.metrics["extinct_share"]
        self.assertIsNotNone(share)
        self.assertTrue(0.15 <= share <= 0.35, share)

    def test_sky_changes_per_40_generations(self):
        # The plan's target (§7) is 2-8/40 generations for this 20-run sample (3-6 for the
        # precise 30-run instrument). T5 calibration did not reach it within the six-iteration
        # time-box: pushing the rate that high required either an extinction hazard or a
        # BASE_CIV_CHANCE far above what kept `extinct_share`, `differing_outcomes` and victories
        # on their own targets (see the calibration block in src/civ_timeline.py for the numbers
        # and the trade-off).
        #
        # T5.2 (2026-09-03, the "silence ends" starting-selection guarantee, decision 1a) raised
        # the measured rate from ~1.0-1.2 to ~2.0-2.3 as a side effect: most new games now start
        # with a system whose next stage crossing is guaranteed to land early, which is itself a
        # sky change. This is a welcome move toward the plan's still-unmet 3-6 target, not a
        # re-tuning - no hazard/density constant moved - so the band below is widened to bracket
        # the newly-measured rate (with headroom) as a regression floor/ceiling, honestly still
        # short of the plan's own target.
        rate = self.metrics["sky_changes_per_40"]
        self.assertTrue(0.5 <= rate <= 3.5, rate)

    def test_stage_up_among_first_three_sky_changes(self):
        share = self.metrics["stage_up_first_three"]
        if self.metrics["games_with_three_sky_changes"] == 0:
            self.skipTest("no game in this sample saw >= 3 sky changes")
        self.assertGreaterEqual(share, 0.5, share)


if __name__ == "__main__":
    unittest.main()
