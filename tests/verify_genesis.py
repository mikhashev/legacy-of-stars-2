import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.legacy_of_stars_v3 import ContactProgram


class TestGenesisProject(unittest.TestCase):

    def setUp(self):
        self.program = ContactProgram()

    def test_genesis_attribute_exists(self):
        self.assertTrue(hasattr(self.program, "genesis"))

    def test_genesis_locked_by_default(self):
        self.assertFalse(self.program.genesis.unlocked)

    def test_genesis_seeds_this_gen_zero(self):
        self.assertEqual(self.program.genesis.seeds_this_gen, 0)

    def test_seed_world_fails_when_locked(self):
        system = next(iter(self.program.star_systems.values()))
        success, msg = self.program.genesis.seed_world(self.program, system)
        self.assertFalse(success)
        self.assertIn("not yet researched", msg)


if __name__ == "__main__":
    unittest.main()
