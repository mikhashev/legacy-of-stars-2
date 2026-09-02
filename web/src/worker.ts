/**
 * The Pyodide worker: the Python engine lives here, the main thread never blocks.
 *
 * Startup: load the Pyodide runtime, fetch `engine.zip` (built by
 * `scripts/build_web_engine.py`), unpack it into `/engine`, put that on `sys.path`
 * and create the one `GameSession` the whole session uses.
 *
 * Why the runtime is loaded from our own origin instead of the Pyodide CDN: the game
 * is offline-first, and `vite.config.ts` copies the runtime out of `node_modules` into
 * `public/pyodide/`. It is loaded with a plain dynamic `import()` of a URL rather than
 * `import "pyodide"` so that the bundler never touches it - `pyodide.mjs` reaches for
 * `node:fs` and friends on Node, and the 9.6 MB `.wasm` has no business in a bundle.
 *
 * Boundary rule (plan 3): only JSON strings cross into Python. `los_call` below takes
 * string arguments and returns a string, so no Pyodide proxy is ever handed out.
 */
import type { AssetSize, ReadyMessage, WorkerRequest } from "./types";

type LoadPyodide = typeof import("pyodide").loadPyodide;
type Pyodide = Awaited<ReturnType<LoadPyodide>>;
/** The Python dispatcher, seen from JavaScript: strings in, string out. */
type PyCall = (method: string, a: string, b: string) => string;

/** Files whose transfer size the ready message reports. */
const MEASURED_ASSETS = ["pyodide.asm.wasm", "python_stdlib.zip", "pyodide.asm.mjs", "engine.zip"];

const BOOTSTRAP = `
import json, os, sys

if "/engine" not in sys.path:
    sys.path.insert(0, "/engine")
os.environ["LOS_OFFLINE"] = "1"   # no urllib in the browser: the engine uses its content bank

from src.web_api import GameSession

_session = GameSession(offline=True)


def los_call(method, a="", b=""):
    """The only entry point the worker calls. Strings in, JSON string out."""
    if method == "new_game":
        return _session.new_game(int(a) if a else None)
    if method == "load":
        return _session.load(a)
    if method == "save":
        return _session.save()
    if method == "state":
        return _session.state()
    if method == "perform":
        return _session.perform(a, b or "{}")
    raise ValueError("unknown method %r" % (method,))


json.dumps({"ok": True})   # fail here rather than in the browser if json is broken
sys.version.split()[0]
`;

let call: PyCall | null = null;
let startup: Promise<void> | null = null;

function progress(stage: string, pct: number): void {
  self.postMessage({ type: "progress", stage, pct });
}

/** Resource-timing sizes for the big downloads, so W1 can report what the player pays. */
function assetSizes(): AssetSize[] {
  const entries = performance.getEntriesByType("resource") as PerformanceResourceTiming[];
  const sizes: AssetSize[] = [];
  for (const entry of entries) {
    const name = entry.name.split("/").pop() ?? entry.name;
    if (!MEASURED_ASSETS.includes(name)) continue;
    sizes.push({
      name,
      transferBytes: Math.round(entry.transferSize),
      encodedBytes: Math.round(entry.decodedBodySize || entry.encodedBodySize),
    });
  }
  return sizes;
}

async function boot(baseUrl: string): Promise<void> {
  const started = performance.now();

  progress("runtime", 5);
  const runtimeUrl = new URL("pyodide/pyodide.mjs", baseUrl).href;
  const { loadPyodide } = (await import(/* @vite-ignore */ runtimeUrl)) as {
    loadPyodide: LoadPyodide;
  };

  progress("python", 15);
  const pyodide: Pyodide = await loadPyodide({
    indexURL: new URL("pyodide/", baseUrl).href,
    stdout: (line: string) => console.log("[py]", line),
    stderr: (line: string) => console.warn("[py]", line),
  });

  progress("engine", 60);
  const engineUrl = new URL("engine.zip", baseUrl).href;
  const response = await fetch(engineUrl);
  if (!response.ok) {
    throw new Error(`engine.zip: ${response.status} ${response.statusText} (run 'npm run engine')`);
  }
  const archive = await response.arrayBuffer();

  progress("unpack", 80);
  pyodide.FS.mkdirTree("/engine");
  pyodide.unpackArchive(archive, "zip", { extractDir: "/engine" });

  progress("session", 90);
  const pythonVersion = String(pyodide.runPython(BOOTSTRAP));
  const dispatcher = pyodide.globals.get("los_call") as unknown as PyCall;
  if (typeof dispatcher !== "function") throw new Error("los_call was not defined by the bootstrap");
  call = dispatcher;

  const ready: ReadyMessage = {
    type: "ready",
    startupMs: Math.round(performance.now() - started),
    pythonVersion,
    pyodideVersion: pyodide.version,
    engineZipBytes: archive.byteLength,
    assets: assetSizes(),
  };
  progress("ready", 100);
  self.postMessage(ready);
}

function describe(error: unknown): string {
  if (error instanceof Error) return error.message;
  return String(error);
}

self.onmessage = (event: MessageEvent) => {
  const data = event.data as WorkerRequest | { type: "init"; baseUrl: string };

  if ("type" in data && data.type === "init") {
    if (startup) return;
    startup = boot(data.baseUrl).catch((error: unknown) => {
      self.postMessage({ type: "failed", stage: "startup", error: describe(error) });
    });
    return;
  }

  const request = data as WorkerRequest;
  void (async () => {
    try {
      if (startup) await startup;
      if (!call) throw new Error("the Python engine is not ready");
      // Strings only: `args` are already JSON strings or plain scalars rendered as text.
      const [a = "", b = ""] = request.args ?? [];
      const result = call(request.method, a, b);
      self.postMessage({ id: request.id, result });
    } catch (error: unknown) {
      self.postMessage({ id: request.id, error: describe(error) });
    }
  })();
};
