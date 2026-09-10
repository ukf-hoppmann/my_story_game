import { describe, expect, it } from "vitest";
import type { PromptProfileCatalog } from "../../api/types";
import { isPresetAvailable, matchingPresetId, STYLE_PRESETS } from "./stylePresets";
import wizardReducer, { fieldChanged } from "./wizardSlice";

function option(id: string) {
  return { id, description: id };
}

const fullCatalog: PromptProfileCatalog = {
  package_id: "story.base",
  package_version: "1",
  categories: [
    { id: "prose_style", default_option_id: "balanced", options: ["balanced", "concise", "descriptive", "dialogue_driven"].map(option) },
    { id: "pacing", default_option_id: "balanced", options: ["balanced", "slow", "fast"].map(option) },
    { id: "length", default_option_id: "standard", options: ["short", "standard", "long"].map(option) },
    { id: "consequence", default_option_id: "balanced", options: ["balanced", "forgiving", "harsh"].map(option) },
    { id: "challenge", default_option_id: "balanced", options: ["balanced", "narrative", "demanding"].map(option) },
  ],
};

describe("isPresetAvailable", () => {
  it("returns false without a catalog", () => {
    expect(isPresetAvailable(STYLE_PRESETS[0], undefined)).toBe(false);
  });

  it("returns true when every referenced option id exists", () => {
    for (const preset of STYLE_PRESETS) {
      expect(isPresetAvailable(preset, fullCatalog)).toBe(true);
    }
  });

  it("returns false when a referenced option id is missing from the catalog", () => {
    const trimmedCatalog: PromptProfileCatalog = {
      ...fullCatalog,
      categories: fullCatalog.categories.map((category) =>
        category.id === "pacing" ? { ...category, options: [option("balanced")] } : category,
      ),
    };

    // "episch" needs pacing "slow", which was just removed.
    const episch = STYLE_PRESETS.find((preset) => preset.id === "episch")!;
    expect(isPresetAvailable(episch, trimmedCatalog)).toBe(false);
  });
});

describe("matchingPresetId", () => {
  const initial = wizardReducer(undefined, { type: "@@INIT" });

  it("matches the default 'ausgewogen' preset out of the box", () => {
    let state = initial;
    for (const [field, value] of [
      ["proseStyle", "balanced"],
      ["pacing", "balanced"],
      ["length", "standard"],
      ["consequence", "balanced"],
      ["challenge", "balanced"],
    ] as const) {
      state = wizardReducer(state, fieldChanged({ field, value }));
    }

    expect(matchingPresetId(state)).toBe("ausgewogen");
  });

  it("returns undefined for a hand-picked combination matching no preset", () => {
    let state = initial;
    state = wizardReducer(state, fieldChanged({ field: "proseStyle", value: "concise" }));
    state = wizardReducer(state, fieldChanged({ field: "pacing", value: "slow" }));
    state = wizardReducer(state, fieldChanged({ field: "length", value: "long" }));
    state = wizardReducer(state, fieldChanged({ field: "consequence", value: "balanced" }));
    state = wizardReducer(state, fieldChanged({ field: "challenge", value: "balanced" }));

    expect(matchingPresetId(state)).toBeUndefined();
  });
});
