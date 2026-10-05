import { configureStore } from "@reduxjs/toolkit";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
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
  beforeEach(() => {
    vi.spyOn(auth, "checkSession").mockResolvedValue(true);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the Landing page at / without forcing a login", () => {
    vi.spyOn(auth, "checkSession").mockResolvedValue(false);
    const ensureAuthSpy = vi.spyOn(auth, "ensureAuth");
    renderAt("/");

    expect(
      screen.getByRole("heading", { name: "Geschichten, die deinen Entscheidungen folgen." }),
    ).toBeInTheDocument();
    expect(ensureAuthSpy).not.toHaveBeenCalled();
  });

  it("offers sign-in to anonymous visitors and starts the Keycloak login on click", async () => {
    vi.spyOn(auth, "checkSession").mockResolvedValue(false);
    const ensureAuthSpy = vi.spyOn(auth, "ensureAuth").mockResolvedValue(undefined);
    renderAt("/");

    await userEvent.click(await screen.findByRole("button", { name: "Anmelden" }));

    expect(ensureAuthSpy).toHaveBeenCalledOnce();
    expect(screen.queryByRole("button", { name: "Menü" })).not.toBeInTheDocument();
  });

  it("shows menu and sign-out instead of sign-in when a session exists", async () => {
    vi.spyOn(auth, "checkSession").mockResolvedValue(true);
    vi.spyOn(auth, "currentUsername").mockReturnValue("TestAdmin");
    vi.spyOn(auth, "isAdmin").mockReturnValue(false);
    const logoutSpy = vi.spyOn(auth, "logout").mockImplementation(() => {});
    renderAt("/");

    await userEvent.click(await screen.findByRole("button", { name: "Menü" }));

    expect(screen.queryByRole("button", { name: "Anmelden" })).not.toBeInTheDocument();
    expect(screen.getByText("TestAdmin")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Deine Geschichten" })).toHaveAttribute("href", "/library");
    expect(screen.getByRole("link", { name: "Neue Geschichte" })).toHaveAttribute("href", "/new");
    expect(screen.queryByRole("link", { name: "Einstellungen" })).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Abmelden" }));
    expect(logoutSpy).toHaveBeenCalledOnce();
  });

  it("lists the settings in the menu for an admin and closes the menu on Escape", async () => {
    vi.spyOn(auth, "checkSession").mockResolvedValue(true);
    vi.spyOn(auth, "isAdmin").mockReturnValue(true);
    renderAt("/");

    await userEvent.click(await screen.findByRole("button", { name: "Menü" }));
    expect(screen.getByRole("link", { name: "Einstellungen" })).toHaveAttribute("href", "/settings");

    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("link", { name: "Einstellungen" })).not.toBeInTheDocument();
  });

  it("treats a failing session check as anonymous", async () => {
    vi.spyOn(auth, "checkSession").mockRejectedValue(new Error("keycloak unreachable"));
    renderAt("/");

    expect(await screen.findByRole("button", { name: "Anmelden" })).toBeInTheDocument();
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

    expect(await screen.findByRole("heading", { name: "Welt" })).toBeInTheDocument();
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
        story: { turns: [], summaries: [], current_turn_sequence: 0, initialization: null },
      },
    });

    renderAt("/stories/11111111-1111-1111-1111-111111111111");

    expect(
      await screen.findByRole("heading", { name: "Die Schatten von Auenfall" }),
    ).toBeInTheDocument();
  });

  it("renders the settings at /settings for an admin", async () => {
    vi.spyOn(auth, "ensureAuth").mockResolvedValue(undefined);
    vi.spyOn(auth, "isAdmin").mockReturnValue(true);
    vi.spyOn(client, "listAdminPrompts").mockResolvedValue({
      package_id: "story.base",
      package_version: "1",
      entries: [],
    });

    renderAt("/settings");

    expect(await screen.findByRole("heading", { name: "Einstellungen" })).toBeInTheDocument();
  });

  it("refuses /settings to a user without the admin role", async () => {
    vi.spyOn(auth, "ensureAuth").mockResolvedValue(undefined);
    vi.spyOn(auth, "isAdmin").mockReturnValue(false);

    renderAt("/settings");

    expect(await screen.findByText("Dafür fehlt dir die Berechtigung.")).toBeInTheDocument();
  });
});
