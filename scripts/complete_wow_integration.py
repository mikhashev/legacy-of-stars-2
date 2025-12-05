"""
Complete WOW Signal integration - Part 2
Add opening scenario call and Gen 144 event check
"""

with open("legacy_of_stars_v3.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find and modify the advance_generation method to add Gen 144 check
# Look for the line after "# === PHASE 1B: Process Attacks ===" 
modified = False
for i, line in enumerate(lines):
    # Add Gen 144 check before processing attacks
    if "# === PHASE 1B: Process Attacks ===" in line and not modified:
        # Insert WOW Signal Gen 144 check before attacks
        indent = "        "
        insert_lines = [
            f"\n{indent}# === WOW! SIGNAL: Check for Gen 144 Event ===\n",
            f"{indent}if self.wow_signal.check_gen144_event():\n",
            f"{indent}    self.wow_signal.trigger_gen144_event()\n",
            f"{indent}    return\n",
            "\n"
        ]
        for j, new_line in enumerate(insert_lines):
            lines.insert(i + j, new_line)
        modified = True
        print("✓ Added Gen 144 event check in advance_generation()")
        break

# Find game.play() call and add WOW opening scenario before it
for i, line in enumerate(lines):
    if line.strip() == "game.play()":
        # Insert opening scenario call before play()
        lines[i] = "    # Present WOW! Signal opening scenario\n    game.program.wow_signal.present_opening_scenario()\n    \n    game.play()\n"
        print("✓ Added WOW! Signal opening scenario call")
        break

# Write back
with open("legacy_of_stars_v3.py", "w", encoding="utf-8") as f:
    f.writelines(lines)

print("\n✅ WOW Signal integration complete!")
print("\nAll integration points added:")
print("  1. Import and initialization")
print("  2. Opening scenario (Gen 1, 1977)")
print("  3. Gen 144 event check")
