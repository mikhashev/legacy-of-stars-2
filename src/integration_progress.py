"""
Integration Progress System for Legacy of Stars

Tracks humanity's progress merging biological and technological systems.
Based on Section 11 philosophical framework - the Dual DNA problem.

Low integration = higher Great Filter risk (biological instincts cause problems)
High integration = reduced risk (successfully merged biology and technology)
"""

import logging
from typing import Dict, List, Tuple


class IntegrationProgress:
    """Tracks biological-technological integration progress"""
    
    def __init__(self):
        self.integration_level = 0.0  # 0.0 = pure biological, 1.0 = full integration
        self.integration_events = []  # History of integration milestones
        self.crisis_threshold = 0.3   # Below this, penalties apply
        self.high_integration_threshold = 0.7  # Above this, bonuses apply
        
        logging.info("Integration Progress system initialized")
    
    def add_integration(self, amount: float, source: str):
        """
        Add integration progress from technology research
        
        Args:
            amount: Integration amount (0.0-1.0 scale)
            source: Technology or event that caused integration
        """
        old_level = self.integration_level
        self.integration_level = min(1.0, self.integration_level + amount)
        
        # Record milestone
        self.integration_events.append({
            'source': source,
            'amount': amount,
            'new_level': self.integration_level
        })
        
        logging.info(
            f"INTEGRATION: {source} +{amount:.1%} "
            f"(Total: {old_level:.1%} → {self.integration_level:.1%})"
        )
        
        # Log threshold crossing
        if old_level < self.crisis_threshold <= self.integration_level:
            logging.info("MILESTONE: Crossed crisis threshold (0.3) - penalties removed!")
        elif old_level < self.high_integration_threshold <= self.integration_level:
            logging.info("MILESTONE: High integration achieved (0.7+) - bonuses active!")
    
    def to_dict(self) -> Dict:
        return {"integration_level": self.integration_level, "integration_events": list(self.integration_events)}

    @classmethod
    def from_dict(cls, data: Dict) -> "IntegrationProgress":
        progress = cls()
        progress.integration_level = float(data.get("integration_level", 0.0))
        progress.integration_events = list(data.get("integration_events", []))
        return progress

    def get_filter_risk_modifier(self, current_generation: int = 999) -> float:
        """
        Return self-destruct risk multiplier based on integration
        
        Args:
            current_generation: Current game generation (for grace period)
            
        Returns:
            float: Multiplier for self-destruct risk
                   - Grace Period (Gen <= 30): 1.0 (no penalty)
                   - Low integration (<0.3): 1.2 (20% increase)
                   - Medium integration (0.3-0.7): 1.0 (no change)
                   - High integration (>0.7): 0.7 (30% reduction)
        """
        # Grace period for first 30 generations
        if current_generation <= 30:
            return 1.0
            
        if self.integration_level < self.crisis_threshold:
            # Low integration - biological instincts cause chaos
            return 1.2
        elif self.integration_level >= self.high_integration_threshold:
            # High integration - successfully merged
            return 0.7
        else:
            # Medium integration - neutral
            return 1.0
    
    def get_support_penalty(self, current_generation: int = 999) -> float:
        """
        Return public support penalty per generation for low integration
        
        Args:
            current_generation: Current game generation (for grace period)
            
        Returns:
            float: Support penalty (-10% per gen if <0.3 integration)
        """
        # Grace period
        if current_generation <= 30:
            return 0.0
            
        if self.integration_level < self.crisis_threshold:
            return -10.0
        return 0.0
    
    def get_research_efficiency(self, current_generation: int = 999) -> float:
        """
        Return research efficiency modifier based on integration
        
        Args:
            current_generation: Current game generation (for grace period)
            
        Returns:
            float: Multiplier for research points
                   - Low integration (<0.3): 0.85 (15% penalty)
                   - Otherwise: 1.0 (no change)
        """
        # Grace period
        if current_generation <= 30:
            return 1.0
            
        if self.integration_level < self.crisis_threshold:
            # Biological limitations hinder understanding advanced tech
            return 0.85
        return 1.0
    
    def can_research_tier5(self) -> bool:
        """
        Check if civilization can research Tier 5 technologies
        
        Returns:
            bool: True if integration >= 0.4
        """
        return self.integration_level >= 0.4
    
    def get_integration_status(self, current_generation: int = 999) -> Dict:
        """
        Return current integration statistics
        
        Args:
            current_generation: Current game generation
            
        Returns:
            dict: Complete integration status
        """
        status = ""
        description = ""
        
        if self.integration_level < self.crisis_threshold:
            status = "CRISIS"
            description = "Biological-technological mismatch causing instability"
            if current_generation <= 30:
                status += " (GRACE PERIOD)"
        elif self.integration_level < self.high_integration_threshold:
            status = "TRANSITIONING"
            description = "Making progress toward full integration"
        else:
            status = "INTEGRATED"
            description = "Successfully merged biological and technological systems"
        
        return {
            'level': self.integration_level,
            'status': status,
            'description': description,
            'filter_risk_modifier': self.get_filter_risk_modifier(current_generation),
            'support_penalty': self.get_support_penalty(current_generation),
            'research_efficiency': self.get_research_efficiency(current_generation),
            'can_research_tier5': self.can_research_tier5(),
            'milestone_count': len(self.integration_events),
            'events': self.integration_events,
            'grace_period_active': current_generation <= 30
        }
    
    def get_display_message(self, current_generation: int = 999) -> str:
        """
        Get user-facing status message
        
        Args:
            current_generation: Current game generation
            
        Returns:
            str: Formatted status message for game UI
        """
        status = self.get_integration_status(current_generation)
        
        msg = f"\n🧬 Integration Progress: {status['level']:.1%} ({status['status']})"
        
        if status['level'] < self.crisis_threshold:
            if current_generation <= 30:
                 msg += "\n🛡️ GRACE PERIOD ACTIVE (Gen 1-30): Penalties suppressed."
            else:
                msg += "\n⚠️ WARNING: Low integration causing:"
                msg += f"\n  • +20% self-destruct risk"
                msg += f"\n  • -10% public support per generation"
                msg += f"\n  • -15% research efficiency"
                msg += f"\n  • Cannot research Tier 5 technologies"
        elif status['level'] >= self.high_integration_threshold:
            msg += "\n✨ High integration benefits:"
            msg += f"\n  • -30% self-destruct risk"
        
        return msg
