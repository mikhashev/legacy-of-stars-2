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
          </>
        )}
      </div>
    </div>
  );
}
