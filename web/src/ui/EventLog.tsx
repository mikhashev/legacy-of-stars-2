import type { GameEvent, GameEventKind } from "../types";
import { Collapsible } from "./Collapsible";

/** These two carry fixed-width, multi-line reports (rulers, indented lines): they need a
 *  monospace block that wraps anywhere rather than the normal prose wrap the other kinds get. */
const MONOSPACE_KINDS: ReadonlySet<GameEventKind> = new Set(["briefing", "wow"]);

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
  briefing: "\u{1F4CB}", // clipboard: the mission analyst's unasked read of the board
  fermi_evidence: "\u{1F9E9}",
  achievement: "\u{1F3C6}",
  genesis: "\u{1F331}",
  victory: "\u{1F389}",
  wow: "\u{1F4E1}",
  game_over: "⏹️",
  sky_change: "\u{1F52D}", // telescope: new light from a studied system
};

/** The event journal: every `GameEvent` from every `perform()` call, newest first. */
export function EventLog({ events }: { events: GameEvent[] }) {
  const ordered = [...events].reverse();
  return (
    <Collapsible id="journal" title="Event log" extraClass="event-log">
      {ordered.length === 0 ? (
        <p class="empty">Nothing has happened yet.</p>
      ) : (
        <ul class="event-list">
          {ordered.map((event, i) => (
            // eslint-disable-next-line react/no-array-index-key -- events carry no stable id
            <li key={i} class={`event-row event-${event.kind}`}>
              <span class="event-icon">{KIND_ICON[event.kind]}</span>
              <span class="event-gen">Gen {event.generation}</span>
              <span class={`event-text${MONOSPACE_KINDS.has(event.kind) ? " event-text-mono" : ""}`}>
                {event.text}
              </span>
            </li>
          ))}
        </ul>
      )}
    </Collapsible>
  );
}
