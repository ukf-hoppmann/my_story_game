import type { RouteObject } from "react-router-dom";
import { RequireAuth } from "../app/RequireAuth";
import { Landing } from "./Landing/Landing";
import { Library } from "./Library/Library";
import { Play } from "./Play/Play";
import { Wizard } from "./Wizard/Wizard";

/**
 * The route table, kept separate from `router.tsx` so tests can build a
 * `createMemoryRouter` from the exact same routes instead of duplicating
 * them.
 *
 * "/" (Landing) is intentionally outside `RequireAuth` — it must stay
 * reachable without a login redirect (Schritt 5b). Every other route is a
 * child of the `RequireAuth` layout route, so only entering one of them
 * triggers the Keycloak login-required flow.
 */
export const routes: RouteObject[] = [
  { path: "/", element: <Landing /> },
  {
    element: <RequireAuth />,
    children: [
      { path: "/library", element: <Library /> },
      { path: "/new", element: <Wizard /> },
      { path: "/stories/:runId", element: <Play /> },
    ],
  },
];
