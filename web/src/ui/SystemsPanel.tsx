import type { Store } from "../store";
import type { StarSystem, ViewState } from "../types";

function excerpt(text: string, max = 90): string {
  return text.length <= max ? text : `${text.slice(0, max - 3)}...`;
}

function SystemRow({ s, onOpen }: { s: StarSystem; onOpen: () => void }) {
  const lastMessage = s.messages_sent[s.messages_sent.length - 1];
  const lastResponse = s.responses[s.responses.length - 1];
  return (
    <li class="system-row" onClick={onOpen}>
      <div class="system-row-head">
        <span class="system-index">{s.index}.</span>
        <span class="system-name">{s.name}</span>
        <span class="system-meta">
          {s.distance} LY{s.spectral_type ? `, ${s.spectral_type}` : ""}
        </span>
        <span class="system-knowledge">{s.knowledge}% known</span>
        {s.is_seeded && <span class="system-seeded" title="Genesis ark en route or landed">seeded</span>}
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
  return (
    <section class="panel systems-panel">
      <h2>
        Star systems ({view.catalog.known} of {view.catalog.total} catalogued,{" "}
        {Math.round(view.catalog.discovery_chance * 100)}% chance of a new one per generation)
      </h2>
      {view.systems.length === 0 ? (
        <p class="empty">No systems catalogued yet.</p>
      ) : (
        <ul class="system-list">
          {view.systems.map((s) => (
            <SystemRow key={s.name} s={s} onOpen={() => store.openDossier(s.name)} />
          ))}
        </ul>
      )}
    </section>
  );
}
