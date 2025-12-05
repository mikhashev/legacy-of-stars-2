from legacy.legacy_of_stars import ContactProgram

def test_run():
    print("Initializing Contact Program...")
    program = ContactProgram()
    
    print(f"Initial Research Points: {program.research_points}")
    print("CHEAT: Adding 2000 Research Points for testing.")
    program.research_points = 2000
    
    print("\n--- Researching Prerequisites ---")
    # Basic Physics
    print("Researching Basic Physics...")
    program.research_tech("physics_1")
    print(f"Physics 1 Researched: {program.technologies['physics_1'].researched}")
    
    # Industrial Engineering
    print("Researching Industrial Engineering...")
    program.research_tech("engineering_1")
    print(f"Engineering 1 Researched: {program.technologies['engineering_1'].researched}")
    
    print("\n--- Attempting Nuclear Fission (Doctrine Trigger) ---")
    # Nuclear Fission
    tech_id = "nuclear_fission"
    needs_choice = program.research_tech(tech_id)
    
    if needs_choice:
        print("SUCCESS: Doctrine Choice Triggered!")
        tech = program.technologies[tech_id]
        print(f"Doctrine Name: {tech.doctrine_choice['name']}")
        
        print("\n--- Making Choice: Weaponization ---")
        # Choose option 0 (Weaponization)
        program.choose_doctrine(tech_id, 0)
        
        print(f"Chosen Doctrine: {tech.chosen_doctrine}")
        print(f"Self-Destruct Risk: {program.self_destruct_risk}")
        print(f"Public Support: {program.public_support}")
        
        if program.self_destruct_risk > 0:
             print("VERIFICATION PASSED: Risk increased as expected.")
        else:
             print("VERIFICATION FAILED: Risk did not increase.")
    else:
        print("FAILURE: Doctrine Choice NOT Triggered.")

if __name__ == "__main__":
    test_run()
