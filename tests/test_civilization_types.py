"""
Test suite for Civilization Types (Phase 3A.2)

Tests that alien civilizations are assigned appropriate types based on
whether they solved the Dual DNA integration crisis.
"""

import sys
from pathlib import Path

# Add root directory to path
root_path = Path(__file__).parent.parent
sys.path.insert(0, str(root_path))

# Fix UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import random
random.seed(42)  # Reproducible tests

from src.legacy_of_stars_v3 import StarSystem


def test_civilization_types_assigned():
    """Test that all civilizations with culture get a type assigned"""
    systems = []
    for i in range(100):
        system = StarSystem(f"Test-{i}", random.uniform(10, 50))
        if system.has_civilization:
            systems.append(system)
    
    # All civilizations should have a type
    for system in systems:
        assert system.civilization_type is not None, f"{system.name} has no civilization type"
        assert system.civilization_type in [
            "biological_pure", "digital_ascended", "hybrid_integrated", "failed_transition"
        ], f"Invalid type: {system.civilization_type}"
    
    print(f"✓ Civilization types assigned test passed ({len(systems)} civilizations)")


def test_extinct_civs_mostly_failed_transition():
    """Test that ~70% of extinct civilizations are failed_transition"""
    extinct_systems = []
    for i in range(500):  # Large sample for statistical accuracy
        system = StarSystem(f"Test-{i}", random.uniform(10, 50))
        if system.has_civilization and system.is_extinct:
            extinct_systems.append(system)
    
    failed_count = sum(1 for s in extinct_systems if s.civilization_type == "failed_transition")
    total_extinct = len(extinct_systems)
    
    if total_extinct > 0:
        failed_percentage = (failed_count / total_extinct) * 100
        
        # Allow some variance (60-80% range)
        assert 60 <= failed_percentage <= 80, \
            f"Expected ~70% failed_transition, got {failed_percentage:.1f}% ({failed_count}/{total_extinct})"
        
        print(f"✓ Extinct civilization distribution test passed ({failed_percentage:.1f}% failed_transition)")
    else:
        print("⚠ No extinct civilizations generated in sample (test skipped)")


def test_living_civs_never_failed_transition():
    """Test that living civilizations are never failed_transition"""
    living_systems = []
    for i in range(200):
        system = StarSystem(f"Test-{i}", random.uniform(10, 50))
        if system.has_civilization and not system.is_extinct:
            living_systems.append(system)
    
    for system in living_systems:
        assert system.civilization_type != "failed_transition", \
            f"Living civilization {system.name} has failed_transition type"
    
    print(f"✓ Living civilizations type exclusion test passed ({len(living_systems)} civilizations)")


def test_type_distribution_in_living_civs():
    """Test that living civilizations have reasonable type distribution"""
    living_systems = []
    for i in range(500):
        system = StarSystem(f"Test-{i}", random.uniform(10, 50))
        if system.has_civilization and not system.is_extinct:
            living_systems.append(system)
    
    if len(living_systems) > 0:
        type_counts = {
            "biological_pure": 0,
            "digital_ascended": 0,
            "hybrid_integrated": 0
        }
        
        for system in living_systems:
            type_counts[system.civilization_type] += 1
        
        total = len(living_systems)
        print(f"\n  Type Distribution ({total} living civilizations):")
        print(f"    Biological Pure: {type_counts['biological_pure']} ({type_counts['biological_pure']/total*100:.1f}%)")
        print(f"    Digital Ascended: {type_counts['digital_ascended']} ({type_counts['digital_ascended']/total*100:.1f}%)")
        print(f"    Hybrid Integrated: {type_counts['hybrid_integrated']} ({type_counts['hybrid_integrated']/total*100:.1f}%)")
        
        # Biological should be most common (weight 20), hybrid least common (weight 10)
        assert type_counts["biological_pure"] >= type_counts["digital_ascended"], \
            "Biological should be more common than digital"
        assert type_counts["digital_ascended"] >= type_counts["hybrid_integrated"], \
            "Digital should be more common than hybrid"
        
        print("✓ Type distribution test passed")
    else:
        print("⚠ No living civilizations generated in sample (test skipped)")


def test_systems_without_civilization():
    """Test that systems without civilizations have None type"""
    empty_systems = []
    for i in range(100):
        system = StarSystem(f"Test-{i}", random.uniform(10, 50))
        if not system.has_civilization:
            empty_systems.append(system)
    
    for system in empty_systems:
        assert system.civilization_type is None, \
            f"Empty system {system.name} has civilization type {system.civilization_type}"
    
    print(f"✓ Empty systems test passed ({len(empty_systems)} empty systems)")


def run_all_tests():
    """Run all civilization type tests"""
    print("\n" + "="*60)
    print("CIVILIZATION TYPES TEST SUITE")
    print("="*60 + "\n")
    
    test_civilization_types_assigned()
    test_living_civs_never_failed_transition()
    test_extinct_civs_mostly_failed_transition()
    test_type_distribution_in_living_civs()
    test_systems_without_civilization()
    
    print("\n" + "="*60)
    print("ALL TESTS PASSED ✓")
    print("="*60 + "\n")


if __name__ == "__main__":
    run_all_tests()
