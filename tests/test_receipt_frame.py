"""The receipt frame (T2) and the WOW! source's own reading of it (T3).

Our signal is answered by the civilization that will be there when it lands, not the one our
telescopes are looking at as it leaves. The scenario below is deliberately the cruel one: a
neighbour 20 light-years away that is alive and talkative in every observation Earth has, and
already dead in the year our message arrives. Nothing the player is told at send time may give
that away; the sky says it later, in its own year, when the light of the death gets here.
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

from src.civ_timeline import (  # noqa: E402
    TIMELINE_HORIZON_YEARS, CivEvent, CivilizationStage, CivState, CivTimeline)
from src.legacy_of_stars_v3 import (  # noqa: E402
    START_YEAR, ContactProgram, StarSystem, public_message_fate)
from src.wow_signal_event import WOW_SOURCE_NAME  # noqa: E402

RANDOM = "src.legacy_of_stars_v3.random.random"
DISTANCE = 20.0


def make_system(name: str = "Tau Ceti", distance: float = DISTANCE, *,
                stage: CivilizationStage = CivilizationStage.DIGITAL, strategy: str = "LB",
                deception: float = 0.0, knowledge: int = 30, events=()) -> StarSystem:
    """A civilization with a written history: alive from 1500, changing exactly as `events` say."""
    system = StarSystem(name, distance)
    system.has_civilization = True
    system.civilization_age = 477
    system.civilization_stage = stage
    system.civilization_attitude = 0.5
    system.civilization_type = "biological_pure"
    system.true_strategy = strategy
    system.deception_level = deception
    system.is_extinct = False
    system.extinct_years_ago = None
    system.has_swan_song = False
    system.knowledge = knowledge
    system.observations = []
    initial = CivState(alive=True, stage=stage, strategy=strategy, attitude=0.5,
                       civ_type="biological_pure", deception=deception, died_year=None)
    system.timeline = CivTimeline(1500, initial, list(events))
    return system


def make_program(*systems: StarSystem, generation: int = 4) -> ContactProgram:
    """A program whose sky is exactly the given systems, at a chosen generation."""
    program = ContactProgram(seed=99, offline=True)
    program.star_systems = {system.name: system for system in systems}
    program.undiscovered = []          # no new stars during the test
    program.swan_song_manager.swan_songs.clear()
    program.generation = generation
    program.funding, program.public_support = 90, 90
    program.action_points = program.max_action_points = 4
    for system in systems:
        program._observe_system(system)
    program.drain_events()
    return program


def only_message(system):
    return system.messages_sent[-1]


class DeadOnArrivalTest(unittest.TestCase):
    """A friendly civilization that dies while our message is still crossing the gap."""

    def _program(self):
        # Sent in 2052, read in 2072 - and there is nobody left from 2060 on.
        system = make_system(events=[CivEvent(2060, "extinct", {"has_swan_song": False})])
        return make_program(system, generation=4), system

    def test_no_reply_and_the_wording_never_reveals_the_death(self):
        program, system = self._program()
        program.send_message(system.name, "Hello")
        self.assertEqual(system.pending_responses, [])
        self.assertIn("If anyone answers, the reply arrives around Generation", program.message)
        for leak in ("dead", "extinct", "no response capability", "2060"):
            self.assertNotIn(leak, program.message.lower())

    def test_the_hidden_fate_is_recorded_and_counted(self):
        program, system = self._program()
        program.send_message(system.name, "Hello")
        entry = only_message(system)
        self.assertEqual(entry["fate"], "died_in_flight")
        self.assertEqual(entry["expected_reply_year"], 2052 + 40)
        # We learn of the death when its light arrives: 2060 + 20 LY.
        self.assertEqual(entry["explanation_year"], 2080)
        self.assertEqual(program.stats["messages_died_in_flight"], 1)
        self.assertEqual(program.stats["messages_replied"], 0)

    def test_the_public_fate_is_in_flight_and_then_only_unanswered(self):
        program, system = self._program()
        program.send_message(system.name, "Hello")
        public = program.view_state()["systems"][0]["messages_sent"][-1]
        self.assertEqual(public["fate"], "in_flight")
        self.assertIsNone(public["explanation_year"])   # a future date would be the same secret
        self.assertEqual(public["expected_reply_year"], 2092)

        program.generation = 6                          # 2102: the reply is overdue
        public = program.view_state()["systems"][0]["messages_sent"][-1]
        self.assertEqual(public["fate"], "unanswered")
        self.assertEqual(public["explanation_year"], 2080)  # the light has arrived; the date is free
        self.assertNotIn("died_in_flight", str(program.view_state()["systems"][0]))

    def test_the_sky_explains_the_silence_when_the_light_arrives(self):
        program, system = self._program()
        program.send_message(system.name, "Hello")
        with mock.patch(RANDOM, return_value=0.99):
            program.advance_generation()                # 2077: observed 2057, still alive
        self.assertEqual([e for e in program.drain_events() if e.kind == "sky_change"], [])
        with mock.patch(RANDOM, return_value=0.99):
            program.advance_generation()                # 2102: observed 2082, the death is visible
        changes = [e for e in program.drain_events() if e.kind == "sky_change"]
        self.assertEqual([e.data["change"] for e in changes], ["extinction"])
        # Which is exactly the year the message recorded as its explanation.
        self.assertLessEqual(only_message(system)["explanation_year"], program.current_year)

    def test_the_advisor_says_the_message_is_overdue_without_saying_why(self):
        program, system = self._program()
        program.send_message(system.name, "Hello")
        program.generation = 6                          # 2102: the reply should have come
        briefing = program.ai_advisor._rule_based_briefing(program)
        self.assertIn("reached its target in 2072", briefing)
        self.assertIn("no longer there", briefing)
        self.assertNotIn("2060", briefing)

    def test_a_system_we_already_watched_die_keeps_the_old_wording(self):
        system = make_system(events=[CivEvent(2000, "extinct", {"has_swan_song": False})])
        program = make_program(system, generation=4)    # observed 2032: the death is old news
        self.assertTrue(system.is_extinct)
        program.send_message(system.name, "Hello")
        self.assertEqual(program.message, f"Message sent to {system.name}. No response detected.")


class ReceiptFrameDecidesTest(unittest.TestCase):
    def test_a_pre_radio_neighbour_that_learns_to_listen_can_answer(self):
        # PRE_RADIO in every observation Earth has, EARLY_RADIO by the time we are read.
        system = make_system(stage=CivilizationStage.PRE_RADIO,
                             events=[CivEvent(2060, "stage", "EARLY_RADIO")])
        program = make_program(system, generation=4)
        self.assertEqual(system.observed(program.current_year).stage, CivilizationStage.PRE_RADIO)
        with mock.patch(RANDOM, return_value=0.0):
            program.send_message(system.name, "Hello")
        self.assertEqual(len(system.pending_responses), 1)
        self.assertEqual(only_message(system)["fate"], "in_flight")

    def test_a_pre_radio_neighbour_that_stays_pre_radio_cannot(self):
        system = make_system(stage=CivilizationStage.PRE_RADIO)
        program = make_program(system, generation=4)
        with mock.patch(RANDOM, return_value=0.0):
            program.send_message(system.name, "Hello")
        self.assertEqual(system.pending_responses, [])
        self.assertEqual(only_message(system)["fate"], "nobody")
        self.assertEqual(only_message(system)["explanation_year"], 2052)   # known at once
        self.assertIn("no response capability", program.message)

    def test_a_beacon_civilization_that_drifts_to_a_trap_springs_it(self):
        # LB in 2032 (the last light we have), LBA from 2060 - and 2072 is when they read us.
        system = make_system(strategy="LB", deception=0.7,
                             events=[CivEvent(2060, "strategy", "LBA")])
        program = make_program(system, generation=4)
        self.assertEqual(system.observed(program.current_year).strategy, "LB")
        program.send_message(system.name, "Hello")
        self.assertEqual(len(program.pending_attack_warnings), 1)
        self.assertEqual(len(system.pending_responses), 1)   # the friendly bait still comes
        # The wording must not distinguish a trap's bait from any other silent send.
        self.assertIn("If anyone answers, the reply arrives around Generation", program.message)

    def test_a_fleet_is_as_advanced_as_its_builders_were_at_launch(self):
        system = make_system(strategy="LA", stage=CivilizationStage.DIGITAL,
                             events=[CivEvent(2200, "stage", "INTERSTELLAR")])
        program = make_program(system, generation=4)
        program.send_message(system.name, "Hello")
        warning = program.pending_attack_warnings[0]
        self.assertEqual(warning.source_stage_name, "DIGITAL")
        # By the time the fleet lands its builders are interstellar; the fleet is not.
        program.generation = warning.arrival_gen
        self.assertEqual(system.timeline_state(program.current_year).stage,
                         CivilizationStage.INTERSTELLAR)
        with mock.patch(RANDOM, return_value=0.99):
            program._resolve_attack(warning)
        # Digital against tech level 1 is an "ADVANCED" strike; interstellar would have been
        # a devastating one, and would have ended the game.
        text = " ".join(e.text for e in program.drain_events())
        self.assertIn("ADVANCED ATTACK", text)
        self.assertFalse(program.game_over)

    def test_the_launch_stage_survives_a_save(self):
        system = make_system(strategy="LA")
        program = make_program(system, generation=4)
        program.send_message(system.name, "Hello")
        restored = ContactProgram.from_dict(program.to_dict(), offline=True)
        self.assertEqual(restored.pending_attack_warnings[0].source_stage_name, "DIGITAL")

    def test_send_text_does_not_reveal_who_is_listening(self):
        """L (never answers), LB (usually friendly) and LR (sometimes friendly) must read
        identically at send time - the wording is the only thing the player has, and it must
        not give away which hidden strategy, or which roll, is behind a given target."""
        texts = {}
        for strategy in ("L", "LB", "LR"):
            for roll in (0.0, 0.99):   # covers both a response and a silence, where applicable
                system = make_system(strategy=strategy)
                program = make_program(system, generation=4)
                with mock.patch(RANDOM, return_value=roll):
                    program.send_message(system.name, "Hello")
                texts[(strategy, roll)] = program.message
        unique = set(texts.values())
        self.assertEqual(len(unique), 1, texts)
        self.assertIn("If anyone answers, the reply arrives around Generation", unique.pop())


class PresentFrameTest(unittest.TestCase):
    """Passive leakage is answered by whoever is there now: our radio arrived long ago."""

    def _leakage(self, program, system):
        with mock.patch(RANDOM, return_value=0.0), \
                mock.patch.object(program.leakage_system, "determine_attack_type",
                                  return_value="laser_sail"):
            program._process_passive_leakage()
        return system.has_detected_earth

    def test_a_hostile_civilization_alive_today_still_finds_us(self):
        system = make_system("Ross 128", 10.0, strategy="LA")
        program = make_program(system, generation=4)
        self.assertTrue(self._leakage(program, system))
        self.assertEqual(program.pending_attack_warnings[0].source_stage_name, "DIGITAL")

    def test_a_hostile_civilization_already_dead_today_does_not(self):
        # Dead since 2000; the light of that death has not reached us yet (10 LY, year 2052 -
        # observed 2042), so Earth still sees them. Nobody is there to hear anything.
        system = make_system("Ross 128", 10.0, strategy="LA",
                             events=[CivEvent(2045, "extinct", {"has_swan_song": False})])
        program = make_program(system, generation=4)
        self.assertTrue(system.observed(program.current_year).alive)   # still visible
        self.assertFalse(self._leakage(program, system))
        self.assertEqual(program.pending_attack_warnings, [])

    def test_an_information_attack_from_a_source_that_has_since_died_is_discarded(self):
        system = make_system("Ross 128", 10.0, strategy="LA",
                             events=[CivEvent(2045, "extinct", {"has_swan_song": False})])
        program = make_program(system, generation=4)
        program.pending_info_attacks.append([system.name, program.generation])
        program._deliver_pending_info_attacks()
        self.assertEqual(program.stats["info_attacks"], 0)
        self.assertEqual(program.pending_info_attacks, [])


class MessageSerializationTest(unittest.TestCase):
    def test_an_old_save_of_text_and_generation_pairs_still_loads(self):
        system = make_system()
        program = make_program(system, generation=4)
        data = program.to_dict()
        entry = data["star_systems"][0]
        entry["messages_sent"] = [["Hello", 2], ["Anyone?", 3]]   # the pre-T2 shape
        restored = ContactProgram.from_dict(data, offline=True)
        messages = restored.star_systems[system.name].messages_sent
        self.assertEqual([m["text"] for m in messages], ["Hello", "Anyone?"])
        self.assertEqual([m["fate"] for m in messages], ["in_flight", "in_flight"])
        self.assertEqual(messages[0]["generation"], 2)
        self.assertEqual(messages[0]["expected_reply_year"], 2002 + 40)
        self.assertIsNone(messages[0]["explanation_year"])
        # And the web contract is served from them without a crash.
        public = restored.view_state()["systems"][0]["messages_sent"]
        self.assertEqual(len(public), 2)

    def test_a_sent_message_survives_a_save_with_its_fate(self):
        system = make_system(strategy="L")
        program = make_program(system, generation=4)
        program.send_message(system.name, "Hello")
        restored = ContactProgram.from_dict(program.to_dict(), offline=True)
        self.assertEqual(only_message(restored.star_systems[system.name]),
                         only_message(system))

    def test_a_reply_closes_the_message_it_answers(self):
        system = make_system(strategy="LB")
        program = make_program(system, generation=4)
        with mock.patch(RANDOM, return_value=0.0):
            program.send_message(system.name, "Hello")
        self.assertEqual(only_message(system)["fate"], "in_flight")
        system.pending_responses[:] = [(text, program.generation) for text, _ in system.pending_responses]
        program._deliver_responses()
        self.assertEqual(only_message(system)["fate"], "replied")
        self.assertEqual(program.stats["messages_replied"], 1)
        self.assertEqual(program.view_state()["systems"][0]["messages_sent"][-1]["fate"], "replied")


class WowReceiptFrameTest(unittest.TestCase):
    """Generation 144 asks the source what it is in 3777, not what it was in 1977."""

    EVALUATION_YEAR = 3777

    def _replied_program(self, seed=7):
        program = ContactProgram(seed=seed, offline=True)
        program.wow_signal.reply("Hello")
        return program, program.wow_signal.wow_source_system

    def _resolve(self, program):
        program.generation = 144
        self.assertTrue(program.wow_signal.check_gen144_event())
        program.wow_signal.trigger_gen144_event()

    def _write_timeline(self, source, strategy="LB", died_year=None):
        source.has_civilization = True
        source.is_extinct = False
        source.civilization_stage = CivilizationStage.DIGITAL
        source.civilization_type = "biological_pure"
        source.true_strategy = strategy
        source.deception_level = 0.0
        initial = CivState(alive=True, stage=CivilizationStage.DIGITAL, strategy=strategy,
                           attitude=0.5, civ_type="biological_pure", deception=0.0)
        events = [] if died_year is None else [CivEvent(died_year, "extinct", {"has_swan_song": True})]
        source.timeline = CivTimeline(1000, initial, events)

    def test_the_evaluation_year_is_the_year_our_reply_lands(self):
        program, source = self._replied_program()
        self.assertEqual(program.wow_signal.evaluation_year(source), self.EVALUATION_YEAR)
        self.assertGreaterEqual(START_YEAR + TIMELINE_HORIZON_YEARS, self.EVALUATION_YEAR)

    def test_a_source_that_died_before_3777_answers_with_silence(self):
        program, source = self._replied_program()
        self._write_timeline(source, "LB", died_year=3000)
        self.assertEqual(source.timeline_state(self.EVALUATION_YEAR).alive, False)
        self._resolve(program)
        self.assertEqual(program.wow_signal.outcome, "silence")
        self.assertIn("The Long Wait", program.achievements)

    def test_a_source_still_alive_and_talkative_in_3777_answers(self):
        program, source = self._replied_program()
        self._write_timeline(source, "LB")
        self._resolve(program)
        self.assertEqual(program.wow_signal.outcome, "friendly")
        self.assertIn("The WOW! Response", program.achievements)

    def test_a_source_that_turns_hostile_before_3777_answers_with_a_weapon(self):
        program, source = self._replied_program()
        self._write_timeline(source, "LB")
        source.timeline.events = [CivEvent(3000, "strategy", "LA")]
        self._resolve(program)
        self.assertEqual(program.wow_signal.outcome, "hostile")

    def test_nobody_was_ever_there_is_still_half_the_outcomes(self):
        program, source = self._replied_program()
        source.has_civilization = False
        source._clear_civilization()
        self._resolve(program)
        self.assertEqual(program.wow_signal.outcome, "silence")

    def test_a_rolled_source_has_a_timeline_that_reaches_3777(self):
        for seed in range(1, 12):
            program = ContactProgram(seed=seed, offline=True)
            program.wow_signal.reply("Hello")
            source = program.star_systems[WOW_SOURCE_NAME]
            if not source.has_civilization:
                continue
            self.assertIsNotNone(source.timeline)
            # `state_at` is total, but the rolls behind it must actually cover the year we read.
            self.assertLessEqual(max((e.year for e in source.timeline.events), default=0),
                                 START_YEAR + TIMELINE_HORIZON_YEARS)
            self.assertIsInstance(source.timeline_state(self.EVALUATION_YEAR).alive, bool)


class PublicFateTest(unittest.TestCase):
    def test_the_public_fate_never_exposes_the_hidden_ones(self):
        cases = {
            "replied": "replied",
            "nobody": "nobody",
            "in_flight": "in_flight",
            "died_in_flight": "in_flight",
            "silent": "in_flight",
        }
        for hidden, expected in cases.items():
            entry = {"fate": hidden, "expected_reply_year": 2100}
            self.assertEqual(public_message_fate(entry, 2050), expected, hidden)
        for hidden in ("in_flight", "died_in_flight", "silent"):
            entry = {"fate": hidden, "expected_reply_year": 2100}
            self.assertEqual(public_message_fate(entry, 2100), "unanswered", hidden)


if __name__ == "__main__":
    unittest.main()
