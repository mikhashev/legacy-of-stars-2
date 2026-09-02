/**
 * Everything on the map that moves: light spheres, reply spheres, fleet trajectories, the
 * leakage front, Genesis arks and the fire-and-forget event flashes. `StarMap` owns the
 * renderer, the camera and the stars; this class owns the animated layer hanging off them.
 *
 * The split of responsibilities is strict:
 *
 * - **State -> objects.** `applyState()` diffs `ViewState` (systems, threats, broadcast
 *   radius, Genesis worlds) and creates or destroys persistent visuals. No game logic: every
 *   generation number comes from the engine.
 * - **Events -> flashes.** `playEvents()` turns one `perform()` result's event stream into
 *   short-lived objects that clean themselves up.
 * - **Scene time -> geometry.** `step(t, seconds)` positions and sizes everything from the
 *   continuous generation `t` using `timeline.ts`, which is where all the arithmetic lives.
 *
 * Nothing here reads a fact the engine did not state, and nothing here decides one: a fleet's
 * launch generation, for instance, is derived from the engine's own `arrival_gen`,
 * `source_distance` and `attack_type` (see `timeline.fleetLaunchGen`).
 */
import {
  BufferGeometry,
  CylinderGeometry,
  Float32BufferAttribute,
  Group,
  IcosahedronGeometry,
  Line,
  LineDashedMaterial,
  Mesh,
  type ShaderMaterial,
  SphereGeometry,
  Vector3,
} from "three";
import { CSS2DObject } from "three/examples/jsm/renderers/CSS2DRenderer.js";
import type { GameEvent, GenesisWorld, StarSystem, Threat } from "../types";
import { createBeamMaterial, createMarkerMaterial, createSphereMaterial } from "./shaders";
import {
  arkProgress,
  fleetLaunchGen,
  fleetProgress,
  leakageRadiusLy,
  messageFade,
  messageRadiusLy,
  replyFade,
  replyRadiusLy,
} from "./timeline";

/* ---------------------------------------------------------------- budget */

/** At most this many transmissions per system are drawn (plan W4: "the last 3"). */
export const MAX_MESSAGES_PER_SYSTEM = 3;
const MAX_MESSAGE_SPHERES = 36;
const MAX_FLEETS = 12;
const MAX_ARKS = 8;
const MAX_FLASHES = 20;
/** Vertices per trajectory: enough for the `attack_warning` draw-in to look smooth. */
const TRAJECTORY_POINTS = 48;

/* ---------------------------------------------------------------- colours */

const OUTGOING_COLOR = 0x4fd6ff; // cyan: our transmissions
const INCOMING_COLOR = 0xffe9c4; // warm white: their replies
const FLEET_COLOR = 0xff5a4a; // red: an inbound attack
const LEAKAGE_COLOR = 0x9fb6d8; // cold grey-blue: the radio leakage front
const ARK_COLOR = 0x7fe0a0; // green: a Genesis ark and the colony it becomes
const DISCOVERY_COLOR = 0xdfe7f2; // pale white: a star coming out of the fog
const VICTORY_COLOR = 0xffd479; // gold
const WOW_COLOR = 0x8fd4ff; // the 1977 beam towards Sagittarius

/* ---------------------------------------------------------------- host */

/** What `effects.ts` needs from `StarMap`; keeps this file free of camera and scale details. */
export interface EffectsHost {
  /** Scene position of a system the map is drawing, or null when it is not on the map. */
  positionOf(name: string): Vector3 | null;
  /** Scene radius for a distance in light-years, under the scale mode in force. */
  radiusOf(distanceLy: number): number;
  /** True when that distance would fall outside the rim of the scene. */
  beyondRim(distanceLy: number): boolean;
  /** The rim radius itself, where an over-large leakage front is pinned. */
  rimRadius(): number;
  /** Ask for one more rendered frame. */
  requestRender(): void;
}

/** The slice of `ViewState` the animated layer is built from. */
export interface EffectsState {
  generation: number;
  systems: StarSystem[];
  threats: Threat[];
  broadcastRadius: number;
  genesisWorlds: GenesisWorld[];
}

/* ---------------------------------------------------------------- visuals */

interface SphereVisual {
  key: string;
  system: string;
  kind: "outgoing" | "reply";
  /** The generation the light left its source. */
  launchGen: number;
  distance: number;
  mesh: Mesh<SphereGeometry, ShaderMaterial>;
  /** Last computed values, for the debug hook. */
  radiusLy: number;
  opacity: number;
}

interface FleetVisual {
  key: string;
  source: string;
  attackType: string;
  typeLabel: string;
  eta: number;
  launchGen: number;
  arrivalGen: number;
  line: Line<BufferGeometry, LineDashedMaterial>;
  marker: Mesh<IcosahedronGeometry, ShaderMaterial>;
  label: CSS2DObject;
  labelEl: HTMLDivElement;
  /** Scene seconds at which the `attack_warning` draw-in started, or null when fully drawn. */
  drawStart: number | null;
  origin: Vector3;
  progress: number;
}

interface ArkVisual {
  key: string;
  system: string;
  seedGen: number;
  arrivalGen: number;
  stage: number;
  line: Line<BufferGeometry, LineDashedMaterial>;
  marker: Mesh<IcosahedronGeometry, ShaderMaterial>;
  glow: Mesh<IcosahedronGeometry, ShaderMaterial>;
  target: Vector3;
}

interface Flash {
  kind: string;
  mesh: Mesh;
  material: ShaderMaterial;
  /** Scene seconds when it was spawned. */
  start: number;
  delay: number;
  duration: number;
  fromRadius: number;
  toRadius: number;
  peak: number;
  /** A beam animates `uHead` instead of its scale. */
  beam: boolean;
}

/** One row of the `window.__losMap` debug view of the animated layer. */
export interface DebugSphere {
  system: string;
  kind: "outgoing" | "reply";
  launchGen: number;
  radiusLy: number;
  opacity: number;
}

export interface DebugFleet {
  source: string;
  attackType: string;
  eta: number;
  progress: number;
}

/* ---------------------------------------------------------------- the layer */

export class SceneEffects {
  /** The one node `StarMap` adds to its scene; disposing this class empties it. */
  readonly root = new Group();

  private readonly host: EffectsHost;

  // Shared geometries: one sphere, one marker, one beam for the whole layer.
  private readonly sphereGeometry = new SphereGeometry(1, 32, 20);
  private readonly markerGeometry = new IcosahedronGeometry(1, 1);
  private readonly beamGeometry: CylinderGeometry;

  private readonly spheres = new Map<string, SphereVisual>();
  private readonly fleets = new Map<string, FleetVisual>();
  private readonly arks = new Map<string, ArkVisual>();
  private flashes: Flash[] = [];

  private readonly leakage: Mesh<SphereGeometry, ShaderMaterial>;
  private readonly leakageRim: Mesh<SphereGeometry, ShaderMaterial>;

  private state: EffectsState = {
    generation: 1,
    systems: [],
    threats: [],
    broadcastRadius: 0,
    genesisWorlds: [],
  };
  private reduced = false;
  private leakageLy = 0;
  private seconds = 0;

  private readonly scratch = new Vector3();

  constructor(host: EffectsHost) {
    this.host = host;
    this.root.name = "effects";

    // A unit cylinder along +y whose base sits at the origin, so a beam is placed by
    // pointing it at the target and scaling y to the distance.
    this.beamGeometry = new CylinderGeometry(1, 1, 1, 14, 1, true);
    this.beamGeometry.translate(0, 0.5, 0);

    this.leakage = new Mesh(
      this.sphereGeometry,
      // core 0: only the limb lights up, which is what makes the front readable at all.
      createSphereMaterial({ color: LEAKAGE_COLOR, opacity: 0.11, rimPower: 3.4, core: 0 }),
    );
    this.leakage.name = "leakage-front";
    this.leakage.frustumCulled = false;

    this.leakageRim = new Mesh(
      this.sphereGeometry,
      createSphereMaterial({ color: LEAKAGE_COLOR, opacity: 0.1, rimPower: 5, core: 0 }),
    );
    this.leakageRim.name = "leakage-rim";
    this.leakageRim.visible = false;
    this.leakageRim.frustumCulled = false;

    this.root.add(this.leakage, this.leakageRim);
  }

  /* ------------------------------------------------------------ toggles */

  /** "Reduce effects": the nebula is `StarMap`'s, the flashes are ours. */
  setReduced(reduced: boolean): void {
    if (this.reduced === reduced) return;
    this.reduced = reduced;
    if (reduced) this.clearFlashes();
    this.host.requestRender();
  }

  /* ------------------------------------------------------------ state -> objects */

  applyState(state: EffectsState): void {
    this.state = state;
    this.syncSpheres(state);
    this.syncFleets(state);
    this.syncArks(state);
    this.host.requestRender();
  }

  private syncSpheres(state: EffectsState): void {
    const seen = new Set<string>();
    let budget = MAX_MESSAGE_SPHERES;

    for (const system of state.systems) {
      if (budget <= 0) break;
      // The last three transmissions to this system, oldest of the three first.
      const recent = system.messages_sent.slice(-MAX_MESSAGES_PER_SYSTEM);
      for (const message of recent) {
        if (budget <= 0) break;
        const key = `out|${system.name}|${message.generation}`;
        seen.add(key);
        budget -= 1;
        if (this.spheres.has(key)) continue;
        this.spheres.set(
          key,
          this.createSphere(key, system.name, "outgoing", message.generation, system.distance, OUTGOING_COLOR),
        );
      }

      // A reply is in flight whenever the engine has named the generation it lands in.
      if (system.next_response_gen !== null) {
        const key = `in|${system.name}|${system.next_response_gen}`;
        seen.add(key);
        budget -= 1;
        if (!this.spheres.has(key)) {
          this.spheres.set(
            key,
            this.createSphere(key, system.name, "reply", system.next_response_gen, system.distance, INCOMING_COLOR),
          );
        }
      }
    }

    for (const [key, visual] of this.spheres) {
      if (seen.has(key)) continue;
      this.destroySphere(visual);
      this.spheres.delete(key);
    }
  }

  private createSphere(
    key: string,
    system: string,
    kind: "outgoing" | "reply",
    launchGen: number,
    distance: number,
    color: number,
  ): SphereVisual {
    const mesh = new Mesh(
      this.sphereGeometry,
      createSphereMaterial({ color, opacity: 0, rimPower: kind === "outgoing" ? 2.6 : 2.2, core: 0.045 }),
    );
    mesh.name = key;
    mesh.visible = false;
    mesh.frustumCulled = false;
    this.root.add(mesh);
    // `launchGen` is the send generation for an outgoing sphere and the *arrival* generation
    // for a reply; `timeline.replyRadiusLy` walks the arrival back to the actual launch.
    return { key, system, kind, launchGen, distance, mesh, radiusLy: 0, opacity: 0 };
  }

  private destroySphere(visual: SphereVisual): void {
    this.root.remove(visual.mesh);
    visual.mesh.material.dispose();
  }

  private syncFleets(state: EffectsState): void {
    const seen = new Set<string>();
    for (const threat of state.threats.slice(0, MAX_FLEETS)) {
      const key = `${threat.source}|${threat.attack_type}|${threat.arrival_gen}`;
      seen.add(key);
      const existing = this.fleets.get(key);
      if (existing) {
        existing.eta = threat.eta;
        this.labelFleet(existing);
        continue;
      }
      this.fleets.set(key, this.createFleet(key, threat));
    }
    for (const [key, visual] of this.fleets) {
      if (seen.has(key)) continue;
      this.destroyFleet(visual);
      this.fleets.delete(key);
    }
  }

  private createFleet(key: string, threat: Threat): FleetVisual {
    const line = this.createTrajectory(FLEET_COLOR, 0.55);
    line.name = `fleet-line:${key}`;

    const marker = new Mesh(this.markerGeometry, createMarkerMaterial(FLEET_COLOR, 0.95));
    marker.name = `fleet:${key}`;
    marker.frustumCulled = false;

    const labelEl = document.createElement("div");
    labelEl.className = "fleet-label";
    labelEl.dataset["source"] = threat.source;
    const label = new CSS2DObject(labelEl);
    label.center.set(0.5, 0);
    label.position.set(0, -1.4, 0);
    marker.add(label);

    this.root.add(line, marker);

    const visual: FleetVisual = {
      key,
      source: threat.source,
      attackType: threat.attack_type,
      typeLabel: threat.type_label,
      eta: threat.eta,
      launchGen: fleetLaunchGen(threat.arrival_gen, threat.source_distance, threat.attack_type),
      arrivalGen: threat.arrival_gen,
      line,
      marker,
      label,
      labelEl,
      drawStart: null,
      origin: new Vector3(),
      progress: 0,
    };
    this.labelFleet(visual);
    return visual;
  }

  private labelFleet(visual: FleetVisual): void {
    visual.labelEl.textContent = `${visual.typeLabel} - ETA ${visual.eta}`;
    visual.labelEl.dataset["urgent"] = visual.eta <= 2 ? "true" : "false";
  }

  private destroyFleet(visual: FleetVisual): void {
    visual.labelEl.remove();
    visual.marker.remove(visual.label);
    this.root.remove(visual.line, visual.marker);
    visual.line.geometry.dispose();
    visual.line.material.dispose();
    visual.marker.material.dispose();
  }

  private syncArks(state: EffectsState): void {
    const seen = new Set<string>();
    for (const world of state.genesisWorlds.slice(0, MAX_ARKS)) {
      if (world.is_destroyed) continue;
      const key = `${world.system_name}|${world.seed_gen}`;
      seen.add(key);
      const existing = this.arks.get(key);
      if (existing) {
        existing.stage = world.evolution_stage;
        continue;
      }
      this.arks.set(key, this.createArk(key, world));
    }
    for (const [key, visual] of this.arks) {
      if (seen.has(key)) continue;
      this.destroyArk(visual);
      this.arks.delete(key);
    }
  }

  private createArk(key: string, world: GenesisWorld): ArkVisual {
    const line = this.createTrajectory(ARK_COLOR, 0.35);
    line.name = `ark-line:${key}`;

    const marker = new Mesh(this.markerGeometry, createMarkerMaterial(ARK_COLOR, 0.85));
    marker.name = `ark:${key}`;
    marker.frustumCulled = false;

    const glow = new Mesh(this.markerGeometry, createMarkerMaterial(ARK_COLOR, 0.4));
    glow.name = `colony:${key}`;
    glow.visible = false;
    glow.frustumCulled = false;

    this.root.add(line, marker, glow);
    return {
      key,
      system: world.system_name,
      seedGen: world.seed_gen,
      arrivalGen: world.arrival_gen,
      stage: world.evolution_stage,
      line,
      marker,
      glow,
      target: new Vector3(),
    };
  }

  private destroyArk(visual: ArkVisual): void {
    this.root.remove(visual.line, visual.marker, visual.glow);
    visual.line.geometry.dispose();
    visual.line.material.dispose();
    visual.marker.material.dispose();
    visual.glow.material.dispose();
  }

  /** A dashed straight line, sampled at `TRAJECTORY_POINTS` so it can draw itself in. */
  private createTrajectory(color: number, opacity: number): Line<BufferGeometry, LineDashedMaterial> {
    const geometry = new BufferGeometry();
    geometry.setAttribute("position", new Float32BufferAttribute(new Float32Array(TRAJECTORY_POINTS * 3), 3));
    const material = new LineDashedMaterial({
      color,
      dashSize: 1.6,
      gapSize: 1.4,
      transparent: true,
      opacity,
      depthWrite: false,
    });
    const line = new Line<BufferGeometry, LineDashedMaterial>(geometry, material);
    line.frustumCulled = false;
    return line;
  }

  /** Rewrites a trajectory's vertices when either end has moved (a scale toggle, mostly). */
  private layTrajectory(line: Line<BufferGeometry, LineDashedMaterial>, from: Vector3, to: Vector3): void {
    const attribute = line.geometry.getAttribute("position");
    const array = attribute.array as Float32Array;
    for (let i = 0; i < TRAJECTORY_POINTS; i += 1) {
      const p = i / (TRAJECTORY_POINTS - 1);
      array[i * 3] = from.x + (to.x - from.x) * p;
      array[i * 3 + 1] = from.y + (to.y - from.y) * p;
      array[i * 3 + 2] = from.z + (to.z - from.z) * p;
    }
    attribute.needsUpdate = true;
    line.geometry.computeBoundingSphere();
    line.computeLineDistances();
  }

  /* ------------------------------------------------------------ events -> flashes */

  /**
   * One `perform()` result's events. Flashes are decoration only: every one of them is
   * additive light that disappears on its own, so dropping them (reduced effects, or a
   * full flash budget) never hides information the state does not also carry.
   */
  playEvents(events: readonly GameEvent[]): void {
    if (this.reduced) return;
    for (const event of events) {
      switch (event.kind) {
        case "system_discovered":
          this.flashAt(event.data.system, DISCOVERY_COLOR, 0.6, 9, 1.0, 0.85, 0);
          break;
        case "response_received":
          // A pulse at the star, then the arrival on Earth half a second later.
          this.flashAt(event.data.system, INCOMING_COLOR, 0.5, 12, 1.1, 0.9, 0);
          this.flashAtOrigin(INCOMING_COLOR, 1, 14, 1.2, 0.8, 0.5);
          break;
        case "attack_resolved":
        case "info_attack":
          this.flashAtOrigin(FLEET_COLOR, 1, 20, 1.3, 1.0, 0);
          break;
        case "attack_warning":
          this.startFleetDrawIn(event.data.system);
          break;
        case "genesis":
          this.flashAt(event.data.system, ARK_COLOR, 0.6, 11, 1.4, 0.7, 0);
          break;
        case "wow":
          this.spawnWowBeam();
          break;
        case "victory":
          this.flashAtOrigin(VICTORY_COLOR, 1, 26, 2.6, 0.75, 0);
          break;
        default:
          break;
      }
    }
    this.host.requestRender();
  }

  /** The `attack_warning` line drawing itself from the source star to Earth. */
  private startFleetDrawIn(source: string): void {
    for (const fleet of this.fleets.values()) {
      if (fleet.source !== source) continue;
      fleet.drawStart = this.seconds;
      fleet.line.geometry.setDrawRange(0, 2);
    }
  }

  private flashAt(
    system: string,
    color: number,
    fromRadius: number,
    toRadius: number,
    duration: number,
    peak: number,
    delay: number,
  ): void {
    const position = this.host.positionOf(system);
    if (!position) return;
    this.spawnFlash(`flash:${system}`, position, color, fromRadius, toRadius, duration, peak, delay);
  }

  private flashAtOrigin(
    color: number,
    fromRadius: number,
    toRadius: number,
    duration: number,
    peak: number,
    delay: number,
  ): void {
    this.spawnFlash("flash:earth", this.scratch.set(0, 0, 0), color, fromRadius, toRadius, duration, peak, delay);
  }

  private spawnFlash(
    name: string,
    position: Vector3,
    color: number,
    fromRadius: number,
    toRadius: number,
    duration: number,
    peak: number,
    delay: number,
  ): void {
    if (this.flashes.length >= MAX_FLASHES) return;
    const material = createSphereMaterial({ color, opacity: 0, rimPower: 2.2, core: 0.08 });
    const mesh = new Mesh(this.sphereGeometry, material);
    mesh.name = name;
    mesh.position.copy(position);
    mesh.scale.setScalar(fromRadius);
    mesh.frustumCulled = false;
    this.root.add(mesh);
    this.flashes.push({
      kind: name,
      mesh,
      material,
      start: this.seconds,
      delay,
      duration,
      fromRadius,
      toRadius,
      peak,
      beam: false,
    });
  }

  /** The 1977 beam: Earth -> the WOW! source's direction, three seconds, then gone. */
  private spawnWowBeam(): void {
    if (this.flashes.length >= MAX_FLASHES) return;
    const target = this.wowDirection();
    if (!target) return;
    const material = createBeamMaterial(WOW_COLOR, 0.8);
    const mesh = new Mesh(this.beamGeometry, material);
    mesh.name = "flash:wow-beam";
    const length = target.length();
    mesh.quaternion.setFromUnitVectors(new Vector3(0, 1, 0), target.clone().normalize());
    mesh.scale.set(1.1, length, 1.1);
    mesh.frustumCulled = false;
    this.root.add(mesh);
    this.flashes.push({
      kind: "flash:wow-beam",
      mesh,
      material,
      start: this.seconds,
      delay: 0,
      duration: 3,
      fromRadius: 1,
      toRadius: 1,
      peak: 0.8,
      beam: true,
    });
  }

  /**
   * Where the beam points. The engine names the source "Wow! source (Chi Sagittarii)" and
   * puts it on the map like any other system; if it is not listed (the player stayed silent),
   * nothing is drawn rather than a direction invented here.
   */
  private wowDirection(): Vector3 | null {
    for (const system of this.state.systems) {
      if (!system.name.startsWith("Wow! source")) continue;
      const position = this.host.positionOf(system.name);
      if (position && position.lengthSq() > 1) return position.clone();
    }
    return null;
  }

  private clearFlashes(): void {
    for (const flash of this.flashes) {
      this.root.remove(flash.mesh);
      flash.material.dispose();
    }
    this.flashes = [];
  }

  /* ------------------------------------------------------------ scene time -> geometry */

  /**
   * Positions the whole layer for scene time `t` (a continuous generation) at wall-clock
   * `seconds` (a shared `THREE.Clock`). Returns true while something still needs another
   * frame after this one, which is how `StarMap` decides whether to keep rendering.
   */
  step(t: number, seconds: number): boolean {
    this.seconds = seconds;
    let busy = false;

    // Spheres and arks are functions of `t` alone: they only change when scene time does, and
    // `StarMap` already knows whether that is happening, so they never claim a frame of their
    // own. A pulsing fleet marker and a flash do run off the clock, and say so.
    for (const visual of this.spheres.values()) {
      this.stepSphere(visual, t);
    }
    for (const visual of this.fleets.values()) {
      busy = this.stepFleet(visual, t, seconds) || busy;
    }
    for (const visual of this.arks.values()) {
      this.stepArk(visual, t, seconds);
    }
    this.stepLeakage(t);
    busy = this.stepFlashes(seconds) || busy;
    return busy;
  }

  private stepSphere(visual: SphereVisual, t: number): void {
    const radiusLy =
      visual.kind === "outgoing"
        ? messageRadiusLy(visual.launchGen, visual.distance, t)
        : replyRadiusLy(visual.launchGen, visual.distance, t);
    const opacity =
      visual.kind === "outgoing"
        ? messageFade(visual.launchGen, visual.distance, t)
        : replyFade(visual.launchGen, visual.distance, t);

    visual.radiusLy = radiusLy;
    visual.opacity = opacity;

    if (opacity <= 0.004 || radiusLy <= 0) {
      visual.mesh.visible = false;
      return;
    }
    // The same compression the stars go through, so a sphere touches its star exactly when
    // its light gets there.
    visual.mesh.scale.setScalar(Math.max(0.4, this.host.radiusOf(radiusLy)));
    if (visual.kind === "reply") {
      const star = this.host.positionOf(visual.system);
      if (star) visual.mesh.position.copy(star);
    }
    visual.mesh.material.uniforms["uOpacity"]!.value = opacity * 0.8;
    visual.mesh.visible = true;
  }

  private stepFleet(visual: FleetVisual, t: number, seconds: number): boolean {
    const source = this.host.positionOf(visual.source);
    if (!source) {
      visual.line.visible = false;
      visual.marker.visible = false;
      return false;
    }
    if (!source.equals(visual.origin)) {
      visual.origin.copy(source);
      this.layTrajectory(visual.line, source, this.scratch.set(0, 0, 0));
    }
    visual.line.visible = true;
    visual.marker.visible = true;

    let busy = false;
    if (visual.drawStart !== null) {
      const p = Math.min(1, (seconds - visual.drawStart) / 1.0);
      visual.line.geometry.setDrawRange(0, Math.max(2, Math.round(p * TRAJECTORY_POINTS)));
      if (p >= 1) visual.drawStart = null;
      busy = true;
    } else {
      visual.line.geometry.setDrawRange(0, TRAJECTORY_POINTS);
    }

    const progress = fleetProgress(t, visual.launchGen, visual.arrivalGen);
    visual.progress = progress;
    // Straight from the star to Earth, in compressed coordinates.
    visual.marker.position.copy(source).multiplyScalar(1 - progress);
    visual.marker.scale.setScalar(visual.eta <= 2 ? 2.2 : 1.7);
    const uniforms = visual.marker.material.uniforms;
    uniforms["uTime"]!.value = seconds;
    uniforms["uPulse"]!.value = visual.eta <= 2 ? 1 : 0;
    return busy || visual.eta <= 2;
  }

  private stepArk(visual: ArkVisual, t: number, seconds: number): void {
    const star = this.host.positionOf(visual.system);
    if (!star) {
      visual.line.visible = false;
      visual.marker.visible = false;
      visual.glow.visible = false;
      return;
    }
    if (!star.equals(visual.target)) {
      visual.target.copy(star);
      this.layTrajectory(visual.line, this.scratch.set(0, 0, 0), star);
    }
    const progress = arkProgress(visual.seedGen, visual.arrivalGen, t);
    const landed = progress >= 1;
    visual.line.visible = !landed;
    visual.marker.visible = !landed;
    visual.marker.position.copy(star).multiplyScalar(progress);
    visual.marker.scale.setScalar(1.4);
    visual.marker.material.uniforms["uTime"]!.value = seconds;

    // The colony itself: only once the engine says the world has started evolving.
    visual.glow.visible = visual.stage >= 1;
    if (visual.glow.visible) {
      visual.glow.position.copy(star);
      visual.glow.scale.setScalar(4 + visual.stage * 1.2);
      visual.glow.material.uniforms["uTime"]!.value = seconds;
    }
  }

  private stepLeakage(t: number): void {
    const ly = leakageRadiusLy(this.state.broadcastRadius, this.state.generation, t);
    this.leakageLy = ly;
    if (ly <= 0) {
      this.leakage.visible = false;
      this.leakageRim.visible = false;
      return;
    }
    if (this.host.beyondRim(ly)) {
      // Past the edge of the scene the sphere would swallow the whole map, so it is replaced
      // by a ring pinned to the rim - the fresnel shader draws only the limb, so a shell at
      // the rim radius reads as exactly that: "everyone within the frame can hear us".
      this.leakage.visible = false;
      this.leakageRim.visible = true;
      this.leakageRim.scale.setScalar(this.host.rimRadius() * 0.995);
      return;
    }
    this.leakageRim.visible = false;
    this.leakage.visible = true;
    this.leakage.scale.setScalar(Math.max(0.5, this.host.radiusOf(ly)));
  }

  private stepFlashes(seconds: number): boolean {
    if (this.flashes.length === 0) return false;
    const alive: Flash[] = [];
    for (const flash of this.flashes) {
      const elapsed = seconds - flash.start - flash.delay;
      if (elapsed < 0) {
        flash.mesh.visible = false;
        alive.push(flash);
        continue;
      }
      const p = elapsed / flash.duration;
      if (p >= 1) {
        this.root.remove(flash.mesh);
        flash.material.dispose();
        continue;
      }
      flash.mesh.visible = true;
      if (flash.beam) {
        // The beam lights up along its length, then fades where it stands.
        flash.material.uniforms["uHead"]!.value = Math.min(1.05, p * 3);
        flash.material.uniforms["uTime"]!.value = seconds;
        flash.material.uniforms["uOpacity"]!.value = flash.peak * (1 - Math.max(0, (p - 0.6) / 0.4));
      } else {
        // Grow fast, fade over the whole life: a bloom, not a balloon.
        const eased = 1 - (1 - p) ** 2;
        flash.mesh.scale.setScalar(flash.fromRadius + (flash.toRadius - flash.fromRadius) * eased);
        flash.material.uniforms["uOpacity"]!.value = flash.peak * (1 - p) ** 1.4;
      }
      alive.push(flash);
    }
    this.flashes = alive;
    return this.flashes.length > 0;
  }

  /* ------------------------------------------------------------ debug / teardown */

  debugSpheres(): DebugSphere[] {
    return [...this.spheres.values()].map((v) => ({
      system: v.system,
      kind: v.kind,
      launchGen: v.launchGen,
      radiusLy: v.radiusLy,
      opacity: v.opacity,
    }));
  }

  debugFleets(): DebugFleet[] {
    return [...this.fleets.values()].map((v) => ({
      source: v.source,
      attackType: v.attackType,
      eta: v.eta,
      progress: v.progress,
    }));
  }

  debugLeakageLy(): number {
    return this.leakageLy;
  }

  debugFlashes(): string[] {
    return this.flashes.map((f) => f.kind);
  }

  /** Objects currently in the animated layer, for the performance budget. */
  objectCount(): number {
    return this.root.children.length;
  }

  dispose(): void {
    this.clearFlashes();
    for (const visual of this.spheres.values()) this.destroySphere(visual);
    this.spheres.clear();
    for (const visual of this.fleets.values()) this.destroyFleet(visual);
    this.fleets.clear();
    for (const visual of this.arks.values()) this.destroyArk(visual);
    this.arks.clear();
    this.leakage.material.dispose();
    this.leakageRim.material.dispose();
    this.sphereGeometry.dispose();
    this.markerGeometry.dispose();
    this.beamGeometry.dispose();
    this.root.clear();
  }
}
