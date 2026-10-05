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
    is_custom: false,
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
    vi.spyOn(client, "listArchivedPromptOptions").mockResolvedValue({ versions: [] });
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
    expect(within(article).getByText("balanced")).toBeInTheDocument();
    expect(within(article).queryByText("tone/balanced")).not.toBeInTheDocument();
    expect(within(article).queryByRole("textbox")).not.toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Ton & Stil", selected: true })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Ton" })).toBeInTheDocument();
    expect(screen.queryByRole("article", { name: "story_generation" })).not.toBeInTheDocument();

    await userEvent.click(within(article).getAllByRole("button")[0]);
    expect(within(article).getByRole("textbox")).toHaveValue("Ausgewogen");
  });

  it("groups the option categories into a few sub-tabs", async () => {
    const option = (id: string, key: string) =>
      version({ version_id: id, kind: "option", key, text: key });
    vi.spyOn(client, "listAdminPrompts").mockResolvedValue({
      ...list,
      entries: [
        option("00000000-0000-0000-0000-000000000011", "genre/fantasy"),
        option("00000000-0000-0000-0000-000000000012", "tone/balanced"),
        option("00000000-0000-0000-0000-000000000013", "prose_style/concise"),
        option("00000000-0000-0000-0000-000000000014", "pacing/slow"),
        option("00000000-0000-0000-0000-000000000015", "content_profile/teen"),
        option("00000000-0000-0000-0000-000000000016", "setting/harbor"),
      ],
    });
    renderSettings();
    await userEvent.click(await screen.findByRole("tab", { name: "Optionen" }));

    await screen.findByRole("article", { name: "genre/fantasy" });
    expect(screen.getAllByRole("tab").map((tab) => tab.textContent)).toEqual([
      "Modelle",
      "Aufgaben",
      "Optionen",
      "Direktiven",
      "Genre",
      "Ton & Stil",
      "Spielgefühl",
      "Sonstiges",
    ]);
    expect(screen.queryByRole("article", { name: "tone/balanced" })).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("tab", { name: "Ton & Stil" }));
    expect(screen.getByRole("article", { name: "tone/balanced" })).toBeInTheDocument();
    expect(screen.getByRole("article", { name: "prose_style/concise" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Prosastil" })).toBeInTheDocument();

    await userEvent.click(screen.getByRole("tab", { name: "Sonstiges" }));
    expect(screen.getByRole("article", { name: "content_profile/teen" })).toBeInTheDocument();
    expect(screen.getByRole("article", { name: "setting/harbor" })).toBeInTheDocument();
  });

  describe("options added by hand", () => {
    const custom = version({
      version_id: "00000000-0000-0000-0000-000000000021",
      kind: "option",
      key: "tone/melancholic",
      text: "Wehmütig",
      source: "ui",
      created_by: "admin-1",
      is_modified: true,
      is_custom: true,
    });
    const withCustom: AdminPromptList = { ...list, entries: [...list.entries, custom] };

    it("adds a new option to a category and closes the form", async () => {
      vi.spyOn(client, "listAdminPrompts").mockResolvedValue(list);
      const create = vi.spyOn(client, "createPromptOption").mockResolvedValue(custom);
      renderSettings();
      await userEvent.click(await screen.findByRole("tab", { name: "Optionen" }));

      await userEvent.click(await screen.findByRole("button", { name: "Neue Option" }));
      const create_ = screen.getByRole("button", { name: "Anlegen" });
      expect(create_).toBeDisabled();
      await userEvent.type(screen.getByLabelText("Options-ID"), "melancholic");
      await userEvent.type(screen.getByLabelText("Beschreibung für das Modell"), "Wehmütig");
      await userEvent.click(create_);

      expect(create).toHaveBeenCalledWith({
        category: "tone",
        option_id: "melancholic",
        text: "Wehmütig",
      });
      await vi.waitFor(() => expect(screen.queryByLabelText("Options-ID")).not.toBeInTheDocument());
    });

    it("rejects an id that is not a lowercase slug before sending it", async () => {
      vi.spyOn(client, "listAdminPrompts").mockResolvedValue(list);
      const create = vi.spyOn(client, "createPromptOption");
      renderSettings();
      await userEvent.click(await screen.findByRole("tab", { name: "Optionen" }));
      await userEvent.click(await screen.findByRole("button", { name: "Neue Option" }));

      await userEvent.type(screen.getByLabelText("Options-ID"), "Not Valid");
      await userEvent.type(screen.getByLabelText("Beschreibung für das Modell"), "Text");

      expect(screen.getByRole("button", { name: "Anlegen" })).toBeDisabled();
      expect(create).not.toHaveBeenCalled();
    });

    it("shows the reason when the backend refuses the new option", async () => {
      vi.spyOn(client, "listAdminPrompts").mockResolvedValue(list);
      vi.spyOn(client, "createPromptOption").mockRejectedValue(
        new client.ApiError(409, { error: "prompt_option_exists", detail: "Die Option tone/dark gibt es schon." }),
      );
      renderSettings();
      await userEvent.click(await screen.findByRole("tab", { name: "Optionen" }));
      await userEvent.click(await screen.findByRole("button", { name: "Neue Option" }));
      await userEvent.type(screen.getByLabelText("Options-ID"), "dark");
      await userEvent.type(screen.getByLabelText("Beschreibung für das Modell"), "Text");

      await userEvent.click(screen.getByRole("button", { name: "Anlegen" }));

      expect(await screen.findByText(/Die Option tone\/dark gibt es schon/)).toBeInTheDocument();
    });

    it("offers no new-option button for fixed categories", async () => {
      vi.spyOn(client, "listAdminPrompts").mockResolvedValue({
        ...list,
        entries: [
          version({
            version_id: "00000000-0000-0000-0000-000000000031",
            kind: "option",
            key: "pacing/slow",
            text: "Langsam",
          }),
        ],
      });
      renderSettings();
      await userEvent.click(await screen.findByRole("tab", { name: "Optionen" }));

      await screen.findByRole("article", { name: "pacing/slow" });
      expect(screen.queryByRole("button", { name: "Neue Option" })).not.toBeInTheDocument();
    });

    it("marks a custom option, offers removal instead of a reset, and removes it after confirming", async () => {
      vi.spyOn(client, "listAdminPrompts").mockResolvedValue(withCustom);
      const remove = vi.spyOn(client, "archivePromptOption").mockResolvedValue(undefined);
      const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
      renderSettings();
      await openEntry("Optionen", "tone/melancholic");

      expect(entry("tone/melancholic").getByText("Eigene")).toBeInTheDocument();
      expect(
        entry("tone/melancholic").queryByRole("button", { name: "Auf Original zurücksetzen" }),
      ).not.toBeInTheDocument();
      await userEvent.click(entry("tone/melancholic").getByRole("button", { name: "Entfernen" }));

      expect(confirm).toHaveBeenCalled();
      expect(remove).toHaveBeenCalledWith({ category: "tone", option_id: "melancholic" });
    });

    it("keeps the option when the removal is not confirmed", async () => {
      vi.spyOn(client, "listAdminPrompts").mockResolvedValue(withCustom);
      const remove = vi.spyOn(client, "archivePromptOption");
      vi.spyOn(window, "confirm").mockReturnValue(false);
      renderSettings();
      await openEntry("Optionen", "tone/melancholic");

      await userEvent.click(entry("tone/melancholic").getByRole("button", { name: "Entfernen" }));

      expect(remove).not.toHaveBeenCalled();
    });

    it("shows the X of an option in its collapsed header", async () => {
      vi.spyOn(client, "listAdminPrompts").mockResolvedValue(withCustom);
      const archive = vi.spyOn(client, "archivePromptOption").mockResolvedValue(undefined);
      vi.spyOn(window, "confirm").mockReturnValue(true);
      renderSettings();
      await userEvent.click(await screen.findByRole("tab", { name: "Optionen" }));
      await screen.findByRole("article", { name: "tone/melancholic" });

      expect(entry("tone/melancholic").queryByRole("textbox")).not.toBeInTheDocument();
      await userEvent.click(entry("tone/melancholic").getByRole("button", { name: "Entfernen" }));

      expect(archive).toHaveBeenCalledWith({ category: "tone", option_id: "melancholic" });
    });

    it("lets the X of a shipped option reset it to the original, only when it was changed", async () => {
      vi.spyOn(client, "listAdminPrompts").mockResolvedValue(withCustom);
      const reset = vi.spyOn(client, "resetPrompts").mockResolvedValue({ versions: [] });
      renderSettings();
      await userEvent.click(await screen.findByRole("tab", { name: "Optionen" }));
      await screen.findByRole("article", { name: "tone/balanced" });

      await userEvent.click(
        entry("tone/balanced").getByRole("button", { name: "Auf Original zurücksetzen" }),
      );

      expect(reset).toHaveBeenCalledWith({ kind: "option", key: "tone/balanced" });
    });

    it("disables the X of an unchanged shipped option", async () => {
      vi.spyOn(client, "listAdminPrompts").mockResolvedValue({
        ...list,
        entries: [
          version({
            version_id: "00000000-0000-0000-0000-000000000041",
            kind: "option",
            key: "tone/dark",
            text: "Düster",
          }),
        ],
      });
      renderSettings();
      await userEvent.click(await screen.findByRole("tab", { name: "Optionen" }));
      await screen.findByRole("article", { name: "tone/dark" });

      expect(
        entry("tone/dark").getByRole("button", { name: "Auf Original zurücksetzen" }),
      ).toBeDisabled();
    });

    it("does not offer removal for a shipped option", async () => {
      vi.spyOn(client, "listAdminPrompts").mockResolvedValue(withCustom);
      renderSettings();
      await openEntry("Optionen", "tone/balanced");

      expect(entry("tone/balanced").queryByRole("button", { name: "Entfernen" })).not.toBeInTheDocument();
    });
  });

  describe("resetting all options", () => {
    const custom = version({
      version_id: "00000000-0000-0000-0000-000000000021",
      kind: "option",
      key: "tone/melancholic",
      text: "Wehmütig",
      source: "ui",
      created_by: "admin-1",
      is_modified: true,
      is_custom: true,
    });
    const withCustom: AdminPromptList = { ...list, entries: [...list.entries, custom] };

    async function clickResetAll() {
      await userEvent.click(await screen.findByRole("tab", { name: "Optionen" }));
      await screen.findByRole("article", { name: "tone/balanced" });
      await userEvent.click(screen.getByRole("button", { name: "Alle Optionen zurücksetzen" }));
    }

    it("resets right away when there are no options of one's own", async () => {
      vi.spyOn(client, "listAdminPrompts").mockResolvedValue(list);
      const reset = vi.spyOn(client, "resetPrompts").mockResolvedValue({ versions: [] });
      const remove = vi.spyOn(client, "removePromptOptions");
      renderSettings();

      await clickResetAll();

      expect(reset).toHaveBeenCalledWith({ kind: "option" });
      expect(remove).not.toHaveBeenCalled();
    });

    it("asks what to do with options of one's own before resetting", async () => {
      vi.spyOn(client, "listAdminPrompts").mockResolvedValue(withCustom);
      const reset = vi.spyOn(client, "resetPrompts").mockResolvedValue({ versions: [] });
      renderSettings();

      await clickResetAll();

      expect(await screen.findByText(/1 eigene Option/)).toBeInTheDocument();
      expect(reset).not.toHaveBeenCalled();
    });

    it("resets only the shipped options when asked to", async () => {
      vi.spyOn(client, "listAdminPrompts").mockResolvedValue(withCustom);
      const reset = vi.spyOn(client, "resetPrompts").mockResolvedValue({ versions: [] });
      const remove = vi.spyOn(client, "removePromptOptions");
      renderSettings();
      await clickResetAll();

      await userEvent.click(await screen.findByRole("button", { name: "Nur Standard-Optionen zurücksetzen" }));

      expect(reset).toHaveBeenCalledWith({ kind: "option" });
      expect(remove).not.toHaveBeenCalled();
    });

    it("also moves the options of one's own to the trash when asked to", async () => {
      vi.spyOn(client, "listAdminPrompts").mockResolvedValue(withCustom);
      const reset = vi.spyOn(client, "resetPrompts").mockResolvedValue({ versions: [] });
      const remove = vi
        .spyOn(client, "removePromptOptions")
        .mockResolvedValue({ outcomes: [{ key: "tone/melancholic", status: "done", message: "" }] });
      renderSettings();
      await clickResetAll();

      await userEvent.click(await screen.findByRole("button", { name: "Auch eigene entfernen" }));

      await vi.waitFor(() => expect(remove).toHaveBeenCalledWith({ mode: "archive" }));
      expect(reset).toHaveBeenCalledWith({ kind: "option" });
    });

    it("names an own option that stayed because a story still uses it", async () => {
      vi.spyOn(client, "listAdminPrompts").mockResolvedValue(withCustom);
      vi.spyOn(client, "resetPrompts").mockResolvedValue({ versions: [] });
      vi.spyOn(client, "removePromptOptions").mockResolvedValue({
        outcomes: [
          { key: "tone/melancholic", status: "in_use", message: "Die Option wird noch von einer Geschichte verwendet." },
        ],
      });
      renderSettings();
      await clickResetAll();

      await userEvent.click(await screen.findByRole("button", { name: "Auch eigene entfernen" }));

      expect(await screen.findByText(/tone\/melancholic.*noch von einer Geschichte/)).toBeInTheDocument();
    });

    it("does nothing when cancelled", async () => {
      vi.spyOn(client, "listAdminPrompts").mockResolvedValue(withCustom);
      const reset = vi.spyOn(client, "resetPrompts");
      renderSettings();
      await clickResetAll();

      await userEvent.click(await screen.findByRole("button", { name: "Abbrechen" }));

      expect(reset).not.toHaveBeenCalled();
      expect(screen.queryByRole("button", { name: "Auch eigene entfernen" })).not.toBeInTheDocument();
    });
  });

  describe("the trash", () => {
    const trashed = version({
      version_id: "00000000-0000-0000-0000-000000000051",
      kind: "option",
      key: "tone/melancholic",
      text: "Wehmütig",
      source: "ui",
      is_active: false,
      is_custom: true,
    });

    async function openTrash() {
      vi.spyOn(client, "listAdminPrompts").mockResolvedValue(list);
      vi.spyOn(client, "listArchivedPromptOptions").mockResolvedValue({ versions: [trashed] });
      renderSettings();
      await userEvent.click(await screen.findByRole("tab", { name: "Optionen" }));
      return screen.findByRole("region", { name: "Papierkorb" });
    }

    it("is only shown when something is in it", async () => {
      vi.spyOn(client, "listAdminPrompts").mockResolvedValue(list);
      renderSettings();
      await userEvent.click(await screen.findByRole("tab", { name: "Optionen" }));

      await screen.findByRole("article", { name: "tone/balanced" });
      expect(screen.queryByRole("region", { name: "Papierkorb" })).not.toBeInTheDocument();
    });

    it("lists the archived options and restores one", async () => {
      const restore = vi.spyOn(client, "restorePromptOption").mockResolvedValue(undefined);
      const trash = within(await openTrash());

      expect(trash.getByText("tone/melancholic")).toBeInTheDocument();
      await userEvent.click(trash.getByRole("button", { name: "Wiederherstellen" }));

      expect(restore).toHaveBeenCalledWith({ category: "tone", option_id: "melancholic" });
    });

    it("deletes one option for good only after confirming", async () => {
      const purge = vi.spyOn(client, "purgePromptOption").mockResolvedValue(undefined);
      const confirm = vi.spyOn(window, "confirm").mockReturnValueOnce(false).mockReturnValueOnce(true);
      const trash = within(await openTrash());

      await userEvent.click(trash.getByRole("button", { name: "Endgültig löschen" }));
      expect(purge).not.toHaveBeenCalled();
      await userEvent.click(trash.getByRole("button", { name: "Endgültig löschen" }));

      expect(confirm).toHaveBeenCalledTimes(2);
      expect(purge).toHaveBeenCalledWith({ category: "tone", option_id: "melancholic" });
    });

    it("empties the trash after confirming", async () => {
      const remove = vi
        .spyOn(client, "removePromptOptions")
        .mockResolvedValue({ outcomes: [{ key: "tone/melancholic", status: "done", message: "" }] });
      vi.spyOn(window, "confirm").mockReturnValue(true);
      const trash = within(await openTrash());

      await userEvent.click(trash.getByRole("button", { name: "Papierkorb leeren" }));

      expect(remove).toHaveBeenCalledWith({ mode: "purge" });
    });
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
