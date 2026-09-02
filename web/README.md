# Legacy of Stars - web front-end (phase W1)

The browser build runs the unchanged Python engine inside a [Pyodide](https://pyodide.org)
worker. The main thread only talks JSON to it: `src/bridge.ts` sends `{id, method, args}`,
`src/worker.ts` calls `src/web_api.py::GameSession` and sends the JSON string back.

W1 is plumbing only - there is no game UI yet (`preact` and `three` are installed for W2/W3).
What exists is a smoke page that starts a game, advances ten generations and prints a
view-state summary plus startup measurements.

## Install

```bash
cd web
npm install
npx playwright install chromium      # once, for the smoke test
```

Python 3.12+ must be on `PATH` as `python` (override with the `PYTHON` environment variable).

## Where engine.zip comes from

`web/public/engine.zip` is **generated, not committed**. `scripts/build_web_engine.py` (in the
repository root) packs `src/*.py` and `data/**/*.json` - no tests, no `legacy/`, no
`__pycache__`, no saves or logs - keeping the repository layout, so the worker can unpack it
into `/engine`, put `/engine` on `sys.path` and `from src.web_api import GameSession`. The
engine reads `data/` relative to `src/`, which is why the layout is preserved.

```bash
npm run engine        # == python ../scripts/build_web_engine.py; prints the size
```

`npm run dev` and `npm run build` run it first, so a stale zip is not a failure mode.

The Pyodide runtime (`pyodide.mjs`, `pyodide.asm.mjs`, `pyodide.asm.wasm`,
`python_stdlib.zip`, `pyodide-lock.json`) is copied out of `node_modules/pyodide` into
`public/pyodide/` by a small plugin in `vite.config.ts`. It is self-hosted rather than
loaded from the Pyodide CDN so the game stays offline-first, and it is loaded at run time
with a dynamic `import()` of a URL, never bundled: `pyodide.mjs` has Node-only branches and
the 9.15 MiB `.wasm` has no business going through a bundler. Both directories are
git-ignored; a clean checkout regenerates them.

## Run

```bash
npm run dev           # http://localhost:5173
npm run build         # engine.zip + dist/
npm run preview       # serve dist/ (Pyodide needs http://, file:// will not do)
npm test              # Playwright: builds, previews, drives the smoke page
```

`npm test` starts its own server (`npm run build && npm run preview` on port 4173), waits for
the ready marker `#app[data-ready="true"]`, checks generation 1 / year 1977 and then
generation 11, asserts there were no console errors and writes `test-results/smoke.png`.

## Measurements (Windows 11, Node 24.18, Chromium via Playwright)

| | |
|---|---|
| `engine.zip` | 98.6 KiB (25 files) |
| Pyodide runtime | 12.9 MiB raw / ~6.1 MiB gzipped (`pyodide.asm.wasm` 9.15 → 3.43 MiB, `python_stdlib.zip` 2.43 MiB, `pyodide.asm.mjs` 1.19 → 0.25 MiB) |
| `dist/` | 14 MiB (13 MiB of it is the Pyodide runtime) |
| Time to `ready` | ~1.1 s (worker start → engine imported, uncached local server) |

Well inside the plan's 4-second budget, so variant A (Pyodide) stands.

## Layout

```
web/
├── index.html            smoke page
├── src/types.ts          the contract from docs/web_contract.md, hand-written
├── src/worker.ts         Pyodide: unpack engine.zip, one GameSession, {id, method, args}
├── src/bridge.ts         EngineBridge: promises, JSON parsing, progress/ready
├── src/main.ts           the smoke page's logic (W2 replaces this with the Preact HUD)
├── scripts/engine.mjs    npm -> python scripts/build_web_engine.py
└── tests/smoke.spec.ts   Playwright acceptance for W1
```
