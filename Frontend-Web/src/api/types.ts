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

/** One immutable segment of the summary chain (TASK-032): appended, never replaced. */
export interface StorySummarySegment {
  from_sequence: number;
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
  summaries: StorySummarySegment[];
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
  /** Optional: when omitted, no tone text is rendered and the genre's own
   *  implied mood applies undiluted. */
  tone?: string;
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

/** Narration prose plus the player's suggested next moves (TASK-033/034). */
export interface Continuation {
  narration: string;
  options: string[];
}

export interface RunProposal {
  proposal_id: string;
  continuation: Continuation;
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
  continuation: Continuation;
  proposed_change_count: number;
  summary_failed: boolean;
  summary_failure_message: string | null;
}

export type SceneImageStatus = "pending" | "ready" | "failed";

export interface SceneImage {
  image_id: string;
  run_id: string;
  turn_sequence: number;
  status: SceneImageStatus;
  model: string | null;
  refine: boolean;
  refine_model: string | null;
  refine_strength: number;
  width: number;
  height: number;
  seed: number;
  prompt: string | null;
  compact_prompt: string | null;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface SceneImageList {
  images: SceneImage[];
}

export interface ImageModel {
  name: string;
}

export interface SceneImageCapabilities {
  enabled: boolean;
  models: ImageModel[];
  refine_models: ImageModel[];
  model_listing_failed: boolean;
  default_model: string | null;
  default_refine: boolean;
  default_refine_model: string | null;
  default_refine_strength: number | null;
  min_refine_strength: number | null;
  max_refine_strength: number | null;
  turn_window: number | null;
}

/** Every field is optional: an omitted one uses the server default. */
export interface CreateSceneImageRequest {
  model?: string;
  refine?: boolean;
  refine_strength?: number;
}

export interface ApiErrorBody {
  error: string;
  detail: string;
  [key: string]: unknown;
}

export type AdminPromptKind = "task" | "option" | "directive";
export type AdminPromptSource = "toml_seed" | "ui" | "toml_reset";

/** One stored version of a system-prompt entry (admin settings). */
export interface AdminPromptVersion {
  version_id: string;
  kind: AdminPromptKind;
  /** Task/directive id, or `<category>/<option>` for an option. */
  key: string;
  text: string;
  is_default: boolean;
  task_ids: string[];
  source: AdminPromptSource;
  created_at: string;
  created_by: string | null;
  is_active: boolean;
  /** True while the active version is an edit made in the UI. */
  is_modified: boolean;
  /** True for an option added in the UI: it has no shipped original and can be removed. */
  is_custom: boolean;
}

export interface AdminPromptList {
  package_id: string;
  package_version: string;
  entries: AdminPromptVersion[];
}

export interface AdminPromptVersionList {
  versions: AdminPromptVersion[];
}

export interface SavePromptTextRequest {
  kind: AdminPromptKind;
  key: string;
  text: string;
}

/** A new selectable option; only genre, tone and prose_style accept one. */
export interface CreatePromptOptionRequest {
  category: string;
  option_id: string;
  text: string;
}

/** Names one option: the category and the id after the slash of its key. */
export interface PromptOptionRef {
  category: string;
  option_id: string;
}

export type RemovalMode = "archive" | "purge";
export type RemovalStatus = "done" | "in_use" | "protected" | "not_archived" | "not_found";

/** Archive (trash) or purge (delete for good); without `options`, every option the mode applies to. */
export interface RemovePromptOptionsRequest {
  mode: RemovalMode;
  options?: PromptOptionRef[];
}

export interface RemovalOutcome {
  /** `<category>/<option>` */
  key: string;
  status: RemovalStatus;
  message: string;
}

export interface RemovalResult {
  outcomes: RemovalOutcome[];
}

/** Name one entry, one `kind`, or send `{}` to reset the whole package. */
export interface ResetPromptsRequest {
  kind?: AdminPromptKind;
  key?: string;
}

export type AdminModelTask = "story" | "extraction" | "summary" | "scene_image";

/** One stored version of a task's model choice (admin settings). */
export interface AdminModelSetting {
  version_id: string;
  task: AdminModelTask;
  /** Logical id of a model in the backend's `llm.toml` catalog. */
  model_ref: string;
  temperature: number | null;
  max_output_tokens: number | null;
  source: AdminPromptSource;
  created_at: string;
  created_by: string | null;
  is_active: boolean;
  /** True while the active version is an edit made in the UI. */
  is_modified: boolean;
}

/** A catalog model that may be selected for `task`. */
export interface AdminModelCandidate {
  task: AdminModelTask;
  model_ref: string;
  provider_id: string;
  model_id: string;
}

export interface AdminModelOverview {
  settings: AdminModelSetting[];
  candidates: AdminModelCandidate[];
}

export interface AdminModelSettingList {
  versions: AdminModelSetting[];
}

export interface SaveModelSettingRequest {
  task: AdminModelTask;
  model_ref: string;
  temperature: number | null;
  max_output_tokens: number | null;
}

/** Name one task, or send `{}` to reset every task. */
export interface ResetModelSettingsRequest {
  task?: AdminModelTask;
}
