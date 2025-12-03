"""
Add detailed civilization logging at game start to legacy_of_stars_v3.py
Shows all hidden strategies, ages, and extinction status for debugging
"""

with open(r"c:\Users\mike\Documents\Antigravity Test\legacy-of-stars\legacy_of_stars_v3.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find where to insert the logging (after star_systems are generated in __init__)
insert_index = None
for i, line in enumerate(lines):
    if "self.star_systems = self.generate_star_systems(8)" in line:
        insert_index = i + 1
        break

if insert_index:
    # Create the logging code to insert
    logging_code = '''        
        # === DEBUG: Log all civilization details at game start ===
        logging.info("")
        logging.info("="*60)
        logging.info("GALAXY OVERVIEW - Hidden Civilization Details")
        logging.info("="*60)
        for name, system in self.star_systems.items():
            if system.has_civilization:
                if system.is_extinct:
                    logging.info(f"  {name} ({system.distance:.1f} LY) - EXTINCT")
                    logging.info(f"    Age: {int(system.civilization_age)} years")
                    logging.info(f"    Died: {system.extinct_years_ago} years ago")
                    logging.info(f"    Swan Song: {'YES' if system.has_swan_song else 'NO'}")
                else:
                    logging.info(f"  {name} ({system.distance:.1f} LY) - ACTIVE")
                    logging.info(f"    Age: {int(system.civilization_age)} years")
                    logging.info(f"    Stage: {system.civilization_stage.name}")
                    logging.info(f"    Strategy: {system.true_strategy}")
                    logging.info(f"    Deception: {system.deception_level:.2f}")
                    
                    # Explain what this means
                    strategy_desc = {
                        "L": "Listen Only - Will NEVER respond",
                        "LB": "Listen & Broadcast - Enthusiastic, friendly METI",
                        "LR": "Listen & Reply - Cautious, only responds when contacted",
                        "LA": "Listen & Annihilate - HOSTILE, attacks silently",
                        "LBA": "Listen, Broadcast & Annihilate - TRAP! Friendly bait then attack"
                    }
                    logging.info(f"    >>> {strategy_desc[system.true_strategy]}")
            else:
                logging.info(f"  {name} ({system.distance:.1f} LY) - No civilization")
            logging.info("")
        
        logging.info("="*60)
        logging.info("")
'''
    
    # Insert the logging code
    lines.insert(insert_index, logging_code)
    
    # Write back
    with open(r"c:\Users\mike\Documents\Antigravity Test\legacy-of-stars\legacy_of_stars_v3.py", "w", encoding="utf-8") as f:
        f.writelines(lines)
    
    print("✅ Added detailed civilization logging to game startup")
    print("\nNow when you start a game, the log will show:")
    print("  • All civilization names and distances")
    print("  • Their hidden strategies (L/LB/LR/LA/LBA)")
    print("  • Civilization age and tech stage")
    print("  • Deception levels")
    print("  • Extinction status and swan song availability")
    print("\nThis lets you see the 'answer key' for each playthrough!")
else:
    print("❌ Could not find insertion point in file")
