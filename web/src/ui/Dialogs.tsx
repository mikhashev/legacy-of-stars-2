/**
 * The parameter dialogs `ActionSpec.needs` drives (web_version_plan.md W2 item 4). One
 * component per `Dialog` kind from store.ts; `MainScreen` picks which one to render.
 *
 * None of these filter on affordability or add rules the engine did not state: the tech
 * and threat lists show everything the engine listed, `locked` markers included, and a
 * refusal comes back as the engine's own message (a toast), exactly like the console.
 */
import type { ComponentChildren } from "preact";
import { useEffect, useState } from "preact/hooks";
import type { Store } from "../store";
import type { ActionSpec, ViewState } from "../types";

function DialogFrame({ title, onClose, children }: { title: string; onClose: () => void; children: ComponentChildren }) {
  return (
    <div class="modal-backdrop" onClick={onClose}>
      <div class="modal dialog-modal" onClick={(e) => e.stopPropagation()}>
        <button class="modal-close" onClick={onClose} aria-label="Close">
          ×
        </button>
        <h2>{title}</h2>
        {children}
      </div>
    </div>
  );
}

export function SystemDialog({ view, spec, store }: { view: ViewState; spec: ActionSpec; store: Store }) {
  const isGenesis = spec.id === "genesis_seed";
  // genesis_seed: the engine hands back the exact eligible list (sterile, habitable,
  // unseeded, not the WOW! source) as `genesis.targets`, in order; look each one up in
  // `systems` for its distance/type rather than re-deriving eligibility here.
  const eligible = isGenesis
    ? view.genesis.targets
        .map((name) => view.systems.find((s) => s.name === name))
        .filter((s): s is (typeof view.systems)[number] => s !== undefined)
    : view.systems;
  // W3: the star picked on the map is the default. It is only a default - every eligible
  // system is still listed below and one click changes it.
  const preselected = store.state.selectedSystem;
  const preselectedIsEligible = eligible.some((s) => s.name === preselected);
  return (
    <DialogFrame title={`${spec.label}: choose a system`} onClose={() => store.closeDialog()}>
      {preselected && preselectedIsEligible && (
        <button class="primary picker-preselected" onClick={() => store.pickSystem(preselected)}>
          Continue with {preselected} (selected on the map)
        </button>
      )}
      {eligible.length === 0 ? (
        <p class="empty">{isGenesis ? "No habitable sterile worlds within reach" : "No systems to choose from."}</p>
      ) : (
        <ul class="picker-list">
          {eligible.map((s) => (
            <li key={s.name}>
              <button
                class={s.name === preselected ? "picker-row is-selected" : "picker-row"}
                aria-current={s.name === preselected ? "true" : undefined}
                onClick={() => store.pickSystem(s.name)}
              >
                <span class="picker-name">{s.name}</span>
                <span class="picker-meta">
                  {s.distance} LY{s.spectral_type ? `, ${s.spectral_type}` : ""} &middot; {s.knowledge}% known
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </DialogFrame>
  );
}

export function TextDialog({ system, store }: { system: string; store: Store }) {
  // useState (not a plain closure variable): MainScreen re-renders on every store change
  // (e.g. a toast elsewhere auto-dismissing), which would otherwise reset an unstated
  // local variable and silently drop whatever the player had typed.
  const [text, setText] = useState("");
  return (
    <DialogFrame title={`Message to ${system}`} onClose={() => store.closeDialog()}>
      <textarea
        class="message-textarea"
        rows={5}
        placeholder="Message content (may be left empty)"
        value={text}
        onInput={(e) => setText((e.target as HTMLTextAreaElement).value)}
      />
      <div class="modal-actions">
        <button onClick={() => store.closeDialog()}>Cancel</button>
        <button class="primary" onClick={() => store.submitText(text)}>
          Send
        </button>
      </div>
    </DialogFrame>
  );
}

export function TechDialog({ view, store }: { view: ViewState; store: Store }) {
  const byTier = new Map<number, typeof view.technologies.available>();
  for (const tech of view.technologies.available) {
    const list = byTier.get(tech.tier) ?? [];
    list.push(tech);
    byTier.set(tech.tier, list);
  }
  const tiers = [...byTier.keys()].sort((a, b) => a - b);
  return (
    <DialogFrame title="Research a technology" onClose={() => store.closeDialog()}>
      {tiers.length === 0 ? (
        <p class="empty">No new technologies available to research.</p>
      ) : (
        tiers.map((tier) => (
          <div key={tier} class="tech-tier">
            <h3>Tier {tier}</h3>
            <ul class="picker-list">
              {(byTier.get(tier) ?? []).map((tech) => (
                <li key={tech.id}>
                  <button class="picker-row tech-row" onClick={() => store.pickTech(tech.id)}>
                    <span class="picker-name">
                      {tech.name} ({tech.cost} RP)
                    </span>
                    <span class="picker-meta">{tech.description}</span>
                    {tech.year_context && <span class="picker-meta tech-year">{tech.year_context}</span>}
                    {tech.locked && <span class="tech-locked">LOCKED: {tech.locked}</span>}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ))
      )}
    </DialogFrame>
  );
}

export function ThreatDialog({ view, store }: { view: ViewState; store: Store }) {
  return (
    <DialogFrame title="Defend against which threat?" onClose={() => store.closeDialog()}>
      {view.threats.length === 0 ? (
        <p class="empty">No active threats.</p>
      ) : (
        <ul class="picker-list">
          {view.threats.map((t) => (
            <li key={t.index}>
              <button class="picker-row" onClick={() => store.pickThreat(t.index - 1)}>
                <span class="picker-name">
                  {t.type_label} from {t.source}
                </span>
                <span class="picker-meta">
                  ETA {t.eta} gen(s) &middot; defense {t.defense_pct}%
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </DialogFrame>
  );
}

const DEFENSE_OPTIONS = [
  { id: "emergency" as const, label: "Emergency Defense Protocol", detail: "All Action Points, 50% damage reduction" },
  { id: "evacuate" as const, label: "Evacuate Critical Infrastructure", detail: "1 AP, 30% damage reduction" },
  { id: "diplomacy" as const, label: "Attempt Diplomatic Contact", detail: "1 AP, small chance to abort the attack" },
];

export function DefenseDialog({ store }: { store: Store }) {
  return (
    <DialogFrame title="Choose a defensive action" onClose={() => store.closeDialog()}>
      <ul class="picker-list">
        {DEFENSE_OPTIONS.map((option) => (
          <li key={option.id}>
            <button class="picker-row" onClick={() => store.pickDefense(option.id)}>
              <span class="picker-name">{option.label}</span>
              <span class="picker-meta">{option.detail}</span>
            </button>
          </li>
        ))}
      </ul>
    </DialogFrame>
  );
}

/** The `v` shortcut: pick a system to open its dossier (no engine call, just navigation). */
export function DossierPickerDialog({ view, store }: { view: ViewState; store: Store }) {
  return (
    <DialogFrame title="View system dossier" onClose={() => store.closeDialog()}>
      {view.systems.length === 0 ? (
        <p class="empty">No systems catalogued yet.</p>
      ) : (
        <ul class="picker-list">
          {view.systems.map((s) => (
            <li key={s.name}>
              <button class="picker-row" onClick={() => store.openDossier(s.name)}>
                <span class="picker-name">{s.name}</span>
                <span class="picker-meta">
                  {s.distance} LY{s.spectral_type ? `, ${s.spectral_type}` : ""} &middot; {s.knowledge}% known
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </DialogFrame>
  );
}

export function EventDialog({ view, store }: { view: ViewState; store: Store }) {
  const event = view.pending_event;
  // The engine can drop the pending event while this dialog is open (answering it elsewhere,
  // loading a save). Closing from the render body would re-enter the store mid-render, so the
  // render just yields nothing and the close happens in an effect afterwards.
  useEffect(() => {
    if (!event) store.closeDialog();
  }, [event, store]);
  if (!event) return null;
  return (
    <DialogFrame title={event.name} onClose={() => store.closeDialog()}>
      <p class="dialog-hint">{event.description}</p>
      <ul class="picker-list">
        {event.choices.map((choice, i) => (
          <li key={i}>
            <button class="picker-row" onClick={() => void store.respondEvent(i)}>
              <span class="picker-name">{choice.name}</span>
              <span class="picker-meta">{choice.description}</span>
            </button>
          </li>
        ))}
      </ul>
    </DialogFrame>
  );
}
