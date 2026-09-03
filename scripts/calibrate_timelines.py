"""
Calibration instrument for the civilization timelines (plan T5, docs/plans/civilization_timelines_plan.md section 7).

It drives `scripts/auto_playtest.py` over N runs per profile and prints the metrics the plan
puts a target on, so a re-run reproduces the same numbers instead of eyeballing a playtest log:

    a) share of catalogued civilizations already extinct at first observation, per distance band
    b) sky-change events per game and per 40 generations
    c) share of messages to an inhabited target whose outcome the receipt frame decided
       differently from a static evaluation (died_in_flight / (replied + silent + died_in_flight))
    d) victories (contact or philosophical) per profile
    e) median generation of the first successful reply
    f) whether at least one of the first three sky changes is a stage advance

Usage:

    python scripts/calibrate_timelines.py --runs 30 --max-gen 60
    python scripts/calibrate_timelines.py --profiles observer --runs 30 --json out.json
    python scripts/calibrate_timelines.py --baseline baseline.json   # compare (d) and (e)

The baseline for (d) and (e) is the pre-T1 engine (commit 2a4e0ec) run with the same seeds; its
harness has no observer/talker profiles, so the comparison is made on the shared profiles only.
`--baseline` reads a JSON file of `{profile: [run summary, ...]}` produced by running the same
seeds against that commit (see the T5 report).
"""
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for extra in (ROOT, ROOT / "scripts"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))
os.environ.setdefault("LOS_OFFLINE", "1")

from auto_playtest import (  # noqa: E402
    DISTANCE_BANDS, STRATEGIES, calibration_metrics, run_headless)

# The profiles the plan fixes for the measurement, plus the shared ones the baseline also has.
DEFAULT_PROFILES = ("observer", "talker", "balanced", "cautious", "integration")
SHARED_PROFILES = ("balanced", "aggressive", "cautious", "integration", "neglect")

# The plan's targets, for the printed "target vs measured" column.
TARGETS = {
    "extinct_share": (0.20, 0.30),
    "sky_changes_per_40": (3.0, 6.0),      # the "observer" profile is the instrument
    "differing_outcomes": (0.10, 0.20),
}


def _pct(value):
    return "  n/a " if value is None else f"{value:6.1%}"


def run_profile(profile: str, runs: int, seed: int, max_gen: int, verbose: bool = True):
    """Play `runs` games of one profile with seeds `seed .. seed + runs - 1`."""
    results = []
    for index in range(runs):
        result = run_headless(seed + index, profile, max_gen, run_id=index + 1)
        results.append(result)
        if verbose:
            print(f"  {profile} seed {seed + index}: gen {result['generations']}, "
                  f"sky {result['sky_changes']}, "
                  f"reply {result['first_reply_gen'] or '-'}", flush=True)
    return results


def print_report(metrics_by_profile: dict, baseline_by_profile: dict = None) -> None:
    baseline_by_profile = baseline_by_profile or {}
    print("\n=== T5 CALIBRATION (plan section 7) ===")
    header = (f"{'Profile':<12}{'Games':<7}{'Extinct':<9}{'<=20':<8}{'20-60':<8}{'60-160':<9}"
              f"{'Sky/40':<8}{'Differ':<9}{'Wins':<7}{'Reply':<8}{'Stage3':<8}")
    print(header)
    print("-" * len(header))
    for profile, m in metrics_by_profile.items():
        bands = m["extinct_by_band"]
        reply = m["first_reply_median"]
        print(f"{profile:<12}{m['games']:<7}{_pct(m['extinct_share']):<9}"
              f"{_pct(bands['<=20 LY']['share']):<8}{_pct(bands['20-60 LY']['share']):<8}"
              f"{_pct(bands['60-160 LY']['share']):<9}"
              f"{m['sky_changes_per_40']:<8.2f}{_pct(m['differing_outcomes']):<9}"
              f"{m['victory_rate']:<7.0%}{(f'{reply:.0f}' if reply is not None else '-'):<8}"
              f"{_pct(m['stage_up_first_three']):<8}")
    print("\nTargets: extinct 20-30 %; sky changes 3-6 per 40 gens (observer); "
          "differing outcomes 10-20 %; a stage advance among the first three sky changes in "
          "most games.")
    for profile, m in metrics_by_profile.items():
        print(f"  {profile}: {m['civilizations_observed']} civilizations observed; "
              f"{m['messages_to_inhabited']} message(s) to inhabited targets; "
              f"{m['games_with_three_sky_changes']} game(s) with >= 3 sky changes, "
              f"{m['games_below_three_sky_changes']} with fewer; "
              f"{m['games_with_a_reply']} game(s) got a reply.")
        for _, _, label in DISTANCE_BANDS:
            band = m["extinct_by_band"][label]
            print(f"      {label}: {band['extinct']}/{band['civs']} extinct at first sight")

    if baseline_by_profile:
        print("\n--- baseline (pre-T1 engine, commit 2a4e0ec, same seeds) ---")
        print(f"{'Profile':<12}{'Wins now':<11}{'Wins base':<12}{'Reply now':<11}{'Reply base':<11}")
        for profile, m in metrics_by_profile.items():
            base = baseline_by_profile.get(profile)
            if not base:
                continue
            base_m = calibration_metrics(base)
            reply, base_reply = m["first_reply_median"], base_m["first_reply_median"]
            print(f"{profile:<12}{m['victory_rate']:<11.0%}{base_m['victory_rate']:<12.0%}"
                  f"{(f'{reply:.0f}' if reply is not None else '-'):<11}"
                  f"{(f'{base_reply:.0f}' if base_reply is not None else '-'):<11}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("--runs", type=int, default=30)
    parser.add_argument("--seed", type=int, default=500)
    parser.add_argument("--max-gen", type=int, default=60,
                        help="generation cap; 60 keeps the sky-change count comparable between runs")
    parser.add_argument("--profiles", default=",".join(DEFAULT_PROFILES),
                        help=f"comma-separated, from {STRATEGIES}")
    parser.add_argument("--json", help="write the raw run summaries and metrics to this file")
    parser.add_argument("--baseline", help="baseline JSON ({profile: [run, ...]}) to compare (d) and (e)")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    profiles = [p.strip() for p in args.profiles.split(",") if p.strip()]
    runs_by_profile, metrics_by_profile = {}, {}
    for profile in profiles:
        print(f"Running {args.runs} game(s) of '{profile}' (seeds {args.seed}..{args.seed + args.runs - 1}, "
              f"cap {args.max_gen})...", flush=True)
        results = run_profile(profile, args.runs, args.seed, args.max_gen, verbose=not args.quiet)
        runs_by_profile[profile] = results
        metrics_by_profile[profile] = calibration_metrics(results)

    baseline = None
    if args.baseline:
        with open(args.baseline, encoding="utf-8") as handle:
            baseline = json.load(handle)

    print_report(metrics_by_profile, baseline)

    if args.json:
        with open(args.json, "w", encoding="utf-8") as handle:
            json.dump({"runs": runs_by_profile, "metrics": metrics_by_profile}, handle, indent=1)
        print(f"\nWrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
