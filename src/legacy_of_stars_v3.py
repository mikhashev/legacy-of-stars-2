import math
import random
import time
import os
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from pathlib import Path
import logging
import datetime
from .ai_manager import AIManager
from .content import ContentBank
from .wow_signal_event import WOWSignalEvent
from .attack_warning import AttackWarning
from .ai_strategic_advisor import AIStrategicAdvisor
from .swan_song_messages import SwanSongManager
from .passive_leakage import PassiveLeakageSystem
from .integration_progress import IntegrationProgress
from .philosophical_events import PhilosophicalEvents
from .genesis_project import GENESIS_KNOWLEDGE_REQUIRED, GenesisProject
from .civ_timeline import (  # the timeline model; CivilizationStage lives there so the
    CivEvent, CivState, CivTimeline, CivilizationStage,  # stage thresholds cannot diverge
    TIMELINE_HORIZON_YEARS, generate_timeline, no_civilization, stage_for_age, static_timeline)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CATALOG_PATH = DATA_DIR / "star_catalog.json"

START_YEAR = 1977  # WOW! Signal era; base year for Technology.year_context calculations

# Base of the per-system civilization-timeline RNG. `ContactProgram.__init__` sets it from the
# game seed before any system is generated, so a replayed or reloaded game rolls the same
# histories; a system's own stream is `random.Random(f"{CIV_SEED_BASE}:{name}")`. It is kept
# separate from the global `random` the rest of the engine draws from, so adding timelines
# cannot shift a single existing roll.
CIV_SEED_BASE: int = 0


def set_civ_seed_base(seed: Optional[int]) -> int:
    """Point the timeline RNG at this game's seed (a fresh random base when there is none)."""
    global CIV_SEED_BASE
    # A fresh Random() instead of the module-level one: seeding from entropy must not consume a
    # draw from the global stream that every existing roll depends on.
    CIV_SEED_BASE = int(seed) if seed is not None else random.Random().getrandbits(32)
    return CIV_SEED_BASE


def civ_rng(name: str) -> random.Random:
    """The deterministic timeline stream of one star system."""
    return random.Random(f"{CIV_SEED_BASE}:{name}")


# Knowledge a system must have before the player may point a deep scan at it. It is the same
# threshold `StarSystem.describe_civilization` reveals extinction at: below it, offering (or
# refusing) a swan-song scan would tell the player a system is dead before a telescope was
# ever pointed at it.
SWAN_SONG_KNOWLEDGE_REQUIRED = 20

# Knowledge a system must have before Earth keeps watching it: below it nobody is pointing a
# telescope at that star from one generation to the next, so no observation is recorded and no
# sky change is noticed. The same 20 % at which a civilization is named at all.
OBSERVATION_KNOWLEDGE_REQUIRED = 20

# How many dated observations one system keeps (the dossier shows a history, not an archive).
MAX_OBSERVATIONS = 30


def stage_phrase(stage: Optional[CivilizationStage]) -> str:
    """A stage as prose: `DIGITAL` -> "digital era"."""
    return f"{stage.name.replace('_', ' ').lower()} era" if stage else "unknown era"


def observed_change(before: Optional[CivState], after: Optional[CivState],
                    has_beacon: bool = False) -> Optional[str]:
    """What a watcher would notice between two observations of the same system, or None.

    Only what a telescope can actually see counts: whether anyone is broadcasting, and how far
    along they are. A strategy or an attitude never shows up here - those are inferences, not
    observations, and T1 keeps them hidden.
    """
    if before is None or after is None:
        return None
    if before.alive and not after.alive and after.died_year is not None:
        # An automated beacon is still carrying, so what stopped is the civilization, not the star.
        return "silence" if has_beacon else "extinction"
    if not before.alive and after.alive:
        return "activity"
    if before.alive and after.alive and before.stage and after.stage and after.stage.value > before.stage.value:
        return "stage_up"
    return None


# ---------------------------------------------------------------------- messages in flight (T2)
# The fate the engine keeps on every sent message. Two of these are secrets: "died_in_flight"
# says the civilization will be dead when our signal lands, and "silent" says no reply will
# ever come - both are facts about a future the player has not observed yet, and the whole
# point of the receipt frame is that nobody on Earth can know them. `public_message_fate`
# below is the only thing `view_state` may show.
MESSAGE_FATES = ("in_flight", "replied", "nobody", "died_in_flight", "silent")
PUBLIC_MESSAGE_FATES = ("in_flight", "replied", "nobody", "unanswered")


def sent_message(text: str, generation: int, arrival_gen: int, expected_reply_year: int,
                 explanation_year: Optional[int] = None, fate: str = "in_flight") -> Dict[str, Any]:
    """One entry of `StarSystem.messages_sent`.

    `arrival_gen` is when our signal reaches them, `expected_reply_year` when an answer would
    reach us (`send_year + 2d`), and `explanation_year` the year an observation explains a
    silence: the send year when we already know nobody can answer, the year the light of their
    death arrives when they die before receipt, and None while a reply may still be coming.
    """
    return {
        "text": text,
        "generation": int(generation),
        "arrival_gen": int(arrival_gen),
        "expected_reply_year": int(expected_reply_year),
        "explanation_year": None if explanation_year is None else int(explanation_year),
        "fate": fate if fate in MESSAGE_FATES else "in_flight",
    }


def public_message_fate(entry: Dict[str, Any], year_now: int) -> str:
    """The fate of a sent message as the player may see it.

    A reply that came and a target we knew could not answer are public knowledge. Everything
    else is one of two things the player cannot tell apart, and must not be told apart: a reply
    still in flight, or a silence - which is exactly what "unanswered" means here.
    """
    fate = entry.get("fate", "in_flight")
    if fate in ("replied", "nobody"):
        return fate
    expected = entry.get("expected_reply_year")
    if expected is not None and int(year_now) >= int(expected):
        return "unanswered"
    return "in_flight"


def public_explanation_year(entry: Dict[str, Any], year_now: int) -> Optional[int]:
    """`explanation_year`, but only once that year has arrived.

    The stored value can be in the future ("the light of their death reaches us in 2312"), and
    publishing it would hand the player the same secret `public_message_fate` withholds. Once
    the year has passed the observation itself has already been made, so the date is free.
    """
    explanation = entry.get("explanation_year")
    if explanation is None or int(year_now) < int(explanation):
        return None
    return int(explanation)


# Chance that a star with a perfectly habitable spectral class (G/K main sequence) hosts a
# civilization. Calibrated so the full 53-star catalog still averages ~8 civilizations, as the
# flat 0.15 model did: the mean habitability weight of the catalog is 30.8 / 53 = 0.581, and
# 0.26 x 30.8 = 8.0.
BASE_CIV_CHANCE = 0.26

# Habitability by spectral class. Longer-lived, more stable stars get a higher weight; evolved
# stars (giants, white dwarfs) burned their old habitable zone and get none.
_HABITABILITY_BY_CLASS = {"G": 1.0, "K": 1.0, "M": 0.6, "F": 0.6, "A": 0.1,
                          "O": 0.0, "B": 0.0,               # live a few million years
                          "L": 0.0, "T": 0.0, "Y": 0.0}     # brown dwarfs
_UNKNOWN_CLASS_WEIGHT = 0.5  # a type we cannot parse: neither ruled out nor favoured


def habitability_weight(spectral_type: Optional[str]) -> float:
    """Relative chance that a star of this spectral type hosts life (1.0 = G/K main sequence)."""
    if not spectral_type:
        return 1.0
    core = str(spectral_type).split("(")[0].strip().upper()
    if not core:
        return 1.0
    if core.startswith("D"):
        return 0.0  # white dwarf: the former habitable zone was swallowed by the red giant phase
    # Luminosity class: check III before IV before V, and treat "IV-V" as main sequence.
    if "III" in core:
        return 0.0  # giant: post-main-sequence, the old habitable zone is gone
    if "IV-V" not in core and "IV" in core:
        return 0.5  # subgiant: leaving the main sequence, planets still possible
    return _HABITABILITY_BY_CLASS.get(core[0], _UNKNOWN_CLASS_WEIGHT)


def format_year(year: int) -> str:
    """A calendar year for display, with years at or before 0 written as BC.

    Light-time makes this necessary: what a telescope sees of a system `d` light-years away
    left it `d` years ago, and for the WOW! source (1,800 LY) that is deep in antiquity. The
    astronomical convention is used - year 0 is 1 BC, year -1 is 2 BC - so the arithmetic
    `year - distance` stays a single unbroken number line.
    """
    year = int(year)
    return str(year) if year > 0 else f"{1 - year} BC"


def load_star_catalog(path: Path = CATALOG_PATH) -> List[Dict[str, Any]]:
    """Real nearby stars (name, distance in LY, spectral type, RA/Dec), nearest first."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            stars = json.load(f).get("stars", [])
    except (OSError, json.JSONDecodeError) as exc:
        logging.warning(f"Star catalog unavailable ({exc}); using a synthetic neighbourhood")
        return []
    return sorted(stars, key=lambda s: s["distance"])


@dataclass(frozen=True)
class ActionSpec:
    """A player action the engine currently offers (UI-agnostic)."""
    id: str
    label: str
    cost: str = ""                 # e.g. "1 AP", "Free", "All AP"
    needs: Tuple[str, ...] = ()    # what the UI must ask for: "system", "text", "tech", "threat", "defense", "choice"


@dataclass
class GameEvent:
    """Something that happened, for the UI to show (console) or animate (future front-ends)."""
    kind: str
    text: str
    data: Dict[str, Any] = field(default_factory=dict)
    generation: int = 0


class Technology:
    def __init__(self, data: dict):
        self.id = data["id"]
        self.name = data["name"]
        self.description = data["description"]
        self.cost = data["cost"]
        self.prerequisites = data["prerequisites"]
        self.category = data["category"]
        self.tier = data.get("tier", 0)
        self.min_generation = data.get("min_generation", 1)
        if self.min_generation <= 1:
            year_line = "Available from start"
        else:
            unlock_year = START_YEAR + (self.min_generation - 1) * 25
            year_line = f"Unlocks Gen {self.min_generation}+ (Year {unlock_year})"
        history = data.get("history", "")
        self.year_context = f"{year_line}. {history}" if history else year_line
        self.special = data.get("special", None)
        self.passive_rp = data.get("passive_rp", 0)  # New: Passive research points per turn
        self.is_legacy = False  # Flag for pre-1977 legacy knowledge
        self.detection_bonus = data.get("detection_bonus", 0.0)  # Adds to the per-generation discovery chance
        doctrine_choice = data.get("doctrine_choice")
        if doctrine_choice and not doctrine_choice.get("options"):
            doctrine_choice = None  # a doctrine without options is not a choice
        self.doctrine_choice = doctrine_choice
        self.researched = False
        self.chosen_doctrine = None

class StarSystem:
    """One catalogued star, and whatever lives (or lived) around it.

    Three of its fields are the *observed* frame from T1 on - `is_extinct`, `extinct_years_ago`
    and `has_swan_song` mean "as our telescopes show it in the current year", not "as the
    civilization truly is". `ContactProgram` keeps them current with `refresh_observation()`;
    the truth is in `timeline`, and `observed(year)` is the one way to read it honestly.
    """

    def __init__(self, name: str, distance: float, spectral_type: Optional[str] = None,
                 ra: Optional[float] = None, dec: Optional[float] = None):
        self.name = name
        self.distance = distance
        self.spectral_type = spectral_type
        self.ra = ra    # J2000 right ascension, degrees (for star maps)
        self.dec = dec  # J2000 declination, degrees
        # The Fermi paradox made concrete: most stars are silent. With ~50 catalogued stars this
        # yields a handful of civilizations per game, a quarter of them already extinct. The
        # spectral class weights the roll: a red giant or white dwarf never hosts anyone.
        self.has_civilization = random.random() < BASE_CIV_CHANCE * habitability_weight(spectral_type)

        if self.has_civilization:
            self._roll_civilization()
        else:
            self._clear_civilization()

        self.knowledge = 0
        self.messages_sent = []
        self.pending_responses = []
        self.received_messages = []
        # Dated telescope observations: {"year", "observed_year", "summary"}, oldest first.
        self.observations: List[Dict[str, Any]] = []
        self.pending_attack = None
        self.is_seeded = False           # Genesis Project marker
        self.has_detected_earth = False  # hostile civ already found us (no double attacks)
        self.is_wow_source = False

    def _roll_civilization(self) -> None:
        """Roll the hidden profile of a civilization living in this system."""
        distance = self.distance
        # === PHASE 1: Statistical Realism ===
        human_age = 100

        if random.random() < 0.75:
            civ_age = human_age * random.uniform(1.5, 50)
        else:
            civ_age = human_age * random.uniform(0.1, 0.9)
        
        if random.random() < 0.10:
            civ_age = human_age * random.uniform(10, 1000)
        
        self.civilization_age = civ_age
        self.civilization_stage = self._age_to_stage(civ_age)
        creation_stage = self.civilization_stage  # kept when extinction clears the field below
        
        self.is_extinct = random.random() < 0.25
        if self.is_extinct:
            # We can't know about a death whose light hasn't reached us yet: the system is
            # `distance` light-years away, so its last living signal is at least that old.
            self.extinct_years_ago = random.randint(min(max(50, int(distance)), 5000), 5000)
            self.has_swan_song = random.random() < 0.8
            self.civilization_stage = None
        
        if not self.is_extinct:
            strategy_weights = {"L": 10, "LB": 30, "LR": 40, "LA": 15, "LBA": 5}
            self.true_strategy = random.choices(list(strategy_weights.keys()), weights=list(strategy_weights.values()))[0]
            
            if self.civilization_age > human_age * 2:
                self.deception_level = random.uniform(0.3, 1.0)
            else:
                self.deception_level = random.uniform(0, 0.5)
        else:
            self.true_strategy = None
            self.deception_level = 0
        
        # === PHASE 3A.2: Civilization Type (How they solved Dual DNA problem) ===
        if not self.is_extinct:
            # Living civilizations - successfully solved the integration crisis
            civ_type_weights = {
                "biological_pure": 20,      # Stayed biological, cautious
                "digital_ascended": 15,     # Uploaded consciousness
                "hybrid_integrated": 10     # Successfully merged
            }
            self.civilization_type = random.choices(
                list(civ_type_weights.keys()),
                weights=list(civ_type_weights.values())
            )[0]
        else:
            # Extinct civilizations - 70% failed the transition
            if random.random() < 0.7:
                self.civilization_type = "failed_transition"
            else:
                # Some died for other reasons (war, asteroid, etc.)
                self.civilization_type = random.choice([
                    "biological_pure", "digital_ascended", "hybrid_integrated"
                ])
        
        self.civilization_attitude = random.uniform(0.2, 0.8)

        # Everything above is unchanged and draws from the global `random` in the same order as
        # before; the timeline is rolled afterwards, from this system's own stream.
        self.timeline = self._build_timeline(creation_stage)

    def _build_timeline(self, creation_stage: Optional[CivilizationStage]) -> CivTimeline:
        """The history behind the profile `_roll_civilization` just rolled.

        The rolled fields become the state at creation: the timeline starts from them at
        `origin_year = START_YEAR - civilization_age` and, for a living civilization, is rolled
        forward from 1977 to the horizon (stage crossings, extinction hazard, strategy drift).
        Holding the hazard back until 1977 is what keeps T0 free of behaviour change: a timeline
        can never kill a civilization the game already presents as alive.

        For a civilization the roll marks extinct the timeline is static, with a single `extinct`
        event at `START_YEAR - extinct_years_ago`. That is today's semantics kept verbatim - the
        engine defines `extinct_years_ago` as "silent for N years as seen from Earth" and folds
        the light-time into the `max(50, distance)` lower bound of the roll - so the death can
        land before `origin_year` for a young civilization that has been silent a long time. T1
        re-derives `extinct_years_ago` from the timeline and retires that inconsistency.
        """
        origin_year = int(round(START_YEAR - self.civilization_age))
        initial = CivState(alive=True, stage=creation_stage, strategy=self.true_strategy,
                           attitude=self.civilization_attitude, civ_type=self.civilization_type,
                           deception=self.deception_level, died_year=None)
        if self.is_extinct:
            died_year = START_YEAR - int(self.extinct_years_ago)
            return CivTimeline(origin_year, initial,
                               [CivEvent(died_year, "extinct", {"has_swan_song": bool(self.has_swan_song)})])
        return generate_timeline(civ_rng(self.name), origin_year, initial,
                                 START_YEAR + TIMELINE_HORIZON_YEARS, first_change_year=START_YEAR)

    def set_static_timeline(self, origin_year: int) -> CivTimeline:
        """Give this system a timeline that never changes, starting from its current profile.

        For civilizations the engine writes by hand (Genesis colonies, the mirror civilization)
        rather than rolls.
        """
        self.timeline = static_timeline(origin_year, self._state_from_fields())
        return self.timeline

    def _state_from_fields(self) -> CivState:
        """The cached fields as a `CivState` (what a system without a timeline looks like)."""
        if not self.has_civilization:
            return no_civilization()
        if self.is_extinct:
            silent = getattr(self, "extinct_years_ago", None)
            return CivState(alive=False, stage=None, strategy=None,
                            attitude=self.civilization_attitude, civ_type=self.civilization_type,
                            deception=self.deception_level,
                            died_year=START_YEAR - int(silent) if silent is not None else None)
        return CivState(alive=True, stage=self.civilization_stage, strategy=self.true_strategy,
                        attitude=self.civilization_attitude, civ_type=self.civilization_type,
                        deception=self.deception_level, died_year=None)

    def timeline_state(self, year: int) -> CivState:
        """This civilization as it is in `year`.

        A system without a timeline (an old save, or one written by a test) is static: it reports
        its cached fields for every year, exactly as the engine has always behaved.
        """
        timeline = getattr(self, "timeline", None)
        if timeline is None:
            return self._state_from_fields()
        return timeline.state_at(year)

    # ------------------------------------------------------------------ the observed frame (T1)
    def observed_year(self, year_now: int) -> int:
        """The year of the light that reaches Earth in `year_now`: `year_now - round(distance)`."""
        return int(year_now) - int(round(self.distance))

    def observed(self, year_now: int) -> CivState:
        """This civilization as our telescopes show it in `year_now`.

        Everything the player may see goes through here: the light left this system
        `round(distance)` years ago, so a civilization the timeline has already killed is still
        seen alive until that light arrives. A system without a timeline (an old save) keeps
        reporting its cached fields, which is exactly how the engine behaved before T1.
        """
        return self.timeline_state(self.observed_year(year_now))

    def observed_silent_years(self, year_now: int) -> Optional[int]:
        """How long the last living light of a dead civilization has been past us, or None.

        `(year_now - round(distance)) - died_year`: the death is only ever counted in Earth's
        reception frame, so the number is never negative while the death is observable at all
        (which is what retires the v1.1 clamp). A system without a timeline keeps its cached
        `extinct_years_ago`.
        """
        if getattr(self, "timeline", None) is None:
            return getattr(self, "extinct_years_ago", None)
        state = self.observed(year_now)
        if state.alive or state.died_year is None:
            return None
        return max(0, self.observed_year(year_now) - int(state.died_year))

    def observed_swan_song(self, year_now: Optional[int] = None) -> bool:
        """Whether a beacon left by an *observable* death is already reaching us."""
        timeline = getattr(self, "timeline", None)
        if timeline is None or year_now is None:
            return bool(getattr(self, "has_swan_song", False))
        state = self.observed(year_now)
        return bool(timeline.has_swan_song and not state.alive and state.died_year is not None)

    def refresh_observation(self, year_now: int) -> Optional[str]:
        """Bring the "as observed now" attributes up to date; return what just became visible.

        `is_extinct`, `extinct_years_ago` and `has_swan_song` are kept as plain attributes
        because half the engine reads them, but from T1 on they mean *as observed from Earth in
        the current year*, not as the civilization truly is. `ContactProgram` refreshes them at
        the start of every generation and whenever a system is created or loaded.

        Returns `"extinct"` the first time a death becomes observable (the caller registers the
        swan song then), otherwise None. A system without a timeline is static: nothing is
        refreshed and nothing is returned.
        """
        if getattr(self, "timeline", None) is None or not self.has_civilization:
            return None
        state = self.observed(year_now)
        dead = (not state.alive) and state.died_year is not None
        was_extinct = bool(getattr(self, "is_extinct", False))
        self.is_extinct = dead
        self.extinct_years_ago = self.observed_silent_years(year_now) if dead else None
        self.has_swan_song = bool(dead and self.timeline.has_swan_song)
        return "extinct" if dead and not was_extinct else None

    def observation_summary(self, year_now: int) -> str:
        """One line for the dossier's observation history ("digital era, cautious")."""
        if not self.has_civilization:
            return "No artificial signals."
        state = self.observed(year_now)
        if not state.alive:
            if state.died_year is None:
                return "No artificial signals."
            silent = self.observed_silent_years(year_now) or 0
            return f"Silent for {int(silent)} years."
        summary = stage_phrase(state.stage)
        if self.knowledge >= 40:
            attitude = "cautious"
            if state.attitude < 0.4:
                attitude = "potentially hostile"
            elif state.attitude > 0.6:
                attitude = "seemingly friendly"
            summary = f"{summary}, {attitude}"
        return summary

    def record_observation(self, year_now: int, summary: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Append one dated observation, unless it repeats the last one verbatim."""
        entry = {"year": int(year_now), "observed_year": self.observed_year(year_now),
                 "summary": summary if summary is not None else self.observation_summary(year_now)}
        history = getattr(self, "observations", None)
        if history is None:
            history = self.observations = []
        if history and history[-1] == entry:
            return None
        history.append(entry)
        del history[:-MAX_OBSERVATIONS]
        return entry

    def _clear_civilization(self) -> None:
        """Reset the civilization fields to the 'nobody lives here' defaults."""
        self.civilization_age = 0
        self.civilization_stage = None
        self.civilization_attitude = 0
        self.is_extinct = False
        self.extinct_years_ago = None
        self.has_swan_song = False
        self.true_strategy = None
        self.deception_level = 0
        self.civilization_type = None  # No civilization, no type
        self.timeline = None

    _SCALAR_FIELDS = ("name", "distance", "spectral_type", "ra", "dec", "has_civilization", "civilization_age",
                      "is_extinct", "has_swan_song", "true_strategy", "deception_level", "civilization_type",
                      "civilization_attitude", "knowledge", "is_seeded", "has_detected_earth", "is_wow_source")

    def to_dict(self) -> Dict[str, Any]:
        data = {name: getattr(self, name, None) for name in self._SCALAR_FIELDS}
        data["civilization_stage"] = self.civilization_stage.name if self.civilization_stage else None
        data["extinct_years_ago"] = getattr(self, "extinct_years_ago", None)
        timeline = getattr(self, "timeline", None)
        data["timeline"] = timeline.to_dict() if timeline else None
        data["observations"] = [dict(entry) for entry in getattr(self, "observations", [])]
        data["messages_sent"] = [dict(entry) for entry in self.normalize_messages(self.messages_sent)]
        data["pending_responses"] = [[text, gen] for text, gen in self.pending_responses]
        data["received_messages"] = list(self.received_messages)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StarSystem":
        """Rebuild a system without re-rolling its hidden civilization."""
        system = cls.__new__(cls)
        system.name = data["name"]
        system.distance = float(data["distance"])
        system.spectral_type = data.get("spectral_type")
        system.ra = data.get("ra")
        system.dec = data.get("dec")
        system.has_civilization = bool(data.get("has_civilization", False))
        system.civilization_age = data.get("civilization_age", 0)
        stage = data.get("civilization_stage")
        system.civilization_stage = CivilizationStage[stage] if stage else None
        system.is_extinct = bool(data.get("is_extinct", False))
        system.extinct_years_ago = data.get("extinct_years_ago")
        system.has_swan_song = bool(data.get("has_swan_song", False))
        system.true_strategy = data.get("true_strategy")
        system.deception_level = data.get("deception_level", 0)
        system.civilization_type = data.get("civilization_type")
        system.civilization_attitude = data.get("civilization_attitude", 0)
        # A save written before timelines existed has no key: that system stays static.
        system.timeline = CivTimeline.from_dict(data.get("timeline"))
        system.knowledge = data.get("knowledge", 0)
        # A save written before the observed frame has no history: the dossier starts empty.
        system.observations = [dict(entry) for entry in data.get("observations", [])]
        # Saves written before T2 hold `[text, generation]` pairs; they migrate on load.
        system.messages_sent = system.normalize_messages(data.get("messages_sent", []))
        system.pending_responses = [tuple(item) for item in data.get("pending_responses", [])]
        system.received_messages = list(data.get("received_messages", []))
        system.pending_attack = None
        system.is_seeded = bool(data.get("is_seeded", False))
        system.has_detected_earth = bool(data.get("has_detected_earth", False))
        system.is_wow_source = bool(data.get("is_wow_source", False))
        return system

    def _age_to_stage(self, age: float) -> CivilizationStage:
        """Stage by age, from the thresholds timelines are built on (50/200/1000/10k/100k)."""
        return stage_for_age(age)
    
    def get_round_trip_time(self) -> int:
        """Get the communication round trip time in generations (rounded up)"""
        years = self.distance * 2  # There and back
        generations = (years / 25)  # Each generation is ~25 years
        return max(1, int(generations + 0.999))  # Round up to nearest generation

    def one_way_generations(self) -> int:
        """Generations our signal needs to reach this system (half the round trip, rounded up)."""
        return math.ceil(self.get_round_trip_time() / 2)

    def normalize_messages(self, items: List[Any], start_year: int = START_YEAR) -> List[Dict[str, Any]]:
        """Sent messages as dicts, from either shape a save can hold.

        Before T2 a message was the pair `[text, generation]` and nothing was recorded about
        what would answer it. Such an entry is rebuilt with the dates the pair implies and the
        neutral fate "in_flight": an old save cannot know whether its silences were chosen.
        """
        one_way = self.one_way_generations()
        messages: List[Dict[str, Any]] = []
        for item in items or []:
            if isinstance(item, dict):
                generation = int(item.get("generation", 1))
                send_year = start_year + (generation - 1) * 25
                messages.append(sent_message(
                    item.get("text", ""), generation,
                    item.get("arrival_gen", generation + one_way),
                    item.get("expected_reply_year", send_year + 2 * int(round(self.distance))),
                    item.get("explanation_year"), item.get("fate", "in_flight")))
                continue
            text, generation = item[0], int(item[1])
            send_year = start_year + (generation - 1) * 25
            messages.append(sent_message(text, generation, generation + one_way,
                                         send_year + 2 * int(round(self.distance))))
        return messages

    
    def describe_civilization(self, year_now: Optional[int] = None) -> str:
        """What the player is told about this system, read in the observed frame.

        With `year_now` everything below comes from `observed(year_now)`: the light our
        telescopes are looking at left this system `round(distance)` years ago, so a
        civilization the timeline has already killed is still described as alive until that
        light arrives, and the "silent for N years" number is counted from the death in
        Earth's reception frame (`observed_year - died_year`), never below zero.

        Without `year_now` the cached fields are used, which is what the engine did before the
        observed frame existed - the fallback for old callers and for systems written by hand.
        """
        if not self.has_civilization:
            return "No signs of civilization detected."

        state = self.observed(year_now) if year_now is not None else self._state_from_fields()

        if not state.alive and state.died_year is None:
            # Nothing has reached us yet: this civilization is younger than the light we are
            # looking at. An empty sky is the honest description of that.
            return "No signs of civilization detected."

        # Handle extinct civilizations (their stage is cleared at the death)
        if not state.alive:
            silent = (self.observed_silent_years(year_now) if year_now is not None
                      else getattr(self, "extinct_years_ago", None))
            silent = max(0, int(silent or 0))
            if self.knowledge < 20:
                return "Faint signals detected. System appears lifeless."
            elif self.knowledge < 60:
                return f"EXTINCT CIVILIZATION detected. Silent for ~{silent} years (as seen from Earth)."
            else:
                beacon = self.observed_swan_song(year_now)
                swan_info = " Data archives may exist." if beacon else " No archives detected."
                return f"EXTINCT: Civilization went silent {silent} years ago; automated transmissions continue.{swan_info}"

        if self.knowledge < 20:
            return "Possible artificial signals detected."
        elif self.knowledge < 40:
            return f"Civilization detected at {state.stage.name} stage."
        elif self.knowledge < 60:
            attitude = "cautious"
            if state.attitude < 0.4:
                attitude = "potentially hostile"
            elif state.attitude > 0.6:
                attitude = "seemingly friendly"
            return f"{state.stage.name} civilization. Attitude: {attitude}."
        elif self.knowledge < 80:
            return f"{state.stage.name} civilization with {int(state.attitude * 100)}% positive attitude toward contact."
        else:
            # Full knowledge
            stage_descriptions = {
                CivilizationStage.PRE_RADIO: "Pre-radio civilization using primitive communication.",
                CivilizationStage.EARLY_RADIO: "Early radio-capable civilization, similar to Earth's 20th century.",
                CivilizationStage.DIGITAL: "Digital-era civilization with global communication networks.",
                CivilizationStage.INTERPLANETARY: "Interplanetary civilization spanning multiple worlds in their system.",
                CivilizationStage.INTERSTELLAR: "Advanced interstellar civilization with probes and settlements in several star systems.",
                CivilizationStage.POST_BIOLOGICAL: "Post-biological intelligence transcending physical limitations."
            }
            return stage_descriptions[state.stage]


class Director:
    """Represents a generation's director of the contact program"""
    def __init__(self, name: str):
        self.name = name
        self.skills = {
            "diplomacy": random.uniform(0.5, 1.0),
            "science": random.uniform(0.5, 1.0),
            "administration": random.uniform(0.5, 1.0),
        }
        self.traits = []
        self.generation = 0
        
        # Add random traits
        potential_traits = [
            "Cautious", "Bold", "Analytical", "Intuitive", "Diplomatic", 
            "Direct", "Patient", "Efficient", "Visionary", "Traditional"
        ]
        num_traits = random.randint(1, 3)
        self.traits = random.sample(potential_traits, num_traits)
    
    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "skills": dict(self.skills), "traits": list(self.traits), "generation": self.generation}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Director":
        director = cls.__new__(cls)
        director.name = data["name"]
        director.skills = dict(data.get("skills", {"diplomacy": 0.5, "science": 0.5, "administration": 0.5}))
        director.traits = list(data.get("traits", []))
        director.generation = data.get("generation", 0)
        return director

    def get_skill_bonus(self, skill: str) -> float:
        """Get bonus for a particular skill based on traits"""
        bonus = 0
        if skill == "diplomacy" and "Diplomatic" in self.traits:
            bonus += 0.2
        elif skill == "science" and "Analytical" in self.traits:
            bonus += 0.2
        elif skill == "administration" and "Efficient" in self.traits:
            bonus += 0.2
        
        if "Bold" in self.traits:
            bonus += 0.1
        if "Direct" in self.traits and skill == "diplomacy":
             bonus -= 0.1 # Direct is bad for diplomacy maybe? Or good? Let's say bad for nuances but good for action.
             
        return bonus
    
    def get_effective_skill(self, skill: str) -> float:
        """Get effective skill level with bonuses"""
        return min(1.0, self.skills[skill] + self.get_skill_bonus(skill))

class ContactProgram:
    """Manages Earth's interstellar contact program"""
    LEGACY_TECHS = (
        "arecibo_telescope",        # Built 1963
        "drake_equation",           # Published 1961
        "project_ozma",             # Conducted 1960
        "signal_processing_basic",  # 1970s technology
        "voyager_golden_record",    # Launched 1977
    )

    def __init__(self, seed: Optional[int] = None, offline: bool = False, generate: bool = True,
                 data_dir: Optional[Path] = None):
        if seed is not None:
            random.seed(seed)
        self.seed = seed
        # Before any system is generated: the timelines follow the game seed. Saved with the
        # game (an unseeded game still has to reload and undo into the same histories).
        self.civ_seed_base = set_civ_seed_base(seed)
        self.offline = bool(offline) or os.getenv("LOS_OFFLINE") == "1"

        # --- where star_catalog.json, tech_tree.json and templates/ are read from.
        # Defaults to the repository's data/; an explicit directory (web build, tests) must exist.
        if data_dir is None:
            self.data_dir = DATA_DIR
        else:
            self.data_dir = Path(data_dir)
            if not self.data_dir.is_dir():
                raise FileNotFoundError(f"data directory not found: {self.data_dir}")

        # --- core program state
        self.generation = 1
        self.start_year = 1977  # WOW! Signal era
        self.funding = 50  # 0-100 scale
        self.research_points = 0
        self.message_quality = 1.0
        self.public_support = 50  # 0-100 scale
        self.knowledge_base = 10  # General knowledge about other civilizations
        self.game_over = False
        self.game_over_reason = ""
        self.victory = False
        self.philosophical_victory = False  # Separate from contact victory
        self.message = ""

        # --- galaxy
        self.catalog = load_star_catalog(self.data_dir / "star_catalog.json")
        self.undiscovered: List[str] = []  # catalogued stars we have not resolved yet, nearest first
        self.star_systems: Dict[str, StarSystem] = {}

        # --- people
        self.directors: List[Director] = []
        self.current_director: Optional[Director] = None

        # --- technology, risks, economy
        self.technologies = self.load_tech_tree()
        self.self_destruct_risk = 0.0
        self.ecological_risk = 0.0
        self.active_doctrines: List[str] = []
        self.action_points = 0
        self.max_action_points = 0
        self.ap_modifier = 0  # permanent bonus/penalty from events
        # Anti-stagnation bookkeeping: player actions taken in the current generation, and the
        # number of consecutive generations that ended with none. Neither changes any rule;
        # they only decide when the mission analyst volunteers a briefing (advance_generation).
        self.actions_this_generation = 0
        self.idle_generations = 0
        # What the player has done in the current generation, oldest first, as display rows
        # ({"action", "summary", "cost"}). Written by the action methods, cleared by
        # `advance_generation`; it decides nothing, it only lets the player see this
        # generation's decisions before ending it (and the web facade's undo name them).
        self.generation_log: List[Dict[str, str]] = []

        # --- optional AI and the written content bank
        self.ai = AIManager(offline=self.offline)
        self.content = ContentBank(self.data_dir / "templates")
        self.ai_advisor = AIStrategicAdvisor(self.ai)
        self.advisor_consulted_this_gen = False

        # --- subsystems
        self.wow_signal = WOWSignalEvent(self)
        self.pending_attack_warnings: List[AttackWarning] = []
        self.swan_song_manager = SwanSongManager(self.ai, self.content)
        # Systems a deep scan has already been pointed at and found nothing in. Kept so the
        # candidate list shrinks after a fruitless scan instead of offering the same silent
        # system forever (a discovered swan song leaves the list via the manager instead).
        self.scanned_for_swan_song: Set[str] = set()
        self.leakage_system = PassiveLeakageSystem()
        self.broadcast_radius = 0.0  # leakage front, recalculated each generation
        self.leakage_multiplier = 1.0  # 1.0 = full leakage, 0.0 = complete silence
        # Information attacks in flight: [system_name, arrival_generation]
        self.pending_info_attacks: List[List] = []
        self.integration = IntegrationProgress()
        self.philosophical_events = PhilosophicalEvents()
        self.pending_philosophical_event = None  # event waiting for the player's choice
        self.genesis = GenesisProject()

        # --- technology special-effect flags
        self.passive_defense_bonus = 1.0  # damage multiplier from passive defenses (1.0 = none)
        self.warning_time_bonus = 0  # extra generations of warning time
        self.has_backup_colonies = False  # prevents total annihilation
        self.cloaking_active = False
        self.ai_advisor_unlocked = False
        self.can_contact_post_biological = False
        self.ultimate_survival = False
        self.has_solar_sails = False
        self.has_laser_sails = False
        self.message_delivery_speed = 1.0
        self.von_neumann_defense_bonus = 1.0  # damage multiplier against probe attacks
        self.has_fusion_propulsion = False
        self.can_send_heavy_probes = False

        # --- victory tracking, events, statistics
        self.fermi_evidence = {
            "extinction_evidence": 0,       # Swan songs discovered
            "dark_forest_evidence": 0,      # Hostile encounters
            "cooperation_evidence": 0,      # Peaceful contacts
            "great_filter_evidence": 0,     # Integration techs, philosophical crises
        }
        self.events: List[GameEvent] = []
        self.stats: Dict[str, int] = {
            "messages_sent": 0, "responses_received": 0, "attacks_scheduled": 0, "attacks_survived": 0,
            "attacks_landed": 0, "info_attacks": 0, "swan_songs_found": 0, "systems_discovered": 0,
            "events_resolved": 0, "techs_researched": 0, "worlds_seeded": 0, "passive_detections": 0,
            # What became of every message sent (T2). "died_in_flight" and "silent" are the two
            # the player is never told apart at the time; they exist so the receipt frame can be
            # measured (plan §7c) rather than eyeballed.
            "messages_replied": 0, "messages_nobody": 0, "messages_died_in_flight": 0,
            "messages_silent": 0,
        }
        self.achievements: List[str] = []

        if generate:
            self._start_new_game()

    def _start_new_game(self) -> None:
        """Roll the initial neighbourhood, the first director and pre-1977 knowledge."""
        self.star_systems = self.generate_star_systems(5)
        logging.debug("")
        logging.debug("=" * 60)
        logging.debug("GALAXY OVERVIEW - Hidden Civilization Details")
        logging.debug("=" * 60)
        for system in self.star_systems.values():
            self._log_system_profile(system)
            self._observe_system(system)
        logging.debug("=" * 60)

        self.current_director = self.generate_director()
        self.directors.append(self.current_director)

        for tech_id in self.LEGACY_TECHS:
            tech = self.technologies.get(tech_id)
            if tech:
                tech.researched = True
                tech.is_legacy = True
                logging.info(f"Legacy Knowledge: {tech.name} (pre-1977)")

        self.calculate_ap()

    # ------------------------------------------------------------------ persistence
    _SCALAR_STATE = (
        "generation", "start_year", "funding", "research_points", "message_quality", "public_support",
        "knowledge_base", "game_over", "game_over_reason", "victory", "philosophical_victory",
        "self_destruct_risk", "ecological_risk", "action_points", "max_action_points", "ap_modifier",
        "advisor_consulted_this_gen", "broadcast_radius", "leakage_multiplier",
        "actions_this_generation", "idle_generations",
    )
    _FLAG_STATE = (
        "passive_defense_bonus", "warning_time_bonus", "has_backup_colonies", "cloaking_active",
        "ai_advisor_unlocked", "can_contact_post_biological", "ultimate_survival", "has_solar_sails",
        "has_laser_sails", "message_delivery_speed", "von_neumann_defense_bonus", "has_fusion_propulsion",
        "can_send_heavy_probes",
    )

    def to_dict(self) -> Dict[str, Any]:
        """Complete game state (including hidden information) as JSON-compatible data."""
        event = self.pending_philosophical_event
        return {
            "seed": self.seed,
            "civ_seed_base": self.civ_seed_base,
            "state": {name: getattr(self, name) for name in self._SCALAR_STATE},
            "flags": {name: getattr(self, name) for name in self._FLAG_STATE},
            "undiscovered": list(self.undiscovered),
            "star_systems": [system.to_dict() for system in self.star_systems.values()],
            "directors": [director.to_dict() for director in self.directors],
            "technologies": {
                tech_id: {"researched": tech.researched, "is_legacy": tech.is_legacy, "chosen_doctrine": tech.chosen_doctrine}
                for tech_id, tech in self.technologies.items() if tech.researched or tech.chosen_doctrine
            },
            "active_doctrines": list(self.active_doctrines),
            "pending_attack_warnings": [warning.to_dict() for warning in self.pending_attack_warnings],
            "pending_info_attacks": [[name, arrival] for name, arrival in self.pending_info_attacks],
            "wow_signal": self.wow_signal.to_dict(),
            "swan_songs": self.swan_song_manager.to_dict(),
            "scanned_for_swan_song": sorted(self.scanned_for_swan_song),
            "integration": self.integration.to_dict(),
            "philosophical_events": self.philosophical_events.to_dict(),
            "pending_philosophical_event": event.id if event else None,
            "fermi_evidence": dict(self.fermi_evidence),
            "genesis": self.genesis.to_dict(),
            "stats": dict(self.stats),
            "achievements": list(self.achievements),
            "generation_log": [dict(entry) for entry in self.generation_log],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], offline: Optional[bool] = None,
                  data_dir: Optional[Path] = None) -> "ContactProgram":
        """Rebuild a program from to_dict() output. Unknown keys are ignored, missing ones get defaults."""
        program = cls(seed=None, offline=bool(offline) if offline is not None else False, generate=False,
                      data_dir=data_dir)
        program.seed = data.get("seed")
        # Systems discovered after the load keep the stream the game was played with.
        program.civ_seed_base = set_civ_seed_base(data.get("civ_seed_base", data.get("seed")))

        for name, value in data.get("state", {}).items():
            if name in cls._SCALAR_STATE:
                setattr(program, name, value)
        for name, value in data.get("flags", {}).items():
            if name in cls._FLAG_STATE:
                setattr(program, name, value)

        program.star_systems = {}
        for entry in data.get("star_systems", []):
            system = StarSystem.from_dict(entry)
            program.star_systems[system.name] = system
        program.undiscovered = [name for name in data.get("undiscovered", []) if name not in program.star_systems]

        program.directors = [Director.from_dict(entry) for entry in data.get("directors", [])]
        if not program.directors:
            program.directors.append(program.generate_director())
        program.current_director = program.directors[-1]

        for tech_id, tech_state in data.get("technologies", {}).items():
            tech = program.technologies.get(tech_id)
            if tech is None:
                continue  # technology removed in a later version
            tech.researched = bool(tech_state.get("researched", False))
            tech.is_legacy = bool(tech_state.get("is_legacy", False))
            tech.chosen_doctrine = tech_state.get("chosen_doctrine")
        program.active_doctrines = list(data.get("active_doctrines", []))

        program.pending_attack_warnings = []
        for entry in data.get("pending_attack_warnings", []):
            warning = AttackWarning.from_dict(entry, program.star_systems)
            if warning is not None:
                program.pending_attack_warnings.append(warning)

        program.pending_info_attacks = [[entry[0], int(entry[1])]
                                        for entry in data.get("pending_info_attacks", [])]

        program.wow_signal = WOWSignalEvent.from_dict(data.get("wow_signal", {}), program)
        program.swan_song_manager = SwanSongManager.from_dict(data.get("swan_songs", {}), program.ai, program.content)
        program.scanned_for_swan_song = set(data.get("scanned_for_swan_song", []))
        for system in program.star_systems.values():
            program._observe_system(system)
        program.integration = IntegrationProgress.from_dict(data.get("integration", {}))
        program.philosophical_events = PhilosophicalEvents.from_dict(data.get("philosophical_events", {}))
        pending_id = data.get("pending_philosophical_event")
        program.pending_philosophical_event = program.philosophical_events.events.get(pending_id) if pending_id else None
        program.fermi_evidence.update({k: v for k, v in data.get("fermi_evidence", {}).items() if k in program.fermi_evidence})
        program.genesis = GenesisProject.from_dict(data.get("genesis", {}))
        program.stats.update({k: v for k, v in data.get("stats", {}).items() if k in program.stats})
        program.achievements = list(data.get("achievements", []))
        program.generation_log = [dict(entry) for entry in data.get("generation_log", [])
                                  if isinstance(entry, dict)]
        return program

        
    def load_tech_tree(self) -> Dict[str, Technology]:
        """Load technologies from JSON"""
        try:
            path = Path(getattr(self, "data_dir", DATA_DIR)) / "tech_tree.json"
            if not path.exists():
                return {}
            with open(path, "r") as f:
                data = json.load(f)
                return {t["id"]: Technology(t) for t in data["technologies"]}
        except Exception as e:
            logging.error(f"Error loading tech tree: {e}")
            return {}

    def generate_star_systems(self, count: int = 5) -> Dict[str, StarSystem]:
        """The systems known at game start: a random handful of the nearest catalogued stars."""
        catalog = self.catalog
        if not catalog:  # no data file: synthetic neighbourhood
            catalog = [{"name": f"Star {i + 1}", "distance": round(random.uniform(4.0, 20.0), 1)} for i in range(8)]
            catalog.sort(key=lambda s: s["distance"])
            self.catalog = catalog
        nearest = catalog[:max(count, 8)]
        chosen = random.sample(nearest, min(count, len(nearest)))
        chosen.sort(key=lambda s: s["distance"])
        systems = {}
        for entry in chosen:
            systems[entry["name"]] = self._make_system(entry)
        self.undiscovered = [s["name"] for s in catalog if s["name"] not in systems]
        return systems

    @staticmethod
    def _make_system(entry: Dict[str, Any]) -> StarSystem:
        return StarSystem(entry["name"], float(entry["distance"]), entry.get("spectral_type"),
                          entry.get("ra"), entry.get("dec"))

    def _catalog_entry(self, name: str) -> Optional[Dict[str, Any]]:
        for entry in self.catalog:
            if entry["name"] == name:
                return entry
        return None
    
    def generate_director(self) -> Director:
        """Generate a new program director"""
        first_names = ["Emma", "Liam", "Olivia", "Noah", "Ava", "William", "Sophia", "James",
                       "Isabella", "Logan", "Charlotte", "Benjamin", "Amelia", "Mason", "Harper", "Elijah"]
        last_names = ["Smith", "Johnson", "Williams", "Jones", "Brown", "Davis", "Miller", "Wilson",
                      "Taylor", "Clark", "Lewis", "Lee", "Walker", "Hall", "Young", "Harris"]
        
        # A new director who shares the outgoing one's surname reads as a dynasty, or as a bug.
        # With 16 names either half repeats about once every six successions, so exclude the
        # previous director's own first name and surname from the pools.
        previous = self.directors[-1].name.split() if self.directors else []
        previous_first = previous[1] if len(previous) > 2 else None
        previous_last = previous[-1] if len(previous) > 2 else None
        firsts = [n for n in first_names if n != previous_first] or first_names
        lasts = [n for n in last_names if n != previous_last] or last_names

        name = f"Dr. {random.choice(firsts)} {random.choice(lasts)}"
        director = Director(name)
        director.generation = self.generation
        return director
    
    def _log_system_profile(self, system) -> None:
        """Write the hidden profile of one star system to the debug log."""
        name = system.name
        if not system.has_civilization:
            logging.debug(f"  {name} ({system.distance:.1f} LY) - No civilization")
            logging.debug("")
            return
        if system.is_extinct:
            logging.debug(f"  {name} ({system.distance:.1f} LY) - EXTINCT")
            logging.debug(f"    Age: {int(system.civilization_age)} years")
            logging.debug(f"    Died: {system.extinct_years_ago} years ago")
            logging.debug(f"    Swan Song: {'YES' if system.has_swan_song else 'NO'}")
            logging.debug(f"    Type: {system.civilization_type}")
        else:
            strategy_desc = {
                "L": "Listen Only - Will NEVER respond",
                "LB": "Listen & Broadcast - Enthusiastic, friendly METI",
                "LR": "Listen & Reply - Cautious, only responds when contacted",
                "LA": "Listen & Annihilate - HOSTILE, attacks silently",
                "LBA": "Listen, Broadcast & Annihilate - TRAP! Friendly bait then attack",
            }
            logging.debug(f"  {name} ({system.distance:.1f} LY) - ACTIVE")
            logging.debug(f"    Age: {int(system.civilization_age)} years")
            logging.debug(f"    Stage: {system.civilization_stage.name}")
            logging.debug(f"    Strategy: {system.true_strategy}")
            logging.debug(f"    Deception: {system.deception_level:.2f}")
            logging.debug(f"    Type: {system.civilization_type}")
            logging.debug(f"    >>> {strategy_desc.get(system.true_strategy, '?')}")
        logging.debug("")

    def _register_swan_song(self, system) -> None:
        """Give an extinct civilization its swan song record (text comes later, on discovery).

        The fields it reads are the observed ones (`StarSystem.refresh_observation`), so a
        beacon is only registered once the death itself is visible from Earth - which is also
        the year the beacon's own signal arrives. Idempotent: it runs for every system in
        every generation, and a death that happens mid-game registers when its light lands.
        """
        if (system.has_civilization and system.is_extinct and system.has_swan_song
                and not self.swan_song_manager.has_swan_song(system.name)):
            self.swan_song_manager.create_swan_song(
                system.name, system.extinct_years_ago, system.civilization_age, system.civilization_type
            )
            logging.info(f"Swan Song created for {system.name}")

    # ------------------------------------------------------------------ the observed frame (T1)
    def _observe_system(self, system) -> Optional[str]:
        """Refresh one system's "as observed now" fields and register a death that just became
        visible. Returns what changed for the caller ("extinct", or None)."""
        change = system.refresh_observation(self.current_year)
        self._register_swan_song(system)  # a no-op unless the death is observable and left a beacon
        return change

    def _observe_sky(self, previous_year: int) -> None:
        """New light arrives: refresh every system and report what a watcher would notice.

        The sky changes on its own - a civilization we are watching advances a stage, or the
        light of its death finally reaches us - so this runs once per generation, after the
        year has advanced and before any reply is delivered. Only systems studied to
        `OBSERVATION_KNOWLEDGE_REQUIRED` are being watched closely enough to notice; the rest
        still have their fields refreshed, they just make no news.
        """
        year = self.current_year
        for name, system in list(self.star_systems.items()):
            timeline = getattr(system, "timeline", None)
            before = system.observed(previous_year) if timeline is not None else None
            self._observe_system(system)
            if timeline is None or system.knowledge < OBSERVATION_KNOWLEDGE_REQUIRED:
                continue
            after = system.observed(year)
            change = observed_change(before, after, has_beacon=system.observed_swan_song(year))
            if change is None:
                continue
            observed_year = system.observed_year(year)
            system.record_observation(year)
            self.emit("sky_change", self._sky_change_text(name, observed_year, change, after),
                      system=name, observed_year=observed_year, change=change)
            logging.info(f"SKY CHANGE: {name} ({change}) as of {format_year(observed_year)}")
            if change in ("extinction", "silence"):
                # Owner decision 4: watching the sky is the cautious strategy, and a death seen
                # with our own telescopes is evidence about the Fermi paradox.
                self.add_fermi_evidence("extinction_evidence", 1,
                                        f"{name} observed to fall silent")

    @staticmethod
    def _sky_change_text(name: str, observed_year: int, change: str, after: CivState) -> str:
        bodies = {
            "stage_up": f"they have entered the {stage_phrase(after.stage)}.",
            "silence": "their broadcasts have stopped; only an automated beacon still carries.",
            "extinction": "their broadcasts have stopped, and nothing has followed.",
            "activity": "artificial signals have appeared where the sky was quiet.",
        }
        return (f"🔭 New light from {name} (as of {format_year(observed_year)}): "
                f"{bodies.get(change, 'something has changed.')}")

    # ------------------------------------------------------------------ events, evidence, achievements
    FERMI_LABELS = {
        "extinction_evidence": "Extinction",
        "dark_forest_evidence": "Dark Forest",
        "cooperation_evidence": "Cooperation",
        "great_filter_evidence": "Great Filter",
    }

    def emit(self, event_kind: str, event_text: str, **data) -> GameEvent:
        """Record something the player should see. The UI drains events with drain_events()."""
        event = GameEvent(kind=event_kind, text=event_text, data=data, generation=self.generation)
        self.events.append(event)
        if len(self.events) > 500:
            del self.events[:-500]
        return event

    def note_player_action(self, action: str = "", summary: str = "", cost: str = "") -> None:
        """Record that the player did something this generation (anti-stagnation only).

        Called by the actions that actually went through - never by a refusal, and never by
        a read-only query - so `advance_generation` can tell a generation the player played
        from one they only clicked past. It changes no rule and costs nothing.

        When `action` and `summary` are given the same call also writes the generation log
        row (`log_action`), so an action states what it did in one place.
        """
        self.actions_this_generation += 1
        if action and summary:
            self.log_action(action, summary, cost)

    def log_action(self, action: str, summary: str, cost: str = "") -> None:
        """Append one row to `generation_log` - what the player just did, in their words.

        Separate from `note_player_action` because two things belong in the log without
        counting as anti-stagnation activity: the free advisor consultation, and the
        follow-up choices (a doctrine, a philosophical crisis) that answer an earlier action.
        """
        self.generation_log.append({"action": action, "summary": summary, "cost": cost})

    def drain_events(self) -> List[GameEvent]:
        events, self.events = self.events, []
        return events

    def add_fermi_evidence(self, kind: str, amount: int, reason: str, announce: bool = True) -> None:
        """Single entry point for Fermi Paradox evidence (the philosophical victory resource)."""
        self.fermi_evidence[kind] = self.fermi_evidence.get(kind, 0) + amount
        total = sum(self.fermi_evidence.values())
        label = self.FERMI_LABELS.get(kind, kind)
        logging.info(f"FERMI EVIDENCE: +{amount} {label} ({reason}) -> {total}/15")
        if announce:
            self.emit("fermi_evidence", f"🔭 Fermi evidence +{amount} ({label}): {reason}. Total {total}/15.",
                      kind=kind, amount=amount, total=total, reason=reason)

    def unlock_achievement(self, name: str) -> None:
        if name in self.achievements:
            return
        self.achievements.append(name)
        logging.info(f"ACHIEVEMENT UNLOCKED: {name}")
        self.emit("achievement", f"🏆 Achievement unlocked: {name}", name=name)

    def _end_game(self, reason: str, text: str) -> None:
        self.game_over = True
        self.game_over_reason = reason
        logging.critical(f"GAME OVER: {reason}")
        self.emit("game_over", text, reason=reason)

    def _researched(self, tech_id: str) -> bool:
        tech = self.technologies.get(tech_id)
        return bool(tech and tech.researched)

    def contacted_systems(self) -> List[StarSystem]:
        """Living civilizations that have answered at least one message."""
        return [s for s in self.star_systems.values()
                if s.has_civilization and not s.is_extinct and len(s.received_messages) > 0]

    def tech_lock_reason(self, tech) -> Optional[str]:
        """Why an otherwise available technology cannot be researched right now (None if it can)."""
        if tech.tier >= 5 and not self.integration.can_research_tier5():
            return f"requires 40% integration progress (currently {self.integration.integration_level:.0%})"
        return None

    def _transmission_bonus(self) -> float:
        """Extra response chance from high-power directed transmissions."""
        return 0.10 if self.has_laser_sails else 0.0

    FLEET_SPEED_C = 0.10  # hostile fleets travel at a tenth of light speed (no FTL in this universe)

    def base_research_income(self) -> float:
        """Research points per generation from funding alone."""
        return 20 + self.funding / 5

    def passive_research_income(self) -> float:
        """Research points per generation before the integration efficiency modifier."""
        return self.base_research_income() + sum(t.passive_rp for t in self.technologies.values() if t.researched)

    def attack_arrival_generation(self, system) -> int:
        """When a fleet launched in reply to our message reaches Earth: light-speed message out, slow fleet back."""
        years = system.distance + system.distance / self.FLEET_SPEED_C
        return self.generation + max(2, math.ceil(years / 25))

    def calculate_ap(self):
        """Calculate Action Points for the current generation"""
        base_ap = 2
        
        # Public Mandate
        if self.public_support > 70:
            base_ap += 1
            
        # Well Funded
        if self.funding > 70:
            base_ap += 1
            
        # Efficient Administration
        if self.current_director.get_effective_skill("administration") > 0.7:
            base_ap += 1
            
        base_ap = max(1, base_ap + self.ap_modifier)
        self.max_action_points = base_ap
        self.action_points = base_ap

    @property
    def current_year(self) -> int:
        """The in-game year of the current generation (one generation = 25 years).

        The observed frame is built on it: what a telescope shows of a system `d` light-years
        away is `state_at(current_year - round(d))`.
        """
        return self.start_year + (self.generation - 1) * 25

    @property
    def tech_level(self) -> int:
        """Humanity's technology level: 1 + the highest researched tier (1..6)."""
        technologies = getattr(self, "technologies", None) or {}
        max_tier = max((t.tier for t in technologies.values() if t.researched), default=0)
        return 1 + max_tier

    # ------------------------------------------------------------------ optional AI text
    def ai_available(self) -> bool:
        """True when an LLM can be used for flavour text."""
        if self.offline:
            return False
        checker = getattr(self.ai, "is_available", None)
        if callable(checker):
            return bool(checker())
        return self.ai.current_provider is not None

    def _ai_text(self, prompt: str, system_prompt: str) -> Optional[str]:
        """Ask the LLM for text; None when unavailable or when it returned an error/empty string."""
        if not self.ai_available():
            return None
        try:
            text = self.ai.generate_text(prompt, system_prompt)
        except Exception as exc:  # noqa: BLE001 - flavour text must never break the game
            logging.warning(f"AI generation failed: {exc}")
            return None
        if not text or text.startswith("AI Error"):
            return None
        return text.strip()

    def compose_director_message(self) -> str:
        """Earth's WOW! reply in the current director's voice (LLM if available, else a written one)."""
        traits = ", ".join(self.current_director.traits)
        prompt = ("Compose a short (max 2 sentences) first contact message from Earth to an unknown alien "
                  f"civilization. The Director sending it has these traits: {traits}. "
                  "The tone should reflect these traits.")
        text = self._ai_text(prompt, "You are a sci-fi writer.")
        if text:
            return text
        return self.content.director_message({
            "director": self.current_director.name,
            "traits": traits.lower() or "hopeful",
            "year": self.start_year,
        })

    def compose_wow_response(self, wow_system, original_message: str) -> str:
        """The WOW! source's reply after 3,600 years (AI if available, otherwise a written fallback)."""
        context = (f"After 3,600 years, civilization from {wow_system.name} responds to 1977 WOW! Signal reply. "
                   f"144 generations passed.\n\nEarth's original message was: \"{original_message}\"\n\n"
                   "Reference this message in your response.")
        prompt = ("You are an ancient alien civilization responding after 3,600 years. Your message crosses "
                  "144 human generations. Acknowledge their original message. Be profound about time, patience, "
                  "cosmic perspective, and the courage to reach out. Keep under 300 words.")
        text = self._ai_text(context, prompt)
        if text:
            return text
        excerpt = original_message[:100] + ("..." if len(original_message) > 100 else "")
        return self.content.wow_friendly({"system": wow_system.name, "original_excerpt": excerpt})

    _ALIEN_PROMPTS = {
        "LB": ("You are enthusiastic aliens from {name}.\n{tech}\n\nBased on Earth's technological level shown above, "
               "craft your response. Be optimistic, friendly, eager to share knowledge and culture. If they have "
               "advanced tech, treat them as peers. If primitive, be encouraging."),
        "LR": ("You are cautious aliens from {name}.\n{tech}\n\nBased on Earth's technological level shown above, "
               "craft your response. Reply defensively, ask about intent, avoid sharing coordinates. If they have "
               "advanced tech, show more respect. If primitive, be more dismissive."),
        "LBA": ("You are predatory aliens from {name} pretending to be friendly.\n{tech}\n\nBased on Earth's "
                "technological level shown above, craft your response. Extract Earth's location and defenses. Be "
                "charming but subtly request tactical information. Advanced tech might make you more cautious, "
                "primitive tech might make you dismissive."),
    }

    def _reply_context(self, system, message_content: str, them: Optional[CivState] = None) -> Dict[str, Any]:
        """Placeholders available to reply templates.

        `them` is the civilization at *receipt* time (T2): the answer is written by whoever
        reads our signal, so the stage it speaks from is theirs when it arrives, not the one
        our telescopes were looking at when we sent it.
        """
        excerpt = (message_content or "").strip().replace("\n", " ")
        if len(excerpt) > 80:
            excerpt = excerpt[:77] + "..."
        their_stage = them.stage if them is not None else system.civilization_stage
        stage = their_stage.name.replace("_", " ").title() if their_stage else "Unknown"
        return {
            "system": system.name,
            "earth_excerpt": excerpt or "...",
            "tech_tier": self.tech_level - 1,
            "stage": stage,
            "year": self.start_year + (self.generation - 1) * 25,
            "distance": f"{system.distance:.1f}",
            "director": self.current_director.name,
        }

    def _compose_alien_reply(self, system, strategy: str, message_content: str,
                             them: Optional[CivState] = None) -> str:
        """Text of an alien reply: LLM when available, otherwise the written content bank.

        `them` is the state at receipt (T2), so the reply describes the civilization that read
        the message rather than the one that was visible when it was sent.
        """
        tech_context = self._build_tech_context()
        system_prompt = self._ALIEN_PROMPTS[strategy].format(name=system.name, tech=tech_context)
        text = self._ai_text(f"Human: {message_content}", system_prompt)
        if text:
            return text
        civ_type = them.civ_type if them is not None else system.civilization_type
        return self.content.alien_reply(strategy, civ_type, self._reply_context(system, message_content, them))

    def research_tech(self, tech_id: str) -> bool:
        """Attempt to research a technology"""
        if tech_id not in self.technologies:
            return False
            
        tech = self.technologies[tech_id]
        if tech.researched:
            return False
        
        # Check minimum generation requirement
        if self.generation < tech.min_generation:
            min_year = self.start_year + ((tech.min_generation - 1) * 25)
            self.message = f"Technology not yet available. Unlocks in Generation {tech.min_generation} (Year {min_year})."
            return False

        lock_reason = self.tech_lock_reason(tech)
        if lock_reason:
            self.message = f"{tech.name} is locked: {lock_reason}."
            return False
            
        # Director Science Skill: Reduces research cost
        science_skill = self.current_director.get_effective_skill("science")
        cost_modifier = 1.1 - (0.4 * science_skill)
        effective_cost = int(tech.cost * cost_modifier)
        
        if self.research_points < effective_cost:
            self.message = f"Not enough Research Points! Need {effective_cost} (Base: {tech.cost}, Director Efficiency: {int((1-cost_modifier)*100)}%)"
            return False
            
        # Check prerequisites
        for prereq_id in tech.prerequisites:
            if prereq_id not in self.technologies or not self.technologies[prereq_id].researched:
                prereq_name = self.technologies[prereq_id].name if prereq_id in self.technologies else prereq_id
                self.message = f"Prerequisite not met: {prereq_name}"
                return False
        
        # Handle Swan Song discount
        final_cost = effective_cost
        discount_msg = ""
        swan_discount = 0.0
        
        if hasattr(self, 'swan_song_manager'):
             swan_discount = self.swan_song_manager.next_tech_discount
             if swan_discount > 0:
                 final_cost = int(final_cost * (1 - swan_discount))
                 discount_msg = f" (Discounted by {int(swan_discount*100)}%)"

        if self.research_points < final_cost:
            self.message = f"Not enough Research Points! Need {final_cost} (Base: {tech.cost}, Dir: {int(effective_cost)}, Discount: {int(swan_discount*100)}%)"
            return False
            
        # Consume discount if used
        if swan_discount > 0:
            self.swan_song_manager.get_tech_discount()

        # Research complete
        self.research_points -= final_cost
        tech.researched = True
        self.note_player_action("research_tech", f"Researched {tech.name}", f"{final_cost} RP")
        self.stats["techs_researched"] += 1
        self.message = f"Researched {tech.name}!{discount_msg}\nDirector Efficiency Saved {tech.cost - effective_cost} RP."
        logging.info(f"Researched Technology: {tech.name} (Tier {tech.tier}, Gen {self.generation})")
        
        # Apply special effects
        if tech.special:
            self._apply_tech_special_effect(tech)
        
        # Check for doctrine choice
        if tech.doctrine_choice:
            return True # Signal that a choice is needed
            
        return False

    def _apply_tech_special_effect(self, tech):
        """Apply special effects from technology research"""
        if tech.special == "passive_defense_40":
            self.passive_defense_bonus = 0.6
            logging.info(f"PASSIVE DEFENSE ACTIVATED: {tech.name} - 40% damage reduction")
            self.message += f"\n🛡️ Passive Defense Online: All future attacks reduced by 40%"
            
        elif tech.special == "warning_time_bonus_2":
            self.warning_time_bonus = 2
            logging.info(f"EARLY WARNING ACTIVATED: {tech.name} - +2 generations warning time")
            self.message += f"\n⚠️ Early Warning Active: +2 generations to prepare for attacks"
            
        elif tech.special == "prevents_annihilation":
            self.has_backup_colonies = True
            logging.info(f"BACKUP COLONIES ESTABLISHED: {tech.name}")
            self.message += f"\n🌍 Backup Colonies Online: Humanity no longer depends on Earth alone"
            
        elif tech.special == "reduces_leakage":
            self.cloaking_active = True
            logging.info(f"CLOAKING ACTIVATED: {tech.name}")
            self.message += f"\n🔇 Cloaking Active: Earth's electromagnetic signature reduced"
            
        elif tech.special == "unlocks_ai_advisor":
            self.ai_advisor_unlocked = True
            logging.info(f"AI ADVISOR UNLOCKED: {tech.name}")
            self.message += f"\n🤖 AI Strategic Advisor unlocked!"
            
        elif tech.special == "unlock_post_bio_contact":
            self.can_contact_post_biological = True
            logging.info(f"POST-BIOLOGICAL CONTACT: {tech.name}")
            self.message += f"\n✨ Post-Biological Contact enabled!"
            
        elif tech.special == "ultimate_survival":
            self.ultimate_survival = True
            logging.info(f"ULTIMATE SURVIVAL: {tech.name}")
            self.message += f"\n🚀 Emergency Evacuation: Humanity WILL survive any attack"
            
        elif tech.special == "reduces_ecological_risk":
            self.ecological_risk = max(0.0, self.ecological_risk - 0.10)
            logging.info(f"ECOLOGICAL REMEDIATION: {tech.name} - Risk reduced by 10%")
            self.message += f"\n🌱 Planetary Remediation: Ecological Risk reduced by 10%"
        
        elif tech.special == "passive_eco_scrubbing":
            logging.info(f"ECO TECHNOLOGY: {tech.name} - Passive scrubbing enabled")
            self.message += f"\n🍃 Atmospheric Scrubbing: Passive ecological repair initiated"
            
        elif tech.special == "unlocks_nano_ecology":
            logging.info(f"ECO TECHNOLOGY: {tech.name} - Nano-swarm ready")
            self.message += f"\n🌫️ Nano-Ecological Swarm: Active ecological purge capability unlocked"
        
        # === PASSIVE LEAKAGE MITIGATION TECHS ===
        elif tech.special == "reduces_leakage_30":
            self.leakage_multiplier *= 0.7
            logging.info(f"LEAKAGE REDUCTION: {tech.name} - 30%")
            self.message += f"\n📡 Directional Transmission: Broadcast leakage reduced by 30%"
        
        elif tech.special == "reduces_leakage_50":
            self.leakage_multiplier *= 0.5
            logging.info(f"LEAKAGE REDUCTION: {tech.name} - 50%")
            self.message += f"\n🔇 Radio Silence Protocol: Broadcast leakage reduced by 50%"
        
        elif tech.special == "reduces_leakage_80":
            self.leakage_multiplier *= 0.2
            self.cloaking_active = True
            logging.info(f"LEAKAGE REDUCTION: {tech.name} - 80%")
            self.message += f"\n👻 Civilization Cloaking: Broadcast leakage reduced by 80%"
        
        elif tech.special == "dark_forest_protocol":
            self.leakage_multiplier = 0.0
            self.public_support -= 50
            logging.info(f"DARK FOREST PROTOCOL ACTIVATED: {tech.name}")
            self.message += f"\n🌑 Dark Forest Protocol: Complete electromagnetic silence (-50% public support)"
        
        # === PROPULSION TECHNOLOGY UNLOCKS ===
        elif tech.special == "unlocks_solar_sails":
            self.has_solar_sails = True
            logging.info(f"PROPULSION UNLOCKED: {tech.name}")
            self.message += f"\n☀️ Solar Sails: Foundation for advanced propulsion"
        
        elif tech.special == "unlocks_laser_sails":
            self.has_laser_sails = True
            self.message_delivery_speed = 0.175
            logging.info(f"PROPULSION UNLOCKED: {tech.name} - 0.175c")
            self.message += f"\n🚀 Laser Sails: high-power directed transmissions, +10% response chance"
        
        elif tech.special == "unlocks_von_neumann_defense":
            self.von_neumann_defense_bonus = 0.7
            logging.info(f"DEFENSE UNLOCKED: {tech.name}")
            self.message += f"\n🛡️ Von Neumann Defense: +30% defense against probe attacks"
        
        elif tech.special == "unlocks_fusion_propulsion":
            self.has_fusion_propulsion = True
            self.can_send_heavy_probes = True
            logging.info(f"PROPULSION UNLOCKED: {tech.name}")
            self.message += f"\n⚛️ Fusion Propulsion: Heavy payload delivery capability"
        
        elif tech.special == "unlocks_genesis":
            self.genesis.unlocked = True
            logging.info(f"GENESIS PROJECT UNLOCKED: {tech.name}")
            self.message += f"\n🌱 Genesis Project unlocked: sterile worlds can now be seeded with Earth life"

        # === INTEGRATION PROGRESS ===
        elif tech.special == "integration_30":
            self.integration.add_integration(0.3, tech.name)
            self.message += f"\n🧬 {tech.name}: +30% integration progress (+2 Fermi evidence)"
            self.add_fermi_evidence("great_filter_evidence", 2, f"{tech.name} advances the biological-technological transition", announce=False)
        
        elif tech.special == "integration_40":
            self.integration.add_integration(0.4, tech.name)
            self.message += f"\n🧠 {tech.name}: +40% integration progress (+2 Fermi evidence)"
            self.add_fermi_evidence("great_filter_evidence", 2, f"{tech.name} advances the biological-technological transition", announce=False)
        
        elif tech.special == "integration_60":
            self.integration.add_integration(0.6, tech.name)
            self.message += f"\n💾 {tech.name}: +60% integration progress (+2 Fermi evidence)"
            self.add_fermi_evidence("great_filter_evidence", 2, f"{tech.name} advances the biological-technological transition", announce=False)
            
        elif tech.special == "integration_variable":
            # The integration amount is decided by the doctrine choice that follows
            logging.info(f"INTEGRATION (variable): {tech.name} - resolved by doctrine choice")

        elif tech.special == "hybrid_civilization_complete":
            self.self_destruct_risk = 0.001
            self.integration.add_integration(0.1, tech.name)
            logging.info(f"HYBRID CIVILIZATION ACHIEVED")
            self.message += f"\n✨ HYBRID CIVILIZATION COMPLETE ✨\nSelf-destruct risk minimized."
            
        if hasattr(self, 'integration'):
            self.message += self.integration.get_display_message(self.generation)

    def choose_doctrine(self, tech_id: str, option_index: int) -> None:
        """Apply the effects of a doctrine choice attached to a researched technology."""
        tech = self.technologies.get(tech_id)
        if tech is None or not tech.doctrine_choice:
            self.message = "No doctrine choice available for that technology."
            return
        options = tech.doctrine_choice["options"]
        if not 0 <= option_index < len(options):
            option_index = 0
        option = options[option_index]
        tech.chosen_doctrine = option["name"]
        effects = option.get("effects", {})
        details = []

        if "integration" in effects:
            self.integration.add_integration(effects["integration"], f"{tech.name}: {option['name']}")
            self.add_fermi_evidence("great_filter_evidence", 2, f"{tech.name} advances the biological-technological transition", announce=False)
            details.append(f"+{int(effects['integration'] * 100)}% integration, +2 Fermi evidence (Great Filter)")
        if "public_support" in effects:
            self.public_support = max(0, min(100, self.public_support + effects["public_support"]))
            details.append(f"{effects['public_support']:+.0f}% public support")
        for key in ("self_destruct_modifier", "self_destruct_risk"):
            if key in effects:
                self.self_destruct_risk = max(0.0, self.self_destruct_risk + effects[key])
                details.append(f"{effects[key] * 100:+.1f}% self-destruct risk")
        if "funding" in effects:
            self.funding = max(0, min(100, self.funding + effects["funding"]))
            details.append(f"{effects['funding']:+.0f}% funding")

        self.active_doctrines.append(option["name"])
        summary = f"Doctrine adopted: {option['name']}"
        if details:
            summary += " (" + "; ".join(details) + ")"
        self.message = (self.message + "\n\n" if self.message else "") + summary
        self.log_action("choose_doctrine", f"Adopted the doctrine {option['name']}", "no AP")
        logging.info(f"Doctrine Adopted: {option['name']} for {tech.name}")

    def _schedule_attack(self, system, arrival_gen: int, attack_type: str = "fleet",
                         note: str = "", announce: bool = True,
                         source_stage: Optional[str] = None) -> AttackWarning:
        """Register an incoming attack. The Early Warning Network adds preparation time.

        `source_stage` is what the source was when it *launched* - the receipt year for a fleet
        answering our message, the present year for one answering our leakage. A fleet is built
        by the civilization that sends it, so its strength is fixed then; centuries later the
        senders may have advanced, fallen back or died, and none of that reaches the fleet.
        """
        bonus = self.warning_time_bonus if arrival_gen > self.generation else 0
        arrival = arrival_gen + bonus
        if source_stage is None and system.civilization_stage is not None:
            source_stage = system.civilization_stage.name
        warning = AttackWarning(system, arrival, self.generation, attack_type=attack_type,
                                source_stage_name=source_stage)
        self.pending_attack_warnings.append(warning)
        system.has_detected_earth = True
        self.stats["attacks_scheduled"] += 1
        self.add_fermi_evidence("dark_forest_evidence", 1, f"hostile launch from {system.name}", announce=announce)
        eta = warning.get_etas_remaining(self.generation)
        year = self.start_year + (arrival - 1) * 25
        logging.critical(f"HOSTILE LAUNCH: {system.name} ({attack_type}) - arrival Gen {arrival} ({eta} gens to prepare)")
        if announce:
            self.emit("attack_warning",
                      f"⚠️ HOSTILE LAUNCH DETECTED: {warning.type_label} from {system.name}.\n"
                      f"ETA: Generation {arrival} (Year {year}) - {eta} generation(s) to prepare.{note}\n"
                      "Use Defensive Actions to prepare.",
                      system=system.name, arrival_gen=arrival, eta=eta, attack_type=attack_type)
        return warning

    def process_information_attack(self, system_name: str):
        """An information-warfare attack (instant, delivered by signal)."""
        attack_type = random.choice(["corrupted_technology", "societal_manipulation", "false_hope_signal", "philosophical_weapon"])
        self.stats["info_attacks"] += 1

        if attack_type == "corrupted_technology":
            rp_loss = random.randint(100, 300)
            self.research_points = max(0, self.research_points - rp_loss)
            detail = f"Corrupted technical data spread through our research networks (-{rp_loss} RP)."
        elif attack_type == "societal_manipulation":
            support_loss = random.randint(15, 30)
            self.public_support -= support_loss
            detail = f"Engineered memes fracture public opinion (-{support_loss}% support)."
        elif attack_type == "false_hope_signal":
            funding_loss = random.randint(10, 25)
            support_loss = random.randint(5, 15)
            self.funding -= funding_loss
            self.public_support -= support_loss
            detail = f"A false promise of salvation collapses when exposed (-{funding_loss}% funding, -{support_loss}% support)."
        else:
            self.self_destruct_risk += 0.01
            support_loss = random.randint(10, 20)
            self.public_support -= support_loss
            detail = f"A philosophical weapon seeds despair in our institutions (+1% self-destruct risk, -{support_loss}% support)."

        logging.critical(f"Info Attack {system_name}: {attack_type}")
        self.emit("info_attack", f"⚠️ INFORMATION ATTACK FROM {system_name.upper()} ⚠️\n{detail}",
                  system=system_name, attack_type=attack_type)
        self.add_fermi_evidence("dark_forest_evidence", 1, f"information warfare from {system_name}")

        if self.public_support < 10 or self.funding < 20:
            self._end_game(f"The program was terminated after information warfare from {system_name}.",
                           "PROGRAM TERMINATED: information warfare destroyed public trust in the contact program.")

    def handle_philosophical_event_choice(self, choice_index: int) -> bool:
        """
        Handle player's choice for a philosophical event

        Args:
            choice_index: Index of the chosen option (0-based)

        Returns:
            True if choice was applied successfully, False otherwise
        """
        if not self.pending_philosophical_event:
            return False

        event = self.pending_philosophical_event
        result_message = self.philosophical_events.apply_choice_effects(event, choice_index, self)
        self.stats["events_resolved"] += 1
        self.add_fermi_evidence("great_filter_evidence", 1, f"humanity confronted {event.name}", announce=False)

        # Build response message
        self.message = f"""============================================================
         🤔 PHILOSOPHICAL EVENT: {event.name}
============================================================

CHOICE: {event.chosen_option}

{result_message}

+1 Fermi evidence (Great Filter): humanity confronted this crisis.
============================================================
"""
        self.log_action("respond_event", f"Answered {event.name}: {event.chosen_option}", "no AP")
        logging.info(f"PHILOSOPHICAL EVENT RESOLVED: {event.name} -> {event.chosen_option}")

        # Clear pending event
        self.pending_philosophical_event = None
        return True

    def get_philosophical_event_display(self) -> str:
        """
        Get formatted display text for pending philosophical event

        Returns:
            Formatted string for display, or empty string if no pending event
        """
        if not self.pending_philosophical_event:
            return ""

        event = self.pending_philosophical_event
        choices_text = ""
        for i, choice in enumerate(event.choices):
            choices_text += f"{i + 1}. {choice['name']}\n   {choice['description']}\n\n"

        return f"""============================================================
         🤔 PHILOSOPHICAL EVENT: {event.name}
============================================================

{event.description}

YOUR CHOICE:

{choices_text}============================================================
"""

    # ------------------------------------------------------------------ generation processing
    def advance_generation(self):
        """End the current generation: decay, risks, arrivals, attacks, income, victory checks."""
        # Anti-stagnation bookkeeping, before anything can return early: a generation the
        # player spent no action in extends the idle streak, any action at all breaks it.
        if self.actions_this_generation == 0:
            self.idle_generations += 1
        else:
            self.idle_generations = 0
        self.actions_this_generation = 0
        # A new generation starts with an empty sheet: what the player did last generation is
        # history the moment it ends (the web facade drops its undo stack at the same point).
        self.generation_log = []

        self.generation += 1
        year = self.start_year + (self.generation - 1) * 25
        logging.info(f"--- Advanced to Generation {self.generation} (Year {year}) ---")
        self.emit("generation_start", f"── Generation {self.generation} begins (Year {year}) ──", year=year)

        # Twenty-five more years of light have arrived: bring every system's observed state up
        # to date and report the differences before anything else happens this generation.
        self._observe_sky(year - 25)

        # Support decay
        decay_amount = 0.5
        if self._researched("global_education"):
            decay_amount -= 0.2
        if "Patient" in self.current_director.traits:
            decay_amount -= 0.5
            logging.info("Director Trait (Patient): Reduced support decay")
        self.public_support -= max(0, decay_amount)

        # Integration penalty (only after the Gen 1-30 grace period)
        integration_support_penalty = self.integration.get_support_penalty(self.generation)
        if integration_support_penalty < 0:
            self.public_support += integration_support_penalty
            self.emit("crisis", f"🧬 Integration crisis: public support {integration_support_penalty:+.0f}% "
                                "(our biology and our technology are pulling apart).")

        # Risks: the biology-technology mismatch keeps growing until the two are integrated
        self.self_destruct_risk = self._next_self_destruct_risk()
        eco_growth = 0.0015 if self._researched("planetary_remediation") else 0.004
        if self._researched("atmospheric_scrubbing"):
            self.ecological_risk = max(0.0, self.ecological_risk - 0.001)
        self.ecological_risk = min(self.ECO_RISK_CAP, self.ecological_risk + eco_growth)

        if "Traditional" in self.current_director.traits and self.public_support < 50:
            self.public_support += 1.0
        if "Intuitive" in self.current_director.traits and random.random() < 0.05:
            self.research_points += 50
            self.emit("bonus", "💡 The director's intuition pays off: +50 RP.")

        filter_modifier = self.integration.get_filter_risk_modifier(self.generation)
        adjusted_self_destruct = self.self_destruct_risk * filter_modifier if self.generation > 30 else 0.0
        if random.random() < adjusted_self_destruct:
            self._end_game("Humanity destroyed itself; the contact program died with its civilization.",
                           "💀 GAME OVER: SELF-DESTRUCTION 💀\n\n"
                           "The instincts that built the program outran the wisdom needed to survive it.\n"
                           "Somewhere, a listener notes that another young voice has gone quiet.")
            return

        if self.generation > 30 and random.random() < self.ecological_risk:
            self.public_support -= 15
            self.emit("crisis", "🌍 EVENT: Ecological collapse. Public support -15%.")

        # Responses arriving this generation
        self._deliver_responses()

        # Information attacks whose signal reaches Earth this generation
        self._deliver_pending_info_attacks()
        if self.game_over:
            return

        # Passive electromagnetic leakage: hostile civilizations may notice Earth
        self._process_passive_leakage()
        if self.game_over:
            return

        # WOW! Signal: Generation 144
        if self.wow_signal.check_gen144_event():
            self.wow_signal.trigger_gen144_event()
            if self.game_over:
                return

        # Incoming attacks
        self._resolve_attacks()
        if self.game_over:
            return

        # Research income
        efficiency = self.integration.get_research_efficiency(self.generation)
        income = self.passive_research_income() * efficiency
        self.research_points += income
        logging.info(f"Passive RP Gain: {income:.1f} (efficiency {efficiency:.2f})")

        # Funding follows public support and the director's administration
        self.funding += (self.public_support - 50) / 10
        self.funding += 5 * self.current_director.get_effective_skill("administration")
        self.funding = max(20, min(100, self.funding))
        self.public_support = max(0, min(100, self.public_support))

        # Telescopes catalogue new star systems
        self.discover_systems()

        # Message quality improves with tech and knowledge
        self.message_quality = 1.0 + (self.tech_level * 0.1) + (self.knowledge_base / 100)

        # New director, new action points
        self.current_director = self.generate_director()
        self.directors.append(self.current_director)
        self.calculate_ap()
        self.advisor_consulted_this_gen = False

        # A player who has stopped acting gets the analyst's read of the board, unasked. It is
        # the same rule-based briefing the AI Strategic Advisor prints, so it needs neither
        # that technology nor the once-per-generation consultation - and it changes no rule.
        if self.idle_generations >= 2 and self.idle_generations % 2 == 0:
            briefing = self.ai_advisor._rule_based_briefing(self)
            self.emit("briefing",
                      f"Mission analyst's briefing (the program has been idle for "
                      f"{self.idle_generations} generations):{briefing}",
                      idle_generations=self.idle_generations)

        # Genesis Project worlds evolve
        self.genesis.advance_generation(self)

        # Contact victory (the game continues afterwards)
        contacted = self.contacted_systems()
        if len(contacted) >= 3 and not self.victory:
            self.victory = True
            names = ", ".join(s.name for s in contacted)
            self.emit("victory", f"""
============================================================
       🎉 ACHIEVEMENT UNLOCKED: FIRST CONTACT NETWORK 🎉
============================================================

You have established contact with {len(contacted)} distinct civilizations: {names}.
Humanity is no longer alone in the dark.

The program continues. Foster these relationships, warn them of dangers,
or seek the answer to the ultimate question.
============================================================
""", contacts=[s.name for s in contacted])
            self.unlock_achievement("First Contact Network")
            logging.info("CONTACT VICTORY (game continues)")

        # Defunding
        if self.funding < 20 or self.public_support < 10:
            self._end_game("The contact program was defunded: public support collapsed.",
                           "GAME OVER: The contact program has been defunded due to lack of results or public support.")
            return

        # Philosophical crisis events
        if not self.pending_philosophical_event:
            event = self.philosophical_events.check_and_trigger(self)
            if event:
                self.pending_philosophical_event = event
                self.emit("philosophical_event",
                          f"🤔 PHILOSOPHICAL CRISIS: {event.name}. A decision is required before the next generation.",
                          event_id=event.id)

        # Philosophical victory (the game continues afterwards)
        self._check_philosophical_victory()

    RISK_CAP = 0.08          # self-destruct chance per generation never exceeds 8%
    RISK_FLOOR = 0.001       # ...and never drops below 0.1% once the grace period is over
    ECO_RISK_CAP = 0.30

    def _next_self_destruct_risk(self) -> float:
        """Self-destruct risk after one more generation of the Dual DNA problem."""
        level = self.integration.integration_level
        risk = self.self_destruct_risk
        if self.generation <= 30:
            risk += 0.0005      # capabilities grow faster than wisdom, slowly at first
        elif level < self.integration.crisis_threshold:
            risk += 0.0015      # crisis: destructive tools in the hands of tribal instincts
        elif level < self.integration.high_integration_threshold:
            risk += 0.0005      # the transition is under way
        else:
            risk -= 0.001       # an integrated society: the danger recedes
        floor = self.RISK_FLOOR if self.generation > 30 else 0.0
        return max(floor, min(self.RISK_CAP, risk))

    def _deliver_responses(self) -> None:
        """Alien replies whose light reaches Earth this generation."""
        for name, system in self.star_systems.items():
            arrived = [r for r in system.pending_responses if r[1] <= self.generation]
            for response in arrived:
                system.pending_responses.remove(response)
                message = response[0]
                system.received_messages.append(message)
                first = len(system.received_messages) == 1
                self._mark_message_replied(system)

                k_gain = 10 * self.tech_level
                if "Visionary" in self.current_director.traits:
                    k_gain = int(k_gain * 1.1)
                system.knowledge = min(100, system.knowledge + k_gain)
                self.knowledge_base = min(100, self.knowledge_base + 5)
                self.public_support = min(100, self.public_support + 5)
                self.stats["responses_received"] += 1

                self.emit("response_received",
                          f"📨 RESPONSE RECEIVED FROM {name.upper()}\n\"{message}\"\n\n"
                          f"Knowledge of {name} +{k_gain}%, public support +5%.",
                          system=name, text=message, first=first)
                # Evidence of cooperation: the first two replies from a civilization count, later ones do not
                replies = len(system.received_messages)
                amount = 2 if replies == 1 else (1 if replies == 2 else 0)
                if amount:
                    self.add_fermi_evidence("cooperation_evidence", amount,
                                            f"{'first' if first else 'second'} response from {name}")
                logging.info(f"Response received from {name} (reply #{replies})")

    def _mark_message_replied(self, system) -> None:
        """A reply just landed: close the oldest message on this system that was still open."""
        for entry in getattr(system, "messages_sent", []):
            if isinstance(entry, dict) and entry.get("fate") == "in_flight":
                entry["fate"] = "replied"
                self.stats["messages_replied"] += 1
                return

    def _process_passive_leakage(self) -> None:
        """Hostile civilizations inside our leakage front may detect Earth's electromagnetic leakage.

        Leakage is read in the **present** frame (T2): our radio has already reached them, so
        what decides is who they are right now, not who our telescopes can see them being.
        """
        year = self.start_year + (self.generation - 1) * 25
        self.broadcast_radius = self.leakage_system.leakage_front(year)
        for system_name, system in list(self.star_systems.items()):
            if not system.has_civilization:
                continue
            now = system.timeline_state(year)
            if not now.alive or now.strategy not in ("LA", "LBA"):
                continue
            if system.is_wow_source:
                continue  # the WOW! source has its own scripted answer in Generation 144
            if system.distance > self.broadcast_radius or system.has_detected_earth:
                continue
            detection_chance = self.leakage_system.calculate_detection_probability(
                system.distance, year, self.leakage_multiplier)
            if random.random() >= detection_chance:
                continue

            system.has_detected_earth = True
            self.stats["passive_detections"] += 1
            logging.critical(f"PASSIVE DETECTION: {system_name} ({now.strategy}) detected Earth via leakage")
            attack_type = self.leakage_system.determine_attack_type(system, system.distance)
            leak_note = " They found us through our own electromagnetic leakage."
            launch_stage = now.stage.name if now.stage else None
            # The front check above means our leakage has already reached them; what remains is
            # the one-way trip of whatever they send back.
            if attack_type == "information":
                arrival = self.generation + max(1, math.ceil(system.distance / 25))
                self.pending_info_attacks.append([system_name, arrival])
                logging.info(f"LEAKAGE INFO ATTACK IN FLIGHT: {system_name} -> arrival Gen {arrival}")
            elif attack_type == "laser_sail":
                travel = self.leakage_system.calculate_travel_time(system.distance, "laser_sail")
                self._schedule_attack(system, self.generation + travel, "laser_sail_probe", note=leak_note,
                                      source_stage=launch_stage)
            else:
                travel = self.leakage_system.calculate_travel_time(system.distance, "fusion")
                self._schedule_attack(system, self.generation + travel, "fusion_strike", note=leak_note,
                                      source_stage=launch_stage)

    def _deliver_pending_info_attacks(self) -> None:
        """Information attacks in flight land when their signal finally reaches Earth."""
        for entry in list(self.pending_info_attacks):
            system_name, arrival_gen = entry[0], entry[1]
            if arrival_gen > self.generation:
                continue
            self.pending_info_attacks.remove(entry)
            source = self.star_systems.get(system_name)
            # The present frame again (T2): the weapon was aimed centuries ago, but a source
            # that has since died or turned away never finished sending it.
            now = source.timeline_state(self.current_year) if source is not None else None
            if now is None or not now.alive or now.strategy not in ("LA", "LBA"):
                logging.info(f"Information attack from {system_name} discarded: source no longer hostile")
                continue
            logging.critical(f"INFORMATION ATTACK ARRIVES: {system_name} (due Gen {arrival_gen})")
            self.process_information_attack(system_name)
            if self.game_over:
                return

    def _resolve_attacks(self) -> None:
        """Fleets that arrive this generation strike Earth."""
        for warning in list(self.pending_attack_warnings):
            etas = warning.get_etas_remaining(self.generation)
            if etas > 0:
                logging.warning(f"HOSTILE FLEET from {warning.source.name} - ETA: {etas} generations")
                continue
            self.pending_attack_warnings.remove(warning)
            self._resolve_attack(warning)
            if self.game_over:
                return

    def _resolve_attack(self, warning) -> None:
        source = warning.source
        # The fleet is as advanced as its builders were on the day it launched (T2), not as
        # they are now: whatever became of them since, it cannot reach a ship already in flight.
        launch_stage = getattr(warning, "source_stage_name", None)
        if launch_stage is None and source.civilization_stage is not None:
            launch_stage = source.civilization_stage.name
        stage_value = (CivilizationStage[launch_stage].value if launch_stage
                       else CivilizationStage.DIGITAL.value)
        tech_gap = stage_value - self.tech_level
        if tech_gap >= 2:
            base_support, base_funding, devastating, severity = 50, 40, True, "DEVASTATING"
        elif tech_gap >= 1:
            base_support, base_funding, devastating, severity = 40, 30, False, "ADVANCED"
        else:
            base_support, base_funding, devastating, severity = 25, 15, False, "SIGNIFICANT"

        multiplier = warning.defense_multiplier * self.passive_defense_bonus
        multiplier *= (1.0 - self.wow_signal.attack_damage_reduction)
        if warning.attack_type == "laser_sail_probe":
            multiplier *= self.von_neumann_defense_bonus
        support_loss = int(base_support * multiplier)
        funding_loss = int(base_funding * multiplier)
        self.stats["attacks_landed"] += 1
        logging.critical(f"ATTACK ARRIVED from {source.name}: tech gap {tech_gap}, damage multiplier {multiplier:.2f}")

        saved_by = None
        if devastating and multiplier <= 0.5:
            devastating, saved_by = False, "our defensive preparations"
        if devastating and self.has_backup_colonies:
            devastating, saved_by = False, "the backup colonies beyond Earth"
        if devastating and self.ultimate_survival:
            devastating, saved_by = False, "the emergency evacuation infrastructure"
            support_loss, funding_loss = min(support_loss, 30), min(funding_loss, 20)

        self.public_support -= support_loss
        self.funding -= funding_loss
        self.add_fermi_evidence("dark_forest_evidence", 1, f"the attack from {source.name} struck Earth", announce=False)

        defense_info = ""
        if warning.defensive_actions_taken:
            defense_info = "\n\n🛡️ Defensive actions taken: " + ", ".join(warning.defensive_actions_taken)
        defense_info += f"\nTotal damage reduction: {int((1 - multiplier) * 100)}%"

        stage_name = launch_stage or "UNKNOWN"
        if devastating:
            self._end_game(f"Earth annihilated by the {warning.type_label} from {source.name}.",
                           f"""💀 GAME OVER: EARTH ANNIHILATED 💀

{source.name}'s overwhelming technological superiority ({stage_name} vs our tech level {self.tech_level})
has proven catastrophic. The {warning.type_label} has destroyed all major population centers.
Humanity's first contact... was its last.{defense_info}

Dark Forest theory confirmed.""")
            return

        self.stats["attacks_survived"] += 1
        self.unlock_achievement("Survivor")
        survived_note = f"\nWe survived only thanks to {saved_by}." if saved_by else "\nThe program survives, but at great cost."
        self.emit("attack_resolved", f"""⚠️ {severity} ATTACK FROM {source.name.upper()} ⚠️

The {warning.type_label} has struck Earth.
Support: -{support_loss}% | Funding: -{funding_loss}%{defense_info}{survived_note}""",
                  system=source.name, support_loss=support_loss, funding_loss=funding_loss, severity=severity)

        if self.funding < 20 or self.public_support < 10:
            self._end_game(f"The program was shut down after the attack from {source.name}.",
                           "Public support and funding have collapsed. The contact program is shut down.")

    def _check_philosophical_victory(self) -> None:
        if self.philosophical_victory or self.game_over:
            return
        total_evidence = sum(self.fermi_evidence.values())
        if total_evidence < 15:
            return
        self.philosophical_victory = True
        primary = max(self.fermi_evidence.items(), key=lambda kv: kv[1])[0]
        explanations = {
            "extinction_evidence": "Most civilizations go extinct before reaching interstellar capability.",
            "dark_forest_evidence": "The galaxy is a dark forest where speaking means death.",
            "cooperation_evidence": "Peaceful civilizations exist but are extremely rare and cautious.",
            "great_filter_evidence": "The biological-technological integration crisis destroys most species.",
        }
        self.emit("victory", f"""🌟 PHILOSOPHICAL VICTORY 🌟

After {self.generation} generations, humanity has gathered sufficient evidence
to answer the Fermi Paradox:

{explanations[primary]}

Evidence collected:
- Extinction cases: {self.fermi_evidence['extinction_evidence']}
- Hostile encounters: {self.fermi_evidence['dark_forest_evidence']}
- Peaceful contacts: {self.fermi_evidence['cooperation_evidence']}
- Great Filter evidence: {self.fermi_evidence['great_filter_evidence']}

Total Evidence: {total_evidence}/15

You have answered one of humanity's greatest questions.
(The game continues...)
""", explanation=explanations[primary])
        self.unlock_achievement("Answer to Fermi")
        logging.info(f"PHILOSOPHICAL VICTORY ACHIEVED: {explanations[primary]}")

    # ------------------------------------------------------------------ special encounters
    def _spawn_mirror_system(self) -> StarSystem:
        """A newly resolved technosignature at exactly our level (the Mirror Civilization event)."""
        # A mirror of ourselves cannot live around a red giant or a white dwarf: take the nearest
        # habitable star still undiscovered and leave the others for normal discovery.
        entry = None
        for name in list(self.undiscovered):
            candidate = self._catalog_entry(name)
            if candidate is None or name in self.star_systems:
                self.undiscovered.remove(name)
                continue
            if habitability_weight(candidate.get("spectral_type")) > 0:
                self.undiscovered.remove(name)
                entry = candidate
                break
        if entry is None:
            n = 1
            while f"Technosignature TS-{n}" in self.star_systems:
                n += 1
            entry = {"name": f"Technosignature TS-{n}", "distance": round(random.uniform(18.0, 30.0), 1)}
        system = self._make_system(entry)
        system.has_civilization = True
        system.is_extinct = False
        system.has_swan_song = False
        system.civilization_age = 100
        system.civilization_stage = CivilizationStage(max(1, min(5, self.tech_level)))
        system.civilization_type = random.choice(["biological_pure", "digital_ascended", "hybrid_integrated"])
        system.deception_level = 0.2
        system.knowledge = 50
        system.set_static_timeline(self.start_year + (self.generation - 1) * 25 - 100)
        self.star_systems[system.name] = system
        self.stats["systems_discovered"] += 1
        return system

    def resolve_mirror_contact(self) -> str:
        """Outcome of 'Extend Contact' in the Mirror Civilization event: an equal, friend or foe."""
        system = self._spawn_mirror_system()
        round_trip = system.get_round_trip_time()
        ctx = {"system": system.name, "year": self.start_year + (self.generation - 1) * 25}
        intro = f"A technosignature at {system.distance:.1f} light-years has been catalogued as {system.name}."
        if random.random() < 0.5:
            system.true_strategy = "LB"
            system.civilization_attitude = 0.8
            system.set_static_timeline(system.timeline.origin_year)  # refresh: the profile is final now
            system.pending_responses.append((self.content.mirror_reply(False, ctx), self.generation + round_trip))
            self.public_support = min(100, self.public_support + 10)
            logging.info(f"MIRROR CONTACT: {system.name} friendly")
            return (f"{intro} Our message is on its way; their reply, if it comes, arrives around "
                    f"Generation {self.generation + round_trip}. Public support +10%.")
        system.true_strategy = "LA"
        system.civilization_attitude = 0.2
        system.set_static_timeline(system.timeline.origin_year)  # refresh: the profile is final now
        warning = self._schedule_attack(system, self.attack_arrival_generation(system), "mirror_fleet", announce=False)
        logging.warning(f"MIRROR CONTACT: {system.name} hostile")
        return (f"{intro} {self.content.mirror_reply(True, ctx)} "
                f"Hostile fleet ETA: Generation {warning.arrival_gen}.")

    # ------------------------------------------------------------------ public state
    def active_effects(self) -> List[str]:
        """Every permanent modifier currently in force, as short player-facing lines.

        Derived only from engine state, so a line can never promise a rule the engine does
        not apply: the flags below are exactly the ones `_apply_tech_special_effect`, the
        1977 decision and the doctrine choices set. Playtesters could see the numbers move
        and not say why; this is the list that answers that, and `view_state()` carries it.
        """
        lines: List[str] = []

        if self.wow_signal.attack_damage_reduction > 0:
            lines.append(f"Defensive mindset: -{self.wow_signal.attack_damage_reduction:.0%} attack damage")
        if self.passive_defense_bonus < 1.0:
            lines.append(f"Orbital Defense Grid: -{1 - self.passive_defense_bonus:.0%} attack damage")
        if self.warning_time_bonus:
            lines.append(f"Early Warning Network: +{self.warning_time_bonus} generations of warning")
        if self.has_backup_colonies:
            lines.append("Distributed Backup Colonies: Earth is no longer humanity's only home")
        if self.ultimate_survival:
            lines.append("Emergency Evacuation Infrastructure: humanity survives any attack")

        if self.leakage_multiplier == 0:
            lines.append("Dark Forest Protocol: total silence")
        elif self.leakage_multiplier < 1.0:
            lines.append(f"Leakage reduced by {1 - self.leakage_multiplier:.0%}")

        if self.has_laser_sails:
            lines.append("Laser sails: +10% response chance")
        if self.von_neumann_defense_bonus < 1.0:
            lines.append(f"Von Neumann Defense: -{1 - self.von_neumann_defense_bonus:.0%} probe attack damage")
        if self.has_fusion_propulsion:
            lines.append("Fusion Propulsion: heavy payloads can be delivered")
        if self.can_contact_post_biological:
            lines.append("Post-Biological Transition: post-biological minds can be addressed")
        if self.genesis.unlocked:
            lines.append("Genesis Ark Program: sterile worlds can be seeded")
        if self.ai_advisor_unlocked:
            lines.append("AI Strategic Advisor: a free briefing once per generation")

        integration = self.integration.get_integration_status(self.generation)
        if integration["status"].startswith("CRISIS") and self.generation > 30:
            lines.append("Integration crisis: -10% public support per generation")
            lines.append("Integration crisis: +20% self-destruct risk")
            lines.append("Integration crisis: -15% research income")
        elif integration["status"] == "INTEGRATED":
            lines.append("High integration: -30% self-destruct risk")

        for doctrine in self.active_doctrines:
            lines.append(f"Doctrine: {doctrine}")
        return lines

    def view_state(self) -> Dict[str, Any]:
        """Everything the player may see, as plain data. Hidden strategies never appear here."""
        year = self.start_year + (self.generation - 1) * 25
        director = self.current_director
        systems = []
        for index, (name, s) in enumerate(self.star_systems.items(), 1):
            systems.append({
                "index": index,
                "name": name,
                "distance": round(s.distance, 1),
                "spectral_type": getattr(s, "spectral_type", None),
                "ra": getattr(s, "ra", None),
                "dec": getattr(s, "dec", None),
                "knowledge": int(s.knowledge),
                "description": s.describe_civilization(year) if s.knowledge > 0 else "",
                "round_trip_generations": s.get_round_trip_time(),
                # Light-time honesty: what our telescopes see of this system left it
                # `distance` years ago, so everything `description` says describes that year.
                "observed_year": s.observed_year(year),
                # The dated history of what that light showed, oldest first (Focus Research
                # writes one, and so does every generation whose new light changed something).
                "observations": [dict(entry) for entry in getattr(s, "observations", [])],
                # Every message we sent, with the dates that let the UI tell the three classes
                # of silence apart (plan §8) - and nothing that would let it tell them apart
                # *early*: the fate is the public one, and the year an observation will explain
                # a silence appears only once that year has come.
                "messages_sent": [{"text": m["text"], "generation": m["generation"],
                                   "arrival_gen": m["arrival_gen"],
                                   "expected_reply_year": m["expected_reply_year"],
                                   "explanation_year": public_explanation_year(m, year),
                                   "fate": public_message_fate(m, year)}
                                  for m in s.normalize_messages(s.messages_sent)],
                "responses": list(s.received_messages),
                "next_response_gen": min((a for _, a in s.pending_responses), default=None),
                "contacted": bool(s.received_messages),
                "is_seeded": s.is_seeded,
            })
        threats = []
        for i, w in enumerate(self.pending_attack_warnings, 1):
            threats.append({
                "index": i,
                "source": w.source.name,
                "attack_type": w.attack_type,
                "type_label": w.type_label,
                "eta": w.get_etas_remaining(self.generation),
                "arrival_gen": w.arrival_gen,
                "arrival_year": self.start_year + (w.arrival_gen - 1) * 25,
                "source_distance": round(w.source.distance, 1),
                # What the fleet was built by, on the day it launched - which is what decides
                # the damage when it lands (T2), whatever its builders have become since.
                "enemy_stage": (getattr(w, "source_stage_name", None)
                                or (w.source.civilization_stage.name if w.source.civilization_stage else "UNKNOWN")),
                "defense_pct": w.get_defense_percentage(),
                "actions_taken": list(w.defensive_actions_taken),
            })
        available = [{"id": t.id, "name": t.name, "tier": t.tier, "cost": t.cost, "description": t.description,
                      "year_context": t.year_context, "locked": self.tech_lock_reason(t)}
                     for t in self.available_technologies()]
        integration = self.integration.get_integration_status(self.generation)
        passive_rp = self.passive_research_income() * self.integration.get_research_efficiency(self.generation)
        event = self.pending_philosophical_event
        return {
            "generation": self.generation,
            "year": year,
            "start_year": self.start_year,
            "director": {
                "name": director.name,
                "traits": list(director.traits),
                "skills": {k: round(director.get_effective_skill(k), 2) for k in ("diplomacy", "science", "administration")},
            },
            "status": {
                "action_points": self.action_points,
                "max_action_points": self.max_action_points,
                "funding": round(self.funding, 1),
                "public_support": round(self.public_support, 1),
                "knowledge_base": round(self.knowledge_base, 1),
                "research_points": int(self.research_points),
                "passive_rp": round(passive_rp, 1),
                "tech_level": self.tech_level,
                "self_destruct_risk": round(self.self_destruct_risk, 4),
                "ecological_risk": round(self.ecological_risk, 4),
                "broadcast_radius": self.leakage_system.leakage_front(year),
                "leakage_multiplier": self.leakage_multiplier,
                "integration_level": integration["level"],
                "integration_status": integration["status"],
            },
            "active_doctrines": list(self.active_doctrines),
            "active_effects": self.active_effects(),
            "systems": systems,
            "catalog": {"known": len(self.star_systems), "total": max(len(self.catalog), len(self.star_systems)),
                        "undiscovered": len(self.undiscovered), "discovery_chance": round(self.discovery_chance(), 2)},
            "threats": threats,
            "technologies": {
                "researched": [t.id for t in self.technologies.values() if t.researched],
                "available": available,
            },
            "fermi_evidence": {**self.fermi_evidence, "total": sum(self.fermi_evidence.values()), "goal": 15},
            "contacts": len(self.contacted_systems()),
            "contacts_goal": 3,
            "victory": self.victory,
            "philosophical_victory": self.philosophical_victory,
            "genesis": {"unlocked": self.genesis.unlocked, "summary": self.genesis.get_summary(),
                        "worlds": self.genesis.to_dict()["worlds"],
                        "targets": self.genesis_targets()},
            "swan_song_targets": self.swan_song_targets(),
            "pending_event": None if event is None else {
                "id": event.id, "name": event.name, "description": event.description,
                "choices": [{"name": c["name"], "description": c["description"]} for c in event.choices],
            },
            "wow": {"decided": self.wow_signal.decided, "replied": self.wow_signal.wow_replied,
                    "outcome": self.wow_signal.outcome},
            "achievements": list(self.achievements),
            "stats": dict(self.stats),
            "generation_log": [dict(entry) for entry in self.generation_log],
            "actions": [{"id": a.id, "label": a.label, "cost": a.cost, "needs": list(a.needs)} for a in self.available_actions()],
            "game_over": self.game_over,
            "game_over_reason": self.game_over_reason,
        }

    def genesis_targets(self) -> List[str]:
        """Systems an ark may be launched at: studied to 20 % knowledge, sterile, habitable,
        not yet seeded, not the WOW! source.

        The knowledge floor is not a cost, it is what keeps this list honest: without it the
        list named every sterile system in the catalogue, which told the player where nobody
        lives before a single telescope was pointed at it. `has_civilization` is a fact about
        the star, not an observation, so it needs no light-time correction; the extinction
        fields around it are the observed ones.
        """
        return [s.name for s in self.star_systems.values()
                if s.knowledge >= GENESIS_KNOWLEDGE_REQUIRED
                and not s.has_civilization and not s.is_seeded and not s.is_wow_source
                and habitability_weight(s.spectral_type) > 0]

    # ------------------------------------------------------------------ discovery
    def discovery_chance(self) -> float:
        """Chance per generation of cataloguing a new star system (detection technologies add to it)."""
        bonus = sum(t.detection_bonus for t in self.technologies.values() if t.researched)
        return min(0.85, 0.10 + bonus)

    def _next_catalog_entry(self) -> Optional[Dict[str, Any]]:
        """Pop the nearest catalogued star the player has not resolved yet."""
        while self.undiscovered:
            name = self.undiscovered.pop(0)
            if name in self.star_systems:
                continue
            entry = self._catalog_entry(name)
            if entry:
                return entry
        return None

    def add_star_system(self, entry: Dict[str, Any], announce: bool = True) -> StarSystem:
        """Add a catalogued star to the known systems (its civilization, if any, is rolled on creation)."""
        system = self._make_system(entry)
        self.star_systems[system.name] = system
        self._observe_system(system)
        self._log_system_profile(system)
        self.stats["systems_discovered"] += 1
        if announce:
            kind = system.spectral_type or "unknown type"
            self.emit("system_discovered",
                      f"🔭 ADDED TO SETI TARGET LIST: {system.name} ({system.distance:.1f} LY, {kind}). "
                      "Focus Research to learn whether anyone lives there.",
                      system=system.name, distance=system.distance)
        return system

    def discover_systems(self) -> List[StarSystem]:
        """Roll for newly catalogued systems this generation."""
        found = []
        chance = self.discovery_chance()
        rolls = [chance] + ([chance / 2] if chance > 0.6 else [])
        for roll_chance in rolls:
            if not self.undiscovered:
                break
            if random.random() < roll_chance:
                entry = self._next_catalog_entry()
                if entry:
                    found.append(self.add_star_system(entry))
        return found

    # ------------------------------------------------------------------ UI-facing queries
    def undiscovered_swan_songs(self) -> List[str]:
        """Extinct systems with a swan song the player has not found yet.

        "Extinct" is the observed frame: a death only appears here once its light has reached
        Earth, i.e. from `current_year >= died_year + round(distance)` on.

        Omniscient: it knows which systems hold an archive whether or not the player has
        looked. Never show it (or its length) to the player - use `swan_song_targets()`.
        """
        return [name for name, system in self.star_systems.items()
                if system.has_civilization and system.is_extinct and system.has_swan_song
                and not self.swan_song_manager.is_discovered(name)]

    def swan_song_targets(self) -> List[str]:
        """Systems a deep scan may be pointed at: studied to 20 % knowledge, known to be
        extinct, not scanned to a null result, and not already recovered.

        Unlike `undiscovered_swan_songs()` this leaks nothing: whether the system holds an
        archive is exactly what the scan is for, so a silent system stays on the list until
        the player spends the point that empties it. The knowledge floor is what keeps the
        list honest - it is the level at which `describe_civilization` says "EXTINCT", so the
        list only ever names systems the player has already been told are dead - which, from
        the observed frame on, means dead *as observed*: `is_extinct` turns true in the
        generation the light of the death arrives, not in the year the civilization died.
        """
        return [name for name, system in self.star_systems.items()
                if system.knowledge >= SWAN_SONG_KNOWLEDGE_REQUIRED
                and system.has_civilization and system.is_extinct
                and name not in self.scanned_for_swan_song
                and not self.swan_song_manager.is_discovered(name)]

    def available_technologies(self) -> List[Technology]:
        """Researchable technologies (prerequisites met, generation reached), sorted by tier then cost."""
        result = []
        for tech in self.technologies.values():
            if tech.researched or self.generation < tech.min_generation:
                continue
            if not all(p in self.technologies and self.technologies[p].researched for p in tech.prerequisites):
                continue
            result.append(tech)
        result.sort(key=lambda t: (t.tier, t.cost))
        return result

    def available_actions(self) -> List[ActionSpec]:
        """Actions the player may take right now (drives the menu and any other front-end)."""
        actions = [
            ActionSpec("send_message", "Send Message to Star System", "1 AP", ("system", "text")),
            ActionSpec("focus_research", "Focus Research on Star System", "1 AP", ("system",)),
            ActionSpec("public_outreach", "Conduct Public Outreach Campaign", "1 AP"),
            ActionSpec("research_tech", "Research Technology", "Free", ("tech",)),
            ActionSpec("advance_generation", "Advance to Next Generation"),
        ]
        if self.pending_attack_warnings:
            actions.append(ActionSpec("defend", "Defensive Actions (Respond to Threats)", "", ("threat", "defense")))
        if self.ai_advisor_unlocked:
            actions.append(ActionSpec("consult_advisor", "Consult AI Strategic Advisor", "Free, once/gen"))
        # Candidates, not archives: the label may only count systems the player already knows
        # are extinct, never the (hidden) systems that actually hold a swan song.
        candidates = self.swan_song_targets()
        if candidates:
            plural = "" if len(candidates) == 1 else "s"
            actions.append(ActionSpec("listen_swan_song",
                                      f"Listen for Swan Song ({len(candidates)} candidate system{plural})",
                                      "1 AP", ("system",)))
        if self.genesis.unlocked:
            actions.append(ActionSpec("genesis_seed", "Genesis Ark Program (Launch Ark)",
                                      f"1 AP + {self.genesis.seed_cost_rp} RP", ("system",)))
        if self.pending_philosophical_event is not None:
            actions.append(ActionSpec("respond_event",
                                      f"Respond to Philosophical Event: {self.pending_philosophical_event.name}",
                                      "", ("choice",)))
        return actions

    def send_message(self, system_name: str, message_content: str):
        """Transmit to a system - and let the civilization that will be there answer it.

        This is the receipt frame (plan §4). Our signal needs `round(distance)` years to cross,
        and it is read on arrival, by whoever is there *then*: `state_at(now + d)`. A cautious
        neighbour may have turned expansionist, a friendly one may be dead, a pre-radio one may
        have learned to listen. None of that is visible from Earth when the message goes out -
        the observed frame is still `d` years behind - so the reply the player is promised, and
        the wording they are given, must never give the future away.
        """
        if self.action_points < 1:
            self.message = "Not enough Action Points!"
            return

        if system_name not in self.star_systems:
            self.message = f"System {system_name} not found in database."
            return

        system = self.star_systems[system_name]

        # Post-biological minds cannot be addressed with radio-era protocols
        if (system.has_civilization and not system.is_extinct
                and system.civilization_stage == CivilizationStage.POST_BIOLOGICAL
                and not self.can_contact_post_biological):
            self.message = (f"{system_name}: the structured signals from this system follow no protocol we can "
                            "address. Research Post-Biological Transition to attempt contact.")
            return

        light_years = int(round(system.distance))
        send_year = self.current_year
        receipt_year = send_year + light_years
        them = system.timeline_state(receipt_year)   # who reads this, in the year they read it

        entry = sent_message(message_content, self.generation,
                             self.generation + system.one_way_generations(),
                             send_year + 2 * light_years)
        system.messages_sent.append(entry)
        self.stats["messages_sent"] += 1

        def settle(fate: str, explanation_year: Optional[int] = None) -> None:
            """Record what will become of this message. Hidden: see `public_message_fate`."""
            entry["fate"] = fate
            entry["explanation_year"] = explanation_year
            self.stats[f"messages_{fate}"] += 1

        # Director Diplomacy Skill: Improves message quality
        diplomacy_skill = self.current_director.get_effective_skill("diplomacy")
        # Multiplier: 0.5 (incompetent) to 1.5 (expert)
        quality_multiplier = 0.5 + diplomacy_skill
        effective_quality = self.message_quality * quality_multiplier

        logging.info(f"Message Sent to {system_name} (Dir. Skill: {diplomacy_skill:.2f}, Quality Multiplier: {quality_multiplier:.2f})")

        self.action_points -= 1
        self.note_player_action("send_message", f"Sent message to {system_name}", "1 AP")

        # The WOW! source is 1,800 light-years away: whatever is there answers, if at all, in the
        # scripted response window, and nothing we learn before then reveals its nature.
        if system.is_wow_source and self.wow_signal.outcome is None:
            self.message = (f"Message sent toward {system_name} (1,800 LY). It arrives in 72 generations; "
                            f"any answer comes with the response window in Generation "
                            f"{self.wow_signal.wow_response_gen}.")
            logging.info("Message to the WOW! source queued behind the Generation 144 window")
            return

        round_trip_time = system.get_round_trip_time()

        def can_answer(state) -> bool:
            """Somebody is there, and radio-capable enough to make sense of a radio message."""
            return bool(state.alive and state.stage is not None
                        and state.stage.value >= CivilizationStage.EARLY_RADIO.value)

        if not can_answer(them):
            # Nobody will read this. What we may *say* about it depends on what Earth can see:
            # if our telescopes already show an empty or extinct system, today's wording still
            # tells the whole truth. If they show a living radio civilization, the silence has
            # to stay a silence - the observed frame will explain it when the light arrives.
            if (not them.alive) and them.died_year is not None:
                settle("died_in_flight", int(them.died_year) + light_years)
                logging.info(f"{system_name}: nobody left by {receipt_year}; the light of that death "
                             f"reaches Earth in {entry['explanation_year']}")
            else:
                settle("nobody", send_year)
            if can_answer(system.observed(send_year)):
                self.message = (f"Message sent to {system_name}. Any reply would arrive around "
                                f"Generation {self.generation + round_trip_time}.")
            elif system.has_civilization and system.is_extinct:
                self.message = f"Message sent to {system_name}. No response detected."
            else:
                self.message = f"Message sent to {system_name}, but no response capability detected."
            return

        # A hostile civilization that has already launched against us does not launch again per message
        if them.strategy in ("LA", "LBA") and system.has_detected_earth:
            settle("silent")
            self.message = f"Message sent to {system_name}. No response detected."
            logging.info(f"{them.strategy}: {system_name} already committed to attack - no new fleet")
            return

        launch_stage = them.stage.name if them.stage else None

        # L Strategy
        if them.strategy == "L":
            settle("silent")
            self.message = f"Message sent to {system_name}. No response detected."
            logging.info(f"L Strategy: {system_name} - Silent")
            return

        # LA Strategy
        elif them.strategy == "LA":
            settle("silent")
            # Deep-space monitoring picks up the launch signature of a hostile response
            warning = self._schedule_attack(system, self.attack_arrival_generation(system), "fleet",
                                            announce=False, source_stage=launch_stage)
            eta = warning.get_etas_remaining(self.generation)
            self.message = f"""⚠️⚠️⚠️ HOSTILE FLEET DETECTED ⚠️⚠️⚠️

Aggressive response from {system_name}!
Our message triggered a hostile reaction.

Our signal crossed {system.distance:.1f} light-years at light speed; their fleet, limited to a tenth
of that speed, needs far longer. Fleet ETA: Generation {warning.arrival_gen} (Year {self.start_year + (warning.arrival_gen - 1) * 25}).
Time to prepare: {eta} generations.

Use Defensive Actions in the menu to prepare.
"""

            logging.critical(f"HOSTILE FLEET DETECTED: {system_name}")
            logging.warning(f"Attack ETA: Gen {self.generation + round_trip_time} ({round_trip_time} gens to prepare)")
            return

        # LBA Strategy
        elif them.strategy == "LBA":
            if them.deception > 0.6:
                arrival_generation = self.generation + round_trip_time

                # The fleet follows the friendly reply; slower than light, it arrives later
                attack_gen = max(arrival_generation + 1, self.attack_arrival_generation(system))
                self._schedule_attack(system, attack_gen, "fleet", announce=False, source_stage=launch_stage)

                response_text = self._compose_alien_reply(system, "LBA", message_content, them)
                system.pending_responses.append((response_text, arrival_generation))

                self.message = f"Message sent to {system_name}. Response expected in ~{round_trip_time * 25} years."
                logging.warning(f"LBA Trap: {system_name} - Friendly bait, attack Gen {attack_gen}")
            else:
                # Low deception LBA - silent attack, no bait
                settle("silent")
                self._schedule_attack(system, self.attack_arrival_generation(system), "fleet",
                                      announce=False, source_stage=launch_stage)

                self.message = f"Message sent to {system_name}. No response detected."
                logging.critical(f"HOSTILE FLEET DETECTED (LBA low deception): {system_name}")
            return

        # LR Strategy
        elif them.strategy == "LR":
            # Use effective_quality instead of self.message_quality
            response_chance = 0.3 + (effective_quality * 0.2) + (0.1 * them.stage.value)
            response_chance = min(0.85, response_chance + self._transmission_bonus())

            if random.random() < response_chance:
                arrival_generation = self.generation + round_trip_time

                response_text = self._compose_alien_reply(system, "LR", message_content, them)
                system.pending_responses.append((response_text, arrival_generation))

                self.message = f"Message sent to {system_name}. Response expected in ~{round_trip_time * 25} years."
                self.public_support = min(100, self.public_support + 2)
            else:
                settle("silent")
                self.message = f"Message sent to {system_name}. No response (yet)."
            return

        # LB Strategy
        elif them.strategy == "LB":
            # Use effective_quality instead of self.message_quality
            response_chance = 0.7 + (effective_quality * 0.2)

            if random.random() < min(0.95, response_chance + self._transmission_bonus()):
                arrival_generation = self.generation + round_trip_time

                response_text = self._compose_alien_reply(system, "LB", message_content, them)
                system.pending_responses.append((response_text, arrival_generation))

                self.message = f"Message sent to {system_name}. Enthusiastic response expected!"
                self.public_support = min(100, self.public_support + 5)
            else:
                settle("silent")
                self.message = f"Message sent to {system_name}. Awaiting response..."
            return

        # Alive and radio-capable but holding no strategy at all (a system written by hand):
        # there is nobody to decide to answer.
        settle("silent")
        self.message = f"Message sent to {system_name}. No response detected."

    def focus_research(self, system_name: str):
        """Focus research efforts on a particular system"""
        if self.action_points < 1:
            self.message = "Not enough Action Points!"
            return

        if system_name not in self.star_systems:
            self.message = f"System {system_name} not found in database."
            return
            
        system = self.star_systems[system_name]
        
        # Deduct AP
        self.action_points -= 1
        self.note_player_action("focus_research", f"Focused research on {system_name}", "1 AP")

        # Research effectiveness based on science skill
        science_factor = self.current_director.get_effective_skill("science")
        knowledge_gain = 10 * science_factor
        
        # Tech Bonus: Deep Space Listening
        if "deep_space_listening" in self.technologies and self.technologies["deep_space_listening"].researched:
            knowledge_gain += 2

        # Apply knowledge gain
        old_knowledge = system.knowledge
        system.knowledge += knowledge_gain
        system.knowledge = min(100, system.knowledge)
        
        # Research points
        self.research_points += 5 * science_factor
        
        # What this study saw goes into the dossier, dated in both frames: the year we looked
        # and the year the light left. It reads the same observed state `describe_civilization`
        # does, so the history can never contradict the description.
        observed_year = system.observed_year(self.current_year)
        system.record_observation(self.current_year)
        self.message = (f"Research focused on {system_name}. Knowledge increased by {int(knowledge_gain)} points.\n"
                        f"The light we studied left {system_name} in {format_year(observed_year)}.")
        logging.info(f"Research Focused on {system_name}. Knowledge +{int(knowledge_gain)}")

        # Check for Discovery Bonus (Crossing 20% threshold)
        if old_knowledge < 20 and system.knowledge >= 20 and system.has_civilization:
            self.public_support += 20
            self.public_support = min(100, self.public_support)
            self.research_points += 50
            self.message += f"\n*** MAJOR DISCOVERY: Civilization Detected at {system_name}! (+20 Support, +50 RP) ***"
            logging.info(f"MAJOR DISCOVERY: Civilization Detected at {system_name}")

    def public_outreach(self):
        """Conduct public outreach to boost support"""
        if self.action_points < 1:
            self.message = "Not enough Action Points!"
            return
            
        # Deduct AP
        self.action_points -= 1
        self.note_player_action("public_outreach", "Ran a public outreach campaign", "1 AP")

        admin_skill = self.current_director.get_effective_skill("administration")
        support_gain = 10 + (20 * admin_skill)
        
        self.public_support += support_gain
        self.public_support = min(100, self.public_support)
        
        if admin_skill > 0.7:
            self.funding += 5
            self.funding = min(100, self.funding)
            self.message = f"Successful public outreach campaign! Public support increased by {int(support_gain)} points. Funding also increased."
        else:
            self.message = f"Public outreach campaign completed. Public support increased by {int(support_gain)} points."
    
    def _build_tech_context(self) -> str:
        """Build tech context for AI message generation"""
        researched = [t for t in self.technologies.values() if t.researched]
        
        if not researched:
            return "Humanity's Technology: Basic radio astronomy (1977)"
        
        # Separate legacy from player research
        legacy = [t for t in researched if t.is_legacy]
        modern = [t for t in researched if not t.is_legacy]
        
        context_lines = []
        context_lines.append("Humanity's Technological Capabilities:")
        
        # Legacy (baseline 1977)
        if legacy:
            context_lines.append("\nBaseline (1977):")
            for tech in legacy[:3]:  # Top 3 most significant
                context_lines.append(f"  • {tech.name}")
        
        # Recent achievements
        if modern:
            context_lines.append("\nRecent Achievements:")
            for tech in modern:
                tier_label = f"Tier {tech.tier}"
                context_lines.append(f"  • {tech.name} - {tier_label}")
        
        # Overall tech level summary
        max_tier = max(t.tier for t in researched)
        context_lines.append(f"\nOverall Tech Level: Tier {max_tier}")
        
        return "\n".join(context_lines)
    
    def consult_advisor(self):
        """Consult AI Strategic Advisor for recommendations (free, once per generation)"""
        
        # Check if tech is unlocked
        if not self.ai_advisor_unlocked:
            self.message = "AI Strategic Advisor not yet unlocked. Research 'AI Strategic Advisor' technology first."
            return
        
        # Check if already consulted this generation
        if self.advisor_consulted_this_gen:
            self.message = "AI Advisor already consulted this generation. Advice refreshes each generation."
            return
        
        # Mark as consulted
        self.advisor_consulted_this_gen = True
        self.log_action("consult_advisor", "Consulted the AI strategic advisor", "free")
        
        # Generate strategic analysis
        logging.info(f"Consulting AI Strategic Advisor - Gen {self.generation}")
        
        advice = self.ai_advisor.analyze_game_state(self)
        
        # Store in message for display
        self.message = advice
        logging.info("AI Strategic Advisor consultation complete")
    
    def listen_for_swan_song(self, system_name: str):
        """Listen for Swan Song - Attempt to discover final transmission from extinct civilization"""

        if system_name not in self.star_systems:
            self.message = f"System {system_name} not found in database."
            return

        system = self.star_systems[system_name]

        # Before the extinction check, deliberately: "X does not contain an extinct
        # civilization" is a fact about the system, and answering it for an unstudied one
        # would hand the player free reconnaissance (and, refused for free, at no cost at
        # all). 20 % is the same threshold `describe_civilization` reveals extinction at.
        if system.knowledge < SWAN_SONG_KNOWLEDGE_REQUIRED:
            self.message = "Study the system first: 20% knowledge is needed before a deep scan."
            return

        # Only reachable through the API: `swan_song_targets()` never lists these. `is_extinct`
        # is the observed frame: a civilization that dies during the game becomes a candidate in
        # the generation the light of its death (and of its beacon) reaches Earth.
        if not system.has_civilization or not system.is_extinct:
            self.message = f"{system_name} is not a candidate for a deep scan."
            return

        if self.action_points < 1:
            self.message = "Not enough Action Points!"
            return

        # Check if swan song exists
        if not system.has_swan_song:
            self.message = f"""Deep scan of {system_name} complete.

No data archives detected. This civilization left no final transmission.
Their ending remains a mystery."""
            self.action_points -= 1
            self.note_player_action("listen_swan_song", f"Deep scan of {system_name}", "1 AP")
            self.scanned_for_swan_song.add(system_name)
            logging.info(f"Swan song scan of {system_name}: None found")
            return

        # Consume action point
        self.action_points -= 1
        self.note_player_action("listen_swan_song", f"Deep scan of {system_name}", "1 AP")
        
        # Attempt discovery
        
        result = self.swan_song_manager.discover_swan_song(system_name, system.knowledge)
        
        if "error" in result:
            self.message = result["error"]
            logging.info(f"Swan song discovery attempt - {system_name}: {result['error']}")
            return
        
        # Success! Display the swan song
        logging.info(f"SWAN SONG DISCOVERED: {system_name} ({result['category']})")
        
        # Apply rewards
        rewards = result["rewards"]
        reward_msgs = []
        
        if "knowledge" in rewards:
            self.knowledge_base += rewards["knowledge"]
            self.knowledge_base = min(100, self.knowledge_base)
            reward_msgs.append(f"+{rewards['knowledge']} Knowledge")
        
        if "research_points" in rewards:
            self.research_points += rewards["research_points"]
            reward_msgs.append(f"+{rewards['research_points']} RP")
        
        if "public_support" in rewards:
            self.public_support += rewards["public_support"]
            self.public_support = min(100, max(0, self.public_support))
            if rewards["public_support"] > 0:
                reward_msgs.append(f"+{rewards['public_support']}% Support")
            else:
                reward_msgs.append(f"{rewards['public_support']}% Support")
        
        if "tech_hint" in rewards:
            reward_msgs.append("Tech Hint Unlocked")
        
        if "tech_discount" in rewards:
            discount_pct = int(rewards["tech_discount"] * 100)
            reward_msgs.append(f"{discount_pct}% discount on next tech!")
        
        # === PHASE 3A.3: Award Fermi Paradox evidence ===
        self.add_fermi_evidence("extinction_evidence", 2, f"swan song of {system_name}", announce=False)
        reward_msgs.append(f"+2 Fermi Evidence (Extinction)")
        self.stats["swan_songs_found"] += 1
        self.unlock_achievement("Archivist")
        
        # Build final message
        separator = "="*60
        self.message = f"""
{separator}
🕊️ SWAN SONG DISCOVERED: {system_name.upper()} 🕊️
{separator}

Category: {result['category'].upper()}
Extinct: {system.extinct_years_ago} years ago

{result['message']}

{separator}
REWARDS: {' | '.join(reward_msgs)}
{rewards.get('message', '')}
{separator}
"""
        
        logging.info(f"Rewards applied: {reward_msgs}")

    
    def defend_emergency(self, warning_index: int):

        """Emergency Defense Protocol - 50% damage reduction, costs ALL AP"""
        if warning_index < 0 or warning_index >= len(self.pending_attack_warnings):
            self.message = "Invalid warning index."
            return
        
        warning = self.pending_attack_warnings[warning_index]
        
        # Check if already used
        if "Emergency Defense Protocol" in warning.defensive_actions_taken:
            self.message = "Emergency Defense Protocol already activated for this threat!"
            return
        
        # Check if attack already arrived
        if warning.get_etas_remaining(self.generation) <= 0:
            self.message = "Too late! The attack has already arrived."
            return
        
        # Requires ALL action points
        if self.action_points < self.max_action_points:
            self.message = f"Emergency Defense Protocol requires ALL action points ({self.max_action_points} AP)!"
            return
        
        # Consume all AP
        self.action_points = 0
        self.note_player_action("defend", f"Emergency defense against {warning.source.name}", "all AP")
        
        # Apply defense
        warning.apply_emergency_defense()
        
        self.message = f"""🛡️ EMERGENCY DEFENSE PROTOCOL ACTIVATED 🛡️

All available resources diverted to planetary defense.
Expected damage reduction: 50%
Current total defense: {warning.get_defense_percentage()}%

Fleet from {warning.source.name} ETA: {warning.get_etas_remaining(self.generation)} generations
"""
        logging.warning(f"Emergency Defense Protocol activated against {warning.source.name}")
    
    def defend_evacuate(self, warning_index: int):
        """Evacuate Critical Infrastructure - 30% damage reduction, costs 1 AP"""
        if warning_index < 0 or warning_index >= len(self.pending_attack_warnings):
            self.message = "Invalid warning index."
            return
        
        warning = self.pending_attack_warnings[warning_index]
        
        # Check if already used
        if "Evacuation" in warning.defensive_actions_taken:
            self.message = "Evacuation already completed for this threat!"
            return
        
        # Check if attack already arrived
        if warning.get_etas_remaining(self.generation) <= 0:
            self.message = "Too late! The attack has already arrived."
            return
        
        if self.action_points < 1:
            self.message = "Not enough Action Points!"
            return
        
        # Consume 1 AP
        self.action_points -= 1
        self.note_player_action("defend", f"Evacuated infrastructure against {warning.source.name}", "1 AP")

        # Apply evacuation
        warning.apply_evacuation()
        
        self.message = f"""🚀 EVACUATION PROTOCOL INITIATED 🚀

Critical infrastructure and population being relocated.
Expected casualty reduction: 30%
Current total defense: {warning.get_defense_percentage()}%

Fleet from {warning.source.name} ETA: {warning.get_etas_remaining(self.generation)} generations
"""
        logging.warning(f"Evacuation Protocol initiated for {warning.source.name} attack")
    
    def defend_diplomacy(self, warning_index: int):
        """Attempt Diplomatic Contact - might work on low-deception LBA, costs 1 AP"""
        if warning_index < 0 or warning_index >= len(self.pending_attack_warnings):
            self.message = "Invalid warning index."
            return
        
        warning = self.pending_attack_warnings[warning_index]
        
        # Check if already used
        if "Diplomatic Contact" in warning.defensive_actions_taken:
            self.message = "Diplomatic contact already attempted for this threat!"
            return
        
        # Check if attack already arrived
        if warning.get_etas_remaining(self.generation) <= 0:
            self.message = "Too late! The attack has already arrived."
            return
        
        if self.action_points < 1:
            self.message = "Not enough Action Points!"
            return
        
        # Consume 1 AP
        self.action_points -= 1
        self.note_player_action("defend", f"Diplomatic contact with {warning.source.name}", "1 AP")

        # Apply diplomatic attempt
        warning.apply_diplomatic_attempt()
        
        # Check if diplomacy might work (only for low-deception LBA)
        success_chance = 0.0
        
        # Director Diplomacy Skill Bonus
        diplomacy_skill = self.current_director.get_effective_skill("diplomacy")
        skill_bonus = diplomacy_skill * 0.2 # Up to +20% chance
        
        # Our peace offer travels at light speed too, so it is read `d` years from now (T2):
        # the civilization that decides whether to call the fleet back is the one that will be
        # there then, not the one that launched it.
        source = warning.source
        they_answer = source.timeline_state(self.current_year + int(round(source.distance)))
        if they_answer.strategy == "LBA" and they_answer.deception < 0.4:
            success_chance = 0.3 + skill_bonus # Base 30% + skill
            
            if random.random() < success_chance:
                # Diplomacy worked! Remove the warning
                self.pending_attack_warnings.remove(warning)
                self.message = f"""🕊️ DIPLOMATIC BREAKTHROUGH! 🕊️

Our urgent diplomatic transmission reached {warning.source.name}.
Director {self.current_director.name}'s diplomatic skill ({int(diplomacy_skill*100)}%) was crucial!
After intense negotiations, they have agreed to abort their attack!

This proves that even hostile civilizations can sometimes be reasoned with.
Public support surges!
"""
                self.public_support += 30
                self.public_support = min(100, self.public_support)
                self.add_fermi_evidence("cooperation_evidence", 1, f"diplomacy turned back {warning.source.name}", announce=False)
                self.message += "\n+1 Fermi Evidence (Cooperation)"
                self.unlock_achievement("Diplomatic Breakthrough")
                logging.info(f"DIPLOMATIC SUCCESS: {warning.source.name} attack aborted!")
                return
        
        # Diplomacy failed or not applicable
        self.message = f"""📡 DIPLOMATIC TRANSMISSION SENT 📡

Desperate peace offer transmitted to {warning.source.name}.
Success probability: {int(success_chance * 100)}%
Result: {"No response..." if success_chance > 0 else "Unlikely to work against pure LA strategy"}

Fleet from {warning.source.name} ETA: {warning.get_etas_remaining(self.generation)} generations
Defense preparations: {warning.get_defense_percentage()}% damage reduction
"""
        logging.warning(f"Diplomatic attempt made against {warning.source.name} (failed)")
