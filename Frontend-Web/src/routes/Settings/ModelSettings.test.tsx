import { configureStore } from "@reduxjs/toolkit";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { afterEach, describe, expect, it, vi } from "vitest";
import { apiSlice } from "../../api/apiSlice";
import * as client from "../../api/client";
import type { AdminModelOverview, AdminModelSetting } from "../../api/types";
import { ModelSettings } from "./ModelSettings";

function buildStore() {
  return configureStore({
    reducer: { [apiSlice.reducerPath]: apiSlice.reducer },
    middleware: (getDefaultMiddleware) => getDefaultMiddleware().concat(apiSlice.middleware),
  });
}

function setting(overrides: Partial<AdminModelSetting>): AdminModelSetting {
  return {
    version_id: "00000000-0000-0000-0000-000000000001",
    task: "story",
    model_ref: "model.story.default",
    temperature: 0.5,
    max_output_tokens: null,
    source: "toml_seed",
    created_at: "2026-10-05T10:00:00Z",
    created_by: null,
    is_active: true,
    is_modified: false,
    ...overrides,
  };
}

const overview: AdminModelOverview = {
  settings: [
    setting({}),
    setting({
      version_id: "00000000-0000-0000-0000-000000000002",
      task: "extraction",
      model_ref: "model.extraction.default",
      source: "ui",
      created_by: "testadmin",
      is_modified: true,
    }),
  ],
  candidates: [
    { task: "story", model_ref: "model.story.default", provider_id: "lmstudio", model_id: "qwen" },
    { task: "story", model_ref: "model.story.groq", provider_id: "groq", model_id: "gpt-oss" },
    {
      task: "extraction",
      model_ref: "model.extraction.default",
      provider_id: "lmstudio",
      model_id: "qwen",
    },
  ],
};

function renderModels() {
  render(
    <Provider store={buildStore()}>
      <ModelSettings />
    </Provider>,
  );
}

function card(name: string) {
  return within(screen.getByRole("article", { name }));
}

/** Waits for the item and expands it (items start collapsed). */
async function openCard(name: string) {
  const article = await screen.findByRole("article", { name });
  await userEvent.click(within(article).getAllByRole("button")[0]);
}

describe("ModelSettings", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows the current model and options of each task and marks edited ones", async () => {
    vi.spyOn(client, "listAdminModels").mockResolvedValue(overview);

    renderModels();

    expect(await screen.findByRole("heading", { name: "Modelle" })).toBeInTheDocument();
    await openCard("Story");
    await screen.findByRole("article", { name: "Extraktion" });
    const story = card("Story");
    expect(story.getByRole("combobox", { name: "Modell" })).toHaveValue("model.story.default");
    expect(story.getByRole("spinbutton", { name: "Temperatur" })).toHaveValue(0.5);
    expect(story.getByRole("spinbutton", { name: "Maximale Ausgabelänge (Tokens)" })).toHaveValue(
      null,
    );
    expect(story.queryByText("Geändert")).not.toBeInTheDocument();
    expect(card("Extraktion").getByText("Geändert")).toBeInTheDocument();
  });

  it("offers only the models of that task", async () => {
    vi.spyOn(client, "listAdminModels").mockResolvedValue(overview);
    renderModels();

    await openCard("Story");

    const options = card("Story").getAllByRole("option");
    expect(options.map((o) => o.textContent)).toEqual(["lmstudio · qwen", "groq · gpt-oss"]);
  });

  it("saves a changed model together with the options", async () => {
    vi.spyOn(client, "listAdminModels").mockResolvedValue(overview);
    const save = vi.spyOn(client, "saveModelSetting").mockResolvedValue(setting({}));
    renderModels();
    await openCard("Story");
    expect(card("Story").getByRole("button", { name: "Speichern" })).toBeDisabled();

    await userEvent.selectOptions(
      card("Story").getByRole("combobox", { name: "Modell" }),
      "model.story.groq",
    );
    const temperature = card("Story").getByRole("spinbutton", { name: "Temperatur" });
    await userEvent.clear(temperature);
    await userEvent.type(temperature, "0.9");
    await userEvent.type(
      card("Story").getByRole("spinbutton", { name: "Maximale Ausgabelänge (Tokens)" }),
      "800",
    );
    await userEvent.click(card("Story").getByRole("button", { name: "Speichern" }));

    expect(save).toHaveBeenCalledWith({
      task: "story",
      model_ref: "model.story.groq",
      temperature: 0.9,
      max_output_tokens: 800,
    });
  });

  it("sends null for an emptied option", async () => {
    vi.spyOn(client, "listAdminModels").mockResolvedValue(overview);
    const save = vi.spyOn(client, "saveModelSetting").mockResolvedValue(setting({}));
    renderModels();
    await openCard("Story");

    await userEvent.clear(card("Story").getByRole("spinbutton", { name: "Temperatur" }));
    await userEvent.click(card("Story").getByRole("button", { name: "Speichern" }));

    expect(save).toHaveBeenCalledWith({
      task: "story",
      model_ref: "model.story.default",
      temperature: null,
      max_output_tokens: null,
    });
  });

  it("restores the original of one task, or of all", async () => {
    vi.spyOn(client, "listAdminModels").mockResolvedValue(overview);
    const reset = vi.spyOn(client, "resetModelSettings").mockResolvedValue({ versions: [] });
    renderModels();
    await openCard("Story");
    await openCard("Extraktion");
    expect(card("Story").getByRole("button", { name: "Auf Original zurücksetzen" })).toBeDisabled();

    await userEvent.click(
      card("Extraktion").getByRole("button", { name: "Auf Original zurücksetzen" }),
    );
    await userEvent.click(screen.getByRole("button", { name: "Alle Modelle zurücksetzen" }));

    expect(reset).toHaveBeenNthCalledWith(1, { task: "extraction" });
    expect(reset).toHaveBeenNthCalledWith(2, {});
  });

  it("shows the history of a task on demand", async () => {
    vi.spyOn(client, "listAdminModels").mockResolvedValue(overview);
    const history = vi.spyOn(client, "fetchModelHistory").mockResolvedValue({
      versions: [
        setting({
          model_ref: "model.story.groq",
          source: "ui",
          created_by: "testadmin",
          is_modified: true,
        }),
        setting({ is_active: false, created_at: "2026-10-01T08:00:00Z" }),
      ],
    });
    renderModels();
    await openCard("Story");

    await userEvent.click(card("Story").getByRole("button", { name: "Verlauf" }));

    expect(history).toHaveBeenCalledWith("story");
    const items = await card("Story").findAllByRole("listitem");
    expect(items).toHaveLength(2);
    expect(items[0]).toHaveTextContent("Bearbeitet");
    expect(items[0]).toHaveTextContent("testadmin");
    expect(items[0]).toHaveTextContent("model.story.groq");
    expect(items[1]).toHaveTextContent("Original (TOML)");
  });
});
