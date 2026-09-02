import type { ViewState } from "../types";
import { Collapsible } from "./Collapsible";

function pct(value: number): string {
  return `${Math.round(value)}%`;
}

/** The console's "Program Status" block, plus win-condition counters and doctrines. */
export function StatusPanel({ view }: { view: ViewState }) {
  const s = view.status;
  const evidence = view.fermi_evidence;
  return (
    <Collapsible id="status" title="Program status" extraClass="status-panel">
      <dl class="status-grid">
        <dt>Action Points</dt>
        <dd>
          {s.action_points} / {s.max_action_points}
        </dd>
        <dt>Funding</dt>
        <dd class={s.funding < 25 ? "danger" : undefined}>{pct(s.funding)}</dd>
        <dt>Public Support</dt>
        <dd class={s.public_support < 15 ? "danger" : undefined}>{pct(s.public_support)}</dd>
        <dt>Knowledge Base</dt>
        <dd>{pct(s.knowledge_base)}</dd>
        <dt>Research Points</dt>
        <dd>
          {s.research_points} (+{s.passive_rp.toFixed(1)}/gen)
        </dd>
        <dt>Tech Level</dt>
        <dd>{s.tech_level}</dd>
        <dt>Leakage Front</dt>
        <dd>{s.broadcast_radius.toFixed(0)} LY</dd>
        <dt>Self-Destruct Risk</dt>
        <dd>{(s.self_destruct_risk * 100).toFixed(1)}%</dd>
        <dt>Ecological Risk</dt>
        <dd>{(s.ecological_risk * 100).toFixed(1)}%</dd>
        <dt>Integration</dt>
        <dd>
          {Math.round(s.integration_level * 100)}% - {s.integration_status}
        </dd>
        <dt>Contacts</dt>
        <dd>
          {view.contacts} / {view.contacts_goal}
        </dd>
        <dt>Fermi Evidence</dt>
        <dd>
          {evidence.total} / {evidence.goal}
        </dd>
      </dl>
      {view.active_doctrines.length > 0 && (
        <p class="status-doctrines">
          <strong>Active doctrines:</strong> {view.active_doctrines.join(", ")}
        </p>
      )}
      {view.genesis.unlocked && <p class="status-genesis">{view.genesis.summary}</p>}
    </Collapsible>
  );
}
