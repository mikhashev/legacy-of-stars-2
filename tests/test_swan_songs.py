"""
Swan Song Messages: creation, discovery thresholds, rewards, and the in-game action.
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

from src.legacy_of_stars_v3 import ContactProgram  # noqa: E402
from src.swan_song_messages import SwanSong, SwanSongCategory, SwanSongManager  # noqa: E402

SONG_RANDOM = "src.swan_song_messages.random.random"


class SwanSongManagerTest(unittest.TestCase):
    def test_creation_and_status(self):
        manager = SwanSongManager()
        manager.create_swan_song("Alpha Centauri", 1500, 50000)
        manager.create_swan_song("Wolf 359", 500, 10000, "failed_transition")
        self.assertTrue(manager.has_swan_song("Alpha Centauri"))
        self.assertFalse(manager.has_swan_song("Sirius"))
        self.assertFalse(manager.is_discovered("Alpha Centauri"))
        self.assertEqual(manager.get_all_swan_songs_status(), {"Alpha Centauri": False, "Wolf 359": False})
        for song in manager.swan_songs.values():
            self.assertIn(song.category, [c.value for c in SwanSongCategory])
            self.assertIsNone(song.message)  # generated lazily

    def test_discovery_thresholds(self):
        manager = SwanSongManager()
        manager.create_swan_song("Proxima Centauri", 2000, 100000)
        self.assertIn("Insufficient knowledge", manager.discover_swan_song("Proxima Centauri", 20)["error"])
        with mock.patch(SONG_RANDOM, return_value=0.9):  # roll fails at 50% knowledge (66% chance)
            self.assertIn("Deep scan in progress", manager.discover_swan_song("Proxima Centauri", 50)["error"])
        result = manager.discover_swan_song("Proxima Centauri", 100)  # 100% chance
        self.assertNotIn("error", result)
        self.assertEqual(result["system"], "Proxima Centauri")
        self.assertGreater(len(result["message"]), 100)
        self.assertIn("already discovered", manager.discover_swan_song("Proxima Centauri", 100)["error"].lower())
        self.assertIn("No swan song", manager.discover_swan_song("Nowhere", 100)["error"])

    def test_rewards_by_category(self):
        expectations = {
            "warning": {"knowledge", "research_points", "public_support"},
            "archive": {"knowledge", "research_points", "tech_hint"},
            "technical": {"research_points", "tech_discount"},
            "plea": {"knowledge", "research_points", "public_support"},
            "philosophy": {"knowledge", "public_support", "research_points"},
        }
        for category, keys in expectations.items():
            song = SwanSong("X", category, 1000, 5000.0)
            self.assertTrue(keys <= set(song.rewards), category)
        ancient = SwanSong("Y", "archive", 1000, 200000.0)
        self.assertEqual(ancient.rewards["research_points"], 250)
        self.assertIn("Ancient", ancient.rewards["message"])

    def test_tech_discount_accumulates_and_is_consumed(self):
        manager = SwanSongManager()
        manager.swan_songs["T1"] = SwanSong("T1", "technical", 1000, 5000.0)
        manager.swan_songs["T2"] = SwanSong("T2", "technical", 1000, 5000.0)
        manager.discover_swan_song("T1", 100)
        manager.discover_swan_song("T2", 100)
        self.assertAlmostEqual(manager.next_tech_discount, 0.5)
        self.assertAlmostEqual(manager.get_tech_discount(), 0.5)
        self.assertEqual(manager.get_tech_discount(), 0.0)


class SwanSongActionTest(unittest.TestCase):
    def _extinct_program(self):
        p = ContactProgram(seed=51, offline=True)
        system = next(iter(p.star_systems.values()))
        system.has_civilization = True
        system.is_extinct = True
        system.extinct_years_ago = 1200
        system.civilization_age = 8000
        system.has_swan_song = True
        system.civilization_type = "failed_transition"
        system.true_strategy = None
        system.civilization_stage = None
        p.swan_song_manager.swan_songs.pop(system.name, None)
        p._register_swan_song(system)
        return p, system

    def test_listening_applies_rewards_evidence_and_achievement(self):
        p, system = self._extinct_program()
        self.assertIn(system.name, p.undiscovered_swan_songs())
        self.assertIn("listen_swan_song", [a.id for a in p.available_actions()])
        system.knowledge = 100
        p.action_points = 2
        rp, knowledge = p.research_points, p.knowledge_base
        with mock.patch(SONG_RANDOM, return_value=0.0):
            p.listen_for_swan_song(system.name)
        self.assertEqual(p.action_points, 1)
        self.assertIn("SWAN SONG DISCOVERED", p.message)
        self.assertGreater(p.research_points, rp)
        self.assertGreaterEqual(p.knowledge_base, knowledge)
        self.assertEqual(p.fermi_evidence["extinction_evidence"], 2)
        self.assertEqual(p.stats["swan_songs_found"], 1)
        self.assertIn("Archivist", p.achievements)
        self.assertNotIn(system.name, p.undiscovered_swan_songs())
        p.listen_for_swan_song(system.name)
        self.assertIn("already discovered", p.message.lower())

    def test_listening_needs_knowledge_and_action_points(self):
        p, system = self._extinct_program()
        system.knowledge = 10
        p.action_points = 1
        p.listen_for_swan_song(system.name)
        self.assertIn("Insufficient knowledge", p.message)
        self.assertEqual(p.action_points, 0)
        p.listen_for_swan_song(system.name)
        self.assertIn("Not enough Action Points", p.message)

    def test_non_extinct_system_has_nothing_to_hear(self):
        p, _ = self._extinct_program()
        other = list(p.star_systems.values())[1]
        other.has_civilization = False
        p.action_points = 1
        p.listen_for_swan_song(other.name)
        self.assertIn("does not contain an extinct civilization", p.message)


if __name__ == "__main__":
    unittest.main()
