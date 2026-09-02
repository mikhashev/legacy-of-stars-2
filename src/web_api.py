"""
JSON facade over the engine for the web front-end (web_version_plan.md, phase W0).

One `GameSession` owns one `ContactProgram`.  Everything that crosses the
Python/JavaScript boundary is a JSON string built from plain types only, so no
engine object and no Pyodide proxy ever leaks out; `json.dumps` is always called
without a `default=` hook and would raise here rather than in the browser.

This module adds no game rules.  Every action calls the same `ContactProgram`
method the console dispatcher (`GameInterface._act_*`) calls, with the same
arguments, and returns whatever the engine put in `program.message`.  The two
deliberate differences from the console are documented on `perform`.
"""
import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from . import save_manager
from .legacy_of_stars_v3 import ContactProgram
from .summary import build_summary, compute_score, score_breakdown
from .ui_text import HELP_TEXT

WOW_MESSAGE_LIMIT = 500                       # the console truncates a custom reply at 500 chars
WOW_ARRIVAL_GENERATION = 72                   # 1,800 LY at light speed
DEFENSES = ("emergency", "evacuate", "diplomacy")

#: Actions that are always offered, whatever `available_actions()` currently lists:
#: the 1977 opening, the doctrine follow-up and the two read-only queries.
UNGATED_ACTIONS = frozenset({
    "wow_reply", "wow_silent", "compose_director_message", "choose_doctrine", "summary", "help",
})
#: Actions that still work once the game is over (they only read state).
POST_GAME_ACTIONS = frozenset({"summary", "help"})


class _ParamError(Exception):
    """A parameter is missing, of the wrong type or out of range."""


class _Result:
    """What one action handler reports back to `perform`."""

    __slots__ = ("ok", "needs", "data", "message")

    def __init__(self, ok: bool, needs: Optional[dict] = None, data: Optional[dict] = None,
                 message: Optional[str] = None):
        self.ok = ok
        self.needs = needs
        self.data = data
        self.message = message


def _dumps(payload: Any) -> str:
    """The only place JSON leaves this module. No `default=`: plain types or nothing."""
    return json.dumps(payload, ensure_ascii=False)


def _need_str(params: Dict[str, Any], key: str) -> str:
    value = params.get(key)
    if not isinstance(value, str) or not value.strip():
        raise _ParamError(f"missing or invalid parameter '{key}' (expected a non-empty string)")
    return value


def _need_int(params: Dict[str, Any], key: str) -> int:
    value = params.get(key)
    if isinstance(value, bool):
        raise _ParamError(f"missing or invalid parameter '{key}' (expected an integer)")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            pass
    raise _ParamError(f"missing or invalid parameter '{key}' (expected an integer)")


def _optional_text(params: Dict[str, Any], key: str) -> str:
    value = params.get(key, "")
    if value is None:
        return ""
    if not isinstance(value, str):
        raise _ParamError(f"parameter '{key}' must be a string")
    return value


def _serialize_event(event) -> Dict[str, Any]:
    """GameEvent -> plain dict. Every `emit()` in src/ passes plain values as `data`."""
    return {"kind": event.kind, "text": event.text, "data": dict(event.data), "generation": event.generation}


def _doctrine_needs(tech) -> Dict[str, Any]:
    doctrine = tech.doctrine_choice
    return {
        "kind": "doctrine",
        "tech_id": tech.id,
        "name": doctrine.get("name", tech.name),
        "description": doctrine.get("description", ""),
        "options": [{"index": i, "name": option["name"], "description": option.get("description", "")}
                    for i, option in enumerate(doctrine["options"])],
    }


class GameSession:
    """One game, driven entirely by JSON strings.

    Typical bridge use:

        session = GameSession()
        state = session.new_game(seed=7)                       # JSON view_state
        result = session.perform("wow_silent")                 # JSON perform result
        save_text = session.save()                             # JSON save file
        session.load(save_text)

    `offline` defaults to True: the browser build has no `urllib`, so the engine
    must use its written content bank rather than an LLM.  `data_dir` overrides
    where `star_catalog.json`, `tech_tree.json` and `templates/` are read from;
    a directory that does not exist raises `FileNotFoundError` immediately.
    """

    def __init__(self, data_dir: Optional[Path] = None, offline: bool = True):
        self.data_dir = Path(data_dir) if data_dir is not None else None
        self.offline = bool(offline)
        self.program: Optional[ContactProgram] = None
        self._handlers: Dict[str, Callable[[Dict[str, Any]], _Result]] = {
            "send_message": self._do_send_message,
            "focus_research": self._do_focus_research,
            "public_outreach": self._do_public_outreach,
            "research_tech": self._do_research_tech,
            "choose_doctrine": self._do_choose_doctrine,
            "advance_generation": self._do_advance_generation,
            "defend": self._do_defend,
            "consult_advisor": self._do_consult_advisor,
            "listen_swan_song": self._do_listen_swan_song,
            "genesis_seed": self._do_genesis_seed,
            "respond_event": self._do_respond_event,
            "wow_reply": self._do_wow_reply,
            "wow_silent": self._do_wow_silent,
            "compose_director_message": self._do_compose_director_message,
            "summary": self._do_summary,
            "help": self._do_help,
        }

    # ------------------------------------------------------------------ lifecycle
    def new_game(self, seed: Optional[int] = None) -> str:
        """Start a fresh program and return its `view_state` as JSON."""
        self.program = ContactProgram(seed=seed, offline=self.offline, data_dir=self.data_dir)
        self.program.drain_events()
        return self.state()

    def load(self, save_json: str) -> str:
        """Restore a save produced by `save()` (or by the console) and return `view_state`.

        Raises `save_manager.SaveError` when the text is not a save this version can read.
        """
        program = save_manager.deserialize(save_json, offline=self.offline, data_dir=self.data_dir)
        program.drain_events()
        self.program = program
        return self.state()

    def save(self) -> str:
        """The save file for this session (identical to the console's saves/*.json)."""
        return save_manager.serialize(self._require_program())

    def state(self) -> str:
        """The current `view_state` as JSON. The single source of truth for the UI."""
        return _dumps(self._require_program().view_state())

    def _require_program(self) -> ContactProgram:
        if self.program is None:
            raise RuntimeError("no game in progress: call new_game() or load() first")
        return self.program

    # ------------------------------------------------------------------ actions
    def perform(self, action_id: str, params_json: str = "{}") -> str:
        """Run one action and return `{ok, message, events, state, needs}` (plus `data` when useful).

        `ok` means "the engine applied this action", and is decided per action from
        observable state - action points spent, a flag flipped, a technology now
        researched, the engine's own return value - never by parsing
        `program.message`.  A refusal the engine reports through `program.message`
        ("Not enough Action Points!", "System X not found in database.", a locked
        technology) comes back as `ok=false` with that message.  A swan-song scan
        that finds nothing is `ok=true`: the action ran and cost an action point.

        `needs` is non-null only after `research_tech` unlocked a doctrine choice;
        answer it with the `choose_doctrine` action.

        Errors never escape: an unknown action, a missing or malformed parameter,
        an action that `available_actions()` does not currently offer, a finished
        game, or an unexpected exception all return `ok=false` with a message.

        Two deliberate differences from the console dispatcher:
        - it does not autosave after `advance_generation` (the browser stores saves itself);
        - the "a philosophical crisis must be answered first" refusal names the
          `respond_event` action instead of a numeric menu key.
        """
        if self.program is None:
            return _dumps({"ok": False, "message": "no game in progress: call new_game() or load() first",
                           "events": [], "state": None, "needs": None})
        program = self.program
        result = self._invoke(action_id, params_json)
        payload: Dict[str, Any] = {
            "ok": result.ok,
            "message": result.message if result.message is not None else (program.message or ""),
            "events": [_serialize_event(event) for event in program.drain_events()],
            "state": program.view_state(),
            "needs": result.needs,
        }
        if result.data is not None:
            payload["data"] = result.data
        return _dumps(payload)

    def _invoke(self, action_id: Any, params_json: Any) -> _Result:
        program = self.program
        if not isinstance(action_id, str) or action_id not in self._handlers:
            known = ", ".join(sorted(self._handlers))
            return _Result(False, message=f"unknown action {action_id!r}. Known actions: {known}.")

        try:
            params = self._parse_params(params_json)
        except _ParamError as exc:
            return _Result(False, message=str(exc))

        if program.game_over and action_id not in POST_GAME_ACTIONS:
            reason = program.game_over_reason or "The program ended."
            return _Result(False, message=f"the game is over: {reason}")

        if action_id not in UNGATED_ACTIONS:
            if action_id not in {spec.id for spec in program.available_actions()}:
                return _Result(False, message="action not available now")

        # The doctrine follow-up appends to the message the research action left behind,
        # exactly as the console does; every other action starts from a clean message.
        if action_id != "choose_doctrine":
            program.message = ""

        try:
            return self._handlers[action_id](params)
        except _ParamError as exc:
            return _Result(False, message=str(exc))
        except Exception as exc:  # noqa: BLE001 - the bridge must never raise
            return _Result(False, message=f"internal error in action '{action_id}': {exc!r}")

    @staticmethod
    def _parse_params(params_json: Any) -> Dict[str, Any]:
        if params_json is None or params_json == "":
            return {}
        if isinstance(params_json, dict):
            return params_json  # tolerated for direct Python callers and tests
        if not isinstance(params_json, str):
            raise _ParamError("params must be a JSON object string")
        try:
            params = json.loads(params_json)
        except json.JSONDecodeError as exc:
            raise _ParamError(f"params is not valid JSON ({exc.msg})") from exc
        if params is None:
            return {}
        if not isinstance(params, dict):
            raise _ParamError("params must be a JSON object")
        return params

    # ------------------------------------------------------------------ handlers
    def _do_send_message(self, params: Dict[str, Any]) -> _Result:
        program = self.program
        system = _need_str(params, "system")
        text = _optional_text(params, "text")
        before = program.stats["messages_sent"]
        program.send_message(system, text)
        return _Result(program.stats["messages_sent"] > before)

    def _do_focus_research(self, params: Dict[str, Any]) -> _Result:
        program = self.program
        system = _need_str(params, "system")
        before = program.action_points
        program.focus_research(system)
        return _Result(program.action_points < before)

    def _do_public_outreach(self, params: Dict[str, Any]) -> _Result:
        program = self.program
        before = program.action_points
        program.public_outreach()
        return _Result(program.action_points < before)

    def _do_research_tech(self, params: Dict[str, Any]) -> _Result:
        program = self.program
        tech_id = _need_str(params, "tech")
        tech = program.technologies.get(tech_id)
        if tech is None:
            raise _ParamError(f"unknown technology '{tech_id}'")
        if tech.researched:
            return _Result(False, message=f"{tech.name} is already researched.")
        needs_doctrine = program.research_tech(tech_id)
        if not tech.researched:
            return _Result(False)
        needs = _doctrine_needs(tech) if needs_doctrine and tech.doctrine_choice else None
        return _Result(True, needs=needs)

    def _do_choose_doctrine(self, params: Dict[str, Any]) -> _Result:
        program = self.program
        tech_id = _need_str(params, "tech")
        tech = program.technologies.get(tech_id)
        if tech is None:
            raise _ParamError(f"unknown technology '{tech_id}'")
        if not tech.doctrine_choice:
            return _Result(False, message=f"{tech.name} has no doctrine choice.")
        if tech.chosen_doctrine:
            return _Result(False, message=f"A doctrine is already in force for {tech.name}: {tech.chosen_doctrine}.")
        options = tech.doctrine_choice["options"]
        choice = _need_int(params, "choice")
        if not 0 <= choice < len(options):
            raise _ParamError(f"parameter 'choice' must be between 0 and {len(options) - 1}")
        program.choose_doctrine(tech_id, choice)
        return _Result(tech.chosen_doctrine is not None)

    def _do_advance_generation(self, params: Dict[str, Any]) -> _Result:
        program = self.program
        if program.pending_philosophical_event is not None:
            program.message = ("A philosophical crisis demands a decision before this generation can end "
                               "(action 'respond_event').")
            return _Result(False)
        before = program.generation
        program.advance_generation()
        if program.generation <= before:
            return _Result(False)
        if not program.message:
            year = program.start_year + (program.generation - 1) * 25
            program.message = f"Advanced to Generation {program.generation} (Year {year})."
        return _Result(True)

    def _do_defend(self, params: Dict[str, Any]) -> _Result:
        program = self.program
        warnings = program.pending_attack_warnings
        if not warnings:
            program.message = "No active threats."
            return _Result(False)
        index = _need_int(params, "threat")
        if not 0 <= index < len(warnings):
            raise _ParamError(f"parameter 'threat' must be between 0 and {len(warnings) - 1}")
        defense = _need_str(params, "defense").strip().lower()
        if defense not in DEFENSES:
            raise _ParamError(f"parameter 'defense' must be one of: {', '.join(DEFENSES)}")
        warning = warnings[index]
        taken_before = len(warning.defensive_actions_taken)
        {"emergency": program.defend_emergency,
         "evacuate": program.defend_evacuate,
         "diplomacy": program.defend_diplomacy}[defense](index)
        applied = (warning not in program.pending_attack_warnings
                   or len(warning.defensive_actions_taken) > taken_before)
        return _Result(applied)

    def _do_consult_advisor(self, params: Dict[str, Any]) -> _Result:
        program = self.program
        before = program.advisor_consulted_this_gen
        program.consult_advisor()
        return _Result(program.advisor_consulted_this_gen and not before)

    def _do_listen_swan_song(self, params: Dict[str, Any]) -> _Result:
        program = self.program
        system = _need_str(params, "system")
        before = program.action_points
        program.listen_for_swan_song(system)
        return _Result(program.action_points < before)

    def _do_genesis_seed(self, params: Dict[str, Any]) -> _Result:
        program = self.program
        name = _need_str(params, "system")
        system = program.star_systems.get(name)
        if system is None:
            program.message = f"System {name} not found in database."
            return _Result(False)
        success, message = program.genesis.seed_world(program, system)
        program.message = message
        return _Result(bool(success))

    def _do_respond_event(self, params: Dict[str, Any]) -> _Result:
        program = self.program
        event = program.pending_philosophical_event
        if event is None:
            program.message = "No philosophical event is pending."
            return _Result(False)
        choice = _need_int(params, "choice")
        if not 0 <= choice < len(event.choices):
            raise _ParamError(f"parameter 'choice' must be between 0 and {len(event.choices) - 1}")
        return _Result(bool(program.handle_philosophical_event_choice(choice)))

    def _do_wow_reply(self, params: Dict[str, Any]) -> _Result:
        program = self.program
        wow = program.wow_signal
        if wow.decided:
            return _Result(False, message="Earth's 1977 decision has already been made.")
        text = _optional_text(params, "text")[:WOW_MESSAGE_LIMIT]
        wow.reply(text)
        sent = wow.wow_reply_message
        excerpt = sent[:100] + ("..." if len(sent) > 100 else "")
        arrival_year = program.start_year + (WOW_ARRIVAL_GENERATION - 1) * 25
        response_year = program.start_year + (wow.wow_response_gen - 1) * 25
        message = (
            "November 1977 - Reply Transmitted\n\n"
            f"Message: \"{excerpt}\"\n\n"
            "Target: Chi Sagittarii region (~1,800 LY)\n"
            f"ETA: Generation {WOW_ARRIVAL_GENERATION} (Year {arrival_year})\n"
            f"Response ETA: Generation {wow.wow_response_gen} (Year {response_year})\n\n"
            "The die is cast. Future generations will learn the truth.\n"
            "+100 Research Points\n+10% Public Support"
        )
        data = {"message": sent, "arrival_gen": WOW_ARRIVAL_GENERATION,
                "response_gen": wow.wow_response_gen, "replied": True}
        return _Result(True, data=data, message=message)

    def _do_wow_silent(self, params: Dict[str, Any]) -> _Result:
        program = self.program
        wow = program.wow_signal
        if wow.decided:
            return _Result(False, message="Earth's 1977 decision has already been made.")
        wow.stay_silent()
        message = (
            "November 1977 - Silence Maintained\n\n"
            "Earth chooses caution over contact.\n"
            "The WOW! Signal remains unexplained.\n"
            "Humanity stays hidden in the dark.\n\n"
            "Defensive Mindset: -15% attack damage (permanent)\n"
            "Achievement Unlocked: Silent Wisdom"
        )
        return _Result(True, data={"replied": False, "attack_damage_reduction": wow.attack_damage_reduction},
                       message=message)

    def _do_compose_director_message(self, params: Dict[str, Any]) -> _Result:
        """The director's draft for the WOW! reply. Decides nothing; feed it back to wow_reply."""
        draft = self.program.compose_director_message()
        return _Result(True, data={"draft": draft}, message=draft)

    def _do_summary(self, params: Dict[str, Any]) -> _Result:
        program = self.program
        data = {"score": compute_score(program), "score_breakdown": score_breakdown(program)}
        return _Result(True, data=data, message=build_summary(program))

    def _do_help(self, params: Dict[str, Any]) -> _Result:
        return _Result(True, data={"ai": self.program.ai.describe()}, message=HELP_TEXT)


def action_ids() -> List[str]:
    """Every action id `perform` accepts (documentation and front-end type generation)."""
    return sorted(GameSession()._handlers)
