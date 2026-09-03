# Telemetry Schema (playtest analytics)

**Date:** 2026-09-03
**Status:** proposal; the service is chosen after this schema (team decision 2026-09-03)
**Purpose:** answer the playtest questions, not count page views. The questions: do players
reach Generation 4, do they send a first message, do they live to a first reply or a first sky
change, do they come back for a second game, and what ends their games.

## Principles

- **Consent first.** Nothing is sent until the player switches telemetry on (start screen, off by
  default on GitHub Pages; itch.io build may ask once). The switch and its answer live in
  `localStorage`; the Help screen explains exactly what is sent.
- **No personal data.** No IP-based identification on our side, no names, no message texts, no
  save contents. `navigator.doNotTrack === "1"` disables telemetry regardless of the switch.
- **Anonymous return id.** A random id generated locally on first consent, stored in
  `localStorage`, resettable from the settings. It exists only to answer "did this browser come
  back", never to join with anything else.
- **Enums and buckets only.** Every attribute is a closed set or a bucket, so the same schema
  encodes as GoatCounter paths (`/event/attr1/attr2`) and as Umami/Plausible event properties
  without change. Free-form values are forbidden.
- **Sampling, not census.** Ad blockers and the itch.io iframe will drop a share of events;
  conclusions are about funnels (reached / did not reach), never about exact percentages.

## Events

| Event | Attributes (closed sets) | When |
|---|---|---|
| `session_start` | `platform` ∈ pages, itch, local; `build` = short git sha; `returning` ∈ first, returning | app ready, consent on |
| `game_new` | `seed` ∈ given, random | New Game |
| `game_load` | `source` ∈ autosave, manual, file | Load |
| `wow_decision` | `choice` ∈ reply, silent; `text` ∈ custom, director, standard | 1977 decision |
| `generation_reached` | `gen` ∈ 2, 4, 8, 12, 20, 30, 50, 100 (milestones only, each once per game) | advance |
| `first_message` | `gen_bucket` ∈ 1, 2-3, 4-7, 8-15, 16+ | first send_message |
| `first_reply` | `gen_bucket` (same buckets) | first response_received |
| `first_sky_change` | `gen_bucket` | first sky_change event |
| `first_threat` | `gen_bucket`; `type` ∈ fleet, probe, info | first attack_warning or info_attack |
| `undo` | `depth` ∈ 1, 2-3, 4+ (per generation, sent once per generation at advance) | advance |
| `briefing_shown` | `idle` ∈ 2, 4, 6+ | analyst briefing event |
| `victory` | `kind` ∈ contact, philosophical; `gen_bucket` ∈ <20, 20-39, 40-79, 80+ | victory event |
| `game_over` | `reason` ∈ annihilated, self_destruct, defunded, info_war, other; `gen_bucket` | game_over event |
| `session_end` | `minutes` ∈ <5, 5-14, 15-44, 45+; `max_gen_bucket` ∈ <4, 4-7, 8-15, 16-30, 31+ | pagehide / visibilitychange hidden |
| `return_visit` | `days` ∈ 1, 2-7, 8-30, 31+ | session_start with a known id |

Path encoding for GoatCounter: `/{event}/{attr1}/{attr2}` in the table's attribute order, e.g.
`/game_over/self_destruct/20-39`, `/first_reply/4-7`, `/session_end/15-44/8-15`.

## Funnels the schema answers

1. `session_start` → `game_new` → `generation_reached/4` → `generation_reached/8`: does the game
   survive its first quarter hour.
2. `game_new` → `first_message` → `first_reply`: does the letter loop close.
3. `game_new` → `first_sky_change` by `gen_bucket`: does the sky ever move for a real player
   (the calibration promise: by Generation 30).
4. `session_start/returning` share and `return_visit/days`: did it hook.
5. `game_over/reason` vs `victory/kind`: what ends games; read together with §12 of
   `design/design_notes.md` (survival is half the game).

## Implementation notes (one day)

- `web/src/telemetry.ts`: consent state, anonymous id, `track(event, attrs)` with a pluggable
  sink (`goatcounter` path sink first; `umami` property sink later), a queue flushed on
  `pagehide` via `navigator.sendBeacon`, a 60-second cap on `session_end` reporting.
- Hook points: the store's `applyResult` (events of every perform), `advance`, `enterGame`,
  `dismissModal` for victory/game over, `OpeningScene` for the WOW! decision.
- Start-screen switch and Help text; `?telemetry=off` URL flag for testers.
- Playwright: with consent off no request leaves the page; with consent on the expected paths are
  produced (intercept the sink, assert the encoded paths); DNT disables.
- Service decision after this schema: GoatCounter hosted (free, non-commercial, no cookies,
  path events) is sufficient for every event above; Umami self-hosted is the later step when
  volume or property-level analysis justifies a server.
