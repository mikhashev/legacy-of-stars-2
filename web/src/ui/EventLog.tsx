import type { GameEvent, GameEventKind } from "../types";

const KIND_ICON: Record<GameEventKind, string> = {
  generation_start: "\u{1F4C5}", // calendar
  crisis: "⚠️",
  bonus: "✨",
  response_received: "\u{1F4E8}",
  system_discovered: "\u{1F52D}",
  attack_warning: "\u{1F6A8}",
  attack_resolved: "\u{1F4A5}",
  info_attack: "\u{1F9E0}",
  philosophical_event: "\u{1F914}",
  fermi_evidence: "\u{1F9E9}",
  achievement: "\u{1F3C6}",
  genesis: "\u{1F331}",
  victory: "\u{1F389}",
  wow: "\u{1F4E1}",
  game_over: "⏹️",
};

/** The event journal: every `GameEvent` from every `perform()` call, newest first. */
export function EventLog({ events }: { events: GameEvent[] }) {
  const ordered = [...events].reverse();
  return (
    <section class="panel event-log">
      <h2>Event log</h2>
      {ordered.length === 0 ? (
        <p class="empty">Nothing has happened yet.</p>
      ) : (
        <ul class="event-list">
          {ordered.map((event, i) => (
            // eslint-disable-next-line react/no-array-index-key -- events carry no stable id
            <li key={i} class={`event-row event-${event.kind}`}>
              <span class="event-icon">{KIND_ICON[event.kind]}</span>
              <span class="event-gen">Gen {event.generation}</span>
              <span class="event-text">{event.text}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
