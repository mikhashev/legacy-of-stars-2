/**
 * Unit tests for `src/scene/timeline.ts` (run with `npm run unit`).
 *
 * These are the numbers every W4 animation is drawn from, so they are checked against the
 * game's own physics rather than against the implementation: 25 light-years per generation at
 * light speed, and the fraction of c each attack type is labelled with in
 * `docs/reference/web_contract.md` ("fusion strike fleet (0.12c)").
 */
import { describe, expect, it } from "vitest";
import {
  ARK_SPEED_C,
  DEFAULT_ATTACK_SPEED_C,
  LY_PER_GENERATION,
  arkProgress,
  attackSpeedC,
  easeInOut,
  fleetLaunchGen,
  fleetProgress,
  leakageRadiusLy,
  messageFade,
  messageProgress,
  messageRadiusLy,
  replyFade,
  replyProgress,
  replyLaunchGen,
  replyRadiusLy,
  travelGenerations,
} from "../../src/scene/timeline";

/** Proxima Centauri, the nearest catalogue star: a message gets there in a fifth of a turn. */
const PROXIMA_LY = 4.24;
/** Vega: 25 LY, i.e. exactly one generation of light travel. */
const VEGA_LY = 25;

describe("scene-time basics", () => {
  it("moves light 25 light-years per generation", () => {
    expect(LY_PER_GENERATION).toBe(25);
    expect(travelGenerations(VEGA_LY)).toBeCloseTo(1, 12);
    expect(travelGenerations(PROXIMA_LY)).toBeCloseTo(0.1696, 4);
  });

  it("eases in and out between the two generations it connects", () => {
    expect(easeInOut(0)).toBe(0);
    expect(easeInOut(1)).toBe(1);
    expect(easeInOut(0.5)).toBeCloseTo(0.5, 12);
    // Clamped, and monotonic in between.
    expect(easeInOut(-3)).toBe(0);
    expect(easeInOut(7)).toBe(1);
    let previous = 0;
    for (let i = 1; i <= 20; i += 1) {
      const value = easeInOut(i / 20);
      expect(value).toBeGreaterThan(previous);
      previous = value;
    }
    // Slow at the ends, fast in the middle.
    expect(easeInOut(0.1)).toBeLessThan(0.1);
    expect(easeInOut(0.9)).toBeGreaterThan(0.9);
  });
});

describe("message light spheres", () => {
  it("has no sphere before the transmission leaves", () => {
    expect(messageRadiusLy(5, VEGA_LY, 4.9)).toBe(0);
    expect(messageRadiusLy(5, VEGA_LY, 5)).toBe(0);
    expect(messageFade(5, VEGA_LY, 4.5)).toBe(0);
  });

  it("expands at 25 LY per generation and stops at the target", () => {
    expect(messageRadiusLy(5, VEGA_LY, 5.5)).toBeCloseTo(12.5, 12);
    expect(messageRadiusLy(5, VEGA_LY, 6)).toBeCloseTo(25, 12);
    // Past the star the light has already arrived: the drawn sphere stops growing.
    expect(messageRadiusLy(5, VEGA_LY, 9)).toBeCloseTo(25, 12);
  });

  it("reaches Proxima Centauri a fifth of the way through one generation", () => {
    expect(messageRadiusLy(1, PROXIMA_LY, 1.1)).toBeCloseTo(2.5, 12);
    expect(messageRadiusLy(1, PROXIMA_LY, 1.17)).toBeCloseTo(PROXIMA_LY, 6);
    expect(messageRadiusLy(1, PROXIMA_LY, 2)).toBeCloseTo(PROXIMA_LY, 12);
  });

  it("dims as it grows and is gone shortly after it lands", () => {
    const early = messageFade(5, VEGA_LY, 5.1);
    const late = messageFade(5, VEGA_LY, 5.9);
    expect(early).toBeGreaterThan(late);
    expect(early).toBeLessThanOrEqual(1);
    // At the moment of arrival it still has something left, and 0.35 generations later none.
    expect(messageFade(5, VEGA_LY, 6)).toBeCloseTo(0.55, 6);
    expect(messageFade(5, VEGA_LY, 6.35)).toBeCloseTo(0, 6);
    expect(messageFade(5, VEGA_LY, 7)).toBe(0);
  });
});

describe("reply spheres", () => {
  it("starts at the star `distance / 25` generations before it lands on Earth", () => {
    // A reply landing in generation 10 from 25 LY away left the star in generation 9.
    expect(replyLaunchGen(10, VEGA_LY)).toBeCloseTo(9, 12);
    expect(replyLaunchGen(10, PROXIMA_LY)).toBeCloseTo(10 - 0.1696, 4);
    // 51 LY, the catalogue's edge: just over two generations of flight.
    expect(replyLaunchGen(20, 51)).toBeCloseTo(20 - 2.04, 6);
  });

  it("is nothing before the launch, and exactly the distance on arrival", () => {
    expect(replyRadiusLy(10, VEGA_LY, 8.5)).toBe(0);
    expect(replyRadiusLy(10, VEGA_LY, 9)).toBe(0);
    expect(replyRadiusLy(10, VEGA_LY, 9.5)).toBeCloseTo(12.5, 12);
    expect(replyRadiusLy(10, VEGA_LY, 10)).toBeCloseTo(VEGA_LY, 12);
    expect(replyRadiusLy(10, VEGA_LY, 11)).toBeCloseTo(VEGA_LY, 12);
  });

  it("fades on the same curve as an outgoing sphere", () => {
    expect(replyFade(10, VEGA_LY, 8.9)).toBe(0);
    expect(replyFade(10, VEGA_LY, 10)).toBeCloseTo(0.55, 6);
    expect(replyFade(10, VEGA_LY, 10.35)).toBeCloseTo(0, 6);
  });
});

describe("fleets", () => {
  it("knows each attack type's fraction of c", () => {
    expect(attackSpeedC("fleet")).toBe(0.1);
    expect(attackSpeedC("laser_sail_probe")).toBe(0.175);
    expect(attackSpeedC("fusion_strike")).toBe(0.12);
    expect(attackSpeedC("genesis_fleet")).toBe(0.1);
    expect(attackSpeedC("mirror_fleet")).toBe(0.1);
    // `wow_fleet` carries no stated speed, and neither does a future type.
    expect(attackSpeedC("wow_fleet")).toBe(DEFAULT_ATTACK_SPEED_C);
    expect(attackSpeedC(null)).toBe(DEFAULT_ATTACK_SPEED_C);
    expect(attackSpeedC("something_new")).toBe(DEFAULT_ATTACK_SPEED_C);
  });

  it("works the launch generation back from the arrival the engine stated", () => {
    // 10 LY at 0.1c = 2.5 LY per generation = 4 generations.
    expect(fleetLaunchGen(20, 10, "fleet")).toBeCloseTo(16, 12);
    // 0.175c = 4.375 LY per generation.
    expect(fleetLaunchGen(20, 10, "laser_sail_probe")).toBeCloseTo(20 - 10 / 4.375, 12);
    // 0.12c = 3 LY per generation.
    expect(fleetLaunchGen(20, 10, "fusion_strike")).toBeCloseTo(20 - 10 / 3, 12);
    // A faster fleet leaves later for the same arrival.
    expect(fleetLaunchGen(20, 10, "laser_sail_probe")).toBeGreaterThan(fleetLaunchGen(20, 10, "fleet"));
  });

  it("covers the trajectory linearly and clamps at both ends", () => {
    const launch = fleetLaunchGen(20, 10, "fleet");
    expect(fleetProgress(launch, launch, 20)).toBe(0);
    expect(fleetProgress(18, launch, 20)).toBeCloseTo(0.5, 12);
    expect(fleetProgress(20, launch, 20)).toBe(1);
    // Before the launch and after the arrival it stays pinned.
    expect(fleetProgress(10, launch, 20)).toBe(0);
    expect(fleetProgress(99, launch, 20)).toBe(1);
    // A degenerate span (an attack that arrives the generation it is detected) is "arrived".
    expect(fleetProgress(5, 7, 7)).toBe(1);
  });
});

describe("Genesis arks", () => {
  it("interpolates between the engine's seed and arrival generations", () => {
    expect(ARK_SPEED_C).toBe(0.12);
    expect(arkProgress(4, 12, 4)).toBe(0);
    expect(arkProgress(4, 12, 8)).toBeCloseTo(0.5, 12);
    expect(arkProgress(4, 12, 12)).toBe(1);
    expect(arkProgress(4, 12, 30)).toBe(1);
    expect(arkProgress(4, 12, 1)).toBe(0);
  });
});

describe("the leakage front", () => {
  it("is the engine's broadcast radius at the generation it describes", () => {
    expect(leakageRadiusLy(100, 4, 4)).toBeCloseTo(100, 12);
  });

  it("lags 25 LY per generation of scene time behind it", () => {
    expect(leakageRadiusLy(100, 4, 3.5)).toBeCloseTo(87.5, 12);
    expect(leakageRadiusLy(100, 4, 3)).toBeCloseTo(75, 12);
    // Never negative: the front did not exist before the programme started transmitting.
    expect(leakageRadiusLy(25, 1, -5)).toBe(0);
  });
});

describe("message and reply pulses", () => {
  it("does not leave Earth before the generation it was sent in", () => {
    expect(messageProgress(3, PROXIMA_LY, 2)).toBe(0);
    expect(messageProgress(3, PROXIMA_LY, 3)).toBe(0);
  });

  it("covers 25 light-years of the trip per generation", () => {
    // Vega is exactly one generation of light travel away.
    expect(messageProgress(1, VEGA_LY, 1.5)).toBeCloseTo(0.5, 12);
    expect(messageProgress(1, VEGA_LY, 2)).toBe(1);
    // Proxima at 4.24 LY is reached a sixth of the way through the generation.
    expect(messageProgress(1, PROXIMA_LY, 1 + 4.24 / 25)).toBeCloseTo(1, 12);
    expect(messageProgress(1, PROXIMA_LY, 1.05)).toBeCloseTo((25 * 0.05) / 4.24, 12);
  });

  it("stops at the star and stays there", () => {
    expect(messageProgress(1, PROXIMA_LY, 4)).toBe(1);
    expect(messageProgress(1, VEGA_LY, 99)).toBe(1);
  });

  it("agrees with the expanding sphere it belongs to", () => {
    for (const t of [1.1, 1.4, 1.9, 2.3]) {
      expect(messageProgress(1, VEGA_LY, t)).toBeCloseTo(messageRadiusLy(1, VEGA_LY, t) / VEGA_LY, 12);
    }
  });

  it("walks a reply back from the arrival generation the engine states", () => {
    // A reply landing in generation 5 from 25 LY away left the star in generation 4.
    expect(replyProgress(5, VEGA_LY, 4)).toBe(0);
    expect(replyProgress(5, VEGA_LY, 3)).toBe(0);
    expect(replyProgress(5, VEGA_LY, 4.5)).toBeCloseTo(0.5, 12);
    expect(replyProgress(5, VEGA_LY, 5)).toBe(1);
    expect(replyProgress(5, VEGA_LY, 6)).toBe(1);
  });

  it("treats a zero distance as arrived the moment it is sent", () => {
    expect(messageProgress(2, 0, 1)).toBe(0);
    expect(messageProgress(2, 0, 2)).toBe(1);
  });
});
