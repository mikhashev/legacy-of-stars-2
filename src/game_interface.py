"""
Console interface for Legacy of Stars.

The engine (ContactProgram) knows nothing about the terminal.  This module
renders engine state, asks the player for input and calls engine actions.
Menu entries are derived from ContactProgram.available_actions(), so the same
action list can drive a different front-end later.
"""
import logging
import math
import os
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from . import save_manager
from .console import QuitGame, read_input
from .genesis_project import ark_arrival_generation
from .legacy_of_stars_v3 import ContactProgram
from .summary import build_summary
from .ui_text import HELP_TEXT

# Fixed hotkeys for the core actions; everything else is numbered dynamically from 7.
CORE_ACTION_KEYS = {
    "send_message": "1",
    "focus_research": "2",
    "public_outreach": "3",
    "research_tech": "4",
    "advance_generation": "5",
}
QUIT_KEY = "6"

ACTION_ICONS = {
    "defend": "🛡️ ",
    "consult_advisor": "🤖 ",
    "listen_swan_song": "🕊️ ",
    "genesis_seed": "🌱 ",
    "respond_event": "🤔 ",
}


@dataclass
class MenuItem:
    key: str
    label: str
    handler: Callable[[], None]
    aliases: tuple = ()


class GameInterface:
    """Handles game display and player input."""

    def __init__(self, program: Optional[ContactProgram] = None, clear_screen: Optional[bool] = None):
        self.program = program if program is not None else ContactProgram()
        if clear_screen is None:
            clear_screen = os.getenv("LOS_CLEAR_SCREEN") == "1"
        self.clear_screen = clear_screen
        self._current_keys: Dict[str, str] = {}
        self._handlers: Dict[str, Callable[[], None]] = {
            "send_message": self._act_send_message,
            "focus_research": self._act_focus_research,
            "public_outreach": self._act_public_outreach,
            "research_tech": self._act_research_tech,
            "advance_generation": self._act_advance,
            "defend": self._act_defense,
            "consult_advisor": self._act_advisor,
            "listen_swan_song": self._act_swan_song,
            "genesis_seed": self._act_genesis,
            "respond_event": self._act_philosophical,
        }

    # ------------------------------------------------------------------ helpers
    def _ai_available(self) -> bool:
        return self.program.ai_available()

    def _year(self, generation: int) -> int:
        return self.program.start_year + (generation - 1) * 25

    def _prompt_index(self, prompt: str, count: int) -> Optional[int]:
        """Ask for a 1-based number; return a 0-based index, or None for cancel/invalid."""
        raw = read_input(prompt)
        try:
            number = int(raw)
        except ValueError:
            self.program.message = "Please enter a valid number."
            return None
        if number == 0:
            return None
        if 1 <= number <= count:
            return number - 1
        self.program.message = f"Invalid selection. Enter a number from 1 to {count} (or 0 to cancel)."
        return None

    def _system_names(self) -> List[str]:
        return list(self.program.star_systems.keys())

    # ------------------------------------------------------------------ opening
    def run_opening_scenario(self) -> None:
        """WOW! Signal decision at game start (Gen 1, 1977)."""
        wow = self.program.wow_signal
        if wow.decided:
            return

        print("\n" + "=" * 70)
        print("LEGACY OF STARS")
        print("=" * 70)
        print("\nAugust 15, 1977 - 23:16 EDT")
        print("Big Ear Radio Telescope, Ohio State University")
        print("\nThe automated receiver records a 72-second burst at 1420 MHz.")
        print("\nSignal intensity: 6EQUJ5 (30x background noise)")
        print("Direction: Sagittarius (Chi Sagittarii region)")
        print("Distance: ~1,800 light-years (disputed estimate)")
        print("\nThree days later, reviewing the printout, Dr. Jerry Ehman circles")
        print("six characters and writes: 'Wow!'")
        print("\nThis signal will never repeat.")
        print("You must decide Earth's response.")
        print("\n" + "=" * 70)
        print("CRITICAL DECISION")
        print("=" * 70)
        print("\nDo you authorize a reply transmission?")
        print("\n1. YES - Send Reply")
        print("   • Message travels 72 generations (1,800 LY)")
        print(f"   • Response/attack arrives Gen 144 (Year {self._year(144)})")
        print("   • Immediate: +100 RP, +10% Support")
        print("   • Warning: Unknown consequences")
        print("\n2. NO - Stay Silent")
        print("   • Earth remains hidden")
        print("   • Immediate: -15% attack damage (permanent)")
        print("   • WOW! mystery unsolved")
        print("\nNote: Most players won't reach Gen 144")
        print("This is your legacy decision.")
        print("=" * 70)

        while True:
            choice = read_input("\nYour decision (1 or 2): ")
            if choice in ("1", "2"):
                break
            print("Please enter 1 or 2")

        if choice == "1":
            message = self._compose_wow_reply()
            wow.reply(message)
            sent = wow.wow_reply_message
            print("\n" + "=" * 70)
            print("November 1977 - Reply Transmitted")
            print("=" * 70)
            print(f"\nMessage: \"{sent[:100]}{'...' if len(sent) > 100 else ''}\"")
            print("\nTarget: Chi Sagittarii region (~1,800 LY)")
            print(f"ETA: Generation 72 (Year {self._year(72)})")
            print(f"Response ETA: Generation 144 (Year {self._year(144)})")
            print("\nThe die is cast. Future generations will learn the truth.")
            print("\n+100 Research Points")
            print("+10% Public Support")
            print("=" * 70)
        else:
            wow.stay_silent()
            print("\n" + "=" * 70)
            print("November 1977 - Silence Maintained")
            print("=" * 70)
            print("\nEarth chooses caution over contact.")
            print("The WOW! Signal remains unexplained.")
            print("Humanity stays hidden in the dark.")
            print("\nDefensive Mindset: -15% attack damage (permanent)")
            print("\nAchievement Unlocked: Silent Wisdom")
            print("=" * 70)

        read_input("\nPress Enter to begin your mission...")

    def _compose_wow_reply(self) -> str:
        """Let the player compose Earth's reply; empty string means the standard message."""
        print("\n" + "=" * 70)
        print("COMPOSE EARTH'S FIRST INTERSTELLAR MESSAGE")
        print("=" * 70)
        print("\nYou are composing humanity's reply to the WOW! Signal.")
        print("This message will travel 1,800 light-years to Chi Sagittarii.")
        print("\nInspiration: The 1974 Arecibo Message included:")
        print("  • Numbers 1-10, atomic numbers of key elements")
        print("  • DNA structure, human form")
        print("  • Earth's population, solar system position")
        print("\nWhat message should Earth send?")
        print("1. Compose custom message")
        print("2. Let the Director draft the message")
        print("3. Use Standard Format (Default)")
        print("-" * 70)

        msg_choice = read_input("\nChoose option (1-3): ")
        if msg_choice == "1":
            print("(Max 500 chars)")
            return read_input("Message: ")[:500]
        if msg_choice == "2":
            generated = self.program.compose_director_message()
            print(f"\nDraft: \"{generated}\"")
            confirm = read_input("Use this message? (y/n): ")
            if confirm.lower() == "y":
                return generated
        return ""

    # ------------------------------------------------------------------ display
    def display_game(self) -> None:
        """Display the game state (rendered from the engine's public view)."""
        p = self.program
        state = p.view_state()
        if self.clear_screen:
            os.system("cls" if os.name == "nt" else "clear")

        director = state["director"]
        skills = director["skills"]
        status = state["status"]
        print(f"\n=== LEGACY OF STARS: Generation {state['generation']} (Year {state['year']}) ===")
        print(f"Director: {director['name']}")
        print(f"Traits: {', '.join(director['traits'])}")
        print(f"Skills: Diplomacy {int(skills['diplomacy'] * 100)}%, Science {int(skills['science'] * 100)}%, "
              f"Administration {int(skills['administration'] * 100)}%")

        print("\nProgram Status:")
        print(f"  Action Points: {status['action_points']}/{status['max_action_points']}")
        print(f"  Funding: {int(status['funding'])}%")
        print(f"  Public Support: {int(status['public_support'])}%")
        print(f"  Knowledge Base: {int(status['knowledge_base'])}%")
        print(f"  Research Points: {status['research_points']} (+{int(status['passive_rp'])}/turn)")
        print(f"  Tech Level: {status['tech_level']}  |  Leakage front: {status['broadcast_radius']:.0f} LY")
        print(f"  Self-Destruct Risk: {status['self_destruct_risk'] * 100:.1f}%  |  "
              f"Ecological Risk: {status['ecological_risk'] * 100:.1f}%")
        print(f"  Integration: {status['integration_level']:.0%} - {status['integration_status']}")
        evidence = state["fermi_evidence"]
        print(f"  Contacts: {state['contacts']}/{state['contacts_goal']}  |  "
              f"Fermi Evidence: {evidence['total']}/{evidence['goal']}")
        if state["active_doctrines"]:
            print(f"  Active Doctrines: {', '.join(state['active_doctrines'])}")
        if state["genesis"]["unlocked"]:
            print(f"  {state['genesis']['summary']}")

        if p.message:
            print(f"\n{p.message}")
            p.message = ""

        events = p.drain_events()
        if events:
            print()
            for event in events:
                print(event.text)
                print()

        if state["pending_event"]:
            print(p.get_philosophical_event_display())

        if state["threats"]:
            print("\n⚠️⚠️⚠️ === ACTIVE THREATS === ⚠️⚠️⚠️")
            for threat in state["threats"]:
                print(f"\n{threat['index']}. {threat['type_label'].upper()} from {threat['source']}")
                print(f"   Source Distance: {threat['source_distance']} LY")
                print(f"   ETA: {threat['eta']} generations (Year {threat['arrival_year']})")
                print(f"   Enemy Tech: {threat['enemy_stage']}")
                print(f"   Current Defense: {threat['defense_pct']}% damage reduction")
                if threat["actions_taken"]:
                    print(f"   Actions Taken: {', '.join(threat['actions_taken'])}")
                else:
                    print("   ⚠️ NO DEFENSES DEPLOYED YET!")
            print()

        catalog = state["catalog"]
        print(f"\n=== Star Systems ({catalog['known']} of {catalog['total']} catalogued, "
              f"{catalog['discovery_chance']:.0%} chance of a new one each generation) ===")
        for s in state["systems"]:
            kind = f", {s['spectral_type']}" if s.get("spectral_type") else ""
            flags = " 🌱" if s["is_seeded"] else ""
            print(f"{s['index']}. {s['name']} ({s['distance']} LY{kind}) - Knowledge {s['knowledge']}%{flags}")
            if s["description"]:
                print(f"   {s['description']}")
            if s["messages_sent"]:
                last = s["messages_sent"][-1]
                print(f"   Messages sent: {len(s['messages_sent'])} (last Gen {last['generation']}, "
                      f"arrives Gen {last['arrival_gen']})")
            if s["responses"]:
                latest = s["responses"][-1]
                excerpt = latest if len(latest) <= 90 else latest[:87] + "..."
                print(f"   Replies: {len(s['responses'])}  > \"{excerpt}\"")
            if s["next_response_gen"] is not None:
                print(f"   Next reply expected: Generation {s['next_response_gen']}")
        print()

    def print_intro(self) -> None:
        print("\n=== LEGACY OF STARS ===")
        print("You are the overseer of Earth's multi-generational interstellar contact program.")
        print("Your mission is to establish communication with alien civilizations across the stars.")
        print("Each turn represents a generation (~25 years) of human history.")
        print("Make wise decisions to ensure the program's longevity and success.\n")
        print("Win by establishing contact (receiving responses) from at least 3 civilizations,")
        print("or by gathering 15 pieces of evidence that answer the Fermi Paradox.")
        print("Type h at any prompt of the main menu for the full rules.")

    # ------------------------------------------------------------------ menu
    def build_menu(self) -> List[MenuItem]:
        p = self.program
        specs = p.available_actions()
        by_id = {spec.id: spec for spec in specs}
        items: List[MenuItem] = []
        keys: Dict[str, str] = {}

        for action_id, key in CORE_ACTION_KEYS.items():
            spec = by_id[action_id]
            label = f"{spec.label} ({spec.cost})" if spec.cost else spec.label
            items.append(MenuItem(key, label, self._handlers[action_id]))
            keys[action_id] = key

        items.append(MenuItem(QUIT_KEY, "Quit Game", self._act_quit, aliases=("q", "quit")))
        items.append(MenuItem("v", "View system dossier", self._act_view_system, aliases=("view", "dossier")))
        items.append(MenuItem("s", "Save game", self._act_save, aliases=("save",)))
        items.append(MenuItem("h", "Help", self._act_help, aliases=("?", "help")))

        next_key = 7
        for spec in specs:
            if spec.id in CORE_ACTION_KEYS:
                continue
            label = ACTION_ICONS.get(spec.id, "") + spec.label
            if spec.cost:
                label += f" ({spec.cost})"
            if spec.id == "consult_advisor" and p.advisor_consulted_this_gen:
                label += " ✓"
            items.append(MenuItem(str(next_key), label, self._handlers[spec.id]))
            keys[spec.id] = str(next_key)
            next_key += 1

        self._current_keys = keys
        return items

    def render_menu(self, items: List[MenuItem]) -> None:
        print("\nActions:")
        letters = []
        for item in items:
            if item.key.isdigit():
                print(f"{item.key}. {item.label}")
            else:
                letters.append(f"{item.key} = {item.label}")
        if letters:
            print("   " + "  |  ".join(letters))

    def dispatch(self, choice: str, items: List[MenuItem]) -> None:
        lookup: Dict[str, MenuItem] = {}
        for item in items:
            lookup[item.key] = item
            for alias in item.aliases:
                lookup[alias] = item
        item = lookup.get(choice.strip().lower())
        if item is None:
            valid = ", ".join(i.key for i in items)
            self.program.message = f"Invalid choice '{choice}'. Valid options: {valid}."
            return
        item.handler()

    # ------------------------------------------------------------------ actions
    def _act_send_message(self) -> None:
        names = self._system_names()
        idx = self._prompt_index("Enter star system number (0 to cancel): ", len(names))
        if idx is None:
            return
        text = read_input("Enter message content: ")
        self.program.send_message(names[idx], text)

    def _act_focus_research(self) -> None:
        names = self._system_names()
        idx = self._prompt_index("Enter star system number to research (0 to cancel): ", len(names))
        if idx is None:
            return
        self.program.focus_research(names[idx])

    def _act_public_outreach(self) -> None:
        self.program.public_outreach()

    def _act_research_tech(self) -> None:
        techs = self.program.available_technologies()
        if not techs:
            self.program.message = "No new technologies available to research."
            return
        print("\nAvailable Research (by Tier):")
        for i, tech in enumerate(techs, 1):
            lock = self.program.tech_lock_reason(tech)
            marker = f"  [LOCKED: {lock}]" if lock else ""
            print(f"{i}. [T{tech.tier}] {tech.name} ({tech.cost} RP){marker}")
            print(f"   {tech.description}")
            print(f"   {tech.year_context}")
        idx = self._prompt_index("Enter tech number to research (or 0 to cancel): ", len(techs))
        if idx is None:
            return
        tech = techs[idx]
        needs_doctrine = self.program.research_tech(tech.id)
        if needs_doctrine and tech.doctrine_choice:
            self._choose_doctrine(tech)

    def _choose_doctrine(self, tech) -> None:
        doctrine = tech.doctrine_choice
        options = doctrine["options"]
        print(f"\n*** DOCTRINE CHOICE REQUIRED: {doctrine['name']} ***")
        print(doctrine["description"])
        for i, option in enumerate(options, 1):
            print(f"{i}. {option['name']}: {option['description']}")
        idx = self._prompt_index(f"Choose doctrine (1-{len(options)}): ", len(options))
        if idx is None:
            print("Defaulting to the first option.")
            idx = 0
        self.program.choose_doctrine(tech.id, idx)

    def _act_advance(self) -> None:
        if self.program.pending_philosophical_event:
            key = self._current_keys.get("respond_event", "?")
            self.program.message = (
                "A philosophical crisis demands a decision before this generation can end "
                f"(menu option {key})."
            )
            return
        self.program.advance_generation()
        if not self.program.game_over:
            self._autosave()

    def _autosave(self) -> None:
        try:
            save_manager.autosave(self.program)
        except OSError as exc:  # a failed autosave must never stop the game
            logging.warning(f"Autosave failed: {exc}")

    def _act_help(self) -> None:
        print(HELP_TEXT)
        print(f"AI text generation: {self.program.ai.describe()}")
        read_input("\nPress Enter to return to the game...")

    def _act_view_system(self) -> None:
        state = self.program.view_state()
        systems = state["systems"]
        idx = self._prompt_index("Enter star system number for its dossier (0 to cancel): ", len(systems))
        if idx is None:
            return
        s = systems[idx]
        line = "-" * 60
        print(f"\n{line}\nDOSSIER: {s['name']}\n{line}")
        coords = ""
        if s.get("ra") is not None and s.get("dec") is not None:
            coords = f"  |  RA {s['ra']:.1f}°, Dec {s['dec']:+.1f}°"
        print(f"Distance: {s['distance']} light-years  |  Type: {s.get('spectral_type') or 'unknown'}{coords}")
        print(f"Signal round trip: {s['round_trip_generations']} generation(s)")
        print(f"Knowledge: {s['knowledge']}%  -  {s['description'] or 'nothing studied yet'}")
        if s["is_seeded"]:
            print("Genesis Ark Program: an ark from Earth is on its way to this world, or already landed.")
        print(f"\nAssessment: {self.program.ai_advisor.get_system_risk_assessment(self.program, s['name'])}")
        if s["messages_sent"]:
            print(f"\nMessages sent ({len(s['messages_sent'])}):")
            for entry in s["messages_sent"]:
                print(f"  Gen {entry['generation']} (arrives Gen {entry['arrival_gen']}): \"{entry['text']}\"")
        if s["responses"]:
            print(f"\nReplies received ({len(s['responses'])}):")
            for i, text in enumerate(s["responses"], 1):
                print(f"  {i}. \"{text}\"")
        if s["next_response_gen"] is not None:
            print(f"\nA reply is on its way; expected in Generation {s['next_response_gen']}.")
        threats = [t for t in state["threats"] if t["source"] == s["name"]]
        for threat in threats:
            print(f"\n⚠️ {threat['type_label']} inbound: ETA {threat['eta']} generation(s), "
                  f"defense {threat['defense_pct']}%")
        print(line)
        read_input("\nPress Enter to return to the game...")

    def _act_save(self) -> None:
        name = read_input("Save name (Enter for 'quicksave', 0 to cancel): ")
        if name == "0":
            return
        try:
            path = save_manager.save_game(self.program, save_manager.save_path(name or "quicksave"))
        except OSError as exc:
            self.program.message = f"Could not save the game: {exc}"
            return
        self.program.message = f"💾 Game saved to {path.name} (Generation {self.program.generation})."

    def _act_quit(self) -> None:
        confirm = read_input("Are you sure you want to quit? (y/n): ")
        if confirm.lower() == "y":
            self.program.game_over = True
            self.program.game_over_reason = "The overseer closed the program."

    def _act_defense(self) -> None:
        warnings = self.program.pending_attack_warnings
        if not warnings:
            self.program.message = "No active threats."
            return
        print("\n⚠️ === DEFENSIVE ACTIONS MENU === ⚠️")
        for i, warning in enumerate(warnings, 1):
            etas = warning.get_etas_remaining(self.program.generation)
            print(f"{i}. Defend against {warning.source.name} "
                  f"(ETA: {etas} gens, Defense: {warning.get_defense_percentage()}%)")
        idx = self._prompt_index("\nSelect threat to defend against (or 0 to cancel): ", len(warnings))
        if idx is None:
            return
        warning = warnings[idx]
        print(f"\nDefensive options for {warning.source.name}:")
        print("1. 🛡️ Emergency Defense Protocol (ALL AP, 50% reduction)")
        print("2. 🚀 Evacuate Critical Infrastructure (1 AP, 30% reduction)")
        print("3. 📡 Attempt Diplomatic Contact (1 AP, small chance to abort)")
        choice = read_input("\nChoose defensive action (1-3, or 0 to cancel): ")
        if choice == "1":
            self.program.defend_emergency(idx)
        elif choice == "2":
            self.program.defend_evacuate(idx)
        elif choice == "3":
            self.program.defend_diplomacy(idx)
        elif choice != "0":
            self.program.message = "Invalid defensive action choice."

    def _act_advisor(self) -> None:
        if self._ai_available() and not self.program.advisor_consulted_this_gen:
            print("\n🤖 Analyzing game state... please wait.")
        self.program.consult_advisor()

    def _act_swan_song(self) -> None:
        names = self.program.undiscovered_swan_songs()
        if not names:
            self.program.message = "No undiscovered transmissions."
            return
        print("\n🕊️ === SWAN SONG DISCOVERY === 🕊️")
        print("\nExtinct civilizations with undiscovered transmissions:")
        for i, name in enumerate(names, 1):
            system = self.program.star_systems[name]
            print(f"{i}. {name} ({system.distance:.1f} LY) - Knowledge: {int(system.knowledge)}%")
            if system.knowledge < 30:
                print(f"   ⚠️ Need 30%+ knowledge to detect artifacts (currently {int(system.knowledge)}%)")
        idx = self._prompt_index("\nSelect system to scan (or 0 to cancel): ", len(names))
        if idx is None:
            return
        print(f"\n📡 Scanning for ancient transmissions from {names[idx]}...")
        self.program.listen_for_swan_song(names[idx])

    def _act_genesis(self) -> None:
        p = self.program
        print("\n🌱 === GENESIS PROJECT === 🌱")
        print(f"Cost to seed a world: {p.genesis.seed_cost_rp} RP, {p.genesis.seed_cost_funding}% Funding")
        sterile = [p.star_systems[name] for name in p.genesis_targets()]
        if not sterile:
            p.message = "No habitable sterile worlds available for an ark."
            return
        print("Habitable sterile worlds within reach (arrival at 0.12c):")
        for i, system in enumerate(sterile, 1):
            arrival = ark_arrival_generation(p.generation, system.distance)
            print(f"{i}. {system.name} ({system.distance:.1f} LY, {system.spectral_type or 'unknown'}) "
                  f"- lands Generation {arrival} (Year {self._year(arrival)})")
        idx = self._prompt_index("\nSelect system to seed (or 0 to cancel): ", len(sterile))
        if idx is None:
            return
        _success, msg = p.genesis.seed_world(p, sterile[idx])
        p.message = msg

    def _act_philosophical(self) -> None:
        event = self.program.pending_philosophical_event
        if event is None:
            self.program.message = "No philosophical event is pending."
            return
        print(f"\n🤔 === PHILOSOPHICAL EVENT: {event.name} === 🤔")
        for i, choice in enumerate(event.choices, 1):
            print(f"{i}. {choice['name']}")
            print(f"   {choice['description']}")
            print()
        idx = self._prompt_index(
            f"Choose your response (1-{len(event.choices)}, or 0 to postpone): ", len(event.choices)
        )
        if idx is None:
            if not self.program.message:
                self.program.message = "Philosophical event postponed. It stays pending until you respond."
            return
        self.program.handle_philosophical_event_choice(idx)

    # ------------------------------------------------------------------ loop
    def play(self) -> None:
        """Main game loop"""
        self.print_intro()
        try:
            read_input("\nPress Enter to begin...")
            while not self.program.game_over:
                self.display_game()
                items = self.build_menu()
                self.render_menu(items)
                choice = read_input("\nEnter your choice: ")
                self.dispatch(choice, items)
        except QuitGame:
            logging.info("Game closed by the player (EOF/Ctrl+C)")
            if not self.program.game_over:
                self._autosave()
            print("\nGame closed. Progress is in the autosave.")
            return

        self.show_ending()

    def show_ending(self) -> None:
        p = self.program
        events = p.drain_events()
        if events:
            print()
            for event in events:
                print(event.text)
                print()
        print(build_summary(p))
        if p.victory or p.philosophical_victory:
            logging.info("GAME OVER: VICTORY")
        else:
            logging.info(f"GAME OVER: {p.game_over_reason}")
        print("\nThank you for playing Legacy of Stars!")
        try:
            read_input("\nPress Enter to exit...")
        except QuitGame:
            pass


def start_menu() -> Optional[GameInterface]:
    """New game / load game / quit. Returns an interface ready to play, or None to exit."""
    while True:
        saves = save_manager.list_saves()
        print("\n=== LEGACY OF STARS ===")
        print("1. New Game")
        if saves:
            print(f"2. Load Game ({len(saves)} saved)")
        print("3. Quit")
        choice = read_input("\nChoose (1-3): ")
        if choice == "1":
            return GameInterface(ContactProgram())
        if choice == "2" and saves:
            print("\nSaved games (newest first):")
            for i, info in enumerate(saves, 1):
                status = " [finished]" if info.game_over else ""
                print(f"{i}. {info.name} - Generation {info.generation} (Year {info.year}), "
                      f"Director {info.director}, saved {info.saved_at[:16].replace('T', ' ')}{status}")
            raw = read_input("\nLoad which save (0 to go back): ")
            try:
                index = int(raw)
            except ValueError:
                print("Please enter a number.")
                continue
            if index == 0:
                continue
            if not 1 <= index <= len(saves):
                print("No such save.")
                continue
            info = saves[index - 1]
            if info.game_over:
                print("That game is already over; start a new one instead.")
                continue
            try:
                program = save_manager.load_game(info.path)
            except save_manager.SaveError as exc:
                print(f"Could not load {info.name}: {exc}")
                continue
            print(f"\nLoaded {info.name}: Generation {program.generation}, Director {program.current_director.name}.")
            return GameInterface(program)
        if choice in ("3", "q", "quit"):
            return None
        print("Please choose 1, 2 or 3.")
