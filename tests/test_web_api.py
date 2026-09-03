"""
Web facade (src/web_api.py): every action through perform(), the doctrine
follow-up, the opening scenario, save/load round trip, a full headless game and
the "plain JSON only" rule that keeps engine objects out of the browser.
"""
import json
import os
import random
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("LOS_OFFLINE", "1")

from src import save_manager  # noqa: E402
from src.legacy_of_stars_v3 import CivilizationStage, ContactProgram  # noqa: E402
from src.web_api import GameSession, action_ids  # noqa: E402

PLAIN_TYPES = (dict, list, str, int, float, bool, type(None))


def new_session(seed=11, decided=True):
    """A session on a fresh game; the 1977 decision is made unless a test needs it open."""
    session = GameSession()
    session.new_game(seed=seed)
    if decided:
        session.perform("wow_silent")
    return session


def call(session, action_id, **params):
    """perform() with keyword parameters; returns the parsed result."""
    text = session.perform(action_id, json.dumps(params))
    assert isinstance(text, str)
    return json.loads(text)


def assert_plain(testcase, value, path="result"):
    """Every leaf must be a type json.dumps handles without a default= hook."""
    testcase.assertIsInstance(value, PLAIN_TYPES, f"{path} is {type(value).__name__}")
    if isinstance(value, dict):
        for key, item in value.items():
            testcase.assertIsInstance(key, str, f"{path} key {key!r}")
            assert_plain(testcase, item, f"{path}.{key}")
    elif isinstance(value, list):
        for i, item in enumerate(value):
            assert_plain(testcase, item, f"{path}[{i}]")


def hostile_system(program):
    """Turn the second known system into a silent aggressor and make it launch."""
    system = list(program.star_systems.values())[1]
    system.timeline = None   # hand-written: static, so the receipt frame reads these fields
    system.has_civilization = True
    system.is_extinct = False
    system.true_strategy = "LA"
    system.civilization_stage = CivilizationStage.DIGITAL
    system.has_detected_earth = False
    program.action_points = program.max_action_points = 4
    program.send_message(system.name, "Hello")
    program.message = ""
    return system


class ContractShapeTest(unittest.TestCase):
    def test_new_game_returns_view_state_json(self):
        session = GameSession()
        state = json.loads(session.new_game(seed=3))
        for key in ("generation", "year", "director", "status", "systems", "threats",
                    "technologies", "actions", "wow", "pending_event", "game_over"):
            self.assertIn(key, state)
        self.assertEqual(state["generation"], 1)
        self.assertFalse(state["wow"]["decided"])

    def test_perform_result_shape(self):
        session = new_session()
        result = call(session, "public_outreach")
        self.assertEqual(set(result) - {"data"}, {"ok", "message", "events", "state", "needs", "undo"})
        self.assertIsInstance(result["ok"], bool)
        self.assertIsInstance(result["message"], str)
        self.assertIsInstance(result["events"], list)
        self.assertIsNone(result["needs"])
        self.assertEqual(result["state"], json.loads(session.state()))

    def test_state_before_new_game(self):
        session = GameSession()
        with self.assertRaises(RuntimeError):
            session.state()
        result = json.loads(session.perform("public_outreach"))
        self.assertFalse(result["ok"])
        self.assertIsNone(result["state"])

    def test_action_ids_cover_the_contract(self):
        self.assertEqual(set(action_ids()), {
            "send_message", "focus_research", "public_outreach", "research_tech", "choose_doctrine",
            "advance_generation", "defend", "consult_advisor", "listen_swan_song", "genesis_seed",
            "respond_event", "wow_reply", "wow_silent", "compose_director_message", "summary", "help",
            "undo",
        })


class OpeningScenarioTest(unittest.TestCase):
    def test_wow_reply_with_custom_text(self):
        session = new_session(decided=False)
        result = call(session, "wow_reply", text="We are here.")
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["message"], "We are here.")
        self.assertEqual(result["data"]["response_gen"], 144)
        self.assertTrue(result["state"]["wow"]["decided"])
        self.assertTrue(result["state"]["wow"]["replied"])
        self.assertEqual(session.program.research_points, 100)

    def test_wow_reply_empty_text_uses_the_default_message(self):
        session = new_session(decided=False)
        result = call(session, "wow_reply", text="")
        self.assertIn("Greetings from Earth", result["data"]["message"])

    def test_wow_reply_truncates_at_500_characters(self):
        session = new_session(decided=False)
        result = call(session, "wow_reply", text="x" * 900)
        self.assertEqual(len(result["data"]["message"]), 500)

    def test_wow_reply_carries_both_the_full_text_and_the_excerpt(self):
        session = new_session(decided=False)
        result = call(session, "wow_reply", text="y" * 300)
        data = result["data"]
        self.assertEqual(data["message_full"], session.program.wow_signal.wow_reply_message)
        self.assertEqual(len(data["message_full"]), 300)
        self.assertEqual(data["excerpt"], "y" * 100 + "...")
        # The console-style text keeps the 100-character excerpt, not the whole message.
        self.assertIn(data["excerpt"], result["message"])

    def test_wow_silent_and_second_decision_refused(self):
        session = new_session(decided=False)
        result = call(session, "wow_silent")
        self.assertTrue(result["ok"])
        self.assertIn("Silent Wisdom", result["state"]["achievements"])
        self.assertFalse(result["state"]["wow"]["replied"])
        again = call(session, "wow_reply", text="late")
        self.assertFalse(again["ok"])
        self.assertIn("already been made", again["message"])

    def test_compose_director_message_does_not_decide(self):
        session = new_session(decided=False)
        result = call(session, "compose_director_message")
        self.assertTrue(result["ok"])
        self.assertTrue(result["data"]["draft"])
        self.assertEqual(result["message"], result["data"]["draft"])
        self.assertFalse(result["state"]["wow"]["decided"])


class BasicActionsTest(unittest.TestCase):
    def test_send_message_success_and_failures(self):
        session = new_session()
        name = session.program.view_state()["systems"][0]["name"]
        ok = call(session, "send_message", system=name, text="Hello")
        self.assertTrue(ok["ok"])
        self.assertEqual(ok["state"]["stats"]["messages_sent"], 1)

        missing = call(session, "send_message", text="Hello")
        self.assertFalse(missing["ok"])
        self.assertIn("'system'", missing["message"])

        unknown = call(session, "send_message", system="Nowhere", text="Hello")
        self.assertFalse(unknown["ok"])
        self.assertIn("not found in database", unknown["message"])

        session.program.action_points = 0
        broke = call(session, "send_message", system=name, text="Hello")
        self.assertFalse(broke["ok"])
        self.assertEqual(broke["message"], "Not enough Action Points!")

    def test_focus_research_success_and_failure(self):
        session = new_session()
        name = session.program.view_state()["systems"][0]["name"]
        before = session.program.star_systems[name].knowledge
        ok = call(session, "focus_research", system=name)
        self.assertTrue(ok["ok"])
        self.assertGreater(session.program.star_systems[name].knowledge, before)
        session.program.action_points = 0
        self.assertFalse(call(session, "focus_research", system=name)["ok"])

    def test_public_outreach_success_and_failure(self):
        session = new_session()
        session.program.public_support = 20
        ok = call(session, "public_outreach")
        self.assertTrue(ok["ok"])
        self.assertGreater(session.program.public_support, 20)
        session.program.action_points = 0
        self.assertFalse(call(session, "public_outreach")["ok"])

    def test_advance_generation_does_not_autosave(self):
        session = new_session()
        with tempfile.TemporaryDirectory() as tmp:
            original, save_manager.SAVE_DIR = save_manager.SAVE_DIR, Path(tmp)
            try:
                result = call(session, "advance_generation")
            finally:
                save_manager.SAVE_DIR = original
            self.assertTrue(result["ok"])
            self.assertEqual(list(Path(tmp).iterdir()), [])
        self.assertEqual(result["state"]["generation"], 2)
        self.assertTrue(any(e["kind"] == "generation_start" for e in result["events"]))

    def test_unknown_action_and_bad_params(self):
        session = new_session()
        unknown = json.loads(session.perform("teleport"))
        self.assertFalse(unknown["ok"])
        self.assertIn("unknown action", unknown["message"])

        broken = json.loads(session.perform("public_outreach", "{not json"))
        self.assertFalse(broken["ok"])
        self.assertIn("not valid JSON", broken["message"])

        not_object = json.loads(session.perform("public_outreach", "[1, 2]"))
        self.assertFalse(not_object["ok"])
        self.assertIn("must be a JSON object", not_object["message"])

    def test_actions_not_currently_available_are_refused(self):
        session = new_session()
        for action_id in ("defend", "consult_advisor", "listen_swan_song", "genesis_seed", "respond_event"):
            result = call(session, action_id)
            self.assertFalse(result["ok"], action_id)
            self.assertEqual(result["message"], "action not available now")

    def test_game_over_is_reflected_and_never_raises(self):
        session = new_session()
        session.program.game_over = True
        session.program.game_over_reason = "The program was defunded."
        result = call(session, "public_outreach")
        self.assertFalse(result["ok"])
        self.assertIn("the game is over", result["message"])
        self.assertTrue(result["state"]["game_over"])
        self.assertTrue(call(session, "summary")["ok"])  # reports still work


class ResearchAndDoctrineTest(unittest.TestCase):
    def test_research_success_and_failures(self):
        session = new_session()
        program = session.program
        unknown = call(session, "research_tech", tech="warp_drive")
        self.assertFalse(unknown["ok"])
        self.assertIn("unknown technology", unknown["message"])

        program.research_points = 0
        poor = call(session, "research_tech", tech="seti_at_home")
        self.assertFalse(poor["ok"])
        self.assertIn("Not enough Research Points", poor["message"])

        program.research_points = 100000
        ok = call(session, "research_tech", tech="seti_at_home")
        self.assertTrue(ok["ok"])
        self.assertIsNone(ok["needs"])
        self.assertIn("seti_at_home", ok["state"]["technologies"]["researched"])

        again = call(session, "research_tech", tech="seti_at_home")
        self.assertFalse(again["ok"])
        self.assertIn("already researched", again["message"])

    def test_doctrine_flow(self):
        session = new_session()
        program = session.program
        program.generation = 12
        program.research_points = 100000
        for tech_id in ("seti_at_home", "ai_pattern_recognition", "bio_engineering"):
            self.assertTrue(call(session, "research_tech", tech=tech_id)["ok"], tech_id)
            program.research_points = 100000

        result = call(session, "research_tech", tech="genetic_pacification")
        self.assertTrue(result["ok"])
        needs = result["needs"]
        self.assertEqual(needs["kind"], "doctrine")
        self.assertEqual(needs["tech_id"], "genetic_pacification")
        self.assertTrue(needs["name"])
        self.assertEqual([o["index"] for o in needs["options"]], list(range(len(needs["options"]))))

        bad = call(session, "choose_doctrine", tech="genetic_pacification", choice=99)
        self.assertFalse(bad["ok"])
        self.assertIn("'choice'", bad["message"])

        chosen = call(session, "choose_doctrine", tech="genetic_pacification", choice=1)
        self.assertTrue(chosen["ok"])
        expected = needs["options"][1]["name"]
        self.assertIn(expected, chosen["state"]["active_doctrines"])
        self.assertIn("Doctrine adopted", chosen["message"])

        repeat = call(session, "choose_doctrine", tech="genetic_pacification", choice=0)
        self.assertFalse(repeat["ok"])
        self.assertIn("already in force", repeat["message"])

    def test_choose_doctrine_on_a_technology_without_one(self):
        session = new_session()
        result = call(session, "choose_doctrine", tech="seti_at_home", choice=0)
        self.assertFalse(result["ok"])
        self.assertIn("no doctrine choice", result["message"])


class DefenseTest(unittest.TestCase):
    def setUp(self):
        self.session = new_session(seed=31)
        self.source = hostile_system(self.session.program)
        self.assertTrue(self.session.program.pending_attack_warnings)

    def test_defend_evacuate_and_emergency(self):
        session = self.session
        evacuate = call(session, "defend", threat=0, defense="evacuate")
        self.assertTrue(evacuate["ok"])
        self.assertIn("Evacuation", evacuate["state"]["threats"][0]["actions_taken"])

        repeat = call(session, "defend", threat=0, defense="evacuate")
        self.assertFalse(repeat["ok"])
        self.assertIn("already completed", repeat["message"])

        session.program.action_points = session.program.max_action_points
        emergency = call(session, "defend", threat=0, defense="emergency")
        self.assertTrue(emergency["ok"])
        self.assertEqual(session.program.action_points, 0)
        self.assertIn("Emergency Defense Protocol", emergency["state"]["threats"][0]["actions_taken"])

    def test_defend_diplomacy_is_applied_even_when_it_fails(self):
        result = call(self.session, "defend", threat=0, defense="diplomacy")
        self.assertTrue(result["ok"])

    def test_defend_parameter_errors(self):
        bad_index = call(self.session, "defend", threat=7, defense="evacuate")
        self.assertFalse(bad_index["ok"])
        self.assertIn("'threat'", bad_index["message"])

        bad_defense = call(self.session, "defend", threat=0, defense="nuke")
        self.assertFalse(bad_defense["ok"])
        self.assertIn("'defense'", bad_defense["message"])

        missing = call(self.session, "defend", threat=0)
        self.assertFalse(missing["ok"])
        self.assertIn("'defense'", missing["message"])


class SituationalActionsTest(unittest.TestCase):
    def test_consult_advisor_once_per_generation(self):
        session = new_session()
        session.program.ai_advisor_unlocked = True
        first = call(session, "consult_advisor")
        self.assertTrue(first["ok"])
        self.assertTrue(first["message"])
        second = call(session, "consult_advisor")
        self.assertFalse(second["ok"])
        self.assertIn("already consulted", second["message"])

    def test_listen_swan_song(self):
        session = new_session(seed=41)
        program = session.program
        system = list(program.star_systems.values())[0]
        system.has_civilization = True
        system.is_extinct = True
        system.has_swan_song = True
        system.knowledge = 100
        program._register_swan_song(system)
        program.action_points = program.max_action_points = 3

        self.assertIn("listen_swan_song", {a["id"] for a in program.view_state()["actions"]})

        missing = call(session, "listen_swan_song", system="Nowhere")
        self.assertFalse(missing["ok"])
        self.assertIn("not found in database", missing["message"])
        self.assertEqual(program.action_points, 3)

        result = call(session, "listen_swan_song", system=system.name)
        self.assertTrue(result["ok"])            # the scan ran and cost 1 AP
        self.assertEqual(program.action_points, 2)

    def test_an_unstudied_system_is_never_a_swan_song_target(self):
        session = new_session(seed=41)
        program = session.program
        studied, unstudied = list(program.star_systems.values())[:2]
        for system in (studied, unstudied):
            system.has_civilization = True
            system.is_extinct = True
            system.has_swan_song = True
            program._register_swan_song(system)
        studied.knowledge, unstudied.knowledge = 40, 0
        program.action_points = program.max_action_points = 3

        state = call(session, "help")["state"]
        self.assertEqual(state["swan_song_targets"], [studied.name])
        label = next(a["label"] for a in state["actions"] if a["id"] == "listen_swan_song")
        self.assertIn("1 candidate system", label)

        # The refusal costs nothing and says nothing about what is (or is not) out there.
        refused = call(session, "listen_swan_song", system=unstudied.name)
        self.assertFalse(refused["ok"])
        self.assertIn("Study the system first", refused["message"])
        self.assertNotIn("extinct", refused["message"].lower())
        self.assertEqual(program.action_points, 3)

    def test_genesis_seed(self):
        session = new_session(seed=51)
        program = session.program
        program.genesis.unlocked = True
        program.research_points = 5000
        program.funding = 90
        program.action_points = program.max_action_points = 3
        target = next(s for s in program.star_systems.values()
                      if not s.has_civilization and not s.is_wow_source
                      and (s.spectral_type or "G")[:1] in "GKMF")

        # An unstudied system is refused before the civilization check, so neither the refusal
        # nor the picker list can say whether anyone lives there.
        target.knowledge = 0
        unstudied = call(session, "genesis_seed", system=target.name)
        self.assertFalse(unstudied["ok"])
        self.assertIn("Study the system first", unstudied["message"])
        self.assertNotIn(target.name, unstudied["state"]["genesis"]["targets"])

        target.knowledge = 20
        self.assertIn(target.name, call(session, "help")["state"]["genesis"]["targets"])

        ok = call(session, "genesis_seed", system=target.name)
        self.assertTrue(ok["ok"], ok["message"])
        self.assertTrue(any(w["system_name"] == target.name for w in ok["state"]["genesis"]["worlds"]))

        repeat = call(session, "genesis_seed", system=target.name)
        self.assertFalse(repeat["ok"])

        unknown = call(session, "genesis_seed", system="Nowhere")
        self.assertFalse(unknown["ok"])
        self.assertIn("not found in database", unknown["message"])

    def test_respond_event_blocks_and_unblocks_advance(self):
        session = new_session(seed=61)
        program = session.program
        event = next(iter(program.philosophical_events.events.values()))
        program.pending_philosophical_event = event

        blocked = call(session, "advance_generation")
        self.assertFalse(blocked["ok"])
        self.assertIn("respond_event", blocked["message"])
        self.assertEqual(blocked["state"]["generation"], 1)
        self.assertIsNotNone(blocked["state"]["pending_event"])

        bad = call(session, "respond_event", choice=99)
        self.assertFalse(bad["ok"])
        self.assertIn("'choice'", bad["message"])

        answered = call(session, "respond_event", choice=0)
        self.assertTrue(answered["ok"])
        self.assertIsNone(answered["state"]["pending_event"])
        self.assertTrue(call(session, "advance_generation")["ok"])


class ReportsTest(unittest.TestCase):
    def test_summary_returns_text_and_breakdown(self):
        session = new_session()
        result = call(session, "summary")
        self.assertTrue(result["ok"])
        self.assertIn("LEGACY OF STARS - FINAL REPORT", result["message"])
        self.assertIsInstance(result["data"]["score"], int)
        self.assertIn("Generations survived", result["data"]["score_breakdown"])

    def test_help_returns_the_console_help_text(self):
        from src.ui_text import HELP_TEXT
        result = call(new_session(), "help")
        self.assertTrue(result["ok"])
        self.assertEqual(result["message"], HELP_TEXT)
        self.assertIn("ai", result["data"])


class SaveLoadTest(unittest.TestCase):
    def test_new_save_load_state_equality(self):
        session = new_session(seed=71)
        name = session.program.view_state()["systems"][0]["name"]
        call(session, "send_message", system=name, text="Hello")
        call(session, "advance_generation")
        before = json.loads(session.state())

        save_text = session.save()
        json.loads(save_text)  # the save itself is JSON

        restored = GameSession()
        after = json.loads(restored.load(save_text))
        self.assertEqual(before, after)
        self.assertEqual(json.loads(restored.state()), before)

    def test_load_rejects_a_non_save(self):
        session = GameSession()
        with self.assertRaises(save_manager.SaveError):
            session.load('{"hello": "world"}')

    def test_console_saves_load_into_the_session(self):
        program = ContactProgram(seed=81, offline=True)
        program.advance_generation()
        session = GameSession()
        state = json.loads(session.load(save_manager.serialize(program)))
        self.assertEqual(state["generation"], program.generation)


class DataDirTest(unittest.TestCase):
    def test_copy_of_data_directory_works(self):
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "data"
            shutil.copytree(ROOT / "data", copy)
            session = GameSession(data_dir=copy)
            state = json.loads(session.new_game(seed=91))
            self.assertEqual(session.program.data_dir, copy)
            self.assertEqual(len(state["systems"]), 5)
            self.assertTrue(state["technologies"]["available"])
            self.assertTrue(session.program.content.templates_dir.is_dir())

    def test_missing_data_directory_fails_clearly(self):
        missing = ROOT / "data_does_not_exist"
        session = GameSession(data_dir=missing)
        with self.assertRaises(FileNotFoundError) as ctx:
            session.new_game(seed=1)
        self.assertIn("data directory not found", str(ctx.exception))

    def test_default_data_dir_is_unchanged(self):
        program = ContactProgram(seed=1, offline=True)
        self.assertEqual(program.data_dir, ROOT / "data")


class PlainJsonTest(unittest.TestCase):
    """Nothing but plain types crosses the boundary: json.dumps is called without default=."""

    def test_every_string_the_facade_returns_is_plain_json(self):
        session = GameSession()
        texts = [session.new_game(seed=101)]
        program = session.program
        name = program.view_state()["systems"][0]["name"]
        program.ai_advisor_unlocked = True
        program.genesis.unlocked = True
        program.research_points = 100000
        program.generation = 12
        hostile_system(program)
        for tech_id in ("seti_at_home", "ai_pattern_recognition"):
            program.research_tech(tech_id)
        program.research_points = 100000
        program.message = ""

        texts += [
            session.perform("wow_reply", json.dumps({"text": "hi"})),
            session.perform("compose_director_message"),
            session.perform("send_message", json.dumps({"system": name, "text": "hi"})),
            session.perform("focus_research", json.dumps({"system": name})),
            session.perform("public_outreach"),
            session.perform("research_tech", json.dumps({"tech": "bio_engineering"})),
            session.perform("research_tech", json.dumps({"tech": "genetic_pacification"})),
            session.perform("choose_doctrine", json.dumps({"tech": "genetic_pacification", "choice": 0})),
            session.perform("defend", json.dumps({"threat": 0, "defense": "evacuate"})),
            session.perform("consult_advisor"),
            session.perform("listen_swan_song", json.dumps({"system": name})),
            session.perform("genesis_seed", json.dumps({"system": name})),
            session.perform("respond_event", json.dumps({"choice": 0})),
            session.perform("advance_generation"),
            session.perform("summary"),
            session.perform("help"),
            session.perform("nonsense"),
            session.state(),
            session.save(),
        ]
        for text in texts:
            self.assertIsInstance(text, str)
            parsed = json.loads(text)
            assert_plain(self, parsed)
            # A second pass without default= proves no engine object was smuggled through.
            self.assertEqual(json.loads(json.dumps(parsed, ensure_ascii=False)), parsed)

    def test_event_payloads_are_plain(self):
        session = new_session(seed=111)
        seen = 0
        for _ in range(40):
            result = call(session, "advance_generation")
            for event in result["events"]:
                self.assertEqual(set(event), {"kind", "text", "data", "generation"})
                assert_plain(self, event["data"])
                seen += 1
            if result["state"]["game_over"]:
                break
        self.assertGreater(seen, 0)


class HeadlessGameTest(unittest.TestCase):
    """A full game driven only through perform(), like scripts/auto_playtest.py."""

    def test_sixty_generations_through_the_facade(self):
        session = GameSession()
        state = json.loads(session.new_game(seed=2024))
        rng = random.Random(7)
        self.assertTrue(json.loads(session.perform("wow_silent"))["ok"])
        generations = 0

        for _ in range(60):
            state = json.loads(session.state())
            if state["game_over"]:
                break

            if state["pending_event"] is not None:
                choices = len(state["pending_event"]["choices"])
                self.assertTrue(call(session, "respond_event", choice=rng.randrange(choices))["ok"])

            for threat in state["threats"]:
                if threat["eta"] <= 2 and "Evacuation" not in threat["actions_taken"]:
                    call(session, "defend", threat=threat["index"] - 1, defense="evacuate")

            state = json.loads(session.state())
            for tech in state["technologies"]["available"]:
                if tech["locked"] or tech["cost"] > state["status"]["research_points"]:
                    continue
                result = call(session, "research_tech", tech=tech["id"])
                if result["needs"]:
                    self.assertEqual(result["needs"]["kind"], "doctrine")
                    follow_up = call(session, "choose_doctrine",
                                     tech=result["needs"]["tech_id"], choice=0)
                    self.assertTrue(follow_up["ok"], follow_up["message"])
                state = result["state"]

            guard = 0
            while state["status"]["action_points"] > 0 and guard < 20:
                guard += 1
                names = [s["name"] for s in state["systems"]]
                if rng.random() < 0.4:
                    result = call(session, "send_message", system=rng.choice(names),
                                  text="Greetings from Earth.")
                elif rng.random() < 0.5:
                    result = call(session, "public_outreach")
                else:
                    result = call(session, "focus_research", system=rng.choice(names))
                if not result["ok"]:
                    result = call(session, "focus_research", system=rng.choice(names))
                state = result["state"]

            advanced = call(session, "advance_generation")
            self.assertTrue(advanced["ok"], advanced["message"])
            generations += 1
            state = advanced["state"]

        self.assertGreater(generations, 0)
        final = json.loads(session.state())
        self.assertTrue(final["game_over"] or final["generation"] >= 40)
        self.assertTrue(call(session, "summary")["ok"])
        # The whole game round trips through a save.
        reloaded = GameSession()
        self.assertEqual(json.loads(reloaded.load(session.save())), final)


if __name__ == "__main__":
    unittest.main()


class StartScreenAndViewStateTest(unittest.TestCase):
    def test_help_works_without_a_game(self):
        import json as _json
        payload = _json.loads(GameSession().perform("help", "{}"))
        self.assertTrue(payload["ok"])
        self.assertIn("HOW TO PLAY", payload["message"])
        self.assertIsNone(payload["state"])
        # The front-end reads result.data.ai on both help paths, so the no-game one carries it too.
        self.assertIn("data", payload)
        self.assertIn("ai", payload["data"])
        self.assertIsInstance(payload["data"]["ai"], str)

    def test_view_state_exposes_year_context_and_genesis_targets(self):
        import json as _json
        session = GameSession()
        state = _json.loads(session.new_game(3))
        self.assertTrue(all("year_context" in t for t in state["technologies"]["available"]))
        targets = state["genesis"]["targets"]
        self.assertIsInstance(targets, list)
        names = {s["name"] for s in state["systems"]}
        self.assertTrue(set(targets) <= names)
        swan_targets = state["swan_song_targets"]
        self.assertIsInstance(swan_targets, list)
        self.assertTrue(set(swan_targets) <= names)



class UndoTest(unittest.TestCase):
    """The facade's undo stack (docs/reference/web_contract.md 3/7): one step back per undoable action."""

    def test_undo_restores_action_points_messages_and_the_generation_log(self):
        session = new_session(seed=11)
        name = json.loads(session.state())["systems"][0]["name"]
        before = json.loads(session.state())
        sent = call(session, "send_message", system=name, text="hello")
        self.assertTrue(sent["ok"])
        self.assertEqual(sent["state"]["systems"][0]["messages_sent"][0]["text"], "hello")
        self.assertEqual([e["action"] for e in sent["state"]["generation_log"]], ["send_message"])
        self.assertTrue(sent["undo"]["available"])

        undone = call(session, "undo")
        self.assertTrue(undone["ok"])
        self.assertIn("Sent message", undone["message"])
        self.assertEqual(undone["state"]["status"]["action_points"], before["status"]["action_points"])
        self.assertEqual(undone["state"]["systems"][0]["messages_sent"], [])
        self.assertEqual(undone["state"]["generation_log"], [])
        self.assertEqual(undone["state"]["stats"]["messages_sent"], before["stats"]["messages_sent"])

    def test_undo_restores_the_rng_so_a_redone_action_is_identical(self):
        """The point of restoring `random`: undo must not be a way to re-roll a reply."""
        session = new_session(seed=11)
        program = session.program
        system = list(program.star_systems.values())[1]
        system.has_civilization = True
        system.is_extinct = False
        system.true_strategy = "LR"  # answers on a die roll, and the reply text is drawn too
        system.deception_level = 0.1
        system.civilization_stage = CivilizationStage.DIGITAL
        system.knowledge = 40

        rng_before = random.getstate()
        first = call(session, "send_message", system=system.name, text="hello")
        self.assertTrue(first["ok"])
        self.assertNotEqual(random.getstate(), rng_before, "sending a message must roll the dice")

        call(session, "undo")
        self.assertEqual(random.getstate(), rng_before, "undo must put the dice back")

        second = call(session, "send_message", system=system.name, text="hello")
        self.assertEqual(second["message"], first["message"])
        self.assertEqual(second["state"]["systems"], first["state"]["systems"])
        self.assertEqual(second["state"]["threats"], first["state"]["threats"])

    def test_undo_stack_empties_after_advance_generation(self):
        session = new_session(seed=11)
        name = json.loads(session.state())["systems"][0]["name"]
        self.assertTrue(call(session, "focus_research", system=name)["undo"]["available"])
        advanced = call(session, "advance_generation")
        self.assertTrue(advanced["ok"])
        self.assertEqual(advanced["undo"], {"available": False, "depth": 0})
        self.assertEqual(advanced["state"]["generation_log"], [])
        refused = call(session, "undo")
        self.assertFalse(refused["ok"])
        self.assertEqual(refused["message"], "nothing to undo")

    def test_undo_is_refused_when_there_is_nothing_to_undo(self):
        session = GameSession()
        session.new_game(seed=11)
        result = call(session, "undo")
        self.assertFalse(result["ok"])
        self.assertEqual(result["message"], "nothing to undo")
        self.assertEqual(result["undo"], {"available": False, "depth": 0})

    def test_a_refused_action_does_not_become_an_undo_step(self):
        session = new_session(seed=11)
        depth = call(session, "public_outreach")["undo"]["depth"]
        refused = call(session, "focus_research", system="Nowhere")
        self.assertFalse(refused["ok"])
        self.assertEqual(refused["undo"]["depth"], depth)

    def test_the_stack_is_capped_and_cleared_by_new_game_and_load(self):
        session = new_session(seed=11)
        name = json.loads(session.state())["systems"][0]["name"]
        for _ in range(25):
            session.program.action_points = 5
            call(session, "focus_research", system=name)
        self.assertEqual(call(session, "public_outreach")["undo"]["depth"], 20)

        text = session.save()
        session.new_game(seed=11)
        self.assertEqual(call(session, "undo")["message"], "nothing to undo")
        session.load(text)
        self.assertEqual(call(session, "undo")["message"], "nothing to undo")

    def test_undo_snapshots_are_not_written_into_saves(self):
        session = new_session(seed=11)
        name = json.loads(session.state())["systems"][0]["name"]
        call(session, "focus_research", system=name)
        payload = json.loads(session.save())
        self.assertNotIn("undo", payload)
        self.assertNotIn("_undo_stack", json.dumps(payload))
        assert_plain(self, payload)
        # The saved program carries the generation log itself, though: it is game state.
        self.assertEqual([e["action"] for e in payload["program"]["generation_log"]], ["focus_research"])


class ObservedYearTest(unittest.TestCase):
    """Light-time honesty: what we see of a system left it `distance` years ago."""

    def test_view_state_states_the_year_the_light_left(self):
        session = new_session(seed=11)
        state = json.loads(session.state())
        for system in state["systems"]:
            self.assertEqual(system["observed_year"], state["year"] - round(system["distance"]))
        advanced = call(session, "advance_generation")["state"]
        for system in advanced["systems"]:
            self.assertEqual(system["observed_year"], advanced["year"] - round(system["distance"]))

    def test_focus_research_says_when_the_light_left(self):
        session = new_session(seed=11)
        state = json.loads(session.state())
        system = state["systems"][0]
        result = call(session, "focus_research", system=system["name"])
        self.assertTrue(result["ok"])
        self.assertIn(f"The light we studied left {system['name']} in {system['observed_year']}",
                      result["message"])
