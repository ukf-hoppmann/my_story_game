import type { RouteObject } from "react-router-dom";
import { Landing } from "./Landing/Landing";
import { Library } from "./Library/Library";
import { Play } from "./Play/Play";
import { Wizard } from "./Wizard/Wizard";

/**
 * The route table, kept separate from `router.tsx` so tests can build a
 * `createMemoryRouter` from the exact same routes instead of duplicating
 * them. The Play screen's sidebar (Ziele/Weltwissen/Figuren) is still a
 * placeholder note — it lands in Schritt 10.
 */
export const routes: RouteObject[] = [
  { path: "/", element: <Landing /> },
  { path: "/library", element: <Library /> },
  { path: "/new", element: <Wizard /> },
  { path: "/stories/:runId", element: <Play /> },
];
