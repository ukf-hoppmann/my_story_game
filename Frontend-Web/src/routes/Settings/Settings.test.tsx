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

/** Selects a tab, then waits for the item and expands it (items start collapsed). */
async function openEntry(tab: string, key: string) {
  await userEvent.click(screen.getByRole("tab", { name: tab }));
  const article = await screen.findByRole("article", { name: key });
  await userEvent.click(within(article).getAllByRole("button")[0]);
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

  it("opens on the models and offers one tab per prompt kind", async () => {
    vi.spyOn(client, "listAdminPrompts").mockResolvedValue(list);

    renderSettings();

    expect(await screen.findByRole("heading", { name: "Einstellungen" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Modelle", selected: true })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Aufgaben" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Optionen" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Direktiven" })).toBeInTheDocument();
    expect(screen.queryByRole("article", { name: "story_generation" })).not.toBeInTheDocument();
  });

  it("lists the entries of a kind collapsed and marks edited ones", async () => {
    vi.spyOn(client, "listAdminPrompts").mockResolvedValue(list);
    renderSettings();

    await userEvent.click(await screen.findByRole("tab", { name: "Optionen" }));

    const article = await screen.findByRole("article", { name: "tone/balanced" });
    expect(within(article).getByText("Geändert")).toBeInTheDocument();
    expect(within(article).queryByRole("textbox")).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "tone" })).toBeInTheDocument();
    expect(screen.queryByRole("article", { name: "story_generation" })).not.toBeInTheDocument();

    await userEvent.click(within(article).getAllByRole("button")[0]);
    expect(within(article).getByRole("textbox")).toHaveValue("Ausgewogen");
  });

  it("switches tabs with the arrow keys", async () => {
    vi.spyOn(client, "listAdminPrompts").mockResolvedValue(list);
    renderSettings();
    const models = await screen.findByRole("tab", { name: "Modelle" });
    models.focus();

    await userEvent.keyboard("{ArrowRight}");

    expect(screen.getByRole("tab", { name: "Aufgaben", selected: true })).toHaveFocus();
  });

  it("saves an edited text as a new version", async () => {
    vi.spyOn(client, "listAdminPrompts").mockResolvedValue(list);
    const save = vi
      .spyOn(client, "savePromptText")
      .mockResolvedValue(version({ text: "Neuer Text", source: "ui", is_modified: true }));
    renderSettings();
    await openEntry("Aufgaben", "story_generation");
    const box = screen.getByRole("textbox");
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
    await openEntry("Optionen", "tone/balanced");

    await userEvent.click(
      entry("tone/balanced").getByRole("button", { name: "Auf Original zurücksetzen" }),
    );

    expect(reset).toHaveBeenCalledWith({ kind: "option", key: "tone/balanced" });
  });

  it("disables the reset of an unmodified entry", async () => {
    vi.spyOn(client, "listAdminPrompts").mockResolvedValue(list);
    renderSettings();
    await openEntry("Aufgaben", "story_generation");

    expect(
      entry("story_generation").getByRole("button", { name: "Auf Original zurücksetzen" }),
    ).toBeDisabled();
  });

  it("restores every prompt of the open kind at once", async () => {
    vi.spyOn(client, "listAdminPrompts").mockResolvedValue(list);
    const reset = vi.spyOn(client, "resetPrompts").mockResolvedValue({ versions: [] });
    renderSettings();
    await userEvent.click(await screen.findByRole("tab", { name: "Optionen" }));

    await userEvent.click(await screen.findByRole("button", { name: "Alle Optionen zurücksetzen" }));

    expect(reset).toHaveBeenCalledWith({ kind: "option" });
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
    await openEntry("Optionen", "tone/balanced");

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
