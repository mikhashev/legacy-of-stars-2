# Legacy of Stars - web front-end (phases W2-W5)

A playable browser build of the console game, with a 3D star map (Three.js) as the main
screen's centre column, animated by shaders off the engine's own event stream. The Python engine (`src/`) is unchanged and runs inside a
[Pyodide](https://pyodide.org) worker; the main thread only ever talks JSON to it
(`src/bridge.ts` / `src/worker.ts`, per `docs/reference/web_contract.md`). The UI is Preact, plain CSS,
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
repository root) packs `src/*.py` and `data/**/*.json` - no tests, no
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

`npm run unit` (Vitest, `vitest.config.ts`) covers the pure scene modules `src/scene/coords.ts`,
`src/scene/palette.ts` and `src/scene/timeline.ts`: the sky directions of Sirius, Vega and Proxima against their real
J2000 positions, the radial compression (monotonic, and the 1,800 LY WOW! source pinned to
the rim in both scales), the name-hash fallback for a system with no `ra`/`dec`,
spectral-type parsing (including `DZ8` and the WOW! source's annotated
`G2V? (candidate ...)`) and the description-to-mood rules, plus every W4 timing function -
sphere radius over scene time, the reply's launch generation, each attack type's fraction of c
and the leakage front's lag. The two runners never see each other's files: Vitest takes
`tests/unit/**/*.test.ts`, Playwright takes `tests/*.spec.ts`.

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
- `tests/animation.spec.ts` - W4, through the `window.__losMap` debug hook: scene time is
  seated on Generation 1 without animating, a message to Proxima Centauri becomes an outgoing
  sphere with `launchGen` 1 and radius 0, advancing one generation glides scene time through a
  strictly increasing run of values inside (1, 2] and leaves that sphere pinned to the star's
  4.2 LY and fully faded, the leakage front grows, the "Reduce effects" toggle reaches the
  scene and clears the flashes, and six further generations of whatever seed 1 produces (a
  discovery among them) run without a console error and inside the object budget.
- `tests/layout.spec.ts` - W5: 1280x800 and 1024x700 keep the three-column grid, 800x1000
  stacks map-first (a fixed ~4:3 block, >= 320px tall), a panel's collapsed state persists in
  `localStorage` across a fresh mount, and at every width
  `document.documentElement.scrollWidth <= innerWidth` (no horizontal scrollbar).
- `tests/showcase.spec.ts` - W5: loads the three fixtures `scripts/make_web_fixtures.py`
  builds (`web/tests/fixtures/*.json`) through the real Load screen's "Import JSON file", and
  checks the matching effect reached `window.__losMap`: a fleet marker (`threat.json`), a reply
  sphere (`reply.json`), a landed ark's colony glow (`genesis.json` - `arks()[].landed`, added
  to the debug hook alongside `spheres()`/`fleets()` for this test).

Screenshots land in `test-results/` (`opening.png`, `main.png`, `dialog-system-picker.png`,
`smoke.png`, `map.png`, `map-selected.png`, `map-true-scale.png`, `animation.png` mid-glide,
`animation-end.png`, `animation-reduced.png`, `animation-generation-8.png`, `layout-1280.png`,
`layout-1024.png`, `layout-800.png`, `showcase-threat.png`, `showcase-reply.png`,
`showcase-genesis.png` and their `-generation.png` mid-animation counterparts).

## Layout

```
web/
├── index.html            #app mount point; styles.css is linked here
├── src/
│   ├── types.ts           the contract from docs/reference/web_contract.md, hand-written
│   ├── worker.ts           Pyodide: unpack engine.zip, one GameSession, {id, method, args}
│   ├── bridge.ts           EngineBridge: promises, JSON parsing, progress/ready
│   ├── store.ts            app state: ViewState, journal, dialogs, toast, map selection/scale
│   ├── saves.ts             localStorage saves (prefix `los.save.`) + file export/import
│   ├── app.tsx              routes start / opening / main off store.state.phase
│   ├── main.tsx             creates the Store, mounts <App>, maintains #app test hooks
│   ├── styles.css           the one stylesheet (dark theme)
│   ├── scene/               the 3D star map (W3) and its animated layer (W4)
│   │   ├── coords.ts          ra/dec/distance -> scene position; radial compression (pure)
│   │   ├── palette.ts         spectral class -> colour/size; description -> mood (pure)
│   │   ├── timeline.ts        scene time -> radii, fleet fractions, leakage front (pure)
│   │   ├── shaders.ts         the five ShaderMaterials: sphere, marker, beam, starfield, nebula
│   │   ├── effects.ts         SceneEffects: light spheres, fleets, arks, leakage, flashes
│   │   ├── starfield.ts       the twinkling background points and the nebula shell
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
│       └── Collapsible.tsx      W5: a `.panel` that can collapse, remembered in localStorage
├── public/404.html       W5: GitHub Pages has no client routing to fall back to; see "GitHub Pages" below
├── scripts/engine.mjs    npm -> python scripts/build_web_engine.py
├── vitest.config.ts      unit tests only (tests/unit/**/*.test.ts)
└── tests/
    ├── smoke.spec.ts      engine boots, start screen renders
    ├── play.spec.ts       full playable slice (see above)
    ├── map.spec.ts        the 3D map (see above)
    ├── animation.spec.ts  W4 scene time and light spheres (see above)
    ├── layout.spec.ts     W5 responsive layout and collapsible panels (see above)
    ├── showcase.spec.ts   W5 fixture-driven animation showcase (see above)
    ├── fixtures/          threat.json, reply.json, genesis.json - scripts/make_web_fixtures.py
    └── unit/              Vitest: coords.test.ts, palette.test.ts, timeline.test.ts
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

Each system is a `Group` at the star's position and Earth is `StarMap.earthGroup`, so the
animated layer only ever needs a name to find a point in space; `update()` diffs by name, so
objects hung off those groups survive a state change. The default camera sits 35 degrees above
the plane of the rings (W3 looked at it almost edge-on) and star sprites are 1.6x the W3 size.

## Animation and shaders (W4)

Everything that moves is a function of two things and nothing else: the `ViewState` the engine
produced, and the events of the last `perform()`. There is no game logic in the front-end - the
launch generation of a fleet, for instance, is worked back from the engine's own `arrival_gen`,
`source_distance` and `attack_type`, and every constant used to do that is the game's own
(25 years per generation, 0.1c / 0.175c / 0.12c fleets, 0.12c arks, light speed for signals).

**Scene time.** `src/scene/timeline.ts` is pure arithmetic over one variable: `t`, a continuous
generation number. A state update does not snap the map to the new generation - `t` glides from
the old one to the new one over 1.5 s with a cubic ease-in-out, and every radius and position
below is read off `t`. While it glides (or a flash plays, or a fleet at `eta <= 2` pulses, or
the camera flies) the loop renders every frame; the rest of the time the map is asleep and
issues no draw calls, which is also why the background twinkle holds still on an idle page.

**Light spheres.** Each of the last three `messages_sent` per system is a translucent shell
centred on Earth with radius `min(distance, 25 * (t - generation))` LY, mapped through the same
logarithmic compression the stars are, so it touches its star exactly when its light gets
there; it dims as it grows and is gone 0.35 generations after arrival. A reply
(`next_response_gen`) is the same shell centred on the star, launched `distance / 25`
generations before it lands - the engine only ever states the arrival, so the launch is derived.
Outgoing is cyan, incoming warm white; both are the same shader with a different colour.

**Fleets.** Every `threats[]` entry draws a dashed straight line from its source star to Earth
plus a marker at `clamp((t - launch) / (arrival - launch), 0, 1)` along it, labelled with
`type_label` and its ETA. Red, and pulsing off the shader clock once `eta <= 2`.

**Leakage front.** One near-invisible shell on Earth at `status.broadcast_radius`, lagging
25 LY per generation behind it mid-glide. Its shader lights only the limb, so it reads as a
front rather than a ball. Once the front outgrows the scene - around Generation 4, when the
radius passes the catalogue's 51 LY - the sphere gives way to a faint ring pinned to the rim:
everybody in the frame can hear us.

**Event flashes.** `system_discovered` fades the new star up out of the fog over a second with
a bloom; `response_received` pulses the star and then flashes Earth; `attack_resolved` and
`info_attack` flash Earth red; `attack_warning` draws the new fleet's line in from the source;
`genesis` blooms green on the target, and `genesis.worlds[]` keeps an ark trail and, from
`evolution_stage >= 1`, a colony glow; `wow` fires a three-second beam towards Sagittarius;
`victory` is a slow golden pulse on Earth. All of them are fire-and-forget and dispose
themselves.

**Background.** A shader starfield (sparse points, per-point size and twinkle phase) over a
two-octave value-noise nebula on a back-facing shell, dark enough that its brightest patch is
an order of magnitude under a star's core. The "dark forest" is the absence of anything else:
the engine only lists systems it has resolved, so an unexplored direction is simply black. A
fog sprite lifting around discovered systems was tried and dropped - it washed out exactly the
dim `knowledge = 0` stars the player needs to be able to pick out.

**Budget.** Every sphere in the scene shares one shader program (three.js caches them by
source), as does every marker; geometries are shared too. At most 3 message spheres per system
and 36 in total, 12 fleets, 8 arks, 20 flashes - the animated layer stays well under 150
objects. `devicePixelRatio` is capped at 2 and all time comes from one `THREE.Clock`.

**"Effects: full / reduced".** The toolbar button drops the nebula and every flash (the
state-driven spheres, fleets and leakage front stay: they are information, not decoration). It
is remembered in `localStorage` under `los.reduceEffects`, and the map turns it on by itself if
frame time stays above 33 ms for two seconds, with a toast saying so.

**The debug hook.** In a dev build, and in any build opened with `?debug=1` in the URL,
`StarMap` publishes `window.__losMap`: `sceneTime()`, `targetGeneration()`, `animating()`,
`samples()` (the scene times of the current glide), `spheres()`, `fleets()`, `leakageLy()`,
`flashes()`, `objectCount()`, `frameMs()` and `reduced()`. The URL flag exists because
Playwright runs against `vite preview`, i.e. a production build. It is read-only: nothing in
the scene can be driven through it.

## Polish and release (W5)

**Responsive layout.** `styles.css`'s `.main-layout` is a three-column grid at >= 1000px (it
just narrows its gutters below 1200px). Below 1000px it drops to one column and CSS `order`
reflows the three `.main-column`s to map, then status/actions, then the journal - the DOM stays
in its original order, so nothing changes for a screen reader. `.star-map-viewport` switches
from a fixed `60vh` to `aspect-ratio: 4 / 3` with a `320px` floor, so it stays a sane block
instead of a sliver at 800px wide.

**Collapsible panels.** `ui/Collapsible.tsx` wraps `StatusPanel`, `ActionsPanel`,
`ThreatsPanel` and `EventLog`: a header button toggles the body and remembers the choice per
panel in `localStorage` (`los.panelOpen.<id>`), read back on the next mount. Most useful once
the layout stacks, but it works at any width.

**Keyboard.** Console parity end to end: 1-5 the core actions, 6 the menu, 7+ situational
actions in the order `state.actions` lists them (`ui/ActionsPanel.tsx`'s `assignKeys`), `v` the
dossier of the map's selected system or a picker if nothing is selected, `s` a quicksave to the
fixed `"quicksave"` slot (overwritten each time, like the autosave - not a new save per press),
`h` / `?` help, `Escape` closes whichever dialog/modal is on top (dialog, then a big-event
modal, then the summary, then help) and only clears the map selection once nothing else is
open; the doctrine choice is deliberately not on that list; it has no cancel path in the engine
either. Every action button shows its hotkey. All of it is skipped while a text input or
textarea has focus (`MainScreen.tsx`'s `isTyping()`).

**Final report.** `web_api.py`'s `summary` action only puts the score and its breakdown in
`data`; the rest (timeline, contacts, hostile encounters, swan songs, Genesis, the WOW!
outcome, achievements) lives solely in `build_summary()`'s text. `SummaryModal` renders the
breakdown as a table and keeps the full text below it in a `<pre>`, plus "Export save" and
"New game" buttons. The in-game menu (`MenuModal`) adds an **Achievements** section
(`state.achievements`) and a **Statistics** grid (`state.stats`), both already in
`docs/reference/web_contract.md`'s `ViewState` and unused by the UI until now.

**Help.** `HelpModal` still shows the engine's own `HELP_TEXT`, with a short web-specific
section appended below it: mouse controls (rotate/zoom/pan, click to select), the key list
above, the "Effects" toggle, and a reminder that saves live in this browser and "Export save"
is the way to keep them.

**Offline cache.** A hand-written service worker (no plugin) - `vite.config.ts`'s
`serviceWorker()` plugin runs in a `closeBundle` hook after `vite build` writes `dist/`, walks
the finished output (the hashed JS/CSS, `engine.zip`, the Pyodide runtime, `index.html`),
hashes every one of those files' *name and contents* into a version, writes
`dist/version.json`, and generates `dist/sw.js`: cache-first for exactly those precached files,
cleans up any `los-cache-*` that is not the current version on activate, and never touches
anything else - saves are in `localStorage`, not behind a fetchable URL, so there is nothing
there for a service worker to catch. `main.tsx` registers it only when `import.meta.env.PROD`
and `"serviceWorker" in navigator` are both true.

The contents have to be in the hash: `engine.zip`, `index.html`, `404.html` and the Pyodide
runtime all keep the same path across builds, so hashing the file list alone left an edited
engine sharing a cache name with the old one and returning players stuck on the stale copy.
The worker also precaches the scope root (`./`) alongside `index.html` and answers every
navigation to either URL from those two entries, so an offline reload of the bookmarked
directory URL is served from the cache instead of falling through to a dead network.

**GitHub Pages.** `.github/workflows/web.yml` builds (`npm ci`, `npm run build`, `npm run
unit`) and deploys `web/dist` on every push to `main` (and by hand, via `workflow_dispatch`).
Pages serves a project site under `/legacy-of-stars-2/`, not the domain root, so the workflow sets
`VITE_BASE=/legacy-of-stars-2/`; `vite.config.ts`'s `base` reads `VITE_BASE` with a `/` default
for local dev/preview, and everything that fetches `engine.zip` or the Pyodide runtime already
went through `import.meta.env.BASE_URL` since W1 (`bridge.ts`, `worker.ts`). `public/404.html`
exists only because GitHub Pages serves it for any URL it does not recognise; the game has no
client-side routing to fall back to, so it just bounces back to the app's own base path.

**Showcase fixtures.** `scripts/make_web_fixtures.py` (repository root) uses the Python engine
directly - `ContactProgram(seed=1, offline=True)`, then `send_message`/`genesis.seed_world`/
`advance_generation` - to build four saves already in situations a seed-1 playthrough rarely
reaches in a test-sized number of generations: `threat.json` (a hostile fleet inbound, ETA >= 3
generations), `reply.json` (a reply already in flight), `genesis.json` (a landed Genesis
colony) and `gameover.json` (a defunded, finished run). `tests/showcase.spec.ts` loads each one
through the real Load screen ("Import JSON file") and checks the matching effect reached
`window.__losMap` - `arks()` was added to the debug hook for this (`spheres()`/`fleets()`
already existed from W4); `gameover.json` instead checks that the final report opens by itself
and that the action list is replaced by the Game over banner.

## Legibility round (post-W5)

Five things playtesters could not see, now on screen. None of them changes a rule; every number
and line comes from the engine.

- **Active effects.** `StatusPanel` ends with an "Active effects" list (`state.active_effects`,
  new in `docs/reference/web_contract.md` §6): the 1977 silence, each defensive/warning/survival/leakage/
  propulsion technology in force, the integration penalty or bonus, and one line per doctrine.
  "None yet" until something applies. The doctrines paragraph that used to sit there is gone -
  the list already names them. An **Achievements** count joins the status rows (the names stay
  in the Menu).
- **Resources where they are spent.** The Actions panel header carries `AP n/m`; the system and
  message dialogs repeat it, and the tech dialog leads with `Research Points: N (+X/gen)` and
  marks anything the player cannot currently afford "needs approx. N more RP". The hint is
  display only and never disables a button: the real cost moves with the director's science
  skill and any swan-song discount, so only the engine can refuse.
- **The whole transmitted message.** After the 1977 reply the result panel shows the full text
  Earth sent (`data.message_full`) in a scrolling block under the console-style summary, and the
  composer counts characters live against the engine's 500-character limit.
- **The idle briefing.** Two generations with no player action and the engine emits a
  `briefing` event (`data: {idle_generations}`) - the advisor's rule-based read of the board,
  free, needing neither the AI Strategic Advisor technology nor the manual consultation. It
  arrives as a big-kind modal ("Got it") and stays in the journal under a clipboard icon.

## What's covered vs. intentionally missing

Covered: the full action set (`send_message`, `focus_research`, `public_outreach`,
`research_tech` + doctrine follow-up, `advance_generation`, `defend`, `consult_advisor`,
`listen_swan_song`, `genesis_seed`, `respond_event`), the 1977 WOW! opening (custom /
director-drafted / standard reply), system dossiers, threats, the event journal with big-kind
modals, save/load (manual, autosave, export/import JSON, console-compatible), Help (with a
web-specific section) and the final report/score, achievements and statistics; a responsive,
collapsible-panel layout; full keyboard parity with the console; an offline service-worker
cache; and a GitHub Pages deployment workflow.

Missing by design (not part of W2-W5): LLM text in
the browser (`urllib` does not work in Pyodide - the engine falls back to its offline content
bank, same as the console with `LOS_OFFLINE=1`); mobile-specific input (touch works through
OrbitControls' default gestures, but nothing was tuned beyond "doesn't break on a tablet", per
the plan's scope).

Three small contract gaps were found while building the UI and have since been fixed on the
Python side: `help` now works with no game in progress (the Start screen's Help link calls it
directly, no throwaway session needed); `technologies.available[]` carries `year_context`,
shown in the tech dialog under each description; and `genesis.targets[]` is the exact
sterile/habitable/unseeded/non-WOW!-source system list the Genesis picker shows, in order.
`swan_song_targets[]` is the same idea for the deep scan: the systems already studied to
20 % and known to be extinct, so neither the picker nor the action's label can say where a
civilization died, or how many archives are out there.

## Measurements (Windows 11, Node 24.18, Chromium via Playwright)

| | |
|---|---|
| `engine.zip` | ~99 KiB (25 files) |
| Pyodide runtime | ~13 MiB raw / ~6 MiB gzipped |
| `dist/` (W4 build) | ~14 MiB. `index-*.js` ~67 KiB / ~21 KiB gzipped; `StarMap-*.js` ~590 KiB / ~149 KiB gzipped, split out because three.js dominates it and nothing before the main screen needs it (`MapPanel` imports it dynamically; the start screen prefetches it) |
| Time to `ready` | ~1 s (worker start -> engine imported, uncached local server) |

Well inside the plan's 4-second budget.
