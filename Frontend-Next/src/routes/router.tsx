import { createBrowserRouter } from "react-router-dom";

/**
 * Route scaffold (Schritt 0). Real screens (Landing, Bibliothek, Wizard, Play)
 * replace this placeholder as the roadmap steps are implemented — see
 * Schritt 5 in the plan for the intended route list:
 *   "/"               -> Landing
 *   "/library"        -> Bibliothek
 *   "/new"             -> Story-Wizard
 *   "/stories/:runId" -> Play
 */
export const router = createBrowserRouter([
  {
    path: "/",
    element: <div>Story Game — Grundgerüst steht.</div>,
  },
]);
