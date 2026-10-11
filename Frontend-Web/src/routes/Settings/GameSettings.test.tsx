import { configureStore } from "@reduxjs/toolkit";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { afterEach, describe, expect, it, vi } from "vitest";
import { apiSlice } from "../../api/apiSlice";
import * as client from "../../api/client";
import { GameSettings } from "./GameSettings";

function renderGameSettings() {
  const store = configureStore({
    reducer: { [apiSlice.reducerPath]: apiSlice.reducer },
    middleware: (getDefaultMiddleware) => getDefaultMiddleware().concat(apiSlice.middleware),
  });
  render(
    <Provider store={store}>
      <GameSettings />
    </Provider>,
  );
}

describe("GameSettings", () => {
  afterEach(() => vi.restoreAllMocks());

  it("shows world tracking as switched on by default", async () => {
    vi.spyOn(client, "fetchWorldTracking").mockResolvedValue({
      enabled: true,
      updated_at: null,
      updated_by: null,
    });

    renderGameSettings();

    expect(await screen.findByRole("checkbox", { name: "Welt-Tracking" })).toBeChecked();
  });

  it("switches world tracking off and shows who changed it", async () => {
    vi.spyOn(client, "fetchWorldTracking")
      .mockResolvedValueOnce({ enabled: true, updated_at: null, updated_by: null })
      .mockResolvedValue({
        enabled: false,
        updated_at: "2026-10-11T12:00:00Z",
        updated_by: "testadmin",
      });
    const save = vi.spyOn(client, "saveWorldTracking").mockResolvedValue({
      enabled: false,
      updated_at: "2026-10-11T12:00:00Z",
      updated_by: "testadmin",
    });

    renderGameSettings();
    await userEvent.click(await screen.findByRole("checkbox", { name: "Welt-Tracking" }));

    expect(save).toHaveBeenCalledWith(false);
    expect(await screen.findByText(/testadmin/)).toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: "Welt-Tracking" })).not.toBeChecked();
  });
});
