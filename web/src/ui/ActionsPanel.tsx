import type { Store } from "../store";
import type { ActionId, ActionSpec, ViewState } from "../types";
import { Collapsible } from "./Collapsible";

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

/**
 * The run has ended: the engine refuses every action but `summary`/`help`, so offering the
 * numbered buttons would only produce refusal toasts. The two things still worth doing take
 * their place - and the menu stays, since load/import is how a player gets back into a game.
 */
function GameOverPanel({ view, store }: { view: ViewState; store: Store }) {
  return (
    <Collapsible id="actions" title="Actions" extraClass="actions-panel actions-panel-over">
      <div class="actions-gameover">
        <p class="actions-gameover-title">Game over</p>
        {view.game_over_reason && <p class="actions-gameover-reason">{view.game_over_reason}</p>}
        <div class="action-buttons">
          <button class="action-button" disabled={store.state.busy} onClick={() => void store.openSummary()}>
            <span class="action-label">Final report</span>
          </button>
          <button class="action-button" disabled={store.state.busy} onClick={() => store.backToStart()}>
            <span class="action-label">New game</span>
          </button>
          <button class="action-button" disabled={store.state.busy} onClick={() => store.openMenu()}>
            <span class="action-key">6</span>
            <span class="action-label">Menu</span>
            <span class="action-cost">save / load / help</span>
          </button>
        </div>
      </div>
    </Collapsible>
  );
}

export function ActionsPanel({ view, store }: { view: ViewState; store: Store }) {
  if (view.game_over) return <GameOverPanel view={view} store={store} />;
  const keyed = assignKeys(view.actions);
  const disabled = store.state.busy || store.state.pendingDoctrine !== null;
  // The AP counter sits with the buttons that spend it: the status panel is collapsible and
  // may be closed (or scrolled away) exactly when the player is choosing what to spend on.
  const ap = `AP ${view.status.action_points}/${view.status.max_action_points}`;
  return (
    <Collapsible id="actions" title="Actions" badge={ap} extraClass="actions-panel">
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
    </Collapsible>
  );
}
