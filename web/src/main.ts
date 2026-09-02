/**
 * W1 smoke page: prove that the Python engine runs in the browser and answers the bridge.
 *
 * No game UI here - that is W2 (Preact HUD) and W3 (Three.js map). This page only starts a
 * game, advances ten generations, dumps a view-state summary and reports what startup cost.
 */
import { EngineBridge } from "./bridge";
import type { GameEvent, ViewState } from "./types";

const app = document.getElementById("app") as HTMLElement;
const bar = document.getElementById("bar") as HTMLProgressElement;
const stage = document.getElementById("stage") as HTMLElement;
const boot = document.getElementById("boot") as HTMLElement;
const controls = document.getElementById("controls") as HTMLElement;
const meta = document.getElementById("meta") as HTMLElement;
const out = document.getElementById("out") as HTMLElement;
const buttons = {
  newGame: document.getElementById("new-game") as HTMLButtonElement,
  advance: document.getElementById("advance") as HTMLButtonElement,
  save: document.getElementById("save") as HTMLButtonElement,
};

let lastEvents: GameEvent[] = [];

const kib = (bytes: number): string => `${(bytes / 1024).toFixed(1)} KiB`;
const mib = (bytes: number): string => `${(bytes / 1024 / 1024).toFixed(2)} MiB`;

function summarize(state: ViewState): string {
  const s = state.status;
  const lines = [
    `generation      ${state.generation}`,
    `year            ${state.year}`,
    `director        ${state.director.name} [${state.director.traits.join(", ")}]`,
    `action points   ${s.action_points}/${s.max_action_points}`,
    `funding         ${s.funding.toFixed(1)}`,
    `public support  ${s.public_support.toFixed(1)}`,
    `research points ${s.research_points} (+${s.passive_rp.toFixed(1)}/gen)`,
    `tech level      ${s.tech_level}`,
    `systems known   ${state.systems.length} of ${state.catalog.total} catalogued`,
    `threats         ${state.threats.length}`,
    `wow decision    ${state.wow.decided ? (state.wow.replied ? "replied" : "silent") : "open"}`,
    `game over       ${state.game_over ? state.game_over_reason : "no"}`,
    "",
    "actions:",
    ...state.actions.map((a) => `  ${a.id.padEnd(20)} ${a.cost.padEnd(14)} needs: ${a.needs.join(", ") || "-"}`),
  ];

  if (lastEvents.length) {
    lines.push("", `last events (${lastEvents.length}):`);
    for (const event of lastEvents.slice(-12)) {
      const text = event.text.replace(/\s+/g, " ").trim().slice(0, 160);
      lines.push(`  [gen ${event.generation}] ${event.kind}: ${text}`);
    }
  }
  return lines.join("\n");
}

function show(state: ViewState): void {
  out.textContent = summarize(state);
  app.dataset["generation"] = String(state.generation);
}

function fail(error: unknown): void {
  const text = error instanceof Error ? error.message : String(error);
  out.textContent = `ERROR: ${text}`;
  out.classList.add("error");
  console.error(error);
}

/** Serialises the buttons: the engine takes one call at a time and errors must be visible. */
function guard(button: HTMLButtonElement, task: () => Promise<void>): void {
  button.addEventListener("click", () => {
    const all = Object.values(buttons);
    all.forEach((b) => (b.disabled = true));
    task()
      .catch(fail)
      .finally(() => all.forEach((b) => (b.disabled = false)));
  });
}

const engine = new EngineBridge({
  onProgress: ({ stage: name, pct }) => {
    bar.value = pct;
    stage.textContent = name;
  },
});

guard(buttons.newGame, async () => {
  lastEvents = [];
  show(await engine.newGame(1));
});

guard(buttons.advance, async () => {
  let state: ViewState | null = null;
  lastEvents = [];
  for (let i = 0; i < 10; i += 1) {
    // A philosophical crisis blocks advance_generation; the smoke run answers it with the
    // first option so that ten generations really pass (web_contract.md 3).
    if (state?.pending_event) {
      const answered = await engine.perform("respond_event", { choice: 0 });
      lastEvents.push(...answered.events);
      state = answered.state;
    }
    const result = await engine.perform("advance_generation");
    lastEvents.push(...result.events);
    state = result.state;
    if (!result.ok) {
      console.warn("advance_generation refused:", result.message);
      break;
    }
    if (state?.game_over) break;
  }
  show(state ?? (await engine.state()));
});

guard(buttons.save, async () => {
  const text = await engine.save();
  console.log("save file:", text);
  meta.textContent = `${meta.textContent} | save: ${kib(new Blob([text]).size)} (full text in the console)`;
});

engine.ready
  .then((ready) => {
    boot.hidden = true;
    controls.hidden = false;
    const assets = ready.assets
      .map((a) => `${a.name} ${mib(a.transferBytes || a.encodedBytes)}`)
      .join(", ");
    meta.textContent =
      `ready in ${ready.startupMs} ms | Python ${ready.pythonVersion} | Pyodide ${ready.pyodideVersion}` +
      ` | engine.zip ${kib(ready.engineZipBytes)}` +
      (assets ? ` | downloaded: ${assets}` : "");
    // The marker the Playwright smoke test waits for.
    app.dataset["ready"] = "true";
    app.dataset["startupMs"] = String(ready.startupMs);
    console.log("[ready]", JSON.stringify(ready));
  })
  .catch((error: unknown) => {
    boot.hidden = true;
    app.dataset["ready"] = "failed";
    fail(error);
  });
