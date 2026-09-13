import { configureStore } from "@reduxjs/toolkit";
import { afterEach, describe, expect, it, vi } from "vitest";
import { apiSlice } from "./apiSlice";
import { ApiError } from "./client";
import * as client from "./client";
import type { GameDocument, PromptProfileCatalog, RunProposal, RunSummary } from "./types";

function buildStore() {
  return configureStore({
    reducer: { [apiSlice.reducerPath]: apiSlice.reducer },
    middleware: (getDefaultMiddleware) => getDefaultMiddleware().concat(apiSlice.middleware),
  });
}

const sampleRun: RunSummary = {
  id: "11111111-1111-1111-1111-111111111111",
  name: "Die Schatten von Auenfall",
  status: "active",
  current_revision: 12,
  game_role: "owner",
  updated_at: "2026-09-10T00:00:00Z",
};

describe("apiSlice.listRuns", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("returns the typed run list on success", async () => {
    vi.spyOn(client, "listRuns").mockResolvedValue({ runs: [sampleRun] });
    const store = buildStore();

    const result = await store.dispatch(apiSlice.endpoints.listRuns.initiate());

    expect(result.data).toEqual([sampleRun]);
  });

  it("maps a 401 ApiError to the session_expired code (TASK-030)", async () => {
    vi.spyOn(client, "listRuns").mockRejectedValue(
      new ApiError(401, { error: "unauthorized", detail: "Nicht angemeldet." }),
    );
    const store = buildStore();

    const result = await store.dispatch(apiSlice.endpoints.listRuns.initiate());

    expect(result.error).toEqual({
      status: 401,
      code: "session_expired",
      message: "Nicht angemeldet.",
    });
  });
});

const sampleCatalog: PromptProfileCatalog = {
  package_id: "story.base",
  package_version: "1",
  categories: [
    {
      id: "genre",
      default_option_id: "dark_fantasy",
      options: [
        { id: "dark_fantasy", description: "Bedrohliche Fantasy mit moralischen Grauzonen." },
        { id: "fantasy", description: "Klassische Fantasy." },
      ],
    },
  ],
};

describe("apiSlice.promptProfileCatalog", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("returns the typed catalog on success", async () => {
    vi.spyOn(client, "fetchPromptProfileCatalog").mockResolvedValue(sampleCatalog);
    const store = buildStore();

    const result = await store.dispatch(apiSlice.endpoints.promptProfileCatalog.initiate());

    expect(result.data).toEqual(sampleCatalog);
  });

  it("maps a failure into the normalized QueryError shape", async () => {
    vi.spyOn(client, "fetchPromptProfileCatalog").mockRejectedValue(
      new ApiError(502, { error: "story_model_unavailable", detail: "Story-Modell nicht erreichbar." }),
    );
    const store = buildStore();

    const result = await store.dispatch(apiSlice.endpoints.promptProfileCatalog.initiate());

    expect(result.error).toEqual({
      status: 502,
      code: "story_model_unavailable",
      message: "Story-Modell nicht erreichbar.",
    });
  });
});

const sampleProposal: RunProposal = {
  proposal_id: "33333333-3333-3333-3333-333333333333",
  opening_narration: "Der Regen hatte die Spuren fast fortgespült.",
  world: { entities: [], links: [], facts: [], knowledge: [], rules: [], goals: [], scene_location_ids: [] },
  suggested_player_entity_ids: [],
  suggested_title: "Die Schatten von Auenfall",
};

const sampleDocument: GameDocument = {
  schema_version: 1,
  game_run: {
    id: "22222222-2222-2222-2222-222222222222",
    name: "Die Schatten von Auenfall",
    status: "draft",
    current_revision: 1,
    members: [],
    created_at: "2026-09-10T00:00:00Z",
    updated_at: "2026-09-10T00:00:00Z",
  },
  game_state: {
    run_id: "22222222-2222-2222-2222-222222222222",
    revision: 1,
    configuration: {},
    world: { entities: [], links: [], facts: [], knowledge: [], rules: [], goals: [], scene_location_ids: [] },
    story: { turns: [], summary: null, current_turn_sequence: 0, initialization: null },
  },
};

describe("apiSlice submit-flow mutations", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("proposeRun returns the typed proposal on success", async () => {
    vi.spyOn(client, "proposeRun").mockResolvedValue(sampleProposal);
    const store = buildStore();

    const result = await store.dispatch(
      apiSlice.endpoints.proposeRun.initiate({
        initial_prompt: "Ein Kurier verschwindet spurlos.",
        control_mode: "player",
        controllable_characters: [{ name: "Elian" }],
      }),
    );

    expect(result.data).toEqual(sampleProposal);
  });

  it("proposeRun maps a 422 invalid_prompt_selection error", async () => {
    vi.spyOn(client, "proposeRun").mockRejectedValue(
      new ApiError(422, {
        error: "invalid_prompt_selection",
        detail: "Ungültige Auswahl für Genre.",
        category: "genre",
        option_id: "space_opera",
      }),
    );
    const store = buildStore();

    const result = await store.dispatch(
      apiSlice.endpoints.proposeRun.initiate({
        initial_prompt: "Ein Kurier verschwindet spurlos.",
        control_mode: "player",
        controllable_characters: [{ name: "Elian" }],
      }),
    );

    expect(result.error).toEqual({
      status: 422,
      code: "invalid_prompt_selection",
      message: "Ungültige Auswahl für Genre.",
    });
  });

  it("confirmRun returns the created draft document", async () => {
    vi.spyOn(client, "confirmRun").mockResolvedValue(sampleDocument);
    const store = buildStore();

    const result = await store.dispatch(
      apiSlice.endpoints.confirmRun.initiate({
        proposal_id: sampleProposal.proposal_id,
        character_decisions: [],
        item_decisions: [],
      }),
    );

    expect(result.data).toEqual(sampleDocument);
  });

  it("startPlaythrough returns the now-active document", async () => {
    vi.spyOn(client, "startPlaythrough").mockResolvedValue({
      ...sampleDocument,
      game_run: { ...sampleDocument.game_run, status: "active" },
    });
    const store = buildStore();

    const result = await store.dispatch(apiSlice.endpoints.startPlaythrough.initiate(sampleDocument.game_run.id));

    expect(result.data?.game_run.status).toBe("active");
  });
});

describe("apiSlice.loadRun / playTurn", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("loadRun returns the typed document", async () => {
    vi.spyOn(client, "loadRun").mockResolvedValue(sampleDocument);
    const store = buildStore();

    const result = await store.dispatch(apiSlice.endpoints.loadRun.initiate(sampleDocument.game_run.id));

    expect(result.data).toEqual(sampleDocument);
  });

  it("loadRun maps a not-found error into the normalized QueryError shape", async () => {
    vi.spyOn(client, "loadRun").mockRejectedValue(
      new ApiError(404, { error: "not_found", detail: "Geschichte nicht gefunden." }),
    );
    const store = buildStore();

    const result = await store.dispatch(apiSlice.endpoints.loadRun.initiate(sampleDocument.game_run.id));

    expect(result.error).toEqual({ status: 404, code: "not_found", message: "Geschichte nicht gefunden." });
  });

  it("playTurn returns the resulting turn state", async () => {
    const turnResult = {
      state: sampleDocument.game_state,
      proposed_change_count: 2,
      summary_failed: false,
      summary_failure_message: null,
    };
    vi.spyOn(client, "playTurn").mockResolvedValue(turnResult);
    const store = buildStore();

    const result = await store.dispatch(
      apiSlice.endpoints.playTurn.initiate({
        runId: sampleDocument.game_run.id,
        payload: { player_input: "Ich untersuche die Laterne." },
      }),
    );

    expect(result.data).toEqual(turnResult);
  });

  it("playTurn maps a run_not_active error into the normalized QueryError shape", async () => {
    vi.spyOn(client, "playTurn").mockRejectedValue(
      new ApiError(409, { error: "run_not_active", detail: "Diese Geschichte läuft nicht mehr." }),
    );
    const store = buildStore();

    const result = await store.dispatch(
      apiSlice.endpoints.playTurn.initiate({
        runId: sampleDocument.game_run.id,
        payload: { player_input: "Ich untersuche die Laterne." },
      }),
    );

    expect(result.error).toEqual({
      status: 409,
      code: "run_not_active",
      message: "Diese Geschichte läuft nicht mehr.",
    });
  });
});
