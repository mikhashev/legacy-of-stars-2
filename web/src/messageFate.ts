/**
 * The three classes of silence (docs/plans/civilization_timelines_plan.md §8): what a sent
 * message's `fate` means, spelled out in one line instead of an undifferentiated "no reply".
 * Pure text formatting only - `fate` and `explanation_year` are read straight off `SentMessage`
 * (docs/reference/web_contract.md 6), nothing here decides them.
 *
 * Used everywhere a message is shown: the dossier, the map's selected-system card, the system
 * picker and the map's own in-flight label (`scene/effects.ts`).
 */
import { formatYear } from "./scene/coords";
import type { Observation, SentMessage } from "./types";

/** One line for a sent message's fate, e.g. "no reply by 2027: they chose silence, or they
 * are no longer there - watch the sky. Explained by the light of 2027." */
export function messageFateText(message: Pick<SentMessage, "fate" | "expected_reply_year" | "explanation_year">): string {
  const expected = message.expected_reply_year;
  let text: string;
  switch (message.fate) {
    case "replied":
      text = "answered";
      break;
    case "nobody":
      text = "nobody there to answer (known at once)";
      break;
    case "unanswered":
      text =
        expected === undefined
          ? "no reply: they chose silence, or they are no longer there - watch the sky"
          : `no reply by ${formatYear(expected)}: they chose silence, or they are no longer there - watch the sky`;
      break;
    case "in_flight":
    default:
      text =
        expected === undefined
          ? "a reply, if any, is still on its way"
          : `reply, if any, arrives around ${formatYear(expected)}`;
      break;
  }
  // "nobody" is already "known at once" and "replied" already speaks for itself; the
  // explanation only adds information for a silence that might otherwise look unexplained.
  if (
    (message.fate === "unanswered" || message.fate === "in_flight") &&
    message.explanation_year !== undefined &&
    message.explanation_year !== null
  ) {
    text = `${text}. Explained by the light of ${formatYear(message.explanation_year)}.`;
  }
  return text;
}

/** A short map label for a message that just turned up unanswered: `effects.ts`'s star tag. */
export const NO_REPLY_TAG = "no reply";

/** The most recent entry of `observations[]` (oldest first), or null when there is none yet. */
export function lastObservation(observations: readonly Observation[]): Observation | null {
  return observations.length > 0 ? (observations[observations.length - 1] ?? null) : null;
}

/**
 * "our message reaches them in {receipt_year}; they will have {n} more years of history than
 * we have seen" - the dossier line for an in-flight message (docs/plans/civilization_timelines_plan.md
 * §8). `receipt_year` is when our signal lands (`expected_reply_year - distance`, half the
 * round trip already stored); `n = expected_reply_year - observed_year` is how many years past
 * what we last saw of them the reply, if any, will be speaking from. `null` for anything but an
 * in-flight message - a resolved one has nothing left to count down.
 */
export function inFlightHint(
  message: Pick<SentMessage, "fate" | "expected_reply_year">,
  distanceLy: number,
  observedYear: number,
): string | null {
  if (message.fate !== "in_flight" || message.expected_reply_year === undefined) return null;
  const receiptYear = message.expected_reply_year - Math.round(distanceLy);
  const n = Math.max(0, Math.round(message.expected_reply_year - observedYear));
  return `our message reaches them in ${formatYear(receiptYear)}; they will have ${n} more year${
    n === 1 ? "" : "s"
  } of history than we have seen`;
}
