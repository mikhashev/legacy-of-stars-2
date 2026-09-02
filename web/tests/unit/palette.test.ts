/**
 * Unit tests for `src/scene/palette.ts` (run with `npm run unit`).
 *
 * The inputs are the exact strings the engine produces: `spectral_type` values from
 * `data/star_catalog.json` (plus the WOW! source's annotated one from
 * `src/wow_signal_event.py`) and `description` sentences from
 * `StarSystem.describe_civilization()`.
 */
import { describe, expect, it } from "vitest";
import { luminosityClass, moodFor, spectralClass, styleFor } from "../../src/scene/palette";

describe("spectralClass", () => {
  it("reads the Harvard letter off every form the catalogue uses", () => {
    expect(spectralClass("M5.5V")).toBe("M");
    expect(spectralClass("A1V")).toBe("A");
    expect(spectralClass("F5IV-V")).toBe("F");
    expect(spectralClass("G8III")).toBe("G");
    expect(spectralClass("K1.5III")).toBe("K");
    expect(spectralClass("DZ8")).toBe("D");
  });

  it("handles the WOW! source's annotated type and an unknown one", () => {
    expect(spectralClass("G2V? (candidate 2MASS 19281982-2640123)")).toBe("G");
    expect(spectralClass(null)).toBe("?");
    expect(spectralClass("")).toBe("?");
    expect(spectralClass("weird")).toBe("?");
  });
});

describe("luminosityClass", () => {
  it("reads the Yerkes numerals, taking the first of a range", () => {
    expect(luminosityClass("G8III")).toBe("III");
    expect(luminosityClass("K0III")).toBe("III");
    expect(luminosityClass("G8IV")).toBe("IV");
    expect(luminosityClass("F5IV-V")).toBe("IV");
    expect(luminosityClass("M5.5V")).toBe("V");
    expect(luminosityClass("G2V? (candidate 2MASS 19281982-2640123)")).toBe("V");
  });

  it("does not mistake a white dwarf code for a luminosity class", () => {
    expect(luminosityClass("DZ8")).toBeNull();
    expect(luminosityClass(null)).toBeNull();
  });
});

describe("styleFor", () => {
  it("colours the sequence from blue through white to red-orange", () => {
    const classes = ["O5V", "B2V", "A1V", "F5V", "G2V", "K2V", "M5V"].map((t) => styleFor(t).color);
    expect(new Set(classes).size).toBe(classes.length);
    // Blue end: more blue than red. Red end: the other way round.
    const o = styleFor("O5V").color;
    const m = styleFor("M5V").color;
    expect(o & 0xff).toBeGreaterThan((o >> 16) & 0xff);
    expect((m >> 16) & 0xff).toBeGreaterThan(m & 0xff);
    expect(styleFor(null).color).toBe(styleFor("weird").color);
  });

  it("draws giants larger and white dwarfs smaller", () => {
    expect(styleFor("G8III").size).toBeGreaterThan(styleFor("G2V").size);
    expect(styleFor("DZ8").size).toBeLessThan(styleFor("M5V").size);
    expect(styleFor("F5IV-V").size).toBeGreaterThan(styleFor("F5V").size);
  });
});

describe("moodFor", () => {
  it("shows nothing for a system the telescopes have not studied", () => {
    expect(moodFor(0, "")).toBe("unknown");
    expect(moodFor(15, "")).toBe("unknown");
  });

  it("does not read a civilization into a sentence that denies one", () => {
    // Both of these mention the keywords while saying the system is empty.
    expect(moodFor(40, "No signs of civilization detected.")).toBe("quiet");
    expect(moodFor(10, "Faint signals detected. System appears lifeless.")).toBe("quiet");
  });

  it("marks the extinct ones grey, whichever wording the engine used", () => {
    expect(moodFor(40, "EXTINCT CIVILIZATION detected. Silent for ~4200 years (as seen from Earth).")).toBe(
      "extinct",
    );
    expect(
      moodFor(80, "EXTINCT: Civilization went silent 4200 years ago; automated transmissions continue. Data archives may exist."),
    ).toBe("extinct");
  });

  it("marks a living civilization at every knowledge level the engine describes one at", () => {
    expect(moodFor(10, "Possible artificial signals detected.")).toBe("inhabited");
    expect(moodFor(30, "Civilization detected at DIGITAL stage.")).toBe("inhabited");
    expect(moodFor(50, "INTERSTELLAR civilization. Attitude: seemingly friendly.")).toBe("inhabited");
    // The one full-knowledge sentence that never says "civilization".
    expect(moodFor(100, "Post-biological intelligence transcending physical limitations.")).toBe("inhabited");
    expect(moodFor(100, "Digital-era civilization with global communication networks.")).toBe("inhabited");
  });
});
