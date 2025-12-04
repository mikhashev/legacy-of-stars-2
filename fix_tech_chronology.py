"""
Apply tech tree chronology fixes and add legacy knowledge system
This script safely modifies the tech_tree.json and legacy_of_stars_v3.py
"""

import json
import sys

print("=== Tech Tree Chronology Fix Script ===\n")

# Step 1: Check if we're looking at the redesigned tech tree
print("Step 1: Checking tech tree version...")
with open('data/tech_tree.json', 'r', encoding='utf-8') as f:
    tech_data = json.load(f)

techs = tech_data['technologies']

# Check if this is the redesigned version (should have min_generation field)
has_min_gen = any('min_generation' in t for t in techs)

if not has_min_gen:
    print("❌ ERROR: This appears to be the OLD tech tree (pre-redesign)")
    print("   The redesigned tech tree with 27 technologies should already be in place.")
    print("   Please ensure you're using the correct tech_tree.json")
    sys.exit(1)

print(f"✓ Found redesigned tech tree with {len(techs)} technologies")

# Step 2: Apply chronology fixes
print("\nStep 2: Applying chronology fixes...")

fixes_applied = []

for tech in techs:
    # Fix SETI@Home (1999) - should be Gen 1, not Gen 2
    if tech['id'] == 'seti_at_home':
        if tech['min_generation'] == 2:
            tech['min_generation'] = 1
            tech['year_context'] = "Available Gen 1 (launched 1999)"
            fixes_applied.append(f"  ✓ SETI@Home: Gen 2 → Gen 1")
            print(fixes_applied[-1])
    
    # Fix Breakthrough Listen (2015) - should be Gen 2, not Gen 3
    elif tech['id'] == 'breakthrough_listen':
        if tech['min_generation'] == 3:
            tech['min_generation'] = 2
            tech['year_context'] = "Available Gen 2 (launched 2015)"
            fixes_applied.append(f"  ✓ Breakthrough Listen: Gen 3 → Gen 2")
            print(fixes_applied[-1])

if not fixes_applied:
    print("  ℹ All chronology already correct!")
else:
    # Save the updated tech tree
    with open('data/tech_tree.json', 'w', encoding='utf-8') as f:
        json.dump(tech_data, f, indent=4)
    print(f"\n✅ Applied {len(fixes_applied)} chronology fixes to tech_tree.json")

# Step 3: Summary
print("\n" + "="*50)
print("CHRONOLOGY FIXES COMPLETE")
print("="*50)
print("\nNext steps:")
print("1. Add is_legacy flag to Technology class")
print("2. Add legacy tech initialization to ContactProgram")  
print("3. Add _build_tech_context() method")
print("4. Update send_message() to use tech context")
print("\nRun the main game to add these code changes.")
