"""
Genesis Project for Legacy of Stars
Seed sterile worlds with engineered Earth life and watch them evolve over generations.
Unlocked by the Genesis Bio-Programming technology.

Mechanics:
- Seeding costs research points, funding and one action point; one seeding per generation.
- Seeded worlds evolve: microbial -> complex life -> intelligence -> spaceflight.
- A spacefaring creation becomes a real civilization: an ally that greets its makers
  (counts as a contact), or a paranoid rival that launches a fleet at Earth (Dark Forest risk).
"""
import logging
import random
from typing import Dict, Optional, Tuple

STAGE_NAMES = ["Microbial", "Complex Life", "Intelligence", "Spaceflight"]
COMPLEX_LIFE_AGE = 10      # generations after seeding
INTELLIGENCE_AGE = 25
SPACEFLIGHT_AGE = 40
FLEET_SPEED_C = 0.10       # a young civilization's warships, fraction of light speed


class SeededWorld:
    """Represents a world seeded by Earth"""

    def __init__(self, system_name: str, seed_gen: int):
        self.system_name = system_name
        self.seed_gen = seed_gen
        self.evolution_stage = 0  # index into STAGE_NAMES
        self.is_hostile = False
        self.is_destroyed = False
        self.resolved = False     # reached spaceflight and chose a side
        self.outcome: Optional[str] = None  # "ally" | "hostile"

    def get_age(self, current_gen: int) -> int:
        return current_gen - self.seed_gen

    @property
    def stage_name(self) -> str:
        return STAGE_NAMES[min(self.evolution_stage, len(STAGE_NAMES) - 1)]

    def to_dict(self) -> Dict:
        return {
            "system_name": self.system_name,
            "seed_gen": self.seed_gen,
            "evolution_stage": self.evolution_stage,
            "is_hostile": self.is_hostile,
            "is_destroyed": self.is_destroyed,
            "resolved": self.resolved,
            "outcome": self.outcome,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "SeededWorld":
        world = cls(data["system_name"], data["seed_gen"])
        world.evolution_stage = data.get("evolution_stage", 0)
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
        if not self.unlocked:
            return False, "Genesis Project technology not yet researched."
        if system.name not in game.star_systems:
            return False, "System not found in this galaxy."
        if self.seeds_this_gen >= 1:
            return False, "Can only seed one world per generation."
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

        world = SeededWorld(system.name, game.generation)
        self.seeded_worlds[system.name] = world
        system.is_seeded = True
        self.seeds_this_gen += 1
        stats = getattr(game, "stats", None)
        if stats is not None:
            stats["worlds_seeded"] = stats.get("worlds_seeded", 0) + 1

        logging.info(f"GENESIS: Seeded life on {system.name} (Gen {game.generation})")
        return True, (f"🌱 Life seeded on {system.name}. Engineered microbes are on their way; "
                      f"complex life in ~{COMPLEX_LIFE_AGE} generations, intelligence in ~{INTELLIGENCE_AGE}, "
                      f"spaceflight in ~{SPACEFLIGHT_AGE}. What they think of their makers is up to them.")

    # ------------------------------------------------------------------ per generation
    def advance_generation(self, game) -> None:
        """Update seeded worlds"""
        self.seeds_this_gen = 0
        for world in list(self.seeded_worlds.values()):
            if world.is_destroyed or world.resolved:
                continue
            age = world.get_age(game.generation)
            if world.evolution_stage == 0 and age >= COMPLEX_LIFE_AGE:
                world.evolution_stage = 1
                logging.info(f"GENESIS: {world.system_name} advanced to Complex Life")
                game.emit("genesis", f"🌱 GENESIS UPDATE: {world.system_name} has developed complex ecosystems.",
                          system=world.system_name, stage=world.stage_name)
            elif world.evolution_stage == 1 and age >= INTELLIGENCE_AGE:
                world.evolution_stage = 2
                logging.info(f"GENESIS: {world.system_name} advanced to Intelligence")
                game.emit("genesis", f"🧠 GENESIS UPDATE: Intelligence detected on {world.system_name}! "
                                     "Their first radio signals are our own genome, sung back to us.",
                          system=world.system_name, stage=world.stage_name)
            elif world.evolution_stage == 2 and age >= SPACEFLIGHT_AGE:
                world.evolution_stage = 3
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
        system.civilization_age = world.get_age(game.generation) * 25
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
