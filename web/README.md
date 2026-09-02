# Legacy of Stars - web front-end (phases W2-W3)

A playable browser build of the console game, with a 3D star map (Three.js) as the main
screen's centre column. The Python engine (`src/`) is unchanged and runs inside a
[Pyodide](https://pyodide.org) worker; the main thread only ever talks JSON to it
(`src/bridge.ts` / `src/worker.ts`, per `docs/web_contract.md`). The UI is Preact, plain CSS,
no framework.

## Install

```bash
cd web
npm install
npx playwright install chromium      # once, for the tests
```

Python 3.12+ must be on `PATH` as `python` (override with the `PYTHON` environment variable).

## Where engine.zip comes from

`web/public/engine.zip` is **generated, not committed**. `scripts/build_web_engine.py` (in the
repository root) packs `src/*.py` and `data/**/*.json` - no tests, no `legacy/`, no
`__pycache__`, no saves or logs - keeping the repository layout, so the worker can unpack it
into `/engine`, put `/engine` on `sys.path` and `from src.web_api import GameSession`.

```bash
npm run engine        # == python ../scripts/build_web_engine.py; prints the size
```

`npm run dev` and `npm run build` run it first, so a stale zip is not a failure mode.

The Pyodide runtime (`pyodide.mjs`, `pyodide.asm.mjs`, `pyodide.asm.wasm`,
`python_stdlib.zip`, `pyodide-lock.json`) is copied out of `node_modules/pyodide` into
`public/pyodide/` by a small plugin in `vite.config.ts`, self-hosted (offline-first) and
loaded at run time with a dynamic `import()`, never bundled. Both `public/pyodide/` and
`public/engine.zip` are git-ignored; a clean checkout regenerates them.

## Run

```bash
npm run dev           # http://localhost:5173
npm run typecheck     # tsc --noEmit, strict
npm run build          # engine.zip + typecheck + dist/
npm run preview       # serve dist/ (Pyodide needs http://, file:// will not do)
npm run unit          # Vitest: the pure scene modules (no browser, no engine) - ~0.3 s
npm test              # Playwright: builds, previews, runs tests/*.spec.ts
npm run test:all      # unit, then Playwright
```

`npm run unit` (Vitest, `vitest.config.ts`) covers `src/scene/coords.ts` and
`src/scene/palette.ts`: the sky directions of Sirius, Vega and Proxima against their real
J2000 positions, the radial compression (monotonic, and the 1,800 LY WOW! source pinned to
the rim in both scales), the name-hash fallback for a system with no `ra`/`dec`,
spectral-type parsing (including `DZ8` and the WOW! source's annotated
`G2V? (candidate ...)`) and the description-to-mood rules. The two runners never see each
other's files: Vitest takes `tests/unit/**/*.test.ts`, Playwright takes `tests/*.spec.ts`.

`npm test` starts its own server (`npm run build && npm run preview` on port 4173) and runs:

- `tests/smoke.spec.ts` - the engine boots and the start screen renders, no console errors.
- `tests/play.spec.ts` - a full slice: new game (seed 1) -> WOW! decision (standard reply) ->
  Generation 1 / Year 1977 on the main screen -> `focus_research` and `public_outreach` ->
  advance one generation (answering any philosophical-event/doctrine dialog the engine
  raises, generically - the test never asserts a specific random outcome) -> manual save
  ("e2e") -> page reload -> load "e2e" -> the generation matches.
- `tests/map.spec.ts` - W3: the canvas is there and sized, one `.star-label-system` per
  `state.systems[]` entry (compared against `#app[data-systems]`), the WOW! source labelled
  "1,800 LY", clicking Proxima Centauri's label selects it and opens the card, the selection
  becomes the default in the next system picker, Escape clears it, the scale toggle flips
  `data-scale`, and the List overlay selects the same way the map does.

Screenshots land in `test-results/` (`opening.png`, `main.png`, `dialog-system-picker.png`,
`smoke.png`, `map.png`, `map-selected.png`, `map-true-scale.png`).

## Layout

```
web/
├── index.html            #app mount point; styles.css is linked here
├── src/
│   ├── types.ts           the contract from docs/web_contract.md, hand-written
│   ├── worker.ts           Pyodide: unpack engine.zip, one GameSession, {id, method, args}
│   ├── bridge.ts           EngineBridge: promises, JSON parsing, progress/ready
│   ├── store.ts            app state: ViewState, journal, dialogs, toast, map selection/scale
│   ├── saves.ts             localStorage saves (prefix `los.save.`) + file export/import
│   ├── app.tsx              routes start / opening / main off store.state.phase
│   ├── main.tsx             creates the Store, mounts <App>, maintains #app test hooks
│   ├── styles.css           the one stylesheet (dark theme)
│   ├── scene/               the 3D star map (W3)
│   │   ├── coords.ts          ra/dec/distance -> scene position; radial compression (pure)
│   │   ├── palette.ts         spectral class -> colour/size; description -> mood (pure)
│   │   ├── starfield.ts       the static background shell of points
│   │   └── StarMap.ts         the class: renderer, scene, camera, OrbitControls, CSS2D labels
│   └── ui/
│       ├── LoadingScreen.tsx    Pyodide boot progress (kept from W1)
│       ├── StartScreen.tsx      New Game (seed), Load Game, import file, Help
│       ├── OpeningScene.tsx     the 1977 WOW! decision + reply composer + result panel
│       ├── MainScreen.tsx       layout + dialog/modal routing + keyboard shortcuts
│       ├── MapPanel.tsx         the star map's Preact wrapper: toolbar, card, list overlay
│       ├── Header.tsx, StatusPanel.tsx, SystemsPanel.tsx, ThreatsPanel.tsx,
│       │   ActionsPanel.tsx, EventLog.tsx    the HUD panels
│       ├── Dialogs.tsx          system/text/tech/threat/defense/event/dossier pickers
│       ├── DoctrineModal.tsx, EventModal.tsx, DossierModal.tsx, MenuModal.tsx,
│       │   HelpModal.tsx, SummaryModal.tsx, Toast.tsx
├── scripts/engine.mjs    npm -> python scripts/build_web_engine.py
├── vitest.config.ts      unit tests only (tests/unit/**/*.test.ts)
└── tests/
    ├── smoke.spec.ts      engine boots, start screen renders
    ├── play.spec.ts       full playable slice (see above)
    ├── map.spec.ts        the 3D map (see above)
    └── unit/              Vitest: coords.test.ts, palette.test.ts
```

## The star map (W3)

**Coordinates.** `x = d*cos(dec)*cos(ra)`, `y = d*sin(dec)`, `z = d*cos(dec)*sin(ra)`, with the
y axis on the north celestial pole - the plan's formula, fed straight from
`state.systems[].ra/.dec` (J2000 degrees) and `.distance` (light-years).

**Compression.** The catalogue spans 4.24 LY to 51 LY and the WOW! source sits at 1,800 LY, so
the radius is `r = k * ln(1 + d/d0)` with `d0 = 4` and `k` solved from `k * ln(1 + 51/4) = 60`
(k is about 22.9): the catalogue's outer edge lands on scene radius 60, Proxima on 16.5 and
Sirius on 26.3 - a linear scale would have put those two at 5.0 and 10.1. The "Scale" button
switches to `r = d * k2` with `k2 = 60/51`, which keeps the same outer ring so the two views
are comparable. Anything past the catalogue - in practice only the WOW! source - is pinned to
the rim at radius 72 in its true direction (RA 293.7, Dec -27) and labelled "1,800 LY". A
system the engine gave no `ra`/`dec` for gets a deterministic direction from an FNV-1a hash of
its name, spread evenly over the sphere.

**What the map shows.** Earth is a blue sphere with a glow sprite at the origin. Stars are
sprites coloured by spectral class (O blue-white through M red-orange, D pale white and
smaller, luminosity class III larger, unknown grey). `knowledge` 0 draws the star dim; a
description that names a civilization adds an amber halo, one containing "EXTINCT" a grey one;
`is_seeded` adds a green ring and `contacted` a bright blue one (contact outranks a seed);
`messages_sent` adds a small outgoing tick. Undiscovered catalogue stars are simply absent -
the dark forest. Faint rings at 5/10/20/50 LY and a static starfield give orientation.

**Interaction.** OrbitControls rotate/zoom/pan; clicking a star (its label, or within 18 px of
it on the canvas) selects it. The selection lives in the store, opens the compact card
(distance, type, knowledge, description, last reply, Dossier / Send message / Focus research)
and becomes the default in the next system picker - as a "Continue with X" button above the
full list, never as a restriction. "Home" reframes the whole scene, "Focus" flies to the
selected star, Escape clears the selection, and "List" opens the old flat systems list as an
overlay.

**Cost.** At most 60 systems are drawn. One `requestAnimationFrame` loop renders only when
something changed (a state update, a controls `change` event, or a camera flight), so an idle
page issues no draw calls; `devicePixelRatio` is capped at 2 and `dispose()` frees every
geometry, material, texture and DOM label.

Everything about the scene is arranged for W4: each system is a `Group` at the star's
position, Earth is `StarMap.earthGroup`, `update()` diffs by name so objects hung off those
groups survive a state change, and `requestRender()` is the hook an animation drives itself
with.

## What's covered vs. intentionally missing

Covered: the full action set (`send_message`, `focus_research`, `public_outreach`,
`research_tech` + doctrine follow-up, `advance_generation`, `defend`, `consult_advisor`,
`listen_swan_song`, `genesis_seed`, `respond_event`), the 1977 WOW! opening (custom /
director-drafted / standard reply), system dossiers, threats, the event journal with big-kind
modals, save/load (manual, autosave, export/import JSON, console-compatible), Help and the
final report/score.

Missing by design (not part of W2/W3): event animations and shaders (W4), LLM text in
the browser (`urllib` does not work in Pyodide - the engine falls back to its offline content
bank, same as the console with `LOS_OFFLINE=1`).

Three small contract gaps were found while building the UI and have since been fixed on the
Python side: `help` now works with no game in progress (the Start screen's Help link calls it
directly, no throwaway session needed); `technologies.available[]` carries `year_context`,
shown in the tech dialog under each description; and `genesis.targets[]` is the exact
sterile/habitable/unseeded/non-WOW!-source system list the Genesis picker shows, in order.

## Measurements (Windows 11, Node 24.18, Chromium via Playwright)

| | |
|---|---|
| `engine.zip` | ~99 KiB (25 files) |
| Pyodide runtime | ~13 MiB raw / ~6 MiB gzipped |
| `dist/` (W2 build) | ~14 MiB, `index-*.js` ~50 KiB / ~16 KiB gzipped |
| Time to `ready` | ~1 s (worker start -> engine imported, uncached local server) |

Well inside the plan's 4-second budget.
