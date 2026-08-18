// Hand-written types mirroring the backend's Pydantic schemas
// (Backend/src/story_game/api/schemas/). They are deliberately maintained
// without OpenAPI code generation while the frontend remains a small MVP.

export type GameRunStatus = "draft" | "active" | "paused" | "completed";
export type GameRole = "owner" | "player";
export type ControlMode = "player" | "director";
export type ActorRole = "player" | "npc" | "neutral";
export type GoalKind = "main" | "side";
export type GoalStatus = "open" | "completed" | "failed";

export interface PlayerCharacterSeed {
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
  player_entity_id: string | null;
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

export interface WorldEntity {
  id: string;
  kind: string;
  label: string;
  description: string;
  actor: { role: ActorRole } | null;
  conditions: { name: string; description: string }[];
  aliases: string[];
}

export interface Fact {
  id: string;
  statement: string;
  visibility: { scope: string; actor_id: string | null };
  subject_id: string | null;
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
  links: unknown[];
  facts: Fact[];
  knowledge: unknown[];
  rules: unknown[];
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

export interface StoryState {
  turns: StoryTurn[];
  summary: StorySummary | null;
  current_turn_sequence: number;
}

export interface GameState {
  run_id: string;
  revision: number;
  configuration: unknown;
  world: WorldState;
  story: StoryState;
}

export interface GameDocument {
  schema_version: 1;
  game_run: GameRun;
  game_state: GameState;
}

export interface InitializeRunRequest {
  run_name: string;
  initial_prompt: string;
  control_mode: ControlMode;
  player_character?: PlayerCharacterSeed;
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
