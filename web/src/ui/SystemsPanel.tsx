/**
 * The flat systems list. Since W3 this is no longer the main way to see the sky - it is the
 * "List" overlay on top of the star map (ui/MapPanel.tsx) - so a row now *selects* the system
 * (the map flies its highlight there and the selected-system card opens) and the dossier has
 * its own button.
 */
import type { Store } from "../store";
import type { StarSystem, ViewState } from "../types";

function excerpt(text: string, max = 90): string {
  return text.length <= max ? text : `${text.slice(0, max - 3)}...`;
}

function SystemRow({
  s,
  selected,
  onSelect,
  onOpenDossier,
}: {
  s: StarSystem;
  selected: boolean;
  onSelect: () => void;
  onOpenDossier: () => void;
}) {
  const lastMessage = s.messages_sent[s.messages_sent.length - 1];
  const lastResponse = s.responses[s.responses.length - 1];
  return (
    <li
      class={selected ? "system-row is-selected" : "system-row"}
      data-system={s.name}
      aria-current={selected ? "true" : undefined}
      onClick={onSelect}
    >
      <div class="system-row-head">
        <span class="system-index">{s.index}.</span>
        <span class="system-name">{s.name}</span>
        <span class="system-meta">
          {s.distance} LY{s.spectral_type ? `, ${s.spectral_type}` : ""}
        </span>
        <span class="system-knowledge">{s.knowledge}% known</span>
        {s.is_seeded && <span class="system-seeded" title="Genesis ark en route or landed">seeded</span>}
        <button
          class="system-dossier"
          onClick={(e) => {
            e.stopPropagation();
            onOpenDossier();
          }}
        >
          Dossier
        </button>
      </div>
      {s.description && <div class="system-description">{s.description}</div>}
      {lastMessage && (
        <div class="system-line">
          Messages sent: {s.messages_sent.length} (last Gen {lastMessage.generation}, arrives Gen{" "}
          {lastMessage.arrival_gen})
        </div>
      )}
      {lastResponse && (
        <div class="system-line">
          Replies: {s.responses.length} &gt; &ldquo;{excerpt(lastResponse)}&rdquo;
        </div>
      )}
      {s.next_response_gen !== null && (
        <div class="system-line">Next reply expected: Generation {s.next_response_gen}</div>
      )}
    </li>
  );
}

export function SystemsPanel({ view, store }: { view: ViewState; store: Store }) {
  const selected = store.state.selectedSystem;
  return (
    <section class="panel systems-panel">
      <div class="systems-panel-head">
        <h2>
          Star systems ({view.catalog.known} of {view.catalog.total} catalogued,{" "}
          {Math.round(view.catalog.discovery_chance * 100)}% chance of a new one per generation)
        </h2>
        <button class="systems-close" aria-label="Close the list" onClick={() => store.toggleSystemList(false)}>
          ×
        </button>
      </div>
      {view.systems.length === 0 ? (
        <p class="empty">No systems catalogued yet.</p>
      ) : (
        <ul class="system-list">
          {view.systems.map((s) => (
            <SystemRow
              key={s.name}
              s={s}
              selected={s.name === selected}
              onSelect={() => store.selectSystem(s.name)}
              onOpenDossier={() => store.openDossier(s.name)}
            />
          ))}
        </ul>
      )}
    </section>
  );
}
