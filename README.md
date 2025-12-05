# Legacy of Stars

## Overview
Legacy of Stars is a turn-based strategy game about humanity's multi-generational effort to establish contact with alien civilizations. As the overseer of Earth's interstellar communication program, you'll make decisions that span centuries, with each turn representing approximately 25 years of human history.

Unlike most space games focused on physical exploration or conquest, Legacy of Stars explores the realistic challenges of communicating across vast interstellar distances at the speed of light. Your mission is to detect, research, and establish meaningful contact with other intelligent species in nearby star systems.

## Key Features

- **Realistic Light-Speed Communication**: Messages take years or decades to reach their destination and return, creating a unique strategic challenge
- **Generational Management**: Each turn introduces a new program director with different skills and personality traits
- **Multiple Star Systems**: Explore a variety of nearby star systems, each with different distances and potential for harboring intelligent life
- **Technology Progression**: Advance your detection and communication capabilities over generations
- **Public Relations**: Manage public support and funding for your long-term program
- **Scientific Research**: Allocate resources to learn more about detected civilizations
- **Non-Violent Gameplay**: Focus on communication, diplomacy, and scientific discovery rather than conflict

## Game Mechanics

- **Sending Messages**: Compose and transmit messages to potentially habitable star systems
- **Listening for Signals**: Focus research on promising star systems to detect civilization signatures
- **Public Outreach**: Conduct campaigns to maintain public support and funding
- **Technological Development**: Advance your capabilities over generations
- **Knowledge Base**: Build a comprehensive understanding of other civilizations

## Victory and Failure

- **Victory**: Successfully establish two-way communication with at least three different alien civilizations
- **Failure**: Program termination due to lack of funding or public support

## Scientific Foundation

Legacy of Stars is built on real scientific principles:
- Star systems are based on actual nearby stars in our stellar neighborhood
- Communication delays are calculated using actual light-speed travel times
- Civilization detection probabilities reflect realistic technological challenges
- Generational time scales acknowledge the true duration of interstellar contact

## Project Structure

```
legacy-of-stars/
├── src/                    # Core game source code
│   ├── legacy_of_stars_v3.py  # Main game (current version)
│   ├── ai_manager.py
│   ├── ai_strategic_advisor.py
│   ├── attack_warning.py
│   ├── swan_song_messages.py
│   └── wow_signal_event.py
│
├── tests/                  # Test suite
│   └── test_*.py           # Unit and integration tests
│
├── scripts/                # Utility and build scripts
│
├── legacy/                 # Archived legacy versions
│
├── logs/                   # Game and test logs
│
├── data/                   # Game data files
│   ├── tech_tree.json
│   └── llm_providers.json
│
├── docs/                   # Documentation
│   ├── development_roadmap.md
│   ├── design_notes.md
│   └── implementation guides
│
└── README.md              # This file
```

## Installation

```
git clone https://github.com/mikhashev/legacy-of-stars.git
cd legacy-of-stars
python3 src/legacy_of_stars_v3.py
```

## Requirements
- Python 3.6 or higher

## Future Developments

- Enhanced message creation system with content affecting response likelihood
- More detailed civilization types and cultural differences
- Expanded technology tree with specialized research paths
- Graphical user interface with star map visualization
- Extended narrative events and storylines
- Save/load game functionality

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Credits

- Developed by [Mike Shevchenko](https://github.com/mikhashev)
- Concept inspired by scientific principles of interstellar communication and the challenges of generational projects and [@SETIInstitute](@SETIInstitute) researches and [WOW!Signal](https://en.wikipedia.org/wiki/Wow!_signal) and many other thoughts.
- Implementation created by using [Personal Context Technology](https://github.com/mikhashev/personal-context-manager/blob/main/use-cases/game-development/README.md)
