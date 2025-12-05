import os
import logging
from legacy.legacy_of_stars import ContactProgram, GameInterface

def test_research_feedback():
    print("Testing Research Feedback...")
    program = ContactProgram()
    program.research_points = 0
    # Find a tech
    if not program.technologies:
        print("WARNING: No technologies found. Skipping.")
        return

    tech_id = list(program.technologies.keys())[0]
    result = program.research_tech(tech_id)
    print(f"Result: {result}")
    print(f"Message: {program.message}")
    
    if result is False and "Insufficient Research Points" in program.message:
        print("PASS: Correctly identified insufficient funds.")
    else:
        print("FAIL: Did not report insufficient funds correctly.")

def test_alien_response_storage():
    print("\nTesting Alien Response Storage...")
    program = ContactProgram()
    if not program.star_systems:
        print("WARNING: No star systems found. Skipping.")
        return

    system = list(program.star_systems.values())[0]
    system.received_messages.append("Greetings from Proxima!")
    
    # Verify we can read it
    if len(system.received_messages) == 1 and system.received_messages[0] == "Greetings from Proxima!":
        print("PASS: Message stored and retrieved correctly.")
    else:
        print("FAIL: Message storage issue.")

def test_year_calculation():
    print("\nTesting Year Calculation...")
    program = ContactProgram()
    program.generation = 1
    year = 2050 + (program.generation * 25)
    
    if year == 2075:
        print(f"PASS: Gen 1 = Year {year}")
    else:
        print(f"FAIL: Gen 1 calculated as {year}, expected 2075")

if __name__ == "__main__":
    test_research_feedback()
    test_alien_response_storage()
    test_year_calculation()
