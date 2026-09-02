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

export class EngineBridge {
  /** Resolves when the engine can take calls; rejects if startup failed. */
  readonly ready: Promise<ReadyMessage>;

  /** Called for every startup progress message (stage, 0-100). */
  onProgress: ((progress: ProgressMessage) => void) | undefined;

  private readonly worker: Worker;
  private readonly pending = new Map<number, { resolve: (v: string) => void; reject: (e: Error) => void }>();
  private nextId = 1;

  constructor(options: BridgeOptions = {}) {
    this.onProgress = options.onProgress;
    this.worker = new Worker(new URL("./worker.ts", import.meta.url), {
      type: "module",
      name: "los-engine",
    });

    this.ready = new Promise<ReadyMessage>((resolve, reject) => {
      this.worker.onmessage = (event: MessageEvent<WorkerMessage>) => {
        const message = event.data;
        if ("type" in message) {
          if (message.type === "progress") this.onProgress?.(message);
          else if (message.type === "ready") resolve(message);
          else if (message.type === "failed") reject(new Error(`${message.stage}: ${message.error}`));
          return;
        }
        this.settle(message);
      };
      this.worker.onerror = (event: ErrorEvent) => {
        const error = new Error(event.message || "engine worker failed");
        reject(error);
        for (const [id, entry] of this.pending) {
          entry.reject(error);
          this.pending.delete(id);
        }
      };
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
    this.worker.terminate();
    for (const [id, entry] of this.pending) {
      entry.reject(new Error("engine terminated"));
      this.pending.delete(id);
    }
  }

  /* ------------------------------------------------------------ plumbing */

  private send(method: EngineMethod, ...args: string[]): Promise<string> {
    const id = this.nextId++;
    return new Promise<string>((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.worker.postMessage({ id, method, args });
    });
  }

  private settle(message: WorkerResponse): void {
    const entry = this.pending.get(message.id);
    if (!entry) return;
    this.pending.delete(message.id);
    if (message.error !== undefined) entry.reject(new Error(message.error));
    else entry.resolve(message.result ?? "");
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
