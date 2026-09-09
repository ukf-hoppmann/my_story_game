import type { RouteObject } from "react-router-dom";
import { Landing } from "./Landing/Landing";
import { Library } from "./Library/Library";
import { PlaceholderScreen } from "./PlaceholderScreen";
import { Wizard } from "./Wizard/Wizard";

/**
 * The route table, kept separate from `router.tsx` so tests can build a
 * `createMemoryRouter` from the exact same routes instead of duplicating
 * them. Placeholder screens are replaced as later roadmap steps land:
 *   "/stories/:runId" -> Play (Schritt 9/10)
 * "/new" currently only covers Wizard-Schritt 1 (Welt & Prämisse) — Schritte
 * 2/3 (Figur/Stil) and the submit flow land in Schritt 8.
 */
export const routes: RouteObject[] = [
  { path: "/", element: <Landing /> },
  { path: "/library", element: <Library /> },
  { path: "/new", element: <Wizard /> },
  {
    path: "/stories/:runId",
    element: <PlaceholderScreen text="Play-Screen folgt in Schritt 9/10." />,
  },
];
