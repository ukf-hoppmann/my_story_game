import { configureStore } from "@reduxjs/toolkit";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { apiSlice } from "../../api/apiSlice";
import * as client from "../../api/client";
import type { GameDocument, PromptProfileCatalog, RunProposal } from "../../api/types";
import wizardReducer from "../../features/wizard/wizardSlice";
import { Wizard } from "./Wizard";

function buildStore() {
  return configureStore({
    reducer: { [apiSlice.reducerPath]: apiSlice.reducer, wizard: wizardReducer },
    middleware: (getDefaultMiddleware) => getDefaultMiddleware().concat(apiSlice.middleware),
  });
}

function renderWizard() {
  const router = createMemoryRouter(
    [
      { path: "/new", element: <Wizard /> },
      { path: "/stories/:runId", element: <div>Play-Route</div> },
    ],
    { initialEntries: ["/new"] },
  );
  render(
    <Provider store={buildStore()}>
      <RouterProvider router={router} />
    </Provider>,
  );
}

function option(id: string, description = id) {
  return { id, description };
}

const catalog: PromptProfileCatalog = {
  package_id: "story.base",
  package_version: "1",
  categories: [
    { id: "genre", default_option_id: "dark_fantasy", options: [option("dark_fantasy"), option("science_fiction")] },
    { id: "tone", default_option_id: "balanced", options: [option("balanced"), option("dark")] },
    { id: "prose_style", default_option_id: "balanced", options: [option("balanced")] },
    { id: "perspective", default_option_id: "third_person_limited", options: [option("third_person_limited")] },
    { id: "pacing", default_option_id: "balanced", options: [option("balanced")] },
    { id: "length", default_option_id: "standard", options: [option("standard")] },
    { id: "player_agency", default_option_id: "strict", options: [option("strict")] },
    { id: "consequence", default_option_id: "balanced", options: [option("balanced")] },
    { id: "challenge", default_option_id: "balanced", options: [option("balanced")] },
    { id: "content_profile", default_option_id: "teen", options: [option("teen")] },
  ],
};

const proposal: RunProposal = {
  proposal_id: "33333333-3333-3333-3333-333333333333",
  opening_narration: "Der Regen hatte die Spuren fast fortgespült.",
  suggested_title: "Die Schatten von Auenfall",
  suggested_player_entity_ids: ["char-1"],
  world: {
    entities: [
      { id: "char-1", kind: "character", label: "Elian", description: "", actor: null, conditions: [], aliases: [] },
      { id: "item-1", kind: "item", label: "Laterne", description: "", actor: null, conditions: [], aliases: [] },
    ],
    links: [],
    facts: [],
    knowledge: [],
    rules: [],
    goals: [],
    scene_location_ids: [],
  },
};

const activeDocument: GameDocument = {
  schema_version: 1,
  game_run: {
    id: "44444444-4444-4444-4444-444444444444",
    name: "Die Schatten von Auenfall",
    status: "active",
    current_revision: 1,
    members: [],
    created_at: "2026-09-10T00:00:00Z",
    updated_at: "2026-09-10T00:00:00Z",
  },
  game_state: {
    run_id: "44444444-4444-4444-4444-444444444444",
    revision: 1,
    configuration: {},
    world: { entities: [], links: [], facts: [], knowledge: [], rules: [], goals: [], scene_location_ids: [] },
    story: { turns: [], summary: null, current_turn_sequence: 0, initialization: null },
  },
};

async function fillWeltStep(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText("Prämisse"), "Ein Kurier verschwindet spurlos.");
  await user.click(screen.getByRole("button", { name: /Weiter/ }));
}

async function fillFigurStep(user: ReturnType<typeof userEvent.setup>) {
  await user.type(await screen.findByLabelText("Name"), "Elian");
  await user.click(screen.getByRole("button", { name: /Weiter/ }));
}

describe("Wizard", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows an error when the catalog fails to load", async () => {
    vi.spyOn(client, "fetchPromptProfileCatalog").mockRejectedValue(new Error("network down"));
    renderWizard();

    expect(
      await screen.findByText("Optionen konnten nicht geladen werden. Bitte versuche es erneut."),
    ).toBeInTheDocument();
  });

  it("preselects catalog defaults and lets the user change genre/tone", async () => {
    vi.spyOn(client, "fetchPromptProfileCatalog").mockResolvedValue(catalog);
    renderWizard();

    const darkFantasy = await screen.findByRole("button", { name: "Dark Fantasy" });
    expect(darkFantasy).toHaveAttribute("aria-pressed", "true");

    await userEvent.click(screen.getByRole("button", { name: "Science Fiction" }));

    expect(screen.getByRole("button", { name: "Science Fiction" })).toHaveAttribute("aria-pressed", "true");
    expect(darkFantasy).toHaveAttribute("aria-pressed", "false");
  });

  it("keeps 'Weiter' disabled on the Welt step until a premise is entered", async () => {
    vi.spyOn(client, "fetchPromptProfileCatalog").mockResolvedValue(catalog);
    renderWizard();
    await screen.findByRole("button", { name: "Dark Fantasy" });

    expect(screen.getByRole("button", { name: /Weiter/ })).toBeDisabled();

    await userEvent.type(screen.getByLabelText("Prämisse"), "Ein Kurier verschwindet.");

    expect(screen.getByRole("button", { name: /Weiter/ })).toBeEnabled();
  });

  it("updates the premise character counter as the user types", async () => {
    vi.spyOn(client, "fetchPromptProfileCatalog").mockResolvedValue(catalog);
    renderWizard();
    await screen.findByRole("button", { name: "Dark Fantasy" });

    await userEvent.type(screen.getByLabelText("Prämisse"), "Ein Kurier verschwindet spurlos.");

    expect(screen.getByText("32 / 500")).toBeInTheDocument();
  });

  it("walks through Welt -> Figur -> Stil -> Vorschlag -> Geschichte beginnen and navigates to the new run", async () => {
    vi.spyOn(client, "fetchPromptProfileCatalog").mockResolvedValue(catalog);
    vi.spyOn(client, "proposeRun").mockResolvedValue(proposal);
    vi.spyOn(client, "confirmRun").mockResolvedValue({ ...activeDocument, game_run: { ...activeDocument.game_run, status: "draft" } });
    vi.spyOn(client, "startPlaythrough").mockResolvedValue(activeDocument);

    const user = userEvent.setup();
    renderWizard();
    await screen.findByRole("button", { name: "Dark Fantasy" });

    await fillWeltStep(user);
    expect(await screen.findByRole("heading", { name: "Deine Figur" })).toBeInTheDocument();

    await fillFigurStep(user);
    expect(await screen.findByRole("heading", { name: "Erzählstil" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Vorschlag erstellen" }));

    expect(await screen.findByRole("heading", { name: "Geschichte bestätigen" })).toBeInTheDocument();
    expect(screen.getByText("Der Regen hatte die Spuren fast fortgespült.")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Die Schatten von Auenfall")).toBeInTheDocument();
    expect(screen.getByText("Elian")).toBeInTheDocument();
    expect(screen.getByText("Laterne")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Geschichte beginnen" }));

    expect(await screen.findByText("Play-Route")).toBeInTheDocument();
  });

  it("shows an error and stays on Stil when creating the proposal fails", async () => {
    vi.spyOn(client, "fetchPromptProfileCatalog").mockResolvedValue(catalog);
    vi.spyOn(client, "proposeRun").mockRejectedValue(new Error("boom"));

    const user = userEvent.setup();
    renderWizard();
    await screen.findByRole("button", { name: "Dark Fantasy" });
    await fillWeltStep(user);
    await fillFigurStep(user);

    await user.click(screen.getByRole("button", { name: "Vorschlag erstellen" }));

    expect(
      await screen.findByText("Der Vorschlag konnte nicht erstellt werden. Bitte versuche es erneut."),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Erzählstil" })).toBeInTheDocument();
  });

  it("shows an error when confirming/starting the run fails", async () => {
    vi.spyOn(client, "fetchPromptProfileCatalog").mockResolvedValue(catalog);
    vi.spyOn(client, "proposeRun").mockResolvedValue(proposal);
    vi.spyOn(client, "confirmRun").mockRejectedValue(new Error("boom"));

    const user = userEvent.setup();
    renderWizard();
    await screen.findByRole("button", { name: "Dark Fantasy" });
    await fillWeltStep(user);
    await fillFigurStep(user);
    await user.click(screen.getByRole("button", { name: "Vorschlag erstellen" }));
    await screen.findByRole("heading", { name: "Geschichte bestätigen" });

    await user.click(screen.getByRole("button", { name: "Geschichte beginnen" }));

    expect(
      await screen.findByText("Die Geschichte konnte nicht gestartet werden. Bitte versuche es erneut."),
    ).toBeInTheDocument();
  });
});
