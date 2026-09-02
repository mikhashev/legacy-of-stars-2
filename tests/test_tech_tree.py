"""
Technology tree: data integrity, generation gating, legacy knowledge, special effects.
"""
import json
import os
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("LOS_OFFLINE", "1")

from src.legacy_of_stars_v3 import ContactProgram  # noqa: E402

TECH_TREE = ROOT / "data" / "tech_tree.json"
ENGINE_SOURCE = (ROOT / "src" / "legacy_of_stars_v3.py").read_text(encoding="utf-8")


def make_program(seed=41):
    return ContactProgram(seed=seed, offline=True)


class TechTreeDataTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(TECH_TREE, encoding="utf-8") as f:
            cls.techs = json.load(f)["technologies"]
        cls.by_id = {t["id"]: t for t in cls.techs}

    def test_tree_shape(self):
        self.assertGreaterEqual(len(self.techs), 44)
        self.assertEqual(len(self.by_id), len(self.techs))
        self.assertEqual({t["tier"] for t in self.techs}, {0, 1, 2, 3, 4, 5})
        for tech in self.techs:
            for key in ("id", "name", "description", "tier", "min_generation", "cost", "prerequisites", "category"):
                self.assertIn(key, tech, tech["id"])
            self.assertGreater(tech["cost"], 0)

    def test_prerequisites_exist_and_come_from_lower_or_equal_tiers(self):
        for tech in self.techs:
            for prereq in tech["prerequisites"]:
                self.assertIn(prereq, self.by_id, f"{tech['id']} needs unknown {prereq}")
                self.assertLessEqual(self.by_id[prereq]["tier"], tech["tier"], f"{tech['id']} <- {prereq}")

    def test_every_special_effect_is_handled_by_the_engine(self):
        for tech in self.techs:
            special = tech.get("special")
            if special:
                self.assertIn(f'"{special}"', ENGINE_SOURCE, f"unhandled special effect {special} ({tech['id']})")

    def test_passive_rp_is_documented_in_descriptions(self):
        for tech in self.techs:
            if tech.get("passive_rp"):
                self.assertRegex(tech["description"], r"RP/turn|research points/turn", tech["id"])

    def test_historical_chronology(self):
        self.assertEqual(self.by_id["seti_at_home"]["min_generation"], 1)        # launched 1999
        self.assertEqual(self.by_id["breakthrough_listen"]["min_generation"], 2)  # launched 2015
        for tech_id, year in (("arecibo_telescope", "1963"), ("drake_equation", "1961")):
            self.assertIn(year, self.by_id[tech_id]["year_context"] + self.by_id[tech_id]["description"])

    def test_doctrine_options_are_complete(self):
        for tech in self.techs:
            doctrine = tech.get("doctrine_choice")
            if doctrine:
                self.assertTrue(doctrine.get("options"), tech["id"])
                for option in doctrine["options"]:
                    self.assertIn("effects", option)


class TechTreeEngineTest(unittest.TestCase):
    def test_legacy_knowledge_is_pre_researched(self):
        p = make_program()
        legacy = [t for t in p.technologies.values() if t.is_legacy]
        researched = [t for t in p.technologies.values() if t.researched]
        self.assertEqual(len(legacy), 5)
        self.assertEqual(set(t.id for t in legacy), set(ContactProgram.LEGACY_TECHS))
        self.assertEqual(len(legacy), len(researched))
        context = p._build_tech_context()
        self.assertIn("Baseline (1977)", context)
        self.assertIn("Tier 0", context)

    def test_generation_gating(self):
        p = make_program()
        tech = p.technologies["deep_space_network"]  # Gen 2+
        p.research_points = 1000
        self.assertFalse(p.research_tech(tech.id))
        self.assertFalse(tech.researched)
        self.assertIn("Unlocks in Generation 2", p.message)
        p.generation = 2
        p.research_tech(tech.id)
        self.assertTrue(tech.researched)
        self.assertNotIn(tech, p.available_technologies())

    def test_prerequisites_and_cost_are_enforced(self):
        p = make_program()
        p.generation = 5
        p.research_points = 10000
        self.assertFalse(p.research_tech("orbital_defense_grid"))
        self.assertIn("Prerequisite not met", p.message)
        p.research_points = 10
        self.assertFalse(p.research_tech("global_education"))
        self.assertIn("Not enough Research Points", p.message)

    def test_special_effects_apply(self):
        p = make_program()
        p.generation = 10
        for tech_id in ("arecibo_telescope", "deep_space_network", "ska_telescope", "orbital_defense_grid", "distributed_colonies"):
            p.research_points = 100000
            p.research_tech(tech_id)
            self.assertTrue(p.technologies[tech_id].researched, p.message)
        self.assertAlmostEqual(p.passive_defense_bonus, 0.6)
        self.assertTrue(p.has_backup_colonies)
        self.assertEqual(p.tech_level, 5)

    def test_tier_zero_available_from_the_start(self):
        p = make_program()
        p.research_points = 10000
        for tech in [t for t in p.technologies.values() if t.tier == 0 and not t.researched]:
            p.research_tech(tech.id)
            self.assertTrue(tech.researched, tech.id)

    def test_swan_song_discount_is_consumed(self):
        p = make_program()
        p.swan_song_manager.next_tech_discount = 0.25
        p.research_points = 5
        p.research_tech("global_education")
        self.assertFalse(p.technologies["global_education"].researched)
        self.assertEqual(p.swan_song_manager.next_tech_discount, 0.25)  # a failed purchase keeps the discount
        p.research_points = 100
        p.research_tech("global_education")
        self.assertTrue(p.technologies["global_education"].researched)
        self.assertIn("Discounted by 25%", p.message)
        self.assertEqual(p.swan_song_manager.next_tech_discount, 0.0)


if __name__ == "__main__":
    unittest.main()
