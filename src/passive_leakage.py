"""
Passive Signal Leakage System for Legacy of Stars
Implements realistic electromagnetic signal detection by hostile civilizations

Based on scientific research:
- Breakthrough Starshot: Laser sails at 15-20% light speed (0.175c average)
- Project Daedalus: Fusion propulsion at 12% light speed (0.12c)
- Dark Forest Theory: Information warfare is cheapest and most effective
"""

import random
import logging
from typing import List, Tuple, Dict


class PassiveLeakageSystem:
    """Manages Earth's passive electromagnetic signal leakage and hostile detection"""
    
    def __init__(self):
        # Attack type probabilities (based on cost/effectiveness)
        self.attack_type_probabilities = {
            "information": 0.70,  # Cheapest, instant delivery
            "laser_sail": 0.25,   # Gram-scale probes, 0.175c
            "fusion": 0.05        # Expensive, heavy payload, 0.12c
        }
        
        # Travel speeds (fraction of light speed)
        self.laser_sail_speed = 0.175  # Breakthrough Starshot average
        self.fusion_speed = 0.12       # Project Daedalus
        
        # Base detection chance per generation
        self.base_detection_chance = 0.005  # 0.5% per generation
        
    def calculate_broadcast_radius(self, tech_level: int, researched_techs: Dict) -> float:
        """
        Calculate Earth's electromagnetic broadcast radius based on tech tier
        
        Args:
            tech_level: Current tech level (1-5+)
            researched_techs: Dictionary of researched Technology objects
            
        Returns:
            Broadcast radius in light-years
        """
        # Find highest tier researched
        max_tier = 0
        for tech in researched_techs.values():
            if tech.researched and tech.tier > max_tier:
                max_tier = tech.tier
        
        # Broadcast radius increases with technology development
        if max_tier <= 1:
            return 25.0  # Early radio era
        elif max_tier == 2:
            return 50.0  # Distributed computing, SETI arrays
        elif max_tier == 3:
            return 75.0  # Quantum, orbital infrastructure
        else:  # Tier 4+
            return 100.0  # Interstellar capabilities
    
    def get_leakage_multiplier(self, researched_techs: Dict) -> float:
        """
        Calculate signal leakage multiplier based on mitigation technologies
        
        Multiplier = 1.0 means full leakage
        Multiplier = 0.0 means zero leakage (complete stealth)
        
        Multiple mitigation techs stack multiplicatively
        
        Args:
            researched_techs: Dictionary of researched Technology objects
            
        Returns:
            Leakage multiplier (0.0 to 1.0)
        """
        multiplier = 1.0
        
        # Check for each mitigation technology
        if "directional_transmission" in researched_techs and researched_techs["directional_transmission"].researched:
            multiplier *= 0.7  # 30% reduction
            
        if "radio_silence_protocol" in researched_techs and researched_techs["radio_silence_protocol"].researched:
            multiplier *= 0.5  # 50% reduction
            
        if "civilization_cloaking" in researched_techs and researched_techs["civilization_cloaking"].researched:
            multiplier *= 0.2  # 80% reduction
            
        # Dark Forest Protocol gives complete silence (0.0)
        if "dark_forest_protocol" in researched_techs and researched_techs["dark_forest_protocol"].researched:
            multiplier = 0.0
        
        return multiplier
    
    def check_passive_detection(self, generation: int, broadcast_radius: float, 
                                leakage_mult: float, hostile_systems: List[Tuple[str, any]]) -> List[Tuple[str, any]]:
        """
        Check if any LA/LBA civilizations detect Earth this generation
        
        Args:
            generation: Current generation number
            broadcast_radius: Earth's current broadcast radius in LY
            leakage_mult: Signal leakage multiplier (0.0 to 1.0)
            hostile_systems: List of (name, StarSystem) tuples for LA/LBA within range
            
        Returns:
            List of (name, StarSystem) tuples for systems that detected Earth
        """
        detected_by = []
        
        # If complete silence, no detection possible
        if leakage_mult == 0.0:
            return detected_by
        
        for system_name, system in hostile_systems:
            # Skip if already detected Earth
            if hasattr(system, 'has_detected_earth') and system.has_detected_earth:
                continue
            
            # Calculate detection probability
            detection_chance = self.base_detection_chance * leakage_mult
            
            # Roll for detection
            if random.random() < detection_chance:
                detected_by.append((system_name, system))
                system.has_detected_earth = True  # Mark as detected to prevent duplicates
                logging.critical(f"PASSIVE DETECTION: {system_name} detected Earth (chance: {detection_chance*100:.2f}%)")
        
        return detected_by
    
    def determine_attack_type(self, detecting_system: any, distance: float) -> str:
        """
        Determine attack type based on probabilities and distance
        
        Attack types:
        - information: Malicious knowledge (instant, 70%)
        - laser_sail: Gram-scale probe at 0.175c (25%)
        - fusion: Heavy strike at 0.12c (5%)
        
        Args:
            detecting_system: StarSystem object that detected Earth
            distance: Distance to system in light-years
            
        Returns:
            Attack type string: "information", "laser_sail", or "fusion"
        """
        roll = random.random()
        
        if roll < self.attack_type_probabilities["information"]:
            return "information"
        elif roll < (self.attack_type_probabilities["information"] + 
                     self.attack_type_probabilities["laser_sail"]):
            return "laser_sail"
        else:
            return "fusion"
    
    def calculate_travel_time(self, distance: float, attack_type: str) -> int:
        """
        Calculate travel time in generations for physical attacks
        
        Args:
            distance: Distance in light-years
            attack_type: "laser_sail" or "fusion"
            
        Returns:
            Travel time in generations (25 years each)
        """
        if attack_type == "laser_sail":
            # Breakthrough Starshot: 0.175c average
            travel_years = distance / self.laser_sail_speed
        elif attack_type == "fusion":
            # Project Daedalus: 0.12c
            travel_years = distance / self.fusion_speed
        else:
            raise ValueError(f"Unknown attack type for travel calculation: {attack_type}")
        
        # Convert years to generations (25 years each)
        travel_gens = int(travel_years / 25)
        return max(1, travel_gens)  # At least 1 generation
