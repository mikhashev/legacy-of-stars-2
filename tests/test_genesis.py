"""
Genesis Project basics (the outcomes are covered in test_mechanics).
"""
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("LOS_OFFLINE", "1")

from src.genesis_project import GenesisProject, SeededWorld  # noqa: E402
from src.legacy_of_stars_v3 import ContactProgram  # noqa: E402


class GenesisProjectTest(unittest.TestCase):
    def setUp(self):
        self.program = ContactProgram(seed=71, offline=True)

    def test_locked_by_default(self):
        self.assertFalse(self.program.genesis.unlocked)
        self.assertEqual(self.program.genesis.seeds_this_gen, 0)
        self.assertNotIn("genesis_seed", [a.id for a in self.program.available_actions()])
        system = next(iter(self.program.star_systems.values()))
        success, msg = self.program.genesis.seed_world(self.program, system)
        self.assertFalse(success)
        self.assertIn("not yet researched", msg)
        self.assertEqual(self.program.genesis.get_summary(), "Genesis Project: Locked")

    def test_seeding_checks_resources(self):
        genesis = self.program.genesis
        genesis.unlocked = True
        sterile = next(s for s in self.program.star_systems.values() if not s.has_civilization)
        self.program.research_points = 10
        self.assertIn("Research Points", genesis.seed_world(self.program, sterile)[1])
        self.program.research_points = 1000
        self.program.funding = 10
        self.assertIn("Funding", genesis.seed_world(self.program, sterile)[1])
        self.program.funding = 60
        self.program.action_points = 0
        self.assertIn("Action Points", genesis.seed_world(self.program, sterile)[1])
        self.program.action_points = 1
        ok, msg = genesis.seed_world(self.program, sterile)
        self.assertTrue(ok, msg)
        self.assertIn(sterile.name, genesis.get_summary())
        self.assertIn("Microbial", genesis.get_summary())

    def test_world_evolution_stages(self):
        genesis = GenesisProject()
        genesis.unlocked = True
        world = SeededWorld("Vega", 10)
        genesis.seeded_worlds["Vega"] = world
        self.program.star_systems["Vega"] = next(iter(self.program.star_systems.values()))
        for generation, stage in ((15, 0), (20, 1), (36, 2)):
            self.program.generation = generation
            genesis.advance_generation(self.program)
            self.assertEqual(world.evolution_stage, stage, generation)
        self.assertEqual(world.stage_name, "Intelligence")
        events = [e.kind for e in self.program.drain_events()]
        self.assertEqual(events.count("genesis"), 2)

    def test_round_trip(self):
        genesis = GenesisProject()
        genesis.unlocked = True
        genesis.seeded_worlds["Vega"] = SeededWorld("Vega", 12)
        genesis.seeded_worlds["Vega"].evolution_stage = 2
        restored = GenesisProject.from_dict(genesis.to_dict())
        self.assertTrue(restored.unlocked)
        self.assertEqual(restored.seeded_worlds["Vega"].evolution_stage, 2)
        self.assertEqual(restored.to_dict(), genesis.to_dict())


if __name__ == "__main__":
    unittest.main()
