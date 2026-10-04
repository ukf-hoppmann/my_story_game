import { configureStore } from "@reduxjs/toolkit";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { apiSlice } from "../../api/apiSlice";
import * as client from "../../api/client";
import { ApiError } from "../../api/client";
import type { SceneImage, SceneImageCapabilities } from "../../api/types";
import { SceneArt } from "./SceneArt";

const RUN_ID = "11111111-1111-1111-1111-111111111111";

const ENABLED: SceneImageCapabilities = {
  enabled: true,
  models: [{ name: "z-image-turbo" }],
  refine_models: [{ name: "juggernaut-xl-ragnarok" }],
  model_listing_failed: false,
  default_model: "z-image-turbo",
  default_refine: false,
  default_refine_model: "juggernaut-xl-ragnarok",
  default_refine_strength: 0.35,
  min_refine_strength: 0.1,
  max_refine_strength: 0.8,
  turn_window: 3,
};

function image(overrides: Partial<SceneImage> = {}): SceneImage {
  return {
    image_id: "22222222-2222-2222-2222-222222222222",
    run_id: RUN_ID,
    turn_sequence: 2,
    status: "ready",
    model: "z-image-turbo",
    refine: false,
    refine_model: null,
    refine_strength: 0.35,
    width: 1024,
    height: 1024,
    seed: 7,
    prompt: "A tavern.",
    compact_prompt: null,
    error_message: null,
    created_at: "2026-10-04T12:00:00Z",
    completed_at: "2026-10-04T12:00:05Z",
    ...overrides,
  };
}

function renderArt(turn?: number) {
  const store = configureStore({
    reducer: { [apiSlice.reducerPath]: apiSlice.reducer },
    middleware: (getDefaultMiddleware) => getDefaultMiddleware().concat(apiSlice.middleware),
  });
  render(
    <Provider store={store}>
      <SceneArt runId={RUN_ID} name="Die Schatten von Auenfall" turn={turn} />
    </Provider>,
  );
}

describe("SceneArt", () => {
  beforeEach(() => {
    vi.stubGlobal("URL", Object.assign(URL, {
      createObjectURL: vi.fn(() => "blob:scene"),
      revokeObjectURL: vi.fn(),
    }));
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows only the placeholder when the feature is disabled", async () => {
    const capabilities = vi
      .spyOn(client, "fetchSceneImageCapabilities")
      .mockResolvedValue({ ...ENABLED, enabled: false });
    const list = vi.spyOn(client, "listSceneImages");
    renderArt();

    expect(await screen.findByText("Platzhalter · Szenenbild folgt")).toBeInTheDocument();
    await waitFor(() => expect(capabilities).toHaveBeenCalled());
    expect(screen.queryByRole("button", { name: /Szenenbild erzeugen/ })).not.toBeInTheDocument();
    expect(list).not.toHaveBeenCalled();
  });

  it("keeps the placeholder and hides the controls when the capability check fails", async () => {
    vi.spyOn(client, "fetchSceneImageCapabilities").mockRejectedValue(
      new ApiError(500, { error: "boom", detail: "kaputt" }),
    );
    renderArt();

    expect(await screen.findByText("Platzhalter · Szenenbild folgt")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Szenenbild erzeugen/ })).not.toBeInTheDocument();
  });

  it("starts a generation with the server defaults when nothing was changed", async () => {
    vi.spyOn(client, "fetchSceneImageCapabilities").mockResolvedValue(ENABLED);
    vi.spyOn(client, "listSceneImages").mockResolvedValue({ images: [] });
    const create = vi
      .spyOn(client, "createSceneImage")
      .mockResolvedValue(image({ status: "pending" }));
    renderArt();

    await userEvent.click(await screen.findByRole("button", { name: /Szenenbild erzeugen/ }));

    expect(create).toHaveBeenCalledWith(RUN_ID, {});
  });

  it("sends the refine choice and strength when the player sets them", async () => {
    vi.spyOn(client, "fetchSceneImageCapabilities").mockResolvedValue(ENABLED);
    vi.spyOn(client, "listSceneImages").mockResolvedValue({ images: [] });
    const create = vi
      .spyOn(client, "createSceneImage")
      .mockResolvedValue(image({ status: "pending" }));
    renderArt();
    await screen.findByRole("button", { name: /Szenenbild erzeugen/ });

    await userEvent.click(screen.getByText("Bildoptionen"));
    await userEvent.click(screen.getByLabelText("Mit Verfeinerung"));
    await userEvent.click(screen.getByRole("button", { name: /Szenenbild erzeugen/ }));

    expect(create).toHaveBeenCalledWith(RUN_ID, { refine: true });
  });

  it("disables the button and says so while an image is pending", async () => {
    vi.spyOn(client, "fetchSceneImageCapabilities").mockResolvedValue(ENABLED);
    vi.spyOn(client, "listSceneImages").mockResolvedValue({
      images: [image({ status: "pending", completed_at: null })],
    });
    renderArt();

    const button = await screen.findByRole("button", { name: /Bild wird erzeugt/ });
    expect(button).toBeDisabled();
  });

  it("polls while an image is pending and shows it once it is ready", async () => {
    vi.spyOn(client, "fetchSceneImageCapabilities").mockResolvedValue(ENABLED);
    const list = vi
      .spyOn(client, "listSceneImages")
      .mockResolvedValueOnce({ images: [image({ status: "pending", completed_at: null })] })
      .mockResolvedValue({ images: [image()] });
    vi.spyOn(client, "fetchSceneImageBlob").mockResolvedValue(new Blob(["png"]));
    renderArt();
    await screen.findByRole("button", { name: /Bild wird erzeugt/ });

    expect(await screen.findByRole("img", { name: "Szenenbild zu Zug 2" }, { timeout: 4000 })).toBeInTheDocument();
    expect(list.mock.calls.length).toBeGreaterThanOrEqual(2);
    expect(screen.getByRole("button", { name: /Szenenbild erzeugen/ })).toBeEnabled();
  });

  it("shows the latest finished image, loaded with the auth header", async () => {
    vi.spyOn(client, "fetchSceneImageCapabilities").mockResolvedValue(ENABLED);
    vi.spyOn(client, "listSceneImages").mockResolvedValue({ images: [image()] });
    const blob = vi
      .spyOn(client, "fetchSceneImageBlob")
      .mockResolvedValue(new Blob(["png"], { type: "image/png" }));
    renderArt();

    const picture = await screen.findByRole("img", { name: "Szenenbild zu Zug 2" });

    expect(picture).toHaveAttribute("src", "blob:scene");
    expect(blob).toHaveBeenCalledWith(RUN_ID, "22222222-2222-2222-2222-222222222222");
  });

  it("shows why the latest generation failed", async () => {
    vi.spyOn(client, "fetchSceneImageCapabilities").mockResolvedValue(ENABLED);
    vi.spyOn(client, "listSceneImages").mockResolvedValue({
      images: [image({ status: "failed", error_message: "Modal ist nicht erreichbar." })],
    });
    renderArt();

    expect(
      await screen.findByText("Das Szenenbild konnte nicht erzeugt werden: Modal ist nicht erreichbar."),
    ).toBeInTheDocument();
  });

  it("shows the backend's message when starting a generation fails", async () => {
    vi.spyOn(client, "fetchSceneImageCapabilities").mockResolvedValue(ENABLED);
    vi.spyOn(client, "listSceneImages").mockResolvedValue({ images: [] });
    vi.spyOn(client, "createSceneImage").mockRejectedValue(
      new ApiError(422, { error: "scene_image_invalid_options", detail: "Stärke ungültig." }),
    );
    renderArt();

    await userEvent.click(await screen.findByRole("button", { name: /Szenenbild erzeugen/ }));

    expect(await screen.findByText(/Stärke ungültig\./)).toBeInTheDocument();
  });
  it("opens the image enlarged on click, with the collapsed prompt details, and closes it again", async () => {
    vi.spyOn(client, "fetchSceneImageCapabilities").mockResolvedValue(ENABLED);
    vi.spyOn(client, "listSceneImages").mockResolvedValue({
      images: [image({ prompt: "A tavern at dusk.", compact_prompt: "tavern, dusk" })],
    });
    vi.spyOn(client, "fetchSceneImageBlob").mockResolvedValue(new Blob(["png"]));
    renderArt();

    await userEvent.click(await screen.findByRole("button", { name: /Szenenbild vergrößern/ }));

    const dialog = screen.getByRole("dialog");
    expect(dialog).toBeInTheDocument();
    const details = screen.getByText("Prompt (Debug)").closest("details");
    expect(details).not.toHaveAttribute("open");
    expect(dialog).toHaveTextContent("A tavern at dusk.");
    expect(dialog).toHaveTextContent("tavern, dusk");
    expect(dialog).toHaveTextContent("z-image-turbo");

    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("offers no enlarge button while there is no ready image", async () => {
    vi.spyOn(client, "fetchSceneImageCapabilities").mockResolvedValue(ENABLED);
    vi.spyOn(client, "listSceneImages").mockResolvedValue({ images: [] });
    renderArt();

    await screen.findByRole("button", { name: /Szenenbild erzeugen/ });
    expect(screen.queryByRole("button", { name: /Szenenbild vergrößern/ })).not.toBeInTheDocument();
  });

  it("shows the picture in effect at the given turn and steps through its versions", async () => {
    vi.spyOn(client, "fetchSceneImageCapabilities").mockResolvedValue(ENABLED);
    vi.spyOn(client, "listSceneImages").mockResolvedValue({
      images: [
        image({ image_id: "c", turn_sequence: 5 }),
        image({ image_id: "b", turn_sequence: 2 }),
        image({ image_id: "a", turn_sequence: 2 }),
      ],
    });
    const blob = vi.spyOn(client, "fetchSceneImageBlob").mockResolvedValue(new Blob(["x"]));
    renderArt(3);

    expect(await screen.findByRole("img", { name: "Szenenbild zu Zug 2" })).toBeInTheDocument();
    await waitFor(() => expect(blob).toHaveBeenCalledWith(RUN_ID, "b"));
    expect(screen.getByText("Version 2 von 2")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Ältere Version" }));

    await waitFor(() => expect(blob).toHaveBeenCalledWith(RUN_ID, "a"));
    expect(screen.getByText("Version 1 von 2")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ältere Version" })).toBeDisabled();
  });
});
