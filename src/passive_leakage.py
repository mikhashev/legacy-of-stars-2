"""
Passive Signal Leakage System for Legacy of Stars
Implements realistic electromagnetic signal detection by hostile civilizations

Based on scientific research:
- Breakthrough Starshot: Laser sails at 15-20% light speed (0.175c average)
- Project Daedalus: Fusion propulsion at 12% light speed (0.12c)
- Dark Forest Theory: Information warfare is cheapest and most effective

Model (v1.1): Earth's transmissions have been expanding as a sphere since the first
high-power broadcasts of the 1930s, one light-year per year. Technology no longer
changes how far the front has travelled - it only changes how loud we are inside it.
"""

import math
import random
import logging
from typing import Dict

# The leakage front started with high-power broadcasting in the 1930s and expands at c.
LEAKAGE_START_YEAR = 1935

# Interstellar speeds (fraction of c) shared with the Genesis ark program.
LASER_SAIL_SPEED_C = 0.175  # Breakthrough Starshot average
FUSION_SPEED_C = 0.12       # Project Daedalus

# Reference distance for the inverse-square term: at 10 LY a listener hears us at full strength.
REFERENCE_LY = 10.0

# Per-generation detection chance at the reference distance, full loudness, no mitigation.
# 0.015 would reproduce the pre-v1.1 rate (about one passive detection per 90 games, i.e. a
# mechanic nobody ever met); the owner chose ten times that: roughly one detection per five
# games in the 30-run auto-playtest, mostly from close neighbours.
BASE_DETECTION = 0.15

# How loud Earth is: analogue television and radar peak until 2000, then digital
# compression and directional links take the leakage down to a floor by 2075.
LOUDNESS_PEAK_YEAR = 2000.0
LOUDNESS_FLOOR_YEAR = 2075.0
LOUDNESS_FLOOR = 0.4


class PassiveLeakageSystem:
    """Manages Earth's passive electromagnetic signal leakage and hostile detection"""

    def __init__(self):
        # Attack type probabilities (based on cost/effectiveness)
        self.attack_type_probabilities = {
            "information": 0.70,  # Cheapest, delivered by signal
            "laser_sail": 0.25,   # Gram-scale probes, 0.175c
            "fusion": 0.05        # Expensive, heavy payload, 0.12c
        }

        # Travel speeds (fraction of light speed)
        self.laser_sail_speed = LASER_SAIL_SPEED_C
        self.fusion_speed = FUSION_SPEED_C

        # Base detection chance per generation, at the reference distance and full loudness
        self.base_detection_chance = BASE_DETECTION

    def leakage_front(self, year: float) -> float:
        """
        Radius of Earth's expanding sphere of leaked transmissions.

        Args:
            year: Current in-game year

        Returns:
            Distance the front has travelled, in light-years (0.0 before 1935)
        """
        return max(0.0, float(year) - LEAKAGE_START_YEAR)

    def loudness(self, year: float) -> float:
        """
        How detectable Earth's leakage is, relative to the analogue-broadcast peak.

        1.0 up to the year 2000, then a linear decline to LOUDNESS_FLOOR by 2075
        (digital compression, directional links, cable and fibre) and flat afterwards.
        """
        year = float(year)
        if year <= LOUDNESS_PEAK_YEAR:
            return 1.0
        if year >= LOUDNESS_FLOOR_YEAR:
            return LOUDNESS_FLOOR
        fraction = (year - LOUDNESS_PEAK_YEAR) / (LOUDNESS_FLOOR_YEAR - LOUDNESS_PEAK_YEAR)
        return 1.0 - fraction * (1.0 - LOUDNESS_FLOOR)

    def calculate_detection_probability(self, distance: float, year: float,
                                        leakage_multiplier: float) -> float:
        """
        Chance that one listening civilization notices Earth this generation.

            p = BASE_DETECTION * loudness(year) * leakage_multiplier * min(1, (10 / d)^2)

        Args:
            distance: Distance to the system in light-years
            year: Current in-game year
            leakage_multiplier: Leakage mitigation multiplier (0.0 to 1.0)

        Returns:
            Probability 0.0-1.0
        """
        if distance <= 0:
            falloff = 1.0
        else:
            falloff = min(1.0, (REFERENCE_LY / float(distance)) ** 2)
        return self.base_detection_chance * self.loudness(year) * leakage_multiplier * falloff

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

        front = self.leakage_front(year)
        for system_name, system in hostile_systems:
            # Skip if already detected Earth
            if hasattr(system, 'has_detected_earth') and system.has_detected_earth:
                continue

            # Our leakage has not reached them yet
            if system.distance > front:
                continue

            detection_chance = self.calculate_detection_probability(system.distance, year, leakage_mult)

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
        - information: Malicious knowledge (travels at light speed, 70%)
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
            Travel time in generations (25 years each), rounded up
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
        travel_gens = math.ceil(travel_years / 25)
        return max(1, travel_gens)  # At least 1 generation
