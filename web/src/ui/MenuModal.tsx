import { Fragment } from "preact";
import { useRef, useState } from "preact/hooks";
import type { Store } from "../store";
import { exportSave, importSaveFile, listSaves, loadSaveText, type SaveMeta } from "../saves";
import type { ViewState } from "../types";

function formatDate(iso: string): string {
  if (!iso) return "unknown date";
  return iso.replace("T", " ").slice(0, 16);
}

/** The in-game menu: save/load/export/import, help and the final report, any time. */
export function MenuModal({ view, store }: { view: ViewState; store: Store }) {
  const [label, setLabel] = useState("");
  const [saves, setSaves] = useState<SaveMeta[]>(() => listSaves());
  const fileInput = useRef<HTMLInputElement>(null);

  const refresh = () => setSaves(listSaves());

  const doSave = async () => {
    await store.manualSave(label.trim() || `Generation ${view.generation}`);
    refresh();
  };

  const doExport = async () => {
    const text = await store.exportSave();
    exportSave(text, `legacy-of-stars-gen${view.generation}.json`);
  };

  const doLoad = (meta: SaveMeta) => {
    const text = loadSaveText(meta.key);
    if (!text) {
      store.showToast("That save could not be read.");
      refresh();
      return;
    }
    void store.loadFromText(text);
  };

  const doImport = async (file: File) => {
    try {
      const text = await importSaveFile(file);
      await store.loadFromText(text);
    } catch (error) {
      store.showToast(`Could not read file: ${error instanceof Error ? error.message : String(error)}`);
    }
  };

  return (
    <div class="modal-backdrop" onClick={() => store.closeDialog()}>
      <div class="modal menu-modal" onClick={(e) => e.stopPropagation()}>
        <button class="modal-close" onClick={() => store.closeDialog()} aria-label="Close">
          ×
        </button>
        <h2>Menu</h2>

        <section class="menu-section">
          <h3>Save game</h3>
          <div class="menu-save-row">
            <input
              type="text"
              placeholder={`Generation ${view.generation}`}
              value={label}
              onInput={(e) => setLabel((e.target as HTMLInputElement).value)}
            />
            <button onClick={() => void doSave()}>Save</button>
          </div>
          <button onClick={() => void doExport()}>Export current save as file</button>
        </section>

        <section class="menu-section">
          <h3>Load game</h3>
          {saves.length === 0 ? (
            <p class="empty">No saves in this browser yet.</p>
          ) : (
            <ul class="save-list">
              {saves.map((meta) => (
                <li key={meta.key} class="save-row">
                  <button class="save-row-button" onClick={() => doLoad(meta)}>
                    <span class="save-label">{meta.label}</span>
                    <span class="save-meta">
                      Generation {meta.generation} &middot; Year {meta.year}
                      {meta.gameOver ? " · finished" : ""}
                    </span>
                    <span class="save-date">{formatDate(meta.savedAt)}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
          <button onClick={() => fileInput.current?.click()}>Import JSON file</button>
          <input
            ref={fileInput}
            type="file"
            accept="application/json,.json"
            hidden
            onChange={(e) => {
              const file = (e.target as HTMLInputElement).files?.[0];
              (e.target as HTMLInputElement).value = "";
              if (file) void doImport(file);
            }}
          />
        </section>

        <section class="menu-section">
          <h3>Achievements ({view.achievements.length})</h3>
          {view.achievements.length === 0 ? (
            <p class="empty">None unlocked yet.</p>
          ) : (
            <ul class="achievement-list">
              {view.achievements.map((name) => (
                <li key={name} class="achievement-row">
                  {name}
                </li>
              ))}
            </ul>
          )}
        </section>

        <section class="menu-section">
          <h3>Statistics</h3>
          <dl class="stats-grid">
            {Object.entries(view.stats).map(([label, value]) => (
              <Fragment key={label}>
                <dt>{label.replace(/_/g, " ")}</dt>
                <dd>{value}</dd>
              </Fragment>
            ))}
          </dl>
        </section>

        <section class="menu-section menu-links">
          <button
            onClick={() => {
              store.closeDialog();
              store.toggleHelp(true);
            }}
          >
            Help
          </button>
          <button onClick={() => void store.openSummary()}>Final report</button>
          <button onClick={() => store.backToStart()}>Back to start screen</button>
        </section>
      </div>
    </div>
  );
}
