import { exportSave } from "../saves";
import type { Store } from "../store";
import type { PerformResult } from "../types";

/**
 * The final report. `web_api.py`'s `summary` action puts only the score and its breakdown in
 * `data` - the rest (timeline, contacts, hostile encounters, swan songs, Genesis, the WOW!
 * outcome, achievements) is written into `build_summary()`'s text and nowhere else structured,
 * so the breakdown becomes a table and the full text stays below it, verbatim, in a `<pre>`.
 */
export function SummaryModal({ store, result }: { store: Store; result: PerformResult }) {
  const data = result.data as { score: number; score_breakdown: Record<string, number> } | undefined;
  const generation = store.state.view?.generation ?? 0;

  const doExport = async () => {
    const text = await store.exportSave();
    exportSave(text, `legacy-of-stars-final-gen${generation}.json`);
  };

  return (
    <div class="modal-backdrop">
      <div class="modal summary-modal">
        <h2>Final report</h2>
        {data && (
          <table class="score-table">
            <tbody>
              {Object.entries(data.score_breakdown).map(([label, value]) => (
                <tr key={label}>
                  <td>{label}</td>
                  <td class="score-value">{value}</td>
                </tr>
              ))}
              <tr class="score-total">
                <td>Total</td>
                <td class="score-value">{data.score}</td>
              </tr>
            </tbody>
          </table>
        )}
        <pre class="summary-text">{result.message}</pre>
        <div class="modal-actions">
          <button onClick={() => void doExport()}>Export save</button>
          <button onClick={() => store.closeSummary()}>Close</button>
          <button class="primary" onClick={() => store.backToStart()}>
            New game
          </button>
        </div>
      </div>
    </div>
  );
}
