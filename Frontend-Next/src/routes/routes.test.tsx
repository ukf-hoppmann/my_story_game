import { configureStore } from "@reduxjs/toolkit";
import { render, screen } from "@testing-library/react";
import { Provider } from "react-redux";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { apiSlice } from "../api/apiSlice";
import * as auth from "../api/auth";
import * as client from "../api/client";
import wizardReducer from "../features/wizard/wizardSlice";
import { routes } from "./routes";

function buildStore() {
  return configureStore({
    reducer: { [apiSlice.reducerPath]: apiSlice.reducer, wizard: wizardReducer },
    middleware: (getDefaultMiddleware) => getDefaultMiddleware().concat(apiSlice.middleware),
  });
}

function renderAt(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  render(
    <Provider store={buildStore()}>
      <RouterProvider router={router} />
    </Provider>,
  );
}

describe("routes", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the Landing page at / without triggering auth", () => {
    const ensureAuthSpy = vi.spyOn(auth, "ensureAuth");
    renderAt("/");

    expect(
      screen.getByRole("heading", { name: "Geschichten, die deinen Entscheidungen folgen." }),
    ).toBeInTheDocument();
    expect(ensureAuthSpy).not.toHaveBeenCalled();
  });

  it("renders the Bibliothek at /library once auth resolves", async () => {
    vi.spyOn(auth, "ensureAuth").mockResolvedValue(undefined);
    vi.spyOn(client, "listRuns").mockResolvedValue({ runs: [] });

    renderAt("/library");

    expect(await screen.findByRole("heading", { name: "Deine Geschichten" })).toBeInTheDocument();
  });

  it("renders the Wizard at /new once auth resolves", async () => {
    vi.spyOn(auth, "ensureAuth").mockResolvedValue(undefined);
    vi.spyOn(client, "fetchPromptProfileCatalog").mockResolvedValue({
      package_id: "story.base",
      package_version: "1",
      categories: [],
    });

    renderAt("/new");

    expect(await screen.findByRole("heading", { name: "Welt & Prämisse" })).toBeInTheDocument();
  });

  it("renders the Play screen at /stories/:runId once auth resolves", async () => {
    vi.spyOn(auth, "ensureAuth").mockResolvedValue(undefined);
    vi.spyOn(client, "loadRun").mockResolvedValue({
      schema_version: 1,
      game_run: {
        id: "11111111-1111-1111-1111-111111111111",
        name: "Die Schatten von Auenfall",
        status: "active",
        current_revision: 1,
        members: [],
        created_at: "2026-09-10T00:00:00Z",
        updated_at: "2026-09-10T00:00:00Z",
      },
      game_state: {
        run_id: "11111111-1111-1111-1111-111111111111",
        revision: 1,
        configuration: {},
        world: { entities: [], links: [], facts: [], knowledge: [], rules: [], goals: [], scene_location_ids: [] },
        story: { turns: [], summary: null, current_turn_sequence: 0, initialization: null },
      },
    });

    renderAt("/stories/11111111-1111-1111-1111-111111111111");

    expect(
      await screen.findByRole("heading", { name: "Die Schatten von Auenfall" }),
    ).toBeInTheDocument();
  });
});
