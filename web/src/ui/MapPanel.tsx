/**
 * The Preact wrapper around `scene/StarMap.ts`: it owns the DOM node the renderer lives in,
 * feeds the map every `ViewState` the store produces, and draws the flat UI that sits on top
 * of the canvas (toolbar, legend, the selected-system card, the systems list overlay).
 *
 * Everything shown here comes from `ViewState.systems[]`; the map never invents a fact the
 * engine did not state (docs/reference/web_contract.md 6).
 */
import { useEffect, useRef, useState } from "preact/hooks";
// `StarMap` pulls in Three.js (~600 kB), which nothing before the main screen needs, so it is
// imported for its type only and fetched with a dynamic import() when this panel mounts. Vite
// splits it into its own chunk; `scene/coords` is a handful of pure functions with no imports
// of its own, so it stays static.
import type { StarMap } from "../scene/StarMap";
import { formatDistance, formatYear, observedAsOf } from "../scene/coords";
import { lastObservation, messageFateText } from "../messageFate";
import type { Store } from "../store";
import type { ActionId, ActionSpec, StarSystem, ViewState } from "../types";
import { SystemsPanel } from "./SystemsPanel";

function excerpt(text: string, max = 120): string {
  return text.length <= max ? text : `${text.slice(0, max - 3)}...`;
}

/** The action bar's spec for one id, or null when the engine is not offering it now. */
function specFor(view: ViewState, id: ActionId): ActionSpec | null {
  return view.actions.find((action) => action.id === id) ?? null;
}

function CardAction({
  spec,
  system,
  store,
  label,
}: {
  spec: ActionSpec | null;
  system: string;
  store: Store;
  label: string;
}) {
  if (!spec) return null;
  return (
    <button
      class="map-card-action"
      disabled={store.state.busy}
      onClick={() => store.startActionForSystem(spec, system)}
      title={spec.cost}
    >
      {label}
    </button>
  );
}

/** The compact card for whichever star is selected; the map's answer to a dossier teaser. */
function SelectedCard({ system, view, store }: { system: StarSystem; view: ViewState; store: Store }) {
  const lastResponse = system.responses[system.responses.length - 1];
  const lastMessage = system.messages_sent[system.messages_sent.length - 1];
  const lastChange = lastObservation(system.observations);
  return (
    <section class="map-card" data-system={system.name}>
      <div class="map-card-head">
        <span class="map-card-name">{system.name}</span>
        <button class="map-card-close" aria-label="Clear selection" onClick={() => store.selectSystem(null)}>
          ×
        </button>
      </div>
      <p class="map-card-meta">
        {formatDistance(system.distance)} &middot; {system.spectral_type ?? "type unknown"} &middot;{" "}
        {system.knowledge}% known
      </p>
      <p class="map-card-meta map-card-observed">{observedAsOf(system.observed_year, system.distance)}</p>
      {lastChange && (
        <p class="map-card-meta map-card-change">last change seen: {formatYear(lastChange.year)}</p>
      )}
      <p class="map-card-description">{system.description || "Nothing studied yet."}</p>
      {lastResponse && <p class="map-card-reply">&ldquo;{excerpt(lastResponse)}&rdquo;</p>}
      {system.next_response_gen !== null && (
        <p class="map-card-meta">Next reply expected: Generation {system.next_response_gen}</p>
      )}
      {lastMessage && (
        <p class="map-card-meta map-card-fate" data-fate={lastMessage.fate}>
          {messageFateText(lastMessage)}
        </p>
      )}
      <div class="map-card-actions">
        <button class="map-card-action" onClick={() => store.openDossier(system.name)}>
          Dossier
        </button>
        <CardAction spec={specFor(view, "send_message")} system={system.name} store={store} label="Send message" />
        <CardAction spec={specFor(view, "focus_research")} system={system.name} store={store} label="Focus research" />
      </div>
    </section>
  );
}

export function MapPanel({ view, store }: { view: ViewState; store: Store }) {
  const hostRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<StarMap | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Flips once the scene chunk has loaded and the map exists; the update effects below wait
  // on it so the first `view` is pushed into the map the moment it is there.
  const [ready, setReady] = useState(false);

  const { selectedSystem, mapScale, showSystemList, reduceEffects, lastEvents } = store.state;

  // One StarMap for the lifetime of the main screen; it owns the WebGL context. Loading the
  // module and constructing it are the same failure path: a chunk that will not load and a
  // browser without WebGL both end in the list-overlay fallback below.
  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    let cancelled = false;
    void (async () => {
      try {
        const { StarMap } = await import("../scene/StarMap");
        if (cancelled) return;
        mapRef.current = new StarMap(host, {
          onSelect: (name) => store.selectSystem(name),
          onAutoReduce: () => {
            store.toggleReduceEffects(true);
            store.showToast("The map was running slowly, so effects were reduced. Turn them back on in the toolbar.");
          },
        });
        setReady(true);
      } catch (cause: unknown) {
        // No WebGL (a locked-down browser, a headless run without a GPU) or no chunk (an
        // offline first load): the list overlay is the fallback, and the rest of the HUD is
        // unaffected.
        if (cancelled) return;
        setError(cause instanceof Error ? cause.message : String(cause));
        store.toggleSystemList(true);
      }
    })();
    return () => {
      cancelled = true;
      setReady(false);
      mapRef.current?.dispose();
      mapRef.current = null;
    };
  }, [store]);

  // Every state change the map cares about, in one diffing call. `view.generation` is what
  // starts the 1.5 s glide of scene time; everything animated is a function of it.
  useEffect(() => {
    mapRef.current?.update({
      generation: view.generation,
      systems: view.systems,
      threats: view.threats,
      broadcastRadius: view.status.broadcast_radius,
      genesisWorlds: view.genesis.worlds,
      selected: selectedSystem,
      scale: mapScale,
      reduced: reduceEffects,
      reachLy: view.catalog.reach_ly,
    });
  }, [ready, view, selectedSystem, mapScale, reduceEffects]);

  // The flashes for the last action's events, after the state above is in place so every
  // star the events name already has a position. `lastEvents` is a fresh array per
  // `perform()`, so this fires once per action and never replays an old batch.
  useEffect(() => {
    if (lastEvents.length > 0) mapRef.current?.playEvents(lastEvents);
  }, [ready, lastEvents]);

  const selected = selectedSystem ? view.systems.find((s) => s.name === selectedSystem) : undefined;

  return (
    <section class="panel star-map" data-scale={mapScale} data-selected={selectedSystem ?? ""}>
      <div class="star-map-toolbar">
        <h2 class="star-map-title">Star map</h2>
        <div class="star-map-buttons">
          <button onClick={() => mapRef.current?.home()} title="Reset the camera">
            Home
          </button>
          <button
            disabled={!selected}
            onClick={() => mapRef.current?.focus(selectedSystem)}
            title="Fly to the selected star"
          >
            Focus
          </button>
          <button
            onClick={() => store.toggleScale()}
            title={
              mapScale === "compressed"
                ? "Radii are compressed logarithmically so 4 LY and 160 LY both fit"
                : "Radii are proportional to distance"
            }
          >
            Scale: {mapScale === "compressed" ? "compressed" : "true"}
          </button>
          <button
            onClick={() => store.toggleReduceEffects()}
            title={
              reduceEffects
                ? "Nebula and event flashes are off; light spheres, fleets and the leakage front still animate"
                : "Turn off the nebula and the event flashes"
            }
          >
            Effects: {reduceEffects ? "reduced" : "full"}
          </button>
          <button class={showSystemList ? "primary" : undefined} onClick={() => store.toggleSystemList()}>
            List
          </button>
        </div>
      </div>

      <div class="star-map-viewport">
        <div class="star-map-host" ref={hostRef} />
        {!ready && !error && <p class="star-map-loading">Loading star map&hellip;</p>}
        {error && (
          <p class="star-map-error">
            The 3D map could not start ({error}). Use the List panel instead.
          </p>
        )}
        <p class="star-map-legend">
          {view.catalog.known} of {view.catalog.total} catalogued &middot; rings at 5 / 10 / 20 / 50 / 100 LY &middot;
          cyan = our signal, warm = a reply, red = a fleet
          {view.catalog.reach_ly !== null && (
            <> &middot; dashed ring = detection reach ({Math.round(view.catalog.reach_ly)} LY)</>
          )}
          . Far answers arrive to descendants, not to whoever sent them: a reply from 100 LY takes 8
          generations.
        </p>
        {selected && <SelectedCard system={selected} view={view} store={store} />}
        {showSystemList && (
          <div class="star-map-list">
            <SystemsPanel view={view} store={store} />
          </div>
        )}
      </div>
    </section>
  );
}
