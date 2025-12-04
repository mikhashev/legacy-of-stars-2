"""
Attack Early Warning System for Legacy of Stars
Provides realistic light-speed based defense against hostile fleets
"""

import logging

class AttackWarning:
    """Tracks an incoming hostile fleet attack"""
    
    def __init__(self, source_system, arrival_generation, current_generation):
        self.source = source_system
        self.arrival_gen = arrival_generation
        self.detected_gen = current_generation
        self.defensive_actions_taken = []
        self.defense_multiplier = 1.0  # 1.0 = no reduction, 0.5 = 50% reduction
        
    def get_etas_remaining(self, current_gen):
        """Get generations until arrival"""
        return max(0, self.arrival_gen - current_gen)
    
    def get_defense_percentage(self):
        """Get damage reduction as percentage"""
        return int((1 - self.defense_multiplier) * 100)
    
    def apply_emergency_defense(self):
        """Emergency Defense Protocol - 50% reduction"""
        self.defense_multiplier *= 0.5
        self.defensive_actions_taken.append("Emergency Defense Protocol")
        
    def apply_evacuation(self):
        """Evacuate Critical Infrastructure - 30% reduction"""
        self.defense_multiplier *= 0.7
        self.defensive_actions_taken.append("Evacuation")
        
    def apply_diplomatic_attempt(self):
        """Log diplomatic attempt"""
        self.defensive_actions_taken.append("Diplomatic Contact")
