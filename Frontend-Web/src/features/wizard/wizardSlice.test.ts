import { describe, expect, it } from "vitest";
import type { RunProposal } from "../../api/types";
import wizardReducer, {
  buildConfirmRequest,
  buildProposeRequest,
  characterAdded,
  characterFieldChanged,
  characterRemovalToggled,
  characterRemoved,
  characterRoleChanged,
  controlModeChanged,
  fieldChanged,
  hasPlayableCharacter,
  itemRemovalToggled,
  proposalReceived,
  stepChanged,
  wizardReset,
  type WizardState,
} from "./wizardSlice";

const initial = wizardReducer(undefined, { type: "@@INIT" });

const proposal: RunProposal = {
  proposal_id: "33333333-3333-3333-3333-333333333333",
  continuation: { narration: "Der Regen hatte die Spuren fast fortgespült.", options: [] },
  suggested_title: "Die Schatten von Auenfall",
  suggested_player_entity_ids: ["char-1"],
  world: {
    entities: [
      { id: "char-1", kind: "character", label: "Elian", description: "", actor: null, conditions: [], aliases: [] },
      { id: "char-2", kind: "character", label: "Bran", description: "", actor: null, conditions: [], aliases: [] },
      { id: "item-1", kind: "item", label: "Laterne", description: "", actor: null, conditions: [], aliases: [] },
    ],
    links: [],
    facts: [],
    knowledge: [],
    rules: [],
    goals: [],
    scene_location_ids: [],
  },
};

describe("wizardSlice", () => {
  it("starts on the Welt step with one empty character draft", () => {
    expect(initial.step).toBe("welt");
    expect(initial.characters).toEqual([{ name: "", description: "" }]);
  });

  it("updates a text field via fieldChanged", () => {
    const state = wizardReducer(initial, fieldChanged({ field: "premise", value: "Ein Kurier verschwindet." }));

    expect(state.premise).toBe("Ein Kurier verschwindet.");
  });

  it("advances the step", () => {
    const state = wizardReducer(initial, stepChanged("figur"));

    expect(state.step).toBe("figur");
  });

  it("collapses to one character when switching to player mode", () => {
    let state = wizardReducer(initial, controlModeChanged("director"));
    state = wizardReducer(state, characterAdded());
    state = wizardReducer(
      state,
      characterFieldChanged({ index: 0, field: "name", value: "Elian" }),
    );
    expect(state.characters).toHaveLength(2);

    state = wizardReducer(state, controlModeChanged("player"));

    expect(state.characters).toEqual([{ name: "Elian", description: "" }]);
  });

  it("always keeps at least one character draft after removal", () => {
    const state = wizardReducer(initial, characterRemoved(0));

    expect(state.characters).toEqual([{ name: "", description: "" }]);
  });

  it("seeds decisions and run name when a proposal is received", () => {
    const withTitle = wizardReducer(initial, fieldChanged({ field: "title", value: "" }));
    const state = wizardReducer(withTitle, proposalReceived(proposal));

    expect(state.step).toBe("review");
    expect(state.runName).toBe("Die Schatten von Auenfall");
    expect(state.characterDecisions).toEqual({
      "char-1": { role: "player", removed: false },
      "char-2": { role: "npc", removed: false },
    });
    expect(state.itemDecisions).toEqual({ "item-1": { removed: false } });
  });

  it("prefers the user's own title over the suggested one", () => {
    const withTitle = wizardReducer(initial, fieldChanged({ field: "title", value: "Mein Titel" }));
    const state = wizardReducer(withTitle, proposalReceived(proposal));

    expect(state.runName).toBe("Mein Titel");
  });

  it("toggles a character's role and removal", () => {
    let state = wizardReducer(initial, proposalReceived(proposal));
    state = wizardReducer(state, characterRoleChanged({ entityId: "char-2", role: "player" }));
    state = wizardReducer(state, characterRemovalToggled("char-2"));

    expect(state.characterDecisions["char-2"]).toEqual({ role: "player", removed: true });
  });

  it("toggles item removal", () => {
    let state = wizardReducer(initial, proposalReceived(proposal));
    state = wizardReducer(state, itemRemovalToggled("item-1"));

    expect(state.itemDecisions["item-1"]).toEqual({ removed: true });
  });

  it("resets to the initial state", () => {
    const changed = wizardReducer(initial, fieldChanged({ field: "premise", value: "Etwas" }));

    expect(wizardReducer(changed, wizardReset())).toEqual(initial);
  });
});

describe("buildProposeRequest", () => {
  const filled: WizardState = {
    ...initial,
    premise: "Ein Kurier verschwindet spurlos.",
    controlMode: "player",
    characters: [{ name: "Elian", description: "Reisender" }, { name: "", description: "wird ignoriert" }],
    genre: "dark_fantasy",
    tone: "dark",
    proseStyle: "balanced",
    perspective: "third_person_limited",
    pacing: "balanced",
    length: "standard",
    playerAgency: "strict",
    consequence: "balanced",
    challenge: "balanced",
    contentProfile: "teen",
  };

  it("drops characters with an empty name and maps the profile fields", () => {
    expect(buildProposeRequest(filled)).toEqual({
      initial_prompt: "Ein Kurier verschwindet spurlos.",
      control_mode: "player",
      controllable_characters: [{ name: "Elian", description: "Reisender" }],
      language: "de",
      prompt_profile: {
        genre: "dark_fantasy",
        tone: "dark",
        prose_style: "balanced",
        perspective: "third_person_limited",
        pacing: "balanced",
        length: "standard",
        player_agency: "strict",
        consequence: "balanced",
        challenge: "balanced",
        content_profile: "teen",
      },
    });
  });
});

describe("buildConfirmRequest", () => {
  it("throws without a proposal", () => {
    expect(() => buildConfirmRequest(initial)).toThrow();
  });

  it("builds decision arrays from the proposal state", () => {
    const state = wizardReducer(initial, proposalReceived(proposal));

    expect(buildConfirmRequest(state)).toEqual({
      proposal_id: proposal.proposal_id,
      run_name: "Die Schatten von Auenfall",
      character_decisions: [
        { entity_id: "char-1", role: "player", removed: false },
        { entity_id: "char-2", role: "npc", removed: false },
      ],
      item_decisions: [{ entity_id: "item-1", removed: false }],
    });
  });
});

describe("hasPlayableCharacter", () => {
  it("is false before a proposal exists", () => {
    expect(hasPlayableCharacter(initial)).toBe(false);
  });

  it("is true once a character is marked as player", () => {
    const state = wizardReducer(initial, proposalReceived(proposal));

    expect(hasPlayableCharacter(state)).toBe(true);
  });

  it("is false again once the sole player character is removed", () => {
    let state = wizardReducer(initial, proposalReceived(proposal));
    state = wizardReducer(state, characterRemovalToggled("char-1"));

    expect(hasPlayableCharacter(state)).toBe(false);
  });

  it("is false when every character is an NPC", () => {
    let state = wizardReducer(initial, proposalReceived(proposal));
    state = wizardReducer(state, characterRoleChanged({ entityId: "char-1", role: "npc" }));

    expect(hasPlayableCharacter(state)).toBe(false);
  });
});
