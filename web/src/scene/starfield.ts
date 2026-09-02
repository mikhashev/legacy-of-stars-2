/**
 * The static background sky: a shell of dim points far outside the play area, so rotating
 * the camera gives the eye something to hold on to.
 *
 * Deliberately plain `Points` with a `PointsMaterial` - no shader. W4 replaces this with the
 * nebula/dark-forest fog material and keeps the same `Points` object, so the swap is a
 * material change rather than a scene change.
 */
import { AdditiveBlending, BufferAttribute, BufferGeometry, Points, PointsMaterial } from "three";

/** A starfield always owns exactly one geometry and one material, so `dispose()` is unambiguous. */
export type Starfield = Points<BufferGeometry, PointsMaterial>;

/** Radius of the background shell; far enough that it never crosses a star or a ring. */
export const STARFIELD_RADIUS = 900;

/** Mulberry32: a tiny deterministic PRNG, so the backdrop is identical on every run. */
function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/**
 * One `Points` object holding `count` background stars on a sphere of `STARFIELD_RADIUS`.
 * Call `.geometry.dispose()` and `.material.dispose()` on unmount (StarMap.dispose does).
 */
export function createStarfield(count = 1400, seed = 1977): Starfield {
  const random = mulberry32(seed);
  const positions = new Float32Array(count * 3);
  const colors = new Float32Array(count * 3);

  for (let i = 0; i < count; i += 1) {
    // Uniform over the sphere: z uniform in [-1, 1], azimuth uniform in [0, 2pi).
    const y = random() * 2 - 1;
    const azimuth = random() * Math.PI * 2;
    const ring = Math.sqrt(Math.max(0, 1 - y * y));
    positions[i * 3] = Math.cos(azimuth) * ring * STARFIELD_RADIUS;
    positions[i * 3 + 1] = y * STARFIELD_RADIUS;
    positions[i * 3 + 2] = Math.sin(azimuth) * ring * STARFIELD_RADIUS;

    // A faint spread from cool blue-white to warm, and a wide brightness range so the
    // field reads as depth rather than as noise.
    const brightness = 0.18 + random() * 0.5;
    const warmth = random();
    colors[i * 3] = brightness * (0.75 + warmth * 0.25);
    colors[i * 3 + 1] = brightness * 0.85;
    colors[i * 3 + 2] = brightness * (1 - warmth * 0.2);
  }

  const geometry = new BufferGeometry();
  geometry.setAttribute("position", new BufferAttribute(positions, 3));
  geometry.setAttribute("color", new BufferAttribute(colors, 3));

  const material = new PointsMaterial({
    size: 1.6,
    sizeAttenuation: false,
    vertexColors: true,
    transparent: true,
    opacity: 0.7,
    depthWrite: false,
    blending: AdditiveBlending,
  });

  const points: Starfield = new Points(geometry, material);
  points.name = "starfield";
  // Always behind everything else, and never picked by the raycaster.
  points.renderOrder = -1;
  points.frustumCulled = false;
  return points;
}
