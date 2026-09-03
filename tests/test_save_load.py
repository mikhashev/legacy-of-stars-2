"""
Save/load: full state round trip, determinism after loading, file layer and start menu.
"""
import contextlib
import io
import json
import os
import random
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("LOS_OFFLINE", "1")

from src import save_manager  # noqa: E402
from src.game_interface import GameInterface, start_menu  # noqa: E402
from src.legacy_of_stars_v3 import CivilizationStage, ContactProgram  # noqa: E402

RANDOM = "src.legacy_of_stars_v3.random.random"


def busy_program(seed=21) -> ContactProgram:
    """A program with every kind of state populated."""
    p = ContactProgram(seed=seed, offline=True)
    systems = list(p.star_systems.values())
    friend, foe = systems[0], systems[1]
    for system, strategy in ((friend, "LB"), (foe, "LA")):
        system.has_civilization = True
        system.is_extinct = False
        system.true_strategy = strategy
        system.civilization_stage = CivilizationStage.DIGITAL
        system.civilization_type = "hybrid_integrated"
        # `send_message` (T2, the receipt frame) decides from `system.timeline_state(...)`, not
        # from these cached fields directly - without a matching timeline the forced LA strategy
        # above is invisible to it, and whether "Hello foe" schedules an attack below would
        # depend on whatever profile this system's own roll happened to produce. Give it a
        # timeline that actually matches the forced profile, the same way Genesis colonies do.
        system.set_static_timeline(p.start_year)
    p.action_points = 5
    p.send_message(friend.name, "Hello friend")
    friend.pending_responses.append(("We hear you", p.generation + 1))
    p.send_message(foe.name, "Hello foe")           # schedules an attack
    p.defend_evacuate(0)
    p.focus_research(systems[2].name)
    p.generation = 10
    for tech_id in ("seti_at_home", "ai_pattern_recognition", "bio_engineering", "genetic_pacification"):
        p.research_points = 100000
        needs_doctrine = p.research_tech(tech_id)
        if needs_doctrine:
            p.choose_doctrine(tech_id, 1)
    p.genesis.unlocked = True
    p.research_points, p.funding, p.action_points = 2000, 80, 3
    sterile = next(s for s in p.star_systems.values() if not s.has_civilization)
    sterile.knowledge = max(sterile.knowledge, 20)  # an ark needs a studied target
    ok, msg = p.genesis.seed_world(p, sterile)
    assert ok, msg
    p.add_star_system(p._next_catalog_entry(), announce=False)
    p.pending_philosophical_event = p.philosophical_events.events["expansion_instinct"]
    p.philosophical_events.events["expansion_instinct"].has_triggered = True
    p.unlock_achievement("Test Pilot")
    p.pending_info_attacks.append([foe.name, p.generation + 3])  # information attack in flight
    p.wow_signal.reply("We are here")
    p.drain_events()
    p.message = ""
    return p


class RoundTripTest(unittest.TestCase):
    def test_to_dict_round_trip_is_lossless(self):
        p = busy_program()
        data = p.to_dict()
        json.dumps(data)  # JSON-compatible
        p2 = ContactProgram.from_dict(data, offline=True)
        self.assertEqual(p2.to_dict(), data)
        self.assertEqual(list(p2.star_systems), list(p.star_systems))
        self.assertEqual(len(p2.pending_attack_warnings), 1)
        self.assertIs(p2.pending_attack_warnings[0].source, p2.star_systems[p.pending_attack_warnings[0].source.name])
        self.assertEqual(p2.pending_attack_warnings[0].defensive_actions_taken, ["Evacuation"])
        self.assertEqual(p2.pending_info_attacks, p.pending_info_attacks)
        self.assertEqual(len(p2.pending_info_attacks), 1)
        self.assertEqual(p2.pending_philosophical_event.id, "expansion_instinct")
        self.assertEqual(p2.technologies["genetic_pacification"].chosen_doctrine, "Mandatory Global Edit")
        self.assertTrue(p2.genesis.unlocked)
        self.assertEqual(len(p2.genesis.seeded_worlds), 1)
        self.assertIn("Test Pilot", p2.achievements)
        self.assertTrue(p2.wow_signal.wow_replied)
        self.assertEqual(p2.current_director.name, p.current_director.name)
        self.assertEqual(p2.tech_level, p.tech_level)
        self.assertEqual(p2.undiscovered, p.undiscovered)

    def test_loaded_game_evolves_identically(self):
        p = busy_program()
        data = p.to_dict()
        p2 = ContactProgram.from_dict(data, offline=True)
        random.seed(99)
        p.advance_generation()
        random.seed(99)
        p2.advance_generation()
        self.assertEqual(p.to_dict(), p2.to_dict())
        self.assertEqual([e.text for e in p.drain_events()], [e.text for e in p2.drain_events()])

    def test_missing_keys_get_defaults(self):
        minimal = {"state": {"generation": 3}, "star_systems": [], "directors": []}
        p = ContactProgram.from_dict(minimal, offline=True)
        self.assertEqual(p.generation, 3)
        self.assertEqual(p.public_support, 50)
        self.assertIsNotNone(p.current_director)
        self.assertEqual(p.star_systems, {})
        self.assertEqual(p.pending_info_attacks, [])  # old saves have no information attacks in flight
        p.view_state()  # renders without systems


class FileLayerTest(unittest.TestCase):
    def test_serialize_deserialize_and_version_check(self):
        p = busy_program()
        text = save_manager.serialize(p, label="Test")
        payload = json.loads(text)
        self.assertEqual(payload["format_version"], save_manager.FORMAT_VERSION)
        self.assertEqual(payload["generation"], p.generation)
        p2 = save_manager.deserialize(text, offline=True)
        self.assertEqual(p2.to_dict(), p.to_dict())
        payload["format_version"] = 99
        with self.assertRaises(save_manager.SaveError):
            save_manager.deserialize(json.dumps(payload))
        with self.assertRaises(save_manager.SaveError):
            save_manager.deserialize("not json at all")
        with self.assertRaises(save_manager.SaveError):
            save_manager.deserialize(json.dumps({"hello": "world"}))

    def test_save_load_list_and_autosave(self):
        p = busy_program()
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            first = save_manager.save_game(p, save_manager.save_path("My Game!", tmp), label="My Game!")
            self.assertEqual(first.name, "My_Game.json")
            p.generation += 1
            with mock.patch("src.save_manager.datetime") as fake_dt:
                fake_dt.datetime.now.return_value = __import__("datetime").datetime(2999, 1, 1, 12, 0, 0)
                auto = save_manager.autosave(p, tmp)
            self.assertEqual(auto.name, "autosave.json")
            (tmp / "broken.json").write_text("{", encoding="utf-8")
            saves = save_manager.list_saves(tmp)
            self.assertEqual([s.name for s in saves], ["Autosave", "My Game!"])  # newest first
            self.assertEqual(saves[0].generation, p.generation)
            loaded = save_manager.load_game(first, offline=True)
            self.assertEqual(loaded.generation, p.generation - 1)
            with self.assertRaises(save_manager.SaveError):
                save_manager.load_game(tmp / "missing.json")
        self.assertEqual(save_manager.list_saves(Path("definitely-missing-dir")), [])


class InterfaceSaveTest(unittest.TestCase):
    def test_save_key_and_autosave_on_advance(self):
        p = ContactProgram(seed=5, offline=True)
        ui = GameInterface(p)
        with tempfile.TemporaryDirectory() as tmp, mock.patch("src.save_manager.SAVE_DIR", Path(tmp)):
            items = ui.build_menu()
            with mock.patch("builtins.input", side_effect=["slot one"]), contextlib.redirect_stdout(io.StringIO()):
                ui.dispatch("s", items)
            self.assertIn("saved", p.message.lower())
            self.assertTrue((Path(tmp) / "slot_one.json").exists())
            with mock.patch(RANDOM, return_value=0.99),                     mock.patch("builtins.input", side_effect=["y"]),                     contextlib.redirect_stdout(io.StringIO()):
                ui.dispatch("5", items)
            self.assertTrue((Path(tmp) / "autosave.json").exists())
            loaded = save_manager.load_game(Path(tmp) / "autosave.json", offline=True)
            self.assertEqual(loaded.generation, 2)

    def test_start_menu_new_load_quit(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch("src.save_manager.SAVE_DIR", Path(tmp)):
            with mock.patch("builtins.input", side_effect=["3"]), contextlib.redirect_stdout(io.StringIO()):
                self.assertIsNone(start_menu())
            with mock.patch("builtins.input", side_effect=["x", "1"]), contextlib.redirect_stdout(io.StringIO()):
                fresh = start_menu()
            self.assertIsInstance(fresh, GameInterface)
            self.assertEqual(fresh.program.generation, 1)
            saved = busy_program()
            save_manager.save_game(saved, save_manager.save_path("keep", Path(tmp)))
            with mock.patch("builtins.input", side_effect=["2", "1"]), contextlib.redirect_stdout(io.StringIO()):
                loaded = start_menu()
            self.assertEqual(loaded.program.generation, saved.generation)
            self.assertTrue(loaded.program.wow_signal.decided)
            out = io.StringIO()
            with mock.patch("builtins.input", side_effect=["", "6", "y", ""]), contextlib.redirect_stdout(out):
                loaded.run_opening_scenario()  # skipped for a loaded game
                loaded.play()
            self.assertNotIn("Big Ear", out.getvalue())


if __name__ == "__main__":
    unittest.main()
