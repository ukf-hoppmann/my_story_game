import { Fragment, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAppDispatch, useAppSelector } from "../../app/hooks";
import {
  useConfirmRunMutation,
  usePromptProfileCatalogQuery,
  useProposeRunMutation,
  useStartPlaythroughMutation,
} from "../../api/apiSlice";
import { toQueryError } from "../../api/queryError";
import type { PromptProfileCategory } from "../../api/types";
import { Button } from "../../components/Button/Button";
import { Chip } from "../../components/Chip/Chip";
import { ErrorBanner } from "../../components/ErrorBanner/ErrorBanner";
import { ImageSlot } from "../../components/ImageSlot/ImageSlot";
import { Paragraphs } from "../../components/Paragraphs";
import { ArrowRightIcon, ChevronDownIcon, CompassIcon, PlusIcon, TrashIcon } from "../../icons";
import { formatOptionLabel } from "../../utils/formatOptionLabel";
import { getGenreImageUrl } from "./genreImages";
import {
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
  stepChanged,
  proposalReceived,
  type WizardStep,
  type WizardTextField,
} from "../../features/wizard/wizardSlice";
import { isPresetAvailable, matchingPresetId, STYLE_PRESETS } from "../../features/wizard/stylePresets";
import "./Wizard.css";

const PREMISE_MAX_LENGTH = 500;

const STEP_TITLE_KEYS: Record<WizardStep, string> = {
  welt: "wizard.stepTitles.welt",
  figur: "wizard.stepTitles.figur",
  stil: "wizard.stepTitles.stil",
  review: "wizard.stepTitles.review",
};

const STEP_SHORT_LABEL_KEYS: Record<Exclude<WizardStep, "review">, string> = {
  welt: "wizard.stepShortLabels.welt",
  figur: "wizard.stepShortLabels.figur",
  stil: "wizard.stepShortLabels.stil",
};

function findCategory(
  categories: PromptProfileCategory[] | undefined,
  id: string,
): PromptProfileCategory | undefined {
  return categories?.find((category) => category.id === id);
}

/** Maps each prompt-profile catalog category to its wizard-state field.
 *  `CategoryField` below only *displays* the catalog default until the user
 *  clicks a badge — without this, an unedited field is submitted as an
 *  empty string (the backend rejects that with 422 string_too_short). */
const CATEGORY_FIELD_MAP: { categoryId: string; field: WizardTextField }[] = [
  { categoryId: "genre", field: "genre" },
  { categoryId: "tone", field: "tone" },
  { categoryId: "prose_style", field: "proseStyle" },
  { categoryId: "perspective", field: "perspective" },
  { categoryId: "pacing", field: "pacing" },
  { categoryId: "length", field: "length" },
  { categoryId: "player_agency", field: "playerAgency" },
  { categoryId: "consequence", field: "consequence" },
  { categoryId: "challenge", field: "challenge" },
  { categoryId: "content_profile", field: "contentProfile" },
];

interface CategoryFieldProps {
  category: PromptProfileCategory | undefined;
  label: string;
  value: string;
  onSelect: (optionId: string) => void;
}

/** One catalog-backed badge row (Genre, Ton, Prosastil, ...). Renders
 *  nothing until its category has loaded; falls back to the catalog's
 *  default option until the user picks explicitly. */
function CategoryField({ category, label, value, onSelect }: CategoryFieldProps) {
  if (!category) {
    return null;
  }
  const effective = value || category.default_option_id;

  return (
    <div className="wizard-field">
      <label>{label}</label>
      <div className="wizard-badge-row">
        {category.options.map((option) => (
          <Chip
            key={option.id}
            selected={option.id === effective}
            title={option.description}
            onClick={() => onSelect(option.id)}
          >
            {formatOptionLabel(option.id)}
          </Chip>
        ))}
      </div>
    </div>
  );
}

/**
 * The story-creation wizard: Welt -> Figur & Prämisse -> Stil -> Vorschlag
 * bestätigen -> Geschichte beginnen. Every selectable option (Genre, Ton,
 * Prosastil, ...) is sourced live from GET /api/v1/prompt-profile, never
 * hardcoded, so the wizard always reflects what the backend's prompt
 * package currently allows. Field/step state lives in the wizard Redux
 * slice; the propose/confirm/start-playthrough calls are RTK Query
 * mutations.
 */
export function Wizard() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const wizard = useAppSelector((state) => state.wizard);
  const { data: catalog, isLoading: catalogLoading, error: catalogError } = usePromptProfileCatalogQuery();
  const [stilAdvancedOpen, setStilAdvancedOpen] = useState(false);

  const [proposeRun, proposeState] = useProposeRunMutation();
  const [confirmRun, confirmState] = useConfirmRunMutation();
  const [startPlaythrough, startState] = useStartPlaythroughMutation();

  const setField = (field: WizardTextField) => (value: string) => dispatch(fieldChanged({ field, value }));

  // Seed the wizard state with the catalog's defaults once it loads, for
  // every field the user hasn't touched yet — synchronizing with the
  // external catalog data, not deriving a purely local default, so an
  // effect (not "compute during render") is the right tool here.
  useEffect(() => {
    if (!catalog) {
      return;
    }
    for (const { categoryId, field } of CATEGORY_FIELD_MAP) {
      if (wizard[field]) {
        continue;
      }
      const category = findCategory(catalog.categories, categoryId);
      if (category) {
        dispatch(fieldChanged({ field, value: category.default_option_id }));
      }
    }
    // Only re-run when the catalog itself changes — re-checking on every
    // wizard-field change would fight the user's own edits.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [catalog, dispatch]);

  async function handleCreateProposal() {
    try {
      const proposal = await proposeRun(buildProposeRequest(wizard)).unwrap();
      dispatch(proposalReceived(proposal));
    } catch (error) {
      // A rejection from the mutation itself is already surfaced via
      // proposeState.error below; this only still matters for a synchronous
      // exception thrown before the request was dispatched (e.g. a bug in
      // buildProposeRequest), which `unwrap()` never produces — without this,
      // TASK-030's incident showed such a failure would vanish silently.
      if (!(error instanceof Object && "status" in error)) {
        toQueryError(error, "wizard.handleCreateProposal");
      }
    }
  }

  async function handleConfirmAndStart() {
    try {
      const draft = await confirmRun(buildConfirmRequest(wizard)).unwrap();
      const active = await startPlaythrough(draft.game_run.id).unwrap();
      navigate(`/stories/${active.game_run.id}`);
    } catch (error) {
      // Same reasoning as handleCreateProposal: confirmState.error/
      // startState.error already cover the mutations' own rejections.
      if (!(error instanceof Object && "status" in error)) {
        toQueryError(error, "wizard.handleConfirmAndStart");
      }
    }
  }

  const selectedPresetId = matchingPresetId(wizard);
  const canStart = hasPlayableCharacter(wizard);
  // The backend requires exactly one user-named character in player mode
  // (it does not invent a player character from the premise alone) —
  // director mode has no such requirement (0..N controllable characters).
  const canProceedFromFigur =
    wizard.premise.trim().length > 0 &&
    (wizard.controlMode === "director" || wizard.characters[0]?.name.trim().length > 0);

  return (
    <div className="wizard-page">
      <div className="wizard-frame">
        <div className="wizard-art">
          <ImageSlot
            imageUrl={getGenreImageUrl(wizard.genre)}
            label={t("wizard.previewPlaceholder")}
            style={{ height: "100%" }}
          />
          <div className="wizard-art-brand">
            <CompassIcon />
            <span>{t("wizard.artBrand")}</span>
          </div>
        </div>

        <div className="wizard-form">
          <div className="wizard-eyebrow">{t("wizard.eyebrow")}</div>
          <h2>{t(STEP_TITLE_KEYS[wizard.step])}</h2>

          <div className="wizard-stepper">
            {(["welt", "figur", "stil"] as const).map((step, index) => {
              const active = wizard.step === step || (wizard.step === "review" && step === "stil");
              return (
                <Fragment key={step}>
                  {index > 0 && <span className="line" />}
                  <div className={`dot ${active ? "dot--active" : "dot--todo"}`}>{index + 1}</div>
                  <span className={`lbl ${active ? "lbl--active" : ""}`}>{t(STEP_SHORT_LABEL_KEYS[step])}</span>
                </Fragment>
              );
            })}
          </div>

          {wizard.step === "welt" && (
            <>
              {catalogLoading && <p className="wizard-status">{t("wizard.loadingOptions")}</p>}
              <ErrorBanner error={catalogError} fallbackKey="wizard.catalogError" className="wizard-error" />

              <CategoryField
                category={findCategory(catalog?.categories, "genre")}
                label={t("wizard.labels.genre")}
                value={wizard.genre}
                onSelect={setField("genre")}
              />
              <CategoryField
                category={findCategory(catalog?.categories, "tone")}
                label={t("wizard.labels.tone")}
                value={wizard.tone}
                onSelect={setField("tone")}
              />
              <CategoryField
                category={findCategory(catalog?.categories, "content_profile")}
                label={t("wizard.labels.contentProfile")}
                value={wizard.contentProfile}
                onSelect={setField("contentProfile")}
              />
              <CategoryField
                category={findCategory(catalog?.categories, "perspective")}
                label={t("wizard.labels.perspective")}
                value={wizard.perspective}
                onSelect={setField("perspective")}
              />

              <div className="wizard-form-foot">
                <span className="wizard-hint">{t("wizard.laterHint")}</span>
                <Button icon={<ArrowRightIcon />} onClick={() => dispatch(stepChanged("figur"))}>
                  {t("common.next")}
                </Button>
              </div>
            </>
          )}

          {wizard.step === "figur" && (
            <>
              <div className="wizard-field">
                <label htmlFor="wizard-premise">{t("wizard.labels.premise")}</label>
                <textarea
                  id="wizard-premise"
                  placeholder={t("wizard.premisePlaceholder")}
                  maxLength={PREMISE_MAX_LENGTH}
                  value={wizard.premise}
                  onChange={(event) => setField("premise")(event.target.value)}
                />
                <div className="wizard-field-meta">
                  {wizard.premise.length} / {PREMISE_MAX_LENGTH}
                </div>
              </div>

              <div className="wizard-field">
                <label>{t("wizard.labels.viewpoint")}</label>
                <div className="wizard-badge-row">
                  <Chip
                    selected={wizard.controlMode === "player"}
                    onClick={() => dispatch(controlModeChanged("player"))}
                  >
                    {t("wizard.controlModePlayer")}
                  </Chip>
                  <Chip
                    selected={wizard.controlMode === "director"}
                    onClick={() => dispatch(controlModeChanged("director"))}
                  >
                    {t("wizard.controlModeDirector")}
                  </Chip>
                </div>
              </div>

              <p className="wizard-hint-block">
                {wizard.controlMode === "player"
                  ? t("wizard.playerModeHint")
                  : t("wizard.directorModeHint")}
              </p>

              {(wizard.controlMode === "player" ? wizard.characters.slice(0, 1) : wizard.characters).map(
                (character, index) => (
                  <div className="wizard-character-draft" key={index}>
                    {wizard.controlMode === "director" && (
                      <div className="wizard-character-draft-head">
                        <span>{t("wizard.characterHeading", { number: index + 1 })}</span>
                        {wizard.characters.length > 1 && (
                          <button
                            type="button"
                            className="wizard-link-button"
                            onClick={() => dispatch(characterRemoved(index))}
                          >
                            {t("common.remove")}
                          </button>
                        )}
                      </div>
                    )}
                    <div className="wizard-field" style={{ marginBottom: 0 }}>
                      <label htmlFor={`wizard-character-name-${index}`}>{t("wizard.labels.name")}</label>
                      <input
                        id={`wizard-character-name-${index}`}
                        type="text"
                        placeholder={
                          wizard.controlMode === "player"
                            ? t("wizard.namePlaceholderRequired")
                            : t("wizard.namePlaceholderOptional")
                        }
                        value={character.name}
                        onChange={(event) =>
                          dispatch(
                            characterFieldChanged({ index, field: "name", value: event.target.value }),
                          )
                        }
                      />
                    </div>
                    <div className="wizard-field" style={{ marginBottom: 0 }}>
                      <label htmlFor={`wizard-character-desc-${index}`}>{t("wizard.labels.whoAreYou")}</label>
                      <textarea
                        id={`wizard-character-desc-${index}`}
                        placeholder={t("wizard.descriptionPlaceholder")}
                        value={character.description}
                        onChange={(event) =>
                          dispatch(
                            characterFieldChanged({
                              index,
                              field: "description",
                              value: event.target.value,
                            }),
                          )
                        }
                      />
                    </div>
                  </div>
                ),
              )}

              {wizard.controlMode === "director" && (
                <button
                  type="button"
                  className="wizard-add-character"
                  onClick={() => dispatch(characterAdded())}
                >
                  <PlusIcon style={{ width: 14, height: 14 }} />
                  {t("wizard.addCharacter")}
                </button>
              )}

              <CategoryField
                category={findCategory(catalog?.categories, "player_agency")}
                label={t("wizard.labels.playerAgency")}
                value={wizard.playerAgency}
                onSelect={setField("playerAgency")}
              />

              <div className="wizard-form-foot">
                <Button variant="ghost" onClick={() => dispatch(stepChanged("welt"))}>
                  {t("common.back")}
                </Button>
                <Button
                  icon={<ArrowRightIcon />}
                  disabled={!canProceedFromFigur}
                  onClick={() => dispatch(stepChanged("stil"))}
                >
                  {t("common.next")}
                </Button>
              </div>
            </>
          )}

          {wizard.step === "stil" && (
            <>
              <div className="wizard-preset-grid">
                {STYLE_PRESETS.filter((preset) => isPresetAvailable(preset, catalog)).map((preset) => (
                  <button
                    key={preset.id}
                    type="button"
                    className={`wizard-preset-card${
                      selectedPresetId === preset.id ? " wizard-preset-card--selected" : ""
                    }`}
                    onClick={() => {
                      dispatch(fieldChanged({ field: "proseStyle", value: preset.values.proseStyle }));
                      dispatch(fieldChanged({ field: "pacing", value: preset.values.pacing }));
                      dispatch(fieldChanged({ field: "length", value: preset.values.length }));
                      dispatch(fieldChanged({ field: "consequence", value: preset.values.consequence }));
                      dispatch(fieldChanged({ field: "challenge", value: preset.values.challenge }));
                    }}
                  >
                    <div className="wizard-preset-card-title">{t(`wizard.presets.${preset.id}.label`)}</div>
                    <div className="wizard-preset-card-desc">
                      {t(`wizard.presets.${preset.id}.description`)}
                    </div>
                  </button>
                ))}
              </div>

              <button
                type="button"
                className={`wizard-advanced-toggle${stilAdvancedOpen ? " wizard-advanced-toggle--open" : ""}`}
                onClick={() => setStilAdvancedOpen((open) => !open)}
              >
                {stilAdvancedOpen ? t("wizard.hideCustomCombo") : t("wizard.showCustomCombo")}
                <ChevronDownIcon />
              </button>

              {stilAdvancedOpen && (
                <div className="wizard-advanced">
                  <CategoryField
                    category={findCategory(catalog?.categories, "prose_style")}
                    label={t("wizard.labels.proseStyle")}
                    value={wizard.proseStyle}
                    onSelect={setField("proseStyle")}
                  />
                  <CategoryField
                    category={findCategory(catalog?.categories, "pacing")}
                    label={t("wizard.labels.pacing")}
                    value={wizard.pacing}
                    onSelect={setField("pacing")}
                  />
                  <CategoryField
                    category={findCategory(catalog?.categories, "length")}
                    label={t("wizard.labels.length")}
                    value={wizard.length}
                    onSelect={setField("length")}
                  />
                  <CategoryField
                    category={findCategory(catalog?.categories, "consequence")}
                    label={t("wizard.labels.consequence")}
                    value={wizard.consequence}
                    onSelect={setField("consequence")}
                  />
                  <CategoryField
                    category={findCategory(catalog?.categories, "challenge")}
                    label={t("wizard.labels.challenge")}
                    value={wizard.challenge}
                    onSelect={setField("challenge")}
                  />
                </div>
              )}

              <ErrorBanner error={proposeState.error} fallbackKey="wizard.proposeError" className="wizard-error" />

              <div className="wizard-form-foot">
                <Button variant="ghost" onClick={() => dispatch(stepChanged("figur"))}>
                  {t("common.back")}
                </Button>
                <Button
                  icon={<ArrowRightIcon />}
                  disabled={proposeState.isLoading}
                  onClick={handleCreateProposal}
                >
                  {proposeState.isLoading ? t("wizard.creatingProposal") : t("wizard.createProposal")}
                </Button>
              </div>
            </>
          )}

          {wizard.step === "review" && wizard.proposal && (
            <>
              <div className="wizard-narration">
                <Paragraphs text={wizard.proposal.openingNarration} />
              </div>

              <div className="wizard-field">
                <label htmlFor="wizard-run-name">{t("wizard.labels.runName")}</label>
                <input
                  id="wizard-run-name"
                  type="text"
                  value={wizard.runName}
                  onChange={(event) => setField("runName")(event.target.value)}
                />
              </div>

              <div className="wizard-field">
                <label>{t("wizard.labels.characters")}</label>
                {wizard.proposal.world.entities
                  .filter((entity) => entity.kind === "character")
                  .map((entity) => {
                    const decision = wizard.characterDecisions[entity.id];
                    if (!decision) {
                      return null;
                    }
                    return (
                      <div className="wizard-decision-row" key={entity.id}>
                        <span className="wizard-decision-name">{entity.label}</span>
                        <div className="wizard-decision-actions">
                          <Chip
                            selected={decision.role === "player"}
                            onClick={() =>
                              dispatch(characterRoleChanged({ entityId: entity.id, role: "player" }))
                            }
                          >
                            {t("wizard.rolePlayer")}
                          </Chip>
                          <Chip
                            selected={decision.role === "npc"}
                            onClick={() =>
                              dispatch(characterRoleChanged({ entityId: entity.id, role: "npc" }))
                            }
                          >
                            {t("wizard.roleNpc")}
                          </Chip>
                          <Chip
                            selected={decision.removed}
                            icon={<TrashIcon style={{ width: 13, height: 13 }} />}
                            onClick={() => dispatch(characterRemovalToggled(entity.id))}
                          >
                            {t("common.remove")}
                          </Chip>
                        </div>
                      </div>
                    );
                  })}
              </div>

              <div className="wizard-field">
                <label>{t("wizard.labels.items")}</label>
                {wizard.proposal.world.entities
                  .filter((entity) => entity.kind === "item")
                  .map((entity) => {
                    const decision = wizard.itemDecisions[entity.id];
                    if (!decision) {
                      return null;
                    }
                    return (
                      <div className="wizard-decision-row" key={entity.id}>
                        <span className="wizard-decision-name">{entity.label}</span>
                        <div className="wizard-decision-actions">
                          <Chip
                            selected={decision.removed}
                            icon={<TrashIcon style={{ width: 13, height: 13 }} />}
                            onClick={() => dispatch(itemRemovalToggled(entity.id))}
                          >
                            {t("common.remove")}
                          </Chip>
                        </div>
                      </div>
                    );
                  })}
              </div>

              {!canStart && <p className="wizard-error">{t("wizard.noPlayerSelected")}</p>}
              <ErrorBanner
                error={confirmState.error ?? startState.error}
                fallbackKey="wizard.startError"
                className="wizard-error"
              />

              <div className="wizard-form-foot">
                <span className="wizard-hint">{t("wizard.laterHint")}</span>
                <Button
                  icon={<ArrowRightIcon />}
                  disabled={!canStart || confirmState.isLoading || startState.isLoading}
                  onClick={handleConfirmAndStart}
                >
                  {confirmState.isLoading || startState.isLoading
                    ? t("wizard.creatingStory")
                    : t("wizard.startStory")}
                </Button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
