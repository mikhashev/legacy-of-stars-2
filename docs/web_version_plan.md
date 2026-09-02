# Legacy of Stars — Web Version Plan (Three.js + shaders)

**Date:** 2026-09-03
**Basis:** the "Path to a web version" section of the v1.0 plan; the v1.1 engine is stable, 186 tests green
**Status:** approved, owner decisions in §9

---

## 0. Summary and recommendation

The web version is the same game in a browser: a 3D star map around Earth, a HUD instead of the
text menu, animations of light spheres and fleets driven by engine events, browser-based saves,
a static site on GitHub Pages.

**Recommendation:** option **A — Pyodide + Three.js**. The Python engine runs in the browser via
WebAssembly in a Web Worker, the frontend is TypeScript (Vite, Three.js, Preact for the HUD) and
talks to it only through JSON messages. One engine codebase and one test suite; no server needed.

Six phases, W0–W5, ordered so that a playable web version (without 3D yet) appears after W2, with
3D and shaders layered on top. Estimate: 14–19 net working days.

| Phase | What | Estimate |
|---|---|---|
| W0 | Engine facade `GameSession.perform()`, JSON contract, tests | 1 day |
| W1 | Pyodide in a Web Worker, `engine.zip` build, loading screen | 1–2 days |
| W2 | Playable web UI without 3D: HUD, actions, dialogs, log, saves | 3–4 days |
| W3 | 3D star map: coordinates, spectral colors, click selection, fog | 3–4 days |
| W4 | Shaders and event animations: message spheres, fleets, leakage front, background | 3–5 days |
| W5 | Polish and release: responsiveness, hotkeys, final screen, GitHub Pages | 2 days |

---

## 1. Scope

**In scope:** the full v1.1 game loop (the Wow! discovery, all actions, doctrines, philosophical
events, defense, swan songs, arks, victories, the final report); the 3D map; event-driven
animations; saves in localStorage plus JSON file export/import; the game's English text.

**Out of scope:** an in-browser LLM (offline mode is the primary mode anyway; see §7 on a
possible bridge later), multiplayer, new narrative content, localization, mobile optimization
beyond "doesn't break on a tablet."

---

## 2. Platform choice

| Option | How | Pros | Cons |
|---|---|---|---|
| **A. Pyodide + Three.js** | the Python engine runs in the browser (WebAssembly), the frontend calls it over a JSON bridge in a Web Worker | one codebase and one test suite; static site; rule changes are made once | ~7–10 MB initial load (cached), 2–4 s startup; `urllib` doesn't work — LLM unavailable |
| B. Python server + Three.js | the engine sits behind an HTTP/WebSocket API, the browser is a client | LLM works; a thin API | needs a running server; "just open the link" doesn't work |
| C. Rewrite the engine in TypeScript | a native web game | instant start, one language | ~5,000 lines of logic and ~190 tests to rewrite and keep in sync; Python becomes legacy |

**Why A.** The engine already satisfies everything A needs: no I/O in the game logic,
`view_state()`, `available_actions()`, `drain_events()`, `to_dict()/from_dict()`, star
coordinates. The only disk access is reading `data/*.json` at startup, which works fine on
Pyodide's virtual filesystem. Option C stays as a fallback: the JSON contract from W0 is the
same for A and C, so rewriting in TS later wouldn't require changing the frontend.

---

## 3. Architecture

```
browser
├── main thread: Vite + TypeScript
│   ├── ui/        Preact components for the HUD (status, actions, dialogs, log, dossier, tech tree)
│   ├── scene/     Three.js: star map, camera, spheres/trajectories, shaders
│   ├── bridge.ts  postMessage client to the worker: newGame / load / perform / state / save
│   └── store.ts   the latest view_state plus event queue → UI and scene
└── worker: Pyodide
    ├── engine.zip (src/ + data/), unpacked into /engine
    └── src/web_api.py: GameSession — the single entry point for JS
```

**Bridge rules.** Only JSON strings cross the Python↔JS boundary (no Pyodide proxy objects: they
leak memory and break serialization). The worker holds a single `GameSession`. The main thread is
never blocked: every call is a `Promise`.

**Contract (W0)** — `src/web_api.py`:

```python
class GameSession:
    def new_game(self, seed: int | None) -> str            # view_state JSON
    def load(self, save_json: str) -> str                  # view_state
    def save(self) -> str                                  # save JSON (serialize())
    def state(self) -> str                                 # view_state
    def perform(self, action_id: str, params_json: str) -> str
        # -> {"ok": bool, "message": str, "events": [...], "state": {...},
        #     "needs": null | {"kind": "doctrine", "tech_id": ..., "options": [...]}}
```

`perform` covers everything the console dispatcher `GameInterface._act_*` currently does:
`send_message`, `focus_research`, `public_outreach`, `research_tech` (with the `choose_doctrine`
follow-up), `advance_generation`, `defend` (three kinds), `consult_advisor`,
`listen_swan_song`, `genesis_seed`, `respond_event`, plus the two discovery actions
`wow_reply` / `wow_silent` and `compose_director_message`. The parameters are the same as in
`ActionSpec.needs`: `system`, `text`, `tech`, `threat`, `defense`, `choice`.

---

## 4. Phases

### W0 — Engine facade and contract (Python, no frontend)

- A new `src/web_api.py` with `GameSession` (above). Inside it, only calls to existing
  `ContactProgram` methods; no new rules logic.
- `ContactProgram` gets an optional `data_dir` (currently the path is computed from `__file__`;
  this works fine on Pyodide, but an explicit parameter simplifies tests and the build).
- A contract document `docs/web_contract.md`: the `view_state` schema (already present in code,
  describe the fields), all event `kind`s and their `data`, the `perform` response. This is the
  spec for the frontend, and for option C if it's ever needed.
- Tests `tests/test_web_api.py`: every action via `perform`, a doctrine via `needs`, the
  new → save → load → state cycle, a full 60-generation game through the facade with no
  exceptions, and a "sanity" test: JSON responses serialize with `json.dumps` and no `default=`
  (no engine objects leaking out).
- Verification: `python -m unittest discover -s tests -t .`.

### W1 — Pyodide in a worker

- A `web/` directory in this same repository: `package.json`, Vite, TypeScript, Three.js, Preact.
- `scripts/build_web_engine.py` builds `web/public/engine.zip` from `src/` and `data/`
  (excluding `legacy/`, tests, and `__pycache__`).
- `web/src/worker.ts`: load Pyodide (a current version, Python 3.12) from a CDN or from
  `node_modules`, `unpackArchive`, `import web_api`, a message handler
  `{id, method, args}` → `{id, result | error}`.
- `bridge.ts` with types hand-generated from `docs/web_contract.md`
  (`ViewState`, `GameEvent`, `PerformResult`).
- A loading screen with progress; measure startup time and size for the phase report.
- A smoke-test page: new game, list of actions, `advance_generation` ten times, print the JSON.
- Verification: `npm run build` with no errors, the page works in Chrome and Firefox.

### W2 — Playable web UI without 3D

Phase goal: a full game can be played in the browser to victory or defeat, at parity with the
console version.

- HUD panels from `view_state`: program status (AP, funding, support, RP, tech level,
  integration, risks, leakage front), the director, contact/evidence counters (contacts, Fermi
  evidence).
- An actions panel from `available_actions()`; for `needs` — dialogs: pick a system (list with
  distance and type), message text, pick a technology (by tier, with `year_context` and the
  reason it's locked), threat + defense type, an event response choice, a doctrine choice.
- An event log: a feed of `events` with icons by `kind`; the big ones (`wow`, `victory`,
  `game_over`, `attack_warning`, `philosophical_event`) show as modal dialogs.
- The Wow! 1977 opening scene: the same text as `run_opening_scenario`, reply/stay-silent
  buttons, a custom message input or the director's draft.
- A system dossier: messages, replies, expected arrivals.
- Saves: autosave after every generation to localStorage, manual slots, JSON file
  export/import (compatible with the console version's `saves/*.json`).
- Final report and score: `build_summary` returns text — show it as is for now, break it out
  into panels later.
- Verification: a manual playthrough to 40 generations with an event, a doctrine, defense, a
  save and a load; the same scenario as the "Final check" section of the v1.0 plan.

### W3 — 3D star map

- Coordinates: `ra`, `dec` (J2000 degrees) and `distance` (ly) → Cartesian:
  `x = d·cos(dec)·cos(ra)`, `y = d·sin(dec)`, `z = d·cos(dec)·sin(ra)` (y axis = north pole).
  Radial compression for readability: `r' = k·ln(1 + d/d0)`, so that 4 and 51 ly both fit in
  one frame; the Wow! source at 1800 ly is a marker at the edge of the scene in the correct
  direction (RA 293.7°, Dec −27°) with a distance label.
- Stars are sprites/points colored by spectral class (O blue … M red, D white, III larger),
  labels via CSS2DRenderer, Earth at the center.
- Undiscovered catalog stars aren't drawn; known but unstudied ones are dim; those with a
  civilization (per `description`) get a colored halo; extinct ones are gray; seeded ones get a
  green marker.
- Clicking a star selects the system for the next action and opens the dossier.
- Camera: OrbitControls, focus on the selected star, a "home" button.
- Verification: all 53 catalog stars in the correct directions (compare Sirius, Vega, Proxima
  against a planetarium), 60 fps on integrated graphics.

### W4 — Shaders and event animations

| Event / state | Visualization |
|---|---|
| `messages_sent[].generation`, `arrival_gen` | An expanding light sphere from Earth with radius `c × elapsed years`; fades on arrival |
| `next_response_gen` | A sphere from the star toward Earth |
| `threats[]` (`eta`, `arrival_gen`, `attack_type`) | A star→Earth trajectory with a fleet marker at the fraction of the distance covered (0.1c / 0.175c / 0.12c), pulsing when `eta ≤ 2` |
| `status.broadcast_radius` | A translucent sphere for the leakage front, growing by 25 ly per generation |
| `system_discovered` | A flash and the star emerging from the fog |
| `response_received` | A pulse at the star, a flash at Earth |
| `attack_resolved`, `info_attack` | A red flash at Earth |
| `genesis` | An ark trail star←Earth, then a green glow at the colony |
| `wow` | A beam toward Sagittarius |
| Background | A starfield and nebula shader; "dark forest" is a fog hiding directions not yet discovered |

All animations are derived from `view_state` and `events`; the engine doesn't change. A
generation advance is a single 1–2 s animation, all spheres and fleets move forward by 25 years.

### W5 — Polish and release

- Responsive layout (panels stack on narrow screens), hotkeys matching the console (1–6, v, s, h).
- A help screen from `HELP_TEXT`, achievements, statistics.
- GitHub Actions: build `engine.zip` + `vite build` + deploy to GitHub Pages; cache Pyodide via
  a service worker so the second run is instant.
- README: a "play in browser" link, a section on the web build.
- Budgets: first load ≤ 12 MB, startup ≤ 4 s on a typical laptop, 60 fps in the scene.

---

## 5. What needs to change in the engine (minimum)

- `src/web_api.py` — the new facade (W0).
- `ContactProgram(data_dir=...)` — an optional parameter (W0).
- Nothing in the rules. The console `GameInterface` keeps working; the engine's tests aren't
  touched.
- Optional: split `build_summary` into a `summary_dict()` structure for panels (W5).

---

## 6. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Pyodide size and load time | Measure in W1; service worker and caching; a loading screen with progress; if >4 s on a laptop — consider option C |
| Memory leaks via Pyodide proxies | Only JSON strings cross the boundary, enforced in `bridge.ts` and the W0 test |
| Frontend and engine drifting apart after rule changes | A single source of truth — `docs/web_contract.md` + a W0 test that `view_state` matches the schema |
| Paths to `data/` on the virtual filesystem | `data_dir` parameter + the build script places `data/` next to `src/` |
| Map readability (4 vs. 51 ly) | Logarithmic radius compression, distance labels, a "true scale" toggle button |
| Shader performance on weak GPUs | Everything in one `ShaderMaterial` for the spheres, ≤ 100 objects, degrade by disabling the background nebula |

---

## 7. LLM in the browser (later, not part of this plan)

`AIManager` calls `urllib`, which doesn't work on Pyodide. If an LLM in the web version is
wanted later: a `js_fetch` provider, where Python calls the JS `fetch` via `pyodide.ffi` to a
local Ollama/LM Studio with CORS. The engine allows for this (`_ai_text` is already isolated),
the amount of work is small, but it's a separate task after W5.

---

## 8. Verification by phase

```bash
python -m unittest discover -s tests -t . -v        # W0: + tests/test_web_api.py
python scripts/build_web_engine.py                  # W1: web/public/engine.zip
cd web && npm run build && npm run preview          # W1–W5
```

Manual scenarios: W1 the smoke-test page; W2 a 40-generation game with save/load; W3 checking
star directions; W4 a message to Proxima (the sphere arrives in 1 generation) and a fleet from
an LA system (the marker moves along the trajectory to ETA); W5 deploy and launch from a clean
profile.

---

## 9. Owner decisions (made 2026-09-03)

1. **Platform:** A — Pyodide + Three.js.
2. **HUD:** Preact.
3. **Code:** a `web/` directory in this repository.
4. **Order:** playable UI without 3D (W2) before the map (W3).
5. **Hosting:** GitHub Pages.
