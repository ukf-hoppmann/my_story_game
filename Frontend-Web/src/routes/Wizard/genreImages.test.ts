import { describe, expect, it } from "vitest";
import { getGenreImageUrl } from "./genreImages";

describe("getGenreImageUrl", () => {
  it("resolves every catalog genre id to its preview image", () => {
    expect(getGenreImageUrl("dark_fantasy")).toBe("/assets/story-wizard/dark_fantasy.png");
    expect(getGenreImageUrl("fantasy")).toBe("/assets/story-wizard/fantasy.png");
    expect(getGenreImageUrl("science_fiction")).toBe("/assets/story-wizard/science_fiction.png");
    expect(getGenreImageUrl("mystery")).toBe("/assets/story-wizard/mystery.png");
    expect(getGenreImageUrl("steam_punk")).toBe("/assets/story-wizard/steam_punk.png");
  });

  it("returns undefined when no genre is selected yet", () => {
    expect(getGenreImageUrl("")).toBeUndefined();
    expect(getGenreImageUrl(undefined)).toBeUndefined();
  });

  it("returns undefined for a catalog id without an asset yet", () => {
    expect(getGenreImageUrl("unmapped_future_genre")).toBeUndefined();
  });
});
