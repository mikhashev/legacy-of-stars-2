import type { ProgressMessage } from "../types";

/** Shown while the Pyodide worker boots (kept from the W1 smoke page). */
export function LoadingScreen({ progress, error }: { progress: ProgressMessage | null; error: string | null }) {
  return (
    <main class="loading-screen" data-ready={error ? "failed" : "false"}>
      <h1>Legacy of Stars</h1>
      {error ? (
        <p class="error">Failed to start the engine: {error}</p>
      ) : (
        <>
          <progress max={100} value={progress?.pct ?? 0} />
          <p class="loading-stage">{progress?.stage ?? "starting"}</p>
        </>
      )}
    </main>
  );
}
