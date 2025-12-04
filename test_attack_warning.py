"""
Test script for Attack Early Warning System
This script verifies all defensive mechanics work correctly
"""

import logging
import datetime
from legacy_of_stars_v3 import ContactProgram, StarSystem, CivilizationStage
from attack_warning import AttackWarning

# Set up logging
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
log_filename = f"test_attack_warning_{timestamp}.log"

logging.basicConfig(
    filename=log_filename,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

print(f"\n=== ATTACK EARLY WARNING SYSTEM TEST ===")
print(f"Logging to: {log_filename}\n")

# Create game instance
program = ContactProgram()

print("Test 1: Create attack warning")
print("-" * 50)

# Find a system with civilization
hostile_system = None
for name, system in program.star_systems.items():
    if system.has_civilization and not system.is_extinct:
        # Force it to be LA strategy
        system.true_strategy = "LA"
        system.civilization_stage = CivilizationStage.DIGITAL
        hostile_system = system
        print(f"✓ Set {name} to LA (hostile) strategy")
        print(f"  Distance: {system.distance:.1f} LY")
        print(f"  Tech Stage: {system.civilization_stage.name}")
        break

if not hostile_system:
    # Create one if needed
    hostile_system = StarSystem("Test System", 10.0)
    hostile_system.has_civilization = True
    hostile_system.civilization_stage = CivilizationStage.DIGITAL
    hostile_system.true_strategy = "LA"
    program.star_systems["Test System"] = hostile_system
    print(f"✓ Created Test System (LA strategy)")

print()
print("Test 2: Trigger attack warning via message")
print("-" * 50)

initial_warnings = len(program.pending_attack_warnings)
print(f"Initial warnings: {initial_warnings}")

# Send message to hostile civilization
program.send_message(hostile_system.name, "Hello! Peace and greetings from Earth!")
print(f"✓ Sent message to {hostile_system.name}")

warnings_after = len(program.pending_attack_warnings)
print(f"Warnings after message: {warnings_after}")

if warnings_after > initial_warnings:
    warning = program.pending_attack_warnings[-1]
    print(f"✅ PASS: Attack warning created!")
    print(f"   Source: {warning.source.name}")
    print(f"   Arrival Gen: {warning.arrival_gen}")
    print(f"   Current Gen: {program.generation}")
    print(f"   ETA: {warning.get_etas_remaining(program.generation)} generations")
else:
    print(f"❌ FAIL: No warning created!")

print()
print("Test 3: Apply defensive actions")
print("-" * 50)

if warnings_after > 0:
    warning = program.pending_attack_warnings[0]
    warning_idx = 0
    
    # Test Emergency Defense
    print("Testing Emergency Defense Protocol...")
    initial_defense = warning.defense_multiplier
    program.defend_emergency(warning_idx)
    
    if "Emergency Defense Protocol" in warning.defensive_actions_taken:
        print(f"✅ PASS: Emergency Defense applied")
        print(f"   Defense multiplier: {initial_defense} -> {warning.defense_multiplier}")
        print(f"   Damage reduction: {warning.get_defense_percentage()}%")
    else:
        print(f"❌ FAIL: Emergency Defense not applied")
    
    # Restore AP for next test
    program.calculate_ap()
    
    # Test Evacuation
    print("\nTesting Evacuation Protocol...")
    initial_defense = warning.defense_multiplier
    program.defend_evacuate(warning_idx)
    
    if "Evacuation" in warning.defensive_actions_taken:
        print(f"✅ PASS: Evacuation applied")
        print(f"   Defense multiplier: {initial_defense} -> {warning.defense_multiplier}")
        print(f"   Total damage reduction: {warning.get_defense_percentage()}%")
    else:
        print(f"❌ FAIL: Evacuation not applied")
    
    print(f"\nFinal defensive actions: {warning.defensive_actions_taken}")

print()
print("Test 4: Process incoming attack")
print("-" * 50)

if warnings_after > 0:
    warning = program.pending_attack_warnings[0]
    
    # Advance to attack arrival
    print(f"Current generation: {program.generation}")
    print(f"Attack arrives at: {warning.arrival_gen}")
    print(f"Fast-forwarding to attack arrival...")
    
    initial_support = program.public_support
    initial_funding = program.funding
    
    # Advance to arrival generation
    target_gen = warning.arrival_gen
    while program.generation < target_gen and not program.game_over:
        program.advance_generation()
        if program.generation < target_gen:
            print(f"  Gen {program.generation}: Countdown - {warning.get_etas_remaining(program.generation)} gens remaining")
    
    # Check if attack was processed
    if program.game_over:
        print(f"\n⚠️ GAME OVER triggered")
        print(f"Message: {program.message}")
    else:
        support_loss = initial_support - program.public_support
        funding_loss = initial_funding - program.funding
        
        print(f"\n✅ Attack processed!")
        print(f"   Support loss: {support_loss:.1f}%")
        print(f"   Funding loss: {funding_loss:.1f}%")
        print(f"   Defense reduced damage by: {warning.get_defense_percentage()}%")
    
    # Check warning was removed
    if warning not in program.pending_attack_warnings:
        print(f"✅ PASS: Warning removed after attack")
    else:
        print(f"❌ FAIL: Warning still in list after attack")

print()
print("Test 5: Diplomatic success (low-deception LBA)")
print("-" * 50)

# Create a new low-deception LBA civilization
lba_system = StarSystem("Diplomatic Test", 15.0)
lba_system.has_civilization = True
lba_system.civilization_stage = CivilizationStage.EARLY_RADIO
lba_system.true_strategy = "LBA"
lba_system.deception_level = 0.3  # Low deception
program.star_systems["Diplomatic Test"] = lba_system

# Reset game state
program.generation = 1
program.calculate_ap()

# Trigger LBA attack
program.send_message("Diplomatic Test", "Peace!")
if len(program.pending_attack_warnings) > 0:
    lba_warning = program.pending_attack_warnings[-1]
    print(f"✓ LBA warning created from {lba_warning.source.name}")
    print(f"  Deception level: {lba_warning.source.deception_level}")
    
    # Try diplomatic contact multiple times (30% success chance)
    success = False
    attempts = 0
    max_attempts = 10
    
    while not success and attempts < max_attempts and len(program.pending_attack_warnings) > 0:
        program.calculate_ap()  # Restore AP
        initial_warning_count = len(program.pending_attack_warnings)
        program.defend_diplomacy(len(program.pending_attack_warnings) - 1)
        
        attempts += 1
        if len(program.pending_attack_warnings) < initial_warning_count:
            success = True
            print(f"✅ PASS: Diplomatic success after {attempts} attempts!")
            print(f"   Attack aborted!")
            break
    
    if not success:
        print(f"⚠️ Diplomacy didn't succeed in {max_attempts} attempts")
        print(f"   (This can happen due to randomness)")

print()
print("=" * 50)
print("ATTACK EARLY WARNING SYSTEM TEST COMPLETE")
print(f"Check {log_filename} for detailed logs")
print("=" * 50)
