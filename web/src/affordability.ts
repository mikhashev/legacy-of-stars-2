/**
 * Whether a technology is affordable right now: its listed cost against the player's current
 * research points, ignoring any director science-skill or swan-song discount the real cost at
 * research time might apply (Dialogs.tsx TechDialog). Display only - the engine alone decides
 * what may actually be researched, and this never disables a button.
 */
export function affordabilityOf(cost: number, researchPoints: number): boolean {
  return cost <= researchPoints;
}
