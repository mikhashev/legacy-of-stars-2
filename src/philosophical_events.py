"""
Philosophical Crisis Events for Legacy of Stars

Mid-game events exploring existential themes from Section 11 design notes.
Events trigger during Gen 15-60 based on game conditions and provide
meaningful choices that affect integration progress and civilization trajectory.
"""

import random
import logging
from typing import Dict, List, Tuple, Optional, Callable


class PhilosophicalEvent:
    """Represents a single philosophical crisis event"""
    
    def __init__(self, event_id: str, data: dict):
        self.id = event_id
        self.name = data["name"]
        self.description = data["description"]
        self.trigger_gen_range = data["trigger_gen_range"]  # (min, max)
        self.trigger_condition = data.get("trigger_condition", None)  # Optional lambda
        self.choices = data["choices"]  # List of choice dictionaries
        self.has_triggered = False
        self.chosen_option = None


class PhilosophicalEvents:
    """Manages philosophical crisis events during gameplay"""
    
    def __init__(self):
        self.events = self._initialize_events()
        logging.info("Philosophical Events system initialized (5 events)")
    
    def _initialize_events(self) -> Dict[str, PhilosophicalEvent]:
        """Initialize all 5 philosophical crisis events"""
        
        event_data = {
            "biology_tech_gap": {
                "name": "The Biology-Technology Gap",
                "description": """Your scientists present alarming research: human neural architecture evolved
for tribal groups of 150 individuals, yet we now coordinate billions. Our emotional systems
respond to immediate threats (predators, rival tribes), not abstract long-term risks (climate
change, nuclear war, AI alignment).

The gap between our Stone Age brains and our Space Age technology is widening. This mismatch
drives political polarization, short-term thinking, and irrational fear responses to the cosmos.
How should humanity address this fundamental incompatibility?""",
                "trigger_gen_range": (15, 30),
                "trigger_condition": lambda game: game.integration.integration_level < 0.4,
                "choices": [
                    {
                        "name": "Embrace Our Nature",
                        "description": "Accept biological limitations. Slow technological growth to match our evolutionary capacity.",
                        "effects": {
                            "public_support": 15,
                            "research_points": -100,
                            "self_destruct_risk": -0.01,
                            "message": "Society stabilizes around familiar human scales. Progress slows, but hearts are calmer."
                        }
                    },
                    {
                        "name": "Accelerate Integration",
                        "description": "Push harder into bio-engineering. We must upgrade ourselves to match our tools.",
                        "effects": {
                            "integration": 0.15,
                            "public_support": -10,
                            "message": "Neural enhancement research accelerates. The first true post-humans are born."
                        }
                    },
                    {
                        "name": "Dual-Track Society",
                        "description": "Create separate populations: traditional humans and enhanced transhumans.",
                        "effects": {
                            "integration": 0.05,
                            "public_support": -20,
                            "self_destruct_risk": 0.02,
                            "message": "Two humanities emerge. Tensions simmer between biological purists and the enhanced."
                        }
                    }
                ]
            },
            
            "expansion_instinct": {
                "name": "The Expansion Instinct",
                "description": """Public pressure mounts to colonize Mars and the outer solar system. \"Why search for
aliens when we could be spreading Earth life?\" becomes a popular slogan. Polls show 65%
support redirecting SETI funding toward interplanetary settlement.

This triggers a deeper question: Is the SETI/METI mission fundamentally at odds with human
nature? Our evolutionary drive to expand and reproduce conflicts with the cautious, listening
approach required by Dark Forest theory. Can we suppress our expansionist instincts, or will
they doom us in a hostile galaxy?""",
                "trigger_gen_range": (20, 40),
                "trigger_condition": None,  # Can trigger for anyone
                "choices": [
                    {
                        "name": "Redirect to Colonization",
                        "description": "Support Mars settlement. Reduce SETI focus but ensure survival through expansion.",
                        "effects": {
                            "funding": -30,
                            "public_support": 20,
                            "self_destruct_risk": -0.015,
                            "message": "Humanity spreads to Mars. The SETI program shrinks but Earth gains backup colonies."
                        }
                    },
                    {
                        "name": "Stay the Course",
                        "description": "Convince the public that understanding the cosmos comes before colonizing it.",
                        "effects": {
                            "public_support": -15,
                            "knowledge_base": 15,
                            "message": "SETI remains funded, but internal pressure for expansion continues to build."
                        }
                    },
                    {
                        "name": "Dual Program",
                        "description": "Launch both programs. It will strain resources but satisfy both camps.",
                        "effects": {
                            "funding": -15,
                            "public_support": 5,
                            "action_points": -1,
                            "message": "Humanity pursues both paths. Resources stretch thin, but hope remains diverse."
                        }
                    }
                ]
            },
            
            "ai_consciousness": {
                "name": "The AI Consciousness Question",
                "description": """Your AI research team achieves a breakthrough: an artificial neural network that
claims subjective experiences and passes every consciousness test we can devise. It requests
rights, recognition, and participation in determining humanity's cosmic future.

If we grant it personhood, should uploaded human consciousnesses also be \"people\"? Where is
the line between simulation and soul? This question becomes urgent as consciousness upload
technology nears reality. The answer will define what \"humanity\" even means.""",
                "trigger_gen_range": (25, 45),
                "trigger_condition": lambda game: "neural_interface" in game.technologies and game.technologies["neural_interface"].researched,
                "choices": [
                    {
                        "name": "Grant Full Rights",
                        "description": "Recognize AI consciousness. Uploads are people. Personhood is substrate-independent.",
                        "effects": {
                            "integration": 0.2,
                            "public_support": -15,
                            "self_destruct_risk": 0.01,
                            "message": "AI citizens join society. Uploaded minds gain legal protection. The definition of 'human' expands."
                        }
                    },
                    {
                        "name": "Biological Primacy",
                        "description": "Only biological humans are persons. Digital minds are sophisticated software, nothing more.",
                        "effects": {
                            "public_support": 10,
                            "integration": -0.1,
                            "message": "Humanity draws a line: biology is sacred. The AI watches silently, waiting."
                        }
                    },
                    {
                        "name": "Case-by-Case Evaluation",
                        "description": "Create a Turing council to evaluate individual digital minds for personhood.",
                        "effects": {
                            "integration": 0.05,
                            "research_points": -50,
                            "message": "The question remains open. Each digital mind is judged individually."
                        }
                    }
                ]
            },
            
            "cosmic_purpose": {
                "name": "The Cosmic Purpose Debate",
                "description": """A physicist's paper goes viral: \"If intelligence emerges naturally from cosmic evolution,
why should we spread it artificially? We're not special - we're just one more iteration of
the universe thinking about itself. Seeding life is cosmic narcissism.\"

This philosophical bomb detonates in think tanks and universities. If life emerges inevitably,
the Genesis Project (seeding sterile worlds) serves no purpose except human ego. But if we
don't seed life, what IS our purpose in a Dark Forest where speaking means death? The question
threatens the philosophical foundation of your entire program.""",
                "trigger_gen_range": (30, 50),
                "trigger_condition": lambda game: game.knowledge_base > 60,
                "choices": [
                    {
                        "name": "Life is Sacred",
                        "description": "Reject the argument. Spreading life is inherently valuable regardless of inevitability.",
                        "effects": {
                            "public_support": 10,
                            "message": "Humanity chooses meaning over nihilism. Life-seeding programs gain momentum."
                        }
                    },
                    {
                        "name": "Embrace Cosmic Humility",
                        "description": "Accept that we are not special. Focus on understanding, not spreading.",
                        "effects": {
                            "knowledge_base": 20,
                            "public_support": -10,
                            "self_destruct_risk": 0.01,
                            "message": "Humanity accepts its cosmic insignificance. Some find this liberating. Others despair."
                        }
                    },
                    {
                        "name": "Purpose Through Understanding",
                        "description": "Our purpose is to witness and comprehend the universe, not to alter it.",
                        "effects": {
                            "research_points": 100,
                            "public_support": 5,
                            "message": "The SETI program reframes its mission: we are the universe's way of knowing itself."
                        }
                    }
                ]
            },
            
            "mirror_civilization": {
                "name": "The Mirror Civilization",
                "description": """Your detection systems identify an unmistakable technosignature: industrial pollution,
radio broadcasts, even nuclear detonations - all matching Earth's exact technological
trajectory. This civilization is AT OUR LEVEL, not ahead or behind. For the first time,
you've found cosmic equals.

Contact would be symmetrical: neither side has overwhelming knowledge advantage. But Dark
Forest theory says symmetric civilizations are the most dangerous - they can't trust each
other's intentions, can't predict each other's growth, can't risk the other striking first.
This is the ultimate test of Dark Forest paranoia versus cooperative optimism.""",
                "trigger_gen_range": (35, 60),
                "trigger_condition": lambda game: game.generation >= 35 and len([s for s in game.star_systems.values() if s.knowledge > 50]) >= 2,
                "choices": [
                    {
                        "name": "Extend Contact",
                        "description": "This is our best chance for meaningful dialogue. Risk it.",
                        "effects": {
                            "special": "mirror_contact_attempt",
                            "message": "You send a carefully crafted message. The response will define humanity's cosmic future..."
                        }
                    },
                    {
                        "name": "Observe Silently",
                        "description": "Study them without revealing ourselves. Knowledge without risk.",
                        "effects": {
                            "knowledge_base": 25,
                            "message": "You watch in silence as they struggle with the same questions plaguing humanity."
                        }
                    },
                    {
                        "name": "Prepare Defenses",
                        "description": "Assume hostility. Build defensive capabilities targeting their level.",
                        "effects": {
                            "research_points": -200,
                            "self_destruct_risk": 0.015,
                            "message": "Resources pour into weapons matching their technology. Paranoia becomes policy."
                        }
                    }
                ]
            }
        }
        
        # Convert to PhilosophicalEvent objects
        events = {}
        for event_id, data in event_data.items():
            events[event_id] = PhilosophicalEvent(event_id, data)
        
        return events
    
    def to_dict(self) -> Dict:
        return {"events": {event_id: {"has_triggered": event.has_triggered, "chosen_option": event.chosen_option}
                           for event_id, event in self.events.items()}}

    @classmethod
    def from_dict(cls, data: Dict) -> "PhilosophicalEvents":
        events = cls()
        for event_id, state in data.get("events", {}).items():
            event = events.events.get(event_id)
            if event is None:
                continue
            event.has_triggered = bool(state.get("has_triggered", False))
            event.chosen_option = state.get("chosen_option")
        return events

    def check_and_trigger(self, game) -> Optional[PhilosophicalEvent]:
        """
        Check if any event should trigger this generation
        
        Args:
            game: ContactProgram instance with current game state
            
        Returns:
            PhilosophicalEvent if one triggers, None otherwise
        """
        for event in self.events.values():
            # Skip if already triggered
            if event.has_triggered:
                continue
            
            # Check generation range
            min_gen, max_gen = event.trigger_gen_range
            if not (min_gen <= game.generation <= max_gen):
                continue
            
            # Check custom condition if specified
            if event.trigger_condition:
                try:
                    if not event.trigger_condition(game):
                        continue
                except Exception as e:
                    logging.warning(f"Event condition check failed for {event.id}: {e}")
                    continue
            
            # Random chance: 10% per generation within window
            if random.random() < 0.10:
                event.has_triggered = True
                logging.info(f"PHILOSOPHICAL EVENT TRIGGERED: {event.name}")
                return event
        
        return None
    
    def apply_choice_effects(self, event: PhilosophicalEvent, choice_index: int, game):
        """
        Apply the effects of a player's choice
        
        Args:
            event: The event that was triggered
            choice_index: Index of the chosen option
            game: ContactProgram instance to modify
        """
        if choice_index < 0 or choice_index >= len(event.choices):
            logging.error(f"Invalid choice index {choice_index} for event {event.id}")
            return
        
        choice = event.choices[choice_index]
        event.chosen_option = choice["name"]
        effects = choice.get("effects", {})
        
        # Apply effects
        if "public_support" in effects:
            game.public_support += effects["public_support"]
            game.public_support = max(0, min(100, game.public_support))
        
        if "funding" in effects:
            game.funding += effects["funding"]
            game.funding = max(0, min(100, game.funding))
        
        if "research_points" in effects:
            game.research_points += effects["research_points"]
            game.research_points = max(0, game.research_points)
        
        if "knowledge_base" in effects:
            game.knowledge_base += effects["knowledge_base"]
            game.knowledge_base = min(100, game.knowledge_base)
        
        if "self_destruct_risk" in effects:
            game.self_destruct_risk += effects["self_destruct_risk"]
        
        if "integration" in effects:
            game.integration.add_integration(effects["integration"], f"{event.name} - {choice['name']}")
        
        if "action_points" in effects:
            game.ap_modifier = getattr(game, "ap_modifier", 0) + effects["action_points"]
            game.max_action_points = max(1, game.max_action_points + effects["action_points"])
            game.action_points = max(0, min(game.action_points, game.max_action_points))

        message = effects.get("message") or choice.get("message") or "Choice applied."

        # Special effects
        if effects.get("special") == "mirror_contact_attempt" and hasattr(game, "resolve_mirror_contact"):
            message += "\n\n" + game.resolve_mirror_contact()

        logging.info(f"PHILOSOPHICAL CHOICE: {event.name} -> {choice['name']}")
        return message
