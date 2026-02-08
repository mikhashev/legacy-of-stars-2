"""Quick test to show the new debug logging"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.legacy_of_stars_v3 import ContactProgram
import random

random.seed(999)  # Consistent results

print("Initializing game to show debug logging...\n")
cp = ContactProgram()

print("\n✅ Game initialized!")
print(f"Check the log file for GALAXY OVERVIEW section")
print(f"\nQuick preview of what's in this galaxy:")
for name, sys in cp.star_systems.items():
    if sys.has_civilization:
        if sys.is_extinct:
            print(f"  • {name}: EXTINCT ({sys.extinct_years_ago}y ago)")
        else:
            print(f"  • {name}: {sys.true_strategy} strategy, age {int(sys.civilization_age)}y")
