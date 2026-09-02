/**
 * The background sky: a shell of sparse twinkling points plus a very faint nebula, both on
 * custom shaders (`shaders.ts`). W3 drew a plain `PointsMaterial`; W4 keeps the same geometry
 * and swaps the material, so nothing else about the scene graph changed.
 *
 * "Dark forest" fog: an undiscovered direction is simply black. The engine only lists systems
 * it has resolved (`ViewState.systems[]`), so an unexplored quarter of the sky shows nothing
 * but these background points - there is no sprite to lift, and adding a grey haze around the
 * discovered ones was tried and dropped: it washed out the dim `knowledge = 0` stars, which
 * are exactly the ones the player needs to be able to pick out.
 */
import { BufferAttribute, BufferGeometry, Mesh, Points, ShaderMaterial, SphereGeometry } from "three";
import { createNebulaMaterial, createStarfieldMaterial } from "./shaders";

/** A starfield always owns exactly one geometry and one material, so `dispose()` is unambiguous. */
export type Starfield = Points<BufferGeometry, ShaderMaterial>;

/** The nebula shell: one geometry, one material, same disposal contract. */
export type Nebula = Mesh<SphereGeometry, ShaderMaterial>;

/** Radius of the background shell; far enough that it never crosses a star or a ring. */
export const STARFIELD_RADIUS = 900;

/** The nebula sits just outside the points, still well inside the camera's far plane. */
export const NEBULA_RADIUS = 960;

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
 * One `Points` object holding `count` background stars on a sphere of `STARFIELD_RADIUS`,
 * each with its own size and twinkle phase. Advance `material.uniforms.uTime` to animate.
 * Call `.geometry.dispose()` and `.material.dispose()` on unmount (StarMap.dispose does).
 */
export function createStarfield(pixelRatio: number, count = 1400, seed = 1977): Starfield {
  const random = mulberry32(seed);
  const positions = new Float32Array(count * 3);
  const colors = new Float32Array(count * 3);
  const sizes = new Float32Array(count);
  const phases = new Float32Array(count);

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

    // A handful of noticeably bigger points give the eye something to fix on while orbiting.
    const roll = random();
    sizes[i] = roll > 0.97 ? 2.6 : roll > 0.85 ? 1.9 : 1.3;
    phases[i] = random();
  }

  const geometry = new BufferGeometry();
  geometry.setAttribute("position", new BufferAttribute(positions, 3));
  geometry.setAttribute("aColor", new BufferAttribute(colors, 3));
  geometry.setAttribute("aSize", new BufferAttribute(sizes, 1));
  geometry.setAttribute("aPhase", new BufferAttribute(phases, 1));

  const points: Starfield = new Points(geometry, createStarfieldMaterial(pixelRatio));
  points.name = "starfield";
  // Always behind everything else, and never picked by the raycaster.
  points.renderOrder = -1;
  points.frustumCulled = false;
  return points;
}

/**
 * The nebula shell. Back-facing, so it is only ever seen from the inside, and dark enough
 * that the map's stars stay dominant. `visible = false` is how "Reduce effects" turns it off.
 */
export function createNebula(): Nebula {
  const nebula: Nebula = new Mesh(new SphereGeometry(NEBULA_RADIUS, 32, 24), createNebulaMaterial());
  nebula.name = "nebula";
  nebula.renderOrder = -2;
  nebula.frustumCulled = false;
  return nebula;
}
