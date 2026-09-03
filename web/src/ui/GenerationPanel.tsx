/**
 * "This generation": what the player has done since the last advance, and the way back out
 * of it. A generation is 25 years and cannot be replayed, so the two questions this panel
 * answers - *what did I just do?* and *can I take that back?* - are worth their own box under
 * the action buttons.
 *
 * Nothing here is derived: the rows are `ViewState.generation_log`, written by the engine's
 * own action methods, and "Undo last" is the facade's `undo` action (docs/web_contract.md 7).
 */
import type { Store } from "../store";
import type { ViewState } from "../types";
import { Collapsible } from "./Collapsible";

export function GenerationPanel({ view, store }: { view: ViewState; store: Store }) {
  const log = view.generation_log;
  const state = store.state;
  // The engine's undo stack reaches back past the start of this generation only in theory -
  // `advance_generation` clears it - but the button is about *this* generation's decisions,
  // so it follows the log the player can actually see.
  const canUndo = state.undo.available && log.length > 0 && !state.busy && !state.pendingDoctrine;
  const ap = `AP ${view.status.action_points}/${view.status.max_action_points}`;
  return (
    <Collapsible id="generation" title="This generation" badge={ap} extraClass="generation-panel">
      {log.length === 0 ? (
        <p class="generation-empty">No actions taken yet this generation.</p>
      ) : (
        <ol class="generation-log">
          {log.map((entry, i) => (
            <li key={`${entry.action}-${i}`} class="generation-log-row" data-action={entry.action}>
              <span class="generation-log-summary">{entry.summary}</span>
              {entry.cost && <span class="generation-log-cost">{entry.cost}</span>}
            </li>
          ))}
        </ol>
      )}
      <div class="generation-footer">
        <span class="generation-ap">{view.status.action_points} AP left</span>
        <button class="generation-undo" disabled={!canUndo} onClick={() => void store.undoLastAction()}>
          Undo last
        </button>
      </div>
    </Collapsible>
  );
}
