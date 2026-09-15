import { configureStore } from "@reduxjs/toolkit";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { apiSlice } from "../../api/apiSlice";
import * as client from "../../api/client";
import { ApiError } from "../../api/client";
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
    {
      id: "prose_style",
      default_option_id: "balanced",
      options: [option("balanced"), option("concise"), option("descriptive"), option("dialogue_driven")],
    },
    { id: "perspective", default_option_id: "third_person_limited", options: [option("third_person_limited")] },
    { id: "pacing", default_option_id: "balanced", options: [option("balanced"), option("slow"), option("fast")] },
    { id: "length", default_option_id: "standard", options: [option("short"), option("standard"), option("long")] },
    { id: "player_agency", default_option_id: "strict", options: [option("strict")] },
    {
      id: "consequence",
      default_option_id: "balanced",
      options: [option("balanced"), option("forgiving"), option("harsh")],
    },
    {
      id: "challenge",
      default_option_id: "balanced",
      options: [option("balanced"), option("narrative"), option("demanding")],
    },
    { id: "content_profile", default_option_id: "teen", options: [option("teen")] },
  ],
};

const proposal: RunProposal = {
  proposal_id: "33333333-3333-3333-3333-333333333333",
  opening_narration:
    "Der Regen hatte die Spuren fast fortgespült.\n\nElian betrat das Gasthaus und sah sich um.",
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

/** Same shape as `proposal`, but nobody is suggested as the player — used
 *  to test the "choose a player character" gate on the review step. */
const proposalWithoutSuggestedPlayer: RunProposal = {
  ...proposal,
  suggested_player_entity_ids: [],
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
    story: { turns: [], summaries: [], current_turn_sequence: 0, initialization: null },
  },
};

async function fillWeltStep(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole("button", { name: "Weiter" }));
}

/** Defaults to naming a character, since player mode (the wizard's default)
 *  requires one to proceed — pass `null` to explicitly leave it blank when
 *  a test is about that behavior itself. */
async function fillFigurStep(
  user: ReturnType<typeof userEvent.setup>,
  characterName: string | null = "Elian",
) {
  await user.type(await screen.findByLabelText("Prämisse"), "Ein Kurier verschwindet spurlos.");
  if (characterName) {
    await user.type(screen.getByLabelText("Name"), characterName);
  }
  await user.click(screen.getByRole("button", { name: "Weiter" }));
}

describe("Wizard", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows the generic tooling-error message when the catalog fails to load for a non-backend reason", async () => {
    vi.spyOn(client, "fetchPromptProfileCatalog").mockRejectedValue(new Error("network down"));
    vi.spyOn(client, "reportFrontendError").mockResolvedValue(undefined);
    renderWizard();

    expect(
      await screen.findByText(
        "Ein technischer Fehler ist aufgetreten und wurde protokolliert. Bitte versuche es erneut.",
      ),
    ).toBeInTheDocument();
    expect(client.reportFrontendError).toHaveBeenCalled();
  });

  it("shows the backend's own message when the catalog fails to load with a typed API error", async () => {
    vi.spyOn(client, "fetchPromptProfileCatalog").mockRejectedValue(
      new ApiError(500, { error: "prompt_package_configuration_invalid", detail: "Katalog defekt." }),
    );
    renderWizard();

    expect(await screen.findByText("Fehler: Katalog defekt.")).toBeInTheDocument();
  });

  it("Welt: preselects catalog defaults and lets the user change genre/tone, no title/premise fields", async () => {
    vi.spyOn(client, "fetchPromptProfileCatalog").mockResolvedValue(catalog);
    renderWizard();

    const darkFantasy = await screen.findByRole("button", { name: "Dark Fantasy" });
    expect(darkFantasy).toHaveAttribute("aria-pressed", "true");
    expect(screen.queryByLabelText("Titel")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Prämisse")).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Science Fiction" }));

    expect(screen.getByRole("button", { name: "Science Fiction" })).toHaveAttribute("aria-pressed", "true");
    expect(darkFantasy).toHaveAttribute("aria-pressed", "false");
  });

  it("Welt: shows Inhaltsprofil and Erzählperspektive, and 'Weiter' is always enabled", async () => {
    vi.spyOn(client, "fetchPromptProfileCatalog").mockResolvedValue(catalog);
    renderWizard();
    await screen.findByRole("button", { name: "Dark Fantasy" });

    expect(screen.getByText("Inhaltsprofil")).toBeInTheDocument();
    expect(screen.getByText("Erzählperspektive")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Weiter" })).toBeEnabled();
  });

  it("Figur: shows Prämisse and Handlungsfreiheit; in Regie mode 'Weiter' requires only the premise", async () => {
    vi.spyOn(client, "fetchPromptProfileCatalog").mockResolvedValue(catalog);
    const user = userEvent.setup();
    renderWizard();
    await screen.findByRole("button", { name: "Dark Fantasy" });
    await fillWeltStep(user);

    expect(await screen.findByRole("heading", { name: "Figur & Prämisse" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Weiter" })).toBeDisabled();

    await user.click(screen.getByRole("button", { name: "Regie" }));
    await user.type(screen.getByLabelText("Prämisse"), "Ein Kurier verschwindet spurlos.");

    expect(screen.getByText("32 / 500")).toBeInTheDocument();
    expect(screen.getByText("Handlungsfreiheit")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Weiter" })).toBeEnabled();
  });

  it("Figur: Ich-Charakter (player mode) requires a character name to proceed", async () => {
    // The backend requires exactly one user-named character for player
    // mode — it does not invent one from the premise alone (confirmed via
    // live testing: propose fails with invalid_player_character_seed).
    vi.spyOn(client, "fetchPromptProfileCatalog").mockResolvedValue(catalog);
    const user = userEvent.setup();
    renderWizard();
    await screen.findByRole("button", { name: "Dark Fantasy" });
    await fillWeltStep(user);
    await user.type(await screen.findByLabelText("Prämisse"), "Ein Kurier verschwindet spurlos.");

    expect(screen.getByRole("button", { name: "Weiter" })).toBeDisabled();

    await user.type(screen.getByLabelText("Name"), "Elian");

    expect(screen.getByRole("button", { name: "Weiter" })).toBeEnabled();
  });

  it("Figur: Regie (director mode) proceeds without a character name", async () => {
    vi.spyOn(client, "fetchPromptProfileCatalog").mockResolvedValue(catalog);
    const user = userEvent.setup();
    renderWizard();
    await screen.findByRole("button", { name: "Dark Fantasy" });
    await fillWeltStep(user);
    await user.click(screen.getByRole("button", { name: "Regie" }));
    await fillFigurStep(user, null);

    expect(await screen.findByRole("heading", { name: "Erzählstil" })).toBeInTheDocument();
  });

  it("Stil: shows preset cards, 'Ausgewogen' selected by default, custom section starts collapsed", async () => {
    vi.spyOn(client, "fetchPromptProfileCatalog").mockResolvedValue(catalog);
    const user = userEvent.setup();
    renderWizard();
    await screen.findByRole("button", { name: "Dark Fantasy" });
    await fillWeltStep(user);
    await fillFigurStep(user);

    expect(screen.getByRole("button", { name: /Ausgewogen/ })).toHaveClass("wizard-preset-card--selected");
    expect(screen.queryByText("Prosastil")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Eigene Kombination wählen" }));

    expect(screen.getByText("Prosastil")).toBeInTheDocument();
  });

  it("Stil: picking a preset sets all five underlying fields", async () => {
    vi.spyOn(client, "fetchPromptProfileCatalog").mockResolvedValue(catalog);
    const user = userEvent.setup();
    renderWizard();
    await screen.findByRole("button", { name: "Dark Fantasy" });
    await fillWeltStep(user);
    await fillFigurStep(user);

    await user.click(screen.getByRole("button", { name: /Schnell & Intensiv/ }));
    await user.click(screen.getByRole("button", { name: "Eigene Kombination wählen" }));

    expect(screen.getByRole("button", { name: "Concise" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Fast" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Short" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Harsh" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Demanding" })).toHaveAttribute("aria-pressed", "true");
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
    expect(await screen.findByRole("heading", { name: "Figur & Prämisse" })).toBeInTheDocument();

    await fillFigurStep(user, "Elian");
    expect(await screen.findByRole("heading", { name: "Erzählstil" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Vorschlag erstellen" }));

    expect(await screen.findByRole("heading", { name: "Geschichte bestätigen" })).toBeInTheDocument();
    // Regression: submitting without touching any Stil options must still
    // send the catalog's defaults, not empty strings (the backend rejects
    // those with a 422 string_too_short per field).
    expect(client.proposeRun).toHaveBeenCalledWith(
      expect.objectContaining({
        prompt_profile: {
          genre: "dark_fantasy",
          tone: "balanced",
          prose_style: "balanced",
          perspective: "third_person_limited",
          pacing: "balanced",
          length: "standard",
          player_agency: "strict",
          consequence: "balanced",
          challenge: "balanced",
          content_profile: "teen",
        },
      }),
    );
    // Opening narration renders as real paragraphs, not one text block.
    expect(screen.getByText("Der Regen hatte die Spuren fast fortgespült.")).toBeInTheDocument();
    expect(screen.getByText("Elian betrat das Gasthaus und sah sich um.")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Die Schatten von Auenfall")).toBeInTheDocument();
    expect(screen.getAllByText("Elian").length).toBeGreaterThan(0);
    expect(screen.getByText("Laterne")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Geschichte beginnen" }));

    expect(await screen.findByText("Play-Route")).toBeInTheDocument();
  });

  it("Bestätigen: disables 'Geschichte beginnen' until a character is marked as player", async () => {
    vi.spyOn(client, "fetchPromptProfileCatalog").mockResolvedValue(catalog);
    vi.spyOn(client, "proposeRun").mockResolvedValue(proposalWithoutSuggestedPlayer);

    const user = userEvent.setup();
    renderWizard();
    await screen.findByRole("button", { name: "Dark Fantasy" });
    await fillWeltStep(user);
    await fillFigurStep(user);
    await user.click(screen.getByRole("button", { name: "Vorschlag erstellen" }));
    await screen.findByRole("heading", { name: "Geschichte bestätigen" });

    expect(screen.getByText("Wähle eine Figur als Spieler, bevor du beginnst.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Geschichte beginnen" })).toBeDisabled();

    await user.click(screen.getByRole("button", { name: "Spieler" }));

    expect(screen.queryByText("Wähle eine Figur als Spieler, bevor du beginnst.")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Geschichte beginnen" })).toBeEnabled();
  });

  it("shows the tooling-error message and stays on Stil when creating the proposal fails for a non-backend reason", async () => {
    vi.spyOn(client, "fetchPromptProfileCatalog").mockResolvedValue(catalog);
    vi.spyOn(client, "proposeRun").mockRejectedValue(new Error("boom"));
    vi.spyOn(client, "reportFrontendError").mockResolvedValue(undefined);

    const user = userEvent.setup();
    renderWizard();
    await screen.findByRole("button", { name: "Dark Fantasy" });
    await fillWeltStep(user);
    await fillFigurStep(user);

    await user.click(screen.getByRole("button", { name: "Vorschlag erstellen" }));

    expect(
      await screen.findByText(
        "Ein technischer Fehler ist aufgetreten und wurde protokolliert. Bitte versuche es erneut.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Erzählstil" })).toBeInTheDocument();
  });

  it("shows the backend's own message when confirming/starting the run fails with a typed API error", async () => {
    vi.spyOn(client, "fetchPromptProfileCatalog").mockResolvedValue(catalog);
    vi.spyOn(client, "proposeRun").mockResolvedValue(proposal);
    vi.spyOn(client, "confirmRun").mockRejectedValue(
      new ApiError(422, { error: "domain_validation_failed", detail: "Ungültige Auswahl." }),
    );

    const user = userEvent.setup();
    renderWizard();
    await screen.findByRole("button", { name: "Dark Fantasy" });
    await fillWeltStep(user);
    await fillFigurStep(user);
    await user.click(screen.getByRole("button", { name: "Vorschlag erstellen" }));
    await screen.findByRole("heading", { name: "Geschichte bestätigen" });

    await user.click(screen.getByRole("button", { name: "Geschichte beginnen" }));

    expect(await screen.findByText("Fehler: Ungültige Auswahl.")).toBeInTheDocument();
  });

  it("shows the session-expired message with a re-login action on a 401", async () => {
    vi.spyOn(client, "fetchPromptProfileCatalog").mockResolvedValue(catalog);
    vi.spyOn(client, "proposeRun").mockResolvedValue(proposal);
    vi.spyOn(client, "confirmRun").mockRejectedValue(
      new ApiError(401, { error: "unauthorized", detail: "Token abgelaufen." }),
    );

    const user = userEvent.setup();
    renderWizard();
    await screen.findByRole("button", { name: "Dark Fantasy" });
    await fillWeltStep(user);
    await fillFigurStep(user);
    await user.click(screen.getByRole("button", { name: "Vorschlag erstellen" }));
    await screen.findByRole("heading", { name: "Geschichte bestätigen" });

    await user.click(screen.getByRole("button", { name: "Geschichte beginnen" }));

    expect(
      await screen.findByText("Du wurdest ausgeloggt, bitte melde dich erneut an."),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Neu anmelden" })).toBeInTheDocument();
  });
});
