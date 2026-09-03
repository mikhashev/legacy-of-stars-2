"""Civilization timelines: a short, deterministic list of dated changes per civilization.

The engine is honest about transport (a signal takes `distance` years each way) but, before this
module, not about *change*: a civilization was rolled once and never moved, so a reply that
arrived twenty generations after the message was computed from a state that "was always there".

A timeline fixes that without simulating anything per turn. Every civilization gets a list of
dated `CivEvent`s rolled once, from a per-system RNG, and `state_at(year)` replays them. Three
frames then become expressible (later phases use them):

    observed  = state_at(now - d)      what our telescopes show
    receipt   = state_at(now + d)      who reads our message
    arrival   = state_at(now + 2d)     whose answer reaches us

Phase T0 only builds and stores the timelines; every existing reader still uses the cached
fields on `StarSystem`, which are the state at creation. Systems loaded from old saves have
`timeline = None` and stay static.

All constants below are the calibration knobs named in
`docs/plans/civilization_timelines_plan.md` §2 and revisited in §7 (T5).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any, Dict, List, Optional


class CivilizationStage(Enum):
    """How far a civilization has come. Defined here so the thresholds below cannot drift
    away from the engine's `StarSystem._age_to_stage`, which delegates to `stage_for_age`."""
    PRE_RADIO = 0
    EARLY_RADIO = 1
    DIGITAL = 2
    INTERPLANETARY = 3
    INTERSTELLAR = 4
    POST_BIOLOGICAL = 5


# Civilization age (years since the origin) at which the next stage begins. Index i is the age
# at which stage i is left behind, so `STAGE_AGE_THRESHOLDS[i]` promotes `CivilizationStage(i)`
# to `CivilizationStage(i + 1)`.
STAGE_AGE_THRESHOLDS = (50, 200, 1000, 10000, 100000)

# ---------------------------------------------------------------------- T5 calibration (2026-09-03)
# `docs/plans/civilization_timelines_plan.md` §7. Measured with
# `python scripts/calibrate_timelines.py --runs 30 --max-gen 60`, six sweep iterations
# (the plan's time-box), against a baseline of the pre-T1 engine (commit 2a4e0ec) run with
# `scripts/auto_playtest.py --runs 30 --seed 1` at the same generation cap. Numbers below are
# pooled across the seven measurement profiles (observer, talker, balanced, aggressive, cautious,
# integration, neglect) unless noted; per-profile detail is in the T5 section of
# `docs/plans/development_roadmap.md`.
#
#   metric                          target        measured (final)
#   extinct at first observation    20-30 %       ~20 % pooled (18-21 % per profile)
#   sky changes / 40 generations    3-6           0.4-1.0 (observer 0.99) - NOT MET, see below
#   differing message outcomes      10-20 %       ~21 % pooled (19-26 % per profile)
#   victories vs baseline (+-20 %)  within 20 %   balanced only; other 4 shared profiles over
#                                                  (aggressive +22 %, cautious +62 %,
#                                                   integration +29 %, neglect +96 %) - NOT MET
#   stage_up among first 3 changes  >= 50 %       100 % (small samples: 1-3 games/profile had
#                                                  >= 3 sky changes at this cap - low confidence)
#
# Two targets were not reached within the six-iteration time-box, and the trade-off between them
# is the reason: `sky_changes_per_40` is carried almost entirely by two things - the extinction
# hazard below (silence/extinction changes) and `BASE_CIV_CHANCE` (more watched civilizations
# means more of everything, including stage-up crossings, which turned out to be the majority
# kind). Strategy drift never reaches this metric at all: `observed_change()` in
# `legacy_of_stars_v3.py` deliberately hides strategy and attitude from the observed frame, so
# `STRATEGY_DRIFT_PER_CENTURY` and `RARE_STRATEGY_DRIFT_PER_CENTURY` do not move it. Pushing
# either hazard or `BASE_CIV_CHANCE` far enough to reach 3-6 sky changes (tried up to ~2/40 gens
# at `BASE_CIV_CHANCE = 0.5`) drove `extinct_share` past 35 %, `differing_outcomes` past 40 %, and
# victories to more than double the baseline for several profiles - failing three targets to fix
# one. The values below are the best balance found: extinction hazard and `BASE_CIV_CHANCE` both
# sit modestly above their pre-T5 placeholders (0.26 and the original per-stage table), which
# keeps `extinct_share` and `differing_outcomes` on target but still leaves victories elevated
# (more civilizations in the catalogue means more contact opportunities) and sky changes short.
# This is the plan's own escape-hatch condition (§7's time-box); the fallback itself (drift only
# in the observed frame) was not implemented - see the T5 section of development_roadmap.md.

# Chance that a civilization dies during one century of its life, by the stage it is in.
# The Great Filter is a transition, not a wall: the young radio and digital eras are by far the
# most dangerous, and anything that reaches the stars is nearly permanent. Raised modestly from
# the pre-T5 placeholders (0.005 / 0.02 / 0.03 / 0.015 / 0.002 / 0.001) during calibration.
EXTINCTION_HAZARD_PER_CENTURY = {
    "PRE_RADIO": 0.003,
    "EARLY_RADIO": 0.012,
    "DIGITAL": 0.016,
    "INTERPLANETARY": 0.008,
    "INTERSTELLAR": 0.0012,
    "POST_BIOLOGICAL": 0.0006,
}

# Chance per century that a civilization moves one step along the strategy chain L <-> LR <-> LB.
# Halved from the pre-T5 placeholder (0.03) during calibration: this drift never shows up in
# `sky_changes_per_40` (strategy is hidden from the observed frame) but does change who answers a
# message, and the higher rate was pushing victories further above the baseline than the density
# increase alone already does.
STRATEGY_DRIFT_PER_CENTURY = 0.015
# Chance per century of the rare, harder transitions into and out of an active posture. Halved
# from the pre-T5 placeholder (0.005) alongside the ordinary drift rate above.
RARE_STRATEGY_DRIFT_PER_CENTURY = 0.0025
# How far the attitude moves (up or down, clamped to 0..1) whenever the strategy changes.
ATTITUDE_DRIFT_STEP = 0.1
# Chance that a death leaves an automated beacon behind (the same 80 % the engine has always used).
SWAN_SONG_CHANCE = 0.8
# How far past 1977 a timeline is rolled: 5,000 years covers a 200-generation game and the
# WOW! source's answer in 3777.
TIMELINE_HORIZON_YEARS = 5000

# The ordinary drift chain (both directions), and the rare one-way transitions.
STRATEGY_NEIGHBOURS = {
    "L": ("LR",),
    "LR": ("L", "LB"),
    "LB": ("LR",),
    "LA": (),
    "LBA": (),
}
RARE_STRATEGY_TRANSITIONS = {
    "LR": "LA",
    "LB": "LBA",
    "LA": "LR",
}

EVENT_KINDS = ("stage", "strategy", "attitude", "extinct")
# Events that share a year are applied in this order, which also makes the sort deterministic.
_KIND_ORDER = {kind: i for i, kind in enumerate(EVENT_KINDS)}


def stage_for_age(age: float) -> CivilizationStage:
    """The stage a civilization of this age is in (the engine's `_age_to_stage`)."""
    for index, threshold in enumerate(STAGE_AGE_THRESHOLDS):
        if age < threshold:
            return CivilizationStage(index)
    return CivilizationStage(len(STAGE_AGE_THRESHOLDS))


@dataclass
class CivEvent:
    """One dated change in a civilization's history.

    `value` is JSON-compatible: a stage *name* for "stage", a strategy string for "strategy",
    a float for "attitude", and `{"has_swan_song": bool}` for "extinct".
    """
    year: int
    kind: str
    value: Any = None

    def to_dict(self) -> Dict[str, Any]:
        return {"year": int(self.year), "kind": self.kind, "value": self.value}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CivEvent":
        return cls(int(data["year"]), str(data["kind"]), data.get("value"))


@dataclass
class CivState:
    """A civilization as it is in one particular year."""
    alive: bool = False
    stage: Optional[CivilizationStage] = None
    strategy: Optional[str] = None
    attitude: float = 0.0
    civ_type: Optional[str] = None
    deception: float = 0.0
    died_year: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alive": bool(self.alive),
            "stage": self.stage.name if self.stage else None,
            "strategy": self.strategy,
            "attitude": self.attitude,
            "civ_type": self.civ_type,
            "deception": self.deception,
            "died_year": self.died_year,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CivState":
        stage = data.get("stage")
        return cls(
            alive=bool(data.get("alive", False)),
            stage=CivilizationStage[stage] if stage else None,
            strategy=data.get("strategy"),
            attitude=data.get("attitude", 0.0),
            civ_type=data.get("civ_type"),
            deception=data.get("deception", 0.0),
            died_year=data.get("died_year"),
        )


def no_civilization() -> CivState:
    """The state of a system where nobody lives (or does not live *yet*)."""
    return CivState(alive=False, stage=None, strategy=None, attitude=0.0,
                    civ_type=None, deception=0.0, died_year=None)


@dataclass
class CivTimeline:
    """A civilization's whole history as a sorted list of dated changes.

    `initial` is the state the timeline starts from at `origin_year`; every event after it is a
    change. Nothing is simulated per turn - `state_at(year)` replays the events up to `year`.
    """
    origin_year: int
    initial: CivState
    events: List[CivEvent] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.origin_year = int(self.origin_year)
        self.events = sort_events(self.events)

    # ------------------------------------------------------------------ queries
    @property
    def died_year(self) -> Optional[int]:
        for event in self.events:
            if event.kind == "extinct":
                return event.year
        return None

    @property
    def has_swan_song(self) -> bool:
        for event in self.events:
            if event.kind == "extinct":
                return bool((event.value or {}).get("has_swan_song", False))
        return False

    def state_at(self, year: int) -> CivState:
        """The civilization as it is in `year`. O(len(events)).

        Before `origin_year` there is no civilization yet: the state is "nobody home", not the
        initial state, so an observation of a young civilization from before its radio era shows
        an empty sky rather than a civilization that has not been born.
        """
        if year < self.origin_year:
            return no_civilization()
        state = replace(self.initial)
        for event in self.events:
            if event.year > year:
                break
            if not state.alive:
                break  # nothing changes after a death
            _apply(state, event)
        return state

    # ------------------------------------------------------------------ persistence
    def to_dict(self) -> Dict[str, Any]:
        return {
            "origin_year": int(self.origin_year),
            "initial": self.initial.to_dict(),
            "events": [event.to_dict() for event in self.events],
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> Optional["CivTimeline"]:
        """Rebuild a timeline; `None` in, `None` out (an old save has no timelines)."""
        if not data:
            return None
        return cls(
            origin_year=int(data.get("origin_year", 0)),
            initial=CivState.from_dict(data.get("initial", {})),
            events=[CivEvent.from_dict(entry) for entry in data.get("events", [])],
        )


def sort_events(events: List[CivEvent]) -> List[CivEvent]:
    """Events in the order they are applied: by year, then by kind."""
    return sorted(events, key=lambda e: (e.year, _KIND_ORDER.get(e.kind, len(EVENT_KINDS))))


def _apply(state: CivState, event: CivEvent) -> None:
    if event.kind == "stage":
        stage = event.value if isinstance(event.value, CivilizationStage) else CivilizationStage[event.value]
        state.stage = stage
        if stage is CivilizationStage.POST_BIOLOGICAL:
            # How they solved the Dual DNA problem is their history and does not change - except
            # that everyone who reaches the post-biological stage has ascended by definition.
            state.civ_type = "digital_ascended"
    elif event.kind == "strategy":
        state.strategy = event.value
    elif event.kind == "attitude":
        state.attitude = float(event.value)
    elif event.kind == "extinct":
        state.alive = False
        state.died_year = event.year
        # The engine's own extinct systems carry no stage and no strategy; keep that shape.
        state.stage = None
        state.strategy = None


# ---------------------------------------------------------------------- generation
def generate_timeline(rng: random.Random, origin_year: int, initial: CivState,
                      horizon_year: int, first_change_year: Optional[int] = None) -> CivTimeline:
    """Roll one civilization's whole history, deterministically from `rng`.

    `initial` is the state the timeline starts from; `origin_year` is the year the civilization
    reached the radio era (`1977 - civilization_age` for a rolled system). Three kinds of change
    are rolled, in this order per century, so the RNG stream is fixed:

    * **stage** events at every year the age crosses a `STAGE_AGE_THRESHOLDS` entry (only for
      stages above `initial.stage`, so the progression is monotone even when `initial` caches a
      later state than the origin's own);
    * **extinction**, once per century of age, at `EXTINCTION_HAZARD_PER_CENTURY[stage]`, with
      the swan-song flag rolled at the death itself; nothing is rolled after it;
    * **strategy drift** along `L <-> LR <-> LB` at `STRATEGY_DRIFT_PER_CENTURY`, plus the rare
      `LR -> LA` / `LB -> LBA` / `LA -> LR` transitions, each strategy change moving the attitude
      by +/- `ATTITUDE_DRIFT_STEP` (clamped to 0..1).

    `first_change_year` holds the hazard and drift rolls back until that year - the engine passes
    `START_YEAR` for civilizations its own roll declared alive in 1977, so a timeline can never
    contradict the state the game already shows. Stage events are unaffected (they are implied by
    the age and by `initial.stage`).
    """
    origin_year = int(origin_year)
    horizon_year = int(horizon_year)
    if not initial.alive or initial.stage is None:
        return CivTimeline(origin_year, replace(initial), [])

    events: List[CivEvent] = []
    stage_events = [
        CivEvent(origin_year + threshold, "stage", CivilizationStage(index + 1).name)
        for index, threshold in enumerate(STAGE_AGE_THRESHOLDS)
        if index + 1 > initial.stage.value and origin_year + threshold <= horizon_year
    ]
    events.extend(stage_events)

    start_year = origin_year if first_change_year is None else max(origin_year, int(first_change_year))
    strategy = initial.strategy
    attitude = float(initial.attitude)
    stage = initial.stage
    next_stage_index = 0

    first_century = max(1, math.ceil((start_year - origin_year) / 100))
    century = first_century
    while origin_year + 100 * century <= horizon_year:
        century_start = origin_year + 100 * (century - 1)
        century_end = origin_year + 100 * century
        # The stage the civilization spent this century in.
        while next_stage_index < len(stage_events) and stage_events[next_stage_index].year <= century_start:
            stage = CivilizationStage[stage_events[next_stage_index].value]
            next_stage_index += 1

        if rng.random() < EXTINCTION_HAZARD_PER_CENTURY[stage.name]:
            low = max(century_start + 1, start_year)
            died_year = rng.randrange(low, century_end + 1)
            events.append(CivEvent(died_year, "extinct",
                                   {"has_swan_song": rng.random() < SWAN_SONG_CHANCE}))
            # Drop the changes that would have happened after the death.
            events = [e for e in events if e.kind == "extinct" or e.year <= died_year]
            break

        # Two draws every century, whatever the current strategy, so the stream does not depend
        # on the strategy the civilization happens to hold.
        drift_roll = rng.random()
        rare_roll = rng.random()
        new_strategy = strategy
        if drift_roll < STRATEGY_DRIFT_PER_CENTURY and STRATEGY_NEIGHBOURS.get(strategy):
            options = STRATEGY_NEIGHBOURS[strategy]
            new_strategy = options[0] if len(options) == 1 else options[int(rng.random() * len(options))]
        elif rare_roll < RARE_STRATEGY_DRIFT_PER_CENTURY and strategy in RARE_STRATEGY_TRANSITIONS:
            new_strategy = RARE_STRATEGY_TRANSITIONS[strategy]
        if new_strategy != strategy:
            strategy = new_strategy
            step = ATTITUDE_DRIFT_STEP if rng.random() < 0.5 else -ATTITUDE_DRIFT_STEP
            attitude = min(1.0, max(0.0, attitude + step))
            events.append(CivEvent(century_end, "strategy", strategy))
            events.append(CivEvent(century_end, "attitude", attitude))
        century += 1

    return CivTimeline(origin_year, replace(initial), events)


def static_timeline(origin_year: int, state: CivState) -> CivTimeline:
    """A timeline with no changes: the civilization stays exactly as it was founded.

    Used for civilizations the engine writes by hand rather than rolls - Genesis colonies, the
    mirror civilization - so that every reader can go through `state_at()` uniformly.
    """
    return CivTimeline(int(origin_year), replace(state), [])
