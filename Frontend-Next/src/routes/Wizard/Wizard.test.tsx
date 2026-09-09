import { configureStore } from "@reduxjs/toolkit";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { afterEach, describe, expect, it, vi } from "vitest";
import { apiSlice } from "../../api/apiSlice";
import * as client from "../../api/client";
import type { PromptProfileCatalog } from "../../api/types";
import { Wizard } from "./Wizard";

function buildStore() {
  return configureStore({
    reducer: { [apiSlice.reducerPath]: apiSlice.reducer },
    middleware: (getDefaultMiddleware) => getDefaultMiddleware().concat(apiSlice.middleware),
  });
}

function renderWizard() {
  render(
    <Provider store={buildStore()}>
      <Wizard />
    </Provider>,
  );
}

const catalog: PromptProfileCatalog = {
  package_id: "story.base",
  package_version: "1",
  categories: [
    {
      id: "genre",
      default_option_id: "dark_fantasy",
      options: [
        { id: "dark_fantasy", description: "Bedrohliche Fantasy mit moralischen Grauzonen." },
        { id: "fantasy", description: "Klassische Fantasy." },
        { id: "science_fiction", description: "Zukunft, Technik, große Fragen." },
      ],
    },
    {
      id: "tone",
      default_option_id: "balanced",
      options: [
        { id: "balanced", description: "Ausgewogen." },
        { id: "dark", description: "Düster." },
      ],
    },
  ],
};

describe("Wizard", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders genre and tone badges from the live catalog, with the default preselected", async () => {
    vi.spyOn(client, "fetchPromptProfileCatalog").mockResolvedValue(catalog);
    renderWizard();

    const darkFantasy = await screen.findByRole("button", { name: "Dark Fantasy" });
    expect(darkFantasy).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Fantasy" })).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByRole("button", { name: "Balanced" })).toHaveAttribute("aria-pressed", "true");
  });

  it("selects a different genre when its badge is clicked", async () => {
    vi.spyOn(client, "fetchPromptProfileCatalog").mockResolvedValue(catalog);
    renderWizard();

    const sciFi = await screen.findByRole("button", { name: "Science Fiction" });
    await userEvent.click(sciFi);

    expect(sciFi).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Dark Fantasy" })).toHaveAttribute("aria-pressed", "false");
  });

  it("updates the premise character counter as the user types", async () => {
    vi.spyOn(client, "fetchPromptProfileCatalog").mockResolvedValue(catalog);
    renderWizard();
    await screen.findByRole("button", { name: "Dark Fantasy" });

    const premise = screen.getByLabelText("Prämisse");
    await userEvent.type(premise, "Ein Kurier verschwindet spurlos.");

    expect(screen.getByText("32 / 500")).toBeInTheDocument();
  });

  it("shows an error message when the catalog fails to load", async () => {
    vi.spyOn(client, "fetchPromptProfileCatalog").mockRejectedValue(new Error("network down"));
    renderWizard();

    expect(
      await screen.findByText("Optionen konnten nicht geladen werden. Bitte versuche es erneut."),
    ).toBeInTheDocument();
  });
});
