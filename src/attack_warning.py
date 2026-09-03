"""
Attack Early Warning System for Legacy of Stars
Provides realistic light-speed based defense against hostile fleets
"""

import logging
from typing import Any, Dict, Optional

# Player-facing names for the kinds of attack the engine can schedule.
ATTACK_TYPE_LABELS = {
    "fleet": "hostile fleet",
    "laser_sail_probe": "laser-sail probe swarm (0.175c)",
    "fusion_strike": "fusion strike fleet (0.12c)",
    "wow_fleet": "fleet from the WOW! signal source",
    "genesis_fleet": "fleet from a civilization we seeded",
    "mirror_fleet": "fleet from the mirror civilization",
}


class AttackWarning:
    """Tracks an incoming hostile fleet attack"""

    def __init__(self, source_system, arrival_generation, current_generation, attack_type: str = "fleet",
                 source_stage_name: Optional[str] = None):
        self.source = source_system
        self.arrival_gen = arrival_generation
        self.detected_gen = current_generation
        self.attack_type = attack_type
        # The stage the source was in when it launched. A fleet is as strong as the civilization
        # that built it, and it crosses centuries: by the time it arrives its builders may be
        # further along, or gone. `None` means "read the source's current stage" (old saves).
        self.source_stage_name = source_stage_name
        self.defensive_actions_taken = []
        self.defense_multiplier = 1.0  # 1.0 = no reduction, 0.5 = 50% reduction

    @property
    def type_label(self) -> str:
        return ATTACK_TYPE_LABELS.get(self.attack_type, self.attack_type.replace("_", " "))

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

    def apply_diplomatic_attempt(self) -> str:
        """Record diplomatic contact attempt. Outcome unknown — no mechanical guarantee."""
        self.defensive_actions_taken.append("Diplomatic Contact")
        return "Diplomatic signal transmitted. No guaranteed effect — the fleet may ignore it."

    # ------------------------------------------------------------------ persistence
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source.name,
            "arrival_gen": self.arrival_gen,
            "detected_gen": self.detected_gen,
            "attack_type": self.attack_type,
            "source_stage_name": self.source_stage_name,
            "defensive_actions_taken": list(self.defensive_actions_taken),
            "defense_multiplier": self.defense_multiplier,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], systems: Dict[str, Any]) -> Optional["AttackWarning"]:
        source = systems.get(data.get("source"))
        if source is None:
            logging.warning(f"Save refers to an unknown attack source {data.get('source')!r}; warning dropped")
            return None
        warning = cls(source, data["arrival_gen"], data.get("detected_gen", data["arrival_gen"]),
                      data.get("attack_type", "fleet"),
                      # A save written before T2 did not record it: fall back to the source's
                      # current stage, which is exactly what the engine used to do.
                      source_stage_name=data.get("source_stage_name"))
        warning.defensive_actions_taken = list(data.get("defensive_actions_taken", []))
        warning.defense_multiplier = data.get("defense_multiplier", 1.0)
        return warning
