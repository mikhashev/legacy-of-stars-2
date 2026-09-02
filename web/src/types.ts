/**
 * The Python/JavaScript contract, hand-written from `docs/web_contract.md`.
 *
 * `src/web_api.py` is the only producer of these values and that document is the
 * specification for both sides; when the engine changes, the document changes first
 * and this file follows it. Everything here describes JSON that has already been
 * parsed - no Pyodide proxies, no engine objects.
 */

/* -------------------------------------------------------------- actions */

export type ActionId =
  | "send_message"
  | "focus_research"
  | "public_outreach"
  | "research_tech"
  | "choose_doctrine"
  | "advance_generation"
  | "defend"
  | "consult_advisor"
  | "listen_swan_song"
  | "genesis_seed"
  | "respond_event"
  | "wow_reply"
  | "wow_silent"
  | "compose_director_message"
  | "summary"
  | "help";

/** Parameter names the UI must collect for an action (`ViewState.actions[].needs`). */
export type ParamName = "system" | "text" | "tech" | "threat" | "defense" | "choice";

/** The three protocols `defend` accepts. */
export type DefenseKind = "emergency" | "evacuate" | "diplomacy";

/** Integers may travel as JSON numbers or as decimal strings (web_contract.md 2). */
export type IntParam = number | string;

export interface ActionParams {
  /** `system` is the system *name* (`ViewState.systems[].name`), never an index. */
  send_message: { system: string; text?: string };
  focus_research: { system: string };
  public_outreach: Record<string, never>;
  research_tech: { tech: string };
  choose_doctrine: { tech: string; choice: IntParam };
  advance_generation: Record<string, never>;
  /** `threat` is 0-based: `ViewState.threats[i].index - 1`. */
  defend: { threat: IntParam; defense: DefenseKind };
  consult_advisor: Record<string, never>;
  listen_swan_song: { system: string };
  genesis_seed: { system: string };
  /** `choice` indexes `ViewState.pending_event.choices`. */
  respond_event: { choice: IntParam };
  wow_reply: { text?: string };
  wow_silent: Record<string, never>;
  compose_director_message: Record<string, never>;
  summary: Record<string, never>;
  help: Record<string, never>;
}

/** The action bar: what the engine offers now. The six ungated actions are never listed. */
export interface ActionSpec {
  id: ActionId;
  label: string;
  cost: string;
  needs: ParamName[];
}

/* -------------------------------------------------------------- events */

export type AttackType =
  | "fleet"
  | "laser_sail_probe"
  | "fusion_strike"
  | "wow_fleet"
  | "genesis_fleet"
  | "mirror_fleet";

export type InfoAttackType =
  | "corrupted_technology"
  | "societal_manipulation"
  | "false_hope_signal"
  | "philosophical_weapon";

export type GameEventKind =
  | "generation_start"
  | "crisis"
  | "bonus"
  | "response_received"
  | "system_discovered"
  | "attack_warning"
  | "attack_resolved"
  | "info_attack"
  | "philosophical_event"
  | "fermi_evidence"
  | "achievement"
  | "genesis"
  | "victory"
  | "wow"
  | "game_over";

interface GameEventBase<K extends GameEventKind, D> {
  kind: K;
  /** Ready to display; the engine writes it, sometimes multi-line with emoji. */
  text: string;
  data: D;
  /** The generation the event was emitted in. */
  generation: number;
}

export type GameEvent =
  | GameEventBase<"generation_start", { year: number }>
  | GameEventBase<"crisis", Record<string, never>>
  | GameEventBase<"bonus", Record<string, never>>
  | GameEventBase<"response_received", { system: string; text: string; first: boolean }>
  | GameEventBase<"system_discovered", { system: string; distance: number }>
  | GameEventBase<
      "attack_warning",
      { system: string; arrival_gen: number; eta: number; attack_type: AttackType }
    >
  | GameEventBase<
      "attack_resolved",
      { system: string; support_loss: number; funding_loss: number; severity: string }
    >
  | GameEventBase<"info_attack", { system: string; attack_type: InfoAttackType }>
  | GameEventBase<"philosophical_event", { event_id: string }>
  | GameEventBase<"fermi_evidence", { kind: string; amount: number; total: number; reason: string }>
  | GameEventBase<"achievement", { name: string }>
  | GameEventBase<"genesis", { system: string; stage?: string; outcome?: "ally" | "hostile" }>
  | GameEventBase<"victory", { contacts?: string[]; explanation?: string }>
  | GameEventBase<"wow", Record<string, never>>
  | GameEventBase<"game_over", { reason: string }>;

/** The plan renders these as a modal; every other kind is a journal line. */
export const MODAL_EVENT_KINDS: readonly GameEventKind[] = [
  "wow",
  "victory",
  "game_over",
  "attack_warning",
  "philosophical_event",
  "attack_resolved",
];

/* -------------------------------------------------------------- view state */

export interface Director {
  name: string;
  traits: string[];
  skills: { diplomacy: number; science: number; administration: number };
}

export interface ProgramStatus {
  action_points: number;
  max_action_points: number;
  /** 0-100; below 20 ends the game. */
  funding: number;
  /** 0-100; below 10 ends the game. */
  public_support: number;
  knowledge_base: number;
  research_points: number;
  /** RP income per generation, after the integration efficiency modifier. */
  passive_rp: number;
  /** 1 + highest researched tier (1-6). */
  tech_level: number;
  self_destruct_risk: number;
  ecological_risk: number;
  /** Leakage front in light-years, growing 25 LY per generation. */
  broadcast_radius: number;
  /** 1.0 = full leakage, 0.0 = silence. */
  leakage_multiplier: number;
  /** 0-1; tier 5 research needs 0.40. */
  integration_level: number;
  integration_status: string;
}

export interface SentMessage {
  text: string;
  generation: number;
  arrival_gen: number;
}

export interface StarSystem {
  /** 1-based position: the console's menu number. */
  index: number;
  /** The id used in action parameters. */
  name: string;
  distance: number;
  spectral_type: string | null;
  ra: number | null;
  dec: number | null;
  /** 0-100; 0 hides the description, 20 reveals a civilization, 30 enables swan songs. */
  knowledge: number;
  description: string;
  round_trip_generations: number;
  messages_sent: SentMessage[];
  responses: string[];
  next_response_gen: number | null;
  contacted: boolean;
  is_seeded: boolean;
}

export interface CatalogInfo {
  known: number;
  total: number;
  undiscovered: number;
  discovery_chance: number;
}

export interface Threat {
  /** 1-based; `defend` takes `index - 1`. */
  index: number;
  source: string;
  attack_type: AttackType;
  type_label: string;
  /** Generations remaining; 0 = arriving. */
  eta: number;
  arrival_gen: number;
  arrival_year: number;
  source_distance: number;
  /** A `CivilizationStage` name, or "UNKNOWN". */
  enemy_stage: string;
  defense_pct: number;
  actions_taken: string[];
}

export interface Technology {
  id: string;
  name: string;
  tier: number;
  cost: number;
  description: string;
  /** e.g. "Unlocks Gen 4+ (Year 2052). Launched 2015." */
  year_context: string;
  /** null when researchable now, otherwise the reason it is locked. */
  locked: string | null;
}

export interface Technologies {
  /** Technology ids, including the five pre-1977 legacy ones. */
  researched: string[];
  available: Technology[];
}

export interface FermiEvidence {
  extinction_evidence: number;
  dark_forest_evidence: number;
  cooperation_evidence: number;
  great_filter_evidence: number;
  total: number;
  /** Always 15. */
  goal: number;
}

export interface GenesisWorld {
  system_name: string;
  seed_gen: number;
  arrival_gen: number;
  /** 0 = in transit ... 4 = spacefaring. */
  evolution_stage: number;
  is_hostile: boolean;
  is_destroyed: boolean;
  resolved: boolean;
  outcome: string | null;
}

export interface GenesisInfo {
  unlocked: boolean;
  /** Multi-line status text. */
  summary: string;
  worlds: GenesisWorld[];
  /** System names an ark may be launched at (sterile, habitable, unseeded, not the WOW!
   *  source); the Genesis picker must list exactly these, in this order. */
  targets: string[];
}

export interface PendingEventChoice {
  name: string;
  description: string;
}

/** The philosophical crisis that blocks `advance_generation` until it is answered. */
export interface PendingEvent {
  id: string;
  name: string;
  description: string;
  choices: PendingEventChoice[];
}

export interface WowState {
  decided: boolean;
  replied: boolean;
  outcome: null | "silence" | "friendly" | "hostile";
}

/** messages_sent, responses_received, attacks_scheduled, ... (all ints). */
export type GameStats = Record<string, number>;

/** Produced by `ContactProgram.view_state()`; nothing hidden ever appears here. */
export interface ViewState {
  /** 1-based; one generation = 25 years. */
  generation: number;
  /** `start_year + (generation - 1) * 25`. */
  year: number;
  /** Always 1977. */
  start_year: number;
  director: Director;
  status: ProgramStatus;
  active_doctrines: string[];
  /** Known star systems, in discovery order. */
  systems: StarSystem[];
  catalog: CatalogInfo;
  threats: Threat[];
  technologies: Technologies;
  fermi_evidence: FermiEvidence;
  contacts: number;
  /** Always 3. */
  contacts_goal: number;
  victory: boolean;
  philosophical_victory: boolean;
  genesis: GenesisInfo;
  pending_event: PendingEvent | null;
  wow: WowState;
  achievements: string[];
  stats: GameStats;
  actions: ActionSpec[];
  game_over: boolean;
  /** Empty while playing. */
  game_over_reason: string;
}

/* -------------------------------------------------------------- perform */

export interface DoctrineOption {
  index: number;
  name: string;
  description: string;
}

/** The follow-up `research_tech` asks for; answer it with `choose_doctrine`. */
export interface DoctrineNeeds {
  kind: "doctrine";
  tech_id: string;
  name: string;
  description: string;
  options: DoctrineOption[];
}

export type PerformNeeds = DoctrineNeeds;

/** The `data` payloads of the actions that carry one (web_contract.md 3). */
export interface PerformData {
  wow_reply: { message: string; arrival_gen: number; response_gen: number; replied: true };
  wow_silent: { replied: false; attack_damage_reduction: number };
  compose_director_message: { draft: string };
  summary: { score: number; score_breakdown: Record<string, number> };
  help: { ai: string };
}

export interface PerformResult {
  /** True when the engine applied the action; a refusal is false with the engine's message. */
  ok: boolean;
  message: string;
  /** Emitted by this action only, in order. */
  events: GameEvent[];
  /** null only when no game is in progress. */
  state: ViewState | null;
  needs: PerformNeeds | null;
  /** Present only for the actions listed in `PerformData`. */
  data?: Record<string, unknown>;
}

/** A `perform` result whose `data` is the payload of a known action. */
export type PerformResultOf<A extends ActionId> = A extends keyof PerformData
  ? PerformResult & { data: PerformData[A] }
  : PerformResult;

/* -------------------------------------------------------------- worker protocol */

export type EngineMethod = "new_game" | "load" | "save" | "state" | "perform";

export interface WorkerRequest {
  id: number;
  method: EngineMethod;
  /** Strings only: the Python side is called with string arguments (plan 3). */
  args: string[];
}

export interface WorkerResponse {
  id: number;
  /** The raw JSON string the Python facade returned. */
  result?: string;
  error?: string;
}

export interface ProgressMessage {
  type: "progress";
  stage: string;
  /** 0-100. */
  pct: number;
}

export interface AssetSize {
  name: string;
  /** Bytes over the wire (0 when the browser hides it). */
  transferBytes: number;
  /** Bytes after decompression. */
  encodedBytes: number;
}

export interface ReadyMessage {
  type: "ready";
  startupMs: number;
  pythonVersion: string;
  pyodideVersion: string;
  engineZipBytes: number;
  assets: AssetSize[];
}

export interface FailedMessage {
  type: "failed";
  stage: string;
  error: string;
}

export type WorkerMessage = ProgressMessage | ReadyMessage | FailedMessage | WorkerResponse;
