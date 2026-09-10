import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button } from "../../components/Button/Button";
import { ImageSlot } from "../../components/ImageSlot/ImageSlot";
import {
  ArrowRightIcon,
  BookIcon,
  CompassIcon,
  DarkFantasyIcon,
  FantasyIcon,
  MysteryIcon,
  SciFiIcon,
  SignInIcon,
  SteampunkIcon,
} from "../../icons";
import "./Landing.css";

// Illustrative only — the actual selectable options for a story come from
// the live `/api/v1/prompt-profile` catalog (Schritt 7), not from this list.
// `genreKey` matches that catalog's genre option ids, so the label comes
// from the same translation namespace a real catalog-driven label would.
const GENRES = [
  { genreKey: "dark_fantasy", Icon: DarkFantasyIcon },
  { genreKey: "fantasy", Icon: FantasyIcon },
  { genreKey: "science_fiction", Icon: SciFiIcon },
  { genreKey: "mystery", Icon: MysteryIcon },
  { genreKey: "steam_punk", Icon: SteampunkIcon },
] as const;

const STEPS = ["world", "act", "memory"] as const;

export function Landing() {
  const navigate = useNavigate();
  const { t } = useTranslation();

  return (
    <div className="landing">
      <div className="landing-topbar">
        <div className="landing-brand">
          <CompassIcon />
          <span>{t("landing.brand")}</span>
        </div>
        <Button variant="ghost" icon={<SignInIcon />}>
          {t("landing.signIn")}
        </Button>
      </div>

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
        <ImageSlot className="landing-hero-art" label={t("landing.heroArtPlaceholder")} />
      </div>

      <div className="landing-genres">
        <div className="landing-section-label">{t("landing.genresLabel")}</div>
        <div className="landing-genre-row">
          {GENRES.map(({ genreKey, Icon }) => (
            <div className="landing-genre-card" key={genreKey}>
              <Icon />
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
