"""
Integrate Attack Early Warning System into legacy_of_stars_v3.py
Part 2: Modify send_message() to create warnings
"""

with open("legacy_of_stars_v3.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find and modify LA Strategy section
modified = False
for i, line in enumerate(lines):
    # Find LA Strategy section
    if 'elif system.true_strategy == "LA":' in line:
        # Replace next 4 lines with attack warning creation
        # Old: system.pending_attack = self.generation + round_trip_time
        # New: Create AttackWarning
        if i+1 < len(lines) and "system.pending_attack" in lines[i+1]:
            lines[i+1] = "        # Create attack warning instead of instant attack\n"
            lines.insert(i+2, "        warning = AttackWarning(system, self.generation + round_trip_time, self.generation)\n")
            lines.insert(i+3, "        self.pending_attack_warnings.append(warning)\n")
            lines.insert(i+4, "        \n")
            lines.insert(i+5, f"        self.message = f\"\"\"⚠️⚠️⚠️ HOSTILE FLEET DETECTED ⚠️⚠️⚠️\n")
            lines.insert(i+6, "\n")
            lines.insert(i+7, "Aggressive response from {{system_name}}!\n")
            lines.insert(i+8, "Our message triggered a hostile reaction.\n")
            lines.insert(i+9, "\n")
            lines.insert(i+10, "Fleet ETA: Generation {{self.generation + round_trip_time}} (Year {{self.start_year + (round_trip_time) * 25}})\n")
            lines.insert(i+11, "Time to Prepare: {{round_trip_time}} generations\n")
            lines.insert(i+12, "\n")
            lines.insert(i+13, "DEFENSIVE OPTIONS AVAILABLE - Check Emergency Defense menu\n")
            lines.insert(i+14, "\"\"\"\n")
            
            # Update logging
            lines[i+15] = f"        logging.critical(f\"HOSTILE FLEET DETECTED: {{system_name}}\")\n"
            lines[i+16] = f"        logging.warning(f\"Attack ETA: Gen {{self.generation + round_trip_time}} ({{round_trip_time}} gens to prepare)\")\n"
            
            modified = True
            print("✓ Modified LA Strategy to create attack warning")
            break

if not modified:
    print("⚠️ Could not find LA Strategy section to modify")

# Find and modify LBA Strategy attack scheduling
for i, line in enumerate(lines):
    if 'elif system.true_strategy == "LBA":' in line:
        # Find the else block that sets pending_attack
        for j in range(i, min(i+20, len(lines))):
            if "else:" in lines[j] and "system.pending_attack" in lines[j+1]:
                # Replace with warning creation
                lines[j+1] = "            # Create attack warning\n"
                lines.insert(j+2, "            warning = AttackWarning(system, self.generation + round_trip_time, self.generation)\n")
                lines.insert(j+3, "            self.pending_attack_warnings.append(warning)\n")
                lines.insert(j+4, "            \n")
                lines.insert(j+5, "            self.message = f\"Message sent to {system_name}. No response detected.\"\n")
                lines.insert(j+6, "            logging.critical(f\"HOSTILE FLEET DETECTED (LBA low deception): {system_name}\")\n")
                print("✓ Modified LBA Strategy (low deception) to create attack warning")
                break
        
        # Also modify high deception LBA to create warning after responses
        for j in range(i, min(i+15, len(lines))):
            if "system.pending_attack = self.generation + round_trip_time + 2" in lines[j]:
                lines[j] = "            # Schedule attack warning for +2 gens after response\n"
                lines.insert(j+1, "            warning = AttackWarning(system, self.generation + round_trip_time + 2, self.generation)\n")
                lines.insert(j+2, "            self.pending_attack_warnings.append(warning)\n")
                print("✓ Modified LBA Strategy (high deception) to create delayed attack warning")
                break
        break

# Write back
with open("legacy_of_stars_v3.py", "w", encoding="utf-8") as f:
    f.writelines(lines)

print("\n✅ Part 2 complete: send_message() modified to create attack warnings")
