import { useEffect } from "preact/hooks";
import type { Store } from "../store";

/** A dismissable, auto-hiding banner for engine refusals and worker errors. */
export function Toast({ text, store }: { text: string; store: Store }) {
  useEffect(() => {
    const timer = setTimeout(() => store.dismissToast(), 6000);
    return () => clearTimeout(timer);
  }, [text, store]);

  return (
    <div class="toast" role="alert" onClick={() => store.dismissToast()}>
      {text}
    </div>
  );
}
