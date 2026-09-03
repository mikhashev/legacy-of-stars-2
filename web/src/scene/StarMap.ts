/**
 * The star map: Earth at the origin, the known systems around it, orientation rings, the
 * shader backdrop and (since W4) the animated layer in `effects.ts`. This class owns the
 * WebGL renderer, the scene, the camera, OrbitControls and the CSS2D label layer;
 * `ui/MapPanel.tsx` is the only thing that constructs it.
 *
 * How the animation works (W4):
 *
 * - **Scene time.** `t` is a continuous generation number. A state update does not jump the
 *   map to the new generation: `t` glides there over `SCENE_TIME_MS` with an ease-in-out, and
 *   every radius and position in `effects.ts` is a function of `t` (see `timeline.ts`).
 * - **Render on demand.** Nothing renders unless something changed (`requestRender`), so an
 *   idle page costs no GPU. While the glide, a flash, a pulsing fleet or a camera flight is in
 *   flight the loop renders every frame and the shared `Clock` advances; once they finish the
 *   map goes back to sleep, which is also why the background twinkle holds still when idle.
 * - **Groups.** Every system is a `Group` at the star's position and Earth is `earthGroup`, so
 *   effects only ever need a name to find a point in space (`positionOf`).
 * - **Budget.** Star sprites and decorations plus the animated layer stay under ~150 objects;
 *   `devicePixelRatio` is capped at 2, and if frame time stays above `SLOW_FRAME_MS` for
 *   `SLOW_FRAME_WINDOW_MS` the map asks the store to switch "Reduce effects" on.
 */
import {
  AdditiveBlending,
  BufferGeometry,
  CanvasTexture,
  Clock,
  Color,
  Float32BufferAttribute,
  Group,
  LineBasicMaterial,
  LineDashedMaterial,
  LineLoop,
  Mesh,
  MeshBasicMaterial,
  PerspectiveCamera,
  Scene,
  SphereGeometry,
  Sprite,
  SpriteMaterial,
  type Texture,
  Vector3,
  WebGLRenderer,
} from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { CSS2DObject, CSS2DRenderer } from "three/examples/jsm/renderers/CSS2DRenderer.js";
import type { GameEvent, GenesisWorld, StarSystem, Threat } from "../types";
import {
  EDGE_RADIUS,
  RING_DISTANCES_LY,
  type ScaleMode,
  formatDistance,
  isBeyondRim,
  positionForSystem,
  radiusFor,
} from "./coords";
import {
  type DebugArk,
  type DebugFleet,
  type DebugMessageLine,
  type DebugSphere,
  SceneEffects,
} from "./effects";
import { CONTACTED_COLOR, DELIVERED_COLOR, MOOD_COLOR, SEEDED_COLOR, moodFor, styleFor } from "./palette";
import { type Nebula, type Starfield, createNebula, createStarfield } from "./starfield";
import { easeInOut } from "./timeline";

/** What the map needs out of the store; a subset of `ViewState` plus the view toggles. */
export interface MapViewState {
  /** `ViewState.generation`: the generation scene time glides to. */
  generation: number;
  systems: StarSystem[];
  threats: Threat[];
  /** `ViewState.status.broadcast_radius`, in light-years. */
  broadcastRadius: number;
  /** `ViewState.genesis.worlds`. */
  genesisWorlds: GenesisWorld[];
  selected: string | null;
  scale: ScaleMode;
  /** The MapPanel toolbar's "Reduce effects": no nebula, no flashes. */
  reduced: boolean;
  /** `ViewState.catalog.reach_ly`: how far the telescopes resolve a new star. `null` hides
   *  the reach ring (the whole catalogue is already in range). */
  reachLy: number | null;
}

export interface StarMapOptions {
  /** A star was clicked, or empty space was (null). */
  onSelect(name: string | null): void;
  /** The pointer moved onto or off a star. */
  onHover?(name: string | null): void;
  /** Frame time stayed over budget: the map is asking for "Reduce effects" to be switched on. */
  onAutoReduce?(): void;
}

/** The read-only view of the scene `window.__losMap` exposes in dev and `?debug=1` builds. */
export interface MapDebug {
  map: StarMap;
  /** Continuous generation the scene is drawn at. */
  sceneTime(): number;
  /** The generation it is gliding towards. */
  targetGeneration(): number;
  /** True while the glide is still running. */
  animating(): boolean;
  /** Distinct scene-time values sampled since the glide began, oldest first. */
  samples(): number[];
  /** Message and reply spheres currently in the scene. */
  spheres(): DebugSphere[];
  /** Routes of the transmissions and replies in flight, with their pulses and labels. */
  messageLines(): DebugMessageLine[];
  /** Systems wearing the "we have spoken to them" ring: a message of ours has landed. */
  messageRings(): string[];
  fleets(): DebugFleet[];
  /** Genesis arks in flight or landed (the colony glow is `stage >= 1`, i.e. `landed`). */
  arks(): DebugArk[];
  /** The leakage front in light-years at the current scene time. */
  leakageLy(): number;
  /** Names of the flashes still playing. */
  flashes(): string[];
  /** Systems currently wearing the map's brief "no reply" tag (plan §8). */
  unansweredTags(): string[];
  /** The detection reach ring's current radius in LY, or null while hidden (plan §8). */
  reachLy(): number | null;
  /** Objects in the animated layer, for the performance budget. */
  objectCount(): number;
  /** Rolling mean frame time in milliseconds while the map was rendering. */
  frameMs(): number;
  reduced(): boolean;
}

declare global {
  interface Window {
    /** Set by `StarMap` in non-production builds and whenever the URL carries `?debug=1`. */
    __losMap?: MapDebug;
  }
}

/** Hard ceiling on drawn systems (the catalogue is 94 stars plus the WOW! source). */
const MAX_SYSTEMS = 100;

/** World-unit diameter of an average main-sequence star sprite (W4: 1.6x the W3 value of 5). */
const BASE_STAR_SIZE = 8;

const CAMERA_FOV = 50;
/** How much of the rim the default framing leaves as margin. */
const HOME_MARGIN = 1.1;
/** Default elevation above the plane of the rings, in degrees (W4 raised it from ~10). */
const HOME_ELEVATION_DEG = 35;
const FLIGHT_MS = 700;

/** How long the map takes to glide from one generation to the next. */
const SCENE_TIME_MS = 1500;
/** A star coming out of the fog fades in over this long. */
const DISCOVERY_FADE_MS = 1000;

/** Frame time (ms) above which the map is considered to be struggling. */
const SLOW_FRAME_MS = 33;
/** How long it must stay there before effects are reduced automatically. */
const SLOW_FRAME_WINDOW_MS = 2000;
/** How many scene-time samples the debug hook keeps per glide. */
const MAX_TIME_SAMPLES = 240;
/** Click slop: a pointer that moved further than this was a drag, not a click. */
const CLICK_SLOP_PX = 4;
/** Pick radius around the pointer, in CSS pixels. */
const PICK_RADIUS_PX = 18;

interface StarEntry {
  name: string;
  group: Group;
  core: Sprite;
  label: CSS2DObject;
  labelEl: HTMLDivElement;
  distance: number;
  /** Everything the decorations depend on; a change here rebuilds them. */
  signature: string;
  /** Halo / ring / tick sprites, rebuilt as a set when `signature` changes. */
  decorations: Sprite[];
  /** The opacity this star has at rest; the discovery fade scales it. */
  baseOpacity: number;
  /** `performance.now()` when the `system_discovered` fade-in started, or null. */
  fadeStart: number | null;
}

interface Flight {
  fromCamera: Vector3;
  toCamera: Vector3;
  fromTarget: Vector3;
  toTarget: Vector3;
  start: number;
}

/* ---------------------------------------------------------------- textures */

function discTexture(): CanvasTexture {
  const size = 128;
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext("2d");
  if (ctx) {
    const gradient = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
    gradient.addColorStop(0, "rgba(255,255,255,1)");
    gradient.addColorStop(0.18, "rgba(255,255,255,1)");
    gradient.addColorStop(0.34, "rgba(255,255,255,0.55)");
    gradient.addColorStop(0.6, "rgba(255,255,255,0.12)");
    gradient.addColorStop(1, "rgba(255,255,255,0)");
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, size, size);
  }
  return new CanvasTexture(canvas);
}

function ringTexture(innerFraction: number, outerFraction: number): CanvasTexture {
  const size = 128;
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext("2d");
  if (ctx) {
    const gradient = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
    gradient.addColorStop(0, "rgba(255,255,255,0)");
    gradient.addColorStop(Math.max(0, innerFraction - 0.06), "rgba(255,255,255,0)");
    gradient.addColorStop(innerFraction, "rgba(255,255,255,0.85)");
    gradient.addColorStop(outerFraction, "rgba(255,255,255,0.85)");
    gradient.addColorStop(Math.min(1, outerFraction + 0.08), "rgba(255,255,255,0)");
    gradient.addColorStop(1, "rgba(255,255,255,0)");
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, size, size);
  }
  return new CanvasTexture(canvas);
}

/**
 * Whether to publish `window.__losMap`. The URL flag is what `tests/animation.spec.ts` uses,
 * because Playwright runs against `vite preview` - a production build, where `import.meta.env`
 * would otherwise switch the hook off.
 */
function debugEnabled(): boolean {
  if (import.meta.env.MODE !== "production") return true;
  try {
    return new URLSearchParams(window.location.search).get("debug") === "1";
  } catch {
    return false;
  }
}

/* ---------------------------------------------------------------- the map */

export class StarMap {
  private readonly host: HTMLElement;
  private readonly options: StarMapOptions;

  private readonly renderer: WebGLRenderer;
  private readonly labelRenderer: CSS2DRenderer;
  private readonly scene = new Scene();
  private readonly camera: PerspectiveCamera;
  private readonly controls: OrbitControls;

  /** Earth's anchor: W4 hangs the leakage-front sphere and message spheres here. */
  readonly earthGroup = new Group();
  /** Parent of every `StarEntry.group`. */
  private readonly starsGroup = new Group();
  private readonly ringsGroup = new Group();
  private readonly starfield: Starfield;
  private readonly nebula: Nebula;
  /** The animated layer: light spheres, fleets, the leakage front, arks, flashes. */
  private readonly effects: SceneEffects;
  private earthGlobe!: Mesh<SphereGeometry, MeshBasicMaterial>;
  private earthGlow!: Sprite;
  private earthLabel!: CSS2DObject;

  private readonly textures: Texture[] = [];
  private readonly starTexture: CanvasTexture;
  private readonly glowTexture: CanvasTexture;
  private readonly haloTexture: CanvasTexture;
  private readonly ringMarkTexture: CanvasTexture;
  /** The thin ring a star wears once a transmission of ours has actually got there. */
  private readonly deliveredTexture: CanvasTexture;

  private readonly entries = new Map<string, StarEntry>();
  private readonly ringLoops: {
    loop: LineLoop<BufferGeometry, LineBasicMaterial>;
    label: CSS2DObject;
    ly: number;
  }[] = [];

  /** The dashed "detection reach" ring (plan §8): `catalog.reach_ly`, hidden when null. */
  private reachRing!: LineLoop<BufferGeometry, LineDashedMaterial>;
  private reachLabel!: CSS2DObject;
  private reachLabelEl!: HTMLDivElement;
  private reachLy: number | null = null;

  private scale: ScaleMode = "compressed";
  /** The generation of the last `ViewState` applied (scene time glides towards it). */
  private stateGeneration = 1;
  private selected: string | null = null;
  private hovered: string | null = null;

  private dirty = true;
  private raf = 0;
  private started = false;
  private flight: Flight | null = null;
  private disposed = false;

  /* -------------------------------------------------------------- scene time */

  private readonly clock = new Clock();
  /** Continuous generation the scene is drawn at. */
  private sceneTime = 1;
  private timeFrom = 1;
  private timeTo = 1;
  private timeStart = 0;
  private timeAnimating = false;
  /** False until the first `update()`, which seats scene time without animating. */
  private hasState = false;
  private timeSamples: number[] = [];

  private reduced = false;
  /** Rolling mean frame time, in milliseconds, over rendered frames. */
  private frameMs = 16;
  private lastFrameAt = 0;
  private slowSince = 0;
  private autoReduced = false;

  private readonly resizeObserver: ResizeObserver;
  private pointerDown: { x: number; y: number } | null = null;

  private viewWidth = 1;
  private viewHeight = 1;
  /** Measured label boxes, so the declutter pass does not touch the DOM every frame. */
  private readonly labelSizes = new WeakMap<HTMLElement, { w: number; h: number }>();
  private labelSizesStale = true;

  constructor(host: HTMLElement, options: StarMapOptions) {
    this.host = host;
    this.options = options;

    this.renderer = new WebGLRenderer({ antialias: true, alpha: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.domElement.classList.add("star-map-canvas");
    host.appendChild(this.renderer.domElement);

    this.labelRenderer = new CSS2DRenderer();
    this.labelRenderer.domElement.classList.add("star-map-labels");
    this.labelRenderer.domElement.style.position = "absolute";
    this.labelRenderer.domElement.style.inset = "0";
    this.labelRenderer.domElement.style.pointerEvents = "none";
    host.appendChild(this.labelRenderer.domElement);

    this.camera = new PerspectiveCamera(CAMERA_FOV, 1, 0.5, 4000);
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    // Damping would need a render every frame while it settles; without it the map is still
    // smooth (drag maps straight to rotation) and an idle page issues no draw calls at all.
    this.controls.enableDamping = false;
    this.controls.minDistance = 12;
    this.controls.maxDistance = 900;
    this.controls.addEventListener("change", this.requestRender);

    this.starTexture = discTexture();
    this.glowTexture = discTexture();
    this.haloTexture = ringTexture(0.3, 0.4);
    this.ringMarkTexture = ringTexture(0.36, 0.44);
    this.deliveredTexture = ringTexture(0.46, 0.5);
    this.textures.push(this.starTexture, this.glowTexture, this.haloTexture, this.ringMarkTexture,
                       this.deliveredTexture);

    this.starfield = createStarfield(this.renderer.getPixelRatio());
    this.nebula = createNebula();
    this.effects = new SceneEffects({
      positionOf: (name) => this.positionOf(name),
      radiusOf: (ly) => radiusFor(ly, this.scale),
      beyondRim: (ly) => isBeyondRim(ly, this.scale),
      rimRadius: () => EDGE_RADIUS,
      requestRender: this.requestRender,
    });
    this.scene.add(
      this.nebula,
      this.starfield,
      this.ringsGroup,
      this.earthGroup,
      this.starsGroup,
      this.effects.root,
    );

    this.buildEarth();
    this.buildRings();
    this.buildReachRing();
    this.applyRingScale();

    this.resizeObserver = new ResizeObserver(() => this.resize());
    this.resizeObserver.observe(host);
    this.resize();
    this.home();
    this.started = true;

    this.renderer.domElement.addEventListener("pointerdown", this.onPointerDown);
    this.renderer.domElement.addEventListener("pointerup", this.onPointerUp);
    this.renderer.domElement.addEventListener("pointermove", this.onPointerMove);
    this.renderer.domElement.addEventListener("pointerleave", this.onPointerLeave);

    if (debugEnabled()) window.__losMap = this.debug();

    this.raf = requestAnimationFrame(this.tick);
  }

  /** The `window.__losMap` view; built once and handed out in dev/`?debug=1` builds only. */
  private debug(): MapDebug {
    return {
      map: this,
      sceneTime: () => this.sceneTime,
      targetGeneration: () => this.timeTo,
      animating: () => this.timeAnimating,
      samples: () => [...this.timeSamples],
      spheres: () => this.effects.debugSpheres(),
      messageLines: () => this.effects.debugMessageLines(),
      messageRings: () => this.debugMessageRings(),
      fleets: () => this.effects.debugFleets(),
      arks: () => this.effects.debugArks(),
      leakageLy: () => this.effects.debugLeakageLy(),
      flashes: () => this.effects.debugFlashes(),
      unansweredTags: () => this.effects.debugUnansweredTags(),
      reachLy: () => (this.reachRing.visible ? this.reachLy : null),
      objectCount: () => this.effects.objectCount(),
      frameMs: () => this.frameMs,
      reduced: () => this.reduced,
    };
  }

  /* ------------------------------------------------------------ construction */

  private buildEarth(): void {
    const globe = new Mesh(new SphereGeometry(1.5, 24, 16), new MeshBasicMaterial({ color: 0x4e8fd4 }));
    globe.name = "earth-globe";

    const glow = new Sprite(
      new SpriteMaterial({
        map: this.glowTexture,
        color: new Color(0x6fb2ff),
        transparent: true,
        opacity: 0.55,
        depthWrite: false,
        blending: AdditiveBlending,
      }),
    );
    glow.scale.setScalar(9);
    glow.name = "earth-glow";

    const el = document.createElement("div");
    el.className = "star-label star-label-earth";
    el.dataset["star"] = "Earth";
    el.textContent = "Earth";
    const label = new CSS2DObject(el);
    // center (0.5, 1) = the element's bottom edge sits on the point, i.e. above the star.
    label.center.set(0.5, 1);
    label.position.set(0, 3, 0);

    this.earthGroup.name = "earth";
    this.earthGroup.add(globe, glow, label);
    this.earthGlobe = globe;
    this.earthGlow = glow;
    this.earthLabel = label;
  }

  private buildRings(): void {
    // One unit circle in the y = 0 plane, scaled per ring; the rings are an orientation aid,
    // not data, so they are dim and never picked.
    const points: number[] = [];
    const segments = 128;
    for (let i = 0; i < segments; i += 1) {
      const a = (i / segments) * Math.PI * 2;
      points.push(Math.cos(a), 0, Math.sin(a));
    }
    const geometry = new BufferGeometry();
    geometry.setAttribute("position", new Float32BufferAttribute(points, 3));

    for (const ly of RING_DISTANCES_LY) {
      const loop = new LineLoop<BufferGeometry, LineBasicMaterial>(
        geometry,
        new LineBasicMaterial({ color: 0x2a3446, transparent: true, opacity: 0.9 }),
      );
      loop.name = `ring-${ly}`;

      const el = document.createElement("div");
      el.className = "star-map-ring-label";
      el.textContent = `${ly} LY`;
      const label = new CSS2DObject(el);
      // center (0, 0.5) = the text starts at the ring and is vertically centred on it.
      label.center.set(0, 0.5);

      this.ringsGroup.add(loop, label);
      this.ringLoops.push({ loop, label, ly });
    }
  }

  /** Rings and their labels follow whichever scale is active. */
  private applyRingScale(): void {
    for (const ring of this.ringLoops) {
      const r = radiusFor(ring.ly, this.scale);
      ring.loop.scale.setScalar(r);
      // Labels sit on the +x side of each ring, just outside it.
      ring.label.position.set(r, 0, 0);
    }
    this.applyReach(this.reachLy);
  }

  /**
   * The detection reach ring (plan §8): a dashed circle at `catalog.reach_ly`, so far stars
   * still in the fog read as "not yet in reach" rather than "not there". One unit circle,
   * shared geometry with the orientation rings; `LineDashedMaterial` needs its own
   * `computeLineDistances()` call once, which the plain rings' `LineBasicMaterial` does not.
   */
  private buildReachRing(): void {
    const points: number[] = [];
    const segments = 128;
    for (let i = 0; i < segments; i += 1) {
      const a = (i / segments) * Math.PI * 2;
      points.push(Math.cos(a), 0, Math.sin(a));
    }
    const geometry = new BufferGeometry();
    geometry.setAttribute("position", new Float32BufferAttribute(points, 3));
    const loop = new LineLoop<BufferGeometry, LineDashedMaterial>(
      geometry,
      new LineDashedMaterial({ color: 0x5fb0ff, transparent: true, opacity: 0.55, dashSize: 1.4, gapSize: 1.1 }),
    );
    loop.name = "reach-ring";
    loop.computeLineDistances();
    loop.visible = false;

    const el = document.createElement("div");
    el.className = "star-map-ring-label star-map-reach-label";
    const label = new CSS2DObject(el);
    // (0.5, 1): bottom-centred on its anchor point, the same convention `declutterLabels` uses
    // for star labels - it needs that to reason about the label's box when the reach label
    // joins the same declutter pass (plan §8 UI fix: it used to sit on the ring's +x side,
    // the same spot the orientation rings label themselves, and could land squarely on a
    // star's own label with nothing to push either of them apart).
    label.center.set(0.5, 1);
    label.visible = false;

    this.ringsGroup.add(loop, label);
    this.reachRing = loop;
    this.reachLabel = label;
    this.reachLabelEl = el;
  }

  /** Applies (or hides) the detection reach ring for the current `catalog.reach_ly`. */
  private applyReach(ly: number | null): void {
    this.reachLy = ly;
    if (ly === null) {
      this.reachRing.visible = false;
      this.reachLabel.visible = false;
      return;
    }
    const r = radiusFor(ly, this.scale);
    this.reachRing.scale.setScalar(r);
    this.reachRing.visible = true;
    this.reachLabelEl.textContent = `detection reach ${Math.round(ly)} LY`;
    // A fixed spot on the ring's far side from the home camera (-z), deliberately different
    // from the +x side the orientation rings label themselves on: real stars cluster all over
    // the ring in their actual sky directions, so parking this one label somewhere nothing else
    // is anchored to is most of the fix on its own; `declutterLabels` (which it now takes part
    // in, always yielding to a star) covers the rest.
    this.reachLabel.position.set(0, 0, -r);
    this.reachLabel.visible = true;
    this.labelSizesStale = true;
  }

  /* ------------------------------------------------------------ public API */

  /** Applies a new game state to the scene, adding/removing/refreshing systems by name. */
  update(view: MapViewState): void {
    if (this.disposed) return;

    const scaleChanged = view.scale !== this.scale;
    // Before the entries are refreshed: whether a star wears the "we have spoken to them"
    // ring depends on the generation the state describes, not on the gliding scene time.
    this.stateGeneration = view.generation;
    this.scale = view.scale;
    if (scaleChanged) this.applyRingScale();

    const systems = view.systems.slice(0, MAX_SYSTEMS);
    const seen = new Set<string>();

    for (const system of systems) {
      seen.add(system.name);
      const existing = this.entries.get(system.name);
      if (existing) this.refreshEntry(existing, system, scaleChanged);
      else this.entries.set(system.name, this.createEntry(system));
    }

    for (const [name, entry] of this.entries) {
      if (seen.has(name)) continue;
      this.destroyEntry(entry);
      this.entries.delete(name);
    }

    this.setReduced(view.reduced);
    this.setGeneration(view.generation);
    this.applyReach(view.reachLy);
    // The star groups are in place, so the animated layer can resolve every position it needs.
    this.effects.applyState({
      generation: view.generation,
      systems,
      threats: view.threats,
      broadcastRadius: view.broadcastRadius,
      genesisWorlds: view.genesisWorlds,
    });

    this.select(view.selected);
    this.requestRender();
  }

  /**
   * The events of one `perform()` call, in order. Every one of them is decoration: the map
   * would still be correct without them, which is why "Reduce effects" can drop them whole.
   */
  playEvents(events: readonly GameEvent[]): void {
    if (this.disposed || events.length === 0) return;
    if (!this.reduced) {
      for (const event of events) {
        if (event.kind !== "system_discovered") continue;
        const entry = this.entries.get(event.data.system);
        if (entry) entry.fadeStart = performance.now();
      }
    }
    this.effects.playEvents(events);
    this.requestRender();
  }

  /** "Reduce effects": drops the nebula and every flash, keeps all state-driven visuals. */
  setReduced(reduced: boolean): void {
    if (this.reduced === reduced) return;
    this.reduced = reduced;
    this.nebula.visible = !reduced;
    this.effects.setReduced(reduced);
    this.requestRender();
  }

  /**
   * Starts the glide of scene time towards `generation`. The first state to arrive seats the
   * clock outright - there is nothing to animate from when the map has just opened.
   */
  private setGeneration(generation: number): void {
    if (!this.hasState) {
      this.hasState = true;
      this.sceneTime = generation;
      this.timeFrom = generation;
      this.timeTo = generation;
      return;
    }
    if (generation === this.timeTo) return;
    this.timeFrom = this.sceneTime;
    this.timeTo = generation;
    this.timeStart = performance.now();
    this.timeAnimating = true;
    this.timeSamples = [];
    this.requestRender();
  }

  /** Systems the "we have spoken to them" ring is currently drawn on. */
  private debugMessageRings(): string[] {
    const names: string[] = [];
    for (const [name, entry] of this.entries) {
      if (entry.decorations.some((sprite) => sprite.material.map === this.deliveredTexture)) names.push(name);
    }
    return names;
  }

  /** Scene position of a system the map is drawing; `effects.ts` asks by name. */
  private positionOf(name: string): Vector3 | null {
    return this.entries.get(name)?.group.position ?? null;
  }

  /** Marks one system (or nothing) as selected; the caller owns the actual selection state. */
  select(name: string | null): void {
    if (this.selected === name) return;
    this.selected = name;
    this.applyLabelStates();
    this.requestRender();
  }

  /** Flies the camera to a system, keeping the current viewing direction. */
  focus(name: string | null): void {
    const entry = name ? this.entries.get(name) : null;
    if (!entry) return;
    const target = entry.group.position.clone();
    const offset = this.camera.position.clone().sub(this.controls.target);
    const distance = Math.max(this.controls.minDistance + 2, Math.min(offset.length(), 60));
    offset.setLength(distance);
    this.startFlight(target.clone().add(offset), target);
  }

  /** Resets the camera to the framing that fits the whole scene. */
  home(): void {
    const target = new Vector3(0, 0, 0);
    // Looking down on the plane of the rings rather than along it: at 35 degrees the ring
    // circles read as circles and the stars stop piling up on one line.
    const elevation = (HOME_ELEVATION_DEG * Math.PI) / 180;
    const distance = this.fitDistance();
    const position = new Vector3(0, Math.sin(elevation) * distance, Math.cos(elevation) * distance);
    if (!this.started) {
      // Called from the constructor: place the camera outright, no animation.
      this.camera.position.copy(position);
      this.controls.target.copy(target);
      this.controls.update();
      return;
    }
    this.startFlight(position, target);
  }

  /** Whether a WebGL context is alive; MapPanel shows a fallback when construction failed. */
  get canvas(): HTMLCanvasElement {
    return this.renderer.domElement;
  }

  dispose(): void {
    if (this.disposed) return;
    this.disposed = true;
    cancelAnimationFrame(this.raf);
    this.resizeObserver.disconnect();

    this.renderer.domElement.removeEventListener("pointerdown", this.onPointerDown);
    this.renderer.domElement.removeEventListener("pointerup", this.onPointerUp);
    this.renderer.domElement.removeEventListener("pointermove", this.onPointerMove);
    this.renderer.domElement.removeEventListener("pointerleave", this.onPointerLeave);
    this.controls.removeEventListener("change", this.requestRender);
    this.controls.dispose();

    for (const entry of this.entries.values()) this.destroyEntry(entry);
    this.entries.clear();

    for (const ring of this.ringLoops) {
      ring.loop.material.dispose();
      ring.label.element.remove();
    }
    // All rings share one geometry.
    this.ringLoops[0]?.loop.geometry.dispose();
    this.ringLoops.length = 0;

    this.reachRing.geometry.dispose();
    this.reachRing.material.dispose();
    this.reachLabelEl.remove();

    // Sprites share one module-level geometry inside three.js, so only the mesh's is ours.
    this.earthGlobe.geometry.dispose();
    this.earthGlobe.material.dispose();
    this.earthGlow.material.dispose();
    this.earthLabel.element.remove();
    this.earthGroup.clear();

    this.effects.dispose();
    this.starfield.geometry.dispose();
    this.starfield.material.dispose();
    this.nebula.geometry.dispose();
    this.nebula.material.dispose();
    for (const texture of this.textures) texture.dispose();
    if (window.__losMap?.map === this) delete window.__losMap;

    this.scene.clear();
    this.renderer.dispose();
    this.renderer.domElement.remove();
    this.labelRenderer.domElement.remove();
  }

  /* ------------------------------------------------------------ star entries */

  private signatureOf(system: StarSystem): string {
    return [
      system.spectral_type ?? "",
      system.knowledge,
      system.description,
      system.is_seeded ? "seeded" : "",
      system.contacted ? "contacted" : "",
      system.messages_sent.length,
      // Not the same thing as "a message was sent": the ring appears the generation the
      // light lands, which is a later state of the same unchanged message list.
      this.hasDeliveredMessage(system) ? "delivered" : "",
      system.distance,
    ].join("|");
  }

  /** True once at least one of our transmissions has reached this system. */
  private hasDeliveredMessage(system: StarSystem): boolean {
    return system.messages_sent.some((message) => message.arrival_gen <= this.stateGeneration);
  }

  private createEntry(system: StarSystem): StarEntry {
    const style = styleFor(system.spectral_type);
    const group = new Group();
    group.name = `system:${system.name}`;
    const p = positionForSystem(system, this.scale);
    group.position.set(p.x, p.y, p.z);

    const core = new Sprite(
      new SpriteMaterial({
        map: this.starTexture,
        color: new Color(style.color),
        transparent: true,
        depthWrite: false,
        blending: AdditiveBlending,
      }),
    );
    core.name = "core";
    group.add(core);

    const labelEl = document.createElement("div");
    // `star-label-system` marks the per-system labels apart from Earth's, for CSS and tests.
    labelEl.className = "star-label star-label-system";
    labelEl.dataset["star"] = system.name;
    // The CSS2D container is pointer-events: none, so labels opt back in and act as the
    // large, reliable click target (Playwright targets them by `data-star`).
    labelEl.style.pointerEvents = "auto";
    const nameEl = document.createElement("span");
    nameEl.className = "star-label-name";
    nameEl.textContent = system.name;
    const distEl = document.createElement("span");
    distEl.className = "star-label-distance";
    distEl.textContent = formatDistance(system.distance);
    labelEl.append(nameEl, distEl);
    labelEl.addEventListener("click", (event) => {
      event.stopPropagation();
      this.options.onSelect(system.name);
    });
    labelEl.addEventListener("pointerenter", () => this.setHovered(system.name));
    labelEl.addEventListener("pointerleave", () => this.setHovered(null));

    const label = new CSS2DObject(labelEl);
    label.center.set(0.5, 1);
    group.add(label);

    this.starsGroup.add(group);

    const entry: StarEntry = {
      name: system.name,
      group,
      core,
      label,
      labelEl,
      distance: system.distance,
      signature: "",
      decorations: [],
      baseOpacity: 1,
      fadeStart: null,
    };
    this.applyEntry(entry, system);
    return entry;
  }

  private refreshEntry(entry: StarEntry, system: StarSystem, scaleChanged: boolean): void {
    if (scaleChanged) {
      const p = positionForSystem(system, this.scale);
      entry.group.position.set(p.x, p.y, p.z);
    }
    if (this.signatureOf(system) !== entry.signature) this.applyEntry(entry, system);
  }

  /** (Re)builds everything about a star that depends on game state. */
  private applyEntry(entry: StarEntry, system: StarSystem): void {
    entry.signature = this.signatureOf(system);
    entry.distance = system.distance;

    for (const sprite of entry.decorations) {
      entry.group.remove(sprite);
      sprite.material.dispose();
    }
    entry.decorations.length = 0;

    const style = styleFor(system.spectral_type);
    const mood = moodFor(system.knowledge, system.description);
    const size = BASE_STAR_SIZE * style.size;

    entry.core.material.color.set(style.color);
    // knowledge 0 -> dim; anything the telescopes have actually studied -> normal.
    entry.baseOpacity = mood === "unknown" ? 0.6 : 1;
    entry.core.scale.setScalar(size);

    // A halo for what the description says about the inhabitants.
    if (mood === "extinct" || mood === "inhabited") {
      entry.decorations.push(this.addSprite(entry, this.haloTexture, MOOD_COLOR[mood], size * 2.4, 0.75));
    }
    // A ring for what our own programme has done there; contact outranks a seeded ark.
    if (system.contacted) {
      entry.decorations.push(this.addSprite(entry, this.ringMarkTexture, CONTACTED_COLOR, size * 3.2, 0.95));
    } else if (system.is_seeded) {
      entry.decorations.push(this.addSprite(entry, this.ringMarkTexture, SEEDED_COLOR, size * 3.2, 0.85));
    }
    // "We have spoken to them": a thin cyan ring, once one of our transmissions has actually
    // arrived. It is deliberately permanent - the light got there, and that cannot un-happen.
    // A message still in flight is not marked here at all; it is the dotted route and the
    // travelling pulse in `effects.ts` that say one is on its way.
    if (this.hasDeliveredMessage(system)) {
      entry.decorations.push(this.addSprite(entry, this.deliveredTexture, DELIVERED_COLOR, size * 4.0, 0.8));
    }

    entry.label.position.set(0, size * 0.75, 0);
    entry.labelEl.dataset["mood"] = mood;
    entry.labelEl.dataset["seeded"] = system.is_seeded ? "true" : "false";
    entry.labelEl.dataset["contacted"] = system.contacted ? "true" : "false";
    const distEl = entry.labelEl.querySelector(".star-label-distance");
    if (distEl) distEl.textContent = formatDistance(system.distance);
    this.labelSizesStale = true;
    this.applyLabelStates();
    this.applyEntryFade(entry, performance.now());
  }

  private addSprite(entry: StarEntry, map: Texture, color: number, size: number, opacity: number): Sprite {
    const sprite = new Sprite(
      new SpriteMaterial({
        map,
        color: new Color(color),
        transparent: true,
        opacity,
        depthWrite: false,
        blending: AdditiveBlending,
      }),
    );
    sprite.scale.setScalar(size);
    // Remembered so the discovery fade can scale it without losing the styled value.
    sprite.userData["baseOpacity"] = opacity;
    entry.group.add(sprite);
    return sprite;
  }

  /**
   * `system_discovered`: the star comes up out of the fog over `DISCOVERY_FADE_MS` instead of
   * appearing at full brightness. Returns true while the fade still has frames to run.
   */
  private applyEntryFade(entry: StarEntry, now: number): boolean {
    const k = entry.fadeStart === null ? 1 : Math.min(1, (now - entry.fadeStart) / DISCOVERY_FADE_MS);
    entry.core.material.opacity = entry.baseOpacity * k;
    for (const sprite of entry.decorations) {
      const base = typeof sprite.userData["baseOpacity"] === "number" ? sprite.userData["baseOpacity"] : 1;
      sprite.material.opacity = base * k;
    }
    entry.labelEl.style.opacity = k >= 1 ? "" : String(k);
    if (k >= 1) {
      entry.fadeStart = null;
      return false;
    }
    return true;
  }

  private destroyEntry(entry: StarEntry): void {
    for (const sprite of entry.decorations) sprite.material.dispose();
    entry.core.material.dispose();
    entry.labelEl.remove();
    entry.group.clear();
    this.starsGroup.remove(entry.group);
  }

  private applyLabelStates(): void {
    // Hovering or selecting reveals the distance line, so the cached box is out of date.
    this.labelSizesStale = true;
    for (const entry of this.entries.values()) {
      entry.labelEl.classList.toggle("is-selected", entry.name === this.selected);
      entry.labelEl.classList.toggle("is-hovered", entry.name === this.hovered);
    }
  }

  /* ------------------------------------------------------------ interaction */

  private setHovered(name: string | null): void {
    if (this.hovered === name) return;
    this.hovered = name;
    this.applyLabelStates();
    this.options.onHover?.(name);
    this.requestRender();
  }

  private readonly onPointerDown = (event: PointerEvent): void => {
    this.pointerDown = { x: event.clientX, y: event.clientY };
  };

  private readonly onPointerUp = (event: PointerEvent): void => {
    const start = this.pointerDown;
    this.pointerDown = null;
    if (!start) return;
    const moved = Math.hypot(event.clientX - start.x, event.clientY - start.y);
    if (moved > CLICK_SLOP_PX) return; // that was an orbit drag
    this.options.onSelect(this.pick(event));
  };

  private readonly onPointerMove = (event: PointerEvent): void => {
    if (this.pointerDown) return; // dragging the camera, not hovering
    this.setHovered(this.pick(event));
  };

  private readonly onPointerLeave = (): void => {
    this.setHovered(null);
  };

  /**
   * Screen-space picking: project every star (at most 60) and take the nearest one within
   * `PICK_RADIUS_PX`. More forgiving than raycasting a 10-pixel sprite, and it costs nothing
   * at this object count.
   */
  private pick(event: PointerEvent): string | null {
    const rect = this.renderer.domElement.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) return null;
    const px = event.clientX - rect.left;
    const py = event.clientY - rect.top;

    let best: string | null = null;
    let bestDistance = PICK_RADIUS_PX;
    const projected = new Vector3();
    for (const entry of this.entries.values()) {
      projected.copy(entry.group.position).project(this.camera);
      if (projected.z < -1 || projected.z > 1) continue;
      const sx = ((projected.x + 1) / 2) * rect.width;
      const sy = ((1 - projected.y) / 2) * rect.height;
      const d = Math.hypot(sx - px, sy - py);
      if (d < bestDistance) {
        bestDistance = d;
        best = entry.name;
      }
    }
    return best;
  }

  /* ------------------------------------------------------------ camera / loop */

  /** Camera distance at which the whole rim fits, for the current aspect ratio. */
  private fitDistance(): number {
    const vertical = (CAMERA_FOV * Math.PI) / 360;
    const horizontal = Math.atan(Math.tan(vertical) * Math.max(0.2, this.camera.aspect));
    const half = Math.min(vertical, horizontal);
    return (EDGE_RADIUS * HOME_MARGIN) / Math.max(0.05, Math.sin(half));
  }

  private startFlight(toCamera: Vector3, toTarget: Vector3): void {
    this.flight = {
      fromCamera: this.camera.position.clone(),
      toCamera,
      fromTarget: this.controls.target.clone(),
      toTarget,
      start: performance.now(),
    };
    this.requestRender();
  }

  private stepFlight(now: number): void {
    const flight = this.flight;
    if (!flight) return;
    const t = Math.min(1, (now - flight.start) / FLIGHT_MS);
    const eased = t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2;
    this.camera.position.lerpVectors(flight.fromCamera, flight.toCamera, eased);
    this.controls.target.lerpVectors(flight.fromTarget, flight.toTarget, eased);
    this.controls.update();
    if (t >= 1) this.flight = null;
    this.dirty = true;
  }

  private resize(): void {
    const width = Math.max(1, this.host.clientWidth);
    const height = Math.max(1, this.host.clientHeight);
    this.viewWidth = width;
    this.viewHeight = height;
    this.labelSizesStale = true;
    this.renderer.setSize(width, height, false);
    this.labelRenderer.setSize(width, height);
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.requestRender();
  }

  /** Marks the scene as needing one more frame; the loop is idle until this is called. */
  readonly requestRender = (): void => {
    this.dirty = true;
  };

  /**
   * Nudges overlapping star labels apart, nearest star first, so a crowded direction stays
   * readable and every label keeps its own click target. CSS2DRenderer positions each label
   * with a `transform`, so an extra `top` offset moves both the text and its hit box.
   *
   * Sizes are cached and only re-measured when a label's content could have changed, so the
   * steady state costs no DOM reads; positions are projected in JS rather than measured.
   */
  private declutterLabels(): void {
    const items: { el: HTMLElement; x: number; y: number; depth: number; w: number; h: number }[] = [];
    const projected = new Vector3();

    const consider = (object: CSS2DObject, forceLast = false): void => {
      const el = object.element as HTMLElement;
      if (el.style.display === "none") return;
      if (this.labelSizesStale || !this.labelSizes.has(el)) {
        this.labelSizes.set(el, { w: el.offsetWidth, h: el.offsetHeight });
      }
      const size = this.labelSizes.get(el);
      if (!size || size.h === 0) return;
      object.getWorldPosition(projected).project(this.camera);
      if (projected.z < -1 || projected.z > 1) return;
      items.push({
        el,
        x: ((projected.x + 1) / 2) * this.viewWidth,
        y: ((1 - projected.y) / 2) * this.viewHeight,
        // `forceLast` (the reach ring's label only) always sorts after every star and Earth:
        // the loop below places nearest-first and lets whatever is already placed keep its
        // spot, so this guarantees a star's label wins any clash instead of the two fighting
        // over who was "nearer" this frame.
        depth: forceLast ? Number.POSITIVE_INFINITY : projected.z,
        w: size.w,
        h: size.h,
      });
    };

    consider(this.earthLabel);
    for (const entry of this.entries.values()) consider(entry.label);
    if (this.reachRing.visible) consider(this.reachLabel, true);
    this.labelSizesStale = false;

    // Nearest first: the star in front keeps the spot it earned, the ones behind move.
    items.sort((a, b) => a.depth - b.depth);

    const placed: { left: number; right: number; top: number; bottom: number }[] = [];
    for (const item of items) {
      const left = item.x - item.w / 2;
      const right = left + item.w;
      const stride = item.h + 2;
      let offset = 0;
      for (let attempt = 0; attempt < 7; attempt += 1) {
        // 0, -1, +1, -2, +2, ... rows away from the natural position.
        const row = attempt === 0 ? 0 : Math.ceil(attempt / 2) * (attempt % 2 === 1 ? -1 : 1);
        offset = row * stride;
        const top = item.y - item.h + offset;
        const bottom = top + item.h;
        const clash = placed.some((b) => left < b.right && right > b.left && top < b.bottom && bottom > b.top);
        if (!clash) break;
      }
      const top = item.y - item.h + offset;
      placed.push({ left, right, top, bottom: top + item.h });
      item.el.style.top = offset === 0 ? "" : `${offset}px`;
    }
  }

  /**
   * Moves scene time towards the generation the state asked for. Returns true while the glide
   * is still running (and for the one frame that lands on the target).
   */
  private stepSceneTime(now: number): boolean {
    if (!this.timeAnimating) return false;
    const p = Math.min(1, (now - this.timeStart) / SCENE_TIME_MS);
    this.sceneTime = this.timeFrom + (this.timeTo - this.timeFrom) * easeInOut(p);
    if (this.timeSamples.length < MAX_TIME_SAMPLES) this.timeSamples.push(this.sceneTime);
    if (p >= 1) {
      this.sceneTime = this.timeTo;
      this.timeAnimating = false;
    }
    return true;
  }

  /**
   * Frame-time watchdog over consecutively rendered frames only (two frames a minute apart
   * are not a 60-second frame). Two seconds above `SLOW_FRAME_MS` and the map asks the store
   * to turn "Reduce effects" on - once, so a player who turns it back off is left alone.
   */
  private measureFrame(now: number): void {
    if (this.lastFrameAt > 0) {
      const dt = now - this.lastFrameAt;
      if (dt > 0 && dt < 250) this.frameMs = this.frameMs * 0.8 + dt * 0.2;
    }
    this.lastFrameAt = now;

    if (this.frameMs <= SLOW_FRAME_MS || this.reduced) {
      this.slowSince = 0;
      return;
    }
    if (this.slowSince === 0) {
      this.slowSince = now;
      return;
    }
    if (now - this.slowSince >= SLOW_FRAME_WINDOW_MS && !this.autoReduced) {
      this.autoReduced = true;
      this.slowSince = 0;
      this.options.onAutoReduce?.();
    }
  }

  private readonly tick = (now: number): void => {
    this.raf = requestAnimationFrame(this.tick);
    if (this.flight) this.stepFlight(now);

    // "Busy" means something will look different next frame, so the loop must keep going;
    // everything else only redraws when `dirty` says the state or the camera moved.
    let busy = this.stepSceneTime(now);
    for (const entry of this.entries.values()) {
      if (entry.fadeStart !== null && this.applyEntryFade(entry, now)) busy = true;
    }
    if (busy || this.dirty) {
      const seconds = this.clock.getElapsedTime();
      if (this.effects.step(this.sceneTime, seconds)) busy = true;
      // The backdrop only twinkles while the map is awake anyway; freezing it when the page
      // is idle is what keeps an untouched map at zero draw calls.
      this.starfield.material.uniforms["uTime"]!.value = seconds;
    }
    if (busy) this.dirty = true;

    if (!this.dirty) {
      this.lastFrameAt = 0;
      return;
    }
    this.dirty = false;
    this.renderer.render(this.scene, this.camera);
    this.labelRenderer.render(this.scene, this.camera);
    this.declutterLabels();
    this.measureFrame(now);
    // What the canvas actually shows right now, as opposed to what the store has asked
    // for: tests/map.spec.ts waits on this before screenshotting a scale change.
    this.renderer.domElement.dataset["scale"] = this.scale;
  };
}
