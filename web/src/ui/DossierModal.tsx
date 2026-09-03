import { useEffect } from "preact/hooks";
import { observedAsOf } from "../scene/coords";
import type { Store } from "../store";
import type { ViewState } from "../types";

/** Mirrors `GameInterface._act_view_system`: full message/response history for one system. */
export function DossierModal({ system, view, store }: { system: string; view: ViewState; store: Store }) {
  const s = view.systems.find((sys) => sys.name === system);
  // A save loaded behind an open dossier can drop the system entirely. Calling into the store
  // from the render body would update it mid-render; render nothing and close in an effect.
  useEffect(() => {
    if (!s) store.closeDialog();
  }, [s, store]);
  if (!s) return null;
  const threats = view.threats.filter((t) => t.source === s.name);
  return (
    <div class="modal-backdrop" onClick={() => store.closeDialog()}>
      <div class="modal dossier-modal" onClick={(e) => e.stopPropagation()}>
        <button class="modal-close" onClick={() => store.closeDialog()} aria-label="Close">
          ×
        </button>
        <h2>Dossier: {s.name}</h2>
        <p class="dossier-meta">
          Distance: {s.distance} light-years &middot; Type: {s.spectral_type ?? "unknown"}
          {s.ra !== null && s.dec !== null && (
            <>
              {" "}
              &middot; RA {s.ra.toFixed(1)}°, Dec {s.dec >= 0 ? "+" : ""}
              {s.dec.toFixed(1)}°
            </>
          )}
        </p>
        <p class="dossier-meta">Signal round trip: {s.round_trip_generations} generation(s)</p>
        {/* Light-time honesty: the knowledge below describes the system as the light left it. */}
        <p class="dossier-meta dossier-observed">{observedAsOf(s.observed_year, s.distance)}</p>
        <p class="dossier-knowledge">
          Knowledge: {s.knowledge}% - {s.description || "nothing studied yet"}
        </p>
        {s.is_seeded && (
          <p class="dossier-seeded">
            Genesis Ark Program: an ark from Earth is on its way to this world, or already landed.
          </p>
        )}
        {s.messages_sent.length > 0 && (
          <>
            <h3>Messages sent ({s.messages_sent.length})</h3>
            <ul class="dossier-list">
              {s.messages_sent.map((m, i) => (
                <li key={i}>
                  Gen {m.generation} (arrives Gen {m.arrival_gen}): &ldquo;{m.text}&rdquo;
                </li>
              ))}
            </ul>
          </>
        )}
        {s.responses.length > 0 && (
          <>
            <h3>Replies received ({s.responses.length})</h3>
            <ul class="dossier-list">
              {s.responses.map((text, i) => (
                <li key={i}>&ldquo;{text}&rdquo;</li>
              ))}
            </ul>
          </>
        )}
        {s.next_response_gen !== null && (
          <p class="dossier-meta">A reply is on its way; expected in Generation {s.next_response_gen}.</p>
        )}
        {threats.map((t) => (
          <p key={t.index} class="dossier-threat">
            {t.type_label} inbound: ETA {t.eta} generation(s), defense {t.defense_pct}%
          </p>
        ))}
      </div>
    </div>
  );
}
