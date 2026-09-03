# Legacy of Stars — Scientific Accuracy Improvement Plan

**Date:** 2026-09-02
**Basis:** `../design/science_accuracy_audit.md` (audit from the same date)
**File status:** open, in the repository

Goal: bring the game up to its own standard (`../design/design_notes.md` §8) without breaking the
v1.0 balance. The plan is split into seven phases, on the principle of "cheap and safe first,
then whatever changes the gameplay." Each phase is self-contained: you can stop after any of them.

---

## 0. Overview

| Phase | What | Effort | Balance | Owner decision |
|---|---|---|---|---|
| 0 | Text fixes: FTL, year 5577, facts, tech descriptions | ~1 h | no change | no |
| 1 | Tech-tree years from the formula; CRISPR/CO₂ anachronisms | ~1 h | almost none | Stellar Engineering: rename or move |
| 2 | Wow!: a real source at 1800 ly, an honest Gen 144 outcome | ~3 h | small | hostile outcome: signal or fleet |
| 3 | Habitability by spectral class | ~2 h | controlled | no |
| 4 | Causality of the extinct and their swan songs | ~2 h | none | no |
| 5 | Passive leakage: wavefront by time, 1/d², delayed info attacks | ~4 h | noticeable, tunable | full rework or minimum |
| 6 | Genesis: arks instead of microbes, flight time | ~3 h | small | arks (recommended) or leave as is |
| 7 | Documents: flag as outdated, fix numbers | ~1 h | none | no |

Total 2–3 working days. Phases 0–1 are one evening and give the fixes most visible to the player.

**Recommended order:** 0 → 1 → 2 → 3 → 4 → 7, then 6 and 5 as a separate pass with a run of the
balance tests.

**Verification after each phase:**

```bash
python -m unittest discover -s tests -t . -v
LOS_SLOW=1 python -m unittest tests.test_balance -v      # after phases 3, 5, 6
python scripts/auto_playtest.py --runs 10 --seed 1        # compare stats before/after
```

Before starting, save a baseline: `python scripts/auto_playtest.py --runs 10 --seed 1 > baseline.txt`
(in the scratchpad, not in the repository). Compare `attacks_scheduled`, `info_attacks`,
`responses_received`, and the win rate.

---

## Phase 0 — Text fixes (no rule changes)

None of this touches the mechanics. Tests: `test_content`, `test_tech_tree`, `test_smoke`.

### 0.1 Remove FTL
`src/legacy_of_stars_v3.py:272`
```
"Advanced interstellar civilization with faster-than-light communication."
→ "Advanced interstellar civilization with probes and settlements in several star systems."
```

### 0.2 The Gen 144 year
- `src/game_interface.py:121`: `(Year 3577)` → `(Year 5577)`.
- `development_roadmap.md:75, 92`, `../history/phase_2a_complete.md:26, 234`: same.
- Keep `RESPONSE_GENERATION = 144` — it's already the event's "brand"; the one-generation
  discrepancy (3575 vs. 3600 years) is immaterial.

### 0.3 The Wow! scene
`src/game_interface.py:105-110`. Currently Ehman "reviews the data" on the night of August 15.
Rewrite into two lines: the night of August 15 — the telescope records the signal; "Three days
later, reviewing the printout, Dr. Jerry Ehman circles six characters and writes: Wow!".

### 0.4 System-discovery text
`src/legacy_of_stars_v3.py:1677`: `NEW STAR SYSTEM CATALOGUED` →
`ADDED TO SETI TARGET LIST`. Leave the second sentence as is.

### 0.5 Technology descriptions (`data/tech_tree.json`)

| id | Now | Becomes |
|---|---|---|
| `gravitational_wave_comm` | Gravitational Wave Communication | **Gravitational Wave Detection** — "Detect spacetime ripples from stellar-scale engineering. Kardashev Type II+ signatures." |
| `quantum_communication` | Detect quantum-encrypted signals | **Noise-Like Signal Detection** — "Advanced civilizations compress and encrypt; their traffic looks like thermal noise. Statistical detectors find structure where radio SETI sees nothing. Access to post-digital civilizations." (real hypothesis: Lachmann, Newman & Moore 2004) |
| `relativistic_communication` | Near-light-speed laser probes. Faster message delivery | **Interstellar Probe Program** — "Relativistic flyby probes carry physical archives and return imagery from nearby systems. Slower than radio, but a message that cannot be jammed." |
| `dark_forest_protocol` | Complete electromagnetic silence | "Near-total electromagnetic silence: no broadcasts, shielded radar, dimmed cities." |
| `genetic_pacification` | Remove aggressive tribal instincts from human genome | "Polygenic editing to dampen reactive aggression. Effects are partial and contested." |
| `stellar_engineering` | see Phase 1 | |

The `message_delivery_speed` flag is unused in the engine — leave it as is or remove it
(`src/legacy_of_stars_v3.py`, `_FLAG_STATE`); removing it requires editing `from_dict` — not
worth it.

### 0.6 The "Mirror Civilization" event
`src/philosophical_events.py:611-612`: remove "even nuclear detonations." Keep
"industrial pollution, radio broadcasts."

### 0.7 Facts in the documents
- `../history/passive_leakage_implementation.md:353`: "Breakthrough Starshot (NASA/ESA)" →
  "(Breakthrough Initiatives, 2016)"; `:355`: "LightSail-2 (Planetary Society)."
- `development_roadmap.md:151`: "ruled out" → "unconfirmed candidate; a 2024 analysis
  (Arecibo Wow! project) proposes a natural origin — a hydrogen cloud brightened by a magnetar
  flare".
- `README.md`, Credits: add "David Brin, 'The Great Silence' (1983)" next to Liu Cixin.

---

## Phase 1 — Tech-tree years

### 1.1 Year from the formula
- In `Technology.__init__` (`src/legacy_of_stars_v3.py:74`), compute
  `self.year_context` from `min_generation`: `START_YEAR = 1977` as a module constant,
  `f"Unlocks Gen {g}+ (Year {1977 + (g-1)*25})"` when `g > 1`, otherwise "Available from start".
- In the JSON, rename the `year_context` field to `history` and keep only real dates
  ("built 1963", "launched 1999", "Kepler launched 2009"). `Technology` reads
  `data.get("history", "")` and concatenates: "Unlocks Gen 4+ (Year 2052). Launched 2015."
- `tests/test_tech_tree.py:62-63` checks `year_context` for "1963"/"1961" — replace with
  `history`. Add a test: for every technology, the year in `year_context` equals
  `1977 + (min_generation-1)*25`.
- Check where the string is shown to the player (`grep year_context src/`): currently nowhere
  except `research_tech` (`:844`), which computes it itself. After the fix it can be shown in
  `_act_research_tech` next to the description.

### 1.2 Anachronisms
| id | min_generation | Rationale |
|---|---|---|
| `bio_engineering` | 7 → 3 | CRISPR-Cas9 is 2012; Gen 3 = 2027+. The prereq `ai_pattern_recognition` is also Gen 3. Keep Tier 3. |
| `atmospheric_scrubbing` | 6 → 4 | Industrial DAC since 2017; Gen 4 = 2052. |
| `synthetic_biology` | 9 → 7 | Follows bio_engineering; otherwise a 150-year gap. |

Moving `bio_engineering` earlier opens the integration branch 4 generations sooner. This only
gives the player more time before Gen 31 (the integration crisis), no balance risk; the
`test_integration_player_survives_past_grace_period` test only becomes more reliable.

### 1.3 Stellar Engineering — owner decision

The technology at Gen 10 (2202) — manipulating a star 225 years from now. Two options:

- **A (recommended now):** rename to **Stellar Engineering Studies** — "Design
  studies for stellar-scale signalling (Shkadov mirrors, starlifting). Theory only; the
  galaxy would notice us if we ever built one." The mechanic doesn't change, +40 RP stays.
- **B (later, if more depth is wanted):** move it to Gen 20, change the prereq of
  `post_biological_transition` from `stellar_engineering` to `dyson_sphere_detection`.
  Requires re-checking the Tier 5 chain and a balance run.

---

## Phase 2 — Wow!: source and the Gen 144 outcome

Files: `src/wow_signal_event.py`, `src/legacy_of_stars_v3.py`, `src/game_interface.py`,
`data/templates/wow_responses.json`, `tests/test_discovery.py:119-145`.

### 2.1 A dedicated source system
- On `reply()`, create `StarSystem("Wow! source (Chi Sagittarii)", 1800.0, "G2V?
  (candidate 2MASS 19281982-2640123)")` and add it to `star_systems` with `is_wow_source=True`.
  Roll the presence of a civilization separately with a **0.5** chance (half of outcomes are
  "the signal was natural," and text for that already exists). Age/stage/strategy via the
  regular generator.
- The system is visible in the list: the player can send it messages (round trip 144
  generations — honest and visible) and study it via Focus Research.
- Remove `_assign_wow_civilization`; `trigger_gen144_event` uses `wow_source_system`.
- Remove "Message travels 72 generations" from `game_interface.py:120`? No — it's correct
  (1800 / 25 = 72). Keep it.
- `to_dict`/`from_dict` already serialize `wow_source_name`; the system will flow through
  `star_systems` via the shared path. Old saves without the system: when `wow_replied and
  wow_source_system is None` — create it on load (one line in `from_dict`).
- Replace the test `test_source_chosen_at_generation_144_from_known_living_civs` with
  "the source is created on reply, distance 1800, the outcome depends on its strategy."

### 2.2 Hostile outcome — owner decision

- **A (recommended):** at Gen 144 their *signal* arrives, not a fleet: `process_information_attack`
  with an amplified effect (e.g., −30% support, −20% funding) and +2 dark-forest evidence.
  Text: "Their answer was not words. …Their weapons, if they exist, will take eighteen
  thousand years to arrive. Someone will have to be ready." Physically honest, dramatic,
  requires no new entities.
- **B:** keep the fleet, but with a real ETA: `attack_arrival_generation(system)` = 1800·11 / 25
  ≈ 792 generations → Gen 936. The player would see a threat that never arrives. Weaker.

The text at `src/wow_signal_event.py:214-215` ("72 generations for their weapons") gets removed
in either option.

### 2.3 Friendly outcome
No changes. Verify that `compose_wow_response` substitutes the new system name.

---

## Phase 3 — Habitability by spectral class

Files: `src/legacy_of_stars_v3.py` (`StarSystem.__init__:96`, `_spawn_mirror_system:1510`),
`src/genesis_project.py` (`seed_world`), `tests/test_civilization_types.py`.

### 3.1 The weighting function
A module-level function `habitability_weight(spectral_type: Optional[str]) -> float`:

| Class | Weight | Why |
|---|---|---|
| G, K (V) | 1.0 | Long lifetime, stable habitable zone |
| M (V) | 0.6 | Flares, tidal locking — debated but not ruled out |
| F (V, IV-V) | 0.6 | Lifetime 2–4 billion years |
| A (V) | 0.1 | Age < 0.5 billion, lifetime ~1 billion |
| IV (subgiants) | 0.5 | Delta Pavonis — an old star, planets are possible |
| III (giants), D (white dwarfs) | 0.0 | Post-MS, the former zone is burned out |
| None / unrecognized | 1.0 | Synthetic fallback with no catalog entry |

### 3.2 Preserve the expected number of civilizations
Currently 0.15 × 53 ≈ 8 civilizations in the catalog. The catalog's average weight is ≈ 0.64
(32 M, 7 G, 7 K, 5 A, 1 F, 1 D; of which 3 are giants). So the base chance for G/K =
0.15 / 0.64 ≈ **0.23**, for M ≈ 0.14. The expectation stays ~8, the distribution shifts toward
G/K stars — the balance tests shouldn't move. Factor the constant out
(`BASE_CIV_CHANCE = 0.235`) and add a test: the mean over 1000 catalog generations ≈ 8 ± 1.

### 3.3 Where else to apply it
- `seed_world`: reject at weight 0 — "No habitable planet: {spectral_type} star."
- `_spawn_mirror_system`: skip entries with weight 0 when choosing `_next_catalog_entry`
  (otherwise a "mirror civilization" at Arcturus).
- Later (not now): show the weight to the player in the dossier as "Habitability: high/low/none" —
  gives the spectral class, which is currently purely decorative, strategic meaning.

---

## Phase 4 — Causality of the extinct

Files: `src/legacy_of_stars_v3.py:115, 244-250`, `data/templates/swan_songs.json`.

- `extinct_years_ago = random.randint(max(50, int(distance)), 5000)` — we cannot know about a
  death whose light hasn't reached us yet.
- `describe_civilization`: "Dead for ~N years" → "Silent for ~N years (as seen from
  Earth)"; "collapsed N years ago" → "went silent N years ago; automated transmissions
  continue".
- All swan songs become automated, repeating beacons. Templates in the `plea` category
  (3 of them) and the second `warning` ("Our cities have been dark for eleven days") get a
  wrapper: "[AUTOMATED RELAY — this transmission has repeated for {extinct_years_ago}
  years]" at the start. The `archive`, `technical`, and `philosophy` categories are already
  consistent.
- Test in `test_content`: every plea/warning template contains the word "relay" or "repeat".

---

## Phase 5 — Passive leakage

Files: `src/passive_leakage.py`, `src/legacy_of_stars_v3.py:1369-1397, 1092`,
`src/attack_warning.py`, `tests/test_mechanics.py`. The most balance-sensitive phase.

### 5.1 Owner decision: full rework or minimum

- **Minimum (~1 h):** only items 5.4 and 5.5 (delayed info attacks, `ceil` instead of `int`).
  Removes the causality violation; the radius model stays notional.
- **Full (~4 h, recommended):** all of 5.2–5.5. The model becomes something you can explain to
  the player ("Earth was loudest between 1960–2000; it's quieter now, but we'd already been
  heard").

### 5.2 Leakage wavefront by time
`broadcast_radius = year − 1935` (ly), where 1935 marks the start of powerful broadcasting.
In 1977 that's 42, in 2027 92, by Gen 6 167: the whole catalog is inside the wavefront after
~1986. The radius stays in the UI as "Leakage front" — an honest figure.

### 5.3 Loudness instead of radius
Probability of detection per generation by a system at distance d:

```
p = BASE × loudness(year) × leakage_multiplier × min(1, (10 / d)²)
```

- `loudness(year)`: 1.0 in 1960–2000, linear down to 0.4 by 2075 (digitization, directional
  beams), 0.4 thereafter. Each sent message to a receiving system is a separate channel
  (already implemented via strategies), the leakage doesn't duplicate it.
- `(10/d)²` — inverse square with a 10-ly reference distance (the nearest 20 systems fall in
  the 0.04–1.0 range).
- `BASE` is calibrated so the average number of detections per game matches the current one
  (0.5% × number of hostiles within radius). Reference: currently ~1–2 hostiles within radius
  25–50, ~0.5–1% per generation total. Tune `BASE` via `auto_playtest --runs 20`: the total
  `info_attacks + attacks_scheduled − attacks from messages` should stay within ±20%.
- The `has_detected_earth` flag and tech multipliers stay unchanged.

### 5.4 Delayed information attack
- New state `pending_info_attacks: List[Tuple[str, int]]` (system, arrival generation),
  serialized in `to_dict`/`from_dict` with a default of `[]`.
- On detection: `arrival = generation + system.get_round_trip_time()` (our leakage reaching
  them plus their signal reaching us). The player gets no warning — a signal attack can't be
  seen coming.
- `_deliver_responses` or a separate step in `advance_generation` applies
  `process_information_attack` when `arrival <= generation`.
- For physical attacks, ETA = `ceil(d/25) + ceil((d / v) / 25)` — the light-time of our
  leakage plus the flight. Nothing needs to change in `AttackWarning`.

### 5.5 Rounding
`calculate_travel_time`: `int(...)` → `math.ceil(...)`. Test: 10 ly at 0.175c → 3.

### 5.6 Tests and compatibility
- `test_mechanics.py:66` (info attack) — add a test for the delayed arrival.
- `test_save_load` — round trip with a non-empty `pending_info_attacks`; loading an old save
  without the field.
- `LOS_SLOW=1 test_balance` + comparison against the baseline.

---

## Phase 6 — Genesis: arks

Files: `src/genesis_project.py`, `data/tech_tree.json` (`genesis_bioprogramming`),
`data/templates/special_messages.json`, `tests/test_genesis.py`, `README.md:59`.

### 6.1 Owner decision
- **A (recommended):** reframe as the **Genesis Ark Program** — arks carrying engineered
  organisms, frozen embryos, and AI custodians aboard fusion-drive ships (embryo space
  colonization, Crowl et al. 2012). A colony with a technological head start reaches its own
  spaceflight in ~1000 years — defensible. The stage mechanic stays, only the names and
  prereqs change.
- **B:** keep the microbes and change nothing. Then item 3.3 of the audit stays open, and it's
  better to honestly call it "space opera" in the README.

### 6.2 Changes under option A
- Technology: `genesis_bioprogramming` → name "Genesis Ark Program", prereqs
  `synthetic_biology` + `fusion_propulsion` (heavy cargo, braking at the destination) instead
  of `laser_sail_propulsion`. Both stay Gen 10 — the gating doesn't change.
- `SeededWorld`: field `arrival_gen = seed_gen + ceil((distance / 0.12) / 25)`; the stages
  are counted from `arrival_gen`. For 12 ly, flight time is 100 years = 4 generations.
- Stages: `["In transit", "Colony founded", "Self-sustaining", "Industrial", "Spaceflight"]`,
  ages after arrival 0 / 10 / 25 / 40 (as now). The colony's first message ("our own genome,
  sung back") moves to the Industrial stage — that's when they go on the air.
- `seed_world`: check the habitability weight (Phase 3); the success text includes the arrival
  ETA.
- Texts `genesis_greeting` / `genesis_hostile`: "signatures in our own cells… story in the
  oldest rock" → "the ark's archive told us who built it and why"; the rest stays as is.
- README description: "Seed sterile worlds with engineered life" → "Send arks to sterile
  worlds and, forty generations after landing, meet what grew."
- Saves: `SeededWorld.from_dict` — `arrival_gen = data.get("arrival_gen", seed_gen)`.
- `test_world_evolution_stages` — account for `arrival_gen`.

---

## Phase 7 — Documents

- A header: "Historical document — describes the pre-v1.0 model (fleets at light speed, message
  probes). Current rules: README and `src/legacy_of_stars_v3.py`." in:
  `../history/attack_warning_implementation.md`, `../history/passive_leakage_implementation.md`,
  `../history/tech_tree_redesign.md`, `../history/phase_2a_complete.md`.
- `development_roadmap.md:44`: "Extinct civilizations (15%)" → "15% of stars host a
  civilization, 25% of those extinct"; `:1199`: 41 → 44 technologies, 6 tiers.
- `../design/cosmic_game_theory_analysis.md`, "Ancient Observer": replace the "Quantum Entanglement
  Communication — instant" gift with "Deep Archive: reveals the true strategy of every known
  civilization and +500 RP." Add a note: "any form of FTL is forbidden by design_notes §8."
  Same for `age_to_kardashev_scale`: mark "illustrative, not implemented."
- `../design/design_notes.md` §8: add specifics — "Every distance effect uses light-time; fleets
  0.1c, probes 0.175c, fusion 0.12c; the leakage front expands 1 ly/year; habitability
  depends on spectral class."
- (Optional, public-facing) a player-facing notes doc based on `../design/science_accuracy_audit.md` (never written; not planned for v1.0): what in the game is real, what
  is speculative, what is a convention. Useful for the README and the future web version.

---

## Owner decisions (made 2026-09-02)

1. **Stellar Engineering** (1.3): option A — rename to "Stellar Engineering Studies."
2. **Wow! hostile outcome** (2.2): option A — an information attack by signal at Gen 144.
3. **Leakage** (5.1): full rework (5.2–5.5).
4. **Genesis** (6.1): option A — Genesis Ark Program.
5. The audit and the plan are kept open in `docs/`.

If all recommendations are accepted, the order of work is: Phase 0 and 1 (one evening) → 2, 3, 4, 7
(one day) → 6 → 5 with calibration (one day).

---

## Execution (2026-09-03)

All seven phases have been implemented. A code review was carried out on top of the diff;
fixed: double-counting of light-travel time in the leakage, a missing `game_over` check after
the Gen 144 Wow! outcome, the Wow! source's participation in shared mechanics (messages, arks,
leakage), migration of Genesis stage indices from v1.0 saves, the Gen 144 year (5552 per the
engine's formula), weights for O/B/L/T/Y stars, mirror-system selection without silently
cataloguing giants, duplication of the 0.12c constant, dead code in `passive_leakage.py`.
Regression tests: `tests/test_science_review_fixes.py`.

Open question for the owner: passive leakage is calibrated to the old average (~1 detection
per 90 games) and remains rare; `BASE_DETECTION` in `src/passive_leakage.py` is the only knob.
