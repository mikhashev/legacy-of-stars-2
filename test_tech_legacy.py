"""
Test tech chronology fixes and legacy knowledge system
"""

import logging
import datetime
from legacy_of_stars_v3 import ContactProgram

# Set up logging
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
log_filename = f"test_tech_legacy_{timestamp}.log"

logging.basicConfig(
    filename=log_filename,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

print(f"\n=== TECH CHRONOLOGY & LEGACY TEST ===")
print(f"Logging to: {log_filename}\n")

# Create game instance
print("Initializing game...")
program = ContactProgram()

print("Test 1: Tech Tree Loading")
print("-" * 50)
tech_count = len(program.technologies)
print(f"✓ Loaded {tech_count} technologies")

print()
print("Test 2: Legacy Knowledge System")
print("-" * 50)

legacy_techs = [t for t in program.technologies.values() if t.is_legacy]
researched_at_start = [t for t in program.technologies.values() if t.researched]

print(f"Legacy technologies (pre-1977): {len(legacy_techs)}")
for tech in legacy_techs:
    print(f"  ✓ {tech.name} ({tech.year_context})")

print(f"\nResearched at game start: {len(researched_at_start)}")
if len(legacy_techs) == len(researched_at_start):
    print(f"✅ PASS: All legacy techs are pre-researched")
else:
    print(f"❌ FAIL: Mismatch between legacy and researched counts")

print()
print("Test 3: Chronology Fixes")
print("-" * 50)

# Check SETI@Home (1999, should be Gen 1)
seti_home = program.technologies.get("seti_at_home")
if seti_home:
    print(f"SETI@Home (1999):")
    print(f"  min_generation: {seti_home.min_generation}")
    if seti_home.min_generation == 1:
        print(f"  ✅ PASS: Correctly set to Gen 1")
    else:
        print(f"  ❌ FAIL: Should be Gen 1, is Gen {seti_home.min_generation}")

# Check Breakthrough Listen (2015, should be Gen 2)
breakthrough = program.technologies.get("breakthrough_listen")
if breakthrough:
    print(f"\nBreakthrough Listen (2015):")
    print(f"  min_generation: {breakthrough.min_generation}")
    if breakthrough.min_generation == 2:
        print(f"  ✅ PASS: Correctly set to Gen 2")
else:
        print(f"  ❌ FAIL: Should be Gen 2, is Gen {breakthrough.min_generation}")

print()
print("Test 4: Tech Context Building")
print("-" * 50)

tech_context = program._build_tech_context()
print("Generated tech context:")
print(tech_context)

if "Baseline (1977)" in tech_context:
    print(f"\n✅ PASS: Context includes baseline tech")
if "Tier 0" in tech_context:
    print(f"✅ PASS: Context includes tier information")

print()
print("=" * 50)
print(" ALL TESTS COMPLETE")
print(f"Check {log_filename} for detailed logs")
print("=" * 50)
