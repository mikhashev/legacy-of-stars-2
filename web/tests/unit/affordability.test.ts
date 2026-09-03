/**
 * Unit tests for `src/affordability.ts` (run with `npm run unit`): the tech dialog's
 * affordable-now marker (Dialogs.tsx TechDialog).
 */
import { describe, expect, it } from "vitest";
import { affordabilityOf } from "../../src/affordability";

describe("affordabilityOf", () => {
  it("affordable when the cost is exactly what is on hand", () => {
    expect(affordabilityOf(10, 10)).toBe(true);
  });

  it("affordable when the cost is below what is on hand", () => {
    expect(affordabilityOf(5, 10)).toBe(true);
  });

  it("unaffordable when the cost exceeds what is on hand", () => {
    expect(affordabilityOf(11, 10)).toBe(false);
  });

  it("unaffordable with zero research points and any positive cost", () => {
    expect(affordabilityOf(1, 0)).toBe(false);
  });

  it("a free (zero-cost) technology is always affordable", () => {
    expect(affordabilityOf(0, 0)).toBe(true);
  });
});
