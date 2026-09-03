/**
 * Sky coordinates -> scene coordinates. Pure functions only: no Three.js, no DOM, so
 * `tests/unit/coords.test.ts` can exercise them directly.
 *
 * The engine hands out `ra`/`dec` in J2000 degrees and `distance` in light-years
 * (docs/reference/web_contract.md 6, `systems[].ra/.dec/.distance`). The plan's W3 conversion puts
 * the y axis on the north celestial pole:
 *
 *     x = d * cos(dec) * cos(ra)
 *     y = d * sin(dec)
 *     z = d * cos(dec) * sin(ra)
 *
 * Distance is compressed before it becomes a radius, because the catalogue spans 4.24 LY
 * (Proxima) to 159 LY (HD 209458) and the WOW! source sits at 1,800 LY; drawn to scale the
 * near stars would collapse into one pixel at the middle of the screen.
 */

const DEG = Math.PI / 180;

/**
 * `data/star_catalog.json` tops out here; both scales pin this distance to the same radius.
 * The T4 catalogue runs to 159 LY, so the edge is rounded up to a round 160.
 */
export const CATALOG_EDGE_LY = 160;

/** Scene radius the catalogue edge maps to. The default camera frames a little more than this. */
export const CATALOG_EDGE_RADIUS = 60;

/**
 * The rim of the scene. Anything further than the catalogue - in practice only the WOW!
 * source at 1,800 LY - is pinned here, in its true direction, in both scale modes.
 */
export const EDGE_RADIUS = 72;

/** `d0` in `r = k * ln(1 + d/d0)`: the scale below which distances stay nearly linear. */
export const LOG_SOFTENING_LY = 4;

/** `k`, solved from `k * ln(1 + 160/4) = 60`, so the catalogue edge lands on CATALOG_EDGE_RADIUS. */
export const LOG_K = CATALOG_EDGE_RADIUS / Math.log(1 + CATALOG_EDGE_LY / LOG_SOFTENING_LY);

/** `k2`, solved from `160 * k2 = 60`: the "true scale" toggle keeps the same outer ring. */
export const TRUE_K = CATALOG_EDGE_RADIUS / CATALOG_EDGE_LY;

/** Distances (LY) the orientation rings are drawn at; 20 and 100 are also detection reaches. */
export const RING_DISTANCES_LY = [5, 10, 20, 50, 100] as const;

export type ScaleMode = "compressed" | "true";

export interface Vec3 {
  x: number;
  y: number;
  z: number;
}

/** The scene radius a distance in light-years maps to, clamped to the rim. */
export function radiusFor(distanceLy: number, mode: ScaleMode): number {
  const d = Math.max(0, distanceLy);
  const raw = mode === "true" ? d * TRUE_K : LOG_K * Math.log(1 + d / LOG_SOFTENING_LY);
  return Math.min(raw, EDGE_RADIUS);
}

/** True when `radiusFor` had to pin this distance to the rim (the WOW! source, 1,800 LY). */
export function isBeyondRim(distanceLy: number, mode: ScaleMode): boolean {
  const d = Math.max(0, distanceLy);
  const raw = mode === "true" ? d * TRUE_K : LOG_K * Math.log(1 + d / LOG_SOFTENING_LY);
  return raw > EDGE_RADIUS;
}

/** Unit vector for a J2000 direction, y towards the north celestial pole. */
export function direction(raDeg: number, decDeg: number): Vec3 {
  const ra = raDeg * DEG;
  const dec = decDeg * DEG;
  const cosDec = Math.cos(dec);
  return { x: cosDec * Math.cos(ra), y: Math.sin(dec), z: cosDec * Math.sin(ra) };
}

/** Scene position of a star at (ra, dec, distance). */
export function positionFor(raDeg: number, decDeg: number, distanceLy: number, mode: ScaleMode): Vec3 {
  const unit = direction(raDeg, decDeg);
  const r = radiusFor(distanceLy, mode);
  return { x: unit.x * r, y: unit.y * r, z: unit.z * r };
}

/** FNV-1a, 32-bit: a small deterministic hash so a name always yields the same sky position. */
function hash32(text: string): number {
  let h = 0x811c9dc5;
  for (let i = 0; i < text.length; i += 1) {
    h ^= text.charCodeAt(i);
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return h >>> 0;
}

/**
 * A stand-in direction for a system the engine gave no `ra`/`dec` for (synthetic systems in
 * a future content pack; every star in `data/star_catalog.json` has real coordinates). The
 * result is deterministic per name and spread evenly over the sphere, so such a star does
 * not drift between renders or between sessions.
 */
export function fallbackDirection(name: string): { ra: number; dec: number } {
  const a = hash32(name);
  const b = hash32(`${name}#dec`);
  const ra = (a / 0x100000000) * 360;
  // asin of a uniform value in [-1, 1] gives declinations uniform over the sphere's area,
  // instead of piling up at the poles.
  const dec = (Math.asin((b / 0x100000000) * 2 - 1) / DEG);
  return { ra, dec };
}

/** What `positionForSystem` needs off a `ViewState.systems[]` entry. */
export interface SystemPoint {
  name: string;
  ra: number | null;
  dec: number | null;
  distance: number;
}

/** Scene position of a system, falling back to a name-derived direction when ra/dec are null. */
export function positionForSystem(system: SystemPoint, mode: ScaleMode): Vec3 {
  const { ra, dec } =
    system.ra !== null && system.dec !== null
      ? { ra: system.ra, dec: system.dec }
      : fallbackDirection(system.name);
  return positionFor(ra, dec, system.distance, mode);
}

/** "1,800 LY" / "4.2 LY" - the label under a star name. */
export function formatDistance(distanceLy: number): string {
  const rounded = distanceLy >= 100 ? Math.round(distanceLy) : Math.round(distanceLy * 10) / 10;
  return `${rounded.toLocaleString("en-US")} LY`;
}

/**
 * A calendar year for display, with years at or before zero written as BC. The engine's
 * `format_year` does exactly the same (`src/legacy_of_stars_v3.py`), on the astronomical
 * convention: year 0 is 1 BC, year -1 is 2 BC.
 */
export function formatYear(year: number): string {
  const y = Math.round(year);
  return y > 0 ? String(y) : `${1 - y} BC`;
}

/**
 * "observed as of 1973 (4.2 LY of light-time)" - the honest caption for anything the
 * telescopes say about a system. `observedYear` is the engine's `systems[].observed_year`;
 * nothing here recomputes it.
 */
export function observedAsOf(observedYear: number, distanceLy: number): string {
  return `observed as of ${formatYear(observedYear)} (${formatDistance(distanceLy)} of light-time)`;
}
