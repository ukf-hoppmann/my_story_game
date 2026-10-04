import {
  useListSceneImagesQuery,
  useSceneImageCapabilitiesQuery,
} from "../../api/apiSlice";
import type { SceneImage } from "../../api/types";

/** Capabilities and the run's images (newest first). Pure reads — RTK Query
 *  dedupes the requests, so any number of components may call this. */
export function useSceneImages(runId: string) {
  const capabilitiesQuery = useSceneImageCapabilitiesQuery();
  const capabilities = capabilitiesQuery.data;
  const enabled = capabilities?.enabled === true;
  const list = useListSceneImagesQuery(runId, { skip: !enabled });
  return { capabilities, enabled, images: list.data ?? NO_IMAGES, refetch: list.refetch };
}

const NO_IMAGES: SceneImage[] = [];

/** The ready versions generated for exactly this turn, newest first. */
export function versionsForTurn(images: SceneImage[], turn: number): SceneImage[] {
  return images.filter((image) => image.status === "ready" && image.turn_sequence === turn);
}

/** The ready versions of the most recent turn at or before `turn` that has a
 *  picture, newest first — the picture that is "still on screen" at `turn`.
 *  Without a turn, the newest turn that has one. */
export function versionsInEffectAt(images: SceneImage[], turn?: number): SceneImage[] {
  const ready = images.filter(
    (image) => image.status === "ready" && (turn === undefined || image.turn_sequence <= turn),
  );
  if (ready.length === 0) {
    return [];
  }
  const sequence = Math.max(...ready.map((image) => image.turn_sequence));
  return ready.filter((image) => image.turn_sequence === sequence);
}
