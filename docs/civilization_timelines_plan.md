# Legacy of Stars — Civilization Timelines Plan (light-time as the core mechanic)

**Date:** 2026-09-03
**Basis:** owner's design intent — the game is about the speed of light: while a signal travels, both sides change, so every message is a bet on a future nobody has seen, and the only rational play is to accumulate knowledge, build resilience and prepare one's descendants for an answer that will arrive to them.
**Status:** draft for discussion; owner decisions in §9

---

## 0. Summary

Today the engine is honest about *transport* (messages, replies and fleets take light-time and
slower) but not about *change*: every civilization is generated once and never moves. A reply
that arrives twenty generations after the message is computed from a state that "was always
there", so nothing drifts during the flight and there is nothing to adapt to except our own risks.

This plan gives every civilization its own **timeline** and makes the engine evaluate it in the
three frames that physics dictates:

| Frame | Time | What it decides |
|---|---|---|
| **Observed** | `now − d` | what our telescopes show: descriptions, knowledge, extinction, swan songs, the map |
| **Receipt** | `now + d` | how they react to a message: reply, silence, fleet — from the state they will be in when our signal *arrives* |
| **Arrival** | `now + 2d` | when their answer reaches us; the text describes them at receipt time |

`d` is the distance in light-years, `now` the current in-game year. Nothing is simulated per
turn: a timeline is a short, deterministic list of dated changes rolled once per system, and
`state_at(year)` replays it. Old saves load unchanged (a system without a timeline is a static one).

Six phases, T0–T6, about 8–11 working days. Phase T4 (a deeper catalogue out to ~150 LY) is
what makes the delays *bite*: within 50 LY the one-way light-time is at most two generations,
so most drift happens during ordinary play; at 100–150 LY a message takes 4–6 generations each
way and the answer really does arrive to the player's grandchildren.

| Phase | What | Estimate | Balance |
|---|---|---|---|
| T0 | Timeline model: deterministic dated changes per civilization, `state_at()`, serialization, migration | 1–2 days | none (static timelines by default) |
| T1 | Observed frame: descriptions, knowledge, extinction and swan songs read `state_at(now − d)`; "sky change" events | 1–2 days | small |
| T2 | Receipt frame: `send_message` decides from `state_at(now + d)`; replies and fleets originate at receipt time; leakage uses `state_at(now)` | 1–2 days | moderate |
| T3 | WOW! source: an 1,800-year timeline; Gen 144 answers from the civilization as it is in year 3777 | 0.5 day | none |
| T4 | Deeper catalogue to ~150 LY, gated by detection tiers; far targets are richer and slower | 1–2 days | moderate |
| T5 | Hazard constants, statistics, tests | 1–2 days | the calibration itself |
| T6 | Web and console: sky-change flashes, observation history in the dossier, "what will they be when this arrives" hint | 1–2 days | none |

---

## 1. What changes for the player

- **Studying a system shows the past.** Focus Research reveals the system as it was `d` years
  ago; the dossier keeps a dated history of observations ("1977: digital era, cautious";
  "2077: gone silent"). Each generation new light arrives, so a watched system can visibly change
  without any action: a new **sky change** event says so.
- **Writing is a bet.** The message is answered by the civilization as it will be when the signal
  arrives. A cautious neighbour may have turned expansionist; a friendly one may be dead; a
  pre-radio one may have learned to listen. The dossier's "what they will be" is unknowable — the
  UI shows only how many years of their history the signal has to cross.
- **Extinction is an event, not a label.** Civilizations die on their timeline; we learn of it when
  the light arrives; swan songs (automated beacons) become discoverable exactly `d` years after
  the death. A message sent to a civilization that dies during the flight gets no reply, and a
  later observation explains why.
- **Far stars are the long game.** With the deeper catalogue, a 120-LY target is 5 generations
  each way: the director who sends will never know; the program has to be built to still exist,
  still listen and still understand the answer.

---

## 2. The timeline model (T0)

New module `src/civ_timeline.py`.

```python
@dataclass
class CivEvent:
    year: int                  # absolute in-game year
    kind: str                  # "stage" | "strategy" | "attitude" | "extinct"
    value: Any                 # new stage name / strategy / attitude float / None

@dataclass
class CivState:
    alive: bool
    stage: CivilizationStage | None
    strategy: str | None       # L / LB / LR / LA / LBA
    attitude: float
    civ_type: str | None
    deception: float
    died_year: int | None

class CivTimeline:
    origin_year: int           # year the civilization reached "radio" (civilization_age puts it before 1977)
    initial: CivState          # state at origin_year
    events: List[CivEvent]     # sorted by year, generated once
    def state_at(self, year: int) -> CivState
    def to_dict() / from_dict()
```

**Generation, once per system, from a per-system RNG** seeded by the game seed and the system
name (so a save reloaded and a game replayed with the same seed agree):

- `origin_year = 1977 − civilization_age` (the engine's existing age roll).
- **Stage progression** follows the existing `_age_to_stage` thresholds: the timeline gets a
  `stage` event at every year the age crosses 50 / 200 / 1000 / 10,000 / 100,000. This already
  makes young civilizations *grow during the game*: an EARLY_RADIO neighbour aged 150 in 1977
  becomes DIGITAL in 2027.
- **Extinction hazard** per century of civilization age, by stage (the Great Filter is the
  transition): PRE_RADIO 0.5 %, EARLY_RADIO 2 %, DIGITAL 3 %, INTERPLANETARY 1.5 %,
  INTERSTELLAR 0.2 %, POST_BIOLOGICAL 0.1 %. Rolled century by century from the origin up to
  `1977 + 5,000` (the horizon a 200-generation game can see, plus the WOW! source's 1,800 LY).
  Civilizations rolled extinct *before* `1977 − d` reproduce today's "extinct at start" systems
  (the current 25 % share is the calibration target for T5); those that die later are the new
  content.
- **Strategy drift**: 3 % per century to move one step along a Markov chain
  `L ↔ LR ↔ LB` and `LR → LA`, `LB → LBA` (rare, 0.5 %/century), `LA → LR` (rare); attitude
  drifts ±0.1 with each strategy change. Deception rises with age as now.
- **Civilization type** is fixed (how they solved the Dual DNA problem is their history), except
  a `digital_ascended` transition at the POST_BIOLOGICAL stage.
- **Swan song** flag stays a property of the death: rolled at the `extinct` event (80 % as now);
  category weights unchanged.

`StarSystem` keeps its current fields as a **cache of the state at creation** for backward
compatibility, plus `timeline: Optional[CivTimeline]`. Systems loaded from old saves get
`timeline = None` and behave exactly as today (static). Genesis colonies and the mirror system
are created with explicit short timelines (colony: stages from landing; mirror: one event).

Tests: determinism (same seed → same events), monotone stage progression, extinction hazard
statistics over 10,000 rolls within ±15 % of the table, `state_at` before origin is "no
civilization", serialization round trip, old-save migration.

---

## 3. Observed frame (T1)

Everything the player can see reads `system.observed(now) = timeline.state_at(now − round(d))`.

- `describe_civilization`, `view_state()["systems"][i].description`, the dossier, the map halos,
  `swan_song_targets`, `genesis_targets`, the advisor's risk assessment — all through `observed()`.
- **Knowledge stays per system** but is attached to observations: `observations: List[{year,
  observed_year, summary}]` appended by Focus Research and by automatic yearly light arrival for
  systems with `knowledge ≥ 20`. When the observed state differs from the previous observation
  (stage, strategy visible only as "signals changed", extinction), the engine emits
  `sky_change` with a one-line text: "New light from Tau Ceti (as of 2042): their broadcasts have
  stopped." Strategy itself remains hidden; only *stage*, *silence/activity* and *extinction* are
  observable. Attitude becomes visible at knowledge ≥ 60 as today.
- **Extinction and swan songs**: `is_extinct` becomes `observed(now).alive is False`;
  `extinct_years_ago` becomes `now − d − died_year` (always ≥ 0 by construction, which retires the
  v1.1 clamp); a swan song is discoverable when `now ≥ died_year + d`.
- The 20 % knowledge thresholds for deep scans and arks are unchanged.

Tests: a system whose timeline dies in 2050 at 20 LY is "alive" in observations until 2070 and
"silent for 0 years" in 2070; `sky_change` fires once per change; hidden strategy never appears
in `view_state`.

---

## 4. Receipt frame (T2)

`send_message(system, text)`:

1. `receipt_year = now + round(d)`; `them = timeline.state_at(receipt_year)`.
2. If `not them.alive` or `them.stage < EARLY_RADIO`: no reply ever; the message is logged with
   "no response" as today; the truth surfaces later through the observed frame.
3. Otherwise the existing strategy branches run with `them.strategy`, `them.attitude`,
   `them.deception`, `them.stage` (response chances unchanged). The reply text is composed for
   `them.stage`/`them.civ_type` and arrives at `now + 2d` as today.
4. Fleets (LA/LBA) launch at `receipt_year`; `attack_arrival_generation` already models
   `d + d/0.1c` from now, which is the same thing.
5. `has_detected_earth` stays per system: one committed launch per civilization.

**Passive leakage** uses `timeline.state_at(now)` (the leakage is already there; their present
state decides). **Diplomacy** during an inbound fleet uses the state at the year the diplomatic
signal arrives. **WOW! source**: see T3.

A subtle but important consequence: the reply that arrives at `now + 2d` describes a civilization
the player has *observed* only up to `now − d`; the answer is `3d` years ahead of the last thing
they saw. The dossier says so: "This reply left Tau Ceti in 2065; our last observation of them is
from 2029."

Tests: message to a civilization that dies before receipt → no reply and later a sky_change;
message to a PRE_RADIO civilization that becomes EARLY_RADIO before receipt → reply; strategy
drift LB→LBA between send and receipt → the trap fires; RNG determinism preserved for undo.

---

## 5. WOW! source (T3)

The source gets an 1,800-year timeline from 1977 (its origin is rolled as usual, so it can be
ancient). Generation 144 evaluates `state_at(1977 + 1800)`: silence, friendly or hostile from the
civilization *as it is when our reply arrives*, 72 generations of their history after the burst.
The friendly text already speaks of thirty-six centuries; the hostile text already says their
weapons would take eighteen thousand years. No other change.

---

## 6. Deeper catalogue (T4)

- Extend `data/star_catalog.json` with ~30 real stars between 50 and 150 LY, favouring G/K
  main-sequence and known planet hosts (e.g. 47 Ursae Majoris 46, 51 Pegasi 50, Upsilon Andromedae
  44, HD 10180 127, HD 40307 42, Gliese 86 35, 55 Cancri 41, Mu Arae 50, HD 69830 41,
  Epsilon Reticuli 59, Iota Horologii 56, HD 189733 64, HD 209458 159, Rho Coronae Borealis 57,
  Xi Ursae Majoris 29 (fill the 25–50 gap too), Beta Comae 30, Zeta Tucanae 28, plus a few bright
  A/F stars for colour). Distances and coordinates from Gaia DR3; the audit's habitability weights
  apply unchanged.
- Discovery is gated by distance as well as by chance: each detection tier raises the reach
  (Tier 0 → 20 LY, Tier 1 → 35, Tier 2 → 60, Tier 3 → 100, Tier 4+ → the whole catalogue); the
  nearest-first order is kept within reach. This makes the deep sky a *reward* of the technology
  tree and puts 4–6-generation delays into the mid-game.
- The map's compression constant is re-solved so 150 LY lands on the rim; the WOW! marker keeps
  its clamp.

Tests: catalogue validity, reach gating per tier, discovery statistics (median generation of the
first ≥ 80 LY discovery).

---

## 7. Balance and calibration (T5)

Targets (measured with `scripts/auto_playtest.py --runs 30`):

- share of catalogued civilizations already extinct at first observation: 20–30 % (today 25 %);
- sky-change events per 40-generation game: 3–6 (enough to feel the drift, not a news ticker);
- messages that get a different outcome than a static evaluation would have given: 10–20 %;
- victories (contact or philosophical) within ±20 % of today's rate;
- Fermi evidence sources keep working (extinction observed during play counts as extinction
  evidence: +1 per sky-change death).

Knobs: the hazard table, the drift rate, the reach table. Record the final constants in
`src/civ_timeline.py` with the measured statistics, as was done for `BASE_DETECTION`.

---

## 8. Web and console (T6)

- `sky_change` event: map flash on the star (colour shift of the halo, brief ring), journal entry,
  no modal.
- Dossier: an **Observations** list (year, observed year, one line), the "observed as of" line
  already present, and for in-flight messages: "arrives {year}; they will have {n} more years of
  history than we have seen".
- System picker and card: the light-time hint stays; add "last change seen: {year}" when any.
- Console: the dossier prints the observations list; `sky_change` prints like any event.
- Contract: `sky_change` event kind with `data {system, observed_year, change}`;
  `systems[].observations[]`; documented in `docs/web_contract.md`.

---

## 9. Owner decisions

1. **Volatility.** Hazard and drift tables in §2 (recommended: "quiet but real", 3–6 visible
   changes per game) — or a "turbulent galaxy" setting (double rates) as a difficulty option.
2. **Receipt-frame replies** (§4) — recommended yes; the alternative (evaluate at send time,
   drift only in observations) keeps today's balance but breaks the premise.
3. **Deeper catalogue to ~150 LY with tier-gated reach** (§6) — recommended yes; without it the
   delays stay within two generations and the mechanic is mostly felt through our own drift.
4. **Fermi evidence for observed extinctions** (+1 per death seen) — recommended yes, it rewards
   watching the sky, which is the cautious strategy.
5. **Knowledge decay between directors** (design_notes §1, "institutional memory") — recommended
   *not now*; it is a separate mechanic and would compound with this one.

Order if all recommendations are accepted: T0 → T1 → T2 → T3 (engine, tests green after each) →
T4 → T5 calibration → T6 → review.
