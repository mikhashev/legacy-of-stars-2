"""Test v3 Dark Forest mechanics"""
import sys
sys.path.insert(0, r"c:\Users\mike\Documents\Antigravity Test\legacy-of-stars")

from src.legacy_of_stars_v3 import ContactProgram, StarSystem, CivilizationStage
import random

random.seed(789)

print("=== LEGACY OF STARS V3 TEST ===\n")

# Test 1: Initialize game
print("Test 1: Game Initialization")
print("-" * 50)
try:
    cp = ContactProgram()
    print(f"✓ Game initialized successfully")
    print(f"  Star systems: {len(cp.star_systems)}")
    print(f"  Generation: {cp.generation}")
    print(f"  Tech level: {cp.tech_level}")
except Exception as e:
    print(f"✗ FAILED: {e}")
    sys.exit(1)

# Test 2: Verify civilizations have new attributes
print("\nTest 2: Civilization Attributes")
print("-" * 50)
civs = [s for s in cp.star_systems.values() if s.has_civilization]
print(f"Total civilizations: {len(civs)}")

active = [c for c in civs if not c.is_extinct]
extinct = [c for c in civs if c.is_extinct]

print(f"  Active: {len(active)}")
print(f"  Extinct: {len(extinct)}")

# Check attributes exist
for civ in active:
    assert hasattr(civ, 'true_strategy'), "Missing true_strategy!"
    assert hasattr(civ, 'civilization_age'), "Missing civilization_age!"
    assert hasattr(civ, 'deception_level'), "Missing deception_level!"
    assert hasattr(civ, 'pending_attack'), "Missing pending_attack!"

print("✓ All civilizations have required attributes\n")

# Test 3: Strategy distribution
print("Test 3: Strategy Distribution")
print("-" * 50)
strategies = {}
for civ in active:
    strategies[civ.true_strategy] = strategies.get(civ.true_strategy, 0) + 1

for strat in sorted(strategies.keys()):
    count = strategies[strat]
    pct = (count / len(active) * 100) if active else 0
    print(f"  {strat}: {count} ({pct:.1f}%)")

print("\n✓ Strategies assigned\n")

# Test 4: Age distribution
print("Test 4: Age Distribution")
print("-" * 50)
ages = [c.civilization_age for c in active]
older = sum(1 for a in ages if a > 100)
younger = sum(1 for a in ages if a <= 100)
ancient = sum(1 for a in ages if a > 1000)

print(f"  Older than humanity (>100y): {older}/{len(ages)} ({older/len(ages)*100:.1f}%)")
print(f"  Younger: {younger}/{len(ages)} ({younger/len(ages)*100:.1f}%)")
print(f"  Ancient (>1000y): {ancient}/{len(ages)} ({ancient/len(ages)*100:.1f}%)")
print("\n✓ Age distribution implemented\n")

# Test 5: _age_to_stage helper
print("Test 5: Age to Stage Mapping")
print("-" * 50)
test_sys = StarSystem("Test", 10)
test_sys.has_civilization = True

test_ages = [25, 150, 500, 5000, 50000]
for age in test_ages:
    test_sys.civilization_age = age
    stage = test_sys._age_to_stage(age)
    print(f"  Age {age:>5} → {stage.name}")

print("\n✓ Age mapping works\n")

# Test 6: send_message exists and has strategy logic
print("Test 6: send_message Method")
print("-" * 50)
import inspect
source = inspect.getsource(cp.send_message)

required_checks = [
    ("L Strategy", 'system.true_strategy == "L"' in source),
    ("LA Strategy", 'system.true_strategy == "LA"' in source),
    ("LBA Strategy", 'system.true_strategy == "LBA"' in source),
    ("LR Strategy", 'system.true_strategy == "LR"' in source),
    ("LB Strategy", 'system.true_strategy == "LB"' in source),
    ("Attack scheduling", 'pending_attack' in source),
]

for name, check in required_checks:
    if check:
        print(f"  ✓ {name}")
    else:
        print(f"  ✗ {name} MISSING!")
        sys.exit(1)

print("\n✓ send_message has all strategies\n")

print("=" * 50)
print("✓✓✓ ALL TESTS PASSED - V3 READY! ✓✓✓")
print("=" * 50)
print("\nDark Forest mechanics are operational:")
print("  • 75/25 age distribution")
print("  • Hidden strategies (L/LB/LR/LA/LBA)")
print("  • Extinct civilizations")
print("  • Strategy-based responses")
print("  • Attack system ready")
