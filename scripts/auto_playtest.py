
import sys
import os
import random
import logging
from typing import List, Dict

# Add project root to path
sys.path.append(os.path.abspath("."))

from src.legacy_of_stars_v3 import ContactProgram, CivilizationStage

# Configure logging to file only to keep console clean for report
logging.basicConfig(
    filename='logs/auto_playtest.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filemode='w'
)

class AutoPlayer:
    def __init__(self, run_id: int, strategy: str = "balanced"):
        self.run_id = run_id
        self.program = ContactProgram()
        self.strategy = strategy # balanced, aggressive, cautious
        self.logs = []
        
    def log(self, msg: str):
        self.logs.append(f"[Gen {self.program.generation}] {msg}")
        logging.info(f"[Run {self.run_id}] {msg}")

    def make_decisions(self):
        # 1. Handle Defensive Actions (Priority 1)
        if self.program.pending_attack_warnings:
            for i, warning in enumerate(self.program.pending_attack_warnings):
                if warning.get_etas_remaining(self.program.generation) <= 2:
                    # Panic! Use best defense
                    if self.program.action_points == self.program.max_action_points:
                        self.program.defend_emergency(i)
                        self.log(f"Activated Emergency Defense against {warning.source.name}")
                    elif self.program.action_points >= 1:
                        self.program.defend_evacuate(i)
                        self.log(f"Activated Evacuation against {warning.source.name}")

        # 2. Genesis Seeding (Priority 2 - if unlocked and rich)
        if self.program.genesis.unlocked:
            seeds_active = len(self.program.genesis.seeded_worlds)
            if seeds_active < 2 and self.program.research_points > 600 and self.program.funding > 40:
                # Find a sterile world
                sterile = [s for s in self.program.star_systems.values() if not s.has_civilization and not s.is_seeded]
                if sterile:
                    target = random.choice(sterile)
                    success, msg = self.program.genesis.seed_world(self.program, target)
                    if success:
                        self.log(f"Seeded life on {target.name}")

        # 3. Research (Priority 3)
        available_techs = [t for t in self.program.technologies.values() 
                           if not t.researched and 
                           self.program.generation >= t.min_generation and
                           all(self.program.technologies[p].researched for p in t.prerequisites)]
        
        # Sort by cost (cheapest first)
        available_techs.sort(key=lambda t: t.cost)
        
        for tech in available_techs:
            if self.program.research_points >= tech.cost:
                needs_choice = self.program.research_tech(tech.id)
                self.log(f"Researched {tech.name}")
                if needs_choice:
                    # Pick a doctrine - prefer integration if strategy is cautious/balanced
                    choice_idx = 0
                    if self.strategy == "cautious" or self.strategy == "balanced":
                        # Try to find option with "Control" or "Defense" or "Integration"
                        pass 
                    self.program.choose_doctrine(tech.id, choice_idx)
                    self.log(f"Chose doctrine option {choice_idx} for {tech.name}")

        # 4. Messaging / Action Points (Priority 4)
        while self.program.action_points > 0:
            action_choice = random.random()
            
            # Message Sending (Risky!)
            if action_choice < 0.4:
                # Find a target
                targets = list(self.program.star_systems.keys())
                target = random.choice(targets)
                self.program.send_message(target, "Hello world")
                self.log(f"Sent message to {target}")
                
            # Public Outreach (Safe)
            elif action_choice < 0.7:
                self.program.public_outreach()
                # self.log("Conducted public outreach")
                
            # Listen for Swan Song
            elif action_choice < 0.8:
                extinct = [s for n, s in self.program.star_systems.items() if s.is_extinct and not self.program.swan_song_manager.is_discovered(n)]
                if extinct:
                    target = random.choice(extinct)
                    self.program.listen_for_swan_song(target.system_name if hasattr(target, 'system_name') else list(self.program.star_systems.keys())[list(self.program.star_systems.values()).index(target)]) # Hacky way to get name if needed, but dict key is name
                    # Actually name is key in dict
                    name = [k for k, v in self.program.star_systems.items() if v == target][0]
                    self.program.listen_for_swan_song(name)
                    self.log(f"Listened for Swan Song at {name}")
                else:
                    self.program.action_points -= 1 # Waste AP logic for sim simplicity
            
            # Focus Research
            else:
                target = random.choice(list(self.program.star_systems.keys()))
                self.program.focus_research(target)
                # self.log(f"Focused research on {target}")

    def run(self):
        print(f"Starting Run {self.run_id} ({self.strategy})...")
        while not self.program.game_over and self.program.generation < 200:
            self.make_decisions()
            self.program.advance_generation()
            
            # Log critical integration events
            if self.program.generation % 20 == 0:
                status = self.program.integration.get_integration_status()
                self.log(f"Gen {self.program.generation} Stats: "
                         f"Integ={status['level']:.2f}, "
                         f"Risk={self.program.self_destruct_risk:.3f}, "
                         f"Supp={self.program.public_support:.1f}")

        return self.get_summary()

    def get_summary(self):
        status = self.program.integration.get_integration_status()
        return {
            "run_id": self.run_id,
            "generations": self.program.generation,
            "victory": self.program.victory,
            "philosophical_victory": self.program.philosophical_victory,
            "end_message": self.program.message.split('\n')[0],
            "integration_level": status['level'],
            "integration_status": status['status'],
            "tech_level": self.program.tech_level,
            "seeded_worlds": len(self.program.genesis.seeded_worlds),
            "contacts": len([s for s in self.program.star_systems.values() if len(s.received_messages) > 0]),
            "swan_songs_found": sum(1 for s in self.program.star_systems.values() if s.is_extinct and self.program.swan_song_manager.is_discovered([k for k,v in self.program.star_systems.items() if v==s][0]))
        }

def main():
    results = []
    strategies = ["balanced", "aggressive", "cautious", "balanced", "aggressive"]
    
    print("\n=== STARTING AUTOMATED PLAYTEST SUITE (5 RUNS) ===\n")
    
    for i in range(5):
        player = AutoPlayer(i+1, strategies[i])
        result = player.run()
        results.append(result)
        print(f"Run {i+1} Correctly Finished: {result['end_message']}")
        print("-" * 50)

    # Print Report
    print("\n\n=== PLAYTEST SUMMARY REPORT ===")
    print(f"{'Run':<4} {'Gen':<5} {'Victory':<8} {'Integ%':<7} {'Seeded':<7} {'Contacts':<9} {'Swan':<5} {'End Reason'}")
    print("-" * 80)
    for r in results:
        vic_str = "YES" if r['victory'] else "NO"
        if r['philosophical_victory']: vic_str = "PHIL"
        
        print(f"{r['run_id']:<4} {r['generations']:<5} {vic_str:<8} {r['integration_level']:.2f}    {r['seeded_worlds']:<7} {r['contacts']:<9} {r['swan_songs_found']:<5} {r['end_message'][:30]}...")

if __name__ == "__main__":
    main()
