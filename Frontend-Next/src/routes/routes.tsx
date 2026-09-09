import type { RouteObject } from "react-router-dom";
import { Landing } from "./Landing/Landing";
import { Library } from "./Library/Library";
import { PlaceholderScreen } from "./PlaceholderScreen";

/**
 * The route table, kept separate from `router.tsx` so tests can build a
 * `createMemoryRouter` from the exact same routes instead of duplicating
 * them. Placeholder screens are replaced as later roadmap steps land:
 *   "/new"             -> Story-Wizard (Schritt 7/8)
 *   "/stories/:runId" -> Play (Schritt 9/10)
 */
export const routes: RouteObject[] = [
  { path: "/", element: <Landing /> },
  { path: "/library", element: <Library /> },
  { path: "/new", element: <PlaceholderScreen text="Story-Wizard folgt in Schritt 7/8." /> },
  {
    path: "/stories/:runId",
    element: <PlaceholderScreen text="Play-Screen folgt in Schritt 9/10." />,
  },
];
