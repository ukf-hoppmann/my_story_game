import { configureStore } from "@reduxjs/toolkit";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { apiSlice } from "../../api/apiSlice";
import { ApiError } from "../../api/client";
import * as client from "../../api/client";
import type { GameDocument, SceneImageCapabilities, WorldState } from "../../api/types";
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

const CAPABILITIES_DISABLED: SceneImageCapabilities = {
  enabled: false,
  models: [],
  refine_models: [],
  model_listing_failed: false,
  default_model: null,
  default_refine: false,
  default_refine_model: null,
  default_refine_strength: null,
  min_refine_strength: null,
  max_refine_strength: null,
  turn_window: null,
};

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
        summaries: [],
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
  beforeEach(() => {
    localStorage.clear();
    // The scene-image controls ask the backend whether the feature is on;
    // every test here runs with it off unless it says otherwise.
    vi.spyOn(client, "fetchSceneImageCapabilities").mockResolvedValue(CAPABILITIES_DISABLED);
    vi.spyOn(client, "fetchWorldTrackingStatus").mockResolvedValue({ enabled: true });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows a loading state while the run is fetched", () => {
    vi.spyOn(client, "loadRun").mockReturnValue(new Promise(() => {}));
    renderPlay();

    expect(screen.getByText("Lade Geschichte …")).toBeInTheDocument();
  });

  it("shows the backend's own message in the error banner when the run fails to load", async () => {
    vi.spyOn(client, "loadRun").mockRejectedValue(
      new ApiError(404, { error: "not_found", detail: "Nicht gefunden." }),
    );
    renderPlay();

    expect(await screen.findByText("Fehler: Nicht gefunden.")).toBeInTheDocument();
  });

  it("shows the initialization narration and turn history for an active run", async () => {
    vi.spyOn(client, "loadRun").mockResolvedValue(buildDocument());
    renderPlay();

    expect(await screen.findByText("Der Regen hatte die Spuren fast fortgespült.")).toBeInTheDocument();
    expect(screen.getByText("Du: Ich untersuche die Laterne.")).toBeInTheDocument();
    expect(screen.getByText("Unter der Laterne glitzert ein silberner Faden.")).toBeInTheDocument();
    expect(screen.getByText("Zug 1")).toBeInTheDocument();
  });

  it("tells the player when world tracking is switched off", async () => {
    vi.spyOn(client, "fetchWorldTrackingStatus").mockResolvedValue({ enabled: false });
    vi.spyOn(client, "loadRun").mockResolvedValue(buildDocument());
    renderPlay();

    expect(await screen.findByText(/Welt-Tracking ist deaktiviert/)).toBeInTheDocument();
  });

  it("shows no world-tracking notice while tracking is on", async () => {
    vi.spyOn(client, "loadRun").mockResolvedValue(buildDocument());
    renderPlay();

    await screen.findByText("Der Regen hatte die Spuren fast fortgespült.");
    expect(screen.queryByText(/Welt-Tracking ist deaktiviert/)).not.toBeInTheDocument();
  });

  it("opens the world view from the rail in place of story and sidebar", async () => {
    vi.spyOn(client, "loadRun").mockResolvedValue(
      buildDocument(
        {},
        {
          entities: [
            {
              id: "char-1",
              kind: "character",
              label: "Bran",
              description: "Wirkt besorgt.",
              actor: { role: "npc" },
              conditions: [],
              aliases: [],
            },
          ],
        },
      ),
    );
    renderPlay();
    await screen.findByText("Der Regen hatte die Spuren fast fortgespült.");

    await userEvent.click(screen.getByRole("button", { name: "Welt" }));

    expect(screen.getByRole("heading", { level: 2, name: "Bran" })).toBeInTheDocument();
    expect(screen.queryByText("Der Regen hatte die Spuren fast fortgespült.")).not.toBeInTheDocument();
    expect(screen.queryByText("Noch keine Ziele bekannt.")).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Geschichte" }));
    expect(screen.getByText("Der Regen hatte die Spuren fast fortgespült.")).toBeInTheDocument();
  });

  it("shows a scene-art placeholder above the story feed for an active run", async () => {
    vi.spyOn(client, "loadRun").mockResolvedValue(buildDocument());
    renderPlay();

    expect(await screen.findByText("Platzhalter · Szenenbild folgt")).toBeInTheDocument();
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });

  it("renders every summary segment in order under the Chronik tab, not just the last one", async () => {
    const document = buildDocument();
    document.game_state.story.summaries = [
      { from_sequence: 1, through_sequence: 1, text: "Erster Absatz der Chronik.", based_on_revision: 2 },
      { from_sequence: 2, through_sequence: 2, text: "Zweiter Absatz der Chronik.", based_on_revision: 3 },
    ];
    vi.spyOn(client, "loadRun").mockResolvedValue(document);
    renderPlay();
    await screen.findByText("Der Regen hatte die Spuren fast fortgespült.");

    await userEvent.click(screen.getByText("Chronik"));

    expect(screen.getByText("Erster Absatz der Chronik.")).toBeInTheDocument();
    expect(screen.getByText("Zweiter Absatz der Chronik.")).toBeInTheDocument();
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
      continuation: { narration: "Bran nickt.", options: [] },
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

  it("grows the action field with its content", async () => {
    vi.spyOn(client, "loadRun").mockResolvedValue(buildDocument());
    renderPlay();
    const input = await screen.findByPlaceholderText("Was tust du?");
    expect(input.tagName).toBe("TEXTAREA");

    vi.spyOn(input as HTMLTextAreaElement, "scrollHeight", "get").mockReturnValue(120);
    await userEvent.type(input, "Ein langer Text");

    expect((input as HTMLTextAreaElement).style.height).toBe("120px");
  });

  it("submits on Enter but inserts a line break on Shift+Enter", async () => {
    vi.spyOn(client, "loadRun").mockResolvedValue(buildDocument());
    vi.spyOn(client, "playTurn").mockResolvedValue({
      state: buildDocument().game_state,
      continuation: { narration: "Bran nickt.", options: [] },
      proposed_change_count: 1,
      summary_failed: false,
      summary_failure_message: null,
    });
    renderPlay();
    const input = await screen.findByPlaceholderText("Was tust du?");

    await userEvent.type(input, "Zeile eins{Shift>}{Enter}{/Shift}Zeile zwei");
    expect(client.playTurn).not.toHaveBeenCalled();
    expect(input).toHaveValue("Zeile eins\nZeile zwei");

    await userEvent.type(input, "{Enter}");
    expect(client.playTurn).toHaveBeenCalledWith(RUN_ID, {
      player_input: "Zeile eins\nZeile zwei",
    });
  });

  it("hides continuation chips until a turn has been played (TASK-034)", async () => {
    vi.spyOn(client, "loadRun").mockResolvedValue(buildDocument());
    renderPlay();

    await screen.findByPlaceholderText("Was tust du?");
    expect(document.querySelector(".play-continuation-chips")).toBeNull();
  });

  it("shows continuation chips from the playTurn response and submits on the second click", async () => {
    vi.spyOn(client, "loadRun").mockResolvedValue(buildDocument());
    vi.spyOn(client, "playTurn")
      .mockResolvedValueOnce({
        state: buildDocument().game_state,
        continuation: {
          narration: "Die Spur führt weiter.",
          options: ["Ich folge der Spur.", "Ich rede mit dem Wirt."],
        },
        proposed_change_count: 1,
        summary_failed: false,
        summary_failure_message: null,
      })
      .mockResolvedValueOnce({
        state: buildDocument().game_state,
        continuation: { narration: "Die Spur endet abrupt.", options: [] },
        proposed_change_count: 1,
        summary_failed: false,
        summary_failure_message: null,
      });
    renderPlay();

    const input = await screen.findByPlaceholderText("Was tust du?");
    await userEvent.type(input, "Ich schaue mich um.");
    await userEvent.click(screen.getByRole("button", { name: /Handlung ausführen/ }));

    const chip = await screen.findByRole("button", { name: "Ich folge der Spur." });
    expect(chip).toHaveAttribute("aria-pressed", "false");

    await userEvent.click(chip);
    expect(input).toHaveValue("Ich folge der Spur.");
    expect(chip).toHaveAttribute("aria-pressed", "true");

    await userEvent.click(chip);
    expect(client.playTurn).toHaveBeenLastCalledWith(RUN_ID, { player_input: "Ich folge der Spur." });
  });

  it("replaces the active chip instead of submitting when a different chip is clicked", async () => {
    vi.spyOn(client, "loadRun").mockResolvedValue(buildDocument());
    vi.spyOn(client, "playTurn").mockResolvedValueOnce({
      state: buildDocument().game_state,
      continuation: { narration: "...", options: ["Option A", "Option B"] },
      proposed_change_count: 1,
      summary_failed: false,
      summary_failure_message: null,
    });
    renderPlay();

    const input = await screen.findByPlaceholderText("Was tust du?");
    await userEvent.type(input, "Ich schaue mich um.");
    await userEvent.click(screen.getByRole("button", { name: /Handlung ausführen/ }));

    const optionA = await screen.findByRole("button", { name: "Option A" });
    const optionB = screen.getByRole("button", { name: "Option B" });

    await userEvent.click(optionA);
    expect(optionA).toHaveAttribute("aria-pressed", "true");

    await userEvent.click(optionB);
    expect(input).toHaveValue("Option B");
    expect(optionB).toHaveAttribute("aria-pressed", "true");
    expect(optionA).toHaveAttribute("aria-pressed", "false");
    expect(client.playTurn).toHaveBeenCalledTimes(1);
  });

  it("deactivates the active chip once the input is edited manually", async () => {
    vi.spyOn(client, "loadRun").mockResolvedValue(buildDocument());
    vi.spyOn(client, "playTurn").mockResolvedValueOnce({
      state: buildDocument().game_state,
      continuation: { narration: "...", options: ["Option A"] },
      proposed_change_count: 1,
      summary_failed: false,
      summary_failure_message: null,
    });
    renderPlay();

    const input = await screen.findByPlaceholderText("Was tust du?");
    await userEvent.type(input, "Ich schaue mich um.");
    await userEvent.click(screen.getByRole("button", { name: /Handlung ausführen/ }));

    const optionA = await screen.findByRole("button", { name: "Option A" });
    await userEvent.click(optionA);
    expect(optionA).toHaveAttribute("aria-pressed", "true");

    await userEvent.type(input, "!");
    expect(optionA).toHaveAttribute("aria-pressed", "false");
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

  describe("view mode", () => {
    it("starts as flowing text and switches to a chat with the player on the right", async () => {
      vi.spyOn(client, "loadRun").mockResolvedValue(buildDocument());
      renderPlay();
      await screen.findByText("Der Regen hatte die Spuren fast fortgespült.");
      expect(screen.getByText("Du: Ich untersuche die Laterne.")).toBeInTheDocument();

      await userEvent.click(screen.getByRole("button", { name: "Chat-Ansicht" }));

      expect(screen.queryByText("Du: Ich untersuche die Laterne.")).not.toBeInTheDocument();
      const playerBubble = screen.getByText("Ich untersuche die Laterne.").closest(".chat-bubble");
      expect(playerBubble).toHaveClass("chat-bubble--player");
      const narratorBubble = screen
        .getByText("Unter der Laterne glitzert ein silberner Faden.")
        .closest(".chat-bubble");
      expect(narratorBubble).toHaveClass("chat-bubble--narrator");
      expect(screen.getByRole("button", { name: "Fließtext" })).toBeInTheDocument();
    });

    it("remembers the chosen mode", async () => {
      vi.spyOn(client, "loadRun").mockResolvedValue(buildDocument());
      renderPlay();
      await userEvent.click(await screen.findByRole("button", { name: "Chat-Ansicht" }));
      expect(localStorage.getItem("play.viewMode")).toBe("chat");
    });

    it("opens in chat mode when it was stored", async () => {
      localStorage.setItem("play.viewMode", "chat");
      vi.spyOn(client, "loadRun").mockResolvedValue(buildDocument());
      renderPlay();

      expect(await screen.findByRole("button", { name: "Fließtext" })).toBeInTheDocument();
    });
  });
});
