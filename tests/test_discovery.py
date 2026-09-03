"""
Star catalog and discovery: systems are catalogued over the game, driven by detection technologies.
"""
import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("LOS_OFFLINE", "1")

from src.legacy_of_stars_v3 import CATALOG_PATH, CivilizationStage, ContactProgram, load_star_catalog  # noqa: E402
from src.wow_signal_event import WOW_SOURCE_NAME  # noqa: E402

RANDOM = "src.legacy_of_stars_v3.random.random"


def make_program(seed=1):
    return ContactProgram(seed=seed, offline=True)


class CatalogFileTest(unittest.TestCase):
    def test_catalog_is_valid_and_sorted(self):
        with open(CATALOG_PATH, encoding="utf-8") as f:
            stars = json.load(f)["stars"]
        self.assertGreaterEqual(len(stars), 40)
        names = [s["name"] for s in stars]
        self.assertEqual(len(names), len(set(names)))
        for star in stars:
            self.assertGreater(star["distance"], 0)
            self.assertTrue(0 <= star["ra"] < 360, star)
            self.assertTrue(-90 <= star["dec"] <= 90, star)
            self.assertTrue(star["spectral_type"])
        loaded = load_star_catalog()
        self.assertEqual([s["distance"] for s in loaded], sorted(s["distance"] for s in loaded))

    def test_missing_catalog_falls_back_to_synthetic_neighbourhood(self):
        self.assertEqual(load_star_catalog(Path("no-such-catalog.json")), [])
        with mock.patch("src.legacy_of_stars_v3.load_star_catalog", return_value=[]):
            p = make_program(seed=1)
        self.assertEqual(len(p.star_systems), 5)
        self.assertEqual(len(p.undiscovered), 3)


class StartingSystemsTest(unittest.TestCase):
    def test_five_nearby_systems_at_start(self):
        p = make_program(seed=2)
        self.assertEqual(len(p.star_systems), 5)
        eighth_nearest = p.catalog[7]["distance"]
        for system in p.star_systems.values():
            self.assertLessEqual(system.distance, eighth_nearest)
            self.assertIsNotNone(system.ra)
            self.assertIsNotNone(system.dec)
            self.assertTrue(system.spectral_type)
        self.assertEqual(len(p.undiscovered), len(p.catalog) - 5)
        self.assertFalse(set(p.undiscovered) & set(p.star_systems))

    def test_discovery_chance_grows_with_detection_techs_and_caps(self):
        p = make_program(seed=2)
        self.assertAlmostEqual(p.discovery_chance(), 0.25)  # base 0.10 + Arecibo 0.10 + Project Ozma 0.05
        for tech in p.technologies.values():
            tech.researched = True
        self.assertAlmostEqual(p.discovery_chance(), 0.85)


class DiscoveryTest(unittest.TestCase):
    def test_one_system_per_generation_when_rolls_succeed_nearest_first(self):
        p = make_program(seed=3)
        known = len(p.star_systems)
        with mock.patch(RANDOM, return_value=0.0):
            for _ in range(3):
                nearest_remaining = min(p._catalog_entry(n)["distance"] for n in p.undiscovered)
                p.advance_generation()
                self.assertEqual(len(p.star_systems), known + 1)
                newest = list(p.star_systems.values())[-1]
                self.assertAlmostEqual(newest.distance, nearest_remaining)
                known += 1
        self.assertEqual(p.stats["systems_discovered"], 3)
        self.assertTrue(any(e.kind == "system_discovered" for e in p.drain_events()))

    def test_no_discovery_when_rolls_fail(self):
        p = make_program(seed=3)
        with mock.patch(RANDOM, return_value=0.99):
            p.advance_generation()
        self.assertEqual(len(p.star_systems), 5)

    def test_discovered_extinct_systems_get_swan_songs_and_catalog_exhausts(self):
        p = make_program(seed=4)
        while p.undiscovered:
            p.add_star_system(p._next_catalog_entry(), announce=False)
        self.assertEqual(len(p.star_systems), len(p.catalog))
        for system in p.star_systems.values():
            if system.has_civilization and system.is_extinct and system.has_swan_song:
                self.assertTrue(p.swan_song_manager.has_swan_song(system.name))
        self.assertEqual(p.discover_systems(), [])

    def test_mirror_contact_uses_catalog_star(self):
        p = make_program(seed=5)
        catalog_names = {s["name"] for s in p.catalog}
        with mock.patch(RANDOM, return_value=0.1):
            p.resolve_mirror_contact()
        newest = list(p.star_systems.values())[-1]
        self.assertIn(newest.name, catalog_names)
        self.assertIsNotNone(newest.ra)
        self.assertNotIn(newest.name, p.undiscovered)

    def test_view_state_reports_catalog_progress(self):
        p = make_program(seed=5)
        catalog = p.view_state()["catalog"]
        self.assertEqual(catalog["known"], 5)
        self.assertEqual(catalog["total"], len(p.catalog))
        self.assertAlmostEqual(catalog["discovery_chance"], 0.25)


class WowSourceSystemTest(unittest.TestCase):
    """Replying to the WOW! signal puts a real star 1,800 LY away on the target list."""

    @staticmethod
    def _replied_program(seed=6):
        p = make_program(seed=seed)
        p.wow_signal.reply("Hello")
        p.public_support = 100
        p.funding = 100
        return p

    def test_reply_catalogues_the_source_star(self):
        p = self._replied_program()
        source = p.wow_signal.wow_source_system
        self.assertIsNotNone(source)
        self.assertEqual(source.name, WOW_SOURCE_NAME)
        self.assertIs(p.star_systems[WOW_SOURCE_NAME], source)
        self.assertEqual(source.distance, 1800.0)
        self.assertTrue(source.is_wow_source)
        self.assertIn("G2V", source.spectral_type)
        self.assertAlmostEqual(source.ra, 293.7)
        self.assertAlmostEqual(source.dec, -27.0)
        # 1,800 LY out and back is exactly the 144 generations of the event.
        self.assertEqual(source.get_round_trip_time(), 144)
        # It is not a catalog star, so discovery and mirror contact can never pick it.
        self.assertNotIn(WOW_SOURCE_NAME, [entry["name"] for entry in p.catalog])
        self.assertNotIn(WOW_SOURCE_NAME, p.undiscovered)
        # 1,800 LY is far outside the leakage front (year - 1935), so passive leakage ignores it.
        year = p.start_year + (p.generation - 1) * 25
        self.assertGreater(source.distance, p.leakage_system.leakage_front(year))
        self.assertEqual(p.leakage_system.leakage_front(year), year - 1935)

    def test_the_player_can_message_the_source(self):
        p = self._replied_program()
        source = p.wow_signal.wow_source_system
        p.action_points = 2
        p.send_message(WOW_SOURCE_NAME, "Still here")
        self.assertEqual(source.messages_sent[-1]["text"], "Still here")

    def _resolve_at_144(self, program, strategy):
        source = program.wow_signal.wow_source_system
        if strategy is None:
            source.has_civilization = False
            source._clear_civilization()
        else:
            source.has_civilization = True
            source.timeline = None   # hand-written: static, so year 3777 reads these fields
            source.is_extinct = False
            source.true_strategy = strategy
            source.civilization_stage = CivilizationStage.DIGITAL
            source.civilization_type = "biological_pure"
        program.generation = 144
        self.assertTrue(program.wow_signal.check_gen144_event())
        program.wow_signal.trigger_gen144_event()
        self.assertFalse(program.wow_signal.check_gen144_event())  # resolves once

    def test_hostile_source_answers_with_an_information_attack(self):
        p = self._replied_program()
        support, funding, evidence = p.public_support, p.funding, p.fermi_evidence["dark_forest_evidence"]
        self._resolve_at_144(p, "LA")
        self.assertEqual(p.wow_signal.outcome, "hostile")
        self.assertEqual(p.pending_attack_warnings, [])  # no fleet can cross 1,800 LY
        self.assertEqual(p.stats["info_attacks"], 1)
        self.assertEqual(p.stats["attacks_scheduled"], 0)
        self.assertLessEqual(p.public_support, support - 20)
        self.assertLessEqual(p.funding, funding - 10)
        self.assertEqual(p.fermi_evidence["dark_forest_evidence"], evidence + 3)  # +1 attack, +2 outcome
        self.assertIn("The WOW! Reckoning", p.achievements)
        text = " ".join(e.text for e in p.drain_events() if e.kind == "wow")
        self.assertIn("eighteen thousand years", text)
        self.assertNotIn("weapons to reach us", text)

    def test_friendly_source_answers_after_3600_years(self):
        p = self._replied_program()
        self._resolve_at_144(p, "LB")
        self.assertEqual(p.wow_signal.outcome, "friendly")
        self.assertEqual(p.public_support, 100)
        self.assertIn("The WOW! Response", p.achievements)
        self.assertEqual(p.pending_attack_warnings, [])

    def test_natural_source_means_silence(self):
        p = self._replied_program()
        self._resolve_at_144(p, None)
        self.assertEqual(p.wow_signal.outcome, "silence")
        self.assertIn("The Long Wait", p.achievements)

    def test_save_round_trip_keeps_the_source(self):
        p = self._replied_program()
        source = p.wow_signal.wow_source_system
        restored = ContactProgram.from_dict(p.to_dict(), offline=True)
        loaded = restored.wow_signal.wow_source_system
        self.assertIsNotNone(loaded)
        self.assertIs(loaded, restored.star_systems[WOW_SOURCE_NAME])
        self.assertEqual(loaded.distance, 1800.0)
        self.assertTrue(loaded.is_wow_source)
        self.assertEqual(loaded.has_civilization, source.has_civilization)
        self.assertEqual(loaded.true_strategy, source.true_strategy)

    def test_old_save_without_the_source_recreates_it(self):
        p = self._replied_program()
        data = p.to_dict()
        data["star_systems"] = [s for s in data["star_systems"] if s["name"] != WOW_SOURCE_NAME]
        data["wow_signal"]["wow_source_name"] = None
        data["wow_signal"]["wow_replied"] = True
        restored = ContactProgram.from_dict(data, offline=True)
        loaded = restored.wow_signal.wow_source_system
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.name, WOW_SOURCE_NAME)
        self.assertEqual(loaded.distance, 1800.0)
        self.assertTrue(loaded.is_wow_source)
        self.assertIn(WOW_SOURCE_NAME, restored.star_systems)

    def test_silent_old_save_does_not_invent_a_source(self):
        p = make_program(seed=6)
        p.wow_signal.stay_silent()
        restored = ContactProgram.from_dict(p.to_dict(), offline=True)
        self.assertIsNone(restored.wow_signal.wow_source_system)
        self.assertNotIn(WOW_SOURCE_NAME, restored.star_systems)


if __name__ == "__main__":
    unittest.main()
