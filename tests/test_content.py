"""
ContentBank: every template renders with no leftover placeholders or error text.
"""
import json
import os
import random
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("LOS_OFFLINE", "1")

from src.content import TEMPLATES_DIR, ContentBank  # noqa: E402
from src.legacy_of_stars_v3 import CivilizationStage, ContactProgram  # noqa: E402
from src.swan_song_messages import SwanSong, SwanSongCategory, SwanSongManager  # noqa: E402

PLACEHOLDER = re.compile(r"\{[a-z_]+\}")

FULL_CTX = {
    "system": "Tau Ceti", "earth_excerpt": "Hello from Earth", "tech_tier": 2, "stage": "Digital",
    "year": 2027, "distance": "11.9", "director": "Dr. Ada Lovelace", "traits": "bold, patient",
    "existence_duration": "4200 years", "extinct_years_ago": 900, "original_excerpt": "Greetings",
}

STRATEGIES = ("LB", "LR", "LBA")
CIV_TYPES = ("biological_pure", "digital_ascended", "hybrid_integrated", None, "unknown_type")
CATEGORIES = [c.value for c in SwanSongCategory]


class TemplateFilesTest(unittest.TestCase):
    def test_all_banks_exist_and_are_valid_json(self):
        for name in ("alien_replies", "swan_songs", "wow_responses", "special_messages"):
            path = TEMPLATES_DIR / f"{name}.json"
            self.assertTrue(path.exists(), path)
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            self.assertIsInstance(data, dict)

    def test_every_alien_leaf_has_three_variants(self):
        with open(TEMPLATES_DIR / "alien_replies.json", encoding="utf-8") as f:
            data = json.load(f)
        for strategy in STRATEGIES:
            for civ_type in ("biological_pure", "digital_ascended", "hybrid_integrated", "any"):
                self.assertGreaterEqual(len(data[strategy][civ_type]), 3, (strategy, civ_type))

    def test_every_template_renders_cleanly(self):
        bank = ContentBank()
        random.seed(1)
        for strategy in STRATEGIES:
            for civ_type in CIV_TYPES:
                for _ in range(6):
                    text = bank.alien_reply(strategy, civ_type, FULL_CTX)
                    self.assertTrue(text)
                    self.assertIsNone(PLACEHOLDER.search(text), text)
        for category in CATEGORIES:
            for civ_type in ("failed_transition", "biological_pure", None):
                for _ in range(6):
                    text = bank.swan_song(category, civ_type, FULL_CTX)
                    self.assertIsNone(PLACEHOLDER.search(text), text)
                    if civ_type == "failed_transition":
                        self.assertIn("[Analysis", text)
        for _ in range(6):
            self.assertIsNone(PLACEHOLDER.search(bank.wow_friendly(FULL_CTX)))
            self.assertIsNone(PLACEHOLDER.search(bank.director_message(FULL_CTX)))
            for key in ("mirror_friendly", "mirror_hostile", "genesis_greeting", "genesis_hostile"):
                self.assertIsNone(PLACEHOLDER.search(bank.special(key, FULL_CTX)), key)

    def test_swan_song_plea_and_warning_read_as_automated_relays(self):
        # A civilization's last *living* transmission can only reach us once, `distance` years
        # after it was sent. Anything we can still receive after that must be an automated,
        # repeating beacon - so every one-shot-sounding plea (and the "eleven days" warning)
        # must read as a relay, not a live broadcast.
        with open(TEMPLATES_DIR / "swan_songs.json", encoding="utf-8") as f:
            data = json.load(f)
        for template in data["plea"]:
            self.assertTrue("RELAY" in template or "repeat" in template, template)
        eleven_days_warning = next(t for t in data["warning"] if "eleven days" in t)
        self.assertTrue("RELAY" in eleven_days_warning or "repeat" in eleven_days_warning)

    def test_unknown_placeholder_stays_visible_and_missing_bank_falls_back(self):
        self.assertEqual(ContentBank.fill("{system} says {nothing}", {"system": "X"}), "X says {nothing}")
        bank = ContentBank(templates_dir=Path("no-such-dir"))
        text = bank.alien_reply("LB", None, {"system": "Vega"})
        self.assertIn("Vega", text)
        self.assertIsNone(PLACEHOLDER.search(text))


class SwanSongOfflineTest(unittest.TestCase):
    def test_text_is_generated_lazily_and_offline(self):
        manager = SwanSongManager(ai_manager=None)
        song = manager.create_swan_song("Wolf 359", 1200, 5000.0, "failed_transition")
        self.assertIsNone(song.message)
        song.knowledge = 100
        random.seed(3)
        result = manager.discover_swan_song("Wolf 359", 100)
        self.assertNotIn("error", result)
        self.assertEqual(result["system"], "Wolf 359")
        self.assertGreater(len(result["message"]), 100)
        self.assertIn("[Analysis", result["message"])
        self.assertNotIn("AI Error", result["message"])
        self.assertEqual(result["category"], song.category)
        self.assertIn(song.category, CATEGORIES)

    def test_engine_creates_swan_songs_without_network(self):
        program = ContactProgram(seed=11, offline=True)
        extinct = [s for s in program.star_systems.values() if s.has_civilization and s.is_extinct and s.has_swan_song]
        for system in extinct:
            self.assertTrue(program.swan_song_manager.has_swan_song(system.name))
            self.assertIsNone(program.swan_song_manager.swan_songs[system.name].message)


class EngineReplyTest(unittest.TestCase):
    def test_reply_context_and_templates(self):
        program = ContactProgram(seed=12, offline=True)
        system = next(iter(program.star_systems.values()))
        system.has_civilization = True
        system.is_extinct = False
        system.civilization_stage = CivilizationStage.INTERPLANETARY
        for civ_type in ("biological_pure", "digital_ascended", "hybrid_integrated"):
            system.civilization_type = civ_type
            for strategy in STRATEGIES:
                text = program._compose_alien_reply(system, strategy, "We come in peace\nfrom Earth")
                self.assertIsNone(PLACEHOLDER.search(text), text)
                self.assertNotIn("AI Error", text)
        ctx = program._reply_context(system, "x" * 200)
        self.assertTrue(ctx["earth_excerpt"].endswith("..."))
        self.assertEqual(ctx["stage"], "Interplanetary")

    def test_director_message_and_wow_response_offline(self):
        program = ContactProgram(seed=12, offline=True)
        draft = program.compose_director_message()
        self.assertIn(program.current_director.name, draft)
        system = next(iter(program.star_systems.values()))
        text = program.compose_wow_response(system, "Greetings from Earth")
        self.assertTrue(text)
        self.assertIsNone(PLACEHOLDER.search(text))


if __name__ == "__main__":
    unittest.main()
