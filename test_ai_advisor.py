"""
Test script for AI Strategic Advisor
Verifies advisor unlocking, context building, and strategic advice
"""

import logging
import datetime
from legacy_of_stars_v3 import ContactProgram, StarSystem, CivilizationStage

# Set up logging
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
log_filename = f"test_ai_advisor_{timestamp}.log"

logging.basicConfig(
    filename=log_filename,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

print(f"\n=== AI STRATEGIC ADVISOR TEST ===")
print(f"Logging to: {log_filename}\n")

# Create game instance
program = ContactProgram()

print("Test 1: Advisor Locked by Default")
print("-" * 50)

print(f"AI Advisor unlocked: {program.ai_advisor_unlocked}")
if not program.ai_advisor_unlocked:
    print(f"✅ PASS: AI Advisor locked initially")
else:
    print(f"❌ FAIL: AI Advisor should be locked initially")

# Try to consult (should fail)
program.consult_advisor()
if "not yet unlocked" in program.message.lower():
    print(f"✅ PASS: Cannot consult locked advisor")
    print(f"   Message: {program.message}")
else:
    print(f"❌ FAIL: Should not be able to consult locked advisor")

print()
print("Test 2: Unlock AI Advisor Tech")
print("-" * 50)

# Find and research AI Strategic Advisor tech
advisor_tech = program.technologies.get("ai_strategic_advisor")
if advisor_tech:
    print(f"Found tech: {advisor_tech.name}")
    print(f"  Tier: {advisor_tech.tier}")
    print(f"  Min Gen: {advisor_tech.min_generation}")
    print(f"  Cost: {advisor_tech.cost} RP")
    
    # Set up conditions to research it
    program.generation = advisor_tech.min_generation
    program.research_points = advisor_tech.cost + 100
    
    # Research prerequisites
    for prereq_id in advisor_tech.prerequisites:
        prereq = program.technologies.get(prereq_id)
        if prereq:
            prereq.researched = True
            print(f"  Prerequisite researched: {prereq.name}")
    
    # Research the tech
    program.research_tech(advisor_tech.id)
    
    if advisor_tech.researched and program.ai_advisor_unlocked:
        print(f"✅ PASS: AI Advisor tech researched and unlocked")
        print(f"   Flag set: {program.ai_advisor_unlocked}")
    else:
        print(f"❌ FAIL: Tech research or unlock failed")
        print(f"   Researched: {advisor_tech.researched}")
        print(f"   Unlocked: {program.ai_advisor_unlocked}")
else:
    print(f"❌ FAIL: AI Strategic Advisor tech not found in tech tree")

print()
print("Test 3: Consult AI Advisor")
print("-" * 50)

if program.ai_advisor_unlocked:
    print("Consulting AI Strategic Advisor...")
    print("(This will call the AI - may take a few seconds)")
    
    # Set up some game state for interesting analysis
    # Add a hostile system
    hostile_sys = None
    for name, system in program.star_systems.items():
        if system.has_civilization and not system.is_extinct:
            system.true_strategy = "LA"
            hostile_sys = system
            # Send a message to trigger warning
            program.calculate_ap()
            program.send_message(name, "Test message")
            print(f"  Created threat from: {name}")
            break
    
    # Consult advisor
    program.advisor_consulted_this_gen = False  # Reset flag
    program.consult_advisor()
    
    if program.advisor_consulted_this_gen:
        print(f"✅ PASS: Advisor consulted successfully")
        print(f"\nAdvisor Response Preview:")
        print(program.message[:500] + "..." if len(program.message) > 500 else program.message)
    else:
        print(f"❌ FAIL: Advisor consultation failed")
else:
    print(f"⚠️ SKIP: AI Advisor not unlocked, cannot test consultation")

print()
print("Test 4: Once Per Generation Limit")
print("-" * 50)

if program.ai_advisor_unlocked and program.advisor_consulted_this_gen:
    print(f"Already consulted this gen: {program.advisor_consulted_this_gen}")
    
    # Try to consult again
    old_message = program.message
    program.consult_advisor()
    
    if "already consulted" in program.message.lower():
        print(f"✅ PASS: Cannot consult twice in same generation")
        print(f"   Message: {program.message}")
    else:
        print(f"❌ FAIL: Should prevent consulting twice")
    
    # Advance generation and try again
    program.advance_generation()
    print(f"\nAdvanced to Gen {program.generation}")
    print(f"Flag reset: {program.advisor_consulted_this_gen}")
    
    if not program.advisor_consulted_this_gen:
        print(f"✅ PASS: Flag reset on new generation")
        
        # Should be able to consult again
        program.consult_advisor()
        if program.advisor_consulted_this_gen:
            print(f"✅ PASS: Can consult again in new generation")
        else:
            print(f"❌ FAIL: Should be able to consult in new generation")
    else:
        print(f"❌ FAIL: Flag not reset on new generation")

print()
print("Test 5: Context Building")
print("-" * 50)

# Create diverse game state
program.public_support = 45
program.funding = 60
program.knowledge_base = 30
program.generation = 5

# Set up various system states
contacted = 0
silent = 0
extinct = 0

for name, system in list(program.star_systems.items())[:6]:
    if not system.has_civilization:
        continue
    
    if contacted < 2:
        # Make it friendly
        system.true_strategy = "LB"
        system.received_messages.append("Friendly response")
        contacted += 1
    elif silent < 2:
        # Make it silent (sent message, no response)
        system.messages_sent.append(("Test", program.generation - 1))
        silent += 1
    elif extinct < 1:
        # Make it extinct
        system.is_extinct = True
        extinct += 1

print(f"Game state set up:")
print(f"  Generation: {program.generation}")
print(f"  Support: {program.public_support}%")
print(f"  Funding: {program.funding}%")
print(f"  Contacted: {contacted}")
print(f"  Silent: {silent}")
print(f"  Extinct: {extinct}")
print(f"  Threats: {len(program.pending_attack_warnings)}")

# Build context
context = program.ai_advisor._build_context(program)

if "Generation 5" in context:
    print(f"\n✅ PASS: Context includes generation")
if f"Support: {int(program.public_support)}%" in context:
    print(f"✅ PASS: Context includes support level")
if "Contacted (friendly)" in context and f"{contacted}" in context:
    print(f"✅ PASS: Context includes contacted civilizations")
if len(program.pending_attack_warnings) > 0 and "ACTIVE THREATS" in context:
    print(f"✅ PASS: Context includes active threats")

print(f"\nFull context preview:")
print(context[:600] + "..." if len(context) > 600 else context)

print()
print("=" * 50)
print("AI STRATEGIC ADVISOR TEST COMPLETE")
print(f"Check {log_filename} for detailed logs")
print("=" * 50)
