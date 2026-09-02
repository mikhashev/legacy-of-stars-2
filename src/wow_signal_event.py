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

# The source of the 1977 burst, as best anyone can place it: the Chi Sagittarii region, with
# 2MASS 19281982-2640123 as the most-cited Sun-like candidate. The distance is the disputed
# 1,800 LY estimate, which makes the round trip exactly 144 generations.
WOW_SOURCE_NAME = "Wow! source (Chi Sagittarii)"
WOW_SOURCE_DISTANCE = 1800.0
WOW_SOURCE_SPECTRAL_TYPE = "G2V? (candidate 2MASS 19281982-2640123)"
WOW_SOURCE_RA = 293.7    # J2000, degrees
WOW_SOURCE_DEC = -27.0   # J2000, degrees
WOW_SOURCE_CIV_CHANCE = 0.5  # the other half of the outcomes: the burst was a natural transient


def create_wow_source_system(program):
    """Build the WOW! source star and add it to the program's sky.

    Half the time nobody lives there and the 1977 burst was natural; otherwise the civilization
    is rolled with the ordinary generator, so its age, stage, strategy and type are as honest as
    any other system's.
    """
    from .legacy_of_stars_v3 import StarSystem  # local import avoids a circular dependency

    existing = program.star_systems.get(WOW_SOURCE_NAME)
    if existing is not None:
        existing.is_wow_source = True
        return existing

    system = StarSystem(WOW_SOURCE_NAME, WOW_SOURCE_DISTANCE, WOW_SOURCE_SPECTRAL_TYPE,
                        WOW_SOURCE_RA, WOW_SOURCE_DEC)
    # One coin flip decides whether anyone is there; the catalog odds do not apply to a star
    # chosen because a signal came from it.
    system.has_civilization = random.random() < WOW_SOURCE_CIV_CHANCE
    if system.has_civilization:
        system._roll_civilization()
    else:
        system._clear_civilization()

    system.is_wow_source = True
    program.star_systems[system.name] = system
    program._register_swan_song(system)
    program._log_system_profile(system)
    logging.info(f"WOW! source catalogued: {system.name} at {system.distance:.0f} LY "
                 f"(civilization: {'yes' if system.has_civilization else 'no'})")
    return system


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

        # Replying puts the source itself on the target list: a real star 1,800 LY away, whose
        # round trip is the 144 generations of this event.
        self.wow_source_system = create_wow_source_system(self.program)

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
        source_name = data.get("wow_source_name") or WOW_SOURCE_NAME
        wow.wow_source_system = contact_program.star_systems.get(source_name)
        if wow.wow_replied and wow.outcome is None and wow.wow_source_system is None:
            # Saves written before the source became a real star, event still pending: build it now.
            wow.wow_source_system = create_wow_source_system(contact_program)
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
            self.wow_source_system = create_wow_source_system(self.program)
        wow_system = self.wow_source_system
        if not wow_system.has_civilization:
            # The burst really was a natural transient. Nobody was ever there to answer.
            self.outcome = "silence"
            self._wow_outcome_silence()
            return

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
        """The answer is a weapon made of information - the only thing that can cross 1,800 LY."""
        self.program.emit("wow", f"""
{'=' * 70}
⚠️⚠️⚠️ GENERATION 144 - THE ANSWER FROM THE WOW! SOURCE ⚠️⚠️⚠️
{'=' * 70}

August 15, 1977: We replied to the WOW! Signal.
72 generations for our message to reach {wow_system.name}.
72 generations for their answer to reach us.

Their answer was not words.

It is a transmission built to be understood, and to do damage in the
understanding: designs that fail in ways we cannot predict, arguments that
corrode, a promise shaped exactly like the one we wanted to hear.

Their weapons, if they exist, are another matter. At a tenth of light speed
they would need eighteen thousand years to cross the same distance. Nobody
alive today, and nobody alive for seven hundred generations, will see them.

But someone will have to be ready.

This is the price of breaking the Great Silence.
This is the lesson of the Dark Forest.

Achievement Unlocked: "The WOW! Reckoning"
{'=' * 70}
""")
        logging.warning(f"WOW! INFORMATION ATTACK from {wow_system.name}")
        logging.info("Achievement: The WOW! Reckoning")
        self.program.unlock_achievement("The WOW! Reckoning")

        # A signal, not a fleet: the standard information-warfare resolution, hit harder because
        # this one was answered for and waited for across 144 generations.
        wow_system.has_detected_earth = True  # no second attack from the source, whatever we send it
        self.program.process_information_attack(wow_system.name)
        if self.program.game_over:
            return
        self.program.public_support = max(0, self.program.public_support - 20)
        self.program.funding = max(0, self.program.funding - 10)
        self.program.add_fermi_evidence("dark_forest_evidence", 2,
                                        f"the WOW! source answered with a weapon ({wow_system.name})")
