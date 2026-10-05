import type { RouteObject } from "react-router-dom";
import { RequireAdmin } from "../app/RequireAdmin";
import { RequireAuth } from "../app/RequireAuth";
import { AppShell } from "./AppShell/AppShell";
import { Landing } from "./Landing/Landing";
import { Library } from "./Library/Library";
import { Play } from "./Play/Play";
import { Settings } from "./Settings/Settings";
import { Wizard } from "./Wizard/Wizard";

/**
 * The route table, kept separate from `router.tsx` so tests can build a
 * `createMemoryRouter` from the exact same routes instead of duplicating
 * them.
 *
 * `AppShell` wraps every route so the app header (with its way back to
 * Landing) stays visible everywhere, including while `RequireAuth` is still
 * resolving.
 *
 * "/" (Landing) is intentionally outside `RequireAuth` — it must stay
 * reachable without a login redirect (Schritt 5b). Every other route is a
 * child of the `RequireAuth` layout route, so only entering one of them
 * triggers the Keycloak login-required flow. "/settings" additionally sits
 * behind `RequireAdmin` (the admin realm role).
 */
export const routes: RouteObject[] = [
  {
    element: <AppShell />,
    children: [
      { path: "/", element: <Landing /> },
      {
        element: <RequireAuth />,
        children: [
          { path: "/library", element: <Library /> },
          { path: "/new", element: <Wizard /> },
          { path: "/stories/:runId", element: <Play /> },
          {
            element: <RequireAdmin />,
            children: [{ path: "/settings", element: <Settings /> }],
          },
        ],
      },
    ],
  },
];
