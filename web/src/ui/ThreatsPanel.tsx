import type { ViewState } from "../types";
import { Collapsible } from "./Collapsible";

/** Mirrors the console's "ACTIVE THREATS" block; only rendered when threats exist. */
export function ThreatsPanel({ view }: { view: ViewState }) {
  if (view.threats.length === 0) return null;
  return (
    <Collapsible id="threats" title="Active threats" extraClass="threats-panel">
      <ul class="threat-list">
        {view.threats.map((t) => (
          <li key={t.index} class="threat-row">
            <div class="threat-head">
              {t.type_label} from {t.source}
            </div>
            <div class="threat-line">
              Source distance: {t.source_distance} LY &middot; ETA {t.eta} gen(s) &middot; arrives Year{" "}
              {t.arrival_year}
            </div>
            <div class="threat-line">
              Enemy tech: {t.enemy_stage} &middot; Defense: {t.defense_pct}% damage reduction
            </div>
            {t.actions_taken.length > 0 ? (
              <div class="threat-line">Actions taken: {t.actions_taken.join(", ")}</div>
            ) : (
              <div class="threat-line warning">No defenses deployed yet!</div>
            )}
          </li>
        ))}
      </ul>
    </Collapsible>
  );
}
