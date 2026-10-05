import { configureStore } from "@reduxjs/toolkit";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { apiSlice } from "../../api/apiSlice";
import { ApiError } from "../../api/client";
import * as auth from "../../api/auth";
import * as client from "../../api/client";
import type { RunSummary } from "../../api/types";
import { Library } from "./Library";

function buildStore() {
  return configureStore({
    reducer: { [apiSlice.reducerPath]: apiSlice.reducer },
    middleware: (getDefaultMiddleware) => getDefaultMiddleware().concat(apiSlice.middleware),
  });
}

function renderLibrary() {
  const router = createMemoryRouter(
    [
      { path: "/library", element: <Library /> },
      { path: "/new", element: <div>Wizard-Route</div> },
      { path: "/stories/:runId", element: <div>Play-Route</div> },
    ],
    { initialEntries: ["/library"] },
  );
  render(
    <Provider store={buildStore()}>
      <RouterProvider router={router} />
    </Provider>,
  );
}

const draft: RunSummary = {
  id: "11111111-1111-1111-1111-111111111111",
  name: "Ein feuchter Anfang",
  status: "draft",
  current_revision: 1,
  game_role: "owner",
  updated_at: "2026-09-01T10:00:00Z",
};

const active: RunSummary = {
  id: "22222222-2222-2222-2222-222222222222",
  name: "Die Schatten von Auenfall",
  status: "active",
  current_revision: 12,
  game_role: "owner",
  updated_at: "2026-09-09T10:00:00Z",
};

describe("Library", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("groups runs into active and draft sections", async () => {
    vi.spyOn(client, "listRuns").mockResolvedValue({ runs: [draft, active] });
    renderLibrary();

    expect(await screen.findByText("Die Schatten von Auenfall")).toBeInTheDocument();
    expect(screen.getByText("Ein feuchter Anfang")).toBeInTheDocument();
    expect(screen.getByText("Aktiv")).toBeInTheDocument();
    expect(screen.getByText("Entwurf")).toBeInTheDocument();
  });

  it("shows an empty-state message per section when there is nothing to show", async () => {
    vi.spyOn(client, "listRuns").mockResolvedValue({ runs: [] });
    renderLibrary();

    expect(await screen.findByText("Noch keine aktive Geschichte — leg los!")).toBeInTheDocument();
    expect(screen.getByText("Keine offenen Entwürfe.")).toBeInTheDocument();
  });

  it("shows the backend's own message when the runs fail to load", async () => {
    vi.spyOn(client, "listRuns").mockRejectedValue(
      new ApiError(500, { error: "persistence_unavailable", detail: "Datenbank nicht erreichbar." }),
    );
    renderLibrary();

    expect(await screen.findByText("Fehler: Datenbank nicht erreichbar.")).toBeInTheDocument();
  });

  it("navigates to the run when a card is clicked", async () => {
    vi.spyOn(client, "listRuns").mockResolvedValue({ runs: [active] });
    renderLibrary();

    await userEvent.click(await screen.findByText("Die Schatten von Auenfall"));

    expect(await screen.findByText("Play-Route")).toBeInTheDocument();
  });

  it("navigates to the wizard when starting a new story", async () => {
    vi.spyOn(client, "listRuns").mockResolvedValue({ runs: [] });
    renderLibrary();

    await userEvent.click(await screen.findByRole("button", { name: /Neue Geschichte/ }));

    expect(await screen.findByText("Wizard-Route")).toBeInTheDocument();
  });

  it("offers the settings only to admins", async () => {
    vi.spyOn(client, "listRuns").mockResolvedValue({ runs: [] });
    vi.spyOn(auth, "isAdmin").mockReturnValue(true);
    renderLibrary();
    expect(await screen.findByRole("button", { name: "Einstellungen" })).toBeInTheDocument();
  });

  it("hides the settings from other users", async () => {
    vi.spyOn(client, "listRuns").mockResolvedValue({ runs: [] });
    vi.spyOn(auth, "isAdmin").mockReturnValue(false);

    renderLibrary();

    await screen.findByText("Noch keine aktive Geschichte — leg los!");
    expect(screen.queryByRole("button", { name: "Einstellungen" })).not.toBeInTheDocument();
  });
});
