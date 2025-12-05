"""
Apply WOW Signal integration to legacy_of_stars_v3.py
Small targeted changes instead of large replacements
"""

# Read the file
with open("legacy_of_stars_v3.py", "r", encoding="utf-8") as f:
    content = f.read()

# Change 1: Add import
if "from wow_signal_event import WOWSignalEvent" not in content:
    content = content.replace(
        "from ai_manager import AIManager",
        "from ai_manager import AIManager\nfrom wow_signal_event import WOWSignalEvent"
    )
    print("✓ Added WOWSignalEvent import")

# Change 2: Update start year to 1977
content = content.replace(
    "self.start_year = datetime.datetime.now().year",
    "self.start_year = 1977  # WOW! Signal era"
)
print("✓ Changed start year to 1977")

# Change 3: Add WOW Signal initialization after AI Manager
content = content.replace(
    "# AI Manager\n        self.ai = AIManager()\n        ",
    "# AI Manager\n        self.ai = AIManager()\n        \n        # WOW! Signal Event System\n        self.wow_signal = WOWSignalEvent(self)\n        "
)
print("✓ Added WOW Signal event system initialization")

# Write back
with open("legacy_of_stars_v3.py", "w", encoding="utf-8") as f:
    f.write(content)

print("\n✅ WOW Signal integration applied!")
print("Next steps:")
print("1. Add opening scenario call in GameInterface")
print("2. Add Gen 144 check in advance_generation()")
