import { configureStore } from "@reduxjs/toolkit";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { apiSlice } from "../../api/apiSlice";
import { ApiError } from "../../api/client";
import * as client from "../../api/client";
import type { GameDocument, WorldState } from "../../api/types";
import { Play } from "./Play";

function buildStore() {
  return configureStore({
    reducer: { [apiSlice.reducerPath]: apiSlice.reducer },
    middleware: (getDefaultMiddleware) => getDefaultMiddleware().concat(apiSlice.middleware),
  });
}

function renderPlay(runId = "11111111-1111-1111-1111-111111111111") {
  const router = createMemoryRouter(
    [
      { path: "/stories/:runId", element: <Play /> },
      { path: "/stories/:runId/other", element: <div>Other-Route</div> },
    ],
    { initialEntries: [`/stories/${runId}`] },
  );
  render(
    <Provider store={buildStore()}>
      <RouterProvider router={router} />
    </Provider>,
  );
}

const RUN_ID = "11111111-1111-1111-1111-111111111111";

function buildDocument(
  overrides: Partial<GameDocument["game_run"]> = {},
  world: Partial<WorldState> = {},
): GameDocument {
  return {
    schema_version: 1,
    game_run: {
      id: RUN_ID,
      name: "Die Schatten von Auenfall",
      status: "active",
      current_revision: 3,
      members: [],
      created_at: "2026-09-10T00:00:00Z",
      updated_at: "2026-09-10T00:00:00Z",
      ...overrides,
    },
    game_state: {
      run_id: RUN_ID,
      revision: 3,
      configuration: {},
      world: {
        entities: [],
        links: [],
        facts: [],
        knowledge: [],
        rules: [],
        goals: [],
        scene_location_ids: [],
        ...world,
      },
      story: {
        turns: [
          {
            id: "turn-1",
            sequence: 1,
            player_input: "Ich untersuche die Laterne.",
            narration: "Unter der Laterne glitzert ein silberner Faden.",
            based_on_revision: 2,
            resulting_revision: 3,
            completed_at: "2026-09-10T00:00:00Z",
          },
        ],
        summary: null,
        current_turn_sequence: 1,
        initialization: {
          prompt: "Ein Kurier verschwindet spurlos.",
          narration: "Der Regen hatte die Spuren fast fortgespült.",
          completed_at: "2026-09-09T00:00:00Z",
        },
      },
    },
  };
}

describe("Play", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows a loading state while the run is fetched", () => {
    vi.spyOn(client, "loadRun").mockReturnValue(new Promise(() => {}));
    renderPlay();

    expect(screen.getByText("Lade Geschichte …")).toBeInTheDocument();
  });

  it("shows an error banner when the run fails to load", async () => {
    vi.spyOn(client, "loadRun").mockRejectedValue(
      new ApiError(404, { error: "not_found", detail: "Nicht gefunden." }),
    );
    renderPlay();

    expect(await screen.findByText("Die Geschichte konnte nicht geladen werden.")).toBeInTheDocument();
  });

  it("shows the initialization narration and turn history for an active run", async () => {
    vi.spyOn(client, "loadRun").mockResolvedValue(buildDocument());
    renderPlay();

    expect(await screen.findByText("Der Regen hatte die Spuren fast fortgespült.")).toBeInTheDocument();
    expect(screen.getByText("Du: Ich untersuche die Laterne.")).toBeInTheDocument();
    expect(screen.getByText("Unter der Laterne glitzert ein silberner Faden.")).toBeInTheDocument();
    expect(screen.getByText("Zug 1")).toBeInTheDocument();
  });

  it("shows the sidebar panels once the run has loaded", async () => {
    vi.spyOn(client, "loadRun").mockResolvedValue(
      buildDocument(
        {},
        {
          goals: [
            {
              id: "goal-1",
              kind: "main",
              title: "Finde den verschwundenen Kurier",
              description: "Die Spur beginnt am Marktplatz.",
              status: "open",
              related_entity_ids: [],
            },
          ],
          facts: [
            {
              id: "fact-1",
              statement: "Das Nordtor wird bei Einbruch der Nacht verriegelt.",
              visibility: { scope: "public", actor_id: null },
              subject_id: null,
            },
          ],
          entities: [
            {
              id: "char-1",
              kind: "character",
              label: "Bran",
              description: "Wirkt besorgt, sagt aber wenig.",
              actor: { role: "npc" },
              conditions: [],
              aliases: [],
            },
          ],
        },
      ),
    );
    renderPlay();

    expect(await screen.findByText("Finde den verschwundenen Kurier")).toBeInTheDocument();
    expect(screen.getByText("Das Nordtor wird bei Einbruch der Nacht verriegelt.")).toBeInTheDocument();
    expect(screen.getByText("Bran")).toBeInTheDocument();
  });

  it("shows a draft banner with a start-playthrough CTA for a non-active run, navigating on success", async () => {
    vi.spyOn(client, "loadRun").mockResolvedValue(buildDocument({ status: "draft" }));
    vi.spyOn(client, "startPlaythrough").mockResolvedValue(
      buildDocument({ id: "22222222-2222-2222-2222-222222222222", status: "active" }),
    );
    renderPlay();

    await userEvent.click(await screen.findByRole("button", { name: "Spiel starten" }));

    expect(await screen.findByText("Die Schatten von Auenfall")).toBeInTheDocument();
  });

  it("submits a turn and clears the input on success", async () => {
    vi.spyOn(client, "loadRun").mockResolvedValue(buildDocument());
    vi.spyOn(client, "playTurn").mockResolvedValue({
      state: buildDocument().game_state,
      proposed_change_count: 1,
      summary_failed: false,
      summary_failure_message: null,
    });
    renderPlay();

    const input = await screen.findByPlaceholderText("Was tust du?");
    await userEvent.type(input, "Ich spreche mit Bran.");
    await userEvent.click(screen.getByRole("button", { name: /Handlung ausführen/ }));

    expect(client.playTurn).toHaveBeenCalledWith(RUN_ID, { player_input: "Ich spreche mit Bran." });
    expect(await screen.findByDisplayValue("")).toBeInTheDocument();
  });

  it("shows the run_not_active recovery message with a reload action", async () => {
    vi.spyOn(client, "loadRun").mockResolvedValue(buildDocument());
    vi.spyOn(client, "playTurn").mockRejectedValue(
      new ApiError(409, { error: "run_not_active", detail: "Nicht aktiv." }),
    );
    renderPlay();

    const input = await screen.findByPlaceholderText("Was tust du?");
    await userEvent.type(input, "Ich warte.");
    await userEvent.click(screen.getByRole("button", { name: /Handlung ausführen/ }));

    expect(
      await screen.findByText("Diese Geschichte läuft nicht mehr. Lade sie neu, um den aktuellen Stand zu sehen."),
    ).toBeInTheDocument();
  });

  it("shows the revision_conflict recovery message", async () => {
    vi.spyOn(client, "loadRun").mockResolvedValue(buildDocument());
    vi.spyOn(client, "playTurn").mockRejectedValue(
      new ApiError(409, { error: "revision_conflict", detail: "Konflikt." }),
    );
    renderPlay();

    const input = await screen.findByPlaceholderText("Was tust du?");
    await userEvent.type(input, "Ich warte.");
    await userEvent.click(screen.getByRole("button", { name: /Handlung ausführen/ }));

    expect(
      await screen.findByText("Es gab zwischenzeitlich eine neue Aktualisierung. Lade die Geschichte neu."),
    ).toBeInTheDocument();
  });
});
