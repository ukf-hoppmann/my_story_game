/**
 * Fixed illustrative image per genre, shown in the Wizard's preview slot
 * while a genre is selected. These are static design assets — one per
 * catalog genre option — not per-story generated content, so a plain
 * lookup table is all that's needed (no backend, no config file).
 */
const GENRE_IMAGES: Record<string, string> = {
  dark_fantasy: "/assets/story-wizard/dark_fantasy.png",
  fantasy: "/assets/story-wizard/fantasy.png",
  science_fiction: "/assets/story-wizard/science_fiction.png",
  mystery: "/assets/story-wizard/mystery.png",
  steam_punk: "/assets/story-wizard/steam_punk.png",
};

/**
 * Resolves a genre id to its preview image URL. Returns `undefined` for an
 * empty/unknown id (no genre selected yet, or a catalog id without an
 * asset yet) so the caller falls back to the ImageSlot placeholder.
 */
export function getGenreImageUrl(genreId?: string): string | undefined {
  if (!genreId) {
    return undefined;
  }
  return GENRE_IMAGES[genreId];
}
