import random
import time
import os
import json
from enum import Enum
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import logging
import datetime
from ai_manager import AIManager

class CivilizationStage(Enum):
    PRE_RADIO = 0
    EARLY_RADIO = 1
    DIGITAL = 2
    INTERPLANETARY = 3
    INTERSTELLAR = 4
    POST_BIOLOGICAL = 5

class Technology:
    def __init__(self, data: dict):
        self.id = data["id"]
        self.name = data["name"]
        self.description = data["description"]
        self.cost = data["cost"]
        self.prerequisites = data["prerequisites"]
        self.category = data["category"]
        self.doctrine_choice = data.get("doctrine_choice")
        self.researched = False
        self.chosen_doctrine = None

class KnowledgeBank:
    """Tracks preserved knowledge across generations"""
    def __init__(self):
        self.preserved_knowledge = {}  # topic -> integrity (0.0 - 1.0)
        self.capacity = 100
        self.decay_rate = 0.05

    def add_knowledge(self, topic: str, amount: float):
        current = self.preserved_knowledge.get(topic, 0.0)
        self.preserved_knowledge[topic] = min(1.0, current + amount)

    def degrade(self):
        """Apply decay to all knowledge"""
        for topic in list(self.preserved_knowledge.keys()):
            self.preserved_knowledge[topic] -= self.decay_rate
            if self.preserved_knowledge[topic] <= 0:
                del self.preserved_knowledge[topic]

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
        
        # New Mechanics
        self.knowledge_bank = KnowledgeBank()
        self.technologies = self.load_tech_tree()
        self.self_destruct_risk = 0.0
        self.accident_risk = 0.0
        self.ecological_risk = 0.0
        self.active_doctrines = []
        self.start_year = datetime.datetime.now().year
        
        # Action Economy
        self.action_points = 0
        self.max_action_points = 0
        self.calculate_ap()
        
        # AI Manager
        self.ai = AIManager()
        
    def load_tech_tree(self) -> Dict[str, Technology]:
        """Load technologies from JSON"""
        try:
            path = Path("data/tech_tree.json")
            if not path.exists():
                return {}
            with open(path, "r") as f:
                data = json.load(f)
                return {t["id"]: Technology(t) for t in data["technologies"]}
        except Exception as e:
            print(f"Error loading tech tree: {e}")
            return {}

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
    
    def calculate_ap(self):
        """Calculate Action Points for the current generation"""
        base_ap = 2
        
        # Public Mandate
        if self.public_support > 70:
            base_ap += 1
            
        # Well Funded
        if self.funding > 70:
            base_ap += 1
            
        # Efficient Administration
        if self.current_director.get_effective_skill("administration") > 0.7:
            base_ap += 1
            
        self.max_action_points = base_ap
        self.action_points = base_ap

    def research_tech(self, tech_id: str) -> bool:
        """Attempt to research a technology"""
        if tech_id not in self.technologies:
            return False
            
        tech = self.technologies[tech_id]
        if tech.researched:
            return False
            
        if self.research_points < tech.cost:
            self.message = f"Insufficient Research Points. Need {tech.cost}, have {int(self.research_points)}."
            return False
            
        # Check prerequisites
        for prereq in tech.prerequisites:
            if not self.technologies[prereq].researched:
                return False
                
        # Research complete
        self.research_points -= tech.cost
        tech.researched = True
        self.message = f"Researched {tech.name}!"
        logging.info(f"Researched Technology: {tech.name}")
        
        # Check for doctrine choice
        if tech.doctrine_choice:
            return True # Signal that a choice is needed
            
        return False

    def choose_doctrine(self, tech_id: str, option_index: int):
        """Apply effects of a doctrine choice"""
        tech = self.technologies[tech_id]
        choice = tech.doctrine_choice["options"][option_index]
        tech.chosen_doctrine = choice["name"]
        
        effects = choice.get("effects", {})
        if "security" in effects:
            # Implement security logic
            pass
        if "public_support" in effects:
            self.public_support += effects["public_support"]
        if "self_destruct_risk" in effects:
            self.self_destruct_risk += effects["self_destruct_risk"]
        if "accident_risk" in effects:
            self.accident_risk += effects["accident_risk"]
            
        self.active_doctrines.append(choice["name"])
        self.message = f"Doctrine adopted: {choice['name']}"
        logging.info(f"Doctrine Adopted: {choice['name']} for {tech.name}")

        return None
        
    def advance_generation(self):
        """Advance to the next generation"""
        self.generation += 1
        logging.info(f"--- Advanced to Generation {self.generation} ---")
        
        # Knowledge Decay
        self.knowledge_bank.degrade()
        
        # Support Decay (Fatigue)
        decay_amount = 0.5
        if "global_education" in self.technologies and self.technologies["global_education"].researched:
            decay_amount -= 0.2
        self.public_support -= decay_amount
        
        # Increasing Risks
        self.self_destruct_risk += 0.001 # +0.1% per gen
        self.ecological_risk += 0.005 # +0.5% per gen
        
        # Risk Checks (The Great Filter)
        if random.random() < self.self_destruct_risk:
            self.game_over = True
            self.message = "GAME OVER: Civilization collapsed due to internal conflict (Self-Destruction)."
            logging.info("GAME OVER: Self-Destruction triggered.")
            return
            
        if random.random() < self.ecological_risk:
            self.public_support -= 15
            self.message = "ECOLOGICAL COLLAPSE: Environmental degradation has caused famine and unrest. Public support plummets."
            logging.info("EVENT: Ecological Collapse triggered.")
            
        if random.random() < self.accident_risk:
            self.public_support -= 20
            self.message = "MAJOR ACCIDENT: A technological catastrophe has damaged public trust."
        
        # Process pending messages
        for system in self.star_systems.values():
            responses_to_remove = []
            
            for response in system.pending_responses:
                message, arrival_generation = response
                if arrival_generation <= self.generation:
                    # Message has arrived
                    system.received_messages.append(message)
                    logging.info(f"Message Received from {system.name}: {message[:50]}...")
                    
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
        
        # Passive Research Gain
        self.research_points += 10 + (self.funding / 10)
        
        # Funding changes based on public support
        support_modifier = (self.public_support - 50) / 10
        self.funding += support_modifier
        self.funding = max(20, min(100, self.funding))
        
        # Message quality improves with tech and knowledge
        self.message_quality = 1.0 + (self.tech_level * 0.1) + (self.knowledge_base / 100)
        
        # New director each generation
        self.current_director = self.generate_director()
        self.directors.append(self.current_director)
        
        # Calculate AP for new generation
        self.calculate_ap()
        
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
        if self.action_points < 1:
            self.message = "Not enough Action Points!"
            return

        if system_name not in self.star_systems:
            self.message = f"System {system_name} not found in database."
            return
            
        system = self.star_systems[system_name]
        
        # Record that we sent a message
        system.messages_sent.append((message_content, self.generation))
        logging.info(f"Message Sent to {system_name}: {message_content}")
        
        # Deduct AP
        self.action_points -= 1
        
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
                
                # Generate response using AI
                print(f"Generating response from {system_name} (this may take a moment)...")
                
                # Construct System Prompt based on traits
                attitude_desc = "friendly" if system.civilization_attitude > 0.6 else "hostile" if system.civilization_attitude < 0.4 else "cautious"
                tech_desc = system.civilization_stage.name
                
                # Build Earth Context based on Alien Tech Level
                earth_context = ""
                if system.civilization_stage.value >= CivilizationStage.DIGITAL.value:
                    earth_context += f" You detect that Earth is at Tech Level {self.tech_level}."
                
                if system.civilization_stage.value >= CivilizationStage.INTERSTELLAR.value:
                    if self.active_doctrines:
                        earth_context += f" You detect their active doctrines: {', '.join(self.active_doctrines)}."
                    
                    stability = "stable" if self.public_support > 60 else "unstable"
                    earth_context += f" You sense their civilization is politically {stability}."

                system_prompt = f"You are an alien diplomat from the star system {system_name}. " \
                                f"Your civilization is at the {tech_desc} stage of development. " \
                                f"Your attitude towards Earth is {attitude_desc}. " \
                                f"{earth_context} " \
                                f"Respond to the human message. Be creative, alien, and consistent with your tech level."

                user_prompt = f"Human Message: {message_content}"
                
                response_text = self.ai.generate_text(user_prompt, system_prompt)
                
                system.pending_responses.append((response_text, arrival_generation))
                
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
        if self.action_points < 1:
            self.message = "Not enough Action Points!"
            return

        if system_name not in self.star_systems:
            self.message = f"System {system_name} not found in database."
            return
            
        system = self.star_systems[system_name]
        
        # Deduct AP
        self.action_points -= 1
        
        # Research effectiveness based on science skill
        science_factor = self.current_director.get_effective_skill("science")
        knowledge_gain = 10 * science_factor
        
        # Tech Bonus: Deep Space Listening
        if "deep_space_listening" in self.technologies and self.technologies["deep_space_listening"].researched:
            knowledge_gain += 2

        # Apply knowledge gain
        old_knowledge = system.knowledge
        system.knowledge += knowledge_gain
        system.knowledge = min(100, system.knowledge)
        
        # Research points
        self.research_points += 5 * science_factor
        
        self.message = f"Research focused on {system_name}. Knowledge increased by {int(knowledge_gain)} points."
        logging.info(f"Research Focused on {system_name}. Knowledge +{int(knowledge_gain)}")

        # Check for Discovery Bonus (Crossing 20% threshold)
        if old_knowledge < 20 and system.knowledge >= 20 and system.has_civilization:
            self.public_support += 20
            self.public_support = min(100, self.public_support)
            self.research_points += 50
            self.message += f"\n*** MAJOR DISCOVERY: Civilization Detected at {system_name}! (+20 Support, +50 RP) ***"
            logging.info(f"MAJOR DISCOVERY: Civilization Detected at {system_name}")

    def public_outreach(self):
        """Conduct public outreach to boost support"""
        if self.action_points < 1:
            self.message = "Not enough Action Points!"
            return
            
        # Deduct AP
        self.action_points -= 1

        admin_skill = self.current_director.get_effective_skill("administration")
        support_gain = 10 + (20 * admin_skill)
        
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
        current_year = self.program.start_year + ((self.program.generation - 1) * 25)
        print(f"\n=== LEGACY OF STARS: Generation {self.program.generation} (Year {current_year}) ===")
        print(f"Director: {self.program.current_director.name}")
        print(f"Traits: {', '.join(self.program.current_director.traits)}")
        print(f"Skills: Diplomacy {int(self.program.current_director.get_effective_skill('diplomacy')*100)}%, "
              f"Science {int(self.program.current_director.get_effective_skill('science')*100)}%, "
              f"Administration {int(self.program.current_director.get_effective_skill('administration')*100)}%")
        
        # Calculate passive income
        passive_income = 10 + (self.program.funding / 10)
        
        print(f"\nProgram Status:")
        print(f"  Action Points: {self.program.action_points}/{self.program.max_action_points}")
        print(f"  Funding: {int(self.program.funding)}%")
        print(f"  Public Support: {int(self.program.public_support)}%")
        print(f"  Knowledge Base: {int(self.program.knowledge_base)}%")
        print(f"  Research Points: {int(self.program.research_points)} (+{int(passive_income)}/turn)")
        print(f"  Self-Destruct Risk: {self.program.self_destruct_risk*100:.1f}%")
        print(f"  Ecological Risk: {self.program.ecological_risk*100:.1f}%")
        
        if self.program.active_doctrines:
            print(f"  Active Doctrines: {', '.join(self.program.active_doctrines)}")
        
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
                for msg, gen in system.messages_sent:
                    round_trip = system.get_round_trip_time()
                    arrival_gen = gen + (round_trip / 2) # One way
                    arrival_year = self.program.start_year + ((arrival_gen - 1) * 25)
                    print(f"      - Sent Gen {gen}. Est. Arrival: Gen {int(arrival_gen)} (Year {int(arrival_year)})")
            if system.received_messages:
                print(f"   Responses Received: {len(system.received_messages)}")
                for msg in system.received_messages:
                    print(f"      > \"{msg}\"")
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
            print("1. Send Message to Star System (1 AP)")
            print("2. Focus Research on Star System (1 AP)")
            print("3. Conduct Public Outreach Campaign (1 AP)")
            print("4. Research Technology (Free)")
            print("5. Advance to Next Generation")
            print("6. Quit Game")
            
            choice = input("\nEnter your choice (1-6): ")
            
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
                print("\nAvailable Research:")
                available_techs = []
                for tech_id, tech in self.program.technologies.items():
                    if not tech.researched:
                        # Check prerequisites
                        prereqs_met = True
                        for prereq in tech.prerequisites:
                            if not self.program.technologies[prereq].researched:
                                prereqs_met = False
                                break
                        
                        if prereqs_met:
                            available_techs.append(tech)
                            print(f"{len(available_techs)}. {tech.name} (Cost: {tech.cost}) - {tech.description}")
                
                if not available_techs:
                    self.program.message = "No new technologies available to research."
                else:
                    tech_choice = input("Enter tech number to research (or 0 to cancel): ")
                    try:
                        tech_idx = int(tech_choice) - 1
                        if 0 <= tech_idx < len(available_techs):
                            tech = available_techs[tech_idx]
                            needs_doctrine = self.program.research_tech(tech.id)
                            
                            if needs_doctrine:
                                print(f"\n*** DOCTRINE CHOICE REQUIRED: {tech.doctrine_choice['name']} ***")
                                print(tech.doctrine_choice['description'])
                                for i, option in enumerate(tech.doctrine_choice['options']):
                                    print(f"{i+1}. {option['name']}: {option['description']}")
                                
                                doc_choice = input("Choose doctrine (1-2): ")
                                try:
                                    doc_idx = int(doc_choice) - 1
                                    if 0 <= doc_idx < len(tech.doctrine_choice['options']):
                                        self.program.choose_doctrine(tech.id, doc_idx)
                                    else:
                                        print("Invalid choice. Defaulting to first option.")
                                        self.program.choose_doctrine(tech.id, 0)
                                except ValueError:
                                    print("Invalid input. Defaulting to first option.")
                                    self.program.choose_doctrine(tech.id, 0)
                        elif tech_idx != -1:
                            self.program.message = "Invalid selection."
                    except ValueError:
                        self.program.message = "Invalid input."

            elif choice == '5':
                self.program.advance_generation()
                
            elif choice == '6':
                confirm = input("Are you sure you want to quit? (y/n): ")
                if confirm.lower() == 'y':
                    self.program.game_over = True
                    print("Thanks for playing!")
            
            else:
                self.program.message = "Invalid choice. Please enter a number from 1 to 6."
        
        # Final display after game ends
        self.display_game()
        
        if self.program.victory:
            print("\nCONGRATULATIONS!")
            print("Earth has successfully established contact with multiple alien civilizations.")
            print("A new era of interstellar cooperation and knowledge exchange has begun.")
            logging.info("GAME OVER: VICTORY - Contact established with 3+ civilizations.")
        else:
            print("\nTHE PROGRAM HAS ENDED")
            print("Despite your efforts, Earth's interstellar contact program has been discontinued.")
            print(f"You reached Generation {self.program.generation} and achieved a Knowledge Base of {int(self.program.knowledge_base)}%.")
            logging.info(f"GAME OVER: Defeat/Discontinued. Gen {self.program.generation}, Knowledge {int(self.program.knowledge_base)}%")
        
        print("\nThank you for playing Legacy of Stars!")

if __name__ == "__main__":
    logging.basicConfig(filename='game.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.info("Game started.")
    game = GameInterface()
    game.play()