/**
 * The front-end's application state: one `Store` instance holds the current `ViewState`,
 * the event journal, the message box, the toast and whatever dialog/modal is open. UI
 * components never call the engine directly - they call a `Store` method, which calls
 * `EngineBridge`, applies the result and notifies subscribers. `useStore` is the Preact
 * hook that reads it.
 *
 * Nothing here invents game rules: every value shown comes from a `ViewState` or a
 * `PerformResult` the engine produced (bridge.ts / docs/web_contract.md).
 */
import { useEffect, useState } from "preact/hooks";
import { EngineBridge } from "./bridge";
import { withLabel, saveNew, saveToSlot } from "./saves";
import type { ScaleMode } from "./scene/coords";
import type {
  ActionId,
  ActionParams,
  ActionSpec,
  DefenseKind,
  DoctrineNeeds,
  GameEvent,
  PerformResult,
  PerformResultOf,
  ProgressMessage,
  ViewState,
} from "./types";
import { MODAL_EVENT_KINDS } from "./types";

export type Phase = "boot" | "start" | "opening" | "main";

/** One parameter dialog at a time; `spec` carries the action id and cost/label back to the UI. */
export type Dialog =
  | { kind: "system"; spec: ActionSpec }
  | { kind: "text"; spec: ActionSpec; system: string }
  | { kind: "tech"; spec: ActionSpec }
  | { kind: "threat"; spec: ActionSpec }
  | { kind: "defense"; spec: ActionSpec; threat: number }
  | { kind: "event" }
  | { kind: "dossier"; system: string }
  | { kind: "dossier-picker" }
  | { kind: "menu" };

const JOURNAL_LIMIT = 500;

export interface UIState {
  phase: Phase;
  bootProgress: ProgressMessage | null;
  bootError: string | null;
  view: ViewState | null;
  busy: boolean;
  message: string;
  events: GameEvent[];
  modalQueue: GameEvent[];
  modalEvent: GameEvent | null;
  dialog: Dialog | null;
  pendingDoctrine: DoctrineNeeds | null;
  toast: string | null;
  wowResult: PerformResult | null;
  wowComposerOpen: boolean;
  showHelp: boolean;
  summaryResult: PerformResult | null;
  /** The star picked on the map: the default system for the next system-needing action. */
  selectedSystem: string | null;
  /** Which radial scale the map draws in; "compressed" is `k * ln(1 + d/d0)`. */
  mapScale: ScaleMode;
  /** The systems list, which W3 moved off the main column into an overlay. */
  showSystemList: boolean;
}

function describe(error: unknown): string {
  if (error instanceof Error) return error.message;
  return String(error);
}

const initialState: UIState = {
  phase: "boot",
  bootProgress: null,
  bootError: null,
  view: null,
  busy: false,
  message: "",
  events: [],
  modalQueue: [],
  modalEvent: null,
  dialog: null,
  pendingDoctrine: null,
  toast: null,
  wowResult: null,
  wowComposerOpen: false,
  showHelp: false,
  summaryResult: null,
  selectedSystem: null,
  mapScale: "compressed",
  showSystemList: false,
};

export class Store {
  state: UIState = initialState;
  readonly bridge: EngineBridge;

  private readonly listeners = new Set<() => void>();

  constructor() {
    this.bridge = new EngineBridge({ onProgress: (bootProgress) => this.patch({ bootProgress }) });
    this.bridge.ready
      .then(() => this.patch({ phase: "start" }))
      .catch((error: unknown) => this.patch({ bootError: describe(error) }));
  }

  subscribe(listener: () => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private patch(partial: Partial<UIState>): void {
    this.state = { ...this.state, ...partial };
    for (const listener of this.listeners) listener();
  }

  showToast(text: string): void {
    this.patch({ toast: text });
  }

  dismissToast(): void {
    this.patch({ toast: null });
  }

  /* ------------------------------------------------------------ engine calls */

  async newGame(seed?: number): Promise<void> {
    this.patch({ busy: true });
    try {
      const view = await this.bridge.newGame(seed);
      this.enterGame(view);
    } catch (error) {
      this.showToast(`Could not start a new game: ${describe(error)}`);
    } finally {
      this.patch({ busy: false });
    }
  }

  async loadFromText(text: string): Promise<void> {
    this.patch({ busy: true });
    try {
      const view = await this.bridge.load(text);
      this.enterGame(view);
    } catch (error) {
      this.showToast(`Could not load save: ${describe(error)}`);
    } finally {
      this.patch({ busy: false });
    }
  }

  private enterGame(view: ViewState): void {
    this.patch({
      view,
      phase: view.wow.decided ? "main" : "opening",
      events: [],
      modalQueue: [],
      modalEvent: null,
      dialog: null,
      pendingDoctrine: null,
      wowResult: null,
      wowComposerOpen: false,
      message: "",
      showHelp: false,
      summaryResult: null,
      selectedSystem: null,
      showSystemList: false,
    });
  }

  backToStart(): void {
    this.patch({ ...initialState, phase: "start" });
  }

  /** Runs a bridge.perform() promise, applying its result and surfacing refusals as a toast. */
  private async runPerform(promise: Promise<PerformResult>): Promise<PerformResult> {
    this.patch({ busy: true });
    try {
      const result = await promise;
      this.applyResult(result);
      if (!result.ok) this.showToast(result.message);
      return result;
    } catch (error) {
      this.showToast(describe(error));
      throw error;
    } finally {
      this.patch({ busy: false });
    }
  }

  async perform<A extends ActionId>(action: A, params?: ActionParams[A]): Promise<PerformResultOf<A>> {
    return this.runPerform(this.bridge.perform(action, params)) as Promise<PerformResultOf<A>>;
  }

  /** Same as `perform`, but for call sites (dialogs) that only know the action id at run time. */
  private performDynamic(action: ActionId, params: Record<string, unknown>): Promise<PerformResult> {
    // The dialog was opened from `state.actions`, so `action` and `params` already match what
    // the engine asked for (ViewState.actions[].needs); TypeScript just cannot see that here.
    return this.runPerform(this.bridge.perform(action, params as ActionParams[ActionId]));
  }

  private applyResult(result: PerformResult): void {
    const events = [...this.state.events, ...result.events].slice(-JOURNAL_LIMIT);
    const modalQueue = [
      ...this.state.modalQueue,
      ...result.events.filter((event) => MODAL_EVENT_KINDS.includes(event.kind)),
    ];
    // The doctrine modal blocks every other perform() call (openAction/advanceGeneration/
    // openMenu all refuse while it is set), so the only way to reach this with a pending
    // doctrine is answering it via choose_doctrine - which never itself returns `needs`.
    // Anything other than a fresh doctrine request clears it; nothing here can be stale.
    const view = result.state ?? this.state.view;
    // A selection only survives while the engine still lists that system.
    const selectedSystem =
      this.state.selectedSystem && view?.systems.some((s) => s.name === this.state.selectedSystem)
        ? this.state.selectedSystem
        : null;
    this.patch({
      view,
      message: result.message,
      events,
      modalQueue,
      pendingDoctrine: result.needs && result.needs.kind === "doctrine" ? result.needs : null,
      selectedSystem,
    });
    this.popModal();
  }

  private popModal(): void {
    if (this.state.modalEvent || this.state.modalQueue.length === 0) return;
    const [next, ...rest] = this.state.modalQueue;
    this.patch({ modalEvent: next ?? null, modalQueue: rest });
  }

  dismissModal(): void {
    this.patch({ modalEvent: null });
    this.popModal();
  }

  /** From the `philosophical_event` modal: dismiss it and open the response dialog right away. */
  respondToPendingEventNow(): void {
    this.patch({ modalEvent: null, dialog: { kind: "event" } });
    this.popModal();
  }

  /* ------------------------------------------------------------ opening scene */

  openWowComposer(): void {
    this.patch({ wowComposerOpen: true });
  }

  closeWowComposer(): void {
    this.patch({ wowComposerOpen: false });
  }

  async composeDirectorDraft(): Promise<string> {
    const result = await this.perform("compose_director_message", {});
    return result.data.draft;
  }

  async wowReply(text: string): Promise<void> {
    const result = await this.perform("wow_reply", { text });
    this.patch({ wowComposerOpen: false, wowResult: result });
  }

  async wowSilent(): Promise<void> {
    const result = await this.perform("wow_silent", {});
    this.patch({ wowResult: result });
  }

  enterMain(): void {
    this.patch({ phase: "main", wowResult: null });
  }

  /* ------------------------------------------------------------ action dialogs */

  openAction(spec: ActionSpec): void {
    if (this.state.pendingDoctrine) {
      this.showToast("A doctrine choice is waiting for an answer first.");
      return;
    }
    if (this.state.busy) return;
    if (spec.needs.length === 0) {
      // advance_generation gets its own path so a successful advance autosaves, matching the
      // console (game_interface.py _act_advance); every other zero-parameter action just runs.
      if (spec.id === "advance_generation") void this.advanceGeneration();
      else void this.performDynamic(spec.id, {});
      return;
    }
    if (spec.needs.includes("system")) {
      this.patch({ dialog: { kind: "system", spec } });
      return;
    }
    if (spec.needs.includes("tech")) {
      this.patch({ dialog: { kind: "tech", spec } });
      return;
    }
    if (spec.needs.includes("threat")) {
      this.patch({ dialog: { kind: "threat", spec } });
      return;
    }
    if (spec.needs.includes("choice")) {
      this.patch({ dialog: { kind: "event" } });
      return;
    }
    this.showToast(`No dialog is wired up for the parameters ${spec.needs.join(", ")}.`);
  }

  closeDialog(): void {
    this.patch({ dialog: null });
  }

  pickSystem(name: string): void {
    const dialog = this.state.dialog;
    if (!dialog || dialog.kind !== "system") return;
    this.patch({ selectedSystem: name });
    if (dialog.spec.needs.includes("text")) {
      this.patch({ dialog: { kind: "text", spec: dialog.spec, system: name } });
      return;
    }
    this.patch({ dialog: null });
    void this.performDynamic(dialog.spec.id, { system: name });
  }

  submitText(text: string): void {
    const dialog = this.state.dialog;
    if (!dialog || dialog.kind !== "text") return;
    this.patch({ dialog: null });
    void this.performDynamic(dialog.spec.id, { system: dialog.system, text });
  }

  pickTech(techId: string): void {
    const dialog = this.state.dialog;
    if (!dialog || dialog.kind !== "tech") return;
    this.patch({ dialog: null });
    void this.performDynamic(dialog.spec.id, { tech: techId });
  }

  pickThreat(index: number): void {
    const dialog = this.state.dialog;
    if (!dialog || dialog.kind !== "threat") return;
    this.patch({ dialog: { kind: "defense", spec: dialog.spec, threat: index } });
  }

  pickDefense(defense: DefenseKind): void {
    const dialog = this.state.dialog;
    if (!dialog || dialog.kind !== "defense") return;
    this.patch({ dialog: null });
    void this.performDynamic(dialog.spec.id, { threat: dialog.threat, defense });
  }

  async respondEvent(choice: number): Promise<void> {
    this.patch({ dialog: null });
    await this.perform("respond_event", { choice });
  }

  async chooseDoctrine(choice: number): Promise<void> {
    const pending = this.state.pendingDoctrine;
    if (!pending) return;
    await this.perform("choose_doctrine", { tech: pending.tech_id, choice });
  }

  /* ------------------------------------------------------------ star map */

  /** Click on the map (or on a list row): the map's selection is the UI's current system. */
  selectSystem(name: string | null): void {
    if (this.state.selectedSystem === name) return;
    this.patch({ selectedSystem: name });
  }

  toggleScale(): void {
    this.patch({ mapScale: this.state.mapScale === "compressed" ? "true" : "compressed" });
  }

  toggleSystemList(open?: boolean): void {
    this.patch({ showSystemList: open ?? !this.state.showSystemList });
  }

  /**
   * Runs an action straight at one system, skipping the picker - the same path as choosing
   * that row in the picker, so `send_message` still stops at its text dialog. Used by the
   * selected-system card, where the system is already named on screen.
   */
  startActionForSystem(spec: ActionSpec, system: string): void {
    if (this.state.pendingDoctrine) {
      this.showToast("A doctrine choice is waiting for an answer first.");
      return;
    }
    if (this.state.busy) return;
    if (spec.needs.includes("text")) {
      this.patch({ dialog: { kind: "text", spec, system } });
      return;
    }
    this.patch({ dialog: null });
    void this.performDynamic(spec.id, { system });
  }

  openDossier(system: string): void {
    this.patch({ dialog: { kind: "dossier", system } });
  }

  /** The console's `v` shortcut: pick a system, then see its dossier (no engine call). */
  openDossierPicker(): void {
    if (this.state.pendingDoctrine || this.state.busy) return;
    this.patch({ dialog: { kind: "dossier-picker" } });
  }

  openMenu(): void {
    if (this.state.pendingDoctrine || this.state.busy) return;
    this.patch({ dialog: { kind: "menu" } });
  }

  toggleHelp(open: boolean): void {
    this.patch({ showHelp: open });
  }

  /** `help` works with no game in progress, so the Start screen's Help link can call it directly. */
  async fetchHelp(): Promise<{ message: string; ai: string }> {
    const result = await this.perform("help", {});
    return { message: result.message, ai: result.data.ai };
  }

  async openSummary(): Promise<void> {
    const result = await this.perform("summary", {});
    this.patch({ summaryResult: result, dialog: null });
  }

  closeSummary(): void {
    this.patch({ summaryResult: null });
  }

  /* ------------------------------------------------------------ generation / saves */

  async advanceGeneration(): Promise<void> {
    if (this.state.pendingDoctrine) {
      this.showToast("A doctrine choice is waiting for an answer first.");
      return;
    }
    const result = await this.perform("advance_generation", {});
    if (result.ok) await this.autosave();
  }

  async autosave(): Promise<void> {
    try {
      const text = await this.bridge.save();
      saveToSlot("autosave", withLabel(text, "Autosave"));
    } catch (error) {
      this.showToast(`Autosave failed: ${describe(error)}`);
    }
  }

  /** The console's `s` shortcut: save under the label "quicksave" without opening the menu. */
  async quickSave(): Promise<void> {
    await this.manualSave("quicksave");
  }

  async manualSave(label: string): Promise<void> {
    try {
      const text = await this.bridge.save();
      const chosen = label || "save";
      saveNew(withLabel(text, chosen));
      this.showToast(`Saved as "${chosen}".`);
    } catch (error) {
      this.showToast(`Could not save: ${describe(error)}`);
    }
  }

  async exportSave(): Promise<string> {
    return this.bridge.save();
  }
}

/** Subscribes a component to `store`; re-renders on every state change. */
export function useStore(store: Store): UIState {
  const [, setTick] = useState(0);
  useEffect(() => store.subscribe(() => setTick((tick) => tick + 1)), [store]);
  return store.state;
}
