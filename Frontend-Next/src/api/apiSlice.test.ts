import { configureStore } from "@reduxjs/toolkit";
import { afterEach, describe, expect, it, vi } from "vitest";
import { apiSlice } from "./apiSlice";
import { ApiError } from "./client";
import * as client from "./client";
import type { PromptProfileCatalog, RunSummary } from "./types";

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

  it("maps an ApiError into the normalized QueryError shape", async () => {
    vi.spyOn(client, "listRuns").mockRejectedValue(
      new ApiError(401, { error: "unauthorized", detail: "Nicht angemeldet." }),
    );
    const store = buildStore();

    const result = await store.dispatch(apiSlice.endpoints.listRuns.initiate());

    expect(result.error).toEqual({
      status: 401,
      code: "unauthorized",
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
