import type { ViewState } from "../types";

/** Generation, year and the current director - the console's first three lines. */
export function Header({ view }: { view: ViewState }) {
  const d = view.director;
  return (
    <header class="header">
      <div class="header-title">
        <h1>Legacy of Stars</h1>
        <div class="header-gen">
          Generation {view.generation} &middot; Year {view.year}
        </div>
      </div>
      <div class="header-director">
        <div class="director-name">{d.name}</div>
        <div class="director-traits">{d.traits.join(", ") || "no notable traits"}</div>
        <div class="director-skills">
          Diplomacy {Math.round(d.skills.diplomacy * 100)}% &middot; Science{" "}
          {Math.round(d.skills.science * 100)}% &middot; Administration{" "}
          {Math.round(d.skills.administration * 100)}%
        </div>
      </div>
    </header>
  );
}
