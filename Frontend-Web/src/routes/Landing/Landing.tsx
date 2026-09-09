import { useNavigate } from "react-router-dom";
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
const GENRES = [
  { label: "Dark Fantasy", Icon: DarkFantasyIcon },
  { label: "Fantasy", Icon: FantasyIcon },
  { label: "Science Fiction", Icon: SciFiIcon },
  { label: "Mystery", Icon: MysteryIcon },
  { label: "Steampunk", Icon: SteampunkIcon },
];

const STEPS = [
  {
    title: "Welt & Figur festlegen",
    text: "Titel, Prämisse, Genre, Ton und deine Figur — in drei kurzen Schritten.",
  },
  {
    title: "Handeln",
    text: "Beschreibe, was du tust. Die Geschichte reagiert auf jede Entscheidung.",
  },
  {
    title: "Die Welt merkt sich alles",
    text: "Figuren, Wissen und Ziele bleiben über den ganzen Verlauf erhalten.",
  },
];

export function Landing() {
  const navigate = useNavigate();

  return (
    <div className="landing">
      <div className="landing-topbar">
        <div className="landing-brand">
          <CompassIcon />
          <span>Story Engine</span>
        </div>
        <Button variant="ghost" icon={<SignInIcon />}>
          Anmelden
        </Button>
      </div>

      <div className="landing-hero">
        <div>
          <div className="landing-eyebrow">Interaktives Erzählen</div>
          <h1>Geschichten, die deinen Entscheidungen folgen.</h1>
          <p className="landing-hero-sub">
            Lege eine Welt, eine Figur und einen Ton fest — den Rest schreibt die Geschichte
            gemeinsam mit dir, Zug für Zug.
          </p>
          <div className="landing-cta-row">
            <Button icon={<ArrowRightIcon />} onClick={() => navigate("/new")}>
              Neue Geschichte beginnen
            </Button>
            <Button variant="ghost" icon={<BookIcon />} onClick={() => navigate("/library")}>
              Deine Geschichten
            </Button>
          </div>
        </div>
        <ImageSlot className="landing-hero-art" label="Platzhalter · Titelbild folgt" />
      </div>

      <div className="landing-genres">
        <div className="landing-section-label">Fünf Welten, ein Werkzeug</div>
        <div className="landing-genre-row">
          {GENRES.map(({ label, Icon }) => (
            <div className="landing-genre-card" key={label}>
              <Icon />
              <span>{label}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="landing-how">
        <div className="landing-section-label">So funktioniert's</div>
        <div className="landing-steps">
          {STEPS.map((step, index) => (
            <div className="landing-step" key={step.title}>
              <div className="landing-step-num">{index + 1}</div>
              <h3>{step.title}</h3>
              <p>{step.text}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="landing-foot">„Manche Geschichten warten nur darauf, begonnen zu werden.“</div>
    </div>
  );
}
