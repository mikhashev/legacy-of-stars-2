"""
Static texts for the console interface: the help screen.
"""
from .legacy_of_stars_v3 import CONTACT_VICTORY_GOAL

_NUMBER_WORDS = {3: "three", 4: "four", 5: "five"}
_CONTACT_VICTORY_GOAL_WORD = _NUMBER_WORDS.get(CONTACT_VICTORY_GOAL, str(CONTACT_VICTORY_GOAL))

HELP_TEXT = f"""
================================================================
LEGACY OF STARS - HOW TO PLAY
================================================================

THE PROGRAM
  You oversee Earth's interstellar contact program from 1977 onward. Each turn is one
  generation (~25 years) with a new director whose skills modify your actions:
  Diplomacy (message quality), Science (research cost, focus research), Administration
  (outreach and funding).

ACTION POINTS (AP)
  Base 2 per generation; +1 with Public Support above 70%, +1 with Funding above 70%,
  +1 with an efficient director. Events may change the pool permanently.
  Send Message, Focus Research, Public Outreach, Listen for Swan Song and Genesis
  seeding cost 1 AP each. Researching technology is free. Emergency Defense costs all AP.

ACTIONS
  Send Message      Address a star system. Replies travel at light speed, so a system
                    12 light-years away answers about one generation later.
  Focus Research    Learn what a system holds (civilization, extinction, nothing).
                    At 20% knowledge a detected civilization boosts support and research.
  Public Outreach   Raise Public Support (and Funding with a good administrator).
                    Support drives funding; Support below 10% or Funding below 20% ends the game.
  Research          Spend Research Points on technologies (five tiers, unlocking by year).
                    Detection techs also catalogue new star systems each generation.
  Defensive Actions Appear when a hostile fleet is inbound: Emergency Defense (-50% damage,
                    all AP), Evacuation (-30%, 1 AP), Diplomacy (1 AP, may turn back a
                    low-deception trap). Fleets travel far slower than light.
  Genesis Seeding   Send an ark to a habitable world with nobody on it. Only systems you have
                    studied to 20% knowledge can be targeted - until then you do not know
                    whether that world is empty, and the program will not aim an ark blind.

WHO IS OUT THERE
  Every civilization follows a hidden strategy. Some only listen and never answer. Some
  broadcast and answer warmly. Some answer cautiously. Some answer with a fleet. And some
  answer warmly first - asking for your position and defenses - and send the fleet later.
  Silence after several messages is a warning sign; so are questions about where you live.

LEAKAGE
  Earth has been broadcasting since the 1930s, and that sphere of leaked signal expands
  one light-year every year: the leakage front. Nothing shrinks it - technology only
  changes how loud we are inside it, and the nearest listeners hear us best. Hostile
  civilizations the front has reached may find you without being contacted. Directional
  Transmission, Radio Silence Protocol, Civilization Cloaking and the Dark Forest
  Protocol quieten us.

INTEGRATION (THE GREAT FILTER)
  Humanity's biology and technology are drifting apart. From Generation 31 low
  integration (below 30%) costs support and research and raises the self-destruct risk,
  which grows every generation until integration passes 70% - then it recedes.
  Transcendence technologies (Bio-Engineering -> Synthetic Biology, Neural Interface,
  Genetic Pacification, Consciousness Upload, Hybrid Civilization) raise integration.
  Tier 5 requires 40% integration.

VICTORY AND DEFEAT
  Contact victory: replies from {_CONTACT_VICTORY_GOAL_WORD} living civilizations.
  Philosophical victory: 15 pieces of Fermi Paradox evidence (swan songs, hostile
  encounters, first replies, integration technologies, resolved philosophical crises,
  Genesis outcomes). Both victories let the game continue.
  Defeat: defunding, self-destruction, or annihilation by a fleet (survivable with 50%+
  damage reduction, Backup Colonies or Emergency Evacuation).

KEYS
  1-6 core actions and quit, 7+ situational actions (defense, advisor, swan songs,
  Genesis, philosophical events), v system dossier, s save, h or ? this help.
  The game autosaves after every generation; load from the start menu.
================================================================
"""
