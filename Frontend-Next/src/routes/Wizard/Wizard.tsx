import { useState } from "react";
import { usePromptProfileCatalogQuery } from "../../api/apiSlice";
import type { PromptProfileCategory } from "../../api/types";
import { Button } from "../../components/Button/Button";
import { Chip } from "../../components/Chip/Chip";
import { ImageSlot } from "../../components/ImageSlot/ImageSlot";
import { ArrowRightIcon, CompassIcon } from "../../icons";
import { formatOptionLabel } from "../../utils/formatOptionLabel";
import "./Wizard.css";

const PREMISE_MAX_LENGTH = 500;

function findCategory(
  categories: PromptProfileCategory[] | undefined,
  id: string,
): PromptProfileCategory | undefined {
  return categories?.find((category) => category.id === id);
}

interface OptionRowProps {
  category: PromptProfileCategory;
  selected: string;
  onSelect: (optionId: string) => void;
}

function OptionRow({ category, selected, onSelect }: OptionRowProps) {
  return (
    <div className="wizard-badge-row">
      {category.options.map((option) => (
        <Chip
          key={option.id}
          selected={option.id === selected}
          title={option.description}
          onClick={() => onSelect(option.id)}
        >
          {formatOptionLabel(option.id)}
        </Chip>
      ))}
    </div>
  );
}

/**
 * Wizard Schritt 1 ("Welt & Prämisse"). Genre/Ton options are sourced live
 * from GET /api/v1/prompt-profile — never hardcoded — so the wizard always
 * reflects whatever the backend's prompt package currently allows. Steps 2
 * (Figur) and 3 (Stil) plus the propose/confirm/start submit flow land in
 * Schritt 8.
 */
export function Wizard() {
  const { data: catalog, isLoading, error } = usePromptProfileCatalogQuery();

  const genreCategory = findCategory(catalog?.categories, "genre");
  const toneCategory = findCategory(catalog?.categories, "tone");

  const [title, setTitle] = useState("");
  const [premise, setPremise] = useState("");
  // Empty until the user picks explicitly — derive the effective selection
  // from the catalog's default below rather than syncing it into state via
  // an effect (there is no external system to synchronize with here).
  const [genreChoice, setGenreChoice] = useState<string>("");
  const [toneChoice, setToneChoice] = useState<string>("");

  const genre = genreChoice || genreCategory?.default_option_id || "";
  const tone = toneChoice || toneCategory?.default_option_id || "";

  return (
    <div className="wizard-page">
      <div className="wizard-frame">
        <div className="wizard-art">
          <ImageSlot label="Platzhalter · Vorschaubild" style={{ height: "100%" }} />
          <div className="wizard-art-brand">
            <CompassIcon />
            <span>Eine neue Geschichte beginnt</span>
          </div>
        </div>

        <div className="wizard-form">
          <div className="wizard-eyebrow">Neue Geschichte</div>
          <h2>Welt &amp; Prämisse</h2>

          <div className="wizard-stepper">
            <div className="dot dot--active">1</div>
            <span className="lbl lbl--active">Welt</span>
            <span className="line" />
            <div className="dot dot--todo">2</div>
            <span className="lbl">Figur</span>
            <span className="line" />
            <div className="dot dot--todo">3</div>
            <span className="lbl">Stil</span>
          </div>

          <div className="wizard-field">
            <label htmlFor="wizard-title">Titel</label>
            <input
              id="wizard-title"
              type="text"
              placeholder="Titel deiner Geschichte"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
            />
          </div>

          <div className="wizard-field">
            <label htmlFor="wizard-premise">Prämisse</label>
            <textarea
              id="wizard-premise"
              placeholder="Worum geht es in deiner Geschichte?"
              maxLength={PREMISE_MAX_LENGTH}
              value={premise}
              onChange={(event) => setPremise(event.target.value)}
            />
            <div className="wizard-field-meta">
              {premise.length} / {PREMISE_MAX_LENGTH}
            </div>
          </div>

          {isLoading && <p className="wizard-status">Lade Genre- und Ton-Optionen …</p>}
          {error && (
            <p className="wizard-error">
              Optionen konnten nicht geladen werden. Bitte versuche es erneut.
            </p>
          )}

          {genreCategory && (
            <div className="wizard-field">
              <label>Genre</label>
              <OptionRow category={genreCategory} selected={genre} onSelect={setGenreChoice} />
            </div>
          )}

          {toneCategory && (
            <div className="wizard-field">
              <label>Ton</label>
              <OptionRow category={toneCategory} selected={tone} onSelect={setToneChoice} />
            </div>
          )}

          <div className="wizard-form-foot">
            <span className="wizard-hint">Du kannst alles später anpassen.</span>
            <Button icon={<ArrowRightIcon />} disabled>
              Weiter
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
