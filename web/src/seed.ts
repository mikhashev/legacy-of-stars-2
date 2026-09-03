/**
 * Turning whatever the player types into the New Game seed field into the integer the engine's
 * RNG wants (finding 4: the field used to accept digits only, and an alphanumeric seed like
 * "ark-playtest-0903" raised a "must be a number" error at the door instead of just being used).
 *
 * A seed that already reads as a plain integer passes through unchanged, so every numeric seed
 * anyone has already shared behaves exactly as before. Anything else is hashed with FNV-1a
 * (32-bit): deterministic and dependency-free, so the same text always builds the same game.
 */

const FNV_OFFSET_BASIS = 0x811c9dc5;
const FNV_PRIME = 0x01000193;

/** FNV-1a, 32-bit, as an unsigned integer (0 .. 2^32-1). */
export function fnv1a32(text: string): number {
  let hash = FNV_OFFSET_BASIS;
  for (let i = 0; i < text.length; i += 1) {
    hash ^= text.charCodeAt(i);
    hash = Math.imul(hash, FNV_PRIME);
  }
  return hash >>> 0;
}

/** True for a plain (optionally signed) integer with no other characters. */
function isPlainInteger(trimmed: string): boolean {
  return /^-?\d+$/.test(trimmed) && Number.isSafeInteger(Number(trimmed));
}

/** The integer to send the engine for a seed field's raw text (already trimmed, non-empty). */
export function resolveSeed(trimmed: string): number {
  return isPlainInteger(trimmed) ? Number(trimmed) : fnv1a32(trimmed);
}

/**
 * The line to show next to the field, e.g. "seed 1234567 from 'ark-playtest-0903'" for a
 * hashed seed, or just "seed 42" when the player already typed a plain integer. `null` for an
 * empty field (a random seed - nothing to preview).
 */
export function seedPreview(raw: string): string | null {
  const trimmed = raw.trim();
  if (trimmed === "") return null;
  const value = resolveSeed(trimmed);
  return isPlainInteger(trimmed) ? `seed ${value}` : `seed ${value} from '${trimmed}'`;
}
