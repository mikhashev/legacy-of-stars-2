import { useEffect } from "preact/hooks";
import type { Store } from "../store";
import type { ViewState } from "../types";
import { Header } from "./Header";
import { StatusPanel } from "./StatusPanel";
import { MapPanel } from "./MapPanel";
import { ThreatsPanel } from "./ThreatsPanel";
import { ActionsPanel, assignKeys } from "./ActionsPanel";
import { EventLog } from "./EventLog";
import {
  DefenseDialog,
  DossierPickerDialog,
  EventDialog,
  SystemDialog,
  TechDialog,
  TextDialog,
  ThreatDialog,
} from "./Dialogs";
import { DossierModal } from "./DossierModal";
import { MenuModal } from "./MenuModal";
import { HelpModal } from "./HelpModal";
import { SummaryModal } from "./SummaryModal";
import { EventModal } from "./EventModal";
import { DoctrineModal } from "./DoctrineModal";
import { Toast } from "./Toast";

/** True while a text input/textarea somewhere has focus, so shortcut keys don't fight typing. */
function isTyping(): boolean {
  const el = document.activeElement;
  return !!el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA");
}

function ProgramMessage({ text }: { text: string }) {
  if (!text) return null;
  return (
    <section class="panel program-message">
      <h2>Program message</h2>
      <pre>{text}</pre>
    </section>
  );
}

export function MainScreen({ view, store }: { view: ViewState; store: Store }) {
  const state = store.state;

  // Registered once: the handler reads `store.state` when the key is pressed rather than
  // closing over a snapshot. Re-registering on every state change would leave a stale
  // listener for the frame between a store update and Preact running effects again - long
  // enough to swallow the very next keystroke (Escape right after closing a dialog).
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const s = store.state;
      if (isTyping()) return;
      const key = e.key.toLowerCase();
      if (key === "escape") {
        // Closes whatever is currently on top; only clears the map selection when nothing
        // else is open. The doctrine choice cannot be escaped - it has no cancel path in the
        // engine either - so it is deliberately not in this list.
        if (s.dialog) {
          store.closeDialog();
        } else if (s.modalEvent) {
          store.dismissModal();
        } else if (s.summaryResult) {
          store.closeSummary();
        } else if (s.showHelp) {
          store.toggleHelp(false);
        } else {
          store.selectSystem(null);
        }
        return;
      }
      // Everything else needs a clear screen: no dialog/modal on top, and not mid-doctrine.
      if (s.dialog || s.modalEvent || s.showHelp || s.summaryResult || s.pendingDoctrine || s.busy) return;
      if (key === "v") {
        // The dossier of whatever is selected on the map, or the picker if nothing is.
        if (s.selectedSystem) store.openDossier(s.selectedSystem);
        else store.openDossierPicker();
        return;
      }
      if (key === "s") {
        void store.quickSave();
        return;
      }
      if (key === "h" || key === "?") {
        store.toggleHelp(true);
        return;
      }
      if (key === "6") {
        store.openMenu();
        return;
      }
      const keyed = assignKeys(s.view?.actions ?? []);
      const match = keyed.find((k) => k.key === key);
      if (match) store.openAction(match.spec);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [store]);

  return (
    <main class="main-screen">
      <Header view={view} />
      <div class="main-layout">
        <div class="main-column main-column-left">
          <StatusPanel view={view} />
          <ActionsPanel view={view} store={store} />
          <ThreatsPanel view={view} />
          <ProgramMessage text={state.message} />
        </div>
        <div class="main-column main-column-center">
          <MapPanel view={view} store={store} />
        </div>
        <div class="main-column main-column-right">
          <EventLog events={state.events} />
        </div>
      </div>

      {/* Dialogs driven by ActionSpec.needs (web_contract.md 2/3). */}
      {state.dialog?.kind === "system" && <SystemDialog view={view} spec={state.dialog.spec} store={store} />}
      {state.dialog?.kind === "text" && <TextDialog system={state.dialog.system} store={store} />}
      {state.dialog?.kind === "tech" && <TechDialog view={view} store={store} />}
      {state.dialog?.kind === "threat" && <ThreatDialog view={view} store={store} />}
      {state.dialog?.kind === "defense" && <DefenseDialog store={store} />}
      {state.dialog?.kind === "event" && <EventDialog view={view} store={store} />}
      {state.dialog?.kind === "dossier" && <DossierModal system={state.dialog.system} view={view} store={store} />}
      {state.dialog?.kind === "dossier-picker" && <DossierPickerDialog view={view} store={store} />}
      {state.dialog?.kind === "menu" && <MenuModal view={view} store={store} />}

      {/* Big events (web_contract.md 5, MODAL_EVENT_KINDS): one modal at a time. */}
      {state.modalEvent && <EventModal event={state.modalEvent} store={store} />}

      {state.showHelp && <HelpModal store={store} />}
      {state.summaryResult && <SummaryModal store={store} result={state.summaryResult} />}

      {/* The doctrine choice blocks everything else (web_contract.md 4). */}
      {state.pendingDoctrine && <DoctrineModal needs={state.pendingDoctrine} store={store} />}

      {state.toast && <Toast text={state.toast} store={store} />}
    </main>
  );
}
