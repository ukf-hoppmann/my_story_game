import { configureStore } from "@reduxjs/toolkit";
import { render, screen } from "@testing-library/react";
import { Provider } from "react-redux";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { apiSlice } from "../api/apiSlice";
import * as client from "../api/client";
import { routes } from "./routes";

function buildStore() {
  return configureStore({
    reducer: { [apiSlice.reducerPath]: apiSlice.reducer },
    middleware: (getDefaultMiddleware) => getDefaultMiddleware().concat(apiSlice.middleware),
  });
}

function renderAt(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  render(
    <Provider store={buildStore()}>
      <RouterProvider router={router} />
    </Provider>,
  );
}

describe("routes", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the Landing page at /", () => {
    renderAt("/");

    expect(
      screen.getByRole("heading", { name: "Geschichten, die deinen Entscheidungen folgen." }),
    ).toBeInTheDocument();
  });

  it("renders the Bibliothek at /library", async () => {
    vi.spyOn(client, "listRuns").mockResolvedValue({ runs: [] });

    renderAt("/library");

    expect(await screen.findByRole("heading", { name: "Deine Geschichten" })).toBeInTheDocument();
  });

  it("renders the Wizard at /new", async () => {
    vi.spyOn(client, "fetchPromptProfileCatalog").mockResolvedValue({
      package_id: "story.base",
      package_version: "1",
      categories: [],
    });

    renderAt("/new");

    expect(await screen.findByRole("heading", { name: "Welt & Prämisse" })).toBeInTheDocument();
  });

  it("renders the Play placeholder at /stories/:runId", () => {
    renderAt("/stories/11111111-1111-1111-1111-111111111111");

    expect(screen.getByText("Play-Screen folgt in Schritt 9/10.")).toBeInTheDocument();
  });
});
