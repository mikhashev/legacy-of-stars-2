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


class LazyWowSourceTest(unittest.TestCase):
    def test_source_chosen_at_generation_144_from_known_living_civs(self):
        p = make_program(seed=6)
        p.wow_signal.reply("Hello")
        self.assertIsNone(p.wow_signal.wow_source_system)
        for system in p.star_systems.values():
            system.has_civilization = False
        target = next(iter(p.star_systems.values()))
        target.has_civilization = True
        target.is_extinct = False
        target.true_strategy = "L"
        target.civilization_stage = CivilizationStage.DIGITAL
        p.generation = 144
        self.assertTrue(p.wow_signal.check_gen144_event())
        p.wow_signal.trigger_gen144_event()
        self.assertIs(p.wow_signal.wow_source_system, target)
        self.assertEqual(p.wow_signal.outcome, "silence")
        self.assertIn("The Long Wait", p.achievements)
        self.assertFalse(p.wow_signal.check_gen144_event())  # resolves once

    def test_no_known_civilization_means_silence(self):
        p = make_program(seed=6)
        p.wow_signal.reply("")
        for system in p.star_systems.values():
            system.has_civilization = False
        p.generation = 144
        p.wow_signal.trigger_gen144_event()
        self.assertEqual(p.wow_signal.outcome, "silence")


if __name__ == "__main__":
    unittest.main()
