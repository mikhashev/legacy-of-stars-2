/**
 * Unit tests for `src/messageFate.ts` (run with `npm run unit`): the three classes of silence
 * (docs/plans/civilization_timelines_plan.md §8) as the text the dossier, the map's
 * selected-system card and the picker actually show.
 */
import { describe, expect, it } from "vitest";
import { inFlightHint, lastObservation, messageFateText } from "../../src/messageFate";
import type { Observation } from "../../src/types";

describe("messageFateText", () => {
  it("in_flight: names the year a reply would arrive", () => {
    expect(messageFateText({ fate: "in_flight", expected_reply_year: 2077, explanation_year: null })).toBe(
      "reply, if any, arrives around 2077",
    );
  });

  it("nobody: known at once, no year attached", () => {
    expect(messageFateText({ fate: "nobody", expected_reply_year: 2002, explanation_year: 2002 })).toBe(
      "nobody there to answer (known at once)",
    );
  });

  it("unanswered: the two possible reasons, neither favoured", () => {
    expect(messageFateText({ fate: "unanswered", expected_reply_year: 2052, explanation_year: null })).toBe(
      "no reply by 2052: they chose silence, or they are no longer there - watch the sky",
    );
  });

  it("replied: a plain one-word answer", () => {
    expect(messageFateText({ fate: "replied", expected_reply_year: 2052, explanation_year: null })).toBe("answered");
  });

  it("appends the explanation once the light of it has arrived", () => {
    expect(messageFateText({ fate: "unanswered", expected_reply_year: 2027, explanation_year: 2027 })).toBe(
      "no reply by 2027: they chose silence, or they are no longer there - watch the sky. " +
        "Explained by the light of 2027.",
    );
  });

  it("a death not yet explained stays a plain unanswered - never leaks the reason early", () => {
    const text = messageFateText({ fate: "unanswered", expected_reply_year: 2027, explanation_year: null });
    expect(text).not.toContain("Explained");
  });

  it("formats a year at or before zero as BC, matching scene/coords.formatYear", () => {
    expect(messageFateText({ fate: "in_flight", expected_reply_year: -50, explanation_year: null })).toBe(
      "reply, if any, arrives around 51 BC",
    );
  });
});

describe("inFlightHint", () => {
  it("null for anything but an in-flight message", () => {
    expect(inFlightHint({ fate: "replied", expected_reply_year: 2052 }, 20, 2002)).toBeNull();
    expect(inFlightHint({ fate: "unanswered", expected_reply_year: 2052 }, 20, 2002)).toBeNull();
    expect(inFlightHint({ fate: "nobody", expected_reply_year: 2002 }, 20, 2002)).toBeNull();
  });

  it("states the receipt year and how much more history the reply will carry", () => {
    // expected_reply_year = send + 2d; receipt = expected - d.
    const text = inFlightHint({ fate: "in_flight", expected_reply_year: 2077 }, 25, 2002);
    expect(text).toBe("our message reaches them in 2052; they will have 75 more years of history than we have seen");
  });

  it("singular 'year' for exactly one", () => {
    const text = inFlightHint({ fate: "in_flight", expected_reply_year: 2003 }, 1, 2002);
    expect(text).toContain("1 more year of history");
    expect(text).not.toContain("1 more years");
  });
});

describe("lastObservation", () => {
  const a: Observation = { year: 2002, observed_year: 1989, summary: "digital era, cautious" };
  const b: Observation = { year: 2027, observed_year: 2014, summary: "Silent for 0 years." };

  it("null for an empty history", () => {
    expect(lastObservation([])).toBeNull();
  });

  it("the last entry, not the first", () => {
    expect(lastObservation([a, b])).toBe(b);
  });
});
