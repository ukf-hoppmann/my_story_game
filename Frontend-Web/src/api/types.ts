// Hand-written types mirroring the backend's Pydantic schemas
// (Backend/src/story_game/api/schemas/). Deliberately maintained without
// OpenAPI code generation while the frontend remains a small MVP — see
// Frontend-Web/README.md for the original rationale, carried over here.

export type GameRunStatus = "draft" | "active" | "paused" | "completed";
export type GameRole = "owner" | "player";
export type ControlMode = "player" | "director";
export type ActorRole = "player" | "npc" | "neutral";
export type GoalKind = "main" | "side";
export type GoalStatus = "open" | "completed" | "failed";
export type EntityKind = "character" | "location" | "item" | "creature" | "faction";
export type RelationKind =
  | "located_in"
  | "possesses"
  | "contains"
  | "member_of"
  | "knows"
  | "allied_with"
  | "hostile_to"
  | "related_to";
export type VisibilityScope = "public" | "player_known" | "actor_known" | "director_only";

export interface ControllableCharacterSeed {
  name: string;
  description?: string;
}

export interface RunSummary {
  id: string;
  name: string;
  status: GameRunStatus;
  current_revision: number;
  game_role: GameRole;
  updated_at: string;
}

export interface RunSummaryList {
  runs: RunSummary[];
}

export interface GameRunMember {
  issuer: string;
  subject: string;
  game_role: GameRole;
  controlled_entity_ids: string[];
}

export interface GameRun {
  id: string;
  name: string;
  status: GameRunStatus;
  current_revision: number;
  members: GameRunMember[];
  created_at: string;
  updated_at: string;
}

export interface Visibility {
  scope: VisibilityScope;
  actor_id: string | null;
}

export interface WorldEntity {
  id: string;
  kind: EntityKind;
  label: string;
  description: string;
  actor: { role: ActorRole } | null;
  conditions: { name: string; description: string }[];
  aliases: string[];
}

export interface EntityLink {
  id: string;
  source_id: string;
  target_id: string;
  kind: RelationKind;
  visibility: Visibility;
  quantity: number | null;
  description: string | null;
}

export interface Fact {
  id: string;
  statement: string;
  visibility: Visibility;
  subject_id: string | null;
}

/** A fact an actor (the player, an NPC, ...) has learned — and possibly
 *  since forgotten. `learned_at`/`forgotten_at` are story-turn sequence
 *  numbers, not timestamps. */
export interface KnowledgeEntry {
  actor_id: string;
  fact_id: string;
  learned_at: number;
  forgotten_at: number | null;
}

/** A world "law"/boundary, shaped like a Fact but conceptually distinct.
 *  Not surfaced in any screen yet. */
export interface WorldRule {
  id: string;
  statement: string;
  visibility: Visibility;
}

export interface Goal {
  id: string;
  kind: GoalKind;
  title: string;
  description: string;
  status: GoalStatus;
  related_entity_ids: string[];
}

export interface WorldState {
  entities: WorldEntity[];
  links: EntityLink[];
  facts: Fact[];
  knowledge: KnowledgeEntry[];
  rules: WorldRule[];
  goals: Goal[];
  scene_location_ids: string[];
}

export interface StoryTurn {
  id: string;
  sequence: number;
  player_input: string;
  narration: string;
  based_on_revision: number;
  resulting_revision: number;
  completed_at: string;
}

export interface StorySummary {
  through_sequence: number;
  text: string;
  based_on_revision: number;
}

export interface StoryInitialization {
  prompt: string;
  narration: string;
  completed_at: string;
}

export interface StoryState {
  turns: StoryTurn[];
  summary: StorySummary | null;
  current_turn_sequence: number;
  initialization: StoryInitialization | null;
}

export interface GameState {
  run_id: string;
  revision: number;
  // Not typed further yet — no screen consumes configuration fields until
  // Schritt 7/8 (Wizard); type it precisely then, against the live
  // /api/v1/prompt-profile contract rather than guessing the shape now.
  configuration: unknown;
  world: WorldState;
  story: StoryState;
}

export interface GameDocument {
  schema_version: 1;
  game_run: GameRun;
  game_state: GameState;
}

/** The story-creation config fields a user can choose (genre, tone, ...).
 *  Deliberately typed as `string`, not literal unions: the allowed values
 *  are served live by `GET /api/v1/prompt-profile` and must be sourced from
 *  there (see PromptProfileCatalog below), not hardcoded on the frontend. */
export interface EditablePromptProfile {
  genre: string;
  tone: string;
  prose_style: string;
  perspective: string;
  pacing: string;
  length: string;
  player_agency: string;
  consequence: string;
  challenge: string;
  content_profile: string;
}

export interface PromptProfileOption {
  id: string;
  description: string;
}

export interface PromptProfileCategory {
  id: string;
  default_option_id: string;
  options: PromptProfileOption[];
}

/** Response of `GET /api/v1/prompt-profile` — the live source of truth for
 *  every selectable option in the story-creation wizard. */
export interface PromptProfileCatalog {
  package_id: string;
  package_version: string;
  categories: PromptProfileCategory[];
}

export interface ProposeRunRequest {
  initial_prompt: string;
  control_mode: ControlMode;
  controllable_characters: ControllableCharacterSeed[];
  language?: string;
  prompt_profile?: EditablePromptProfile;
}

export interface RunProposal {
  proposal_id: string;
  opening_narration: string;
  world: WorldState;
  suggested_player_entity_ids: string[];
  suggested_title: string;
}

export interface CharacterDecision {
  entity_id: string;
  role: "player" | "npc";
  removed: boolean;
}

export interface ItemDecision {
  entity_id: string;
  removed: boolean;
}

export interface ConfirmRunProposalRequest {
  proposal_id: string;
  run_name?: string;
  character_decisions: CharacterDecision[];
  item_decisions: ItemDecision[];
}

export interface UpdateConfigurationRequest {
  base_revision: number;
  language: string;
  prompt_profile: EditablePromptProfile;
}

export interface PlayTurnRequest {
  player_input: string;
}

export interface TurnResult {
  state: GameState;
  proposed_change_count: number;
  summary_failed: boolean;
  summary_failure_message: string | null;
}

export interface ApiErrorBody {
  error: string;
  detail: string;
  [key: string]: unknown;
}
