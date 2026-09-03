/**
 * "This generation": what the player has done since the last advance, and the way back out
 * of it - now also the plan editor. A generation is 25 years and cannot be replayed, so the
 * three questions this panel answers - *what did I just do?*, *can I take that back?*, *am I
 * ready to move on?* - are worth their own box under the action buttons.
 *
 * Nothing here is derived: the rows are `ViewState.generation_log`, written by the engine's
 * own action methods, and "Undo last" / each row's ✕ are both the facade's `undo` action
 * (docs/reference/web_contract.md 7). The engine's undo is strictly a stack - there is no way
 * to lift one action out of the middle and keep the ones after it, because redoing them would
 * re-roll their random outcomes and turn undo into a re-roll exploit - so a row's ✕ undoes
 * that action *and everything logged after it* (`store.undoRowAndLater`).
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
  // Same gate the actions panel uses for every button, including its own Advance (ActionsPanel.tsx).
  const busyOrDoctrine = state.busy || state.pendingDoctrine !== null;
  const advanceSpec = view.actions.find((a) => a.id === "advance_generation");
  const ap = `AP ${view.status.action_points}/${view.status.max_action_points}`;
  return (
    <Collapsible id="generation" title="This generation" badge={ap} extraClass="generation-panel">
      {log.length === 0 ? (
        <p class="generation-empty">No actions taken yet this generation.</p>
      ) : (
        <ol class="generation-log">
          {log.map((entry, i) => {
            const isLast = i === log.length - 1;
            const undoLabel = isLast ? "Undo" : "Undo this and later actions";
            return (
              <li key={`${entry.action}-${i}`} class="generation-log-row" data-action={entry.action}>
                <span class="generation-log-summary">{entry.summary}</span>
                {entry.cost && <span class="generation-log-cost">{entry.cost}</span>}
                <button
                  type="button"
                  class="generation-row-undo"
                  disabled={!canUndo}
                  title={undoLabel}
                  aria-label={undoLabel}
                  onClick={() => void store.undoRowAndLater(i)}
                >
                  ✕
                </button>
              </li>
            );
          })}
        </ol>
      )}
      <div class="generation-footer">
        <span class="generation-ap">{view.status.action_points} AP left</span>
        <div class="generation-footer-buttons">
          <button class="generation-undo" disabled={!canUndo} onClick={() => void store.undoLastAction()}>
            Undo last
          </button>
          <button
            class="generation-advance primary"
            disabled={busyOrDoctrine || !advanceSpec}
            onClick={() => advanceSpec && store.openAction(advanceSpec)}
          >
            Advance to next generation
          </button>
        </div>
      </div>
    </Collapsible>
  );
}
