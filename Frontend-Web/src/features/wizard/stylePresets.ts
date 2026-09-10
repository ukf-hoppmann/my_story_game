import type { PromptProfileCatalog } from "../../api/types";
import type { WizardState } from "./wizardSlice";

/** The five Stil-step fields a preset sets together. Kept as a distinct
 *  type from `WizardState` so a preset can't accidentally reference an
 *  unrelated field (e.g. genre, which lives on the Welt step). */
export interface StylePresetValues {
  proseStyle: string;
  pacing: string;
  length: string;
  consequence: string;
  challenge: string;
}

export interface StylePreset {
  id: string;
  values: StylePresetValues;
}

/**
 * Curated combinations of the Stil-step catalog options, discussed and
 * approved with the user. These *reference* specific option ids — that's a
 * deliberate, narrow exception to "never hardcode catalog options": the
 * catalog itself (which options exist per category) still comes live from
 * the backend; a preset is a product/UX curation of specific values from
 * it, similar to a copy decision. `isPresetAvailable` guards against a
 * preset referencing an id the live catalog no longer has.
 *
 * `label`/`description` are not stored here — they're display copy, looked
 * up by `id` from the translation catalog (`wizard.presets.<id>.*`) at the
 * call site instead.
 */
export const STYLE_PRESETS: StylePreset[] = [
  {
    id: "ausgewogen",
    values: {
      proseStyle: "balanced",
      pacing: "balanced",
      length: "standard",
      consequence: "balanced",
      challenge: "balanced",
    },
  },
  {
    id: "episch",
    values: {
      proseStyle: "descriptive",
      pacing: "slow",
      length: "long",
      consequence: "forgiving",
      challenge: "narrative",
    },
  },
  {
    id: "schnell",
    values: {
      proseStyle: "concise",
      pacing: "fast",
      length: "short",
      consequence: "harsh",
      challenge: "demanding",
    },
  },
  {
    id: "dialoglastig",
    values: {
      proseStyle: "dialogue_driven",
      pacing: "balanced",
      length: "standard",
      consequence: "forgiving",
      challenge: "narrative",
    },
  },
  {
    id: "duester",
    values: {
      proseStyle: "descriptive",
      pacing: "slow",
      length: "standard",
      consequence: "harsh",
      challenge: "demanding",
    },
  },
];

const PRESET_CATEGORY_IDS: { field: keyof StylePresetValues; categoryId: string }[] = [
  { field: "proseStyle", categoryId: "prose_style" },
  { field: "pacing", categoryId: "pacing" },
  { field: "length", categoryId: "length" },
  { field: "consequence", categoryId: "consequence" },
  { field: "challenge", categoryId: "challenge" },
];

/** A preset is only shown once every option id it references actually
 *  exists in the live catalog — protects against a future catalog change
 *  silently breaking the UI. */
export function isPresetAvailable(preset: StylePreset, catalog: PromptProfileCatalog | undefined): boolean {
  if (!catalog) {
    return false;
  }
  return PRESET_CATEGORY_IDS.every(({ field, categoryId }) => {
    const category = catalog.categories.find((candidate) => candidate.id === categoryId);
    return category?.options.some((option) => option.id === preset.values[field]) ?? false;
  });
}

/** Which preset (if any) matches the wizard's current Stil field values —
 *  used to highlight a card as selected. Returns undefined once the user
 *  has hand-picked a combination that doesn't match any preset. */
export function matchingPresetId(state: WizardState, presets: StylePreset[] = STYLE_PRESETS): string | undefined {
  const current: StylePresetValues = {
    proseStyle: state.proseStyle,
    pacing: state.pacing,
    length: state.length,
    consequence: state.consequence,
    challenge: state.challenge,
  };
  return presets.find(
    (preset) =>
      preset.values.proseStyle === current.proseStyle &&
      preset.values.pacing === current.pacing &&
      preset.values.length === current.length &&
      preset.values.consequence === current.consequence &&
      preset.values.challenge === current.challenge,
  )?.id;
}
