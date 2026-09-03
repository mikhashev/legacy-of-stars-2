"""The observed frame (T1): everything the player sees is the civilization as it was `d` years ago.

The scenario most of these tests use is the one the plan names: a civilization 20 light-years
away that dies in 2050. Until the year 2070 its death has not happened *for us* - the light of
its last living day is still in flight - so the engine must keep describing it as alive, and
must then report the change by itself when the light arrives.
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

from src.civ_timeline import CivEvent, CivilizationStage, CivState, CivTimeline  # noqa: E402
from src.legacy_of_stars_v3 import ContactProgram, StarSystem  # noqa: E402

from auto_playtest import run_headless  # noqa: E402

DIED_YEAR = 2050
DISTANCE = 20.0


def make_system(name: str = "Tau Ceti", distance: float = DISTANCE, died_year=DIED_YEAR,
                swan_song: bool = False, knowledge: int = 30,
                stage: CivilizationStage = CivilizationStage.DIGITAL) -> StarSystem:
    """A civilization with a known history: alive from 1500, dead in `died_year` (or never)."""
    system = StarSystem(name, distance)
    system.has_civilization = True
    system.civilization_age = 477
    system.civilization_stage = stage
    system.civilization_attitude = 0.5
    system.civilization_type = "biological_pure"
    system.true_strategy = "LBA"
    system.deception_level = 0.2
    system.is_extinct = False
    system.extinct_years_ago = None
    system.has_swan_song = False
    system.knowledge = knowledge
    system.observations = []
    initial = CivState(alive=True, stage=stage, strategy="LBA", attitude=0.5,
                       civ_type="biological_pure", deception=0.2, died_year=None)
    events = []
    if died_year is not None:
        events.append(CivEvent(died_year, "extinct", {"has_swan_song": swan_song}))
    system.timeline = CivTimeline(1500, initial, events)
    return system


def make_program(*systems: StarSystem, generation: int = 4) -> ContactProgram:
    """A program whose sky is exactly the given systems, at a chosen generation."""
    program = ContactProgram(seed=99, offline=True)
    program.star_systems = {system.name: system for system in systems}
    program.undiscovered = []          # no new stars during the test
    program.swan_song_manager.swan_songs.clear()
    program.generation = generation
    program.funding, program.public_support = 90, 90
    for system in systems:
        program._observe_system(system)
    program.drain_events()
    return program


class ObservedStateTest(unittest.TestCase):
    def test_observed_year_and_state_lag_by_the_distance(self):
        system = make_system()
        self.assertEqual(system.observed_year(2070), 2050)
        self.assertTrue(system.observed(2069).alive)      # the light of 2049 is arriving
        self.assertFalse(system.observed(2070).alive)     # the light of the death has arrived
        self.assertEqual(system.observed(2070).died_year, DIED_YEAR)

    def test_a_civilization_is_described_alive_until_the_light_of_its_death_arrives(self):
        system = make_system(knowledge=50)
        self.assertIn("DIGITAL", system.describe_civilization(2069))
        self.assertIn("EXTINCT", system.describe_civilization(2070))

    def test_silent_for_zero_years_in_2070(self):
        system = make_system(knowledge=30)
        self.assertIn("Silent for ~0 years", system.describe_civilization(2070))
        self.assertIn("Silent for ~25 years", system.describe_civilization(2095))
        self.assertEqual(system.observed_silent_years(2070), 0)
        self.assertIsNone(system.observed_silent_years(2069))

    def test_refresh_observation_reports_the_death_once_and_dates_it_from_earth(self):
        system = make_system()
        self.assertIsNone(system.refresh_observation(2069))
        self.assertFalse(system.is_extinct)
        self.assertEqual(system.refresh_observation(2070), "extinct")
        self.assertTrue(system.is_extinct)
        self.assertEqual(system.extinct_years_ago, 0)
        self.assertIsNone(system.refresh_observation(2095))   # reported once, not every year
        self.assertEqual(system.extinct_years_ago, 25)

    def test_the_swan_song_becomes_a_target_when_the_death_becomes_visible(self):
        system = make_system(swan_song=True, knowledge=30)
        program = make_program(system, generation=4)          # 2052: observed 2032, still alive
        self.assertFalse(system.is_extinct)
        self.assertEqual(program.swan_song_targets(), [])
        self.assertEqual(program.undiscovered_swan_songs(), [])

        program.generation = 5                                 # 2077: observed 2057, dead
        program._observe_system(system)
        self.assertTrue(system.is_extinct)
        self.assertTrue(system.has_swan_song)
        self.assertEqual(program.swan_song_targets(), [system.name])
        self.assertEqual(program.undiscovered_swan_songs(), [system.name])
        self.assertTrue(program.swan_song_manager.has_swan_song(system.name))

    def test_an_unstudied_system_is_still_refreshed_but_says_nothing(self):
        system = make_system(knowledge=0, swan_song=True)
        program = make_program(system, generation=5)
        self.assertTrue(system.is_extinct)                     # the fields are honest...
        self.assertEqual(program.swan_song_targets(), [])      # ...but nobody has looked


class SkyChangeTest(unittest.TestCase):
    def _advance(self, program):
        program.advance_generation()
        return [event for event in program.drain_events() if event.kind == "sky_change"]

    def test_a_death_becomes_one_sky_change_and_never_repeats(self):
        watched = make_system("Tau Ceti", knowledge=30)
        program = make_program(watched, generation=4)
        events = self._advance(program)                        # 2052 -> 2077
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event.data["system"], "Tau Ceti")
        self.assertEqual(event.data["change"], "extinction")
        self.assertEqual(event.data["observed_year"], 2057)
        self.assertIn("Tau Ceti", event.text)
        self.assertEqual(self._advance(program), [])           # nothing new arrives afterwards

    def test_a_beacon_makes_the_change_a_silence(self):
        watched = make_system("Tau Ceti", swan_song=True, knowledge=30)
        program = make_program(watched, generation=4)
        events = self._advance(program)
        self.assertEqual([e.data["change"] for e in events], ["silence"])
        self.assertIn("beacon", events[0].text)

    def test_only_systems_studied_to_twenty_percent_are_watched(self):
        watched = make_system("Tau Ceti", knowledge=20)
        ignored = make_system("Ross 128", knowledge=19)
        program = make_program(watched, ignored, generation=4)
        events = self._advance(program)
        self.assertEqual([e.data["system"] for e in events], ["Tau Ceti"])
        # The ignored system's own fields are still correct, it simply made no news.
        self.assertTrue(ignored.is_extinct)

    def test_an_observed_stage_advance_is_a_sky_change(self):
        system = make_system("Tau Ceti", died_year=None, knowledge=30,
                             stage=CivilizationStage.EARLY_RADIO)
        system.timeline.events = [CivEvent(2060, "stage", "DIGITAL")]
        program = make_program(system, generation=4)
        events = self._advance(program)                        # observed 2032 -> 2057? not yet
        self.assertEqual(events, [])
        events = self._advance(program)                        # 2102: observed 2082, digital
        self.assertEqual([e.data["change"] for e in events], ["stage_up"])
        self.assertIn("digital era", events[0].text)

    def test_a_strategy_change_is_never_observable(self):
        system = make_system("Tau Ceti", died_year=None, knowledge=100)
        system.timeline.events = [CivEvent(2060, "strategy", "LA"), CivEvent(2060, "attitude", 0.1)]
        program = make_program(system, generation=4)
        self.assertEqual(self._advance(program), [])
        self.assertEqual(self._advance(program), [])

    def test_an_observed_extinction_is_fermi_evidence_exactly_once(self):
        watched = make_system("Tau Ceti", knowledge=30)
        program = make_program(watched, generation=4)
        before = program.fermi_evidence["extinction_evidence"]
        self._advance(program)
        self.assertEqual(program.fermi_evidence["extinction_evidence"], before + 1)
        self._advance(program)
        self.assertEqual(program.fermi_evidence["extinction_evidence"], before + 1)

    def test_a_sky_change_writes_an_observation_into_the_dossier(self):
        watched = make_system("Tau Ceti", knowledge=30)
        program = make_program(watched, generation=4)
        self._advance(program)
        self.assertEqual(len(watched.observations), 1)
        entry = watched.observations[-1]
        self.assertEqual((entry["year"], entry["observed_year"]), (2077, 2057))
        self.assertIn("Silent", entry["summary"])


class ObservationHistoryTest(unittest.TestCase):
    def test_focus_research_records_a_dated_observation(self):
        system = make_system("Tau Ceti", died_year=None, knowledge=30)
        program = make_program(system, generation=4)
        program.action_points = 2
        program.focus_research("Tau Ceti")
        self.assertEqual(len(system.observations), 1)
        entry = system.observations[-1]
        self.assertEqual((entry["year"], entry["observed_year"]), (2052, 2032))
        self.assertIn("digital era", entry["summary"])
        # The same year showing the same sky is not a second observation.
        self.assertIsNone(system.record_observation(program.current_year))
        self.assertEqual(len(system.observations), 1)

    def test_view_state_carries_the_history_and_hides_the_strategy(self):
        system = make_system("Tau Ceti", knowledge=30)
        program = make_program(system, generation=4)
        program.action_points = 1
        program.focus_research("Tau Ceti")
        state = program.view_state()["systems"][0]
        self.assertEqual(state["observed_year"], 2032)
        self.assertEqual(len(state["observations"]), 1)
        self.assertEqual(set(state["observations"][0]), {"year", "observed_year", "summary"})
        blob = json.dumps(program.view_state())
        self.assertNotIn("true_strategy", blob)
        self.assertNotIn("LBA", blob)
        self.assertNotIn("deception", blob)

    def test_observations_survive_a_save_round_trip(self):
        system = make_system("Tau Ceti", knowledge=30)
        program = make_program(system, generation=4)
        program.action_points = 1
        program.focus_research("Tau Ceti")
        restored = ContactProgram.from_dict(program.to_dict(), offline=True)
        self.assertEqual(restored.star_systems["Tau Ceti"].observations, system.observations)


class OldSaveTest(unittest.TestCase):
    """A save written before timelines has no history to replay: it must not gain one."""

    def _old_save_program(self):
        system = make_system("Tau Ceti", knowledge=60)
        system.timeline = None            # an old save has no history to replay
        system.is_extinct = True
        system.extinct_years_ago = 1200
        system.has_swan_song = True
        system.civilization_stage = None
        program = make_program(system, generation=4)
        data = program.to_dict()
        for entry in data["star_systems"]:
            entry.pop("timeline", None)
            entry.pop("observations", None)
        return ContactProgram.from_dict(data, offline=True)

    def test_a_static_system_keeps_its_cached_numbers_in_every_year(self):
        program = self._old_save_program()
        system = program.star_systems["Tau Ceti"]
        self.assertIsNone(system.timeline)
        self.assertEqual(system.observations, [])
        self.assertEqual(system.extinct_years_ago, 1200)
        self.assertIsNone(system.refresh_observation(9999))    # nothing to refresh
        self.assertEqual(system.extinct_years_ago, 1200)
        self.assertTrue(system.is_extinct)
        self.assertEqual(system.describe_civilization(2077), system.describe_civilization())
        self.assertIn("1200 years ago", system.describe_civilization(9999))
        self.assertEqual(program.swan_song_targets(), ["Tau Ceti"])

    def test_a_static_system_never_makes_sky_news(self):
        program = self._old_save_program()
        program.advance_generation()
        self.assertEqual([e for e in program.drain_events() if e.kind == "sky_change"], [])
        self.assertEqual(program.star_systems["Tau Ceti"].observations, [])


class PlaytestRegressionTest(unittest.TestCase):
    def test_headless_games_still_finish(self):
        for seed in (1, 2, 3, 4, 5):
            with self.subTest(seed=seed):
                result = run_headless(seed=seed, strategy="balanced", max_gen=40)
                self.assertIsNone(result["exception"])
                self.assertGreaterEqual(result["sky_changes"], 0)


if __name__ == "__main__":
    unittest.main()
