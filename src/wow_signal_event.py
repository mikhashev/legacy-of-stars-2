"""
WOW! Signal Event System for Legacy of Stars
Implements the ultra-long-term legacy mechanic (Gen 1 -> Gen 144).

This module holds only game state and rules.  The opening scenario text and
the player's prompt live in the UI layer (game_interface.py), which calls
reply() or stay_silent().
"""

import logging
import random

DEFAULT_REPLY_MESSAGE = (
    "Greetings from Earth. We are humanity, a civilization of 4 billion individuals on the "
    "third planet of a yellow star. We seek knowledge and friendship among the stars. This "
    "message was sent in response to your signal of August 15, 1977. We await your reply with hope."
)


class WOWSignalEvent:
    """Manages the WOW! Signal decision and the Gen 144 response"""

    RESPONSE_GENERATION = 144

    def __init__(self, contact_program):
        self.program = contact_program
        self.decided = False
        self.wow_replied = False
        self.wow_response_gen = self.RESPONSE_GENERATION
        self.wow_source_system = None
        self.wow_reply_message = ""
        self.attack_damage_reduction = 0.0  # For the silent choice
        self.outcome = None  # "silence" | "friendly" | "hostile" once Gen 144 has resolved

    # ------------------------------------------------------------ decisions
    def reply(self, message: str = "") -> None:
        """Player chose to reply to the WOW! signal (Generation 1, 1977)."""
        self.decided = True
        self.wow_replied = True
        self.wow_reply_message = (message or "").strip() or DEFAULT_REPLY_MESSAGE

        # The source civilization is chosen when the response window arrives (Gen 144),
        # from whatever the program knows about the sky by then.
        self.wow_source_system = None

        # Immediate bonuses
        self.program.research_points += 100
        self.program.public_support = min(100, self.program.public_support + 10)

        logging.info("=" * 60)
        logging.info("WOW! SIGNAL: Reply sent to 1,800 LY distance")
        logging.info(f"WOW! MESSAGE: {self.wow_reply_message}")
        logging.info("=" * 60)

    def stay_silent(self) -> None:
        """Player chose not to reply."""
        self.decided = True
        self.wow_replied = False
        self.attack_damage_reduction = 0.15

        logging.info("=" * 60)
        logging.info("WOW! SIGNAL: No reply sent - cautious approach")
        logging.info("Achievement: Silent Wisdom")
        self.program.unlock_achievement("Silent Wisdom")
        logging.info("=" * 60)

    def _assign_wow_civilization(self):
        """Secretly assign one civilization as the WOW source"""
        active_civs = [s for s in self.program.star_systems.values()
                       if s.has_civilization and not s.is_extinct]

        if not active_civs:
            all_civs = [s for s in self.program.star_systems.values() if s.has_civilization]
            if all_civs:
                active_civs = all_civs
            else:
                return None

        wow_source = random.choice(active_civs)
        wow_source.is_wow_source = True
        return wow_source

    # ------------------------------------------------------------ persistence
    def to_dict(self) -> dict:
        return {
            "decided": self.decided,
            "wow_replied": self.wow_replied,
            "wow_reply_message": self.wow_reply_message,
            "attack_damage_reduction": self.attack_damage_reduction,
            "outcome": self.outcome,
            "wow_source_name": self.wow_source_system.name if self.wow_source_system else None,
        }

    @classmethod
    def from_dict(cls, data: dict, contact_program) -> "WOWSignalEvent":
        wow = cls(contact_program)
        wow.decided = bool(data.get("decided", False))
        wow.wow_replied = bool(data.get("wow_replied", False))
        wow.wow_reply_message = data.get("wow_reply_message", "")
        wow.attack_damage_reduction = float(data.get("attack_damage_reduction", 0.0))
        wow.outcome = data.get("outcome")
        source_name = data.get("wow_source_name")
        wow.wow_source_system = contact_program.star_systems.get(source_name) if source_name else None
        return wow

    # ------------------------------------------------------------ Gen 144
    def check_gen144_event(self) -> bool:
        """Check if the Gen 144 event should trigger"""
        if not self.wow_replied or self.outcome is not None:
            return False
        return self.program.generation == self.wow_response_gen

    def trigger_gen144_event(self) -> None:
        """Handle the Gen 144 WOW response event"""
        if self.wow_source_system is None:
            self.wow_source_system = self._assign_wow_civilization()
        if not self.wow_source_system:
            self.outcome = "silence"
            self._wow_outcome_silence()
            return

        wow_system = self.wow_source_system

        logging.info("=" * 70)
        logging.info("GENERATION 144 - WOW! SIGNAL RESPONSE")
        logging.info("=" * 70)
        logging.info(f"Source: {wow_system.name}")
        logging.info(f"Strategy: {wow_system.true_strategy}")

        if wow_system.true_strategy in ("LB", "LR"):
            self.outcome = "friendly"
            self._wow_outcome_friendly(wow_system)
        elif wow_system.true_strategy in ("LA", "LBA"):
            self.outcome = "hostile"
            self._wow_outcome_hostile(wow_system)
        else:
            self.outcome = "silence"
            self._wow_outcome_silence()

    def _wow_outcome_silence(self):
        """L civilization (or no source) - eternal silence"""
        self.program.emit("wow", f"""
{'=' * 70}
⭐ GENERATION 144 - THE WOW! SIGNAL ⭐
{'=' * 70}

It has been 3,600 years since humanity sent the reply.
144 generations have passed since August 15, 1977.

The response window has arrived.

...

Silence.

No reply. No attack. Nothing.

Perhaps they were listening but chose not to answer.
Perhaps the signal was natural after all.
Perhaps they witnessed our rise and chose distance.
Perhaps they are extinct.

The galaxy keeps its secrets.

Achievement Unlocked: "The Long Wait"
{'=' * 70}
""")
        logging.info("Achievement: The Long Wait")
        self.program.unlock_achievement("The Long Wait")

    def _wow_outcome_friendly(self, wow_system):
        """Friendly response after 3,600 years"""
        original_message = self.wow_reply_message
        response_text = self.program.compose_wow_response(wow_system, original_message)

        self.program.public_support = 100
        self.program.knowledge_base = min(100, self.program.knowledge_base + 50)

        excerpt = original_message[:100] + ("..." if len(original_message) > 100 else "")
        self.program.emit("wow", f"""
{'=' * 70}
⭐⭐⭐ GENERATION 144 - FIRST CONTACT ⭐⭐⭐
{'=' * 70}

3,600 years after we replied to the WOW! Signal...
144 generations of human history...

In 1977, Earth sent: "{excerpt}"

Today, we received this response from {wow_system.name}:

"{response_text}"

Humanity's patience across the centuries has been rewarded.
Our ancestors' bold decision in 1977 has borne fruit.

Public Support: 100%
Knowledge: +50%

Achievement Unlocked: "The WOW! Response" (ULTRA RARE)
{'=' * 70}
""")
        logging.info("Achievement: The WOW! Response (ULTRA RARE)")
        self.program.unlock_achievement("The WOW! Response")

    def _wow_outcome_hostile(self, wow_system):
        """Attack arrives from the WOW source (resolved by the regular attack system)"""
        self.program.emit("wow", f"""
{'=' * 70}
⚠️⚠️⚠️ GENERATION 144 - ATTACK FROM WOW SOURCE ⚠️⚠️⚠️
{'=' * 70}

August 15, 1977: We replied to the WOW! Signal.
72 generations for our message to reach them.
72 generations for their weapons to reach us.

Hostile fleet from {wow_system.name} has arrived.

Our ancestors' decision 3,600 years ago has sealed our fate.

This is the price of breaking the Great Silence.
This is the lesson of the Dark Forest.

Achievement Unlocked: "The WOW! Reckoning"
{'=' * 70}
""")
        logging.warning(f"WOW! ATTACK from {wow_system.name}")
        logging.info("Achievement: The WOW! Reckoning")
        self.program.unlock_achievement("The WOW! Reckoning")

        # The fleet is here now; the standard attack resolution applies defenses and damage.
        self.program._schedule_attack(wow_system, self.program.generation, "wow_fleet", announce=False)
