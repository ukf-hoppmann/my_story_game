import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button } from "../../components/Button/Button";
import { ImageSlot } from "../../components/ImageSlot/ImageSlot";
import { ArrowRightIcon, BookIcon } from "../../icons";
import "./Landing.css";

// Illustrative only — the actual selectable options for a story come from
// the live `/api/v1/prompt-profile` catalog (Schritt 7), not from this list.
// `genreKey` matches that catalog's genre option ids, so the label comes
// from the same translation namespace a real catalog-driven label would.
// Same fixed one-image-per-genre asset as the wizard's preview (Schritt 8),
// just a separate, landscape-cropped set made for this card layout.
const GENRES = [
  { genreKey: "dark_fantasy", image: "/assets/story-landing/genre-dark_fantasy.png" },
  { genreKey: "fantasy", image: "/assets/story-landing/genre-fantasy.png" },
  { genreKey: "science_fiction", image: "/assets/story-landing/genre-science_fiction.png" },
  { genreKey: "mystery", image: "/assets/story-landing/genre-mystery.png" },
  { genreKey: "steam_punk", image: "/assets/story-landing/genre-steam_punk.png" },
] as const;

const HERO_IMAGE_URL = "/assets/story-landing/landing-hero.png";

const STEPS = ["world", "act", "memory"] as const;

export function Landing() {
  const navigate = useNavigate();
  const { t } = useTranslation();

  return (
    <div className="landing">
      <div className="landing-hero">
        <div>
          <div className="landing-eyebrow">{t("landing.eyebrow")}</div>
          <h1>{t("landing.heroTitle")}</h1>
          <p className="landing-hero-sub">{t("landing.heroSub")}</p>
          <div className="landing-cta-row">
            <Button icon={<ArrowRightIcon />} onClick={() => navigate("/new")}>
              {t("landing.startStory")}
            </Button>
            <Button variant="ghost" icon={<BookIcon />} onClick={() => navigate("/library")}>
              {t("common.yourStories")}
            </Button>
          </div>
        </div>
        <ImageSlot
          className="landing-hero-art"
          imageUrl={HERO_IMAGE_URL}
          label={t("landing.heroArtPlaceholder")}
        />
      </div>

      <div className="landing-genres">
        <div className="landing-section-label">{t("landing.genresLabel")}</div>
        <div className="landing-genre-row">
          {GENRES.map(({ genreKey, image }) => (
            <div className="landing-genre-card" key={genreKey}>
              <img className="landing-genre-card-img" src={image} alt="" />
              <span>{t(`landing.genres.${genreKey}`)}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="landing-how">
        <div className="landing-section-label">{t("landing.howItWorksLabel")}</div>
        <div className="landing-steps">
          {STEPS.map((stepKey, index) => (
            <div className="landing-step" key={stepKey}>
              <div className="landing-step-num">{index + 1}</div>
              <h3>{t(`landing.steps.${stepKey}.title`)}</h3>
              <p>{t(`landing.steps.${stepKey}.text`)}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="landing-foot">{t("landing.footQuote")}</div>
    </div>
  );
}
