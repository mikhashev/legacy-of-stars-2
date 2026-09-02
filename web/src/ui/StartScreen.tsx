import { useRef, useState } from "preact/hooks";
import type { Store } from "../store";
import { importSaveFile, listSaves, loadSaveText, type SaveMeta } from "../saves";

function formatDate(iso: string): string {
  if (!iso) return "unknown date";
  return iso.replace("T", " ").slice(0, 16);
}

export function StartScreen({ store }: { store: Store }) {
  const [seed, setSeed] = useState("");
  const [saves, setSaves] = useState<SaveMeta[]>(() => listSaves());
  const fileInput = useRef<HTMLInputElement>(null);

  const refresh = () => setSaves(listSaves());

  const startNew = () => {
    const trimmed = seed.trim();
    const seedValue = trimmed === "" ? undefined : Number(trimmed);
    if (trimmed !== "" && !Number.isFinite(seedValue)) {
      store.showToast("Seed must be a number.");
      return;
    }
    void store.newGame(seedValue);
  };

  const load = (meta: SaveMeta) => {
    const text = loadSaveText(meta.key);
    if (!text) {
      store.showToast("That save could not be read.");
      refresh();
      return;
    }
    void store.loadFromText(text);
  };

  const importFile = async (file: File) => {
    try {
      const text = await importSaveFile(file);
      await store.loadFromText(text);
    } catch (error) {
      store.showToast(`Could not read file: ${error instanceof Error ? error.message : String(error)}`);
    }
  };

  return (
    <main class="start-screen">
      <h1>Legacy of Stars</h1>
      <p class="start-tagline">
        Oversee Earth's multi-generational interstellar contact program - from the WOW! Signal
        of 1977 onward.
      </p>

      <section class="start-block">
        <h2>New Game</h2>
        <label class="start-seed">
          Seed (optional)
          <input
            type="text"
            inputMode="numeric"
            value={seed}
            placeholder="random"
            onInput={(e) => setSeed((e.target as HTMLInputElement).value)}
          />
        </label>
        <button class="primary" onClick={startNew} disabled={store.state.busy}>
          Start
        </button>
      </section>

      <section class="start-block">
        <h2>Load Game</h2>
        {saves.length === 0 ? (
          <p class="empty">No saves in this browser yet.</p>
        ) : (
          <ul class="save-list">
            {saves.map((meta) => (
              <li key={meta.key} class="save-row">
                <button class="save-row-button" onClick={() => load(meta)} disabled={store.state.busy}>
                  <span class="save-label">{meta.label}</span>
                  <span class="save-meta">
                    Generation {meta.generation} &middot; Year {meta.year} &middot; {meta.director || "no director"}
                    {meta.gameOver ? " · finished" : ""}
                  </span>
                  <span class="save-date">{formatDate(meta.savedAt)}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
        <button
          onClick={() => fileInput.current?.click()}
          disabled={store.state.busy}
        >
          Import JSON file
        </button>
        <input
          ref={fileInput}
          type="file"
          accept="application/json,.json"
          hidden
          onChange={(e) => {
            const file = (e.target as HTMLInputElement).files?.[0];
            (e.target as HTMLInputElement).value = "";
            if (file) void importFile(file);
          }}
        />
      </section>

      <button class="start-help-link" onClick={() => store.toggleHelp(true)}>
        Help
      </button>
    </main>
  );
}
