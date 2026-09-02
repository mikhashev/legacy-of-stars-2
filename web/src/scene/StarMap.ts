/**
 * The W3 star map: Earth at the origin, the known systems around it, orientation rings and a
 * static backdrop. This class owns the WebGL renderer, the scene, the camera, OrbitControls
 * and the CSS2D label layer; `ui/MapPanel.tsx` is the only thing that constructs it.
 *
 * Design notes for W4 (shaders and event animations):
 *
 * - Every system is a `Group` (`StarEntry.group`) parked at the star's position, and Earth is
 *   its own `Group` at the origin. Per-star and per-Earth effects attach as children of those
 *   groups, so nothing has to recompute coordinates.
 * - `update()` diffs by system name and only rebuilds what actually changed, so animation
 *   objects that W4 adds under a group survive a state update.
 * - Nothing renders unless something changed (`requestRender`), so an idle page costs no GPU;
 *   a W4 animation keeps itself alive by calling `requestRender()` from its own step.
 * - `starfield.ts` returns a plain `Points`; W4 swaps its material for the nebula shader.
 */
import {
  AdditiveBlending,
  BufferGeometry,
  CanvasTexture,
  Color,
  Float32BufferAttribute,
  Group,
  LineBasicMaterial,
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
import type { StarSystem } from "../types";
import {
  EDGE_RADIUS,
  RING_DISTANCES_LY,
  type ScaleMode,
  formatDistance,
  positionForSystem,
  radiusFor,
} from "./coords";
import { CONTACTED_COLOR, MOOD_COLOR, SEEDED_COLOR, moodFor, styleFor } from "./palette";
import { type Starfield, createStarfield } from "./starfield";

/** What the map needs out of the store; a subset of `ViewState` plus the two view toggles. */
export interface MapViewState {
  systems: StarSystem[];
  selected: string | null;
  scale: ScaleMode;
}

export interface StarMapOptions {
  /** A star was clicked, or empty space was (null). */
  onSelect(name: string | null): void;
  /** The pointer moved onto or off a star. */
  onHover?(name: string | null): void;
}

/** Hard ceiling on drawn systems (the catalogue is 53 stars plus the WOW! source). */
const MAX_SYSTEMS = 60;

/** World-unit diameter of an average main-sequence star sprite. */
const BASE_STAR_SIZE = 5;

const CAMERA_FOV = 50;
/** How much of the rim the default framing leaves as margin. */
const HOME_MARGIN = 1.1;
const FLIGHT_MS = 700;
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

function squareTexture(): CanvasTexture {
  const size = 32;
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext("2d");
  if (ctx) {
    ctx.fillStyle = "rgba(255,255,255,0.9)";
    ctx.fillRect(6, 6, size - 12, size - 12);
  }
  return new CanvasTexture(canvas);
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
  private earthGlobe!: Mesh<SphereGeometry, MeshBasicMaterial>;
  private earthGlow!: Sprite;
  private earthLabel!: CSS2DObject;

  private readonly textures: Texture[] = [];
  private readonly starTexture: CanvasTexture;
  private readonly glowTexture: CanvasTexture;
  private readonly haloTexture: CanvasTexture;
  private readonly ringMarkTexture: CanvasTexture;
  private readonly tickTexture: CanvasTexture;

  private readonly entries = new Map<string, StarEntry>();
  private readonly ringLoops: {
    loop: LineLoop<BufferGeometry, LineBasicMaterial>;
    label: CSS2DObject;
    ly: number;
  }[] = [];

  private scale: ScaleMode = "compressed";
  private selected: string | null = null;
  private hovered: string | null = null;

  private dirty = true;
  private raf = 0;
  private started = false;
  private flight: Flight | null = null;
  private disposed = false;

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
    this.tickTexture = squareTexture();
    this.textures.push(this.starTexture, this.glowTexture, this.haloTexture, this.ringMarkTexture, this.tickTexture);

    this.starfield = createStarfield();
    this.scene.add(this.starfield, this.ringsGroup, this.earthGroup, this.starsGroup);

    this.buildEarth();
    this.buildRings();
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

    this.raf = requestAnimationFrame(this.tick);
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
  }

  /* ------------------------------------------------------------ public API */

  /** Applies a new game state to the scene, adding/removing/refreshing systems by name. */
  update(view: MapViewState): void {
    if (this.disposed) return;

    const scaleChanged = view.scale !== this.scale;
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

    this.select(view.selected);
    this.requestRender();
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
    const position = new Vector3(0, EDGE_RADIUS * 0.42, this.fitDistance());
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

    // Sprites share one module-level geometry inside three.js, so only the mesh's is ours.
    this.earthGlobe.geometry.dispose();
    this.earthGlobe.material.dispose();
    this.earthGlow.material.dispose();
    this.earthLabel.element.remove();
    this.earthGroup.clear();

    this.starfield.geometry.dispose();
    this.starfield.material.dispose();
    for (const texture of this.textures) texture.dispose();

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
      system.distance,
    ].join("|");
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
    entry.core.material.opacity = mood === "unknown" ? 0.6 : 1;
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
    // A small tick for transmissions on their way there.
    if (system.messages_sent.length > 0) {
      const tick = this.addSprite(entry, this.tickTexture, 0xd6dde8, size * 0.5, 0.9);
      tick.position.set(size * 0.85, size * 0.85, 0);
      entry.decorations.push(tick);
    }

    entry.label.position.set(0, size * 0.75, 0);
    entry.labelEl.dataset["mood"] = mood;
    entry.labelEl.dataset["seeded"] = system.is_seeded ? "true" : "false";
    entry.labelEl.dataset["contacted"] = system.contacted ? "true" : "false";
    const distEl = entry.labelEl.querySelector(".star-label-distance");
    if (distEl) distEl.textContent = formatDistance(system.distance);
    this.labelSizesStale = true;
    this.applyLabelStates();
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
    entry.group.add(sprite);
    return sprite;
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

    const consider = (object: CSS2DObject): void => {
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
        depth: projected.z,
        w: size.w,
        h: size.h,
      });
    };

    consider(this.earthLabel);
    for (const entry of this.entries.values()) consider(entry.label);
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

  private readonly tick = (now: number): void => {
    this.raf = requestAnimationFrame(this.tick);
    if (this.flight) this.stepFlight(now);
    if (!this.dirty) return;
    this.dirty = false;
    this.renderer.render(this.scene, this.camera);
    this.labelRenderer.render(this.scene, this.camera);
    this.declutterLabels();
    // What the canvas actually shows right now, as opposed to what the store has asked
    // for: tests/map.spec.ts waits on this before screenshotting a scale change.
    this.renderer.domElement.dataset["scale"] = this.scale;
  };
}
