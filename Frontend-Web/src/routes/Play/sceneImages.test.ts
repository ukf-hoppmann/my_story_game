import { describe, expect, it } from "vitest";
import type { SceneImage } from "../../api/types";
import { versionsForTurn, versionsInEffectAt } from "./sceneImages";

function image(id: string, turn: number, status: SceneImage["status"] = "ready"): SceneImage {
  return {
    image_id: id,
    run_id: "run",
    turn_sequence: turn,
    status,
    model: null,
    refine: false,
    refine_model: null,
    refine_strength: 0.35,
    width: 1,
    height: 1,
    seed: 1,
    prompt: null,
    compact_prompt: null,
    error_message: null,
    created_at: "2026-10-05T00:00:00Z",
    completed_at: null,
  };
}

// Newest first, as the API returns them.
const IMAGES = [image("d", 5), image("c", 3, "failed"), image("b", 3), image("a", 3), image("z", 0)];

describe("versionsForTurn", () => {
  it("returns only the ready versions of exactly that turn, newest first", () => {
    expect(versionsForTurn(IMAGES, 3).map((i) => i.image_id)).toEqual(["b", "a"]);
    expect(versionsForTurn(IMAGES, 4)).toEqual([]);
  });
});

describe("versionsInEffectAt", () => {
  it("picks the most recent turn at or before the given turn", () => {
    expect(versionsInEffectAt(IMAGES, 4).map((i) => i.image_id)).toEqual(["b", "a"]);
    expect(versionsInEffectAt(IMAGES, 2).map((i) => i.image_id)).toEqual(["z"]);
  });

  it("uses the newest turn without a turn", () => {
    expect(versionsInEffectAt(IMAGES).map((i) => i.image_id)).toEqual(["d"]);
  });

  it("is empty when nothing is in effect yet", () => {
    expect(versionsInEffectAt([image("a", 3)], 2)).toEqual([]);
  });
});
