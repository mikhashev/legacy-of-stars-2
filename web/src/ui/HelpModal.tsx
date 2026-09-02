import { useEffect, useState } from "preact/hooks";
import type { Store } from "../store";

/** HELP_TEXT from the engine (`ui_text.py`), fetched through `store.fetchHelp()`. */
export function HelpModal({ store }: { store: Store }) {
  const [text, setText] = useState<string | null>(null);
  const [ai, setAi] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    store
      .fetchHelp()
      .then((result) => {
        if (cancelled) return;
        setText(result.message);
        setAi(result.ai);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      });
    return () => {
      cancelled = true;
    };
  }, [store]);

  return (
    <div class="modal-backdrop" onClick={() => store.toggleHelp(false)}>
      <div class="modal help-modal" onClick={(e) => e.stopPropagation()}>
        <button class="modal-close" onClick={() => store.toggleHelp(false)} aria-label="Close">
          ×
        </button>
        {error && <p class="error">{error}</p>}
        {!error && text === null && <p>Loading...</p>}
        {text !== null && (
          <>
            <pre class="help-text">{text}</pre>
            {ai && <p class="help-ai">AI text generation: {ai}</p>}
            <section class="help-web">
              <h3>Playing in the browser</h3>
              <ul class="help-web-list">
                <li>
                  <strong>Mouse:</strong> drag to rotate the star map, scroll/pinch to zoom, right-click drag
                  (or two-finger drag) to pan. Click a star or its label to select it.
                </li>
                <li>
                  <strong>Keys:</strong> 1-5 the core actions, 6 the menu, 7+ situational actions in the order
                  the game lists them, <kbd>v</kbd> the dossier of the selected system (or a picker),{" "}
                  <kbd>s</kbd> quicksave, <kbd>h</kbd> / <kbd>?</kbd> this help, <kbd>Esc</kbd> closes the top
                  dialog or clears the map selection. Keys are ignored while a text field has focus.
                </li>
                <li>
                  <strong>Effects toggle:</strong> the map toolbar's "Effects" button drops the background
                  nebula and one-off flashes on slower machines; the light spheres, fleets and leakage front
                  keep animating either way.
                </li>
                <li>
                  <strong>Saves live in this browser</strong> (localStorage) - clearing site data or switching
                  browsers loses them. Use the menu's "Export save" to keep a copy as a file, and "Import JSON
                  file" to load it back, on this machine or the console build.
                </li>
              </ul>
            </section>
          </>
        )}
      </div>
    </div>
  );
}
