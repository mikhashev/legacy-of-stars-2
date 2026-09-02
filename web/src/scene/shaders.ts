/**
 * Every custom `ShaderMaterial` the W4 map uses, in one place. Five programs, no more:
 *
 * | factory | drawn by | used for |
 * |---|---|---|
 * | `createSphereMaterial` | `effects.ts`, `StarMap` | message spheres, reply spheres, the leakage front and its rim, every flash |
 * | `createMarkerMaterial` | `effects.ts` | fleet markers, Genesis ark markers, colony glows |
 * | `createBeamMaterial` | `effects.ts` | the `wow` beam towards Sagittarius |
 * | `createStarfieldMaterial` | `starfield.ts` | the twinkling background points |
 * | `createNebulaMaterial` | `starfield.ts` | the 2-octave value-noise nebula on a back-facing shell |
 *
 * Three.js caches compiled programs by shader source, so the dozens of sphere materials that
 * `effects.ts` creates (each needing its own colour/opacity uniforms) all share **one**
 * `WebGLProgram` - the plan's "everything in one ShaderMaterial for the spheres" (plan 6).
 *
 * Nothing here reads game state; the caller sets the uniforms every frame from `timeline.ts`.
 */
import { AdditiveBlending, BackSide, Color, DoubleSide, ShaderMaterial } from "three";

/* ---------------------------------------------------------------- sphere / fresnel */

const SPHERE_VERTEX = /* glsl */ `
varying vec3 vNormalW;
varying vec3 vViewDir;
void main() {
  vec4 world = modelMatrix * vec4(position, 1.0);
  vNormalW = normalize(mat3(modelMatrix) * normal);
  vViewDir = normalize(cameraPosition - world.xyz);
  gl_Position = projectionMatrix * viewMatrix * world;
}
`;

/**
 * A fresnel shell: brightness rises towards the limb, where the line of sight grazes the
 * surface, so an expanding sphere reads as a thin ring of light rather than a solid ball.
 * `uCore` lifts the whole body a little (message spheres want a hint of volume, the leakage
 * front wants none at all, which is what makes only its limb visible).
 */
const SPHERE_FRAGMENT = /* glsl */ `
uniform vec3 uColor;
uniform float uOpacity;
uniform float uRimPower;
uniform float uCore;
varying vec3 vNormalW;
varying vec3 vViewDir;
void main() {
  float facing = abs(dot(normalize(vNormalW), normalize(vViewDir)));
  float rim = pow(clamp(1.0 - facing, 0.0, 1.0), uRimPower);
  float alpha = uOpacity * (rim + uCore);
  if (alpha <= 0.002) discard;
  gl_FragColor = vec4(uColor * (0.4 + 0.9 * rim), alpha);
}
`;

export interface SphereMaterialOptions {
  color: number;
  opacity?: number;
  /** Higher = thinner rim. 3 is a crisp shell, 1.5 a soft haze. */
  rimPower?: number;
  /** 0 = limb only (the leakage front); 0.06 = a faint interior glow. */
  core?: number;
}

/** One translucent additive shell. Dispose it with `.dispose()` like any material. */
export function createSphereMaterial(options: SphereMaterialOptions): ShaderMaterial {
  return new ShaderMaterial({
    uniforms: {
      uColor: { value: new Color(options.color) },
      uOpacity: { value: options.opacity ?? 0.5 },
      uRimPower: { value: options.rimPower ?? 3 },
      uCore: { value: options.core ?? 0.05 },
    },
    vertexShader: SPHERE_VERTEX,
    fragmentShader: SPHERE_FRAGMENT,
    transparent: true,
    depthWrite: false,
    blending: AdditiveBlending,
    // The camera can end up inside the leakage front, so both faces must draw.
    side: DoubleSide,
  });
}

/* ---------------------------------------------------------------- markers */

const MARKER_VERTEX = /* glsl */ `
varying vec3 vNormalW;
varying vec3 vViewDir;
void main() {
  vec4 world = modelMatrix * vec4(position, 1.0);
  vNormalW = normalize(mat3(modelMatrix) * normal);
  vViewDir = normalize(cameraPosition - world.xyz);
  gl_Position = projectionMatrix * viewMatrix * world;
}
`;

/**
 * A small solid glow. `uPulse` is 0 for a marker that just sits there and 1 for one the
 * player must react to (a fleet at `eta <= 2`), which then throbs off the shared clock.
 */
const MARKER_FRAGMENT = /* glsl */ `
uniform vec3 uColor;
uniform float uOpacity;
uniform float uTime;
uniform float uPulse;
varying vec3 vNormalW;
varying vec3 vViewDir;
void main() {
  float facing = abs(dot(normalize(vNormalW), normalize(vViewDir)));
  float body = 0.55 + 0.45 * facing;
  float throb = 1.0 + uPulse * 0.75 * sin(uTime * 6.5);
  float alpha = clamp(uOpacity * body * throb, 0.0, 1.0);
  gl_FragColor = vec4(uColor * (0.7 + 0.6 * throb), alpha);
}
`;

export function createMarkerMaterial(color: number, opacity = 0.9): ShaderMaterial {
  return new ShaderMaterial({
    uniforms: {
      uColor: { value: new Color(color) },
      uOpacity: { value: opacity },
      uTime: { value: 0 },
      uPulse: { value: 0 },
    },
    vertexShader: MARKER_VERTEX,
    fragmentShader: MARKER_FRAGMENT,
    transparent: true,
    depthWrite: false,
    blending: AdditiveBlending,
  });
}

/* ---------------------------------------------------------------- beam */

const BEAM_VERTEX = /* glsl */ `
varying vec2 vUv;
void main() {
  vUv = uv;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`;

/**
 * A cylinder that lights up from its base outwards: `uHead` (0..1) is how far along the beam
 * the leading edge has travelled, with a shimmer running up the shaft behind it.
 */
const BEAM_FRAGMENT = /* glsl */ `
uniform vec3 uColor;
uniform float uOpacity;
uniform float uTime;
uniform float uHead;
varying vec2 vUv;
void main() {
  float head = smoothstep(uHead, uHead - 0.3, vUv.y);
  float tail = 1.0 - smoothstep(0.8, 1.0, vUv.y);
  float shimmer = 0.7 + 0.3 * sin(vUv.y * 42.0 - uTime * 7.0);
  float alpha = uOpacity * head * tail * shimmer;
  if (alpha <= 0.002) discard;
  gl_FragColor = vec4(uColor * (0.6 + 0.8 * shimmer), alpha);
}
`;

export function createBeamMaterial(color: number, opacity = 0.7): ShaderMaterial {
  return new ShaderMaterial({
    uniforms: {
      uColor: { value: new Color(color) },
      uOpacity: { value: opacity },
      uTime: { value: 0 },
      uHead: { value: 0 },
    },
    vertexShader: BEAM_VERTEX,
    fragmentShader: BEAM_FRAGMENT,
    transparent: true,
    depthWrite: false,
    blending: AdditiveBlending,
    side: DoubleSide,
  });
}

/* ---------------------------------------------------------------- background */

/**
 * Background points. `aColor`/`aSize`/`aPhase` are our own attributes (not three's `color`,
 * whose declaration depends on the `vertexColors` flag) so the program compiles the same way
 * in any three.js build. `uTime` only advances while something else on the map is animating,
 * so an idle page still issues no draw calls.
 */
const STARFIELD_VERTEX = /* glsl */ `
attribute vec3 aColor;
attribute float aSize;
attribute float aPhase;
uniform float uTime;
uniform float uPixelRatio;
varying vec3 vColor;
varying float vTwinkle;
void main() {
  vColor = aColor;
  vTwinkle = 0.55 + 0.45 * sin(uTime * 0.8 + aPhase * 6.2831853);
  gl_PointSize = aSize * uPixelRatio * (0.8 + 0.35 * vTwinkle);
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`;

const STARFIELD_FRAGMENT = /* glsl */ `
uniform float uOpacity;
varying vec3 vColor;
varying float vTwinkle;
void main() {
  vec2 d = gl_PointCoord - vec2(0.5);
  float r2 = dot(d, d);
  float disc = smoothstep(0.25, 0.0, r2);
  if (disc <= 0.002) discard;
  gl_FragColor = vec4(vColor * (0.5 + 0.9 * vTwinkle), disc * uOpacity * vTwinkle);
}
`;

export function createStarfieldMaterial(pixelRatio: number): ShaderMaterial {
  return new ShaderMaterial({
    uniforms: {
      uTime: { value: 0 },
      uOpacity: { value: 0.85 },
      uPixelRatio: { value: pixelRatio },
    },
    vertexShader: STARFIELD_VERTEX,
    fragmentShader: STARFIELD_FRAGMENT,
    transparent: true,
    depthWrite: false,
    blending: AdditiveBlending,
  });
}

/**
 * Two octaves of value noise over the view direction, on a back-facing shell. Deliberately
 * near-black: the brightest patch is well under the dimmest catalogue star, so the nebula
 * gives depth without competing with the data. `uOpacity` 0 hides it (the "Reduce effects"
 * toggle sets `visible = false` outright).
 */
const NEBULA_VERTEX = /* glsl */ `
varying vec3 vDir;
void main() {
  vDir = normalize(position);
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`;

const NEBULA_FRAGMENT = /* glsl */ `
uniform vec3 uColorA;
uniform vec3 uColorB;
uniform float uOpacity;
varying vec3 vDir;

float hash13(vec3 p) {
  return fract(sin(dot(p, vec3(12.9898, 78.233, 37.719))) * 43758.5453123);
}

float valueNoise(vec3 p) {
  vec3 i = floor(p);
  vec3 f = fract(p);
  vec3 u = f * f * (3.0 - 2.0 * f);
  float n000 = hash13(i + vec3(0.0, 0.0, 0.0));
  float n100 = hash13(i + vec3(1.0, 0.0, 0.0));
  float n010 = hash13(i + vec3(0.0, 1.0, 0.0));
  float n110 = hash13(i + vec3(1.0, 1.0, 0.0));
  float n001 = hash13(i + vec3(0.0, 0.0, 1.0));
  float n101 = hash13(i + vec3(1.0, 0.0, 1.0));
  float n011 = hash13(i + vec3(0.0, 1.0, 1.0));
  float n111 = hash13(i + vec3(1.0, 1.0, 1.0));
  float x00 = mix(n000, n100, u.x);
  float x10 = mix(n010, n110, u.x);
  float x01 = mix(n001, n101, u.x);
  float x11 = mix(n011, n111, u.x);
  return mix(mix(x00, x10, u.y), mix(x01, x11, u.y), u.z);
}

void main() {
  vec3 dir = normalize(vDir);
  // Two octaves, as per the plan; a third buys nothing at this brightness.
  float n = 0.65 * valueNoise(dir * 4.6) + 0.35 * valueNoise(dir * 10.3 + vec3(11.3));
  float clouds = smoothstep(0.34, 0.88, n);
  vec3 tint = mix(uColorA, uColorB, n);
  // Additive blending contributes rgb * alpha, so the cloud density belongs in the alpha
  // alone; squaring it here as well made the whole shell disappear.
  float alpha = clouds * uOpacity;
  if (alpha <= 0.002) discard;
  gl_FragColor = vec4(tint, alpha);
}
`;

export function createNebulaMaterial(): ShaderMaterial {
  return new ShaderMaterial({
    uniforms: {
      // Deep indigo into a cold teal. The brightest patch adds about 30/255 to a black sky,
      // an order of magnitude under a catalogue star's core, so the data stays dominant.
      uColorA: { value: new Color(0x3b4a86) },
      uColorB: { value: new Color(0x24616e) },
      uOpacity: { value: 0.8 },
    },
    vertexShader: NEBULA_VERTEX,
    fragmentShader: NEBULA_FRAGMENT,
    transparent: true,
    depthWrite: false,
    depthTest: false,
    blending: AdditiveBlending,
    side: BackSide,
  });
}
