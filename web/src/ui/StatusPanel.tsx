import type { ViewState } from "../types";
import { Collapsible } from "./Collapsible";

function pct(value: number): string {
  return `${Math.round(value)}%`;
}

/**
 * What each row means, as a `title` tooltip on both the term and its value. Playtesters read
 * the numbers fine and could not say what moved them, so every rule stated here is one the
 * engine actually applies (docs/reference/web_contract.md 6) - no row promises a mechanic that is not
 * in `legacy_of_stars_v3.py`.
 */
const HINTS = {
  action_points:
    "What you may do this generation. Most actions cost 1 AP; research is free. Unspent points do not carry over - advancing the generation refills them.",
  funding:
    "The program's budget. Each generation it moves with public support (and the director's administration skill); below 20% the program is defunded and the run ends.",
  public_support:
    "How much the public backs the program. Outreach raises it, replies and recovered archives raise it, crises and low integration cost it.",
  knowledge_base:
    "Everything the program has learned, across all systems. Grows with replies from civilizations, recovered swan songs and resolved crises; Focus Research raises a single system's knowledge instead.",
  research_points: "Spent on technologies. The per-generation figure is passive income, scaled by integration.",
  tech_level: "The highest technology tier researched. Alien civilizations read it as how advanced we look.",
  broadcast_radius:
    "How far Earth's broadcasts since the 1930s have travelled. It grows one light-year a year no matter what you do: technology changes how loud we are, not how far.",
  self_destruct_risk:
    "The chance per generation that Earth ends itself - war, runaway technology, a failed transition. Low integration and reckless doctrines raise it; safeguards lower it.",
  ecological_risk:
    "The chance per generation of an ecological collapse at home. Industrial expansion raises it; ecological and integration technologies lower it.",
  integration:
    "Biological-technological integration. Below 30% after Generation 30 it costs support and raises self-destruct risk; Transcendence technologies raise it. Grace period until Generation 30.",
  contacts:
    "Civilizations that have answered us. Three replies is the contact victory: only a reply counts, not a message sent.",
  fermi_evidence:
    "Evidence toward an answer to the Fermi paradox: extinctions found, hostile encounters survived, peaceful contacts and great-filter discoveries. 15 points is the philosophical victory.",
  achievements: "Milestones this run has unlocked: see Menu for the list.",
  active_effects:
    "The permanent modifiers in force right now - the 1977 decision, researched technologies, doctrines and the integration bonus or penalty. The engine writes these lines; each one is a rule it is applying.",
} as const;

/** The console's "Program Status" block, plus win-condition counters and doctrines. */
export function StatusPanel({ view }: { view: ViewState }) {
  const s = view.status;
  const evidence = view.fermi_evidence;
  return (
    <Collapsible id="status" title="Program status" extraClass="status-panel">
      <p class="status-hint">Hover a row for what it means.</p>
      <dl class="status-grid">
        <dt title={HINTS.action_points}>Action Points</dt>
        <dd title={HINTS.action_points}>
          {s.action_points} / {s.max_action_points}
        </dd>
        <dt title={HINTS.funding}>Funding</dt>
        <dd class={s.funding < 25 ? "danger" : undefined} title={HINTS.funding}>
          {pct(s.funding)}
        </dd>
        <dt title={HINTS.public_support}>Public Support</dt>
        <dd class={s.public_support < 15 ? "danger" : undefined} title={HINTS.public_support}>
          {pct(s.public_support)}
        </dd>
        <dt title={HINTS.knowledge_base}>Knowledge Base</dt>
        <dd title={HINTS.knowledge_base}>{pct(s.knowledge_base)}</dd>
        <dt title={HINTS.research_points}>Research Points</dt>
        <dd title={HINTS.research_points}>
          {s.research_points} (+{s.passive_rp.toFixed(1)}/gen)
        </dd>
        <dt title={HINTS.tech_level}>Tech Level</dt>
        <dd title={HINTS.tech_level}>{s.tech_level}</dd>
        <dt title={HINTS.broadcast_radius}>Leakage Front</dt>
        <dd title={HINTS.broadcast_radius}>{s.broadcast_radius.toFixed(0)} LY</dd>
        <dt title={HINTS.self_destruct_risk}>Self-Destruct Risk</dt>
        <dd title={HINTS.self_destruct_risk}>{(s.self_destruct_risk * 100).toFixed(1)}%</dd>
        <dt title={HINTS.ecological_risk}>Ecological Risk</dt>
        <dd title={HINTS.ecological_risk}>{(s.ecological_risk * 100).toFixed(1)}%</dd>
        <dt title={HINTS.integration}>Integration</dt>
        <dd title={HINTS.integration}>
          {Math.round(s.integration_level * 100)}% - {s.integration_status}
        </dd>
        <dt title={HINTS.contacts}>Contacts</dt>
        <dd title={HINTS.contacts}>
          {view.contacts} / {view.contacts_goal}
        </dd>
        <dt title={HINTS.fermi_evidence}>Fermi Evidence</dt>
        <dd title={HINTS.fermi_evidence}>
          {evidence.total} / {evidence.goal}
        </dd>
        <dt title={HINTS.achievements}>Achievements</dt>
        <dd title={HINTS.achievements}>{view.achievements.length}</dd>
      </dl>
      <div class="status-effects" title={HINTS.active_effects}>
        <p class="status-effects-title">Active effects</p>
        {view.active_effects.length === 0 ? (
          <p class="status-effects-empty">None yet</p>
        ) : (
          <ul class="status-effects-list">
            {view.active_effects.map((effect) => (
              <li key={effect}>{effect}</li>
            ))}
          </ul>
        )}
      </div>
      {view.genesis.unlocked && <p class="status-genesis">{view.genesis.summary}</p>}
    </Collapsible>
  );
}
