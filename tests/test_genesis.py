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

from src.genesis_project import GenesisProject, SeededWorld, ark_arrival_generation  # noqa: E402
from src.legacy_of_stars_v3 import ContactProgram, StarSystem  # noqa: E402


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
        arrival = ark_arrival_generation(self.program.generation, sterile.distance)
        self.assertEqual(genesis.seeded_worlds[sterile.name].arrival_gen, arrival)
        self.assertIn(f"Generation {arrival}", msg)
        self.assertIn(sterile.name, genesis.get_summary())
        self.assertIn("In transit", genesis.get_summary())

    def test_seeding_an_evolved_star_is_refused(self):
        genesis = self.program.genesis
        genesis.unlocked = True
        self.program.research_points, self.program.funding, self.program.action_points = 1000, 80, 2
        for spectral_type in ("K0III", "DZ8"):
            system = StarSystem(f"Dead {spectral_type}", 12.0, spectral_type)
            self.program.star_systems[system.name] = system
            ok, msg = genesis.seed_world(self.program, system)
            self.assertFalse(ok)
            self.assertEqual(msg, f"No habitable planet: {spectral_type} star.")
        self.assertEqual(genesis.seeded_worlds, {})

    def test_arrival_generation_uses_fusion_speed(self):
        # 12 LY at 0.12c is 100 years, four generations of flight.
        self.assertEqual(ark_arrival_generation(10, 12.0), 14)
        self.assertEqual(ark_arrival_generation(1, 4.2), 3)

    def test_world_evolution_stages(self):
        genesis = GenesisProject()
        genesis.unlocked = True
        world = SeededWorld("Vega", 10, arrival_gen=14)
        genesis.seeded_worlds["Vega"] = world
        self.program.star_systems["Vega"] = next(iter(self.program.star_systems.values()))
        # In transit until the ark lands in Gen 14, then founded / self-sustaining / industrial.
        for generation, stage in ((13, 0), (14, 1), (24, 2), (39, 3)):
            self.program.generation = generation
            genesis.advance_generation(self.program)
            self.assertEqual(world.evolution_stage, stage, generation)
        self.assertEqual(world.stage_name, "Industrial")
        events = [e.kind for e in self.program.drain_events()]
        self.assertEqual(events.count("genesis"), 3)

    def test_round_trip(self):
        genesis = GenesisProject()
        genesis.unlocked = True
        genesis.seeded_worlds["Vega"] = SeededWorld("Vega", 12, arrival_gen=16)
        genesis.seeded_worlds["Vega"].evolution_stage = 2
        restored = GenesisProject.from_dict(genesis.to_dict())
        self.assertTrue(restored.unlocked)
        self.assertEqual(restored.seeded_worlds["Vega"].evolution_stage, 2)
        self.assertEqual(restored.seeded_worlds["Vega"].arrival_gen, 16)
        self.assertEqual(restored.to_dict(), genesis.to_dict())

    def test_old_save_without_arrival_defaults_to_the_seed_generation(self):
        world = SeededWorld.from_dict({"system_name": "Vega", "seed_gen": 12, "evolution_stage": 1})
        self.assertEqual(world.arrival_gen, 12)


if __name__ == "__main__":
    unittest.main()
