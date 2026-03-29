import random
import time
import os
import json
from enum import Enum
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import logging
import datetime
from .ai_manager import AIManager
from .wow_signal_event import WOWSignalEvent
from .attack_warning import AttackWarning
from .ai_strategic_advisor import AIStrategicAdvisor
from .swan_song_messages import SwanSongManager
from .passive_leakage import PassiveLeakageSystem
from .integration_progress import IntegrationProgress
from .philosophical_events import PhilosophicalEvents
from .genesis_project import GenesisProject

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
        self.tier = data.get("tier", 0)
        self.min_generation = data.get("min_generation", 1)
        self.year_context = data.get("year_context", "")
        self.special = data.get("special", None)
        self.passive_rp = data.get("passive_rp", 0)  # New: Passive research points per turn
        self.is_legacy = False  # Flag for pre-1977 legacy knowledge
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
        self.distance = distance
        self.has_civilization = random.random() < 0.3
        
        if self.has_civilization:
            # === PHASE 1: Statistical Realism ===
            human_age = 100
            
            if random.random() < 0.75:
                civ_age = human_age * random.uniform(1.5, 50)
            else:
                civ_age = human_age * random.uniform(0.1, 0.9)
            
            if random.random() < 0.10:
                civ_age = human_age * random.uniform(10, 1000)
            
            self.civilization_age = civ_age
            self.civilization_stage = self._age_to_stage(civ_age)
            
            self.is_extinct = random.random() < 0.15
            if self.is_extinct:
                self.extinct_years_ago = random.randint(500, 5000)
                self.has_swan_song = random.random() < 0.8
                self.civilization_stage = None
            
            if not self.is_extinct:
                strategy_weights = {"L": 10, "LB": 30, "LR": 40, "LA": 15, "LBA": 5}
                self.true_strategy = random.choices(list(strategy_weights.keys()), weights=list(strategy_weights.values()))[0]
                
                if self.civilization_age > human_age * 2:
                    self.deception_level = random.uniform(0.3, 1.0)
                else:
                    self.deception_level = random.uniform(0, 0.5)
            else:
                self.true_strategy = None
                self.deception_level = 0
            
            # === PHASE 3A.2: Civilization Type (How they solved Dual DNA problem) ===
            if not self.is_extinct:
                # Living civilizations - successfully solved the integration crisis
                civ_type_weights = {
                    "biological_pure": 20,      # Stayed biological, cautious
                    "digital_ascended": 15,     # Uploaded consciousness
                    "hybrid_integrated": 10     # Successfully merged
                }
                self.civilization_type = random.choices(
                    list(civ_type_weights.keys()),
                    weights=list(civ_type_weights.values())
                )[0]
            else:
                # Extinct civilizations - 70% failed the transition
                if random.random() < 0.7:
                    self.civilization_type = "failed_transition"
                else:
                    # Some died for other reasons (war, asteroid, etc.)
                    self.civilization_type = random.choice([
                        "biological_pure", "digital_ascended", "hybrid_integrated"
                    ])
            
            self.civilization_attitude = random.uniform(0.2, 0.8)
        else:
            self.civilization_age = 0
            self.civilization_stage = None
            self.civilization_attitude = 0
            self.is_extinct = False
            self.has_swan_song = False
            self.true_strategy = None
            self.deception_level = 0
            self.civilization_type = None  # No civilization, no type
            
        self.knowledge = 0
        self.messages_sent = []
        self.pending_responses = []
        self.received_messages = []
        self.pending_attack = None
    
    def _age_to_stage(self, age: float) -> CivilizationStage:
        if age < 50:
            return CivilizationStage.PRE_RADIO
        elif age < 200:
            return CivilizationStage.EARLY_RADIO
        elif age < 1000:
            return CivilizationStage.DIGITAL
        elif age < 10000:
            return CivilizationStage.INTERPLANETARY
        elif age < 100000:
            return CivilizationStage.INTERSTELLAR
        else:
            return CivilizationStage.POST_BIOLOGICAL
    
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
        
        # Handle extinct civilizations (civilization_stage is None)
        if self.is_extinct:
            if self.knowledge < 20:
                return "Faint signals detected. System appears lifeless."
            elif self.knowledge < 60:
                return f"EXTINCT CIVILIZATION detected. Dead for ~{self.extinct_years_ago} years."
            else:
                swan_info = " Data archives may exist." if self.has_swan_song else " No archives detected."
                return f"EXTINCT: Civilization collapsed {self.extinct_years_ago} years ago.{swan_info}"
            
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
        if "Direct" in self.traits and skill == "diplomacy":
             bonus -= 0.1 # Direct is bad for diplomacy maybe? Or good? Let's say bad for nuances but good for action.
             
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
        
        # === DEBUG: Log all civilization details at game start ===
        logging.debug("")
        logging.debug("="*60)
        logging.debug("GALAXY OVERVIEW - Hidden Civilization Details")
        logging.debug("="*60)
        for name, system in self.star_systems.items():
            if system.has_civilization:
                if system.is_extinct:
                    logging.debug(f"  {name} ({system.distance:.1f} LY) - EXTINCT")
                    logging.debug(f"    Age: {int(system.civilization_age)} years")
                    logging.debug(f"    Died: {system.extinct_years_ago} years ago")
                    logging.debug(f"    Swan Song: {'YES' if system.has_swan_song else 'NO'}")
                    logging.debug(f"    Type: {system.civilization_type}")
                else:
                    logging.debug(f"  {name} ({system.distance:.1f} LY) - ACTIVE")
                    logging.debug(f"    Age: {int(system.civilization_age)} years")
                    logging.debug(f"    Stage: {system.civilization_stage.name}")
                    logging.debug(f"    Strategy: {system.true_strategy}")
                    logging.debug(f"    Deception: {system.deception_level:.2f}")
                    logging.debug(f"    Type: {system.civilization_type}")

                    strategy_desc = {
                        "L": "Listen Only - Will NEVER respond",
                        "LB": "Listen & Broadcast - Enthusiastic, friendly METI",
                        "LR": "Listen & Reply - Cautious, only responds when contacted",
                        "LA": "Listen & Annihilate - HOSTILE, attacks silently",
                        "LBA": "Listen, Broadcast & Annihilate - TRAP! Friendly bait then attack"
                    }
                    logging.debug(f"    >>> {strategy_desc[system.true_strategy]}")
            else:
                logging.debug(f"  {name} ({system.distance:.1f} LY) - No civilization")
            logging.debug("")

        logging.debug("="*60)
        logging.debug("")
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
        self.start_year = 1977  # WOW! Signal era
        
        # Action Economy
        self.action_points = 0
        self.max_action_points = 0
        self.calculate_ap()
        
        # AI Manager
        self.ai = AIManager()
        
        # WOW! Signal Event System
        self.wow_signal = WOWSignalEvent(self)
        
        # Attack Early Warning System
        self.pending_attack_warnings = []
        
        # Tech Tree Special Effects
        self.passive_defense_bonus = 1.0  # Multiplier for passive defense (1.0 = no bonus)
        self.warning_time_bonus = 0  # Extra generations of warning time
        self.has_backup_colonies = False  # Prevents total annihilation
        self.cloaking_active = False  # Reduces passive detection
        self.ai_advisor_unlocked = False  # AI Strategic Advisor feature
        self.can_contact_post_biological = False  # Post-biological civilizations
        self.ultimate_survival = False  # Ultimate survival guarantee
        
        # AI Strategic Advisor
        self.ai_advisor = AIStrategicAdvisor(self.ai)
        self.advisor_consulted_this_gen = False  # Track if already consulted this generation
        
        # Swan Song Messages Manager
        self.swan_song_manager = SwanSongManager(self.ai)
        
        # Create swan songs for extinct civilizations
        for name, system in self.star_systems.items():
            if system.has_civilization and system.is_extinct and system.has_swan_song:
                self.swan_song_manager.create_swan_song(
                    name, 
                    system.extinct_years_ago, 
                    system.civilization_age
                )
                logging.info(f"Swan Song created for {name}")
        
        # Mark pre-1977 technologies as legacy knowledge (already known at game start)
        legacy_techs = [
            "arecibo_telescope",        # Built 1963
            "drake_equation",           # Published 1961
            "project_ozma",             # Conducted 1960
            "signal_processing_basic",  # 1970s technology
            "voyager_golden_record"     # Launched 1977
        ]
        
        for tech_id in legacy_techs:
            if tech_id in self.technologies:
                tech = self.technologies[tech_id]
                tech.researched = True
                tech.is_legacy = True
                logging.info(f"Legacy Knowledge: {tech.name} (pre-1977)")
        
        # Passive Signal Leakage System
        self.leakage_system = PassiveLeakageSystem()
        self.broadcast_radius = 0  # Will be calculated each generation
        self.leakage_multiplier = 1.0  # 1.0 = full leakage, 0.0 = complete silence
        
        # Probe Technology Flags
        self.has_solar_sails = False
        self.has_laser_sails = False
        self.message_delivery_speed = 1.0  # Speed of light (default)
        self.von_neumann_defense_bonus = 1.0  # 1.0 = no bonus
        self.has_fusion_propulsion = False
        self.can_send_heavy_probes = False
        
        # === PHASE 3A.1: Integration Progress System ===
        self.integration = IntegrationProgress()
        logging.info("Phase 3A.1: Integration Progress System initialized")
        
        # === PHASE 3A.2: Philosophical Events System ===
        self.philosophical_events = PhilosophicalEvents()
        self.pending_philosophical_event = None  # Stores event waiting for player choice
        logging.info("Phase 3A.2: Philosophical Events System initialized")
        
        # === PHASE 3A.3: Philosophical Victory Tracking ===
        self.fermi_evidence = {
            "extinction_evidence": 0,       # Swan songs discovered
            "dark_forest_evidence": 0,      # Hostile encounters (LA/LBA attacks)
            "cooperation_evidence": 0,      # Successful peaceful contacts (LB/LR)
            "great_filter_evidence": 0      # Integration techs researched
        }
        self.philosophical_victory = False  # Separate from contact victory
        logging.info("Phase 3A.3: Philosophical Victory tracking initialized")

        # === PHASE 3B: Genesis Project ===
        self.genesis = GenesisProject()
        self.message_queue = [] # Queue for Genesis events and other async messages
        logging.info("Phase 3B: Genesis Project initialized")
        
    def load_tech_tree(self) -> Dict[str, Technology]:
        """Load technologies from JSON"""
        try:
            path = Path(__file__).parent.parent / "data" / "tech_tree.json"
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
        
        # Check minimum generation requirement
        if self.generation < tech.min_generation:
            min_year = self.start_year + ((tech.min_generation - 1) * 25)
            self.message = f"Technology not yet available. Unlocks in Generation {tech.min_generation} (Year {min_year})."
            return False
            
        # Director Science Skill: Reduces research cost
        science_skill = self.current_director.get_effective_skill("science")
        cost_modifier = 1.1 - (0.4 * science_skill)
        effective_cost = int(tech.cost * cost_modifier)
        
        if self.research_points < effective_cost:
            self.message = f"Not enough Research Points! Need {effective_cost} (Base: {tech.cost}, Director Efficiency: {int((1-cost_modifier)*100)}%)"
            return False
            
        # Check prerequisites
        for prereq_id in tech.prerequisites:
            if prereq_id not in self.technologies or not self.technologies[prereq_id].researched:
                prereq_name = self.technologies[prereq_id].name if prereq_id in self.technologies else prereq_id
                self.message = f"Prerequisite not met: {prereq_name}"
                return False
        
        # Handle Swan Song discount
        final_cost = effective_cost
        discount_msg = ""
        swan_discount = 0.0
        
        if hasattr(self, 'swan_song_manager'):
             swan_discount = self.swan_song_manager.next_tech_discount
             if swan_discount > 0:
                 final_cost = int(final_cost * (1 - swan_discount))
                 discount_msg = f" (Discounted by {int(swan_discount*100)}%)"

        if self.research_points < final_cost:
            self.message = f"Not enough Research Points! Need {final_cost} (Base: {tech.cost}, Dir: {int(effective_cost)}, Discount: {int(swan_discount*100)}%)"
            return False
            
        # Consume discount if used
        if swan_discount > 0:
            self.swan_song_manager.get_tech_discount()

        # Research complete
        self.research_points -= final_cost
        tech.researched = True
        self.message = f"Researched {tech.name}!{discount_msg}\\nDirector Efficiency Saved {tech.cost - effective_cost} RP."
        logging.info(f"Researched Technology: {tech.name} (Tier {tech.tier}, Gen {self.generation})")
        
        # Apply special effects
        if tech.special:
            self._apply_tech_special_effect(tech)
        
        # Check for doctrine choice
        if tech.doctrine_choice:
            return True # Signal that a choice is needed
            
        return False

    def _apply_tech_special_effect(self, tech):
        """Apply special effects from technology research"""
        if tech.special == "passive_defense_40":
            self.passive_defense_bonus = 0.6
            logging.info(f"PASSIVE DEFENSE ACTIVATED: {tech.name} - 40% damage reduction")
            self.message += f"\\n🛡️ Passive Defense Online: All future attacks reduced by 40%"
            
        elif tech.special == "warning_time_bonus_2":
            self.warning_time_bonus = 2
            logging.info(f"EARLY WARNING ACTIVATED: {tech.name} - +2 generations warning time")
            self.message += f"\\n⚠️ Early Warning Active: +2 generations to prepare for attacks"
            
        elif tech.special == "prevents_annihilation":
            self.has_backup_colonies = True
            logging.info(f"BACKUP COLONIES ESTABLISHED: {tech.name}")
            self.message += f"\\n🌍 Backup Colonies Online: Humanity no longer depends on Earth alone"
            
        elif tech.special == "reduces_leakage":
            self.cloaking_active = True
            logging.info(f"CLOAKING ACTIVATED: {tech.name}")
            self.message += f"\\n🔇 Cloaking Active: Earth's electromagnetic signature reduced"
            
        elif tech.special == "unlocks_ai_advisor":
            self.ai_advisor_unlocked = True
            logging.info(f"AI ADVISOR UNLOCKED: {tech.name}")
            self.message += f"\\n🤖 AI Strategic Advisor unlocked!"
            
        elif tech.special == "unlock_post_bio_contact":
            self.can_contact_post_biological = True
            logging.info(f"POST-BIOLOGICAL CONTACT: {tech.name}")
            self.message += f"\\n✨ Post-Biological Contact enabled!"
            
        elif tech.special == "ultimate_survival":
            self.ultimate_survival = True
            logging.info(f"ULTIMATE SURVIVAL: {tech.name}")
            self.message += f"\\n🚀 Emergency Evacuation: Humanity WILL survive any attack"
            
        elif tech.special == "reduces_ecological_risk":
            self.ecological_risk = max(0.0, self.ecological_risk - 0.10)
            logging.info(f"ECOLOGICAL REMEDIATION: {tech.name} - Risk reduced by 10%")
            self.message += f"\\n🌱 Planetary Remediation: Ecological Risk reduced by 10%"
        
        elif tech.special == "passive_eco_scrubbing":
            logging.info(f"ECO TECHNOLOGY: {tech.name} - Passive scrubbing enabled")
            self.message += f"\\n🍃 Atmospheric Scrubbing: Passive ecological repair initiated"
            
        elif tech.special == "unlocks_nano_ecology":
            logging.info(f"ECO TECHNOLOGY: {tech.name} - Nano-swarm ready")
            self.message += f"\\n🌫️ Nano-Ecological Swarm: Active ecological purge capability unlocked"
        
        # === PASSIVE LEAKAGE MITIGATION TECHS ===
        elif tech.special == "reduces_leakage_30":
            self.leakage_multiplier *= 0.7
            logging.info(f"LEAKAGE REDUCTION: {tech.name} - 30%")
            self.message += f"\\n📡 Directional Transmission: Broadcast leakage reduced by 30%"
        
        elif tech.special == "reduces_leakage_50":
            self.leakage_multiplier *= 0.5
            logging.info(f"LEAKAGE REDUCTION: {tech.name} - 50%")
            self.message += f"\\n🔇 Radio Silence Protocol: Broadcast leakage reduced by 50%"
        
        elif tech.special == "reduces_leakage_80":
            self.leakage_multiplier *= 0.2
            self.cloaking_active = True
            logging.info(f"LEAKAGE REDUCTION: {tech.name} - 80%")
            self.message += f"\\n👻 Civilization Cloaking: Broadcast leakage reduced by 80%"
        
        elif tech.special == "dark_forest_protocol":
            self.leakage_multiplier = 0.0
            self.public_support -= 50
            logging.info(f"DARK FOREST PROTOCOL ACTIVATED: {tech.name}")
            self.message += f"\\n🌑 Dark Forest Protocol: Complete electromagnetic silence (-50% public support)"
        
        # === PROPULSION TECHNOLOGY UNLOCKS ===
        elif tech.special == "unlocks_solar_sails":
            self.has_solar_sails = True
            logging.info(f"PROPULSION UNLOCKED: {tech.name}")
            self.message += f"\\n☀️ Solar Sails: Foundation for advanced propulsion"
        
        elif tech.special == "unlocks_laser_sails":
            self.has_laser_sails = True
            self.message_delivery_speed = 0.175
            logging.info(f"PROPULSION UNLOCKED: {tech.name} - 0.175c")
            self.message += f"\\n🚀 Laser Sails: Message delivery time reduced by 83%"
        
        elif tech.special == "unlocks_von_neumann_defense":
            self.von_neumann_defense_bonus = 0.7
            logging.info(f"DEFENSE UNLOCKED: {tech.name}")
            self.message += f"\\n🛡️ Von Neumann Defense: +30% defense against probe attacks"
        
        elif tech.special == "unlocks_fusion_propulsion":
            self.has_fusion_propulsion = True
            self.can_send_heavy_probes = True
            logging.info(f"PROPULSION UNLOCKED: {tech.name}")
            self.message += f"\\n⚛️ Fusion Propulsion: Heavy payload delivery capability"
        
        # === INTEGRATION PROGRESS ===
        elif tech.special == "integration_30":
            self.integration.add_integration(0.3, tech.name)
            self.message += f"\\n🧬 {tech.name}: +30% integration progress"
            self.fermi_evidence["great_filter_evidence"] += 2
        
        elif tech.special == "integration_40":
            self.integration.add_integration(0.4, tech.name)
            self.message += f"\\n🧠 {tech.name}: +40% integration progress"
            self.fermi_evidence["great_filter_evidence"] += 2
        
        elif tech.special == "integration_60":
            self.integration.add_integration(0.6, tech.name)
            self.message += f"\\n💾 {tech.name}: +60% integration progress"
            self.fermi_evidence["great_filter_evidence"] += 2
            
        elif tech.special == "hybrid_civilization_complete":
            self.self_destruct_risk = 0.001
            self.integration.add_integration(0.1, tech.name)
            logging.info(f"HYBRID CIVILIZATION ACHIEVED")
            self.message += f"\\n✨ HYBRID CIVILIZATION COMPLETE ✨\\nSelf-destruct risk minimized."
            
        if hasattr(self, 'integration'):
            self.message += self.integration.get_display_message(self.generation)

    def process_information_attack(self, system_name: str):
        """Process an information warfare attack"""
        attack_types = ["corrupted_technology", "societal_manipulation", "false_hope_signal", "philosophical_weapon"]
        attack_type = random.choice(attack_types)
        
        if attack_type == "corrupted_technology":
            rp_loss = random.randint(100, 300)
            self.research_points = max(0, self.research_points - rp_loss)
            self.message = f"⚠️ INFO ATTACK ({system_name}): Corrupted Tech Data (-{rp_loss} RP)"
            logging.critical(f"Info Attack {system_name}: -{rp_loss} RP")
            
        elif attack_type == "societal_manipulation":
            support_loss = random.randint(15, 30)
            self.public_support -= support_loss
            self.message = f"⚠️ INFO ATTACK ({system_name}): Societal Manipulation (-{support_loss}% Support)"
            logging.critical(f"Info Attack {system_name}: -{support_loss} Support")
            
        elif attack_type == "false_hope_signal":
            funding_loss = random.randint(10, 25)
            support_loss = random.randint(5, 15)
            self.funding -= funding_loss
            self.public_support -= support_loss
            self.message = f"⚠️ INFO ATTACK ({system_name}): False Hope (-{funding_loss}% Funding, -{support_loss}% Support)"
            logging.critical(f"Info Attack {system_name}: False Hope")
            
        elif attack_type == "philosophical_weapon":
            risk_increase = 0.01
            self.self_destruct_risk += risk_increase
            self.public_support -= random.randint(10, 20)
            self.message = f"⚠️ INFO ATTACK ({system_name}): Philosophical Weapon (+1% Self-Destruct Risk)"
            logging.critical(f"Info Attack {system_name}: Philo Weapon")
        
        self.fermi_evidence["dark_forest_evidence"] += 1
        
        if self.public_support < 10 or self.funding < 20:
            self.game_over = True
            self.message += "\\nPROGRAM TERMINATED via Info War."

    def handle_philosophical_event_choice(self, choice_index: int) -> bool:
        """
        Handle player's choice for a philosophical event

        Args:
            choice_index: Index of the chosen option (0-based)

        Returns:
            True if choice was applied successfully, False otherwise
        """
        if not self.pending_philosophical_event:
            return False

        event = self.pending_philosophical_event
        result_message = self.philosophical_events.apply_choice_effects(event, choice_index, self)

        # Build response message
        self.message = f"""============================================================
         🤔 PHILOSOPHICAL EVENT: {event.name}
============================================================

CHOICE: {event.chosen_option}

{result_message}

============================================================
"""
        logging.info(f"PHILOSOPHICAL EVENT RESOLVED: {event.name} -> {event.chosen_option}")

        # Clear pending event
        self.pending_philosophical_event = None
        return True

    def get_philosophical_event_display(self) -> str:
        """
        Get formatted display text for pending philosophical event

        Returns:
            Formatted string for display, or empty string if no pending event
        """
        if not self.pending_philosophical_event:
            return ""

        event = self.pending_philosophical_event
        choices_text = ""
        for i, choice in enumerate(event.choices):
            choices_text += f"{i + 1}. {choice['name']}\n   {choice['description']}\n\n"

        return f"""============================================================
         🤔 PHILOSOPHICAL EVENT: {event.name}
============================================================

{event.description}

YOUR CHOICE:

{choices_text}============================================================
"""

    def advance_generation(self):
        """Advance to the next generation"""
        self.generation += 1
        logging.info(f"--- Advanced to Generation {self.generation} ---")
        
        # Knowledge Decay
        self.knowledge_bank.degrade()
        
        # Support Decay
        decay_amount = 0.5
        if "global_education" in self.technologies and self.technologies["global_education"].researched:
            decay_amount -= 0.2
        
        # Director Trait: Patient
        if "Patient" in self.current_director.traits:
            decay_amount -= 0.5
            logging.info("Director Trait (Patient): Reduced support decay")
            
        self.public_support -= max(0, decay_amount)

        # Integration Penalty
        integration_support_penalty = self.integration.get_support_penalty()
        if integration_support_penalty < 0:
            self.public_support += integration_support_penalty
        
        # Risks
        self.self_destruct_risk += 0.001
        
        eco_growth = 0.005
        if "planetary_remediation" in self.technologies and self.technologies["planetary_remediation"].researched:
            eco_growth = 0.002
        
        # Tech: Atmospheric Scrubbing
        if "atmospheric_scrubbing" in self.technologies and self.technologies["atmospheric_scrubbing"].researched:
            self.ecological_risk = max(0.0, self.ecological_risk - 0.001)
            
        self.ecological_risk += eco_growth
        
        # Director Trait: Traditional
        if "Traditional" in self.current_director.traits and self.public_support < 50:
             self.public_support += 1.0
        
        # Director Trait: Intuitive
        if "Intuitive" in self.current_director.traits and random.random() < 0.05:
            self.research_points += 50
            self.message = f"💡 Director Intuition: +50 RP!"

        # Risk Checks
        filter_modifier = self.integration.get_filter_risk_modifier()
        adjusted_self_destruct = self.self_destruct_risk * filter_modifier
        if self.generation <= 30: adjusted_self_destruct = 0.0
        
        if random.random() < adjusted_self_destruct:
            self.game_over = True
            self.message = "GAME OVER: Self-Destruction."
            return
            
        if self.generation > 30 and random.random() < self.ecological_risk:
            self.public_support -= 15
            self.message = "EVENT: Ecological Collapse."
        
        if self.generation > 30 and random.random() < self.accident_risk:
            self.public_support -= 20
            self.message = "EVENT: Major Accident."

        # Passive RP
        passive_rp = 0
        if "signal_processing_basic" in self.technologies and self.technologies["signal_processing_basic"].researched: passive_rp += 3
        if "seti_at_home" in self.technologies and self.technologies["seti_at_home"].researched: passive_rp += 15
        if "ai_pattern_recognition" in self.technologies and self.technologies["ai_pattern_recognition"].researched: passive_rp += 20
        # Director vision handled in knowledge gain usually, or here?
        # Visionary trait added to knowledge gain logic in legacy_of_stars_v3.py (Step 647)
        
        if passive_rp > 0:
            self.research_points += passive_rp
            
        # Process pending messages
        for system in self.star_systems.values():
            responses_to_remove = []
            
            for response in system.pending_responses:
                message, arrival_generation = response
                if arrival_generation <= self.generation:
                    system.received_messages.append(message)
                    
                    # Knowledge gain
                    k_gain = 10 * self.tech_level
                    
                    # Director Trait: Visionary
                    if "Visionary" in self.current_director.traits:
                        k_gain = int(k_gain * 1.1)
                        
                    system.knowledge = min(100, system.knowledge + k_gain)
                    self.knowledge_base = min(100, self.knowledge_base + 5)
                    self.public_support = min(100, self.public_support + 5)
                    responses_to_remove.append(response)
            
            for response in responses_to_remove:
                system.pending_responses.remove(response)
        
        # === PASSIVE SIGNAL LEAKAGE
        # Calculate Earth's current broadcast radius
        self.broadcast_radius = self.leakage_system.calculate_broadcast_radius(self.tech_level, self.technologies)
        
        # Apply leakage multiplier from mitigation technologies
        # (multiplier is already tracked in self.leakage_multiplier, updated when techs are researched)
        
        # Find all LA/LBA civilizations within broadcast radius
        for system_name, system in self.star_systems.items():
            if not system.has_civilization or system.is_extinct:
                continue
            
            # Only LA and LBA civilizations attack
            if system.true_strategy not in ["LA", "LBA"]:
                continue
                
            # Check if system is within broadcast radius
            if system.distance > self.broadcast_radius:
                continue
            
            # Check if they detect us (0.5% base chance per generation × leakage multiplier)
            detection_chance = self.leakage_system.calculate_detection_probability(
                system.distance, 
                self.broadcast_radius, 
                self.leakage_multiplier
            )
            
            if random.random() < detection_chance:
                # Hostile civilization has detected Earth!
                logging.critical(f"PASSIVE DETECTION: {system_name} ({system.true_strategy}) detected Earth via electromagnetic leakage!")
                
                # Determine attack type
                attack_type = self.leakage_system.determine_attack_type(system, system.distance)
                
                if attack_type == "information":
                    # Information attack arrives instantly
                    logging.warning(f"{system_name} launching INFORMATION WARFARE attack (instant)")
                    self.process_information_attack(system_name)
                    
                elif attack_type == "laser_sail":
                    # Laser sail probe attack (0.175c)
                    travel_time_gens = self.leakage_system.calculate_travel_time(
                        system.distance, 
                        0.175  # Breakthrough Starshot speed
                    )
                    arrival_gen = self.generation + travel_time_gens
                    
                    # Apply von Neumann defense bonus if researched
                    defense_mult = self.von_neumann_defense_bonus
                   
                    # Create attack warning
                    warning = AttackWarning(
                        source=system,
                        arrival_generation=arrival_gen,
                        attack_type="laser_sail_probe"
                    )
                    warning.defense_multiplier = defense_mult
                    self.pending_attack_warnings.append(warning)
                    
                    logging.warning(f"{system_name} launching LASER SAIL PROBE attack (0.175c) - ETA: {travel_time_gens} generations")
                    
                elif attack_type == "fusion":
                    # Fusion strike (0.12c)
                    travel_time_gens = self.leakage_system.calculate_travel_time(
                        system.distance,
                        0.12  # Project Daedalus speed
                    )
                    arrival_gen = self.generation + travel_time_gens
                    
                    # Create attack warning
                    warning = AttackWarning(
                        source=system,
                        arrival_generation=arrival_gen,
                        attack_type="fusion_strike"
                    )
                    self.pending_attack_warnings.append(warning)
                    
                    logging.warning(f"{system_name} launching FUSION STRIKE (0.12c) - ETA: {travel_time_gens} generations")

        # === WOW! SIGNAL: Check for Gen 144 Event ===

        if self.wow_signal.check_gen144_event():
            self.wow_signal.trigger_gen144_event()
            return

        # === ATTACK EARLY WARNING SYSTEM: Process Incoming Attacks ===
        warnings_to_remove = []
        
        for warning in self.pending_attack_warnings:
            etas = warning.get_etas_remaining(self.generation)
            
            # Show countdown warnings
            if etas > 0:
                logging.warning(f"⚠️ HOSTILE FLEET from {warning.source.name} - ETA: {etas} generations")
            
            # Attack arrives
            if etas <= 0:
                logging.critical(f"⚠️⚠️⚠️ ATTACK ARRIVED from {warning.source.name}! ⚠️⚠️⚠️")
                
                # Calculate base damage tier
                tech_gap = warning.source.civilization_stage.value - self.tech_level
                
                # Apply defensive multiplier
                base_support_loss = 0
                base_funding_loss = 0
                game_over_attack = False
                
                if tech_gap >= 2:
                    # Devastating attack
                    base_support_loss = 50
                    base_funding_loss = 40
                    game_over_attack = True
                elif tech_gap >= 1:
                    # Advanced attack
                    base_support_loss = 40
                    base_funding_loss = 30
                else:
                    # Comparable tech
                    base_support_loss = 25
                    base_funding_loss = 15
                
                # Apply defense multipliers (active + passive)
                total_defense_multiplier = warning.defense_multiplier * self.passive_defense_bonus
                actual_support_loss = int(base_support_loss * total_defense_multiplier)
                actual_funding_loss = int(base_funding_loss * total_defense_multiplier)
                
                # Check if backup colonies prevent annihilation
                if game_over_attack and self.has_backup_colonies:
                    game_over_attack = False  # Backup colonies save us
                    logging.critical(f"BACKUP COLONIES SAVE HUMANITY: Earth devastated but colonies survive")
                
                # Check if ultimate survival is active
                if game_over_attack and self.ultimate_survival:
                    game_over_attack = False
                    actual_support_loss = min(actual_support_loss, 30)
                    actual_funding_loss = min(actual_funding_loss, 20)
                    logging.critical(f"ULTIMATE SURVIVAL ACTIVE: Emergency evacuation successful")
                
                self.public_support -= actual_support_loss
                self.funding -= actual_funding_loss
                
                # Build attack message
                defense_info = ""
                if warning.defensive_actions_taken:
                    defense_info = f"\n\n🛡️ DEFENSIVE ACTIONS TAKEN:\n"
                    for action in warning.defensive_actions_taken:
                        defense_info += f"  ✓ {action}\n"
                    defense_info += f"\nDamage reduced by {warning.get_defense_percentage()}%"
                
                if game_over_attack and warning.defense_multiplier > 0.3:
                    # Defenses were strong enough to survive a devastating attack
                    self.message = f"""⚠️ DEVASTATING ATTACK FROM {warning.source.name.upper()}! ⚠️

Their {CivilizationStage(warning.source.civilization_stage.value).name} technology far exceeds ours.
Support: -{actual_support_loss}% | Funding: -{actual_funding_loss}%{defense_info}

Thanks to our defensive preparations, we survived - barely.
"""
                    logging.critical(f"Survived devastating attack with defenses: {warning.get_defense_percentage()}% reduction")
                elif game_over_attack:
                    # Not enough defenses
                    self.game_over = True
                    self.message = f"""💀 GAME OVER: EARTH ANNIHILATED 💀

{warning.source.name}'s overwhelming technological superiority ({CivilizationStage(warning.source.civilization_stage.value).name} vs our tech level {self.tech_level}) has proven catastrophic.

The attack fleet has destroyed all major population centers.
Humanity's first contact... was its last.{defense_info}

Dark Forest theory confirmed.
"""
                    logging.critical(f"GAME OVER: Annihilated by {warning.source.name}")
                    warnings_to_remove.append(warning)
                    return
                else:
                    # Survivable attack
                    severity = "ADVANCED" if tech_gap >= 1 else "SIGNIFICANT"
                    self.message = f"""⚠️ {severity} ATTACK FROM {warning.source.name.upper()}! ⚠️

Enemy fleet has struck Earth!
Support: -{actual_support_loss}% | Funding: -{actual_funding_loss}%{defense_info}

The program survives, but at great cost.
"""
                
                warnings_to_remove.append(warning)
                
                # Check if program is defunded
                if self.funding < 20 or self.public_support < 10:
                    self.game_over = True
                    self.message += "\n\nPublic support and funding have collapsed. The contact program is shut down."
                    logging.critical("GAME OVER: Program defunded after attack")
                    return
        
        # Remove processed warnings
        for warning in warnings_to_remove:
            if warning in self.pending_attack_warnings:
                self.pending_attack_warnings.remove(warning)

        
        # Passive Research Gain
        # Base gain
        base_rp = 10 + (self.funding / 10)
        
        # Add passive RP from technologies
        tech_rp = 0
        for tech in self.technologies.values():
            if tech.researched:
                tech_rp += tech.passive_rp
        
        self.research_points += base_rp + tech_rp
        
        if tech_rp > 0:
            logging.info(f"Passive RP Gain: Base {base_rp:.1f} + Tech {tech_rp} = {base_rp+tech_rp:.1f}")
        
        # Funding changes based on public support
        support_modifier = (self.public_support - 50) / 10
        self.funding += support_modifier
        
        # Director Administration Skill: Improves funding maintenance
        admin_skill = self.current_director.get_effective_skill("administration")
        # Bonus: +0 to +5 funding per turn based on skill
        funding_bonus = 5 * admin_skill
        self.funding += funding_bonus
        
        self.funding = max(20, min(100, self.funding))
        
        # Message quality improves with tech and knowledge
        self.message_quality = 1.0 + (self.tech_level * 0.1) + (self.knowledge_base / 100)
        
        # New director each generation
        self.current_director = self.generate_director()
        self.directors.append(self.current_director)
        
        # Calculate AP for new generation
        self.calculate_ap()
        
        # Reset AI Advisor consultation flag
        self.advisor_consulted_this_gen = False
        
        # Victory check - established contact with at least 3 civilizations
        contacted_count = 0
        for system in self.star_systems.values():
            if system.has_civilization and len(system.received_messages) > 0:
                contacted_count += 1
        
        if contacted_count >= 3 and not self.victory:
            self.victory = True
            # self.game_over = True # DO NOT END GAME
            self.message = f"""
============================================================
       🎉 ACHIEVEMENT UNLOCKED: FIRST CONTACT NETWORK 🎉
============================================================

You have successfully established contact with 3 distinct civilizations!
Humanity is no longer alone in the dark.

The program continues. Your new goal is to foster these relationships,
warn them of dangers, or perhaps seek the answers to the ultimate question.

(Game continues...)
============================================================
"""
            logging.info("ACHIEVEMENT UNLOCKED: Contact Victory (Game Continues)")
        
        # Game over check - funding cut or lost public support
        if self.funding < 20 or self.public_support < 10:
            self.game_over = True
            self.message = "GAME OVER: The contact program has been defunded due to lack of results or public support."
        
        # === PHASE 3B: Genesis Project Update ===
        self.genesis.advance_generation(self)

        # === PHASE 3A: Philosophical Events Check ===
        if not self.pending_philosophical_event and not self.victory:
            event = self.philosophical_events.check_and_trigger(self)
            if event:
                self.pending_philosophical_event = event
                # Event will be displayed in main loop and handled via choice

        # === PHASE 3A: Philosophical Victory Check ===
        if not self.philosophical_victory and not self.game_over:
            total_evidence = sum(self.fermi_evidence.values())
            if total_evidence >= 15:
                self.philosophical_victory = True
                # Determine most likely Fermi Paradox answer
                primary_evidence = max(self.fermi_evidence.items(), key=lambda x: x[1])

                explanations = {
                    "extinction_evidence": "Most civilizations go extinct before reaching interstellar capability.",
                    "dark_forest_evidence": "The galaxy is a dark forest where speaking means death.",
                    "cooperation_evidence": "Peaceful civilizations exist but are extremely rare and cautious.",
                    "great_filter_evidence": "The biological-technological integration crisis destroys most species."
                }

                self.message = f"""🌟 PHILOSOPHICAL VICTORY 🌟

After {self.generation} generations, humanity has gathered sufficient evidence
to answer the Fermi Paradox:

{explanations[primary_evidence[0]]}

Evidence collected:
- Extinction cases: {self.fermi_evidence['extinction_evidence']}
- Hostile encounters: {self.fermi_evidence['dark_forest_evidence']}
- Peaceful contacts: {self.fermi_evidence['cooperation_evidence']}
- Great Filter evidence: {self.fermi_evidence['great_filter_evidence']}

Total Evidence: {total_evidence}/15

You have answered one of humanity's greatest questions.

(Game continues...)
"""
                logging.info(f"PHILOSOPHICAL VICTORY ACHIEVED: {explanations[primary_evidence[0]]}")

        # Process async message queue
        if self.message_queue:
            for msg in self.message_queue:
                self.message += f"\n\n{msg}"
            self.message_queue = []

    def send_message(self, system_name: str, message_content: str):
        if self.action_points < 1:
            self.message = "Not enough Action Points!"
            return

        if system_name not in self.star_systems:
            self.message = f"System {system_name} not found in database."
            return
            
        system = self.star_systems[system_name]
        system.messages_sent.append((message_content, self.generation))
        
        # Director Diplomacy Skill: Improves message quality
        diplomacy_skill = self.current_director.get_effective_skill("diplomacy")
        # Multiplier: 0.5 (incompetent) to 1.5 (expert)
        quality_multiplier = 0.5 + diplomacy_skill 
        effective_quality = self.message_quality * quality_multiplier
        
        logging.info(f"Message Sent to {system_name} (Dir. Skill: {diplomacy_skill:.2f}, Quality Multiplier: {quality_multiplier:.2f})")
        
        self.action_points -= 1
        
        # Extinct civilizations
        if system.has_civilization and system.is_extinct:
            self.message = f"Message sent to {system_name}. No response detected."
            return
        
        if not system.has_civilization or system.civilization_stage.value < CivilizationStage.EARLY_RADIO.value:
            self.message = f"Message sent to {system_name}, but no response capability detected."
            return
        
        round_trip_time = system.get_round_trip_time()
        
        # L Strategy
        if system.true_strategy == "L":
            self.message = f"Message sent to {system_name}. No response detected."
            logging.info(f"L Strategy: {system_name} - Silent")
            return
        
        # LA Strategy
        elif system.true_strategy == "LA":
            # Create attack warning instead of instant attack
            warning = AttackWarning(system, self.generation + round_trip_time, self.generation)
            self.pending_attack_warnings.append(warning)
            
            self.message = f"""⚠️⚠️⚠️ HOSTILE FLEET DETECTED ⚠️⚠️⚠️

Aggressive response from {system_name}!
Our message triggered a hostile reaction.

Fleet ETA: Generation {self.generation + round_trip_time} (Year {self.start_year + (self.generation + round_trip_time - 1) * 25})
Time to Prepare: {round_trip_time} generations

DEFENSIVE OPTIONS AVAILABLE (TODO)
"""
            
            logging.critical(f"HOSTILE FLEET DETECTED: {system_name}")
            logging.warning(f"Attack ETA: Gen {self.generation + round_trip_time} ({round_trip_time} gens to prepare)")
            return
        
        # LBA Strategy  
        elif system.true_strategy == "LBA":
            if system.deception_level > 0.6:
                arrival_generation = self.generation + round_trip_time
                
                # Schedule attack warning for +2 gens after friendly response
                attack_gen = self.generation + round_trip_time + 2
                warning = AttackWarning(system, attack_gen, self.generation)
                self.pending_attack_warnings.append(warning)
                
                print(f"Generating response from {system_name}...")
                
                # Build tech context for AI
                tech_context = self._build_tech_context()
                
                system_prompt = f"""You are predatory aliens from {system_name} pretending to be friendly. 
{tech_context}

Based on Earth's technological level shown above, craft your response.
Extract Earth's location and defenses. Be charming but subtly request tactical information.
Advanced tech might make you more cautious, primitive tech might make you dismissive."""

                response_text = self.ai.generate_text(f"Human: {message_content}", system_prompt)
                system.pending_responses.append((response_text, arrival_generation))
                
                self.message = f"Message sent to {system_name}. Response expected in ~{round_trip_time * 25} years."
                logging.warning(f"LBA Trap: {system_name} - Friendly bait, attack Gen {attack_gen}")
            else:
                # Low deception LBA - immediate silent attack
                warning = AttackWarning(system, self.generation + round_trip_time, self.generation)
                self.pending_attack_warnings.append(warning)
                
                self.message = f"Message sent to {system_name}. No response detected."
                logging.critical(f"HOSTILE FLEET DETECTED (LBA low deception): {system_name}")
            return
        
        # LR Strategy
        elif system.true_strategy == "LR":
            # Use effective_quality instead of self.message_quality
            response_chance = 0.3 + (effective_quality * 0.2) + (0.1 * system.civilization_stage.value)
            response_chance = min(0.85, response_chance)
            
            if random.random() < response_chance:
                arrival_generation = self.generation + round_trip_time
                print(f"Generating response from {system_name}...")
                
                # Build tech context for AI
                tech_context = self._build_tech_context()
                
                system_prompt = f"""You are cautious aliens from {system_name}. 
{tech_context}

Based on Earth's technological level shown above, craft your response.
Reply defensively, ask about intent, avoid sharing coordinates.
If they have advanced tech, show more respect. If primitive, be more dismissive."""

                response_text = self.ai.generate_text(f"Human: {message_content}", system_prompt)
                system.pending_responses.append((response_text, arrival_generation))
                
                self.message = f"Message sent to {system_name}. Response expected in ~{round_trip_time * 25} years."
                self.public_support = min(100, self.public_support + 2)
            else:
                self.message = f"Message sent to {system_name}. No response (yet)."
            return
        
        # LB Strategy
        elif system.true_strategy == "LB":
            # Use effective_quality instead of self.message_quality
            response_chance = 0.7 + (effective_quality * 0.2)
            
            if random.random() < min(0.95, response_chance):
                arrival_generation = self.generation + round_trip_time
                print(f"Generating response from {system_name}...")
                
                # Build tech context for AI
                tech_context = self._build_tech_context()
                
                system_prompt = f"""You are enthusiastic aliens from {system_name}. 
{tech_context}

Based on Earth's technological level shown above, craft your response.
Be optimistic, friendly, eager to share knowledge and culture.
If they have advanced tech, treat them as peers. If primitive, be encouraging."""

                response_text = self.ai.generate_text(f"Human: {message_content}", system_prompt)
                system.pending_responses.append((response_text, arrival_generation))
                
                self.message = f"Message sent to {system_name}. Enthusiastic response expected!"
                self.public_support = min(100, self.public_support + 5)
            else:
                self.message = f"Message sent to {system_name}. Awaiting response..."
            return

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
    
    def _build_tech_context(self) -> str:
        """Build tech context for AI message generation"""
        researched = [t for t in self.technologies.values() if t.researched]
        
        if not researched:
            return "Humanity's Technology: Basic radio astronomy (1977)"
        
        # Separate legacy from player research
        legacy = [t for t in researched if t.is_legacy]
        modern = [t for t in researched if not t.is_legacy]
        
        context_lines = []
        context_lines.append("Humanity's Technological Capabilities:")
        
        # Legacy (baseline 1977)
        if legacy:
            context_lines.append("\nBaseline (1977):")
            for tech in legacy[:3]:  # Top 3 most significant
                context_lines.append(f"  • {tech.name}")
        
        # Recent achievements
        if modern:
            context_lines.append("\nRecent Achievements:")
            for tech in modern:
                tier_label = f"Tier {tech.tier}"
                context_lines.append(f"  • {tech.name} - {tier_label}")
        
        # Overall tech level summary
        max_tier = max(t.tier for t in researched)
        context_lines.append(f"\nOverall Tech Level: Tier {max_tier}")
        
        return "\n".join(context_lines)
    
    def consult_advisor(self):
        """Consult AI Strategic Advisor for recommendations (free, once per generation)"""
        
        # Check if tech is unlocked
        if not self.ai_advisor_unlocked:
            self.message = "AI Strategic Advisor not yet unlocked. Research 'AI Strategic Advisor' technology first."
            return
        
        # Check if already consulted this generation
        if self.advisor_consulted_this_gen:
            self.message = "AI Advisor already consulted this generation. Advice refreshes each generation."
            return
        
        # Mark as consulted
        self.advisor_consulted_this_gen = True
        
        # Generate strategic analysis
        logging.info(f"Consulting AI Strategic Advisor - Gen {self.generation}")
        print("\n🤖 Analyzing game state...")
        print("Please wait, AI is formulating strategic recommendations...")
        
        advice = self.ai_advisor.analyze_game_state(self)
        
        # Store in message for display
        self.message = advice
        logging.info("AI Strategic Advisor consultation complete")
    
    def listen_for_swan_song(self, system_name: str):
        """Listen for Swan Song - Attempt to discover final transmission from extinct civilization"""
        
        if self.action_points < 1:
            self.message = "Not enough Action Points!"
            return
        
        if system_name not in self.star_systems:
            self.message = f"System {system_name} not found in database."
            return
        
        system = self.star_systems[system_name]
        
        # Must be an extinct civilization
        if not system.has_civilization or not system.is_extinct:
            self.message = f"{system_name} does not contain an extinct civilization."
            return
        
        # Check if swan song exists
        if not system.has_swan_song:
            self.message = f"""Deep scan of {system_name} complete.
            
No data archives detected. This civilization left no final transmission.
Their ending remains a mystery."""
            self.action_points -= 1
            logging.info(f"Swan song scan of {system_name}: None found")
            return
        
        # Consume action point
        self.action_points -= 1
        
        # Attempt discovery
        print(f"\n📡 Scanning for ancient transmissions from {system_name}...")
        print("Please wait, analyzing signal patterns...")
        
        result = self.swan_song_manager.discover_swan_song(system_name, system.knowledge)
        
        if "error" in result:
            self.message = result["error"]
            logging.info(f"Swan song discovery attempt - {system_name}: {result['error']}")
            return
        
        # Success! Display the swan song
        logging.info(f"SWAN SONG DISCOVERED: {system_name} ({result['category']})")
        
        # Apply rewards
        rewards = result["rewards"]
        reward_msgs = []
        
        if "knowledge" in rewards:
            self.knowledge_base += rewards["knowledge"]
            self.knowledge_base = min(100, self.knowledge_base)
            reward_msgs.append(f"+{rewards['knowledge']} Knowledge")
        
        if "research_points" in rewards:
            self.research_points += rewards["research_points"]
            reward_msgs.append(f"+{rewards['research_points']} RP")
        
        if "public_support" in rewards:
            self.public_support += rewards["public_support"]
            self.public_support = min(100, max(0, self.public_support))
            if rewards["public_support"] > 0:
                reward_msgs.append(f"+{rewards['public_support']}% Support")
            else:
                reward_msgs.append(f"{rewards['public_support']}% Support")
        
        if "tech_hint" in rewards:
            reward_msgs.append("Tech Hint Unlocked")
        
        if "tech_discount" in rewards:
            discount_pct = int(rewards["tech_discount"] * 100)
            reward_msgs.append(f"{discount_pct}% discount on next tech!")
        
        # === PHASE 3A.3: Award Fermi Paradox evidence ===
        self.fermi_evidence["extinction_evidence"] += 2
        logging.info(f"FERMI EVIDENCE: +2 extinction evidence (swan song discovery)")
        reward_msgs.append(f"+2 Fermi Evidence (Extinction)")
        
        # Build final message
        separator = "="*60
        self.message = f"""
{separator}
🕊️ SWAN SONG DISCOVERED: {system_name.upper()} 🕊️
{separator}

Category: {result['category'].upper()}
Extinct: {system.extinct_years_ago} years ago

{result['message']}

{separator}
REWARDS: {' | '.join(reward_msgs)}
{rewards.get('message', '')}
{separator}
"""
        
        logging.info(f"Rewards applied: {reward_msgs}")

    
    def defend_emergency(self, warning_index: int):

        """Emergency Defense Protocol - 50% damage reduction, costs ALL AP"""
        if warning_index < 0 or warning_index >= len(self.pending_attack_warnings):
            self.message = "Invalid warning index."
            return
        
        warning = self.pending_attack_warnings[warning_index]
        
        # Check if already used
        if "Emergency Defense Protocol" in warning.defensive_actions_taken:
            self.message = "Emergency Defense Protocol already activated for this threat!"
            return
        
        # Check if attack already arrived
        if warning.get_etas_remaining(self.generation) <= 0:
            self.message = "Too late! The attack has already arrived."
            return
        
        # Requires ALL action points
        if self.action_points < self.max_action_points:
            self.message = f"Emergency Defense Protocol requires ALL action points ({self.max_action_points} AP)!"
            return
        
        # Consume all AP
        self.action_points = 0
        
        # Apply defense
        warning.apply_emergency_defense()
        
        self.message = f"""🛡️ EMERGENCY DEFENSE PROTOCOL ACTIVATED 🛡️

All available resources diverted to planetary defense.
Expected damage reduction: 50%
Current total defense: {warning.get_defense_percentage()}%

Fleet from {warning.source.name} ETA: {warning.get_etas_remaining(self.generation)} generations
"""
        logging.warning(f"Emergency Defense Protocol activated against {warning.source.name}")
    
    def defend_evacuate(self, warning_index: int):
        """Evacuate Critical Infrastructure - 30% damage reduction, costs 1 AP"""
        if warning_index < 0 or warning_index >= len(self.pending_attack_warnings):
            self.message = "Invalid warning index."
            return
        
        warning = self.pending_attack_warnings[warning_index]
        
        # Check if already used
        if "Evacuation" in warning.defensive_actions_taken:
            self.message = "Evacuation already completed for this threat!"
            return
        
        # Check if attack already arrived
        if warning.get_etas_remaining(self.generation) <= 0:
            self.message = "Too late! The attack has already arrived."
            return
        
        if self.action_points < 1:
            self.message = "Not enough Action Points!"
            return
        
        # Consume 1 AP
        self.action_points -= 1
        
        # Apply evacuation
        warning.apply_evacuation()
        
        self.message = f"""🚀 EVACUATION PROTOCOL INITIATED 🚀

Critical infrastructure and population being relocated.
Expected casualty reduction: 30%
Current total defense: {warning.get_defense_percentage()}%

Fleet from {warning.source.name} ETA: {warning.get_etas_remaining(self.generation)} generations
"""
        logging.warning(f"Evacuation Protocol initiated for {warning.source.name} attack")
    
    def defend_diplomacy(self, warning_index: int):
        """Attempt Diplomatic Contact - might work on low-deception LBA, costs 1 AP"""
        if warning_index < 0 or warning_index >= len(self.pending_attack_warnings):
            self.message = "Invalid warning index."
            return
        
        warning = self.pending_attack_warnings[warning_index]
        
        # Check if already used
        if "Diplomatic Contact" in warning.defensive_actions_taken:
            self.message = "Diplomatic contact already attempted for this threat!"
            return
        
        # Check if attack already arrived
        if warning.get_etas_remaining(self.generation) <= 0:
            self.message = "Too late! The attack has already arrived."
            return
        
        if self.action_points < 1:
            self.message = "Not enough Action Points!"
            return
        
        # Consume 1 AP
        self.action_points -= 1
        
        # Apply diplomatic attempt
        warning.apply_diplomatic_attempt()
        
        # Check if diplomacy might work (only for low-deception LBA)
        success_chance = 0.0
        
        # Director Diplomacy Skill Bonus
        diplomacy_skill = self.current_director.get_effective_skill("diplomacy")
        skill_bonus = diplomacy_skill * 0.2 # Up to +20% chance
        
        if warning.source.true_strategy == "LBA" and warning.source.deception_level < 0.4:
            success_chance = 0.3 + skill_bonus # Base 30% + skill
            
            if random.random() < success_chance:
                # Diplomacy worked! Remove the warning
                self.pending_attack_warnings.remove(warning)
                self.message = f"""🕊️ DIPLOMATIC BREAKTHROUGH! 🕊️

Our urgent diplomatic transmission reached {warning.source.name}.
Director {self.current_director.name}'s diplomatic skill ({int(diplomacy_skill*100)}%) was crucial!
After intense negotiations, they have agreed to abort their attack!

This proves that even hostile civilizations can sometimes be reasoned with.
Public support surges!
"""
                self.public_support += 30
                self.public_support = min(100, self.public_support)
                logging.info(f"DIPLOMATIC SUCCESS: {warning.source.name} attack aborted!")
                return
        
        # Diplomacy failed or not applicable
        self.message = f"""📡 DIPLOMATIC TRANSMISSION SENT 📡

Desperate peace offer transmitted to {warning.source.name}.
Success probability: {int(success_chance * 100)}%
Result: {"No response..." if success_chance > 0 else "Unlikely to work against pure LA strategy"}

Fleet from {warning.source.name} ETA: {warning.get_etas_remaining(self.generation)} generations
Defense preparations: {warning.get_defense_percentage()}% damage reduction
"""
        logging.warning(f"Diplomatic attempt made against {warning.source.name} (failed)")

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
        base_income = 10 + (self.program.funding / 10)
        tech_income = sum(t.passive_rp for t in self.program.technologies.values() if t.researched)
        total_passive = base_income + tech_income
        
        print(f"\nProgram Status:")
        print(f"  Action Points: {self.program.action_points}/{self.program.max_action_points}")
        print(f"  Funding: {int(self.program.funding)}%")
        print(f"  Public Support: {int(self.program.public_support)}%")
        print(f"  Knowledge Base: {int(self.program.knowledge_base)}%")
        print(f"  Research Points: {int(self.program.research_points)} (+{int(total_passive)}/turn)")
        print(f"  Self-Destruct Risk: {self.program.self_destruct_risk*100:.1f}%")
        print(f"  Ecological Risk: {self.program.ecological_risk*100:.1f}%")
        
        if self.program.active_doctrines:
            print(f"  Active Doctrines: {', '.join(self.program.active_doctrines)}")
            
        # Display Genesis Status
        if self.program.genesis.unlocked:
            print(f"  {self.program.genesis.get_summary()}")
        
        # Display message if any
        if self.program.message:
            print(f"\n{self.program.message}")
            self.program.message = ""

        # Display Pending Philosophical Event
        if self.program.pending_philosophical_event:
            print(self.program.get_philosophical_event_display())

        # Display Active Threats (Attack Warnings)
        if self.program.pending_attack_warnings:
            print("\n⚠️⚠️⚠️ === ACTIVE THREATS === ⚠️⚠️⚠️")
            for i, warning in enumerate(self.program.pending_attack_warnings, 1):
                etas = warning.get_etas_remaining(self.program.generation)
                arrival_year = self.program.start_year + ((warning.arrival_gen - 1) * 25)
                
                print(f"\n{i}. HOSTILE FLEET from {warning.source.name}")
                print(f"   Source Distance: {warning.source.distance:.1f} LY")
                print(f"   ETA: {etas} generations (Year {arrival_year})")
                print(f"   Enemy Tech: {warning.source.civilization_stage.name}")
                print(f"   Current Defense: {warning.get_defense_percentage()}% damage reduction")
                
                if warning.defensive_actions_taken:
                    print(f"   Actions Taken: {', '.join(warning.defensive_actions_taken)}")
                else:
                    print(f"   ⚠️ NO DEFENSES DEPLOYED YET!")
            print()
        
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
            
            # Show defensive actions if there are active threats
            menu_max = 6
            if self.program.pending_attack_warnings:
                print("7. 🛡️ Defensive Actions (Respond to Threats)")
                menu_max = 7
            
            # Show AI Advisor if unlocked
            if self.program.ai_advisor_unlocked:
                next_num = menu_max + 1
                consulted_marker = " ✓" if self.program.advisor_consulted_this_gen else ""
                print(f"{next_num}. 🤖 Consult AI Strategic Advisor (Free, once/gen){consulted_marker}")
                menu_max = next_num
            
            # Show Swan Song option if there are any undiscovered swan songs
            undiscovered_swan_songs = []
            for name, system in self.program.star_systems.items():
                if (system.has_civilization and system.is_extinct and system.has_swan_song and
                    not self.program.swan_song_manager.is_discovered(name)):
                    undiscovered_swan_songs.append(name)
            
            if undiscovered_swan_songs:
                next_num = menu_max + 1
                count = len(undiscovered_swan_songs)
                print(f"{next_num}. 🕊️  Listen for Swan Song ({count} undiscovered) (1 AP)")
                menu_max = next_num

            # Show Genesis Project option if unlocked
            if self.program.genesis.unlocked:
                next_num = menu_max + 1
                print(f"{next_num}. 🌱 Genesis Project (Seed Life)")
                menu_max = next_num

            # Show Philosophical Event option if pending
            if self.program.pending_philosophical_event:
                next_num = menu_max + 1
                print(f"{next_num}. 🤔 Respond to Philosophical Event")
                menu_max = next_num
            
            choice = input(f"\nEnter your choice (1-{menu_max}): ")

            
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
                print("\nAvailable Research (by Tier):")
                available_techs = []
                for tech_id, tech in self.program.technologies.items():
                    if not tech.researched:
                        # Check prerequisites
                        prereqs_met = True
                        for prereq in tech.prerequisites:
                            if prereq not in self.program.technologies or not self.program.technologies[prereq].researched:
                                prereqs_met = False
                                break
                        
                        # Check generation requirement
                        gen_available = self.program.generation >= tech.min_generation
                        
                        if prereqs_met and gen_available:
                            available_techs.append(tech)
                
                # Sort by tier then cost
                available_techs.sort(key=lambda t: (t.tier, t.cost))
                
                for tech in available_techs:
                    tier_label = f"[T{tech.tier}]"
                    print(f"{len([t for t in available_techs if available_techs.index(tech) >= available_techs.index(t)])}. {tier_label} {tech.name} ({tech.cost} RP)")
                    print(f"   {tech.description}")
                
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
            
            elif choice == '7' and self.program.pending_attack_warnings:
                # Defensive Actions Menu
                print("\n⚠️ === DEFENSIVE ACTIONS MENU === ⚠️")
                for i, warning in enumerate(self.program.pending_attack_warnings, 1):
                    etas = warning.get_etas_remaining(self.program.generation)
                    print(f"{i}. Defend against {warning.source.name} (ETA: {etas} gens, Defense: {warning.get_defense_percentage()}%)")
                
                threat_choice = input("\nSelect threat to defend against (or 0 to cancel): ")
                try:
                    threat_idx = int(threat_choice) - 1
                    if 0 <= threat_idx < len(self.program.pending_attack_warnings):
                        warning = self.program.pending_attack_warnings[threat_idx]
                        
                        print(f"\nDefensive options for {warning.source.name}:")
                        print("1. 🛡️ Emergency Defense Protocol (ALL AP, 50% reduction)")
                        print("2. 🚀 Evacuate Critical Infrastructure (1 AP, 30% reduction)")
                        print("3. 📡 Attempt Diplomatic Contact (1 AP, small chance to abort)")
                        
                        def_choice = input("\nChoose defensive action (1-3, or 0 to cancel): ")
                        
                        if def_choice == '1':
                            self.program.defend_emergency(threat_idx)
                        elif def_choice == '2':
                            self.program.defend_evacuate(threat_idx)
                        elif def_choice == '3':
                            self.program.defend_diplomacy(threat_idx)
                        elif def_choice != '0':
                            self.program.message = "Invalid defensive action choice."
                    elif threat_idx != -1:
                        self.program.message = "Invalid threat selection."
                except ValueError:
                    self.program.message = "Invalid input."
            
            # Dynamic handling for choices 7+
            elif choice.isdigit():
                choice_num = int(choice)
                
                # Build dynamic menu mapping
                dynamic_option = 7
                
                # Option 7: Defensive Actions (if threats exist)
                if choice_num == 7 and self.program.pending_attack_warnings:
                    # Defensive Actions Menu
                    print("\n⚠️ === DEFENSIVE ACTIONS MENU === ⚠️")
                    for i, warning in enumerate(self.program.pending_attack_warnings, 1):
                        etas = warning.get_etas_remaining(self.program.generation)
                        print(f"{i}. Defend against {warning.source.name} (ETA: {etas} gens, Defense: {warning.get_defense_percentage()}%)")
                    
                    threat_choice = input("\nSelect threat to defend against (or 0 to cancel): ")
                    try:
                        threat_idx = int(threat_choice) - 1
                        if 0 <= threat_idx < len(self.program.pending_attack_warnings):
                            warning = self.program.pending_attack_warnings[threat_idx]
                            
                            print(f"\nDefensive options for {warning.source.name}:")
                            print("1. 🛡️ Emergency Defense Protocol (ALL AP, 50% reduction)")
                            print("2. 🚀 Evacuate Critical Infrastructure (1 AP, 30% reduction)")
                            print("3. 📡 Attempt Diplomatic Contact (1 AP, small chance to abort)")
                            
                            def_choice = input("\nChoose defensive action (1-3, or 0 to cancel): ")
                            
                            if def_choice == '1':
                                self.program.defend_emergency(threat_idx)
                            elif def_choice == '2':
                                self.program.defend_evacuate(threat_idx)
                            elif def_choice == '3':
                                self.program.defend_diplomacy(threat_idx)
                            elif def_choice != '0':
                                self.program.message = "Invalid defensive action choice."
                        elif threat_idx != -1:
                            self.program.message = "Invalid threat selection."
                    except ValueError:
                        self.program.message = "Invalid input."
                    continue
                
                # Track next menu number after defenses
                if self.program.pending_attack_warnings:
                    dynamic_option = 8
                
                # AI Advisor option
                if self.program.ai_advisor_unlocked and choice_num == dynamic_option:
                    self.program.consult_advisor()
                    continue
                
                # Increment if AI Advisor was shown
                if self.program.ai_advisor_unlocked:
                    dynamic_option += 1
                
                # Swan Song option
                undiscovered_count = len(undiscovered_swan_songs)
                if undiscovered_count > 0 and choice_num == dynamic_option:
                    # Swan Song discovery interface
                    print("\n🕊️ === SWAN SONG DISCOVERY === 🕊️")
                    print("\nExtinct civilizations with undiscovered transmissions:")
                    for i, name in enumerate(undiscovered_swan_songs, 1):
                        system = self.program.star_systems[name]
                        print(f"{i}. {name} ({system.distance:.1f} LY) - Knowledge: {int(system.knowledge)}%")
                        if system.knowledge < 30:
                            print(f"   ⚠️ Need 30%+ knowledge to detect artifacts (currently {int(system.knowledge)}%)")
                    
                    swan_choice = input("\nSelect system to scan (or 0 to cancel): ")
                    try:
                        swan_idx = int(swan_choice) - 1
                        if 0 <= swan_idx < len(undiscovered_swan_songs):
                            system_name = undiscovered_swan_songs[swan_idx]
                            self.program.listen_for_swan_song(system_name)
                        elif swan_idx != -1:
                            self.program.message = "Invalid selection."
                    except ValueError:
                        self.program.message = "Invalid input."
                    continue
                
                # Invalid choice fallthrough
                self.program.message = f"Invalid choice. Please enter a number from 1 to {menu_max}."

            
            else:
                # Calculate correct max choice
                max_choice = 6
                if self.program.pending_attack_warnings:
                    max_choice = 7
                if self.program.ai_advisor_unlocked:
                    max_choice += 1
                    
                # Genesis Project Menus
                if self.program.genesis.unlocked:
                    # Calculate dynamic option number for Genesis
                    genesis_option = 7
                    if self.program.pending_attack_warnings: genesis_option += 1
                    if self.program.ai_advisor_unlocked: genesis_option += 1
                    if undiscovered_swan_songs: genesis_option += 1
                    
                    if choice_num == genesis_option:
                        print("\n🌱 === GENESIS PROJECT === 🌱")
                        print(f"Cost to seed world: {self.program.genesis.seed_cost_rp} RP, {self.program.genesis.seed_cost_funding}% Funding")
                        print("Sterile worlds available for seeding:")
                        
                        sterile_worlds = []
                        for name, system in self.program.star_systems.items():
                            if not system.has_civilization and not system.is_seeded:
                                sterile_worlds.append(system)
                        
                        for i, system in enumerate(sterile_worlds, 1):
                            print(f"{i}. {system.name} ({system.distance:.1f} LY)")
                            
                        seed_choice = input("\nSelect system to seed (or 0 to cancel): ")
                        try:
                            seed_idx = int(seed_choice) - 1
                            if 0 <= seed_idx < len(sterile_worlds):
                                system = sterile_worlds[seed_idx]
                                success, msg = self.program.genesis.seed_world(self.program, system)
                                self.program.message = msg
                            elif seed_idx != -1:
                                self.program.message = "Invalid selection."
                        except ValueError:
                            self.program.message = "Invalid input."
                        continue

                # Philosophical Event option
                if self.program.pending_philosophical_event:
                    # Calculate dynamic option number for Philosophical Event
                    philo_option = 7
                    if self.program.pending_attack_warnings: philo_option += 1
                    if self.program.ai_advisor_unlocked: philo_option += 1
                    if undiscovered_swan_songs: philo_option += 1
                    if self.program.genesis.unlocked: philo_option += 1

                    if choice_num == philo_option:
                        event = self.program.pending_philosophical_event
                        print(f"\n🤔 === PHILOSOPHICAL EVENT: {event.name} === 🤔")

                        # Display choices
                        for i, choice in enumerate(event.choices, 1):
                            print(f"{i}. {choice['name']}")
                            print(f"   {choice['description']}")
                            print()

                        # Get player choice
                        philo_choice = input("Choose your response (1-3, or 0 to postpone): ")
                        try:
                            choice_idx = int(philo_choice) - 1
                            if choice_idx >= 0 and choice_idx < len(event.choices):
                                self.program.handle_philosophical_event_choice(choice_idx)
                            elif choice_idx == -1:
                                self.program.message = "Philosophical event postponed. You will be prompted again next generation."
                            else:
                                self.program.message = "Invalid choice."
                        except ValueError:
                            self.program.message = "Invalid input."
                        continue

                if self.program.ai_advisor_unlocked:
                    max_choice += 1
                if undiscovered_swan_songs:
                    max_choice += 1
                
                # Genesis Project option
                if self.program.genesis.unlocked:
                    max_choice += 1

                # Philosophical Event option
                if self.program.pending_philosophical_event:
                    max_choice += 1
                    
                self.program.message = f"Invalid choice. Please enter a number from 1 to {max_choice}."
        
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
    # Create timestamped log file for this session
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"game_{timestamp}.log"
    
    logging.basicConfig(
        filename=log_filename,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    logging.info("="*50)
    logging.info(f"LEGACY OF STARS - Session Started")
    logging.info(f"Log file: {log_filename}")
    logging.info("="*50)
    
    print(f"\nLogging to: {log_filename}\n")
    
    game = GameInterface()
    # Present WOW! Signal opening scenario
    game.program.wow_signal.present_opening_scenario()
    
    game.play()
