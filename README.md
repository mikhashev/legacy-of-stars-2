# Legacy of Stars

![Legacy of Stars Banner](media/legacy_of_stars_v2_variant_1_1280x640_small.jpg)

## Overview
Legacy of Stars is a turn-based strategy game about humanity's multi-generational effort to establish contact with alien civilizations. As the overseer of Earth's interstellar communication program, you'll make decisions that span centuries, with each turn representing approximately 25 years of human history.

Inspired by the "Dark Forest" theory and realistic interstellar communication challenges, the game explores what it would truly mean to reach out across the cosmic void when message travel times are measured in generations, not minutes.

## Key Features

### Core Gameplay
- **Realistic Light-Speed Communication**: Messages take years or decades to reach their destination and return
- **Generational Management**: Each turn introduces a new program director with different skills and personality traits
- **Dark Forest Theory**: Hidden alien strategies (Silent, Benign, Cautious, Aggressive, Deceptive)
- **Multiple Victory Conditions**: Contact Victory (3+ civilizations) or Philosophical Victory (answer the Fermi Paradox)

### Advanced Systems
- **WOW! Signal Event**: Opening scenario with 144-generation consequence (1977 → Year 3577)
- **Attack Early Warning**: Light-speed travel time gives you generations to prepare for hostile fleets
- **AI Strategic Advisor**: Context-aware recommendations for navigating the Dark Forest
- **Swan Song Messages**: Discover final transmissions from extinct civilizations
- **Passive Signal Leakage**: Your broadcasts can be detected by hostile civilizations
- **Philosophical Crisis Events**: Mid-game existential choices about humanity's evolution
- **Integration Progress**: Track biological-technological merging to survive the Great Filter
- **Genesis Project**: Seed sterile worlds with Earth life

### Technology Tree
- **41 technologies** across 5 tiers (1977 to Year 2475+)
- Historically accurate SETI projects (Arecibo, SETI@Home, Breakthrough Listen, SKA)
- Generation-gated unlocking based on realistic timelines
- Doctrine choices with meaningful consequences

## Game Mechanics

- **Sending Messages**: Compose and transmit messages to potentially habitable star systems
- **Listening for Signals**: Focus research on promising star systems to detect civilization signatures
- **Public Outreach**: Conduct campaigns to maintain public support and funding
- **Technological Development**: Advance your capabilities over generations
- **Knowledge Base**: Build a comprehensive understanding of other civilizations
- **Defensive Actions**: Deploy countermeasures against incoming hostile fleets

## Victory and Failure

### Victory Conditions
- **Contact Victory**: Establish two-way communication with at least 3 different alien civilizations
- **Philosophical Victory**: Collect 15+ pieces of Fermi Paradox evidence from:
  - Extinct civilization discoveries (swan songs)
  - Hostile encounters (Dark Forest evidence)
  - Peaceful contacts (cooperation evidence)
  - Transcendence technologies (Great Filter evidence)

### Failure Conditions
- **Defunding**: Program termination due to lack of funding or public support
- **Self-Destruction**: Humanity destroys itself through internal conflict (mitigated by Integration Progress)
- **Annihilation**: Destruction by hostile civilization (unless Backup Colonies established)

## Scientific Foundation

Legacy of Stars is built on real scientific principles:
- Star systems based on actual nearby stars in our stellar neighborhood
- Communication delays calculated using actual light-speed travel times
- Civilization detection probabilities reflect realistic technological challenges
- Generational time scales acknowledge the true duration of interstellar contact
- SETI projects and technologies based on real historical initiatives

## Project Structure

```
legacy-of-stars/
├── src/                         # Core game source code
│   ├── legacy_of_stars_v3.py    # Main game engine (current version)
│   ├── ai_manager.py            # AI integration system
│   ├── ai_strategic_advisor.py  # Context-aware recommendations
│   ├── wow_signal_event.py      # Ultra-long-term legacy system
│   ├── attack_warning.py        # Hostile civilization warnings
│   ├── swan_song_messages.py    # Extinct civilization data
│   ├── passive_leakage.py       # Signal detection mechanics
│   ├── integration_progress.py  # Bio-tech integration tracking
│   ├── philosophical_events.py  # Mid-game crisis events
│   └── genesis_project.py       # Seeding new civilizations
│
├── tests/                       # Comprehensive test suite
│   └── test_*.py                # Unit and integration tests
│
├── data/                        # Game data files
│   ├── tech_tree.json           # 41 technologies across 5 tiers
│   └── llm_providers.json       # AI provider configurations
│
├── docs/                        # Documentation
│   ├── development_roadmap.md   # Development phases and status
│   ├── design_notes.md          # 11 foundational design principles
│   ├── phase_2a_complete.md     # Phase 2A completion report
│   └── implementation guides    # Feature documentation
│
└── README.md                    # This file
```

## Installation

```bash
git clone https://github.com/mikhashev/legacy-of-stars.git
cd legacy-of-stars
python3 src/legacy_of_stars_v3.py
```

## Requirements
- Python 3.6 or higher
- (Optional) Ollama, Claude, or OpenAI API keys for AI-enhanced features

## Development Status

**Current Version:** Feature-complete with all major systems implemented
- ✅ Phase 1+1b: Dark Forest Core
- ✅ Phase 2A: Historical Foundation (WOW! Signal, Attack Warning, Tech Tree, AI Advisor)
- ✅ Phase 2B: Content & Discovery (Swan Songs, Passive Leakage)
- ✅ Phase 2C: Polish & Player Experience
- ✅ Phase 3A: Philosophical Depth (Integration Progress, Events, Victory)
- ✅ Phase 3B: Genesis Project

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Credits

- Developed by [Mike Shevchenko](https://github.com/mikhashev)
- Concept inspired by:
  - Scientific principles of interstellar communication
  - [@SETIInstitute](@SETIInstitute) research
  - [WOW! Signal](https://en.wikipedia.org/wiki/Wow!_signal)
  - Liu Cixin's "Dark Forest" theory
- Implementation created using [Personal Context Technology](https://github.com/mikhashev/personal-context-manager/blob/main/use-cases/game-development/README.md)
