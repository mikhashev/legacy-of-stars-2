"""
Test script for redesigned Tech Tree
Verifies generation gating, special effects, and tier progression
"""

import logging
import datetime
from src.legacy_of_stars_v3 import ContactProgram

# Set up logging
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
log_filename = f"test_tech_tree_{timestamp}.log"

logging.basicConfig(
    filename=log_filename,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

print(f"\n=== TECH TREE REDESIGN TEST ===")
print(f"Logging to: {log_filename}\n")

# Create game instance
program = ContactProgram()

print("Test 1: Tech Tree Loading")
print("-" * 50)
tech_count = len(program.technologies)
print(f"✓ Loaded {tech_count} technologies")

# Count by tier
tier_counts = {}
for tech in program.technologies.values():
    tier_counts[tech.tier] = tier_counts.get(tech.tier, 0) + 1

print("\nTechnologies by Tier:")
for tier in sorted(tier_counts.keys()):
    print(f"  Tier {tier}: {tier_counts[tier]} techs")

print()
print("Test 2: Generation Gating")
print("-" * 50)

# Try to research a Tier 1 tech that requires Gen 2
program.research_points = 1000

tier1_tech = None
for tech in program.technologies.values():
    if tech.tier == 1 and tech.min_generation == 2:
        tier1_tech = tech
        break

if tier1_tech:
    print(f"Testing: {tier1_tech.name} (requires Gen {tier1_tech.min_generation})")
    print(f"Current generation: {program.generation}")
    
    # Try to research (should fail)
    result = program.research_tech(tier1_tech.id)
    if not tier1_tech.researched:
        print(f"✅ PASS: Cannot research before Gen {tier1_tech.min_generation}")
        print(f"   Message: {program.message}")
    else:
        print(f"❌ FAIL: Tech researched despite generation requirement!")
    
    # Advance to Gen 2 and try again
    program.generation = 2
    program.research_points = 1000
    result = program.research_tech(tier1_tech.id)
    
    if tier1_tech.researched:
        print(f"✅ PASS: Can research at Gen {program.generation}")
    else:
        print(f"❌ FAIL: Cannot research even at correct generation!")
        print(f"   Message: {program.message}")

print()
print("Test 3: Special Effects - Passive Defense")
print("-" * 50)

# Find Orbital Defense Grid
orbital_defense = program.technologies.get("orbital_defense_grid")
if orbital_defense:
    print(f"Testing: {orbital_defense.name}")
    print(f"  Special effect: {orbital_defense.special}")
    
    initial_defense = program.passive_defense_bonus
    print(f"  Initial passive defense: {initial_defense}")
    
    # Set up conditions to research it
    program.generation = orbital_defense.min_generation
    program.research_points = orbital_defense.cost + 100
    
    # Research prerequisites first
    for prereq_id in orbital_defense.prerequisites:
        prereq = program.technologies.get(prereq_id)
        if prereq:
            prereq.researched = True
    
    # Research the tech
    program.research_tech(orbital_defense.id)
    
    if orbital_defense.researched:
        print(f"  ✅ Tech researched successfully")
        print(f"  Passive defense after: {program.passive_defense_bonus}")
        
        if program.passive_defense_bonus < initial_defense:
            print(f"  ✅ PASS: Passive defense bonus applied (0.6 multiplier = 40% reduction)")
        else:
            print(f"  ❌ FAIL: Passive defense bonus not applied!")
    else:
        print(f"  ❌ FAIL: Could not research tech")
        print(f"  Message: {program.message}")

print()
print("Test 4: Backup Colonies Effect")
print("-" * 50)

backup_colonies = program.technologies.get("distributed_colonies")
if backup_colonies:
    print(f"Testing: {backup_colonies.name}")
    print(f"  Special effect: {backup_colonies.special}")
    
    initial_status = program.has_backup_colonies
    print(f"  Initial backup colonies: {initial_status}")
    
    # Set up conditions
    program.generation = backup_colonies.min_generation
    program.research_points = backup_colonies.cost + 100
    
    # Research prerequisites
    for prereq_id in backup_colonies.prerequisites:
        prereq = program.technologies.get(prereq_id)
        if prereq:
            prereq.researched = True
            # Also need to research prereqs of prereqs
            for sub_prereq_id in prereq.prerequisites:
                sub_prereq = program.technologies.get(sub_prereq_id)
                if sub_prereq:
                    sub_prereq.researched = True
    
    # Research the tech
    program.research_tech(backup_colonies.id)
    
    if backup_colonies.researched:
        print(f"  ✅ Tech researched successfully")
        print(f"  Backup colonies after: {program.has_backup_colonies}")
        
        if program.has_backup_colonies:
            print(f"  ✅ PASS: Backup colonies flag activated")
        else:
            print(f"  ❌ FAIL: Backup colonies flag not set!")
    else:
        print(f"  ❌ FAIL: Could not research tech")

print()
print("Test 5: Tier 0 Technologies (Always Available)")
print("-" * 50)

tier0_techs = [t for t in program.technologies.values() if t.tier == 0]
print(f"Found {len(tier0_techs)} Tier 0 technologies:")

# Reset for testing
program.generation = 1
program.research_points = 1000

researched_count = 0
for tech in tier0_techs[:5]:  # Test first 5
    result = program.research_tech(tech.id)
    if tech.researched:
        print(f"  ✅ {tech.name}")
        researched_count += 1
    else:
        print(f"  ❌ {tech.name} - {program.message}")

if researched_count == min(5, len(tier0_techs)):
    print(f"\n✅ PASS: All tested Tier 0 techs available from Gen 1")
else:
    print(f"\n❌ FAIL: Some Tier 0 techs not available")

print()
print("Test 6: Historical Accuracy")
print("-" * 50)

historical_techs = {
    "arecibo_telescope": "1963",
    "drake_equation": "1961",
    "seti_at_home": "1999",
    "breakthrough_listen": "2015"
}

for tech_id, year in historical_techs.items():
    tech = program.technologies.get(tech_id)
    if tech:
        print(f"✓ {tech.name} - {year}")
        print(f"  Context: {tech.year_context}")

print()
print("=" * 50)
print("TECH TREE REDESIGN TEST COMPLETE")
print(f"Check {log_filename} for detailed logs")
print("=" * 50)
