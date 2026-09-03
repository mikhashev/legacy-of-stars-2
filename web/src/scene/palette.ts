/**
 * Spectral class -> colour and size for the star map. Pure functions (unit-tested in
 * `tests/unit/palette.test.ts`); nothing here touches Three.js.
 *
 * The only input is `ViewState.systems[].spectral_type`, the string the engine copied out of
 * `data/star_catalog.json` ("M5.5V", "A1V", "G8III", "DZ8", or the WOW! source's
 * "G2V? (candidate 2MASS 19281982-2640123)"). Colours follow the usual Harvard sequence.
 */

/** Harvard class, plus `D` for white dwarfs and `?` when the engine gave us nothing usable. */
export type SpectralClass = "O" | "B" | "A" | "F" | "G" | "K" | "M" | "D" | "?";

/** Yerkes luminosity class, when the type string carries one. `IV-V` is reported as `IV`. */
export type LuminosityClass = "I" | "II" | "III" | "IV" | "V" | "VI" | null;

const CLASS_COLOR: Record<SpectralClass, number> = {
  O: 0xa9c4ff, // blue-white
  B: 0x7f9fff, // blue
  A: 0xf1f5ff, // white
  F: 0xfdf3d0, // yellow-white
  G: 0xffe07a, // yellow
  K: 0xffb35e, // orange
  M: 0xff8452, // red-orange
  D: 0xdfe7f2, // pale white (white dwarf)
  "?": 0x93a0b0, // unknown
};

/** Multiplier on the base sprite size; giants read bigger, white dwarfs smaller. */
const CLASS_SIZE: Record<SpectralClass, number> = {
  O: 1.3,
  B: 1.2,
  A: 1.1,
  F: 1.0,
  G: 1.0,
  K: 0.95,
  M: 0.85,
  D: 0.6,
  "?": 0.85,
};

const LUMINOSITY_SIZE: Record<NonNullable<LuminosityClass>, number> = {
  I: 2.0,
  II: 1.7,
  III: 1.5,
  IV: 1.15,
  V: 1.0,
  VI: 0.85,
};

/**
 * The leading token of a spectral type: everything before the first space, "(" or "?".
 * "G2V? (candidate ...)" -> "G2V"; "F5IV-V" -> "F5IV" (the first of a range).
 */
function leadingToken(spectralType: string | null): string {
  const first = (spectralType ?? "").trim().split(/[\s(?]/, 1)[0] ?? "";
  return first.replace(/-.*$/, "").toUpperCase();
}

export function spectralClass(spectralType: string | null): SpectralClass {
  const letter = leadingToken(spectralType).charAt(0);
  return letter in CLASS_COLOR ? (letter as SpectralClass) : "?";
}

export function luminosityClass(spectralType: string | null): LuminosityClass {
  // White dwarf codes ("DZ8", "DA2") are letter+letter+number, never Yerkes numerals.
  const token = leadingToken(spectralType);
  if (token.startsWith("D")) return null;
  const match = /(VI|IV|III|II|I|V)$/.exec(token);
  return match ? (match[1] as NonNullable<LuminosityClass>) : null;
}

export interface StarStyle {
  /** Sprite tint, as a Three.js hex colour. */
  color: number;
  /** Multiplier on the map's base star size. */
  size: number;
  spectral: SpectralClass;
  luminosity: LuminosityClass;
}

/** Colour and relative size for one star. */
export function styleFor(spectralType: string | null): StarStyle {
  const spectral = spectralClass(spectralType);
  const luminosity = luminosityClass(spectralType);
  const size = CLASS_SIZE[spectral] * (luminosity ? LUMINOSITY_SIZE[luminosity] : 1);
  return { color: CLASS_COLOR[spectral], size, spectral, luminosity };
}

/* -------------------------------------------------------------- knowledge states */

/**
 * What the player has learned about a system, as far as the *displayed* text says it.
 *
 * `description` is `StarSystem.describe_civilization()` and is empty while `knowledge` is 0
 * (docs/web_contract.md 6). Nothing here peeks at anything the engine did not print: the
 * three markers below are read straight off that sentence.
 */
export type SystemMood = "unknown" | "quiet" | "extinct" | "inhabited";

/** Halo colours for the moods that get one. */
export const MOOD_COLOR: Record<"extinct" | "inhabited", number> = {
  extinct: 0x8b97a8, // --text-dim: a civilization that is already gone
  inhabited: 0xffcf6b, // --warning: something is transmitting
};

export const SEEDED_COLOR = 0x7fe0a0; // --good: a Genesis ark is on its way or has landed
export const CONTACTED_COLOR = 0x5fb0ff; // --accent: this system has answered us
/** The cyan of our own transmissions (`effects.ts` OUTGOING_COLOR): one of ours has landed here. */
export const DELIVERED_COLOR = 0x4fd6ff;

export function moodFor(knowledge: number, description: string): SystemMood {
  if (knowledge <= 0 || description.trim() === "") return "unknown";
  // "EXTINCT CIVILIZATION detected..." / "EXTINCT: Civilization went silent..."
  if (/EXTINCT/.test(description)) return "extinct";
  // "No signs of civilization detected." and "Faint signals detected. System appears
  // lifeless." both mention the keywords while saying the opposite, so they lose first.
  if (/no signs of civilization|appears lifeless/i.test(description)) return "quiet";
  // "civilization" covers five of the six full-knowledge stage sentences and every partial
  // one; "post-biological" catches the sixth, which never uses the word.
  if (/civilization|signals detected|post-biological/i.test(description)) return "inhabited";
  return "quiet";
}
