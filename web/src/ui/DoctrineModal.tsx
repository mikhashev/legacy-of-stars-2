import type { Store } from "../store";
import type { DoctrineNeeds } from "../types";

/**
 * `research_tech`'s follow-up (web_contract.md 4). The technology is already researched;
 * only the doctrine's effects are pending, so this blocks every other action until answered.
 */
export function DoctrineModal({ needs, store }: { needs: DoctrineNeeds; store: Store }) {
  return (
    <div class="modal-backdrop">
      <div class="modal doctrine-modal">
        <h2>Doctrine choice required: {needs.name}</h2>
        <p class="dialog-hint">{needs.description}</p>
        <ul class="picker-list">
          {needs.options.map((option) => (
            <li key={option.index}>
              <button class="picker-row" onClick={() => void store.chooseDoctrine(option.index)}>
                <span class="picker-name">{option.name}</span>
                <span class="picker-meta">{option.description}</span>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
