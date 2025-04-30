import random
import time
import os
from enum import Enum
from typing import Dict, List, Tuple

class CivilizationStage(Enum):
    PRE_RADIO = 0
    EARLY_RADIO = 1
    DIGITAL = 2
    INTERPLANETARY = 3
    INTERSTELLAR = 4
    POST_BIOLOGICAL = 5

class StarSystem:
    def __init__(self, name: str, distance: float):
        self.name = name
        self.distance = distance  # In light years
        self.has_civilization = random.random() < 0.3
        
        if self.has_civilization:
            # Most civilizations are at lower technological levels
            weights = [20, 30, 25, 15, 7, 3]
            stage_values = list(range(len(CivilizationStage)))
            self.civilization_stage = CivilizationStage(random.choices(stage_values, weights=weights)[0])
            self.civilization_attitude = random.uniform(0.2, 0.8)  # 0 = hostile, 1 = friendly
        else:
            self.civilization_stage = None
            self.civilization_attitude = 0
            
        self.knowledge = 0  # How much we know about this system
        self.messages_sent = []  # List of messages sent to this system
        self.pending_responses = []  # Messages en route back to Earth
        self.received_messages = []  # Messages we've received and analyzed
    
    def get_round_trip_time(self) -> int:
        """Get the communication round trip time in generations (rounded up)"""
        years = self.distance * 2  # There and back
        generations = (years / 25)  # Each generation is ~25 years
        return max(1, int(generations + 0.999))  # Round up to nearest generation
    
    def can_detect_civilization(self, transmission_tech: int) -> bool:
        """Check if Earth can detect civilization with current tech"""
        if not self.has_civilization:
            return False
            
        # Need at least matching tech level to detect
        if self.civilization_stage.value <= CivilizationStage.PRE_RADIO.value:
            return False
        
        # Higher tech civilizations are easier to detect
        tech_diff = transmission_tech - self.civilization_stage.value
        detection_chance = 0.1 + (0.15 * self.civilization_stage.value) + (0.1 * tech_diff)
        detection_chance = max(0.05, min(0.9, detection_chance))
        
        return random.random() < detection_chance
    
    def update_knowledge(self, research_focus: float):
        """Update knowledge based on research focus"""
        if self.knowledge < 100:
            self.knowledge += 5 * research_focus
            self.knowledge = min(100, self.knowledge)
    
    def describe_civilization(self) -> str:
        """Get description of civilization based on current knowledge"""
        if not self.has_civilization:
            return "No signs of civilization detected."
            
        if self.knowledge < 20:
            return "Possible artificial signals detected."
        elif self.knowledge < 40:
            return f"Civilization detected at {self.civilization_stage.name} stage."
        elif self.knowledge < 60:
            attitude = "cautious"
            if self.civilization_attitude < 0.4:
                attitude = "potentially hostile"
            elif self.civilization_attitude > 0.6:
                attitude = "seemingly friendly"
            return f"{self.civilization_stage.name} civilization. Attitude: {attitude}."
        elif self.knowledge < 80:
            return f"{self.civilization_stage.name} civilization with {int(self.civilization_attitude * 100)}% positive attitude toward contact."
        else:
            # Full knowledge
            stage_descriptions = {
                CivilizationStage.PRE_RADIO: "Pre-radio civilization using primitive communication.",
                CivilizationStage.EARLY_RADIO: "Early radio-capable civilization, similar to Earth's 20th century.",
                CivilizationStage.DIGITAL: "Digital-era civilization with global communication networks.",
                CivilizationStage.INTERPLANETARY: "Interplanetary civilization spanning multiple worlds in their system.",
                CivilizationStage.INTERSTELLAR: "Advanced interstellar civilization with faster-than-light communication.",
                CivilizationStage.POST_BIOLOGICAL: "Post-biological intelligence transcending physical limitations."
            }
            return stage_descriptions[self.civilization_stage]

class Director:
    """Represents a generation's director of the contact program"""
    def __init__(self, name: str):
        self.name = name
        self.skills = {
            "diplomacy": random.uniform(0.5, 1.0),
            "science": random.uniform(0.5, 1.0),
            "administration": random.uniform(0.5, 1.0),
        }
        self.traits = []
        self.generation = 0
        
        # Add random traits
        potential_traits = [
            "Cautious", "Bold", "Analytical", "Intuitive", "Diplomatic", 
            "Direct", "Patient", "Efficient", "Visionary", "Traditional"
        ]
        num_traits = random.randint(1, 3)
        self.traits = random.sample(potential_traits, num_traits)
    
    def get_skill_bonus(self, skill: str) -> float:
        """Get bonus for a particular skill based on traits"""
        bonus = 0
        if skill == "diplomacy" and "Diplomatic" in self.traits:
            bonus += 0.2
        elif skill == "science" and "Analytical" in self.traits:
            bonus += 0.2
        elif skill == "administration" and "Efficient" in self.traits:
            bonus += 0.2
        
        if "Bold" in self.traits:
            bonus += 0.1
        if "Cautious" in self.traits and (skill == "diplomacy" or skill == "administration"):
            bonus += 0.1
        
        return bonus
    
    def get_effective_skill(self, skill: str) -> float:
        """Get effective skill level with bonuses"""
        return min(1.0, self.skills[skill] + self.get_skill_bonus(skill))

class ContactProgram:
    """Manages Earth's interstellar contact program"""
    def __init__(self):
        self.generation = 1
        self.tech_level = 1
        self.funding = 50  # 0-100 scale
        self.research_points = 0
        self.diplomacy_points = 0
        self.message_quality = 1.0
        self.public_support = 50  # 0-100 scale
        self.knowledge_base = 10  # General knowledge about other civilizations
        self.star_systems = self.generate_star_systems(8)
        self.directors = []
        self.current_director = self.generate_director()
        self.directors.append(self.current_director)
        self.game_over = False
        self.victory = False
        self.message = ""
        
    def generate_star_systems(self, count: int) -> Dict[str, StarSystem]:
        """Generate star systems within detection range"""
        systems = {}
        star_names = [
            "Proxima Centauri", "Tau Ceti", "Epsilon Eridani", "Ross 128",
            "Luyten's Star", "Teegarden's Star", "Wolf 359", "Lalande 21185",
            "Sirius", "Procyon", "Altair", "Vega", "Fomalhaut", "Deneb",
            "Pollux", "Castor", "Capella", "Achernar", "Hadar", "Rigel"
        ]
        
        selected_names = random.sample(star_names, count)
        
        for name in selected_names:
            # Distance between 4 and 50 light years
            distance = random.uniform(4.0, 50.0)
            systems[name] = StarSystem(name, distance)
            
        return systems
    
    def generate_director(self) -> Director:
        """Generate a new program director"""
        first_names = ["Emma", "Liam", "Olivia", "Noah", "Ava", "William", "Sophia", "James",
                       "Isabella", "Logan", "Charlotte", "Benjamin", "Amelia", "Mason", "Harper", "Elijah"]
        last_names = ["Smith", "Johnson", "Williams", "Jones", "Brown", "Davis", "Miller", "Wilson",
                      "Taylor", "Clark", "Lewis", "Lee", "Walker", "Hall", "Young", "Harris"]
        
        name = f"Dr. {random.choice(first_names)} {random.choice(last_names)}"
        director = Director(name)
        director.generation = self.generation
        return director
    
    def advance_generation(self):
        """Advance to the next generation"""
        self.generation += 1
        
        # Process pending messages
        for system in self.star_systems.values():
            responses_to_remove = []
            
            for response in system.pending_responses:
                message, arrival_generation = response
                if arrival_generation <= self.generation:
                    # Message has arrived
                    system.received_messages.append(message)
                    
                    # Knowledge increase from received message
                    system.knowledge += 10 * self.tech_level
                    system.knowledge = min(100, system.knowledge)
                    
                    # Overall knowledge base increase
                    self.knowledge_base += 5
                    self.knowledge_base = min(100, self.knowledge_base)
                    
                    # Public support boost from successful contact
                    self.public_support += 5
                    self.public_support = min(100, self.public_support)
                    
                    responses_to_remove.append(response)
            
            # Remove processed responses
            for response in responses_to_remove:
                system.pending_responses.remove(response)
            
            # Update system knowledge
            research_focus = self.research_points / 100
            system.update_knowledge(research_focus)
        
        # Tech advances
        self.research_points += 10 + (self.funding / 10)
        if self.research_points >= 100:
            self.tech_level += 1
            self.research_points -= 100
            self.message = f"Technology breakthrough! Advanced to level {self.tech_level}."
            
            # Tech breakthroughs increase public support
            self.public_support += 10
            self.public_support = min(100, self.public_support)
        
        # Funding changes based on public support
        support_modifier = (self.public_support - 50) / 10
        self.funding += support_modifier
        self.funding = max(20, min(100, self.funding))
        
        # Message quality improves with tech and knowledge
        self.message_quality = 1.0 + (self.tech_level * 0.1) + (self.knowledge_base / 100)
        
        # New director each generation
        self.current_director = self.generate_director()
        self.directors.append(self.current_director)
        
        # Victory check - established contact with at least 3 civilizations
        contacted_count = 0
        for system in self.star_systems.values():
            if system.has_civilization and len(system.received_messages) > 0:
                contacted_count += 1
        
        if contacted_count >= 3:
            self.victory = True
            self.game_over = True
            self.message = "VICTORY! Earth has established contact with multiple civilizations."
        
        # Game over check - funding cut or lost public support
        if self.funding < 20 or self.public_support < 10:
            self.game_over = True
            self.message = "GAME OVER: The contact program has been defunded due to lack of results or public support."

    def send_message(self, system_name: str, message_content: str):
        """Send a message to a star system"""
        if system_name not in self.star_systems:
            self.message = f"System {system_name} not found in database."
            return
            
        system = self.star_systems[system_name]
        
        # Record that we sent a message
        system.messages_sent.append((message_content, self.generation))
        
        # Calculate if we receive a response
        if system.has_civilization and system.civilization_stage.value >= CivilizationStage.EARLY_RADIO.value:
            # Calculate how likely they are to respond
            response_chance = 0.2 + (system.civilization_attitude * 0.3) + (self.message_quality * 0.2)
            response_chance = min(0.9, response_chance)
            
            # More advanced civs more likely to detect and respond
            tech_boost = 0.1 * (system.civilization_stage.value - CivilizationStage.EARLY_RADIO.value)
            response_chance += tech_boost
            
            if random.random() < response_chance:
                # They will respond!
                round_trip_time = system.get_round_trip_time()
                arrival_generation = self.generation + round_trip_time
                
                # Better diplomatic skill = better response quality
                diplomacy_factor = self.current_director.get_effective_skill("diplomacy")
                
                # Response quality affects future attitude
                system.civilization_attitude += 0.1 * diplomacy_factor
                system.civilization_attitude = min(1.0, system.civilization_attitude)
                
                # Generate response
                response = f"Response to message sent in Generation {self.generation}"
                system.pending_responses.append((response, arrival_generation))
                
                # Calculate how long before response arrives
                years = round_trip_time * 25
                self.message = f"Message sent to {system_name}. If they respond, it will arrive in approximately {years} years (Generation {arrival_generation})."
                
                # Sending successful messages boosts the program
                self.public_support += 2
                self.public_support = min(100, self.public_support)
                
                # Diplomacy points from successful message
                self.diplomacy_points += 10 * diplomacy_factor
            else:
                # No response
                self.message = f"Message sent to {system_name}. No guarantee of reception or response."
        else:
            # No civilization or pre-radio civilization
            self.message = f"Message sent to {system_name}, but no response capability detected."

    def focus_research(self, system_name: str):
        """Focus research efforts on a particular system"""
        if system_name not in self.star_systems:
            self.message = f"System {system_name} not found in database."
            return
            
        system = self.star_systems[system_name]
        
        # Research effectiveness based on science skill
        science_factor = self.current_director.get_effective_skill("science")
        knowledge_gain = 10 * science_factor
        
        # Apply knowledge gain
        system.knowledge += knowledge_gain
        system.knowledge = min(100, system.knowledge)
        
        # Research points
        self.research_points += 5 * science_factor
        
        self.message = f"Research focused on {system_name}. Knowledge increased by {int(knowledge_gain)} points."

    def public_outreach(self):
        """Conduct public outreach to boost support"""
        admin_skill = self.current_director.get_effective_skill("administration")
        support_gain = 5 + (10 * admin_skill)
        
        self.public_support += support_gain
        self.public_support = min(100, self.public_support)
        
        if admin_skill > 0.7:
            self.funding += 5
            self.funding = min(100, self.funding)
            self.message = f"Successful public outreach campaign! Public support increased by {int(support_gain)} points. Funding also increased."
        else:
            self.message = f"Public outreach campaign completed. Public support increased by {int(support_gain)} points."

class GameInterface:
    """Handles game display and interface"""
    def __init__(self):
        self.program = ContactProgram()
        
    def display_game(self):
        """Display the game state"""
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"\n=== LEGACY OF STARS: Generation {self.program.generation} ===")
        print(f"Director: {self.program.current_director.name}")
        print(f"Traits: {', '.join(self.program.current_director.traits)}")
        print(f"Skills: Diplomacy {int(self.program.current_director.get_effective_skill('diplomacy')*100)}%, "
              f"Science {int(self.program.current_director.get_effective_skill('science')*100)}%, "
              f"Administration {int(self.program.current_director.get_effective_skill('administration')*100)}%")
        
        print(f"\nProgram Status:")
        print(f"  Tech Level: {self.program.tech_level}")
        print(f"  Funding: {int(self.program.funding)}%")
        print(f"  Public Support: {int(self.program.public_support)}%")
        print(f"  Knowledge Base: {int(self.program.knowledge_base)}%")
        print(f"  Research Points: {int(self.program.research_points)}/100")
        
        # Display message if any
        if self.program.message:
            print(f"\n{self.program.message}")
            self.program.message = ""
        
        print("\n=== Star Systems ===")
        for i, (name, system) in enumerate(self.program.star_systems.items(), 1):
            print(f"{i}. {name} ({system.distance:.1f} light years)")
            print(f"   Knowledge: {int(system.knowledge)}%")
            if system.knowledge > 0:
                print(f"   Status: {system.describe_civilization()}")
            if system.messages_sent:
                print(f"   Messages Sent: {len(system.messages_sent)}")
            if system.received_messages:
                print(f"   Responses Received: {len(system.received_messages)}")
            if system.pending_responses:
                next_response = min([arrival for _, arrival in system.pending_responses])
                print(f"   Next Response: Generation {next_response}")
            print()
    
    def get_system_by_number(self, number: int) -> str:
        """Get system name by display number"""
        if 1 <= number <= len(self.program.star_systems):
            return list(self.program.star_systems.keys())[number-1]
        return None
        
    def play(self):
        """Main game loop"""
        print("\n=== LEGACY OF STARS ===")
        print("You are the overseer of Earth's multi-generational interstellar contact program.")
        print("Your mission is to establish communication with alien civilizations across the stars.")
        print("Each turn represents a generation (~25 years) of human history.")
        print("Make wise decisions to ensure the program's longevity and success.\n")
        print("Win by establishing contact (receiving responses) from at least 3 civilizations.")
        
        input("Press Enter to begin...")
        
        while not self.program.game_over:
            self.display_game()
            
            print("\nActions:")
            print("1. Send Message to Star System")
            print("2. Focus Research on Star System")
            print("3. Conduct Public Outreach Campaign")
            print("4. Advance to Next Generation")
            print("5. Quit Game")
            
            choice = input("\nEnter your choice (1-5): ")
            
            if choice == '1':
                system_num = input("Enter star system number: ")
                try:
                    system_num = int(system_num)
                    system_name = self.get_system_by_number(system_num)
                    if system_name:
                        message = input("Enter message content: ")
                        self.program.send_message(system_name, message)
                    else:
                        self.program.message = "Invalid star system number."
                except ValueError:
                    self.program.message = "Please enter a valid number."
            
            elif choice == '2':
                system_num = input("Enter star system number to research: ")
                try:
                    system_num = int(system_num)
                    system_name = self.get_system_by_number(system_num)
                    if system_name:
                        self.program.focus_research(system_name)
                    else:
                        self.program.message = "Invalid star system number."
                except ValueError:
                    self.program.message = "Please enter a valid number."
            
            elif choice == '3':
                self.program.public_outreach()
                
            elif choice == '4':
                self.program.advance_generation()
                
            elif choice == '5':
                confirm = input("Are you sure you want to quit? (y/n): ")
                if confirm.lower() == 'y':
                    self.program.game_over = True
                    print("Thanks for playing!")
            
            else:
                self.program.message = "Invalid choice. Please enter a number from 1 to 5."
        
        # Final display after game ends
        self.display_game()
        
        if self.program.victory:
            print("\nCONGRATULATIONS!")
            print("Earth has successfully established contact with multiple alien civilizations.")
            print("A new era of interstellar cooperation and knowledge exchange has begun.")
        else:
            print("\nTHE PROGRAM HAS ENDED")
            print("Despite your efforts, Earth's interstellar contact program has been discontinued.")
            print(f"You reached Generation {self.program.generation} and achieved a Knowledge Base of {int(self.program.knowledge_base)}%.")
        
        print("\nThank you for playing Legacy of Stars!")

if __name__ == "__main__":
    game = GameInterface()
    game.play()