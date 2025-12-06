"""
Phase 3A Playtest Script
Simulates a game run to verify philosophical depth mechanics.
"""

import sys
from pathlib import Path
import random
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    filename='logs/playtest_phase3a.log',
    filemode='w'
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger('').addHandler(console)

# Add root directory to path
root_path = Path(__file__).parent.parent
sys.path.insert(0, str(root_path))

from src.legacy_of_stars_v3 import ContactProgram

def run_playtest():
    print("Initializing Phase 3A Playtest...")
    game = ContactProgram()
    
    # Verify Initialization
    print(f"\nIntegration System Initialized: {hasattr(game, 'integration')}")
    print(f"Philosophical Events Initialized: {hasattr(game, 'philosophical_events')}")
    print(f"Fermi Evidence Initialized: {hasattr(game, 'fermi_evidence')}")
    
    # Check Civilization Types
    print("\nChecking Civilization Types:")
    living_count = 0
    types = {}
    for name, system in game.star_systems.items():
        if system.has_civilization:
            ctype = system.civilization_type
            status = "Extinct" if system.is_extinct else "Living"
            print(f"  {name}: {status} - {ctype}")
            
            if not system.is_extinct:
                living_count += 1
                types[ctype] = types.get(ctype, 0) + 1
    
    # Simulate Generations
    print("\nSimulating 60 Generations...")
    
    # Cheat: Give some resources to survive
    game.public_support = 100
    game.funding = 100
    game.research_points = 5000  # For buying techs
    
    for i in range(1, 61):
        print(f"\n--- Gen {i} ---")
        
        # 1. Research Integration Techs (Cheat)
        if i == 10:
            print(">> Researching Bio-Engineering Foundation")
            game.technologies["bio_engineering"].researched = True
        elif i == 15:
            print(">> Researching Synthetic Biology")
            tech = game.technologies["synthetic_biology"]
            tech.researched = True
            game._apply_tech_special_effect(tech)
        elif i == 25:
             print(">> Researching Neural Interface")
             tech = game.technologies["neural_interface"]
             tech.researched = True
             game._apply_tech_special_effect(tech)
        
        # 2. Advance Generation
        game.advance_generation()
        
        # 3. Check Integration Status
        status = game.integration.get_integration_status()
        print(f"Integration: {status['level']:.1%} ({status['status']})")
        print(f"Risk Modifier: {status['filter_risk_modifier']}x")
        
        # 4. Handle Philosophical Events
        if game.pending_philosophical_event:
            event = game.pending_philosophical_event
            print(f"!!! EVENT TRIGGERED: {event.name}")
            print(f"  Desc: {event.description[:50]}...")
            
            # Make a random choice
            choice_idx = random.randint(0, len(event.choices)-1)
            choice = event.choices[choice_idx]
            print(f"  >> CHOOSING: {choice['name']}")
            
            msg = game.philosophical_events.apply_choice_effects(event, choice_idx, game)
            print(f"  Result: {msg}")
            
            game.pending_philosophical_event = None
    
    # Final Status
    print("\n=== Playtest Complete ===")
    print("Final Fermi Evidence:")
    for key, val in game.fermi_evidence.items():
        print(f"  {key}: {val}")
    
    print(f"Philosophical Victory: {game.philosophical_victory}")

if __name__ == "__main__":
    run_playtest()
