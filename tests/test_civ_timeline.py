"""Civilization timelines (T0): generation, replay, serialization and no behaviour change.

The last test in this file is the guard rail of the whole phase: the timelines are built from a
separate RNG stream, so a seeded game must play out exactly as it did before they existed. The
expected values were recorded by running the engine *before* the timeline code was added.
"""
import json
import os
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
os.environ.setdefault("LOS_OFFLINE", "1")

from src.civ_timeline import (  # noqa: E402
    EXTINCTION_HAZARD_PER_CENTURY, STAGE_AGE_THRESHOLDS, TIMELINE_HORIZON_YEARS, CivEvent, CivState,
    CivilizationStage, CivTimeline, generate_timeline, stage_for_age, static_timeline)
from src.legacy_of_stars_v3 import (  # noqa: E402
    START_YEAR, ContactProgram, StarSystem, _selection_has_early_sky_promise)

import auto_playtest  # noqa: E402


def living(stage=CivilizationStage.DIGITAL, strategy="LR", attitude=0.5):
    return CivState(alive=True, stage=stage, strategy=strategy, attitude=attitude,
                    civ_type="biological_pure", deception=0.2, died_year=None)


def roll(seed, stage=CivilizationStage.DIGITAL, origin_year=0, centuries=50):
    return generate_timeline(random.Random(seed), origin_year, living(stage),
                             origin_year + 100 * centuries)


class TimelineGenerationTest(unittest.TestCase):
    def test_same_seed_gives_identical_events(self):
        a = roll(4242)
        b = roll(4242)
        self.assertEqual(a.to_dict(), b.to_dict())
        self.assertNotEqual(a.to_dict(), roll(4243).to_dict())

    def test_events_are_sorted_and_stages_never_go_backwards(self):
        for seed in range(200):
            timeline = generate_timeline(random.Random(seed), 0, living(CivilizationStage.PRE_RADIO),
                                         TIMELINE_HORIZON_YEARS)
            years = [event.year for event in timeline.events]
            self.assertEqual(years, sorted(years), seed)
            previous = -1
            for event in timeline.events:
                if event.kind == "stage":
                    value = CivilizationStage[event.value].value
                    self.assertGreater(value, previous, seed)
                    previous = value

    def test_stage_events_follow_the_engine_thresholds(self):
        timeline = generate_timeline(random.Random(0), 0, living(CivilizationStage.PRE_RADIO), 100000)
        # A civilization that never dies crosses every threshold at exactly origin + threshold.
        stage_years = {CivilizationStage[e.value]: e.year for e in timeline.events if e.kind == "stage"}
        died = timeline.died_year
        for index, threshold in enumerate(STAGE_AGE_THRESHOLDS):
            stage = CivilizationStage(index + 1)
            if died is not None and threshold > died:
                self.assertNotIn(stage, stage_years)
                continue
            self.assertEqual(stage_years[stage], threshold)
            self.assertEqual(stage_for_age(threshold), stage)

    def test_civ_type_ascends_at_the_post_biological_stage(self):
        timeline = generate_timeline(random.Random(11), 0, living(CivilizationStage.INTERSTELLAR), 200000)
        if timeline.died_year is None or timeline.died_year > 100000:
            self.assertEqual(timeline.state_at(100001).civ_type, "digital_ascended")
            self.assertEqual(timeline.state_at(99999).civ_type, "biological_pure")

    def test_strategy_drift_stays_on_the_chain(self):
        seen = set()
        for seed in range(400):
            timeline = roll(seed, CivilizationStage.INTERSTELLAR, centuries=50)
            for event in timeline.events:
                if event.kind == "strategy":
                    seen.add(event.value)
                self.assertIn(event.kind, ("stage", "strategy", "attitude", "extinct"))
        self.assertTrue(seen <= {"L", "LB", "LR", "LA", "LBA"}, seen)
        self.assertTrue({"L", "LB"} <= seen, seen)  # the ordinary chain is exercised

    def test_attitude_moves_with_every_strategy_change_and_stays_in_range(self):
        for seed in range(200):
            timeline = roll(seed, CivilizationStage.INTERSTELLAR)
            changes = [e for e in timeline.events if e.kind == "strategy"]
            attitudes = [e for e in timeline.events if e.kind == "attitude"]
            self.assertEqual(len(changes), len(attitudes), seed)
            for event in attitudes:
                self.assertTrue(0.0 <= event.value <= 1.0, event.value)


class ExtinctionHazardTest(unittest.TestCase):
    """The hazard table is the calibration knob of T5; these bounds are +/- 15 % of it."""

    SAMPLES = 10000

    def assert_within_15_percent(self, stage, centuries):
        """Measure the per-century hazard over a window the civilization cannot outgrow."""
        deaths = 0
        for seed in range(self.SAMPLES):
            timeline = roll(seed, stage, centuries=centuries)
            self.assertFalse([e for e in timeline.events if e.kind == "stage"],
                             "the window must hold one stage, or two hazards are mixed")
            if timeline.died_year is not None:
                deaths += 1
        fraction = deaths / self.SAMPLES
        measured = 1.0 - (1.0 - fraction) ** (1.0 / centuries)
        expected = EXTINCTION_HAZARD_PER_CENTURY[stage.name]
        self.assertTrue(0.85 * expected <= measured <= 1.15 * expected,
                        f"{stage.name}: measured {measured:.5f}, table {expected:.5f}")

    def test_digital_hazard_matches_the_table(self):
        # The digital era itself is only eight centuries long (ages 200-1000).
        self.assert_within_15_percent(CivilizationStage.DIGITAL, centuries=9)

    def test_interstellar_hazard_matches_the_table(self):
        self.assert_within_15_percent(CivilizationStage.INTERSTELLAR, centuries=50)

    def test_swan_song_is_rolled_at_the_death(self):
        songs = 0
        deaths = 0
        for seed in range(2000):
            timeline = roll(seed, CivilizationStage.DIGITAL, centuries=20)
            if timeline.died_year is not None:
                deaths += 1
                songs += bool(timeline.has_swan_song)
        self.assertGreater(deaths, 100)
        self.assertTrue(0.7 < songs / deaths < 0.9, songs / deaths)


class StateAtTest(unittest.TestCase):
    def test_before_the_origin_there_is_no_civilization(self):
        timeline = roll(1, CivilizationStage.DIGITAL, origin_year=1500)
        state = timeline.state_at(1499)
        self.assertFalse(state.alive)
        self.assertIsNone(state.stage)
        self.assertIsNone(state.strategy)
        self.assertIsNone(state.died_year)
        self.assertTrue(timeline.state_at(1500).alive)

    def test_nothing_changes_after_extinction(self):
        timeline = CivTimeline(1000, living(), [
            CivEvent(1500, "extinct", {"has_swan_song": True}),
            CivEvent(1600, "stage", "INTERPLANETARY"),
            CivEvent(1700, "strategy", "LA"),
        ])
        after = timeline.state_at(9999)
        self.assertFalse(after.alive)
        self.assertEqual(after.died_year, 1500)
        self.assertIsNone(after.stage)
        self.assertEqual(after.to_dict(), timeline.state_at(1500).to_dict())
        self.assertTrue(timeline.state_at(1499).alive)

    def test_generated_timelines_stop_at_the_death(self):
        for seed in range(300):
            timeline = roll(seed, CivilizationStage.EARLY_RADIO)
            died = timeline.died_year
            if died is None:
                continue
            self.assertEqual(timeline.events[-1].kind, "extinct")
            for event in timeline.events[:-1]:
                self.assertLessEqual(event.year, died, seed)

    def test_static_timeline_never_changes(self):
        timeline = static_timeline(1900, living(CivilizationStage.INTERPLANETARY, "LB", 0.9))
        self.assertEqual(timeline.events, [])
        for year in (1900, 1977, 5000):
            self.assertEqual(timeline.state_at(year).strategy, "LB")
        self.assertFalse(timeline.state_at(1899).alive)


class SerializationTest(unittest.TestCase):
    def test_timeline_round_trip(self):
        timeline = roll(9, CivilizationStage.EARLY_RADIO, origin_year=1800)
        data = timeline.to_dict()
        rebuilt = CivTimeline.from_dict(json.loads(json.dumps(data)))
        self.assertEqual(rebuilt.to_dict(), data)
        for year in (1700, 1800, 1977, 2500, 6977):
            self.assertEqual(rebuilt.state_at(year).to_dict(), timeline.state_at(year).to_dict())

    def test_from_dict_of_none_is_none(self):
        self.assertIsNone(CivTimeline.from_dict(None))
        self.assertIsNone(CivTimeline.from_dict({}))

    def test_system_round_trip_keeps_the_timeline(self):
        program = ContactProgram(seed=13, offline=True)
        for system in program.star_systems.values():
            data = system.to_dict()
            rebuilt = StarSystem.from_dict(json.loads(json.dumps(data)))
            self.assertEqual(rebuilt.to_dict()["timeline"], data["timeline"])
            if system.timeline is None:
                self.assertIsNone(rebuilt.timeline)
                continue
            self.assertEqual(rebuilt.timeline.to_dict(), system.timeline.to_dict())
            for year in (1000, START_YEAR, START_YEAR + 2500):
                self.assertEqual(rebuilt.timeline_state(year).to_dict(),
                                 system.timeline_state(year).to_dict())

    def test_old_save_without_a_timeline_stays_static(self):
        program = ContactProgram(seed=13, offline=True)
        civ = next(s for s in program.star_systems.values() if s.has_civilization and not s.is_extinct)
        data = civ.to_dict()
        data.pop("timeline")  # a save written before this phase
        rebuilt = StarSystem.from_dict(data)
        self.assertIsNone(rebuilt.timeline)
        for year in (1000, START_YEAR, START_YEAR + 4000):
            state = rebuilt.timeline_state(year)
            self.assertTrue(state.alive)
            self.assertEqual(state.stage, civ.civilization_stage)
            self.assertEqual(state.strategy, civ.true_strategy)


class EngineWiringTest(unittest.TestCase):
    def test_every_rolled_civilization_gets_a_timeline(self):
        program = ContactProgram(seed=3, offline=True)
        for system in program.star_systems.values():
            if not system.has_civilization:
                self.assertIsNone(system.timeline)
                continue
            self.assertIsNotNone(system.timeline)
            self.assertEqual(system.timeline.origin_year,
                             int(round(START_YEAR - system.civilization_age)))

    def test_the_timeline_agrees_with_the_cached_fields_in_1977(self):
        for seed in range(1, 25):
            program = ContactProgram(seed=seed, offline=True)
            for system in program.star_systems.values():
                if not system.has_civilization:
                    continue
                state = system.timeline_state(START_YEAR)
                self.assertEqual(state.alive, not system.is_extinct, system.name)
                if system.is_extinct:
                    continue
                self.assertEqual(state.stage, system.civilization_stage, system.name)
                self.assertEqual(state.strategy, system.true_strategy, system.name)
                self.assertAlmostEqual(state.attitude, system.civilization_attitude)
                self.assertEqual(state.civ_type, system.civilization_type, system.name)

    def test_extinct_systems_die_where_the_engine_says_they_did(self):
        found = 0
        for seed in range(1, 40):
            program = ContactProgram(seed=seed, offline=True)
            for system in program.star_systems.values():
                if not (system.has_civilization and system.is_extinct):
                    continue
                found += 1
                # `extinct_years_ago` is the observed frame (T1): the death counted from the
                # year of the light we are looking at, not from the current year.
                self.assertEqual(system.timeline.died_year,
                                 system.observed_year(START_YEAR) - system.extinct_years_ago)
                self.assertEqual(system.timeline.has_swan_song, system.has_swan_song)
        self.assertGreater(found, 0)

    def test_timelines_follow_the_game_seed(self):
        first = {n: s.timeline.to_dict() if s.timeline else None
                 for n, s in ContactProgram(seed=77, offline=True).star_systems.items()}
        second = {n: s.timeline.to_dict() if s.timeline else None
                  for n, s in ContactProgram(seed=77, offline=True).star_systems.items()}
        self.assertEqual(first, second)

    def test_reloading_keeps_the_timeline_stream(self):
        """Even an unseeded game must reload (and undo) into the same future histories."""
        import src.legacy_of_stars_v3 as engine
        program = ContactProgram(offline=True)
        data = json.loads(json.dumps(program.to_dict()))
        reloaded = ContactProgram.from_dict(data, offline=True)
        self.assertEqual(reloaded.civ_seed_base, program.civ_seed_base)
        self.assertEqual(engine.CIV_SEED_BASE, program.civ_seed_base)
        name = reloaded.undiscovered[0]
        self.assertEqual(engine.civ_rng(name).random(), engine.civ_rng(name).random())
        self.assertEqual(reloaded.to_dict()["civ_seed_base"], data["civ_seed_base"])

    def test_wow_source_timeline_reaches_the_gen_144_year(self):
        from src.wow_signal_event import create_wow_source_system
        for seed in range(1, 15):
            program = ContactProgram(seed=seed, offline=True)
            source = create_wow_source_system(program)
            if not source.has_civilization:
                continue
            self.assertIsNotNone(source.timeline)
            # Generation 144 reads the source as it is in 3777; the horizon must cover it.
            self.assertGreaterEqual(START_YEAR + TIMELINE_HORIZON_YEARS, 3777)
            self.assertIsInstance(source.timeline_state(3777), CivState)

    def test_genesis_colony_and_mirror_get_timelines(self):
        program = ContactProgram(seed=5, offline=True)
        mirror = program._spawn_mirror_system()
        self.assertIsNotNone(mirror.timeline)
        self.assertEqual(mirror.timeline.events, [])
        self.assertTrue(mirror.timeline_state(program.start_year).alive)

        target = next(s for s in program.star_systems.values()
                      if not s.has_civilization and s.spectral_type and not s.is_wow_source)
        program.genesis.unlocked = True
        target.knowledge = 100
        program.research_points = 10000
        program.funding = 100
        program.action_points = max(program.action_points, 5)
        ok, message = program.genesis.seed_world(program, target)
        self.assertTrue(ok, message)
        world = program.genesis.seeded_worlds[target.name]
        program.generation += 40
        program.genesis._resolve(world, program)
        self.assertIsNotNone(target.timeline)
        self.assertTrue(target.timeline_state(program.start_year + (program.generation - 1) * 25).alive)


class SkyChangeGuaranteeTest(unittest.TestCase):
    """T5.2 (decision 1a): most new games promise an early, observable stage advance.

    Cheap by construction - `_selection_has_early_sky_promise` only walks each of the (at most
    five) known systems' already-generated timeline events, and `ContactProgram(...)` itself is
    fast (see the constant's comment in `legacy_of_stars_v3.py`); 50 seeded games and their checks
    run in well under a second.
    """

    def test_at_least_eighty_percent_of_new_games_satisfy_the_guarantee(self):
        satisfied = 0
        seeds = range(1, 51)
        for seed in seeds:
            program = ContactProgram(seed=seed, offline=True)
            if _selection_has_early_sky_promise(program.star_systems):
                satisfied += 1
        share = satisfied / len(seeds)
        self.assertGreaterEqual(share, 0.80, f"{satisfied}/{len(seeds)} = {share:.1%}")


# --- Recorded from the engine before timelines existed, re-recorded after T5 calibration ---
# (2026-09-03, plan §7) changed BASE_CIV_CHANCE, EXTINCT_AT_CREATION_CHANCE and the hazard/drift
# tables in a way that shows up in this 30-generation run (a different star hosts a civilization,
# a different knowledge threshold is reached) - see the calibration block in src/civ_timeline.py.
# The point this test still guards is narrower than its T0 name: the RNG stream itself is
# deterministic and stable under the *current* constants, not that the constants never move.
#
# Re-recorded again for T5.2 (2026-09-03, decision 1a's "silence ends" guarantee,
# `_selection_has_early_sky_promise` in src/legacy_of_stars_v3.py): `_start_new_game` now
# re-rolls one system at a time from the starting five-system selection - on an isolated, salted
# stream that never touches the shared global `random` (`StarSystem.reroll_civilization`) -
# whenever the first draw does not already put an observable stage advance in a Gen 8-30 window;
# seed 1 and seed 2 both needed one re-roll. Because the global stream itself is untouched, only
# the re-rolled system's own profile differs from the pre-T5.2 numbers - everything downstream
# (director, tech order, ...) would still match exactly *if* the re-rolled system had never been
# targeted by a scripted action; the numbers below differ from pre-T5.2 only insofar as the
# 30-generation playtest policy happens to interact with that one changed system (e.g. messaging
# it now gets a real fate instead of "nobody"). See `_start_new_game`'s docstring for what this
# does and why (including why an earlier, whole-selection-redraw version was rejected).
SEED1_STATS = {
    "messages_sent": 59, "responses_received": 5, "attacks_scheduled": 0, "attacks_survived": 0,
    "attacks_landed": 0, "info_attacks": 0, "swan_songs_found": 0, "systems_discovered": 28,
    "events_resolved": 2, "techs_researched": 21, "worlds_seeded": 0, "passive_detections": 0,
    # T2 added the per-message fates. The counters above are unchanged, which is the point:
    # the receipt frame reads a different year, it does not draw a different random number.
    "messages_replied": 5, "messages_nobody": 39, "messages_died_in_flight": 3, "messages_silent": 12,
}
SEED1_DESCRIPTIONS = [
    ("Proxima Centauri", "No signs of civilization detected."),
    ("Barnard's Star", "Possible artificial signals detected."),
    ("Lalande 21185", "No signs of civilization detected."),
    ("Sirius", "No signs of civilization detected."),
    ("Ross 154", "INTERPLANETARY civilization. Attitude: seemingly friendly."),
    ("Alpha Centauri", "No signs of civilization detected."),
    ("Wolf 359", "Interplanetary civilization spanning multiple worlds in their system."),
    ("Luyten 726-8", ""),
    ("Ross 248", ""),
    ("Epsilon Eridani", "No signs of civilization detected."),
    ("Lacaille 9352", "No signs of civilization detected."),
    ("Ross 128", "No signs of civilization detected."),
    ("EZ Aquarii", "No signs of civilization detected."),
    ("61 Cygni", "No signs of civilization detected."),
    ("Procyon", ""),
    ("Struve 2398", ""),
    ("Groombridge 34", "DIGITAL civilization. Attitude: seemingly friendly."),
    ("DX Cancri", ""),
    ("Epsilon Indi", "No signs of civilization detected."),
    ("Tau Ceti", "No signs of civilization detected."),
    ("GJ 1061", ""),
    ("YZ Ceti", "No signs of civilization detected."),
    ("Luyten's Star", "Possible artificial signals detected."),
    ("Teegarden's Star", "No signs of civilization detected."),
    ("Kapteyn's Star", "No signs of civilization detected."),
    ("Lacaille 8760", ""),
    ("Kruger 60", ""),
    ("Wolf 1061", "No signs of civilization detected."),
    ("Van Maanen's Star", ""),
    ("Gliese 1", ""),
    ("Wolf 424", ""),
    ("TZ Arietis", ""),
    ("Gliese 687", ""),
]
# name, has_civilization, is_extinct, true_strategy - the hidden profile of a fresh game.
# Re-recorded for T5.2 (see the comment above SEED1_STATS): the starting selection for seed 1 and
# seed 2 both changed because their first draw did not satisfy the Gen 8-30 sky-change guarantee -
# in each case exactly one system (the first in nearest-first order) was re-rolled to get one.
SEED_PROFILES = {
    1: [("Barnard's Star", True, False, "L"),
        ("Lalande 21185", False, False, None),
        ("Proxima Centauri", False, False, None),
        ("Ross 154", True, False, "L"),
        ("Sirius", False, False, None)],
    2: [("Alpha Centauri", False, False, None),
        ("Barnard's Star", True, False, "LR"),
        ("Luyten 726-8", False, False, None),
        ("Proxima Centauri", False, False, None),
        ("Ross 154", False, False, None)],
}


class NoBehaviourChangeTest(unittest.TestCase):
    """T0 adds a model, not a rule: a seeded game must play exactly as it did before."""

    def test_seeded_galaxy_profiles_are_unchanged(self):
        for seed, expected in SEED_PROFILES.items():
            program = ContactProgram(seed=seed, offline=True)
            actual = [(name, s.has_civilization, s.is_extinct, s.true_strategy)
                      for name, s in sorted(program.star_systems.items())]
            self.assertEqual(actual, expected, f"seed {seed}")

    def test_thirty_generations_of_the_playtest_policy_are_unchanged(self):
        player = auto_playtest.AutoPlayer(1, "balanced", seed=1, max_gen=30)
        program = player.program
        while not program.game_over and program.generation < 30:
            player.resolve_pending_event()
            player.make_decisions()
            program.advance_generation()
        self.assertEqual(program.generation, 30)
        self.assertFalse(program.game_over)
        self.assertEqual(dict(program.stats), SEED1_STATS)
        descriptions = [(s["name"], s["description"]) for s in program.view_state()["systems"]]
        self.assertEqual(descriptions, SEED1_DESCRIPTIONS)


if __name__ == "__main__":
    unittest.main()
