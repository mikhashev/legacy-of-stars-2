import type { Store } from "../store";
import type { GameEvent, GameEventKind } from "../types";

const TITLES: Partial<Record<GameEventKind, string>> = {
  wow: "The WOW! Signal",
  victory: "Victory",
  game_over: "Game Over",
  attack_warning: "Incoming Attack",
  attack_resolved: "Attack Resolved",
  philosophical_event: "Philosophical Crisis",
  briefing: "Mission Analyst's Briefing",
};

/** The modal weight for `MODAL_EVENT_KINDS` (web_contract.md 5): big beats, one at a time. */
export function EventModal({ event, store }: { event: GameEvent; store: Store }) {
  return (
    <div class="modal-backdrop">
      <div class={`modal event-modal event-modal-${event.kind}`}>
        <h2>{TITLES[event.kind] ?? event.kind}</h2>
        <p class="event-modal-text">{event.text}</p>
        <div class="modal-actions">
          {event.kind === "philosophical_event" ? (
            <>
              <button onClick={() => store.dismissModal()}>Later</button>
              <button class="primary" onClick={() => store.respondToPendingEventNow()}>
                Respond now
              </button>
            </>
          ) : (
            <button class="primary" onClick={() => store.dismissModal()}>
              {event.kind === "briefing" ? "Got it" : "Continue"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
