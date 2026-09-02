# Legacy of Stars - web front-end (phase W2)

A playable browser build of the console game, without the 3D star map (that is W3). The
Python engine (`src/`) is unchanged and runs inside a [Pyodide](https://pyodide.org) worker;
the main thread only ever talks JSON to it (`src/bridge.ts` / `src/worker.ts`, per
`docs/web_contract.md`). The UI is Preact, plain CSS, no framework.

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
npm test              # Playwright: builds, previews, runs smoke.spec.ts + play.spec.ts
```

`npm test` starts its own server (`npm run build && npm run preview` on port 4173) and runs:

- `tests/smoke.spec.ts` - the engine boots and the start screen renders, no console errors.
- `tests/play.spec.ts` - a full slice: new game (seed 1) -> WOW! decision (standard reply) ->
  Generation 1 / Year 1977 on the main screen -> `focus_research` and `public_outreach` ->
  advance one generation (answering any philosophical-event/doctrine dialog the engine
  raises, generically - the test never asserts a specific random outcome) -> manual save
  ("e2e") -> page reload -> load "e2e" -> the generation matches. Screenshots land in
  `test-results/` (`opening.png`, `main.png`, `dialog-system-picker.png`, `smoke.png`).

## Layout

```
web/
├── index.html            #app mount point; styles.css is linked here
├── src/
│   ├── types.ts           the contract from docs/web_contract.md, hand-written
│   ├── worker.ts           Pyodide: unpack engine.zip, one GameSession, {id, method, args}
│   ├── bridge.ts           EngineBridge: promises, JSON parsing, progress/ready
│   ├── store.ts            app state: ViewState, journal, dialogs, toast (store.ts + useStore hook)
│   ├── saves.ts             localStorage saves (prefix `los.save.`) + file export/import
│   ├── app.tsx              routes start / opening / main off store.state.phase
│   ├── main.tsx             creates the Store, mounts <App>, maintains #app test hooks
│   ├── styles.css           the one stylesheet (dark theme)
│   └── ui/
│       ├── LoadingScreen.tsx    Pyodide boot progress (kept from W1)
│       ├── StartScreen.tsx      New Game (seed), Load Game, import file, Help
│       ├── OpeningScene.tsx     the 1977 WOW! decision + reply composer + result panel
│       ├── MainScreen.tsx       layout + dialog/modal routing + keyboard shortcuts
│       ├── Header.tsx, StatusPanel.tsx, SystemsPanel.tsx, ThreatsPanel.tsx,
│       │   ActionsPanel.tsx, EventLog.tsx    the HUD panels
│       ├── Dialogs.tsx          system/text/tech/threat/defense/event/dossier pickers
│       ├── DoctrineModal.tsx, EventModal.tsx, DossierModal.tsx, MenuModal.tsx,
│       │   HelpModal.tsx, SummaryModal.tsx, Toast.tsx
├── scripts/engine.mjs    npm -> python scripts/build_web_engine.py
└── tests/
    ├── smoke.spec.ts      engine boots, start screen renders
    └── play.spec.ts       full playable slice (see above)
```

## What's covered vs. intentionally missing

Covered: the full action set (`send_message`, `focus_research`, `public_outreach`,
`research_tech` + doctrine follow-up, `advance_generation`, `defend`, `consult_advisor`,
`listen_swan_song`, `genesis_seed`, `respond_event`), the 1977 WOW! opening (custom /
director-drafted / standard reply), system dossiers, threats, the event journal with big-kind
modals, save/load (manual, autosave, export/import JSON, console-compatible), Help and the
final report/score.

Missing by design (not part of W2): the 3D star map and event animations (W3/W4), LLM text in
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
