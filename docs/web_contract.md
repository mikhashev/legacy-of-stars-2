# Legacy of Stars — web contract (W0)

The JSON protocol between the browser front-end and the Python engine, as implemented in
`src/web_api.py`. This is the specification the TypeScript types (`ViewState`, `GameEvent`,
`PerformResult`) are written from. Every field below is derived from the code; when the engine
changes, this document and `tests/test_web_api.py` change with it.

---

## 1. Message protocol

One `GameSession` per game, living in the Pyodide worker. Everything crossing the boundary is a
**JSON string** built from plain types only (`json.dumps` is called without a `default=` hook, so a
non-serializable value fails here rather than silently in the browser).

```python
class GameSession:
    def __init__(self, data_dir: Path | None = None, offline: bool = True)
    def new_game(self, seed: int | None = None) -> str   # ViewState JSON
    def load(self, save_json: str) -> str                # ViewState JSON
    def save(self) -> str                                # save-file JSON (save_manager.serialize)
    def state(self) -> str                               # ViewState JSON
    def perform(self, action_id: str, params_json: str = "{}") -> str   # PerformResult JSON
```

- `data_dir` — where `star_catalog.json`, `tech_tree.json` and `templates/` are read from. Default:
  the repository `data/`. A directory that does not exist raises `FileNotFoundError` at
  `new_game()`/`load()`.
- `offline` — defaults to `True`; the browser build has no `urllib`, so the engine uses its written
  content bank instead of an LLM.
- `state()` and `save()` raise `RuntimeError` before `new_game()`/`load()`. `load()` raises
  `save_manager.SaveError` for text that is not a save of format version 1. `perform()` never
  raises: every failure comes back as `ok: false`.
- `new_game()` and `load()` discard any events queued during construction, so the event stream a
  front-end sees comes only from `perform()`.
- Saves are byte-compatible with the console's `saves/*.json`.

### PerformResult

```jsonc
{
  "ok": true,                 // the engine applied the action
  "message": "...",           // program.message, or facade text for actions the engine leaves silent
  "events": [ /* GameEvent */ ],
  "state": { /* ViewState */ },   // null only when no game is in progress
  "needs": null,              // or a follow-up request, see §4
  "data": { }                 // present only for the actions marked "data" in §3
}
```

`ok` semantics: `ok` means *the engine applied this action*. It is decided per action from
observable state — action points spent, a flag flipped, a technology now researched, the engine's
own return value — never by parsing `message`. Engine refusals (`"Not enough Action Points!"`,
`"System X not found in database."`, a locked technology, a defence already taken) come back as
`ok: false` with that message. One deliberate exception: a swan-song scan that finds nothing is
`ok: true`, because it ran and cost an action point.

`events` are the events emitted by this action only (`program.drain_events()`), in order.

### Failure messages produced by the facade itself

| Situation | `message` |
|---|---|
| No game yet | `no game in progress: call new_game() or load() first` (with `"state": null`) |
| Unknown `action_id` | `unknown action 'x'. Known actions: ...` |
| `params_json` not a JSON object | `params is not valid JSON (...)` / `params must be a JSON object` |
| Missing/ill-typed parameter | `missing or invalid parameter 'system' (expected a non-empty string)` |
| Out-of-range index | `parameter 'threat' must be between 0 and N` |
| Action absent from `state.actions` | `action not available now` |
| Game already over | `the game is over: <game_over_reason>` |
| Unexpected engine exception | `internal error in action 'x': ...` |

The availability check applies to all actions except the ungated ones: `wow_reply`, `wow_silent`,
`compose_director_message`, `choose_doctrine`, `summary`, `help`. Once `state.game_over` is true only
`summary` and `help` still work.

### Differences from the console dispatcher

- `advance_generation` does **not** autosave (the browser stores saves itself).
- The "answer the philosophical crisis first" refusal names the `respond_event` action instead of a
  numeric menu key.
- The console forces the 1977 decision before the first turn; the facade does not gate other actions
  on it. Show the opening scene while `state.wow.decided` is `false`.

---

## 2. Parameter types

`system` — star system **name** (`state.systems[].name`), not an index.
`tech` — technology id (`state.technologies.available[].id`).
`threat` — **0-based** index into `state.threats` (i.e. `state.threats[i].index - 1`).
`choice` — **0-based** option index.
Integers may be sent as JSON numbers or as decimal strings.

---

## 3. Actions

| `action_id` | params | ok when | notes |
|---|---|---|---|
| `send_message` | `{system, text}` | a message was queued (`stats.messages_sent` grew) | `text` may be empty; costs 1 AP. Refused for a post-biological civilization without the matching technology. |
| `focus_research` | `{system}` | 1 AP was spent | Crossing 20 % knowledge on an inhabited system adds support and RP to `message`. |
| `public_outreach` | `{}` | 1 AP was spent | |
| `research_tech` | `{tech}` | the technology is now researched | Sets `needs` when the technology carries a doctrine choice (§4). Free (costs RP, not AP). |
| `choose_doctrine` | `{tech, choice}` | a doctrine was recorded | Ungated follow-up to `research_tech`; `message` keeps the research text and appends the doctrine summary, as in the console. |
| `advance_generation` | `{}` | the generation counter grew | Refused while `state.pending_event` is set. Emits most of the game's events. |
| `defend` | `{threat, defense}` | a defensive action was recorded or the threat was removed | `defense` ∈ `"emergency"` (all AP, −50 %), `"evacuate"` (1 AP, −30 %), `"diplomacy"` (1 AP, may abort a low-deception trap). Diplomacy is `ok: true` even when it fails: the attempt was made and paid for. |
| `consult_advisor` | `{}` | the advisor ran this generation | Free, once per generation; needs the AI Strategic Advisor technology. |
| `listen_swan_song` | `{system}` | 1 AP was spent | A scan that detects nothing is still `ok: true`. The target must be studied to 20 % knowledge (see `swan_song_targets`); an unstudied system is refused for free with *"Study the system first: 20% knowledge is needed before a deep scan."*, checked **before** the extinction refusal so that message cannot leak either. |
| `genesis_seed` | `{system}` | `GenesisProject.seed_world` returned success | Costs 1 AP + 500 RP + 20 % funding; one world per generation; the target must be studied to 20 % knowledge (see `genesis.targets`). |
| `respond_event` | `{choice}` | the choice was applied | `choice` indexes `state.pending_event.choices`. |
| `wow_reply` | `{text}` | the 1977 decision was open | Opening scene. Empty/absent `text` sends the standard message; longer text is truncated at 500 characters. `data`: `{message, message_full, excerpt, arrival_gen: 72, response_gen: 144, replied: true}` — `message` and `message_full` are both the whole stored reply (at most 500 characters), `excerpt` its first 100 characters plus `...`, which is what the console prints. |
| `wow_silent` | `{}` | the 1977 decision was open | `data`: `{replied: false, attack_damage_reduction: 0.15}`. |
| `compose_director_message` | `{}` | always | Returns the director's draft in `message`; decides nothing. `data`: `{draft}`. Feed it back as `wow_reply`'s `text`. |
| `summary` | `{}` | always | `message`: `build_summary()` text. `data`: `{score, score_breakdown: {label: points}}`. Works after game over. |
| `help` | `{}` | always | `message`: the console's `HELP_TEXT`. `data`: `{ai}` (the AI provider description). |

`state.actions` lists the ids the engine currently offers, with `label`, `cost` and `needs` — use it
to build the action bar; the ungated six above are never in it.

---

## 4. Doctrine follow-up flow

1. `perform("research_tech", {"tech": "genetic_pacification"})`
2. Result: `ok: true`, and

```jsonc
"needs": {
  "kind": "doctrine",
  "tech_id": "genetic_pacification",
  "name": "Genetic Pacification Doctrine",
  "description": "…",
  "options": [ {"index": 0, "name": "…", "description": "…"},
               {"index": 1, "name": "…", "description": "…"} ]
}
```

3. The UI shows the options and calls
   `perform("choose_doctrine", {"tech": "genetic_pacification", "choice": 1})`.

The technology is already researched at step 2; only the doctrine's effects (integration, support,
self-destruct risk, funding) are still pending. An out-of-range `choice` is rejected with `ok: false`
— unlike the console, the facade does not silently default to option 0. `state.active_doctrines`
lists the names in force.

---

## 5. GameEvent

```jsonc
{"kind": "response_received", "text": "…", "data": {…}, "generation": 12}
```

`text` is ready to display (the engine writes it, sometimes multi-line with emoji). `generation` is
the generation the event was emitted in. `data` keys per kind:

| `kind` | `data` | emitted by |
|---|---|---|
| `generation_start` | `year` (int) | start of `advance_generation` |
| `crisis` | *(none)* | integration crisis, ecological collapse |
| `bonus` | *(none)* | Intuitive director's +50 RP |
| `response_received` | `system` (str), `text` (str, the reply), `first` (bool) | a reply arrives |
| `system_discovered` | `system` (str), `distance` (float, LY) | telescopes catalogue a star |
| `attack_warning` | `system` (str), `arrival_gen` (int), `eta` (int), `attack_type` (str) | a hostile launch is detected |
| `attack_resolved` | `system` (str), `support_loss` (int), `funding_loss` (int), `severity` (str) | a fleet strikes Earth |
| `info_attack` | `system` (str), `attack_type` (`corrupted_technology` \| `societal_manipulation` \| `false_hope_signal` \| `philosophical_weapon`) | an information weapon lands |
| `philosophical_event` | `event_id` (str) | a crisis needs an answer |
| `briefing` | `idle_generations` (int) | the mission analyst volunteers a briefing after 2, 4, 6 … generations in which the player took no action; the text is the advisor's rule-based briefing under one "Mission analyst's briefing (the program has been idle for N generations):" line. Needs neither the AI Strategic Advisor technology nor the once-per-generation consultation, and changes no rule |
| `fermi_evidence` | `kind` (str), `amount` (int), `total` (int), `reason` (str) | evidence gained (announced ones only) |
| `achievement` | `name` (str) | achievement unlocked |
| `genesis` | `system` (str), and either `stage` (str) or `outcome` (`ally` \| `hostile`) | a seeded world progresses or decides |
| `victory` | `contacts` (list[str]) for the contact victory, `explanation` (str) for the philosophical one | victory reached (the game continues) |
| `wow` | *(none)* | the Generation 144 outcome |
| `game_over` | `reason` (str) | the program ends |

`attack_type` values: `fleet`, `laser_sail_probe`, `fusion_strike`, `wow_fleet`, `genesis_fleet`,
`mirror_fleet` (labels in `state.threats[].type_label`).

Suggested UI weight: modal for `wow`, `victory`, `game_over`, `attack_warning`,
`philosophical_event`, `attack_resolved`, `briefing`; journal line for the rest.

---

## 6. ViewState

Produced by `ContactProgram.view_state()` — the single source of truth. Nothing hidden (true
strategies, deception levels) ever appears here.

| Field | Type | Meaning |
|---|---|---|
| `generation` | int | 1-based; one generation = 25 years |
| `year` | int | `start_year + (generation - 1) * 25` |
| `start_year` | int | always 1977 |
| `director.name` | str | the current director |
| `director.traits` | list[str] | trait names |
| `director.skills` | `{diplomacy, science, administration}` → float 0–1, 2 decimals | effective skills |
| `status.action_points` | int | AP left this generation |
| `status.max_action_points` | int | AP pool this generation |
| `status.funding` | float | 0–100; below 20 ends the game |
| `status.public_support` | float | 0–100; below 10 ends the game |
| `status.knowledge_base` | float | 0–100, general xeno-knowledge |
| `status.research_points` | int | RP in hand |
| `status.passive_rp` | float | RP income per generation after the integration efficiency modifier |
| `status.tech_level` | int | 1 + highest researched tier (1–6) |
| `status.self_destruct_risk` | float | per-generation probability (4 decimals), capped at 0.08 |
| `status.ecological_risk` | float | per-generation probability, capped at 0.30 |
| `status.broadcast_radius` | float | leakage front in LY, grows 25 LY per generation |
| `status.leakage_multiplier` | float | 1.0 = full leakage, 0.0 = silence |
| `status.integration_level` | float | 0–1; tier 5 research needs 0.40 |
| `status.integration_status` | str | human-readable integration label |
| `active_doctrines` | list[str] | doctrine names in force |
| `active_effects` | list[str] | every permanent modifier currently in force, as short display lines (`ContactProgram.active_effects()`): the 1977 silence, the defensive/warning/survival technologies, leakage mitigation, propulsion and contact unlocks, the integration penalties or bonus in force, and one line per active doctrine. Derived from engine state only, empty at the start of a game; render it as a list, never parse it |
| `systems[]` | list | known star systems, in discovery order |
| `systems[].index` | int | 1-based position (the console's menu number) |
| `systems[].name` | str | the id used in action parameters |
| `systems[].distance` | float | light-years, 1 decimal |
| `systems[].spectral_type` | str \| null | e.g. `"M5.5V"`; drives the map colour |
| `systems[].ra`, `.dec` | float \| null | J2000 degrees, for the 3D map |
| `systems[].knowledge` | int | 0–100; 0 hides the description, 20 reveals a civilization (and lists an extinct one in `swan_song_targets`), 30 enables swan song recovery |
| `systems[].description` | str | what is known (empty while `knowledge` is 0) |
| `systems[].round_trip_generations` | int | generations for a message and its reply |
| `systems[].messages_sent[]` | `{text, generation, arrival_gen}` | our transmissions and when they land |
| `systems[].responses` | list[str] | replies received so far |
| `systems[].next_response_gen` | int \| null | generation the next reply arrives |
| `systems[].contacted` | bool | at least one reply received |
| `systems[].is_seeded` | bool | a Genesis ark is on its way or has landed |
| `catalog.known` | int | systems on the target list |
| `catalog.total` | int | catalogued stars (53 in `data/star_catalog.json`) |
| `catalog.undiscovered` | int | catalogued stars not yet resolved |
| `catalog.discovery_chance` | float | chance per generation of resolving one |
| `threats[]` | list | inbound attacks |
| `threats[].index` | int | 1-based; `defend` takes `index - 1` |
| `threats[].source` | str | system name |
| `threats[].attack_type` | str | see §5 |
| `threats[].type_label` | str | display name, e.g. `"fusion strike fleet (0.12c)"` |
| `threats[].eta` | int | generations remaining (0 = arriving) |
| `threats[].arrival_gen`, `.arrival_year` | int | when it lands |
| `threats[].source_distance` | float | LY, for the trajectory |
| `threats[].enemy_stage` | str | `CivilizationStage` name or `"UNKNOWN"` |
| `threats[].defense_pct` | int | damage reduction accumulated |
| `threats[].actions_taken` | list[str] | `"Emergency Defense Protocol"`, `"Evacuation"`, `"Diplomatic Contact"` |
| `technologies.researched` | list[str] | technology ids (includes the five pre-1977 legacy ones) |
| `technologies.available[]` | `{id, name, tier, cost, description, year_context, locked}` | researchable now; `locked` is null or the reason string |
| `fermi_evidence` | `{extinction_evidence, dark_forest_evidence, cooperation_evidence, great_filter_evidence, total, goal}` | ints; `goal` is 15 |
| `contacts` | int | living civilizations that answered |
| `contacts_goal` | int | 3 |
| `victory` | bool | contact victory reached |
| `philosophical_victory` | bool | Fermi answer reached |
| `genesis.unlocked` | bool | the ark programme is available |
| `genesis.summary` | str | multi-line status text |
| `genesis.targets[]` | str[] | system names an ark may be launched at: studied to **20 % knowledge or more**, sterile, habitable, unseeded, not the WOW! source — the Genesis picker lists exactly these. The knowledge floor is what keeps the list from revealing where nobody lives before the player has looked; `genesis_seed` refuses an unstudied system with *"Study the system first: 20% knowledge is needed before launching an ark."*, checked **before** the has-civilization refusal so that message cannot leak either |
| `genesis.worlds[]` | `{system_name, seed_gen, arrival_gen, evolution_stage, is_hostile, is_destroyed, resolved, outcome}` | seeded worlds (`evolution_stage` 0 = in transit … 4 = spacefaring) |
| `swan_song_targets[]` | str[] | system names a deep scan may be pointed at: studied to **20 % knowledge or more** (the level at which `systems[].description` says *EXTINCT*), known to be extinct, not already scanned to a null result, not already recovered - the swan-song picker lists exactly these. Whether a system holds an archive is what the scan is for, so a silent system stays listed until one scan empties it; the list never reveals which systems hold archives, nor how many exist |
| `pending_event` | null \| `{id, name, description, choices: [{name, description}]}` | the philosophical crisis blocking `advance_generation` |
| `wow` | `{decided: bool, replied: bool, outcome: null \| "silence" \| "friendly" \| "hostile"}` | the 1977 decision and its Generation 144 result |
| `achievements` | list[str] | unlocked achievement names |
| `stats` | dict[str, int] | `messages_sent`, `responses_received`, `attacks_scheduled`, `attacks_survived`, `attacks_landed`, `info_attacks`, `swan_songs_found`, `systems_discovered`, `events_resolved`, `techs_researched`, `worlds_seeded`, `passive_detections` |
| `actions[]` | `{id, label, cost, needs}` | what the engine offers now; `needs` lists the parameter names the UI must collect (`system`, `text`, `tech`, `threat`, `defense`, `choice`) |
| `game_over` | bool | the run has ended |
| `game_over_reason` | str | why (empty while playing) |
