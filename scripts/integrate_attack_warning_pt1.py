"""
Integrate Attack Early Warning System into legacy_of_stars_v3.py
Part 1: Add import and initialization
"""

with open("legacy_of_stars_v3.py", "r", encoding="utf-8") as f:
    content = f.read()

# Change 1: Add attack_warning import
if "from attack_warning import AttackWarning" not in content:
    content = content.replace(
        "from wow_signal_event import WOWSignalEvent",
        "from wow_signal_event import WOWSignalEvent\nfrom attack_warning import AttackWarning"
    )
    print("✓ Added AttackWarning import")

# Change 2: Add pending_attack_warnings list initialization
content = content.replace(
    "# WOW! Signal Event System\n        self.wow_signal = WOWSignalEvent(self)\n        ",
    "# WOW! Signal Event System\n        self.wow_signal = WOWSignalEvent(self)\n        \n        # Attack Early Warning System\n        self.pending_attack_warnings = []\n        "
)
print("✓ Added pending_attack_warnings list initialization")

# Write back
with open("legacy_of_stars_v3.py", "w", encoding="utf-8") as f:
    f.write(content)

print("\n✅ Part 1 complete: Import and initialization added")
