"""
Genesis Project for Legacy of Stars
Implements the ability to seed sterile worlds with Earth life, creating new civilizations.
Based on "The Genesis Project" from design notes section 11.

Mechanics:
- Seed sterile worlds (Cost: RP + Funding)
- Seeded worlds evolve over generations
- Risk: Created civilizations might become hostile (Dark Forest)
"""

import random
import logging
from typing import Dict, List, Optional, Tuple

class SeededWorld:
    """Represents a world seeded by Earth"""
    def __init__(self, system_name: str, seed_gen: int):
        self.system_name = system_name
        self.seed_gen = seed_gen
        self.evolution_stage = 0  # 0=Microbial, 1=Complex, 2=Intelligence, 3=Spaceflight
        self.is_hostile = False
        self.is_destroyed = False
        
    def get_age(self, current_gen: int) -> int:
        return current_gen - self.seed_gen

class GenesisProject:
    """Manages the Genesis Project and seeded worlds"""
    
    def __init__(self):
        self.seeded_worlds: Dict[str, SeededWorld] = {}
        self.unlocked = False
        self.seed_cost_rp = 500
        self.seed_cost_funding = 20
        self.seeds_this_gen = 0  # Limit: 1 seeding action per generation
        logging.info("Genesis Project system initialized")
        
    def seed_world(self, game, system) -> Tuple[bool, str]:
        """
        Attempt to seed a star system
        
        Args:
            game: ContactProgram instance
            system: StarSystem instance
            
        Returns:
            (success, message)
        """
        if not self.unlocked:
            return False, "Genesis Project technology not yet researched."

        if system.name not in game.star_systems:
            return False, "System not found in this galaxy."

        if self.seeds_this_gen >= 1:
            return False, "Can only seed one world per generation."

        if system.has_civilization:
            return False, "Cannot seed a system that already has a civilization."

        if system.name in self.seeded_worlds:
            return False, "System is already seeded."

        if game.research_points < self.seed_cost_rp:
            return False, f"Insufficient Research Points ({self.seed_cost_rp} required)."
            
        if game.funding < self.seed_cost_funding:
            return False, f"Insufficient Funding ({self.seed_cost_funding}% required)."
            
        # Pay costs
        game.research_points -= self.seed_cost_rp
        game.funding -= self.seed_cost_funding
        
        # Create record
        world = SeededWorld(system.name, game.generation)
        self.seeded_worlds[system.name] = world
        system.is_seeded = True  # Mark system for UI
        self.seeds_this_gen += 1

        logging.info(f"GENESIS: Seeded life on {system.name} (Gen {game.generation})")
        return True, f"Life seeded on {system.name}. Evolution will take many generations."

    def advance_generation(self, game):
        """Update seeded worlds"""
        self.seeds_this_gen = 0  # Reset per-generation seeding limit
        for world in self.seeded_worlds.values():
            if world.is_destroyed:
                continue
                
            age = world.get_age(game.generation)
            
            # Evolution checkpoints
            # In real life: Billions of years. In game: Accelerated by "Genesis Bio-Programming"
            if world.evolution_stage == 0 and age >= 10:
                world.evolution_stage = 1
                logging.info(f"GENESIS: {world.system_name} advanced to Complex Life")
                game.message_queue.append(f"🌱 GENESIS UPDATE: {world.system_name} has developed complex ecosystems.")
                
            elif world.evolution_stage == 1 and age >= 25:
                world.evolution_stage = 2
                logging.info(f"GENESIS: {world.system_name} advanced to Intelligence")
                game.message_queue.append(f"🧠 GENESIS UPDATE: Intelligence detected on {world.system_name}!")
                
            elif world.evolution_stage == 2 and age >= 40:
                world.evolution_stage = 3
                logging.info(f"GENESIS: {world.system_name} achieved Spaceflight")
                
                # Dark Forest Check!
                # 50% chance they are grateful, 50% chance they are paranoid
                if random.random() < 0.5:
                    world.is_hostile = True
                    game.message_queue.append(f"⚠️ GENESIS CRISIS: Your creation on {world.system_name} has turned HOSTILE!\nThey view their 'creators' as a threat to their independence.")
                else:
                    game.message_queue.append(f"🤝 GENESIS SUCCESS: {world.system_name} greets us as Parents of the Stars.\nA permanent alliance is formed.")
                    game.public_support += 20
                    game.knowledge_base += 10

    def get_summary(self) -> str:
        """Get summary string for UI"""
        if not self.unlocked:
            return "Genesis Project: Locked"
        
        count = len(self.seeded_worlds)
        if count == 0:
            return "Genesis Project: Active (0 worlds seeded)"
            
        summary = f"Genesis Project: {count} worlds seeded\n"
        for name, world in self.seeded_worlds.items():
            stages = ["Microbial", "Complex Life", "Intelligence", "Spaceflight"]
            stage_name = stages[world.evolution_stage]
            status = "HOSTILE" if world.is_hostile else "Developing"
            if world.evolution_stage == 3 and not world.is_hostile:
                status = "Allied"
            summary += f"  - {name}: {stage_name} ({status})\n"
            
        return summary.strip()
