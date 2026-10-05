import { configureStore } from "@reduxjs/toolkit";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { apiSlice } from "../../api/apiSlice";
import * as client from "../../api/client";
import type { AdminPromptList, AdminPromptVersion } from "../../api/types";
import { Settings } from "./Settings";

function buildStore() {
  return configureStore({
    reducer: { [apiSlice.reducerPath]: apiSlice.reducer },
    middleware: (getDefaultMiddleware) => getDefaultMiddleware().concat(apiSlice.middleware),
  });
}

function version(overrides: Partial<AdminPromptVersion>): AdminPromptVersion {
  return {
    version_id: "00000000-0000-0000-0000-000000000001",
    kind: "task",
    key: "story_generation",
    text: "Original-Text",
    is_default: false,
    task_ids: [],
    source: "toml_seed",
    created_at: "2026-10-05T10:00:00Z",
    created_by: null,
    is_active: true,
    is_modified: false,
    ...overrides,
  };
}

const list: AdminPromptList = {
  package_id: "story.base",
  package_version: "1",
  entries: [
    version({}),
    version({
      version_id: "00000000-0000-0000-0000-000000000002",
      kind: "option",
      key: "tone/balanced",
      text: "Ausgewogen",
      is_default: true,
      source: "ui",
      created_by: "admin-1",
      is_modified: true,
    }),
    version({
      version_id: "00000000-0000-0000-0000-000000000003",
      kind: "directive",
      key: "content_boundary",
      text: "Grenze",
      task_ids: ["story_generation"],
    }),
  ],
};

function renderSettings() {
  render(
    <Provider store={buildStore()}>
      <Settings />
    </Provider>,
  );
}

function entry(key: string) {
  return within(screen.getByRole("article", { name: key }));
}

describe("Settings", () => {
  beforeEach(() => {
    vi.spyOn(client, "listAdminModels").mockResolvedValue({ settings: [], candidates: [] });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("lists tasks, options and directives and marks edited ones", async () => {
    vi.spyOn(client, "listAdminPrompts").mockResolvedValue(list);

    renderSettings();

    expect(await screen.findByRole("heading", { name: "Einstellungen" })).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Aufgaben" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Optionen" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Direktiven" })).toBeInTheDocument();
    expect(entry("story_generation").getByRole("textbox")).toHaveValue("Original-Text");
    expect(entry("tone/balanced").getByText("Geändert")).toBeInTheDocument();
    expect(entry("story_generation").queryByText("Geändert")).not.toBeInTheDocument();
  });

  it("saves an edited text as a new version", async () => {
    vi.spyOn(client, "listAdminPrompts").mockResolvedValue(list);
    const save = vi
      .spyOn(client, "savePromptText")
      .mockResolvedValue(version({ text: "Neuer Text", source: "ui", is_modified: true }));
    renderSettings();
    const box = (await screen.findAllByRole("textbox"))[0];
    expect(entry("story_generation").getByRole("button", { name: "Speichern" })).toBeDisabled();

    await userEvent.clear(box);
    await userEvent.type(box, "Neuer Text");
    await userEvent.click(entry("story_generation").getByRole("button", { name: "Speichern" }));

    expect(save).toHaveBeenCalledWith({
      kind: "task",
      key: "story_generation",
      text: "Neuer Text",
    });
  });

  it("restores the original of one entry", async () => {
    vi.spyOn(client, "listAdminPrompts").mockResolvedValue(list);
    const reset = vi.spyOn(client, "resetPrompts").mockResolvedValue({ versions: [] });
    renderSettings();
    await screen.findByRole("article", { name: "tone/balanced" });
    expect(
      entry("story_generation").getByRole("button", { name: "Auf Original zurücksetzen" }),
    ).toBeDisabled();

    await userEvent.click(
      entry("tone/balanced").getByRole("button", { name: "Auf Original zurücksetzen" }),
    );

    expect(reset).toHaveBeenCalledWith({ kind: "option", key: "tone/balanced" });
  });

  it("restores every prompt at once", async () => {
    vi.spyOn(client, "listAdminPrompts").mockResolvedValue(list);
    const reset = vi.spyOn(client, "resetPrompts").mockResolvedValue({ versions: [] });
    renderSettings();

    await userEvent.click(await screen.findByRole("button", { name: "Alle zurücksetzen" }));

    expect(reset).toHaveBeenCalledWith({});
  });

  it("shows the history of an entry on demand", async () => {
    vi.spyOn(client, "listAdminPrompts").mockResolvedValue(list);
    const history = vi.spyOn(client, "fetchPromptHistory").mockResolvedValue({
      versions: [
        version({
          kind: "option",
          key: "tone/balanced",
          text: "Ausgewogen",
          source: "ui",
          created_by: "admin-1",
          is_modified: true,
        }),
        version({
          kind: "option",
          key: "tone/balanced",
          text: "Original",
          is_active: false,
          created_at: "2026-10-01T08:00:00Z",
        }),
      ],
    });
    renderSettings();
    await screen.findByRole("article", { name: "tone/balanced" });

    await userEvent.click(entry("tone/balanced").getByRole("button", { name: "Verlauf" }));

    expect(history).toHaveBeenCalledWith("option", "tone/balanced");
    const items = await entry("tone/balanced").findAllByRole("listitem");
    expect(items).toHaveLength(2);
    expect(items[0]).toHaveTextContent("Bearbeitet");
    expect(items[0]).toHaveTextContent("admin-1");
    expect(items[1]).toHaveTextContent("Original (TOML)");
    expect(items[1]).toHaveTextContent("Original");
  });
});
