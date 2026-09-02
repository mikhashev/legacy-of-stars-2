import type { Store } from "../store";
import type { PerformResult } from "../types";

/** The final report: `build_summary()` text plus the score breakdown (action `summary`). */
export function SummaryModal({ store, result }: { store: Store; result: PerformResult }) {
  const data = result.data as { score: number; score_breakdown: Record<string, number> } | undefined;
  return (
    <div class="modal-backdrop">
      <div class="modal summary-modal">
        <pre class="summary-text">{result.message}</pre>
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
        <div class="modal-actions">
          <button onClick={() => store.closeSummary()}>Close</button>
          <button class="primary" onClick={() => store.backToStart()}>
            New game
          </button>
        </div>
      </div>
    </div>
  );
}
