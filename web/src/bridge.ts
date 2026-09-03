/**
 * `EngineBridge` - the main thread's view of the Pyodide worker.
 *
 * Every call is a promise; nothing here blocks the UI. The worker answers with the raw
 * JSON string the Python facade produced and this file is the only place that parses it,
 * so the rest of the front-end sees typed `ViewState` / `PerformResult` values and never
 * a Pyodide proxy (plan 3, "boundary rule").
 */
import type {
  ActionId,
  ActionParams,
  EngineMethod,
  PerformResult,
  PerformResultOf,
  ProgressMessage,
  ReadyMessage,
  ViewState,
  WorkerMessage,
  WorkerResponse,
} from "./types";

/** Where `engine.zip` and `pyodide/` are served from; honours Vite's `base`. */
function baseUrl(): string {
  return new URL(import.meta.env.BASE_URL, location.href).href;
}

export interface BridgeOptions {
  onProgress?: (progress: ProgressMessage) => void;
}

/**
 * How long one engine call may take before the bridge stops waiting for it. Nothing in the
 * worker can time itself out - Pyodide runs Python synchronously, so a wedged call never
 * posts anything back - and a pending promise that never settles leaves the store `busy`
 * forever, which disables every button and hotkey with no way out but a reload. These are
 * watchdogs, not budgets: a healthy call is orders of magnitude under them.
 */
const CALL_TIMEOUT_MS = 30_000;
/** `new_game` builds the star catalogue and `load` rebuilds a whole program from JSON. */
const SLOW_CALL_TIMEOUT_MS = 60_000;
const SLOW_METHODS: ReadonlySet<EngineMethod> = new Set<EngineMethod>(["new_game", "load"]);

interface PendingCall {
  method: EngineMethod;
  resolve: (value: string) => void;
  reject: (error: Error) => void;
  timer: ReturnType<typeof setTimeout>;
}

export class EngineBridge {
  /** Resolves when the engine can take calls; rejects if startup failed. */
  readonly ready: Promise<ReadyMessage>;

  /** Called for every startup progress message (stage, 0-100). */
  onProgress: ((progress: ProgressMessage) => void) | undefined;

  private readonly worker: Worker;
  private readonly pending = new Map<number, PendingCall>();
  private nextId = 1;
  /** Set by `terminate()`: the worker is gone, so no new call can ever be answered. */
  private disposed = false;

  constructor(options: BridgeOptions = {}) {
    this.onProgress = options.onProgress;
    this.worker = new Worker(new URL("./worker.ts", import.meta.url), {
      type: "module",
      name: "los-engine",
    });

    this.ready = new Promise<ReadyMessage>((resolve, reject) => {
      this.worker.addEventListener("message", (event: MessageEvent<WorkerMessage>) => {
        const message = event.data;
        if ("type" in message) {
          if (message.type === "progress") this.onProgress?.(message);
          else if (message.type === "ready") resolve(message);
          else if (message.type === "failed") reject(new Error(`${message.stage}: ${message.error}`));
          return;
        }
        this.settle(message);
      });
      this.worker.addEventListener("error", (event: ErrorEvent) => {
        const error = new Error(event.message || "engine worker failed");
        reject(error);
        this.rejectAll(error);
      });
      // A structured-clone failure on the way in: the message is lost, so whatever call it
      // was answering will never settle on its own.
      this.worker.addEventListener("messageerror", () => {
        const error = new Error("the engine sent a message the browser could not read");
        reject(error);
        this.rejectAll(error);
      });
    });

    this.worker.postMessage({ type: "init", baseUrl: baseUrl() });
  }

  /* ------------------------------------------------------------ engine methods */

  /** Start a fresh program (optionally with a fixed seed) and return its view state. */
  async newGame(seed?: number): Promise<ViewState> {
    return this.json<ViewState>(await this.send("new_game", seed === undefined ? "" : String(seed)));
  }

  /** Restore a save produced by `save()` (or by the console build). */
  async load(saveJson: string): Promise<ViewState> {
    return this.json<ViewState>(await this.send("load", saveJson));
  }

  /** The save file for this session, as JSON text - store it, do not parse it. */
  save(): Promise<string> {
    return this.send("save");
  }

  /** The current view state: the single source of truth for the UI. */
  async state(): Promise<ViewState> {
    return this.json<ViewState>(await this.send("state"));
  }

  /**
   * Run one action. The engine refusing it is not an error here: the result comes back
   * with `ok: false` and the engine's message.
   */
  async perform<A extends ActionId>(action: A, params?: ActionParams[A]): Promise<PerformResultOf<A>> {
    const text = await this.send("perform", action, JSON.stringify(params ?? {}));
    return this.json<PerformResult>(text) as PerformResultOf<A>;
  }

  /** Stop the worker; the session is gone with it. */
  terminate(): void {
    this.disposed = true;
    this.worker.terminate();
    this.rejectAll(new Error("engine terminated"));
  }

  /* ------------------------------------------------------------ plumbing */

  private send(method: EngineMethod, ...args: string[]): Promise<string> {
    if (this.disposed) {
      return Promise.reject(new Error("the engine has been shut down; reload the page to start again"));
    }
    const id = this.nextId++;
    return new Promise<string>((resolve, reject) => {
      const limit = SLOW_METHODS.has(method) ? SLOW_CALL_TIMEOUT_MS : CALL_TIMEOUT_MS;
      const timer = setTimeout(() => {
        // `delete` returning false means `settle` already took this one; the timer just lost
        // the race and must not reject an already-resolved promise.
        if (!this.pending.delete(id)) return;
        reject(
          new Error(
            `the engine did not answer "${method}" within ${Math.round(limit / 1000)}s; ` +
              "reload the page to restart it",
          ),
        );
      }, limit);
      this.pending.set(id, { method, resolve, reject, timer });
      this.worker.postMessage({ id, method, args });
    });
  }

  private settle(message: WorkerResponse): void {
    const entry = this.pending.get(message.id);
    if (!entry) return;
    this.pending.delete(message.id);
    clearTimeout(entry.timer);
    if (message.error !== undefined) entry.reject(new Error(message.error));
    else entry.resolve(message.result ?? "");
  }

  /** Fails every call still waiting: the worker died, or is no longer trusted to answer. */
  private rejectAll(error: Error): void {
    const outstanding = [...this.pending.values()];
    this.pending.clear();
    for (const entry of outstanding) {
      clearTimeout(entry.timer);
      entry.reject(error);
    }
  }

  private json<T>(text: string): T {
    try {
      return JSON.parse(text) as T;
    } catch (error: unknown) {
      const detail = error instanceof Error ? error.message : String(error);
      throw new Error(`the engine returned text that is not JSON: ${detail}`);
    }
  }
}
