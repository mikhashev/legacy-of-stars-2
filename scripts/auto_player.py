import random
import logging
from src.legacy_of_stars_v3 import ContactProgram

# Configure logging to a separate file for the auto-player
import time

# Configure logging to a separate file for the auto-player
log_filename = f"auto_play_{int(time.time())}.log"
logging.basicConfig(filename=log_filename, level=logging.INFO, format='%(message)s')

def auto_play():
    print("Initializing Auto-Player...")
    program = ContactProgram()
    
    # Strategy: Balanced
    # - Prioritize Research until Tech Level 3
    # - Then prioritize Contact
    # - Always keep Public Support > 40
    
    while not program.game_over:
        print(f"\n--- Generation {program.generation} ---")
        logging.info(f"\n--- Generation {program.generation} ---")
        
        # 1. Check available actions
        program.calculate_ap()
        print(f"AP: {program.action_points} | Support: {int(program.public_support)}% | Tech Lvl: {program.tech_level}")
        
        # 2. Spend Action Points
        while program.action_points > 0:
            action_taken = False
            
            # Priority 1: Public Outreach if support is low
            if program.public_support < 40:
                program.public_outreach()
                print("Action: Public Outreach (Low Support)")
                logging.info("Action: Public Outreach (Low Support)")
                action_taken = True
                continue
                
            # Priority 2: Send Messages to detected civs
            for name, system in program.star_systems.items():
                if system.knowledge > 40 and system.has_civilization:
                    # Don't spam if we already sent one recently (last 5 gens)
                    recent_msg = False
                    for msg, gen in system.messages_sent:
                        if program.generation - gen < 5:
                            recent_msg = True
                            break
                    
                    if not recent_msg:
                        msg_content = f"Greetings from Earth. We come in peace. We are at Tech Level {program.tech_level}."
                        program.send_message(name, msg_content)
                        print(f"Action: Sent Message to {name}")
                        logging.info(f"Action: Sent Message to {name}")
                        action_taken = True
                        break
            
            if action_taken: continue
            
            # Priority 3: Focus Research on promising systems
            # Find system with highest knowledge that isn't 100%
            best_system = None
            highest_knowledge = -1
            
            for name, system in program.star_systems.items():
                if system.knowledge < 100:
                    if system.knowledge > highest_knowledge:
                        highest_knowledge = system.knowledge
                        best_system = name
            
            if best_system:
                program.focus_research(best_system)
                print(f"Action: Focused Research on {best_system}")
                logging.info(f"Action: Focused Research on {best_system}")
                action_taken = True
                continue
                
            # Fallback: Outreach
            program.public_outreach()
            print("Action: Public Outreach (Spare AP)")
            logging.info("Action: Public Outreach (Spare AP)")
            program.action_points -= 1 # Force decrement if something goes wrong
        
        # 3. Research Tech (Free)
        # Find cheapest available tech
        available_techs = []
        for tech_id, tech in program.technologies.items():
            if not tech.researched:
                prereqs_met = True
                for prereq in tech.prerequisites:
                    if not program.technologies[prereq].researched:
                        prereqs_met = False
                        break
                if prereqs_met:
                    available_techs.append(tech)
        
        if available_techs:
            # Sort by cost
            available_techs.sort(key=lambda x: x.cost)
            target_tech = available_techs[0]
            
            if program.research_points >= target_tech.cost:
                needs_doctrine = program.research_tech(target_tech.id)
                print(f"Research: Researched {target_tech.name}")
                logging.info(f"Research: Researched {target_tech.name}")
                
                if needs_doctrine:
                    # Randomly choose a doctrine, but prefer "Safe" ones (usually index 1)
                    # Actually let's just pick random for variety
                    choice_idx = random.randint(0, len(target_tech.doctrine_choice["options"]) - 1)
                    program.choose_doctrine(target_tech.id, choice_idx)
                    choice_name = target_tech.doctrine_choice["options"][choice_idx]["name"]
                    print(f"Doctrine: Chose {choice_name}")
                    logging.info(f"Doctrine: Chose {choice_name}")
        
        # 4. Advance Generation
        program.advance_generation()
        
        # Check for responses
        for system in program.star_systems.values():
            if system.received_messages:
                for msg in system.received_messages:
                    print(f"RESPONSE from {system.name}: {msg[:100]}...")
                    logging.info(f"RESPONSE from {system.name}: {msg}")
                system.received_messages = [] # Clear so we don't print again
                
    print(f"\nGAME OVER. Reason: {program.message}")
    logging.info(f"GAME OVER. Reason: {program.message}")

if __name__ == "__main__":
    auto_play()
