/**
 * Entry point: creates the one `Store` (and with it the one `EngineBridge`/Pyodide worker)
 * and mounts the Preact app. `#app`'s `data-ready`/`data-phase`/`data-generation` attributes
 * are maintained here, outside the Preact tree, purely as Playwright hooks (tests/*.spec.ts).
 */
import { render } from "preact";
import { App } from "./app";
import { Store } from "./store";

const found = document.getElementById("app");
if (!found) throw new Error("#app element is missing from index.html");
const root: HTMLElement = found;

const store = new Store();

function updateTestHooks(): void {
  const state = store.state;
  root.dataset["phase"] = state.phase;
  root.dataset["ready"] = state.phase === "boot" ? (state.bootError ? "failed" : "false") : "true";
  if (state.view) {
    root.dataset["generation"] = String(state.view.generation);
    // How many stars the map must be drawing: tests/map.spec.ts compares it to the label count.
    root.dataset["systems"] = String(state.view.systems.length);
  }
}
store.subscribe(updateTestHooks);
updateTestHooks();

render(<App store={store} />, root);
