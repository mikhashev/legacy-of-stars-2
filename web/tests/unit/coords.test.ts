/**
 * Unit tests for `src/scene/coords.ts` (run with `npm run unit`).
 *
 * The sky positions are the ones in `data/star_catalog.json`, which are the real J2000
 * values; the directional assertions are what a planetarium shows (the plan's W3
 * verification step: "compare Sirius, Vega, Proxima against a planetarium").
 */
import { describe, expect, it } from "vitest";
import {
  CATALOG_EDGE_LY,
  CATALOG_EDGE_RADIUS,
  EDGE_RADIUS,
  direction,
  fallbackDirection,
  formatDistance,
  isBeyondRim,
  positionFor,
  positionForSystem,
  radiusFor,
} from "../../src/scene/coords";

/** Catalogue entries used below, verbatim from data/star_catalog.json. */
const SIRIUS = { ra: 101.29, dec: -16.72, distance: 8.6 };
const VEGA = { ra: 279.23, dec: 38.78, distance: 25.0 };
const PROXIMA = { ra: 217.43, dec: -62.68, distance: 4.24 };
/** The 1977 burst's disputed source (src/wow_signal_event.py). */
const WOW = { ra: 293.7, dec: -27.0, distance: 1800 };

function length(v: { x: number; y: number; z: number }): number {
  return Math.hypot(v.x, v.y, v.z);
}

describe("direction", () => {
  it("puts Sirius south of the celestial equator, towards +z", () => {
    const v = direction(SIRIUS.ra, SIRIUS.dec);
    expect(length(v)).toBeCloseTo(1, 12);
    // dec -16.72 deg -> sin(dec) = -0.2877: below the equator.
    expect(v.y).toBeCloseTo(Math.sin((-16.72 * Math.PI) / 180), 10);
    expect(v.y).toBeLessThan(0);
    // RA 101.29 deg is just past 90 deg, so the direction is dominated by +z with a small -x.
    expect(v.z).toBeGreaterThan(0.9);
    expect(v.x).toBeLessThan(0);
  });

  it("puts Vega high in the north, in the +x/-z quadrant", () => {
    const v = direction(VEGA.ra, VEGA.dec);
    expect(v.y).toBeCloseTo(Math.sin((38.78 * Math.PI) / 180), 10);
    expect(v.y).toBeGreaterThan(0.6);
    // RA 279.23 deg: fourth quadrant, cos > 0 and sin < 0.
    expect(v.x).toBeGreaterThan(0);
    expect(v.z).toBeLessThan(0);
  });

  it("puts Proxima Centauri further south than Sirius", () => {
    const proxima = direction(PROXIMA.ra, PROXIMA.dec);
    const sirius = direction(SIRIUS.ra, SIRIUS.dec);
    expect(proxima.y).toBeCloseTo(Math.sin((-62.68 * Math.PI) / 180), 10);
    expect(proxima.y).toBeLessThan(sirius.y);
    expect(proxima.y).toBeLessThan(-0.85);
  });
});

describe("radiusFor", () => {
  it("is strictly increasing with distance in both scales", () => {
    const distances = [0, 1, 4.24, 8.6, 11.9, 25, 40, 51];
    for (const mode of ["compressed", "true"] as const) {
      const radii = distances.map((d) => radiusFor(d, mode));
      for (let i = 1; i < radii.length; i += 1) {
        expect(radii[i]!).toBeGreaterThan(radii[i - 1]!);
      }
    }
  });

  it("pins the catalogue's outer edge to the same radius in both scales", () => {
    expect(radiusFor(CATALOG_EDGE_LY, "compressed")).toBeCloseTo(CATALOG_EDGE_RADIUS, 10);
    expect(radiusFor(CATALOG_EDGE_LY, "true")).toBeCloseTo(CATALOG_EDGE_RADIUS, 10);
  });

  it("spreads the nearby stars out that true scale crowds together", () => {
    // The whole point of the compression: Proxima (4.24 LY) and Sirius (8.6 LY) must be
    // further apart on screen than a linear scale would put them.
    const compressed = radiusFor(SIRIUS.distance, "compressed") - radiusFor(PROXIMA.distance, "compressed");
    const trueScale = radiusFor(SIRIUS.distance, "true") - radiusFor(PROXIMA.distance, "true");
    expect(compressed).toBeGreaterThan(trueScale * 1.5);
  });

  it("clamps the WOW! source at 1,800 LY to the rim in both scales", () => {
    expect(radiusFor(WOW.distance, "compressed")).toBe(EDGE_RADIUS);
    expect(radiusFor(WOW.distance, "true")).toBe(EDGE_RADIUS);
    expect(isBeyondRim(WOW.distance, "compressed")).toBe(true);
    expect(isBeyondRim(WOW.distance, "true")).toBe(true);
    expect(isBeyondRim(CATALOG_EDGE_LY, "compressed")).toBe(false);
  });
});

describe("positionFor", () => {
  it("keeps the WOW! source's true direction while pinning its radius", () => {
    const position = positionFor(WOW.ra, WOW.dec, WOW.distance, "compressed");
    expect(length(position)).toBeCloseTo(EDGE_RADIUS, 10);
    const unit = direction(WOW.ra, WOW.dec);
    expect(position.x / EDGE_RADIUS).toBeCloseTo(unit.x, 10);
    expect(position.y / EDGE_RADIUS).toBeCloseTo(unit.y, 10);
    expect(position.z / EDGE_RADIUS).toBeCloseTo(unit.z, 10);
    // Sagittarius: south of the equator (dec -27), RA 293.7 deg -> +x, -z.
    expect(position.y).toBeLessThan(0);
    expect(position.x).toBeGreaterThan(0);
    expect(position.z).toBeLessThan(0);
  });
});

describe("fallbackDirection", () => {
  it("is deterministic, on the sphere, and different per name", () => {
    const a = fallbackDirection("Synthetic Alpha");
    const b = fallbackDirection("Synthetic Alpha");
    const c = fallbackDirection("Synthetic Beta");
    expect(a).toEqual(b);
    expect(a).not.toEqual(c);
    expect(a.ra).toBeGreaterThanOrEqual(0);
    expect(a.ra).toBeLessThan(360);
    expect(Math.abs(a.dec)).toBeLessThanOrEqual(90);
    expect(length(direction(a.ra, a.dec))).toBeCloseTo(1, 12);
  });

  it("is what positionForSystem uses when the engine gave no ra/dec", () => {
    const system = { name: "Synthetic Alpha", ra: null, dec: null, distance: 12 };
    const position = positionForSystem(system, "compressed");
    const expected = fallbackDirection(system.name);
    expect(position).toEqual(positionFor(expected.ra, expected.dec, 12, "compressed"));
    expect(length(position)).toBeCloseTo(radiusFor(12, "compressed"), 10);
  });

  it("uses the real coordinates whenever the engine supplied them", () => {
    const system = { name: "Sirius", ra: SIRIUS.ra, dec: SIRIUS.dec, distance: SIRIUS.distance };
    expect(positionForSystem(system, "true")).toEqual(
      positionFor(SIRIUS.ra, SIRIUS.dec, SIRIUS.distance, "true"),
    );
  });
});

describe("formatDistance", () => {
  it("groups thousands and keeps one decimal for nearby stars", () => {
    expect(formatDistance(1800)).toBe("1,800 LY");
    expect(formatDistance(4.24)).toBe("4.2 LY");
    expect(formatDistance(51)).toBe("51 LY");
  });
});
