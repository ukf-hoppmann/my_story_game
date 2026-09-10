import { Fragment, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAppDispatch, useAppSelector } from "../../app/hooks";
import {
  useConfirmRunMutation,
  usePromptProfileCatalogQuery,
  useProposeRunMutation,
  useStartPlaythroughMutation,
} from "../../api/apiSlice";
import type { PromptProfileCategory } from "../../api/types";
import { Button } from "../../components/Button/Button";
import { Chip } from "../../components/Chip/Chip";
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

const STEP_TITLES: Record<WizardStep, string> = {
  welt: "Welt",
  figur: "Figur & Prämisse",
  stil: "Erzählstil",
  review: "Geschichte bestätigen",
};

const STEP_SHORT_LABELS: Record<Exclude<WizardStep, "review">, string> = {
  welt: "Welt",
  figur: "Figur",
  stil: "Stil",
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
    } catch {
      // Surfaced via proposeState.error below — nothing else to do here.
    }
  }

  async function handleConfirmAndStart() {
    try {
      const draft = await confirmRun(buildConfirmRequest(wizard)).unwrap();
      const active = await startPlaythrough(draft.game_run.id).unwrap();
      navigate(`/stories/${active.game_run.id}`);
    } catch {
      // Surfaced via confirmState.error / startState.error below.
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
            label="Platzhalter · Vorschaubild"
            style={{ height: "100%" }}
          />
          <div className="wizard-art-brand">
            <CompassIcon />
            <span>Eine neue Geschichte beginnt</span>
          </div>
        </div>

        <div className="wizard-form">
          <div className="wizard-eyebrow">Neue Geschichte</div>
          <h2>{STEP_TITLES[wizard.step]}</h2>

          <div className="wizard-stepper">
            {(["welt", "figur", "stil"] as const).map((step, index) => {
              const active = wizard.step === step || (wizard.step === "review" && step === "stil");
              return (
                <Fragment key={step}>
                  {index > 0 && <span className="line" />}
                  <div className={`dot ${active ? "dot--active" : "dot--todo"}`}>{index + 1}</div>
                  <span className={`lbl ${active ? "lbl--active" : ""}`}>{STEP_SHORT_LABELS[step]}</span>
                </Fragment>
              );
            })}
          </div>

          {wizard.step === "welt" && (
            <>
              {catalogLoading && <p className="wizard-status">Lade Optionen …</p>}
              {catalogError && (
                <p className="wizard-error">
                  Optionen konnten nicht geladen werden. Bitte versuche es erneut.
                </p>
              )}

              <CategoryField
                category={findCategory(catalog?.categories, "genre")}
                label="Genre"
                value={wizard.genre}
                onSelect={setField("genre")}
              />
              <CategoryField
                category={findCategory(catalog?.categories, "tone")}
                label="Ton"
                value={wizard.tone}
                onSelect={setField("tone")}
              />
              <CategoryField
                category={findCategory(catalog?.categories, "content_profile")}
                label="Inhaltsprofil"
                value={wizard.contentProfile}
                onSelect={setField("contentProfile")}
              />
              <CategoryField
                category={findCategory(catalog?.categories, "perspective")}
                label="Erzählperspektive"
                value={wizard.perspective}
                onSelect={setField("perspective")}
              />

              <div className="wizard-form-foot">
                <span className="wizard-hint">Du kannst alles später anpassen.</span>
                <Button icon={<ArrowRightIcon />} onClick={() => dispatch(stepChanged("figur"))}>
                  Weiter
                </Button>
              </div>
            </>
          )}

          {wizard.step === "figur" && (
            <>
              <div className="wizard-field">
                <label htmlFor="wizard-premise">Prämisse</label>
                <textarea
                  id="wizard-premise"
                  placeholder="Worum geht es in deiner Geschichte?"
                  maxLength={PREMISE_MAX_LENGTH}
                  value={wizard.premise}
                  onChange={(event) => setField("premise")(event.target.value)}
                />
                <div className="wizard-field-meta">
                  {wizard.premise.length} / {PREMISE_MAX_LENGTH}
                </div>
              </div>

              <div className="wizard-field">
                <label>Perspektive</label>
                <div className="wizard-badge-row">
                  <Chip
                    selected={wizard.controlMode === "player"}
                    onClick={() => dispatch(controlModeChanged("player"))}
                  >
                    Ich-Charakter
                  </Chip>
                  <Chip
                    selected={wizard.controlMode === "director"}
                    onClick={() => dispatch(controlModeChanged("director"))}
                  >
                    Regie
                  </Chip>
                </div>
              </div>

              <p className="wizard-hint-block">
                {wizard.controlMode === "player"
                  ? "Als Ich-Charakter brauchst du einen Namen für deine Figur — den Rest (Aussehen, Hintergrund, ...) darf die KI ergänzen."
                  : "Kein Name? Kein Problem — die KI schlägt dir passende Figuren aus deiner Prämisse vor, sobald du den Vorschlag erstellst."}
              </p>

              {(wizard.controlMode === "player" ? wizard.characters.slice(0, 1) : wizard.characters).map(
                (character, index) => (
                  <div className="wizard-character-draft" key={index}>
                    {wizard.controlMode === "director" && (
                      <div className="wizard-character-draft-head">
                        <span>Figur {index + 1}</span>
                        {wizard.characters.length > 1 && (
                          <button
                            type="button"
                            className="wizard-link-button"
                            onClick={() => dispatch(characterRemoved(index))}
                          >
                            Entfernen
                          </button>
                        )}
                      </div>
                    )}
                    <div className="wizard-field" style={{ marginBottom: 0 }}>
                      <label htmlFor={`wizard-character-name-${index}`}>Name</label>
                      <input
                        id={`wizard-character-name-${index}`}
                        type="text"
                        placeholder={
                          wizard.controlMode === "player" ? "Name deiner Figur" : "Name deiner Figur (optional)"
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
                      <label htmlFor={`wizard-character-desc-${index}`}>Wer bist du?</label>
                      <textarea
                        id={`wizard-character-desc-${index}`}
                        placeholder="Beschreibe deine Figur in wenigen Sätzen …"
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
                  Weitere Figur hinzufügen
                </button>
              )}

              <CategoryField
                category={findCategory(catalog?.categories, "player_agency")}
                label="Handlungsfreiheit"
                value={wizard.playerAgency}
                onSelect={setField("playerAgency")}
              />

              <div className="wizard-form-foot">
                <Button variant="ghost" onClick={() => dispatch(stepChanged("welt"))}>
                  Zurück
                </Button>
                <Button
                  icon={<ArrowRightIcon />}
                  disabled={!canProceedFromFigur}
                  onClick={() => dispatch(stepChanged("stil"))}
                >
                  Weiter
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
                    <div className="wizard-preset-card-title">{preset.label}</div>
                    <div className="wizard-preset-card-desc">{preset.description}</div>
                  </button>
                ))}
              </div>

              <button
                type="button"
                className={`wizard-advanced-toggle${stilAdvancedOpen ? " wizard-advanced-toggle--open" : ""}`}
                onClick={() => setStilAdvancedOpen((open) => !open)}
              >
                {stilAdvancedOpen ? "Eigene Kombination ausblenden" : "Eigene Kombination wählen"}
                <ChevronDownIcon />
              </button>

              {stilAdvancedOpen && (
                <div className="wizard-advanced">
                  <CategoryField
                    category={findCategory(catalog?.categories, "prose_style")}
                    label="Prosastil"
                    value={wizard.proseStyle}
                    onSelect={setField("proseStyle")}
                  />
                  <CategoryField
                    category={findCategory(catalog?.categories, "pacing")}
                    label="Erzähltempo"
                    value={wizard.pacing}
                    onSelect={setField("pacing")}
                  />
                  <CategoryField
                    category={findCategory(catalog?.categories, "length")}
                    label="Länge"
                    value={wizard.length}
                    onSelect={setField("length")}
                  />
                  <CategoryField
                    category={findCategory(catalog?.categories, "consequence")}
                    label="Konsequenzen"
                    value={wizard.consequence}
                    onSelect={setField("consequence")}
                  />
                  <CategoryField
                    category={findCategory(catalog?.categories, "challenge")}
                    label="Herausforderung"
                    value={wizard.challenge}
                    onSelect={setField("challenge")}
                  />
                </div>
              )}

              {proposeState.error && (
                <p className="wizard-error">
                  Der Vorschlag konnte nicht erstellt werden. Bitte versuche es erneut.
                </p>
              )}

              <div className="wizard-form-foot">
                <Button variant="ghost" onClick={() => dispatch(stepChanged("figur"))}>
                  Zurück
                </Button>
                <Button
                  icon={<ArrowRightIcon />}
                  disabled={proposeState.isLoading}
                  onClick={handleCreateProposal}
                >
                  {proposeState.isLoading ? "Erstelle Vorschlag …" : "Vorschlag erstellen"}
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
                <label htmlFor="wizard-run-name">Name der Geschichte</label>
                <input
                  id="wizard-run-name"
                  type="text"
                  value={wizard.runName}
                  onChange={(event) => setField("runName")(event.target.value)}
                />
              </div>

              <div className="wizard-field">
                <label>Figuren</label>
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
                            Spieler
                          </Chip>
                          <Chip
                            selected={decision.role === "npc"}
                            onClick={() =>
                              dispatch(characterRoleChanged({ entityId: entity.id, role: "npc" }))
                            }
                          >
                            NPC
                          </Chip>
                          <Chip
                            selected={decision.removed}
                            icon={<TrashIcon style={{ width: 13, height: 13 }} />}
                            onClick={() => dispatch(characterRemovalToggled(entity.id))}
                          >
                            Entfernen
                          </Chip>
                        </div>
                      </div>
                    );
                  })}
              </div>

              <div className="wizard-field">
                <label>Gegenstände</label>
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
                            Entfernen
                          </Chip>
                        </div>
                      </div>
                    );
                  })}
              </div>

              {!canStart && (
                <p className="wizard-error">Wähle eine Figur als Spieler, bevor du beginnst.</p>
              )}
              {(confirmState.error || startState.error) && (
                <p className="wizard-error">
                  Die Geschichte konnte nicht gestartet werden. Bitte versuche es erneut.
                </p>
              )}

              <div className="wizard-form-foot">
                <span className="wizard-hint">Du kannst alles später anpassen.</span>
                <Button
                  icon={<ArrowRightIcon />}
                  disabled={!canStart || confirmState.isLoading || startState.isLoading}
                  onClick={handleConfirmAndStart}
                >
                  {confirmState.isLoading || startState.isLoading
                    ? "Geschichte wird erstellt …"
                    : "Geschichte beginnen"}
                </Button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
