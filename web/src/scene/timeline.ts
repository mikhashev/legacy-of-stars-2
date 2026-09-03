/**
 * The physics behind every W4 animation, as pure functions: no Three.js, no DOM, no state.
 * `tests/unit/timeline.test.ts` exercises this file directly.
 *
 * All of it is the *game's* physics, read off `docs/reference/web_contract.md`, not new rules:
 *
 * - one generation is 25 years (`ViewState.year = start_year + (generation - 1) * 25`), so a
 *   signal, which travels at light speed, covers 25 light-years per generation;
 * - `status.broadcast_radius` is the leakage front in LY and grows by exactly that much;
 * - a fleet covers `speed_c * 25` LY per generation, and the speed is the one printed in
 *   `threats[].type_label` ("fusion strike fleet (0.12c)");
 * - a Genesis ark flies at 0.12c, but its `seed_gen` and `arrival_gen` come from the engine,
 *   so the front-end interpolates between them rather than recomputing the flight.
 *
 * The single free variable is **scene time `t`**, a continuous generation number: it equals
 * `ViewState.generation` when the map is at rest and glides to the new value over ~1.5 s after
 * a generation advance. Every radius and position below is a function of `t`.
 */

/** Light-years a signal covers in one generation (25 years at c). */
export const LY_PER_GENERATION = 25;

/** Genesis arks fly at this fraction of c (plan W4). */
export const ARK_SPEED_C = 0.12;

/** Fraction of c per `threats[].attack_type` (docs/reference/web_contract.md 5). */
export const ATTACK_SPEED_C: Readonly<Record<string, number>> = {
  fleet: 0.1,
  laser_sail_probe: 0.175,
  fusion_strike: 0.12,
  genesis_fleet: 0.1,
  mirror_fleet: 0.1,
};

/** What an unrecognised `attack_type` (e.g. `wow_fleet`) is drawn at. */
export const DEFAULT_ATTACK_SPEED_C = 0.1;

/** How long, in generations of scene time, a sphere keeps fading after it has arrived. */
export const FADE_TAIL_GENERATIONS = 0.35;

/** Opacity a sphere has left at the moment it reaches its destination. */
export const ARRIVAL_OPACITY = 0.55;

export function clamp(value: number, min: number, max: number): number {
  return value < min ? min : value > max ? max : value;
}

export function clamp01(value: number): number {
  return clamp(value, 0, 1);
}

/** Cubic ease-in-out on [0, 1]; the curve the scene-time glide uses. */
export function easeInOut(x: number): number {
  const p = clamp01(x);
  return p < 0.5 ? 4 * p * p * p : 1 - (-2 * p + 2) ** 3 / 2;
}

/** Fraction of c for an attack type; anything unknown is drawn as a 0.1c fleet. */
export function attackSpeedC(attackType: string | null | undefined): number {
  if (!attackType) return DEFAULT_ATTACK_SPEED_C;
  return ATTACK_SPEED_C[attackType] ?? DEFAULT_ATTACK_SPEED_C;
}

/** Generations something covers `distanceLy` in, at `speedC` times the speed of light. */
export function travelGenerations(distanceLy: number, speedC = 1): number {
  const speed = Math.max(1e-6, speedC);
  return Math.max(0, distanceLy) / (speed * LY_PER_GENERATION);
}

/* ------------------------------------------------------------------ light spheres */

/**
 * Radius, in light-years, of the sphere of our transmission at scene time `t`:
 * `min(distance, 25 * (t - generation))`, never negative. The message has not left yet
 * while `t < generation`, and stops growing once its light has reached the star.
 */
export function messageRadiusLy(sentGen: number, distanceLy: number, t: number): number {
  const elapsed = t - sentGen;
  if (elapsed <= 0) return 0;
  return Math.min(Math.max(0, distanceLy), LY_PER_GENERATION * elapsed);
}

/**
 * Opacity multiplier for an expanding sphere: it dims as it grows (a fixed amount of light
 * spread over a bigger shell) and dies off within `FADE_TAIL_GENERATIONS` of arriving.
 * `elapsedGen` is generations since launch, `travelGen` the flight time.
 */
export function expandingFade(elapsedGen: number, travelGen: number): number {
  if (elapsedGen <= 0) return 0;
  if (travelGen <= 0) return 0;
  const p = elapsedGen / travelGen;
  if (p <= 1) return 1 - (1 - ARRIVAL_OPACITY) * p;
  const over = elapsedGen - travelGen;
  return Math.max(0, ARRIVAL_OPACITY * (1 - over / FADE_TAIL_GENERATIONS));
}

/** Opacity of our transmission's sphere at scene time `t`. */
export function messageFade(sentGen: number, distanceLy: number, t: number): number {
  return expandingFade(t - sentGen, travelGenerations(distanceLy));
}

/**
 * The generation a reply left the star: `next_response_gen` is when it *lands* on Earth, and
 * it flew at light speed, so it started `distance / 25` generations earlier. The engine only
 * ever states the arrival, which is why this is derived here and not read off the state.
 */
export function replyLaunchGen(nextResponseGen: number, distanceLy: number): number {
  return nextResponseGen - travelGenerations(distanceLy);
}

/** Radius, in light-years, of an inbound reply's sphere (centred on the star). */
export function replyRadiusLy(nextResponseGen: number, distanceLy: number, t: number): number {
  const elapsed = t - replyLaunchGen(nextResponseGen, distanceLy);
  if (elapsed <= 0) return 0;
  return Math.min(Math.max(0, distanceLy), LY_PER_GENERATION * elapsed);
}

/** Opacity of an inbound reply's sphere. */
export function replyFade(nextResponseGen: number, distanceLy: number, t: number): number {
  return expandingFade(t - replyLaunchGen(nextResponseGen, distanceLy), travelGenerations(distanceLy));
}

/* ------------------------------------------------------------------ message pulses */

/**
 * How far along the Earth -> star line our transmission has got at scene time `t`, as a
 * fraction of the trip: `min(1, 25 * (t - generation) / distance)`, never below 0.
 *
 * This is the same physics as `messageRadiusLy` - the sphere's radius divided by the
 * distance - stated as a position rather than a size, because the pulse that carries the
 * "arrives Gen N" label travels *along* the line while the sphere expands around Earth.
 */
export function messageProgress(sentGen: number, distanceLy: number, t: number): number {
  const distance = Math.max(0, distanceLy);
  // A system at zero distance (nothing in the catalogue, but the arithmetic must not divide
  // by it) is reached the instant the message leaves.
  if (distance === 0) return t >= sentGen ? 1 : 0;
  return clamp01((LY_PER_GENERATION * (t - sentGen)) / distance);
}

/**
 * The same fraction for an inbound reply, measured from the star towards Earth. The engine
 * only states when the reply *lands* (`next_response_gen`), so the launch is walked back
 * through `replyLaunchGen` exactly as the reply sphere does.
 */
export function replyProgress(nextResponseGen: number, distanceLy: number, t: number): number {
  return messageProgress(replyLaunchGen(nextResponseGen, distanceLy), distanceLy, t);
}

/* ------------------------------------------------------------------ fleets and arks */

/**
 * The generation a fleet left its home star: it arrives at `arrival_gen` having crossed
 * `source_distance` at `speed_c * 25` LY per generation.
 */
export function fleetLaunchGen(
  arrivalGen: number,
  sourceDistanceLy: number,
  attackType: string | null | undefined,
): number {
  return arrivalGen - travelGenerations(sourceDistanceLy, attackSpeedC(attackType));
}

/** Fraction of the star -> Earth trajectory a fleet has covered at scene time `t`. */
export function fleetProgress(t: number, launchGen: number, arrivalGen: number): number {
  const span = arrivalGen - launchGen;
  if (span <= 0) return 1;
  return clamp01((t - launchGen) / span);
}

/** Fraction of the Earth -> target flight a Genesis ark has covered at scene time `t`. */
export function arkProgress(seedGen: number, arrivalGen: number, t: number): number {
  const span = arrivalGen - seedGen;
  if (span <= 0) return 1;
  return clamp01((t - seedGen) / span);
}

/* ------------------------------------------------------------------ leakage front */

/**
 * The leakage front in light-years at scene time `t`. `status.broadcast_radius` is its value
 * at `targetGen` (the generation the state describes), and it grows 25 LY per generation, so
 * mid-glide the front sits `25 * (targetGen - t)` behind that.
 */
export function leakageRadiusLy(broadcastRadiusLy: number, targetGen: number, t: number): number {
  return Math.max(0, broadcastRadiusLy - LY_PER_GENERATION * (targetGen - t));
}
