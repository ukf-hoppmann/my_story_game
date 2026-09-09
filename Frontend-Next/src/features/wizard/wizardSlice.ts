import { createSlice, type PayloadAction } from "@reduxjs/toolkit";
import type {
  CharacterDecision,
  ConfirmRunProposalRequest,
  ControlMode,
  ItemDecision,
  ProposeRunRequest,
  RunProposal,
  WorldState,
} from "../../api/types";

export type WizardStep = "welt" | "figur" | "stil" | "review";

export interface WizardCharacterDraft {
  name: string;
  description: string;
}

interface CharacterDecisionState {
  role: "player" | "npc";
  removed: boolean;
}

interface ItemDecisionState {
  removed: boolean;
}

interface WizardProposalState {
  proposalId: string;
  openingNarration: string;
  world: WorldState;
  suggestedPlayerEntityIds: string[];
}

/** Text fields set via the generic `fieldChanged` action — one entry per
 *  input across all three steps, so adding a new style field later doesn't
 *  need a new reducer. */
export type WizardTextField =
  | "title"
  | "premise"
  | "genre"
  | "tone"
  | "proseStyle"
  | "perspective"
  | "pacing"
  | "length"
  | "playerAgency"
  | "consequence"
  | "challenge"
  | "contentProfile"
  | "runName";

export interface WizardState {
  step: WizardStep;
  title: string;
  premise: string;
  genre: string;
  tone: string;
  proseStyle: string;
  perspective: string;
  pacing: string;
  length: string;
  playerAgency: string;
  consequence: string;
  challenge: string;
  contentProfile: string;
  controlMode: ControlMode;
  characters: WizardCharacterDraft[];
  runName: string;
  proposal: WizardProposalState | null;
  characterDecisions: Record<string, CharacterDecisionState>;
  itemDecisions: Record<string, ItemDecisionState>;
}

const initialState: WizardState = {
  step: "welt",
  title: "",
  premise: "",
  genre: "",
  tone: "",
  proseStyle: "",
  perspective: "",
  pacing: "",
  length: "",
  playerAgency: "",
  consequence: "",
  challenge: "",
  contentProfile: "",
  controlMode: "player",
  characters: [{ name: "", description: "" }],
  runName: "",
  proposal: null,
  characterDecisions: {},
  itemDecisions: {},
};

const wizardSlice = createSlice({
  name: "wizard",
  initialState,
  reducers: {
    fieldChanged(state, action: PayloadAction<{ field: WizardTextField; value: string }>) {
      state[action.payload.field] = action.payload.value;
    },
    stepChanged(state, action: PayloadAction<WizardStep>) {
      state.step = action.payload;
    },
    controlModeChanged(state, action: PayloadAction<ControlMode>) {
      state.controlMode = action.payload;
      // A player controls exactly one character — collapse to the first
      // draft (keeping whatever the user already typed) when switching away
      // from director mode's multi-character list.
      if (action.payload === "player" && state.characters.length > 1) {
        state.characters = [state.characters[0]];
      }
    },
    characterAdded(state) {
      state.characters.push({ name: "", description: "" });
    },
    characterRemoved(state, action: PayloadAction<number>) {
      state.characters.splice(action.payload, 1);
      if (state.characters.length === 0) {
        state.characters.push({ name: "", description: "" });
      }
    },
    characterFieldChanged(
      state,
      action: PayloadAction<{ index: number; field: keyof WizardCharacterDraft; value: string }>,
    ) {
      const { index, field, value } = action.payload;
      const character = state.characters[index];
      if (character) {
        character[field] = value;
      }
    },
    proposalReceived(state, action: PayloadAction<RunProposal>) {
      const proposal = action.payload;
      state.proposal = {
        proposalId: proposal.proposal_id,
        openingNarration: proposal.opening_narration,
        world: proposal.world,
        suggestedPlayerEntityIds: proposal.suggested_player_entity_ids,
      };
      state.runName = state.title.trim() || proposal.suggested_title;
      state.step = "review";

      state.characterDecisions = {};
      state.itemDecisions = {};
      for (const entity of proposal.world.entities) {
        if (entity.kind === "character") {
          state.characterDecisions[entity.id] = {
            role: proposal.suggested_player_entity_ids.includes(entity.id) ? "player" : "npc",
            removed: false,
          };
        } else if (entity.kind === "item") {
          state.itemDecisions[entity.id] = { removed: false };
        }
      }
    },
    characterRoleChanged(state, action: PayloadAction<{ entityId: string; role: "player" | "npc" }>) {
      const decision = state.characterDecisions[action.payload.entityId];
      if (decision) {
        decision.role = action.payload.role;
      }
    },
    characterRemovalToggled(state, action: PayloadAction<string>) {
      const decision = state.characterDecisions[action.payload];
      if (decision) {
        decision.removed = !decision.removed;
      }
    },
    itemRemovalToggled(state, action: PayloadAction<string>) {
      const decision = state.itemDecisions[action.payload];
      if (decision) {
        decision.removed = !decision.removed;
      }
    },
    wizardReset() {
      return initialState;
    },
  },
});

export const {
  fieldChanged,
  stepChanged,
  controlModeChanged,
  characterAdded,
  characterRemoved,
  characterFieldChanged,
  proposalReceived,
  characterRoleChanged,
  characterRemovalToggled,
  itemRemovalToggled,
  wizardReset,
} = wizardSlice.actions;

export default wizardSlice.reducer;

/** Builds the propose-run request from the collected Welt/Figur/Stil
 *  answers. Characters with an empty name are dropped — an unnamed draft
 *  row is not a real character seed. */
export function buildProposeRequest(state: WizardState): ProposeRunRequest {
  return {
    initial_prompt: state.premise,
    control_mode: state.controlMode,
    controllable_characters: state.characters
      .filter((character) => character.name.trim().length > 0)
      .map((character) => ({
        name: character.name.trim(),
        description: character.description.trim() || undefined,
      })),
    language: "de",
    prompt_profile: {
      genre: state.genre,
      tone: state.tone,
      prose_style: state.proseStyle,
      perspective: state.perspective,
      pacing: state.pacing,
      length: state.length,
      player_agency: state.playerAgency,
      consequence: state.consequence,
      challenge: state.challenge,
      content_profile: state.contentProfile,
    },
  };
}

export function buildConfirmRequest(state: WizardState): ConfirmRunProposalRequest {
  if (!state.proposal) {
    throw new Error("buildConfirmRequest called without a proposal");
  }

  const characterDecisions: CharacterDecision[] = Object.entries(state.characterDecisions).map(
    ([entity_id, decision]) => ({ entity_id, role: decision.role, removed: decision.removed }),
  );
  const itemDecisions: ItemDecision[] = Object.entries(state.itemDecisions).map(
    ([entity_id, decision]) => ({ entity_id, removed: decision.removed }),
  );

  return {
    proposal_id: state.proposal.proposalId,
    run_name: state.runName.trim() || undefined,
    character_decisions: characterDecisions,
    item_decisions: itemDecisions,
  };
}
