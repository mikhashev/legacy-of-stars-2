import type { Store } from "../store";
import type { ActionId, ActionSpec, ViewState } from "../types";

/** Core actions keep the console's fixed hotkeys 1-5 (game_interface.py CORE_ACTION_KEYS). */
const CORE_ORDER: ActionId[] = [
  "send_message",
  "focus_research",
  "public_outreach",
  "research_tech",
  "advance_generation",
];

export interface KeyedAction {
  spec: ActionSpec;
  key: string;
}

/**
 * Assigns the console's numbering: 1-5 for the core actions (if offered), 6 is reserved for
 * the in-game menu (the console's Quit has no browser equivalent), 7+ for everything else
 * in the order the engine lists it.
 */
export function assignKeys(actions: ActionSpec[]): KeyedAction[] {
  const byId = new Map(actions.map((spec) => [spec.id, spec]));
  const keyed: KeyedAction[] = [];
  CORE_ORDER.forEach((id, i) => {
    const spec = byId.get(id);
    if (spec) keyed.push({ spec, key: String(i + 1) });
  });
  let next = 7;
  for (const spec of actions) {
    if (CORE_ORDER.includes(spec.id)) continue;
    keyed.push({ spec, key: String(next) });
    next += 1;
  }
  return keyed;
}

export function ActionsPanel({ view, store }: { view: ViewState; store: Store }) {
  const keyed = assignKeys(view.actions);
  const disabled = store.state.busy || store.state.pendingDoctrine !== null;
  return (
    <section class="panel actions-panel">
      <h2>Actions</h2>
      <div class="action-buttons">
        {keyed.map(({ spec, key }) => (
          <button
            key={spec.id}
            class="action-button"
            disabled={disabled}
            onClick={() => store.openAction(spec)}
            title={spec.needs.length ? `needs: ${spec.needs.join(", ")}` : undefined}
          >
            <span class="action-key">{key}</span>
            <span class="action-label">{spec.label}</span>
            {spec.cost && <span class="action-cost">{spec.cost}</span>}
          </button>
        ))}
        <button class="action-button" disabled={disabled} onClick={() => store.openMenu()}>
          <span class="action-key">6</span>
          <span class="action-label">Menu</span>
          <span class="action-cost">save / load / help</span>
        </button>
      </div>
      {view.pending_event && (
        <p class="actions-hint">
          A philosophical crisis is pending - respond to it before advancing the generation.
        </p>
      )}
    </section>
  );
}
