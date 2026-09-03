# Legacy of Stars - Development Roadmap
**Updated**: 2026-09-03 - v1.2 civilization timelines

## ✅ v1.0 - Playable release (2026-09-02)

An audit of the "feature-complete" build found that the game could not actually be played to the
end: philosophical events could never be answered, three technologies crashed the game, passive
leakage crashed on 30% of detections, the integration penalty applied from Generation 2 instead of
31, the Genesis Project could never be unlocked, victory was statistically unreachable, and every
alien reply was an "AI Error" string without a running LLM. v1.0 fixes all of that and completes
the game:

- **Engine without I/O.** `ContactProgram` exposes `available_actions()`, a structured event
  stream (`emit()` / `drain_events()`), `view_state()` (player-visible data only) and
  `to_dict()` / `from_dict()`. The console UI (`src/game_interface.py`) renders from these, so a
  graphical or web front-end can be built later without touching the rules.
- **Offline first.** Written alien replies (per strategy and civilization type), swan songs, WOW!
  texts and a rule-based advisor in `data/templates/` and `src/content.py`; the LLM is optional
  (`src/ai_manager.py`, timeouts, never shows errors to the player). Wippy was removed.
- **Real galaxy.** `data/star_catalog.json` with ~50 real stars (distance, spectral type, RA/Dec);
  five are known at start and detection technologies catalogue the rest over the game.
- **Physics of attacks.** Fleets travel at 0.1c, so a hostile reply always leaves generations to
  prepare; one hostile civilization launches one fleet; the WOW!, Genesis and mirror fleets use
  the same resolution.
- **Balance.** Research income matches the tech tree's own timeline (funding-based income plus
  passive RP from instruments); the self-destruct risk grows only while integration is low and
  recedes above 70%; Fermi evidence comes from every kind of encounter; Genesis is unlocked by the
  new Genesis Bio-Programming technology.
- **Complete game loop.** Start menu, autosave and manual saves (`saves/`), help screen, system
  dossiers, achievements, statistics and a final report with a score.
- **Tests.** `python -m unittest discover -s tests -t .` runs unit, end-to-end and headless
  whole-game tests; `LOS_SLOW=1` adds statistical balance checks.

## v1.1 - Scientific accuracy pass (2026-09-03)

The game was audited against its own realism standard (`../design/design_notes.md` §8); the audit and
the seven-phase plan live in `../design/science_accuracy_audit.md` and `science_accuracy_plan.md`.
All phases are implemented: no FTL anywhere, technology unlock years derived from the 1977 start,
the WOW! source is a real star 1,800 LY away whose hostile answer is a signal rather than a
light-speed fleet, civilization odds depend on spectral class, extinct systems respect light-time,
the leakage front grows one light-year per year, and the Genesis Project sends embryo arks at 0.12c.

### Deferred from the code review (not in the plan, worth doing next)

- **Information attacks as `AttackWarning`s.** `pending_info_attacks` is a bare
  `[system, arrival]` list with its own delivery loop; it does not appear in `view_state()["threats"]`,
  the advisor's threat list or the final report. Add an `"information"` attack type to
  `ATTACK_TYPE_LABELS`, schedule through `_schedule_attack`, resolve in `_resolve_attack`, and let
  the WOW! hostile outcome use the same path.
- **One year formula.** `start_year + (generation - 1) * 25` appears in about a dozen places
  (`legacy_of_stars_v3.py`, `ai_strategic_advisor.py`, `summary.py`, `save_manager.py`,
  `genesis_project.py`, `game_interface.py`, plus `START_YEAR` for `Technology.year_context`).
  Add `YEARS_PER_GENERATION` and a `ContactProgram.year_of(generation)` helper and route every
  caller through it.

## v1.2 - Civilization timelines (2026-09-03)

Every catalogued civilization now has its own history instead of a state rolled once and frozen.
`docs/plans/civilization_timelines_plan.md` (approved 2026-09-03) ran in six phases, T0-T6; the
five below were completed (T6, the web/console front-end for it, is not yet started):

- **T0** - `src/civ_timeline.py`: a deterministic, per-system-seeded list of dated `CivEvent`s
  (`stage`/`strategy`/`attitude`/`extinct`) and `state_at(year)` to replay them; old saves load
  as static timelines (`timeline = None`) with no behaviour change.
- **T1** - the observed frame: descriptions, extinction, swan songs and the dossier all read
  `state_at(now - d)`; a `sky_change` event fires when new light shows a watched system change.
- **T2** - the receipt frame: `send_message` decides from `state_at(now + d)`; a civilization that
  dies before receipt gets no reply and a later sky-change explains why; every sent message
  carries `expected_reply_year` and `explanation_year`.
- **T3** - the WOW! source's Generation 144 evaluation reads `state_at(1977 + 1800)`, the
  civilization as it is when the reply arrives, instead of its state at first roll.
- **T4** - the catalogue deepened to 94 real stars out to ~160 LY, gated by detection tier
  (20/35/60/100 LY, unlimited at tier 4); the map and mirror-spawn logic respect the reach.

**T4 deviations from the plan text.** Two additions were needed to make the deepened catalogue
actually playable rather than partially inert:

1. **A tier-4 Detection technology** (`solar_gravitational_lens`, "Solar Gravitational Lens
   Telescope", `data/tech_tree.json`) was added so `UNLIMITED_REACH_LY` is reachable at all - the
   tech tree's Detection category topped out at tier 3 (100 LY reach), which permanently stranded
   HD 10180 (127 LY) and HD 209458 (159 LY) outside detection range for every game.
2. **Three planet-host stars in the 80-100 LY band** (HD 134987, HD 216437, HD 82943, all real
   exoplanet hosts) were added to `data/star_catalog.json` alongside the T4 catalogue so that band
   is not empty - the plan's star list left a gap between the ~60 LY group and HD 10180 at 127 LY.

**T5 - calibration.** Measured with `scripts/calibrate_timelines.py` against a baseline of the
pre-T1 engine (commit `2a4e0ec`, `scripts/auto_playtest.py --runs 30 --seed 1`, matched to the
same 60-generation cap for the victory comparison). Six sweep iterations (the plan's time-box);
final numbers pooled across all seven measurement profiles unless noted - see the calibration
block in `src/civ_timeline.py` for the full iteration-by-iteration trade-off:

| Metric | Target (§7) | Measured (final) | Met? |
|---|---|---|---|
| Extinct at first observation | 20-30 % | ~20 % pooled (18-21 % per profile) | yes (floor) |
| Sky changes / 40 generations (observer) | 3-6 | 0.4-1.0 (observer 0.99) | **no** |
| Differing message outcomes | 10-20 % | ~21 % pooled (19-26 % per profile) | close (~1 pt over) |
| Victories vs. baseline, per shared profile | within ±20 % | refreshed against the instrumented baseline, see the T5 addendum below: balanced +5 % and aggressive +0 % (met); cautious +38 %, integration +23 %, neglect +100 % | **no** (2/5 met) |
| First-reply median vs. baseline | not later | superseded — see the T5 addendum below (baseline instrument fixed) | yes, all 5 profiles |
| Stage-up among first 3 sky changes | ≥ 50 % of games with ≥ 3 changes | 100 %, but only 1-3 such games per 30-run profile | yes (low confidence) |
| First sky-change by generation 10 (g) | ≥ 60 % | see the T5 addendum below | **no** |
| (f) reformulated: non-death among first 3 (h) | ≥ 50 % | see the T5 addendum below | yes (low confidence) |

**T5 addendum — calibration instrument fixes (2026-09-03).** The original T5 pass above could not
measure metric (e) (first-reply median vs. baseline) because the pre-T1 harness never recorded
when a reply landed. Fixed: `scripts/auto_playtest.py` now records `first_reply_gen` (already
shipped for the current engine); a matching patch was applied to a detached worktree of the
baseline commit `2a4e0ec` only (never committed there) and used to regenerate
`scripts/calibration/baseline_2a4e0ec.json` — 30 runs/profile, seeds 500-529, `--max-gen 60`, the
five shared profiles (`balanced`/`aggressive`/`cautious`/`integration`/`neglect`); see
`scripts/calibration/README.md` for the exact patch and command. `calibrate_timelines.py` now
uses that file as `--baseline`'s default when present, so `--runs 30 --max-gen 60` alone compares
against it, and reports two more metrics the plan review added:

- **(g) first sky-change by generation 10** (share of games whose first sky-change event lands at
  gen <= 10, target >= 60 %): **7-13 %** across profiles (observer 13.3 %, aggressive 13.3 %,
  cautious 10.0 %, balanced/integration/neglect 6.7 %, talker 6.7 %) — **not met**. Consistent
  with the already-known `sky_changes_per_40` shortfall (~1/40 gens): with sky changes this rare,
  most games' first one lands well past generation 10.
- **(h) (f) reformulated** — at least one of the first three sky changes is not an
  extinction/silence (target >= 50 %): **100 %** in every profile with >= 3 sky changes in the
  sample, same as the original (f) ("stage-up among the first three"); the two formulations agree
  here because every non-death sky change observed in this sample was a stage-up (no "activity"
  kind occurred among the first three anywhere). Same low-confidence caveat as (f): 1-3 qualifying
  games per 30-run profile.
- **First-reply median vs. baseline (e), now numerically comparable:** every shared profile's
  first reply now lands *earlier* than the pre-timelines baseline (lower generation is better):

  | Profile | Reply now (median gen) | Reply baseline | Δ |
  |---|---|---|---|
  | balanced | 10.0 | 15.0 | -5.0 |
  | aggressive | 9.0 | 11.0 | -2.0 |
  | cautious | 12.5 | 19.0 | -6.5 |
  | integration | 14.0 | 20.0 | -6.0 |
  | neglect | 12.0 | 13.5 | -1.5 |

  Target ("not later than baseline") is **met** for all five profiles.
- **Victories vs. baseline, per shared profile — refreshed** with the instrumented baseline
  (relative to baseline rate; target within ±20 %):

  | Profile | Wins now | Wins baseline | Relative Δ | Met? |
  |---|---|---|---|---|
  | balanced | 21/30 (70.0 %) | 20/30 (66.7 %) | +5.0 % | yes |
  | aggressive | 23/30 (76.7 %) | 23/30 (76.7 %) | +0.0 % | yes |
  | cautious | 18/30 (60.0 %) | 13/30 (43.3 %) | +38.5 % | no |
  | integration | 27/30 (90.0 %) | 22/30 (73.3 %) | +22.7 % | no |
  | neglect | 16/30 (53.3 %) | 8/30 (26.7 %) | +100.0 % | no |

  2/5 within ±20 % (balanced, aggressive); cautious/integration/neglect still run well over,
  which matches the original report's overall conclusion (T5's ±20 % victories target was not
  met) even though the exact per-profile percentages above differ from the original write-up —
  this addendum reruns the comparison against the now-instrumented baseline rather than
  re-deriving the earlier estimate. It changes no constant and is not a re-tuning.

**Constants changed:** `BASE_CIV_CHANCE` 0.26 → 0.32, `EXTINCT_AT_CREATION_CHANCE` 0.25 → 0.15,
`EXTINCTION_HAZARD_PER_CENTURY` raised modestly across all stages, `STRATEGY_DRIFT_PER_CENTURY`
0.03 → 0.015 and `RARE_STRATEGY_DRIFT_PER_CENTURY` 0.005 → 0.0025 (see `src/civ_timeline.py` and
`src/legacy_of_stars_v3.py` for the per-constant rationale).

**Time-box outcome (honest report, per §7's escape hatch clause).** Two targets were not met
within the six iterations:

- *Sky changes per 40 generations* stayed at ~1, well under the 3-6 target. The metric is carried
  almost entirely by two things: the extinction hazard (silence/extinction changes) and
  `BASE_CIV_CHANCE` (more watched civilizations means more of everything, including stage-up
  crossings, which are the majority kind - strategy drift never reaches this metric at all, since
  the observed frame deliberately hides strategy). Reaching 3-6 required pushing hazard or civ
  density far enough to break the other three targets (tried up to ~2/40 gens at
  `BASE_CIV_CHANCE = 0.5`, at which point `extinct_share` exceeded 35 %, `differing_outcomes`
  exceeded 40 %, and victories were more than double the baseline for several profiles).
- *Victories within ±20 % of baseline* held for `balanced` only; the other four shared profiles
  ran over, `neglect` badly (+96 %) because a denser catalogue is also more contact/reply
  opportunities, which disproportionately helps a strategy whose only path to victory is contact
  rather than the integration tech tree.

The plan's recorded escape hatch (owner decision 2, §9 variant B - drift only in the observed
frame, replies evaluated at send time as before) was **not implemented**; T2's receipt-frame
replies stay as shipped. This is the owner's call to make, not something to decide unilaterally
under a time-box.

**T5.1/T5.2 - two further calibration levers (2026-09-03).** Applied one at a time with a full
measurement between them, using `python scripts/calibrate_timelines.py --runs 30 --max-gen 60`
over all seven measurement profiles (seeds 500-529). All three tables below share the same
columns: `Extinct` = extinct-at-first-observation share; `Sky/40` = sky changes per 40
generations (observer is the metric's own instrument, §7); `Differ` = differing message outcomes;
`Wins` = victory rate, with the relative delta against the pre-timelines baseline for the five
shared profiles in parentheses (target: within ±20 %); `Reply` = median generation of the first
reply; `Sky≤10`/`Sky≤30` = share of games whose first sky-change lands by generation 10 / 30.

*Before (Step 0):*

| Profile | Games | Extinct | Sky/40 | Differ | Wins (Δ vs baseline) | Reply | Sky≤10 | Sky≤30 |
|---|---|---|---|---|---|---|---|---|
| observer | 30 | 20.6 % | 0.99 | 25.7 % | 60.0 % | 20.5 | 13.3 % | n/a |
| talker | 30 | 21.1 % | 0.50 | 19.9 % | 66.7 % | 8.5 | 6.7 % | n/a |
| balanced | 30 | 20.3 % | 0.42 | 22.2 % | 70.0 % (+5.0 %) | 10.0 | 6.7 % | n/a |
| aggressive | 30 | 19.3 % | 0.57 | 22.9 % | 76.7 % (+0.0 %) | 9.0 | 13.3 % | n/a |
| cautious | 30 | 18.9 % | 0.50 | 21.1 % | 60.0 % (+38.5 %) | 12.5 | 10.0 % | n/a |
| integration | 30 | 20.5 % | 0.57 | 18.7 % | 90.0 % (+22.7 %) | 14.0 | 6.7 % | n/a |
| neglect | 30 | 18.2 % | 0.61 | 18.9 % | 53.3 % (+99.6 %) | 12.0 | 6.7 % | n/a |

(`Sky≤30` did not exist yet as a metric - added for T5.2, see below.)

**Lever 1 - far-band civilization density (decision 2b).** `distance_prior(distance_ly)` in
`src/legacy_of_stars_v3.py`: 1.0 out to 60 LY (the near field, deliberately untouched), then a
ramp linear in *log*-distance down to 0.35 at 160 LY, multiplied into the civilization roll next
to `habitability_weight`. Rationale: beyond ~60 LY our actual knowledge of exoplanets falls off
with distance, so a lower prior there is an honest model of our own ignorance about the T4
catalogue's far tail, not a balance hack; `BASE_CIV_CHANCE` and the near field are untouched by
construction. Measured effect on the direct catalogue-density test
(`tests/test_civilization_types.py`): the full-catalogue mean civilization count drops modestly
(~19.8 → ~19.2 over 300 samples), the within-20-LY mean is unchanged (~10.2, exactly as
designed).

*After lever 1 - the calibration instrument's table is byte-for-byte identical to "before".* This
is an honest, load-bearing finding, not an oversight: across all 210 games in the sample (seeds
500-529, max 60 generations), no run's farthest discovery ever passed ~51 LY (detection reach did
open past 100 LY in several runs, but the *rate* stars are actually resolved at, given nearest-first
discovery order and the reach-gated reveal chance, never got that far within 60 generations). Since
`distance_prior` is exactly 1.0 up to 60 LY, its far-band branch was never exercised by a single
roll in this sample - confirmed by comparing the raw per-seed run JSON, not just the aggregated
metrics. Lever 1's effect is real (see the catalogue-density numbers above and the dedicated
`DistancePriorTest` unit tests) but is invisible to this instrument at a 60-generation cap; a
longer-horizon instrument (or a catalogue-density test, which is what actually caught it) is
needed to see it. Neglect's baseline deviation is unchanged by lever 1: still +99.6 % against the
±20 % target, i.e. **not met**, and lever 1 cannot be expected to move it since it never fires in
this sample.

**Lever 2 - the promise that silence ends (decision 1a).** `_start_new_game` now checks
`_selection_has_early_sky_promise`: at least one of the five known systems, alive and within 20 LY,
must have a `stage` event whose light reaches Earth between Generation 8 and Generation 30. If the
first draw does not qualify, one of the five known systems is re-rolled at a time (cycling through
them, up to `GEN8_30_GUARANTEE_ATTEMPTS = 100` attempts) from an **isolated, salted**
`random.Random`, never the shared global `random` stream every other roll in the game draws from
(`StarSystem.reroll_civilization`); a game that still fails after the budget starts anyway
(logged at INFO) rather than falling back to a scripted event. An earlier version re-rolled the
whole starting *selection* instead (repeating `generate_star_systems(5)`, which re-samples from
the global stream); measurement showed that shifted the global stream enough to move victory
rates and reply timing for essentially every seed in the calibration sample, not just the ones
that needed a re-roll - an outsized, undocumented side effect for a narrow guarantee, so it was
replaced with the per-system salted version before this table was produced. See the constant's
comment in `src/legacy_of_stars_v3.py` for the full account, including why the per-system version
still ends up touching most of a game's five known systems when the search runs long (the target
condition is rare per system-roll, so a game needing many attempts cycles through - and
overwrites - most or all five before it succeeds).

*After lever 2:*

| Profile | Games | Extinct | Sky/40 | Differ | Wins (Δ vs baseline) | Reply | Sky≤10 | Sky≤30 |
|---|---|---|---|---|---|---|---|---|
| observer | 30 | 17.7 % | 2.26 | 21.3 % | 66.7 % | 9.5 | 53.3 % | **90.0 %** |
| talker | 30 | 22.0 % | 1.25 | 16.2 % | 86.7 % | 4.0 | 40.0 % | 76.7 % |
| balanced | 30 | 17.5 % | 1.34 | 17.2 % | 93.3 % (+39.9 %) | 4.5 | 30.0 % | 63.3 % |
| aggressive | 30 | 19.9 % | 1.30 | 21.5 % | 83.3 % (+8.6 %) | 4.0 | 30.0 % | 73.3 % |
| cautious | 30 | 18.3 % | 1.21 | 15.0 % | 76.7 % (+77.1 %) | 10.0 | 30.0 % | 66.7 % |
| integration | 30 | 23.4 % | 1.14 | 22.1 % | 76.7 % (+4.6 %) | 6.0 | 30.0 % | 70.0 % |
| neglect | 30 | 17.9 % | 1.35 | 20.8 % | 63.3 % (+137.1 %) | 5.0 | 33.3 % | 70.0 % |

Lever 2's own target - **met**: the `observer` profile's `first_sky_change_by_30` (T5.2's new
gameplay-level check of the guarantee, alongside the existing `first_sky_change_by_10`) lands at
exactly 90.0 %, hitting the ≥90 % target; `first_sky_change_by_10` also rose sharply (13.3 % →
53.3 %) and `sky_changes_per_40` more than doubled (0.99 → 2.26), still short of the plan's
original 3-6 target but a real move toward it, entirely as a side effect of guaranteeing an early
stage advance rather than any hazard/density re-tuning.

The unit-test guarantee (`tests/test_civ_timeline.py::SkyChangeGuaranteeTest`, seeds 1-50, checked
against the raw timeline data rather than gameplay) succeeds in **43/50 (86.0 %)** games, above the
80 % floor with a comfortable margin.

**Neglect vs. the ±20 % baseline band - not met, and lever 2 makes it worse.** Baseline neglect
victory rate is 26.7 % (8/30). Before and after lever 1: 53.3 % (+99.6 % relative - not met).
After lever 2: 63.3 % (+137.1 % relative - **worse, not better**). This is the honest, disclosed
cost of lever 2's implementation: because the target condition is rare, a game whose starting
selection needs the guarantee typically has several of its five systems re-rolled by the time a
qualifying one is found (see the per-system-reroll account above), which tends to add
civilizations/contact opportunities to games that previously had few - and "neglect" is exactly
the profile whose only path to victory is contact rather than the integration tech tree, so it
benefits disproportionately. Of the five shared profiles, only `aggressive` (+8.6 %) and
`integration` (+4.6 %) land inside ±20 % after lever 2; `balanced` moved from inside the band
(+5.0 %) to outside it (+39.9 %) as a direct consequence of lever 2. This is a real trade-off, not
a bug: lever 2 was scoped to the starting-selection sky-change guarantee only, and reaching its
90 % target while also holding every profile's victory rate within ±20 % of baseline was not
attempted within this task's scope - the owner should decide whether the guarantee is worth this
cost, per the same "owner's call, not a unilateral time-box decision" principle T5's own report
applied to its escape hatch.

**Two dormant bugs surfaced and fixed while implementing lever 2** (both pre-existing, exposed by
the RNG-stream and civilization-profile shifts the guarantee introduces for some seeds, not
introduced by either lever): (1) `ContactProgram._log_system_profile`, a debug-only logger, could
crash when a civilization rolled extinct at creation was discovered by `add_star_system` before
its own timeline origin came into observable range - `refresh_observation` correctly reports
"not observably extinct" in that case, but the legacy `civilization_stage` cache stays `None`,
which the logger did not handle; (2) `tests/test_save_load.py`'s `busy_program()` forced a
system's cached `true_strategy` to `"LA"` without giving it a matching timeline, so
`send_message` (which reads `system.timeline_state`, not the cached fields) was silently
evaluating whatever civilization that system's own roll happened to produce - fixed by also
calling `system.set_static_timeline(...)` so the forced profile is the one actually read.

The sections below are the historical development notes of Phases 1-3. Some figures in them
(27 technologies, 8 star systems, Gemini AI) describe earlier builds.

---

## ✅ Phase 1+1b: COMPLETE (Dark Forest Core)

### What We Built
**Statistical Realism:**
- ✅ 75/25 age distribution (75% civs older than humanity)
- ✅ 15% of stars host a civilization, 25% of those extinct
- ✅ Swan song data archive flags (80% of extinct civs)
- ✅ Age-based tech stage progression
- ✅ Deception capability (scales with civilization age)

**Dark Forest Mechanics:**
- ✅ Hidden strategies (L/LB/LR/LA/LBA) with weighted probabilities
- ✅ Strategy-based message responses
- ✅ Attack system for hostile civilizations (LA/LBA)
- ✅ Deceptive bait mechanics (LBA high-deception trap)
- ✅ Tiered attack consequences based on tech gap

**Developer Experience:**
- ✅ Timestamped session logs (`game_YYYYMMDD_HHMMSS.log`)
- ✅ Debug logging showing all strategies at game start
- ✅ Extinct civilization display fix
- ✅ Comprehensive test suite

### Files Delivered
- `legacy_of_stars_v3.py` - Main game with Dark Forest mechanics
- Test scripts: `test_v3.py`, `test_phase1.py`, `test_debug_log.py`

---

## 🎯 Phase 2A: Historical Foundation & Tutorial (IMMEDIATE - Week 1)

### Priority 1: WOW! Signal Ultra-Long-Term Legacy ⭐⭐⭐⭐ **REFINED!**
**Purpose**: Embody "Legacy of Stars" theme through 144-generation consequence
**User Decision**: Literal gameplay scenario, not just narrative

**The Design:**
Opening scenario (Gen 1, August 15, 1977) - Player makes REAL choice with consequence 144 generations later (Year 5552). This teaches the game's core theme: decisions have multi-generational impact.

**Implementation:**

1. **Tutorial/Opening Choice (Generation 1)**
   ```
   === WOW! Signal Detected ===
   Big Ear Telescope - August 15, 1977
   72-second burst at 1420 MHz (hydrogen line)
   Direction: Sagittarius (Chi Sagittarii region)
   Distance: ~1,800 light-years (disputed estimate)
   
   CRITICAL DECISION:
   Do you authorize a reply transmission?
   
   → YES - Send Reply
      • Message travels 72 generations (1,800 LY)
      • Response/attack arrives Generation 144 (Year 5552)
      • Immediate: +100 RP, +10% Support (bold decision)
      • Long-term: Unknown until Gen 144
   
   → NO - Stay Silent
      • Earth's location remains hidden
      • Immediate: -15% attack damage (entire game)
      • Long-term: WOW! mystery remains unsolved
   
   Note: Most players won't reach Gen 144 - this is an ULTRA-RARE achievement path
   ```

2. **Generation 144 Event Handler**
   - **If player replied** and reaches Gen 144:
     - Response type depends on secretly-assigned civilization strategy
     - **L Strategy**: Silence (no response, no attack)
       - Achievement: "The Long Wait"
       - Message: "3,600 years... silence. The galaxy keeps its secrets."
     
     - **LB/LR Strategy**: Friendly Contact!
       - Achievement: "The WOW! Response" (ULTRA RARE)
       - AI-generated profound message after 144 generations
       - Public support → 100%, major knowledge gain
     
     - **LA/LBA Strategy**: Hostile Attack Arrives
       - Achievement: "The WOW! Reckoning"
       - Fleet from 1,800 LY away attacks Gen 144
       - "Our ancestors' 1977 decision sealed our fate"
       - Apply attack mechanics based on Gen 144 tech levels

3. **Achievement System**
   ```python
   ACHIEVEMENTS = {
       "the_long_wait": {
           "name": "The Long Wait",
           "description": "Reached Gen 144 after replying to WOW!",
           "rarity": "RARE (< 5%)"
       },
       "wow_response": {
           "name": "The WOW! Response",
           "description": "Received friendly reply to 1977 transmission",
           "rarity": "ULTRA RARE (< 1%)"
       },
       "wow_reckoning": {
           "name": "The WOW! Reckoning", 
           "description": "Experienced attack from WOW! source",
           "rarity": "ULTRA RARE (< 1%)"
       },
       "silent_wisdom": {
           "name": "Silent Wisdom",
           "description": "Chose not to reply (cautious path)",
           "rarity": "COMMON"
       }
   }
   ```

4. **Historical Accuracy Notes**
   - Use real 1,800 LY estimate (disputed but commonly cited)
   - Acknowledge uncertainty in tutorial text
   - Star 2MASS 19281982-2640123 remains an unconfirmed candidate; a 2024 analysis (Arecibo
     Wow! project) proposes a natural origin - a hydrogen cloud brightened by a magnetar flare
   - Game treats it as gameplay scenario, not historical claim

**Why This Design is Perfect:**
- ✅ **True Legacy Mechanic**: Gen 1 decision → Gen 144 consequence
- ✅ **Historically Grounded**: Real distance, real uncertainty
- ✅ **Ultra-Rare Achievement**: Dedicated players only
- ✅ **Immediate + Long-Term**: Bonuses now, consequence later
- ✅ **Replayability**: Different WOW! source strategies
- ✅ **Thematic Core**: Embodies multi-generational decision-making
- ✅ **Educational**: Teaches light-speed delay viscerally

**Player Experience:**
- **95% of players**: See Gen 1 choice, get immediate bonus, play 10-20 gens, wonder what happened
- **5% of players**: Actually reach Gen 144, experience profound moment, earn ultra-rare achievement
- **Completionists**: Try both paths, discover all outcomes, share stories

**Timeline**: 2 days implementation
**Impact**: VERY HIGH - defines game's core identity

---

### Priority 2: Attack Early Warning System ⭐⭐⭐ **NEW!**
**Purpose**: Realistic defense - no FTL means time to prepare
**User Feedback**: "Earth can wait for arrival and prepare"

**Implementation:**
1. **Early Detection**
   - When LA/LBA attack triggered, player gets warning
   - Warning appears immediately: "Hostile fleet detected!"
   - Preparation time = light-speed travel time (round trip)
   
2. **Defensive Actions Available**
   - "Emergency Defense Protocol" (all AP, +50% defense)

---

   - "Emergency Defense Protocol" (all AP, +50% defense)
   - "Evacuate Critical Infrastructure" (reduce casualties 30%)
   - "Attempt Diplomatic Contact" (hail mary, might work on low-deception LBA)

3. **Tech-Based Improvements**
   - "Orbital Defense Grid" (passive 40% damage reduction)
   - "Early Warning Network" (+2 generation warning time)
   - "Distributed Civilization" (off-world backups, attack can't destroy Earth)

4. **Countdown UI**
   - Log shows: "⚠️ HOSTILE FLEET ETA: X generations"
   - Tension builds as deadline approaches
   - Player must balance defense vs. other needs

**Timeline**: 1-2 days implementation
**Impact**: VERY HIGH - realistic, strategic, fair, tense

---

### Priority 3: Realistic Tech Tree Redesign ⭐⭐⭐ **NEW!**
**Purpose**: SETI-specific, historically accurate technology progression
**User Feedback**: "Tech tree now is not correct from real view"

**Historical Timeline (Start: 1977):**

**Tier 0 (1977-2000) - Gen 1-2:**
- Arecibo Radio Telescope (real, built 1963)
- Drake Equation Analysis (published 1961)
- Basic Signal Processing (1970s tech)
- Project Ozma Methods (first SETI search, 1960)
- Voyager Golden Record (sent 1977)

**Tier 1 (2000-2050) - Gen 2-3:**
- SETI@Home Distributed Computing (launched 1999)
- Deep Space Network Upgrade (NASA DSN)
- Optical SETI (laser detection)
- Kepler Exoplanet Database (target selection)
- AI Pattern Recognition (ML for signals)

**Tier 2 (2050-2100) - Gen 3-5:**
- Square Kilometre Array (SKA) - world's largest telescope
- Breakthrough Listen (real $100M initiative)
- Quantum Communication Detection
- Technosignature Cataloging (industrial pollution detection)
- **AI Strategic Advisor** ⭐ (NEW!)

**Tier 3 (2100-2200) - Gen 5-8:**
- Neutrino Telescope Networks
- Gravitational Wave Communication
- Dyson Sphere Detection Systems
- Orbital Defense Grid (anti-LA protection)
- Civilization Cloaking (hide Earth's signals)

**Tier 4 (2200-2400+) - Gen 8-15:**
- Relativistic Communication (near-light speed)
- Distributed Backup Colonies (Mars/Europa refuges)
- Stellar Engineering (manipulate stars for signaling)
- Post-Biological Transition Tech
- Emergency Evacuation Infrastructure

**Generation Gating:**
```python
# Tech unlocks based on realism, not just prerequisites
tech.min_generation = calculated_from_year
# Example: Quantum tech unavailable until Gen 4 (2075)
```

**Timeline**: 2-3 days (redesign + implementation)
**Impact**: HIGH - makes game feel realistic and grounded

---

### Priority 4: AI Strategic Advisor ⭐⭐⭐⭐ **NEW!**
**Purpose**: Meta-brilliant - AI helping you play game about alien AI
**User Idea**: "AI assistant that can receive current context and give advice"

**Implementation:**
1. **Tech Unlock**: "AI Strategic Advisor" (Tier 2, ~Gen 4, Cost: 200 RP)
   - Prerequisites: Digital Signal Processing, Linguistic AI
   - Description: "Advanced AI analyzes galactic patterns and provides strategic recommendations"

2. **Context Analysis**
   ```python
   class AIAdvisor:
       def get_advice(self, game_state):
           context = f"""
           Generation {gen}, Year {year}
           Support: {support}%, Funding: {funding}%
           Civilizations: {known_count} detected, {contacted} contacted
           Responses: {responses_received}
           Active Threats: {pending_attacks}
           Recent Events: {last_5_events}
           """
           
           prompt = "You are Earth's strategic AI advisor for SETI.
           Analyze threats, identify safe contacts, recommend actions.
           Remember Dark Forest theory - silence might be safer."
           
           return ai_manager.generate_text(context, prompt)
   ```

3. **New Action**: "Consult AI Advisor" (Free, once per generation)
   - Shows strategic briefing in game log
   - Provides:
     - Risk assessment (current dangers)
     - Pattern analysis (suspicious silent systems)
     - Recommended actions (what to do this turn)
     - Long-term strategy (next 3-5 generations)

4. **Example Output**:
   ```
   === AI STRATEGIC BRIEFING - Gen 8 ===
   
   RISK: MODERATE
   - Support declining (48%), recommend outreach
   - No active threats
   - Ecological risk increasing
   
   OBSERVATIONS:
   - Proxima: No response to 3 messages (L or LA?)
   - Tau Ceti: Enthusiastic responses (verified LB-SAFE)
   - Wolf 359: EXTINCT - potential swan song
   
   RECOMMENDED:
   1. Public Outreach (support critical)
   2. Research Wolf 359 (archives?)
   3. AVOID Proxima (suspicious silence)
   
   FORECAST: Defunding risk by Gen 12 unless support restored
   ```

**Timeline**: 2-3 days implementation
**Impact**: VERY HIGH - helps players, thematically perfect, unique feature

---

## 🎯 Phase 2B: Content & Discovery (Week 2-3)

### Priority 5: Swan Song Messages ⭐⭐⭐
**Purpose**: Make extinct civilizations meaningful

**Implementation:**
- AI-generated final messages from dead civilizations
- Discovery mechanic: "Deep Scan for Artifacts" action
- Categories: Warnings, Archives, Technical Data, Pleas
- Rewards: Tech hints, lore, philosophical insights

**Timeline**: 2 days
**Impact**: HIGH - narrative depth

---

### Priority 6: Passive Signal Leakage ⭐⭐
**Purpose**: Authentic Dark Forest risk - we broadcast accidentally

**Implementation:**
- Tech level determines broadcast radius
- LA/LBA can detect Earth WITHOUT being contacted
- Mitigation tech: Radio Silence, Quantum Encryption
- Creates existential tension

**Timeline**: 2-3 days
**Impact**: VERY HIGH - changes core tension

---

## 📊 Revised Development Order

### **Immediate (Phase 2A - Week 1)**
1. ✅ **Commit Phase 1+1b** (today)
2. 🔨 **WOW! Signal Tutorial** (1 day) - thematic intro
3. 🔨 **Attack Early Warning** (1-2 days) - realistic defense
4. 🔨 **Tech Tree Redesign** (2-3 days) - historical accuracy

### **Short-term (Phase 2B - Week 2)**
5. 🔨 **AI Strategic Advisor** (2-3 days) - meta-feature
6. 🔨 **Swan Song Messages** (2 days) - extinct civ content

### **Medium-term (Phase 2C - Week 3)**
7. 🔨 **Passive Signal Leakage** (2-3 days) - core tension
8. 🔨 **Defensive Technologies** (1-2 days) - player agency
9. 🔨 **Victory Condition Alternatives** (1 day) - replayability

---

## 🎮 Updated Playtest Priorities

**Before Phase 2A:**
- ✅ Verify all 5 strategies
- ✅ Test attack system
- ⚠️ Need: LBA deceptive trap test
- ⚠️ Need: Victory condition test (3 contacts)

**After Phase 2A (WOW Tutorial):**
- Test all 4 tutorial choices
- Verify 1977 start year accuracy
- Confirm starting bonuses work
- Test attack preparation mechanics

---

## 💡 Key Design Decisions Made

1. **Start Year**: 1977 (WOW! Signal era) ✅
2. **Tutorial**: WOW! Signal intro scenario ✅
3. **Attack Defense**: Early warning + preparation window ✅
4. **Tech Tree**: Historically accurate, generation-gated ✅
5. **AI Advisor**: Real AI provides strategic guidance ✅

---

## 📈 Success Metrics

**Phase 2A Goals:**
- [ ] WOW! Signal tutorial is engaging and educational
- [ ] Attack preparation creates strategic depth
- [ ] Tech tree feels realistic (1977-2477 timeline)
- [ ] Players understand game mechanics after tutorial

**Phase 2B Goals:**
- [ ] AI Advisor provides genuinely helpful guidance
- [ ] Swan songs feel authentic and meaningful
- [ ] Passive leakage creates genuine tension
- [ ] 15+ hours of engaging gameplay

---

**Current Status**: Phase 1+1b COMPLETE ✅  
**Next Milestone**: WOW! Signal Tutorial (Phase 2A)  
**Target**: Playable Phase 2A in 1 week, Full Phase 2 in 3 weeks

1. **Leakage System**
   - Tech level determines broadcast radius
   - Higher tech = louder signals = more danger
   - Player can research "Radio Silence Protocol" to reduce leakage

2. **Discovery by Others**
   - Passive chance each generation that LA/LBA detect Earth
   - Attack triggered WITHOUT player sending message
   - Creates authentic existential dread

3. **Mitigation Options**
   - Tech: "Directional Transmission" (reduce leakage 50%)
   - Tech: "Quantum Encryption" (reduce leakage 80%)
   - Doctrine: "Dark Forest Protocol" (stop all outbound, -50% support)

**Complexity**: Medium-High (4-5 hours)  
**Impact**: Very High - changes core tension, makes silence a strategy

---

### Priority 3: Tech Tree Expansion ⭐⭐
**Purpose**: More player agency and strategic options

**New Technologies:**
1. **Defensive Tech**
   - "Asteroid Defense Grid" - Reduces LA attack severity
   - "Early Warning System" - 2 generation advance notice of attacks
   - "Stellar Camouflage" - Reduces passive leakage detection chance

2. **Communication Tech**
   - "Linguistic AI" - +20% message quality
   - "Cultural Database" - Better responses from LB/LR civilizations
   - "Deception Analysis" - Chance to detect LBA traps

3. **Social Tech**
   - "Unified Earth Government" - Larger action point pool
   - "Generational Archives" - Slower knowledge decay

**Complexity**: Low-Medium (2-3 hours)
**Impact**: Medium - adds depth, player choices

---

## 🚀 Phase 3: Polish & Player Experience

### Priority 1: Victory Condition Alternatives ⭐
**Current**: Contact 3 civilizations  
**Problem**: Encourages risky broadcasts

**New Victory Modes:**
1. **Survival Score**
   - Generations survived × (Contacts made + Knowledge gained)
   - Encourages balance between caution and exploration

2. **Knowledge Victory**
   - Reach 100% knowledge base without triggering attacks
   - Pure research/observation path

3. **Diplomatic Victory**
   - Establish verified-peaceful contact with 2+ civilizations
   - Must correctly identify and avoid LA/LBA

**Complexity**: Low (1-2 hours)
**Impact**: High - better replay value

---

### Priority 2: Risk Calculator UI ⭐⭐
**Purpose**: Help players make informed SETI/METI decisions

**Features:**
- Visual display of current broadcast risk
- Shows: Passive leakage radius, contacted systems, estimated danger
- "What-if" simulator: "If I message this system, risk becomes..."
- Warning indicators for suspicious behavior patterns

**Complexity**: Medium (3-4 hours, depends on UI framework)
**Impact**: Medium - improves player understanding

---

### Priority 3: Enhanced Narrative System ⭐
**Purpose**: Make each playthrough feel unique

**Features:**
1. **Procedural Events**
   - Rogue AI warning from friendly LB civilization
   - Intercepted message between two other civilizations
   - Evidence of ancient war (extinct LA civilization found near extinct victim)

2. **Dynamic Descriptions**
   - AI-generated system descriptions based on age/stage
   - Unique alien culture details for LB civilizations
   - Environmental storytelling through research discoveries

**Complexity**: Medium-High (4-6 hours)
**Impact**: High - massively improves immersion

---

## 📊 Recommended Development Order

### Immediate Next Steps (Phase 2A - 1 week)
1. ✅ **Commit Phase 1+1b** (today)
2. 🔨 **Swan Song Messages** (2-3 days)
   - Design message categories
   - Implement discovery mechanic
   - AI prompt engineering for authentic last messages
3. 🔨 **Passive Leakage** (2-3 days)
   - Basic leakage calculation
   - LA/LBA detection of Earth
   - Mitigation tech tree additions

### Medium Term (Phase 2B - 2 weeks)
4. 🔨 **Tech Tree Expansion** (3-4 days)
   - Add 10-15 new technologies
   - Balance costs and prerequisites
   - Doctrine choices for key techs

5. 🔨 **Victory Condition Alternatives** (1-2 days)
   - Implement scoring system
   - Add end-game summary screens

### Longer Term (Phase 3 - 1 month)
6. 🔨 **Risk Calculator UI** (1 week)
7. 🔨 **Enhanced Narrative** (1-2 weeks)
8. 🔨 **Final Polish** (1 week)
   - Balancing pass
   - Bug fixes
   - Playtesting

---

## 🎮 Playtest Priorities

**Before starting Phase 2:**
1. ✅ Verify all 5 strategies work correctly
2. ✅ Confirm attack system triggers properly
3. ✅ Test extinct civilization discovery flow
4. ⚠️ **Need to test**: LBA deceptive trap (high deception)
5. ⚠️ **Need to test**: LA/LBA attacks with different tech gaps
6. ⚠️ **Need to test**: Victory condition (3 contacts)

**Suggested Playtest:**
- Message 5+ different systems
- Document which strategies appear in logs
- Try to trigger both LA and LBA attacks
- Test extinction discovery at different knowledge levels

---

## 🔧 Technical Debt & Improvements

### Code Quality
- [ ] Move strategy constants to config file
- [ ] Refactor `send_message()` into smaller methods
- [ ] Add type hints throughout
- [ ] Create unit tests for strategy selection

### Performance
- [x] Logging system (optimized with timestamps)
- [ ] Save/Load game state
- [ ] Automated playtest suite

### Documentation
- [x] Implementation guide (phase1b_implementation_guide.md)
- [x] Walkthrough (walkthrough.md)
- [ ] Player manual
- [ ] Strategy guide (spoiler version showing all mechanics)

---

## ❓ Open Design Questions

1. **Swan Song Rewards**: Should they unlock full tech or just hints?
2. **Passive Leakage Rate**: What's the sweet spot for danger vs. playability?
3. **LBA Deception Success**: Current 70% for high-deception - too easy to fall for?
4. **Attack Defense**: Should there be a chance to survive LA attacks?
5. **Silent Civilizations (L)**: Should they ever break silence under special circumstances?

---

## 📈 Success Metrics

**Phase 2 Goals:**
- [ ] Swan song messages feel authentic and meaningful
- [ ] Passive leakage creates genuine tension
- [ ] Players have meaningful defensive options
- [ ] Tech tree offers real strategic choices
- [ ] 10+ hours of engaging gameplay

**Phase 3 Goals:**
- [ ] Multiple victory paths feel balanced
- [ ] Risk calculator helps players understand decisions
- [ ] Each playthrough feels narratively unique
- [ ] Game has lasting appeal beyond initial discovery

---

---

## 🌌 Phase 3A: Philosophical Depth (COMPLETE)

> [!NOTE]
> **Status**: Core features implemented and verified as of 2025-12-07.

**Purpose**: Add deep existential mechanics exploring humanity's evolutionary crisis. Based on philosophical foundations from Section 11 of design notes.

**Timeline**: 7-10 days (3 sub-phases)
**Impact**: VERY HIGH - transforms gameplay from "survive contact" to "navigate existential evolution while surviving contact"

### Sub-Phase 3A.1: Integration Progress (COMPLETE) ✅
**Core Mechanic**: Track biological-technological integration

**Implementation**:
- ✅ New `IntegrationProgress` system
- ✅ 6 Transcendence technologies (Tier 4-5):
  - Genetic Pacification (+variable integration)
  - Neural Interface (+40% integration)
  - Consciousness Upload (+60% integration)
  - Synthetic Biology (+30% integration)
  - Hybrid Civilization (reduces self-destruct risk to near-zero)
- ✅ Low integration (<0.3) penalties:
  - +50% self-destruct risk
  - -10% public support per generation
  - -15% research efficiency
  - Cannot research Tier 5 techs

### Sub-Phase 3A.2: Civilization Types & Events (COMPLETE) ✅
**Content**: How aliens solved the Dual DNA problem

**Implementation**:
- ✅ Civilization types for all aliens:
  - `biological_pure` - Stayed biological, cautious
  - `digital_ascended` - Uploaded consciousness (30% incomprehensible)
  - `hybrid_integrated` - Successfully merged, empathetic
  - `failed_transition` - Extinct (70% of extinct civs)
- ✅ 5 Philosophical Crisis Events (Gen 15-60):
  - Biology-Technology Gap
  - Expansion Instinct
  - AI Consciousness Question
  - Cosmic Purpose Debate
  - Mirror Civilization

### Sub-Phase 3A.3: Advanced Features (COMPLETE) ✅
**Endgame Mechanics**: Genesis Project, First Strike, Philosophical Victory

**Implementation**:
- ✅ **Genesis Project**: Seed sterile worlds with Earth life
  - Implemented in `genesis_project.py`
  - Seeding mechanics, evolution simulation, and Dark Forest risks active
- ❌ **First Strike Dilemma** (Deprioritized): Preemptive attack capability
- ✅ **Philosophical Victory**: Answer the Fermi Paradox
  - Collect 15 evidence points from:
    - Swan song discoveries (extinction evidence)
    - Hostile encounters (dark forest evidence)
    - Peaceful contacts (cooperation evidence)
    - Transcendence techs (great filter evidence)
  - Can be achieved alongside Contact Victory

### Design Decisions (User-Approved)
- ✅ Hybrid Civilization tech reduces self-destruct to 0.1% (not complete elimination)
- ✅ Seeded worlds that evolve intelligence can attack you (Dark Forest risk)
- ✅ Philosophical Victory achievable alongside Contact Victory
- ✅ Multiple low-integration penalties beyond self-destruct risk

---

## 🌟 Quality Assurance & Polish (COMPLETE) ✅

- ✅ **Code Restoration**: Restored `legacy_of_stars_v3.py` after corruption
- ✅ **Integration**: All subsystems (Genesis, Integration, Leakage, Warnings) verified working together
- ✅ **UI**: Dynamic menus implemented for all new features

---

## 🌟 Stretch Goals (Phase 4+)


- **Multiplayer**: Civilizations are other players
- **Custom Scenarios**: Preset galaxy configurations
- **Modding Support**: JSON-based civilization definitions
- **Timeline Visualization**: Graph of all events over generations
- **Steam Release**: Polish for public distribution

---

## ✅ FINAL STATUS: ALL PHASES 1-3 COMPLETE

**Completion Date**: 2026-02-09

All planned features from Phases 1-3 have been implemented and integrated:
- ✅ Dark Forest mechanics with 5 civilization strategies
- ✅ WOW! Signal ultra-long-term legacy system (Gen 1 → Gen 144)
- ✅ Attack Warning System with defensive actions
- ✅ 44 technologies across 6 tiers (historically accurate SETI progression)
- ✅ AI Strategic Advisor for player guidance
- ✅ Swan Song Messages from extinct civilizations
- ✅ Passive Signal Leakage (realistic broadcast detection)
- ✅ Integration Progress System (bio-tech tracking)
- ✅ Philosophical Crisis Events (5 mid-game events)
- ✅ Philosophical Victory (answer the Fermi Paradox)
- ✅ Genesis Project (seed sterile worlds)

**Current Status**: FEATURE-COMPLETE ✅
**Next Milestones**:
- Playtesting & balance refinement
- Bug fixes based on playtesting feedback
- Phase 4+ stretch goals (multiplayer, modding, Steam polish)
