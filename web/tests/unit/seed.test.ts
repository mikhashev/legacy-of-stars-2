/**
 * Unit tests for `src/seed.ts` (run with `npm run unit`): the New Game seed field must accept
 * any non-empty text (finding 4 - a playtester's alphanumeric seed used to be rejected outright).
 */
import { describe, expect, it } from "vitest";
import { fnv1a32, resolveSeed, seedPreview } from "../../src/seed";

describe("fnv1a32", () => {
  it("is stable for the same input", () => {
    expect(fnv1a32("ark-playtest-0903")).toBe(fnv1a32("ark-playtest-0903"));
  });

  it("differs for different input", () => {
    expect(fnv1a32("ark-playtest-0903")).not.toBe(fnv1a32("ark-playtest-0904"));
  });

  it("is always a non-negative 32-bit integer", () => {
    for (const text of ["", "a", "Legacy of Stars", "ark-playtest-0903"]) {
      const hash = fnv1a32(text);
      expect(Number.isInteger(hash)).toBe(true);
      expect(hash).toBeGreaterThanOrEqual(0);
      expect(hash).toBeLessThanOrEqual(0xffffffff);
    }
  });
});

describe("resolveSeed", () => {
  it("passes a plain integer straight through", () => {
    expect(resolveSeed("42")).toBe(42);
    expect(resolveSeed("1234567")).toBe(1234567);
  });

  it("passes a negative integer straight through", () => {
    expect(resolveSeed("-7")).toBe(-7);
  });

  it("hashes anything that is not a plain integer", () => {
    expect(resolveSeed("ark-playtest-0903")).toBe(fnv1a32("ark-playtest-0903"));
    expect(resolveSeed("3.14")).toBe(fnv1a32("3.14"));
  });

  it("is deterministic: the same text always resolves to the same seed", () => {
    expect(resolveSeed("ark-playtest-0903")).toBe(resolveSeed("ark-playtest-0903"));
  });
});

describe("seedPreview", () => {
  it("null for an empty (random) field", () => {
    expect(seedPreview("")).toBeNull();
    expect(seedPreview("   ")).toBeNull();
  });

  it("names the seed plainly for a plain integer", () => {
    expect(seedPreview("42")).toBe("seed 42");
  });

  it("names the effective seed and the original text for a hashed one", () => {
    const hashed = fnv1a32("ark-playtest-0903");
    expect(seedPreview("ark-playtest-0903")).toBe(`seed ${hashed} from 'ark-playtest-0903'`);
  });
});
