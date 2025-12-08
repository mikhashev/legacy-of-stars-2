"""
WOW! Signal Event System for Legacy of Stars
Implements ultra-long-term legacy mechanic (Gen 1 -> Gen 144)
"""

import random
import logging

class WOWSignalEvent:
    """Manages the WOW! Signal opening scenario and Gen 144 response"""
    
    def __init__(self, contact_program):
        self.program = contact_program
        self.wow_replied = False
        self.wow_response_gen = 144
        self.wow_source_system = None
        self.wow_reply_message = ""
        self.attack_damage_reduction = 0.0  # For silent choice
        
    def present_opening_scenario(self):
        """Display WOW Signal scenario at game start (Gen 1, 1977)"""
        print("\n" + "="*70)
        print("LEGACY OF STARS")
        print("="*70)
        print("\nAugust 15, 1977 - 23:16 EDT")
        print("Big Ear Radio Telescope, Ohio State University")
        print("\nDr. Jerry Ehman reviews automated radio telescope data.")
        print("A 72-second burst at 1420 MHz catches his eye.")
        print("\nSignal intensity: 6EQUJ5 (30x background noise)")
        print("Direction: Sagittarius (Chi Sagittarii region)")
        print("Distance: ~1,800 light-years (disputed estimate)")
        print("\nHe circles it with red pen and writes: 'Wow!'")
        print("\nThis signal will never repeat.")
        print("You must decide Earth's response.")
        print("\n" + "="*70)
        print("CRITICAL DECISION")
        print("="*70)
        print("\nDo you authorize a reply transmission?")
        print("\n1. YES - Send Reply")
        print("   • Message travels 72 generations (1,800 LY)")
        print("   • Response/attack arrives Gen 144 (Year 3577)")
        print("   • Immediate: +100 RP, +10% Support")
        print("   • Warning: Unknown consequences")
        print("\n2. NO - Stay Silent")
        print("   • Earth remains hidden")
        print("   • Immediate: -15% attack damage (permanent)")
        print("   • WOW! mystery unsolved")
        print("\nNote: Most players won't reach Gen 144")
        print("This is your legacy decision.")
        print("="*70)
        
        while True:
            choice = input("\nYour decision (1 or 2): ").strip()
            if choice in ["1", "2"]:
                break
            print("Please enter 1 or 2")
        
        if choice == "1":
            self.handle_reply_choice()
        else:
            self.handle_silent_choice()
            
    def handle_reply_choice(self):
        """Player chose to reply"""
        self.wow_replied = True
        
        # Compose custom message
        print("\n" + "="*70)
        print("COMPOSE EARTH'S FIRST INTERSTELLAR MESSAGE")
        print("="*70)
        print("\nYou are composing humanity's reply to the WOW! Signal.")
        print("This message will travel 1,800 light-years to Chi Sagittarii.")
        print("\nInspiration: The 1974 Arecibo Message included:")
        print("  • Numbers 1-10, atomic numbers of key elements")
        print("  • DNA structure, human form")
        print("  • Earth's population, solar system position")
        print("\nWhat message should Earth send?")
        print("1. Compose custom message")
        print("2. Generate AI message (Uses Director profile)")
        print("3. Use Standard Format (Default)")
        print("-"*70)
        
        msg_choice = input("\nChoose option (1-3): ").strip()
        custom_message = ""
        
        if msg_choice == '1':
            print("(Max 500 chars)")
            custom_message = input("Message: ").strip()[:500]
        elif msg_choice == '2':
            print("\nGenerating message based on Director profile...")
            director = self.program.current_director
            traits = ", ".join(director.traits)
            prompt = f"Compose a short (max 2 sentences) first contact message from Earth to an unknown alien civilization. The Director sending it has these traits: {traits}. The tone should reflect these traits."
            try:
                custom_message = self.program.ai.generate_text(prompt, "You are a sci-fi writer.")
                print(f"\nGenerated: \"{custom_message}\"")
                confirm = input("Use this message? (y/n): ")
                if confirm.lower() != 'y':
                    custom_message = ""
            except Exception as e:
                print(f"AI Generation failed: {e}")
                custom_message = ""

        if not custom_message:
            # Default message
            custom_message = """Greetings from Earth. We are humanity, a civilization of 4 billion individuals on the third planet of a yellow star. We seek knowledge and friendship among the stars. This message was sent in response to your signal of August 15, 1977. We await your reply with hope."""
        
        # Store the message
        self.wow_reply_message = custom_message
        
        # Secretly assign WOW civilization
        self.wow_source_system = self._assign_wow_civilization()
        
        # Immediate bonuses
        self.program.research_points += 100
        self.program.public_support = min(100, self.program.public_support + 10)
        
        print("\n" + "="*70)
        print("November 1977 - Reply Transmitted")
        print("="*70)
        print(f"\nMessage: \"{custom_message[:100]}{'...' if len(custom_message) > 100 else ''}\"")
        print(f"\nTarget: Chi Sagittarii region (~1,800 LY)")
        print(f"ETA: Generation 72 (Year {1977 + 72*25})")
        print(f"Response ETA: Generation 144 (Year {1977 + 144*25})")
        print("\nThe die is cast. Future generations will learn the truth.")
        print("\n+100 Research Points")
        print("+10% Public Support")
        print("="*70)
        
        logging.info("="*60)
        logging.info("WOW! SIGNAL: Reply sent to 1,800 LY distance")
        logging.info(f"WOW! MESSAGE: {custom_message}")
        logging.info(f"WOW! SIGNAL: Secret source = {self.wow_source_system.name}")
        logging.info(f"WOW! SIGNAL: Strategy = {self.wow_source_system.true_strategy}")
        logging.info("="*60)
        
        input("\nPress Enter to begin your mission...")
        
    def handle_silent_choice(self):
        """Player chose silence"""
        self.wow_replied = False
        
        # Immediate bonus - defensive buff
        self.attack_damage_reduction = 0.15
        
        print("\n" + "="*70)
        print("November 1977 - Silence Maintained")
        print("="*70)
        print("\nEarth chooses caution over contact.")
        print("The WOW! Signal remains unexplained.")
        print("Humanity stays hidden in the dark.")
        print("\nDefensive Mindset: -15% attack damage (permanent)")
        print("\nAchievement Unlocked: Silent Wisdom")
        print("="*70)
        
        logging.info("="*60)
        logging.info("WOW! SIGNAL: No reply sent - cautious approach")
        logging.info("Achievement: Silent Wisdom")
        logging.info("="*60)
        
        input("\nPress Enter to begin your mission...")
        
    def _assign_wow_civilization(self):
        """Secretly assign one civilization as WOW source"""
        # Find active civilizations
        active_civs = [s for s in self.program.star_systems.values() 
                      if s.has_civilization and not s.is_extinct]
        
        if not active_civs:
            # Fallback: pick any system with civilization
            all_civs = [s for s in self.program.star_systems.values() 
                       if s.has_civilization]
            if all_civs:
                active_civs = all_civs
            else:
                return None
        
        # Pick one as WOW source
        wow_source = random.choice(active_civs)
        wow_source.is_wow_source = True
        return wow_source
    
    def check_gen144_event(self):
        """Check if Gen 144 event should trigger"""
        if not self.wow_replied:
            return False
        
        if self.program.generation != self.wow_response_gen:
            return False
        
        return True
    
    def trigger_gen144_event(self):
        """Handle the Gen 144 WOW response event"""
        if not self.wow_source_system:
            return
        
        wow_system = self.wow_source_system
        
        logging.critical("="*70)
        logging.critical("GENERATION 144 - WOW! SIGNAL RESPONSE")
        logging.critical("="*70)
        logging.critical(f"Source: {wow_system.name}")
        logging.critical(f"Strategy: {wow_system.true_strategy}")
        
        # Branch based on strategy
        if wow_system.true_strategy == "L":
            self._wow_outcome_silence()
        elif wow_system.true_strategy in ["LB", "LR"]:
            self._wow_outcome_friendly(wow_system)
        elif wow_system.true_strategy in ["LA", "LBA"]:
            self._wow_outcome_hostile(wow_system)
    
    def _wow_outcome_silence(self):
        """L civilization - eternal silence"""
        self.program.message = f"""
{'='*70}
⭐ GENERATION 144 - THE WOW! SIGNAL ⭐
{'='*70}

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
{'='*70}
        """
        
        logging.info("Achievement: The Long Wait")
    
    def _wow_outcome_friendly(self, wow_system):
        """Friendly response after 3,600 years"""
        original_message = self.wow_reply_message
        
        # Generate profound AI response
        context = f"""After 3,600 years, civilization from {wow_system.name} responds to 1977 WOW! Signal reply. 144 generations passed.

Earth's original message was: "{original_message}"

Reference this message in your response."""
        
        prompt = """You are an ancient alien civilization responding after 3,600 years. Your message crosses 144 human generations. Acknowledge their original message. Be profound about time, patience, cosmic perspective, and the courage to reach out. Keep under 300 words."""
        
        response_text = self.program.ai.generate_text(context, prompt)
        
        # Massive support boost
        self.program.public_support = 100
        self.program.knowledge_base = min(100, self.program.knowledge_base + 50)
        
        self.program.message = f"""
{'='*70}
⭐⭐⭐ GENERATION 144 - FIRST CONTACT ⭐⭐⭐
{'='*70}

3,600 years after we replied to the WOW! Signal...
144 generations of human history...

In 1977, Earth sent: "{original_message[:100]}{'...' if len(original_message) > 100 else ''}"

Today, we received this response from {wow_system.name}:

"{response_text}"

Humanity's patience across the centuries has been rewarded.
Our ancestors' bold decision in 1977 has borne fruit.

Public Support: 100%
Knowledge: +50%

Achievement Unlocked: "The WOW! Response" (ULTRA RARE)
{'='*70}
        """
        
        logging.info("Achievement: The WOW! Response (ULTRA RARE)")
    
    def _wow_outcome_hostile(self, wow_system):
        """Attack arrives from WOW source"""
        self.program.message = f"""
{'='*70}
⚠️⚠️⚠️ GENERATION 144 - ATTACK FROM WOW SOURCE ⚠️⚠️⚠️
{'='*70}

August 15, 1977: We replied to the WOW! Signal.
72 generations for our message to reach them.
72 generations for their weapons to reach us.

Hostile fleet from {wow_system.name} has arrived.

Our ancestors' decision 3,600 years ago has sealed our fate.

This is the price of breaking the Great Silence.
This is the lesson of the Dark Forest.

Achievement Unlocked: "The WOW! Reckoning"
{'='*70}
        """
        
        logging.critical(f"WOW! ATTACK from {wow_system.name}")
        logging.info("Achievement: The WOW! Reckoning")
        
        # Apply attack (use existing attack system)
        # Tech gap check
        if wow_system.civilization_stage.value >= self.program.tech_level + 2:
            self.program.game_over = True
            self.program.message += "\n\nGAME OVER: Devastating attack from WOW! source. Earth annihilated."
        else:
            # Survivable attack but severe consequences
            self.program.research_points = max(0, self.program.research_points - 500)
            self.program.public_support = max(10, self.program.public_support - 50)
            self.program.funding = max(20, self.program.funding - 40)
            self.program.message += f"\n\nAttack survived but at terrible cost:\n-500 RP, -50% Support, -40% Funding"
