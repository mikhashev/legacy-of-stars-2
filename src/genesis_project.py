"""
Genesis Ark Program for Legacy of Stars
Send arks - frozen embryos, engineered organisms and machine guardians - to sterile worlds
and watch what grows there over the generations. Unlocked by the Genesis Ark Program technology.

Mechanics:
- Launching an ark costs research points, funding and one action point; one launch per generation.
- The ark crosses at fusion speed (0.12c), so it is in transit for decades or centuries.
- After landing the colony develops: founded -> self-sustaining -> industrial -> spaceflight.
- A spacefaring creation becomes a real civilization: an ally that greets its makers
  (counts as a contact), or a paranoid rival that launches a fleet at Earth (Dark Forest risk).
"""
import logging
import math
import random
from typing import Dict, Optional, Tuple

from .passive_leakage import FUSION_SPEED_C  # Project Daedalus fusion drive: what carries an ark

STAGE_NAMES = ["In transit", "Colony founded", "Self-sustaining", "Industrial", "Spaceflight"]
#: Knowledge a system must be studied to before an ark may be aimed at it - the same threshold
#: `StarSystem.describe_civilization` reveals whether anyone lives there. Mirrors
#: `ContactProgram.genesis_targets`, which filters the offered list by it.
GENESIS_KNOWLEDGE_REQUIRED = 20
SELF_SUSTAINING_AGE = 10   # generations after the ark lands
INDUSTRIAL_AGE = 25
SPACEFLIGHT_AGE = 40
FLEET_SPEED_C = 0.10       # a young civilization's warships, fraction of light speed


def ark_arrival_generation(seed_gen: int, distance: float) -> int:
    """Generation the ark reaches a system `distance` light-years away at 0.12c."""
    return seed_gen + math.ceil((float(distance) / FUSION_SPEED_C) / 25)


class SeededWorld:
    """Represents a world seeded by Earth"""

    def __init__(self, system_name: str, seed_gen: int, arrival_gen: Optional[int] = None):
        self.system_name = system_name
        self.seed_gen = seed_gen
        # When the ark lands. Every developmental milestone is counted from this generation.
        self.arrival_gen = seed_gen if arrival_gen is None else arrival_gen
        self.evolution_stage = 0  # index into STAGE_NAMES
        self.is_hostile = False
        self.is_destroyed = False
        self.resolved = False     # reached spaceflight and chose a side
        self.outcome: Optional[str] = None  # "ally" | "hostile"

    def get_age_since_arrival(self, current_gen: int) -> int:
        """Generations since the ark landed; negative while it is still in transit."""
        return current_gen - self.arrival_gen

    @property
    def stage_name(self) -> str:
        return STAGE_NAMES[min(self.evolution_stage, len(STAGE_NAMES) - 1)]

    def to_dict(self) -> Dict:
        return {
            "system_name": self.system_name,
            "seed_gen": self.seed_gen,
            "arrival_gen": self.arrival_gen,
            "evolution_stage": self.evolution_stage,
            "is_hostile": self.is_hostile,
            "is_destroyed": self.is_destroyed,
            "resolved": self.resolved,
            "outcome": self.outcome,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "SeededWorld":
        world = cls(data["system_name"], data["seed_gen"],
                    data.get("arrival_gen", data["seed_gen"]))
        world.evolution_stage = data.get("evolution_stage", 0)
        if "arrival_gen" not in data:
            # v1.0 save: stages were Microbial/Complex/Intelligence/Spaceflight (0-3) and the
            # ark was already "there"; shift past the new "In transit" stage 0.
            world.evolution_stage = min(world.evolution_stage + 1, len(STAGE_NAMES) - 1)
        world.is_hostile = data.get("is_hostile", False)
        world.is_destroyed = data.get("is_destroyed", False)
        world.resolved = data.get("resolved", False)
        world.outcome = data.get("outcome")
        return world


class GenesisProject:
    """Manages the Genesis Project and seeded worlds"""

    def __init__(self):
        self.seeded_worlds: Dict[str, SeededWorld] = {}
        self.unlocked = False
        self.seed_cost_rp = 500
        self.seed_cost_funding = 20
        self.seed_cost_ap = 1
        self.seeds_this_gen = 0  # Limit: 1 seeding action per generation
        logging.info("Genesis Project system initialized")

    # ------------------------------------------------------------------ actions
    def seed_world(self, game, system) -> Tuple[bool, str]:
        """Attempt to seed a star system. Returns (success, player message)."""
        from .legacy_of_stars_v3 import habitability_weight  # local import avoids a circular dependency

        if not self.unlocked:
            return False, "Genesis Project technology not yet researched."
        if system.name not in game.star_systems:
            return False, "System not found in this galaxy."
        if self.seeds_this_gen >= 1:
            return False, "Can only seed one world per generation."
        if getattr(system, "is_wow_source", False):
            return False, "Target is 1,800 light-years away: beyond any ark's range."
        if habitability_weight(system.spectral_type) <= 0:
            return False, f"No habitable planet: {system.spectral_type} star."
        # Before the civilization check, deliberately: "already has a civilization" is a fact
        # about the system, and answering it for an unstudied one would hand the player free
        # reconnaissance. 20 % is the same threshold `describe_civilization` reveals it at.
        if system.knowledge < GENESIS_KNOWLEDGE_REQUIRED:
            return False, "Study the system first: 20% knowledge is needed before launching an ark."
        if system.has_civilization:
            return False, "Cannot seed a system that already has a civilization."
        if system.name in self.seeded_worlds or getattr(system, "is_seeded", False):
            return False, "System is already seeded."
        if game.research_points < self.seed_cost_rp:
            return False, f"Insufficient Research Points ({self.seed_cost_rp} required)."
        if game.funding < self.seed_cost_funding:
            return False, f"Insufficient Funding ({self.seed_cost_funding}% required)."
        if game.action_points < self.seed_cost_ap:
            return False, f"Not enough Action Points ({self.seed_cost_ap} required)."

        game.research_points -= self.seed_cost_rp
        game.funding -= self.seed_cost_funding
        game.action_points -= self.seed_cost_ap

        arrival_gen = ark_arrival_generation(game.generation, system.distance)
        world = SeededWorld(system.name, game.generation, arrival_gen)
        self.seeded_worlds[system.name] = world
        system.is_seeded = True
        self.seeds_this_gen += 1
        note = getattr(game, "note_player_action", None)
        if callable(note):  # anti-stagnation bookkeeping and the generation log on the program
            note("genesis_seed", f"Launched a Genesis ark toward {system.name}",
                 f"{self.seed_cost_ap} AP + {self.seed_cost_rp} RP")
        stats = getattr(game, "stats", None)
        if stats is not None:
            stats["worlds_seeded"] = stats.get("worlds_seeded", 0) + 1

        logging.info(f"GENESIS: Ark launched toward {system.name} (Gen {game.generation}, "
                     f"arrival Gen {arrival_gen})")
        return True, (f"🚀 Genesis ark launched toward {system.name} ({system.distance:.1f} LY). "
                      f"At 0.12c it lands in Generation {arrival_gen}; the colony is self-sustaining "
                      f"~{SELF_SUSTAINING_AGE} generations after that, industrial at ~{INDUSTRIAL_AGE}, "
                      f"spacefaring at ~{SPACEFLIGHT_AGE} (Generation {arrival_gen + SPACEFLIGHT_AGE}). "
                      "What they think of their makers is up to them.")

    # ------------------------------------------------------------------ per generation
    def advance_generation(self, game) -> None:
        """Update seeded worlds"""
        self.seeds_this_gen = 0
        for world in list(self.seeded_worlds.values()):
            if world.is_destroyed or world.resolved:
                continue
            age = world.get_age_since_arrival(game.generation)
            if world.evolution_stage == 0 and age >= 0:  # the ark has landed
                world.evolution_stage = 1
                logging.info(f"GENESIS: ark landed on {world.system_name}; colony founded")
                game.emit("genesis", f"🚀 GENESIS UPDATE: The ark has reached {world.system_name}. "
                                     "The guardians report a landing, a shelter and the first thawed embryos.",
                          system=world.system_name, stage=world.stage_name)
            elif world.evolution_stage == 1 and age >= SELF_SUSTAINING_AGE:
                world.evolution_stage = 2
                logging.info(f"GENESIS: {world.system_name} is self-sustaining")
                game.emit("genesis", f"🌱 GENESIS UPDATE: The colony on {world.system_name} feeds itself. "
                                     "The archive is no longer the only thing keeping them alive.",
                          system=world.system_name, stage=world.stage_name)
            elif world.evolution_stage == 2 and age >= INDUSTRIAL_AGE:
                world.evolution_stage = 3
                logging.info(f"GENESIS: {world.system_name} reached Industrial stage")
                game.emit("genesis", f"🏭 GENESIS UPDATE: {world.system_name} has an industrial civilization. "
                                     "Their first radio signals are our own genome, sung back to us.",
                          system=world.system_name, stage=world.stage_name)
            elif world.evolution_stage == 3 and age >= SPACEFLIGHT_AGE:
                world.evolution_stage = 4
                logging.info(f"GENESIS: {world.system_name} achieved Spaceflight")
                self._resolve(world, game)

    def _resolve(self, world: SeededWorld, game) -> None:
        """A spacefaring creation decides what its makers are to it."""
        from .legacy_of_stars_v3 import CivilizationStage  # local import avoids a circular dependency

        world.resolved = True
        system = game.star_systems.get(world.system_name)
        if system is None:
            return

        hostile = random.random() < 0.5
        world.is_hostile = hostile
        world.outcome = "hostile" if hostile else "ally"

        # The seeded world is now a real civilization
        system.has_civilization = True
        system.is_extinct = False
        system.has_swan_song = False
        system.civilization_age = max(1, world.get_age_since_arrival(game.generation)) * 25
        system.civilization_stage = CivilizationStage.INTERPLANETARY
        system.civilization_type = "hybrid_integrated"
        system.deception_level = 0.0
        system.knowledge = max(system.knowledge, 60)
        ctx = {"system": system.name, "year": game.start_year + (game.generation - 1) * 25}

        if hostile:
            system.true_strategy = "LA"
            system.civilization_attitude = 0.1
            travel = max(1, int(system.distance / FLEET_SPEED_C / 25))
            text = game.content.special("genesis_hostile", ctx)
            game.emit("genesis", f"⚠️ GENESIS CRISIS: {text}", system=system.name, outcome="hostile")
            game._schedule_attack(system, game.generation + travel, "genesis_fleet",
                                  note=" Our own creation has turned against us.")
            game.add_fermi_evidence("dark_forest_evidence", 2, f"our creation on {system.name} turned hostile")
        else:
            system.true_strategy = "LB"
            system.civilization_attitude = 0.9
            greeting = game.content.genesis_greeting(ctx)
            system.received_messages.append(greeting)
            game.public_support = min(100, game.public_support + 20)
            game.knowledge_base = min(100, game.knowledge_base + 10)
            game.emit("genesis",
                      f"🤝 GENESIS SUCCESS: {system.name} greets us as Parents of the Stars.\n\"{greeting}\"\n\n"
                      "A permanent alliance is formed. Public support +20%, knowledge +10%.",
                      system=system.name, outcome="ally")
            game.add_fermi_evidence("cooperation_evidence", 2, f"our creation on {system.name} became an ally")
            game.unlock_achievement("Parents of the Stars")

        # A colony we planted has a known history: a static timeline from the year it was founded,
        # so every reader can go through `state_at()` (T1) whether the civilization was rolled or
        # written by hand.
        system.set_static_timeline(int(ctx["year"] - system.civilization_age))

    # ------------------------------------------------------------------ display / persistence
    def get_summary(self) -> str:
        """Get summary string for UI"""
        if not self.unlocked:
            return "Genesis Project: Locked"
        if not self.seeded_worlds:
            return "Genesis Project: Active (0 worlds seeded)"
        lines = [f"Genesis Project: {len(self.seeded_worlds)} world(s) seeded"]
        for name, world in self.seeded_worlds.items():
            if world.resolved:
                status = "HOSTILE" if world.is_hostile else "Allied"
            else:
                status = "Developing"
            lines.append(f"  - {name}: {world.stage_name} ({status})")
        return "\n".join(lines)

    def to_dict(self) -> Dict:
        return {
            "unlocked": self.unlocked,
            "seeds_this_gen": self.seeds_this_gen,
            "worlds": [world.to_dict() for world in self.seeded_worlds.values()],
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "GenesisProject":
        project = cls()
        project.unlocked = data.get("unlocked", False)
        project.seeds_this_gen = data.get("seeds_this_gen", 0)
        for entry in data.get("worlds", []):
            world = SeededWorld.from_dict(entry)
            project.seeded_worlds[world.system_name] = world
        return project
