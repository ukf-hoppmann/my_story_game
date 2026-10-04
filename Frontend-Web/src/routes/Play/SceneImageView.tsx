import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { fetchSceneImageBlob } from "../../api/client";
import type { SceneImage } from "../../api/types";
import { ImageSlot } from "../../components/ImageSlot/ImageSlot";
import { SceneImageLightbox } from "./SceneImageLightbox";
import "./SceneArt.css";

/** One turn's picture: the newest version first, with arrows to step through
 *  older versions when there are several, and a click to enlarge. With no
 *  versions it shows the placeholder (or nothing when `hideWhenEmpty`). */
export function SceneImageView({
  runId,
  versions,
  fallbackAlt,
  className,
  hideWhenEmpty = false,
}: {
  runId: string;
  /** Newest first. */
  versions: SceneImage[];
  fallbackAlt: string;
  className?: string;
  hideWhenEmpty?: boolean;
}) {
  const { t } = useTranslation();
  // The user's pick only counts while it was made against the same newest
  // version; a freshly generated one takes over again.
  const newestId = versions[0]?.image_id;
  const [picked, setPicked] = useState<{ base: string; id: string } | undefined>(undefined);
  const selected =
    picked !== undefined && picked.base === newestId
      ? (versions.find((image) => image.image_id === picked.id) ?? versions[0])
      : versions[0];
  const index = selected ? versions.indexOf(selected) : 0;

  const imageUrl = useImageObjectUrl(runId, selected?.image_id);
  const [enlarged, setEnlarged] = useState(false);
  const alt = selected ? t("play.sceneImage.alt", { turn: selected.turn_sequence }) : fallbackAlt;

  function step(delta: number) {
    const next = versions[index + delta];
    if (next && newestId) {
      setPicked({ base: newestId, id: next.image_id });
    }
  }

  if (!selected && hideWhenEmpty) {
    return null;
  }

  return (
    <>
      {selected && imageUrl ? (
        <button
          type="button"
          className="scene-art-zoom"
          aria-label={t("play.sceneImage.enlarge")}
          onClick={() => setEnlarged(true)}
        >
          <ImageSlot className={className} imageUrl={imageUrl} alt={alt} />
        </button>
      ) : (
        <ImageSlot className={className} label={t("play.sceneArtPlaceholder")} alt={alt} />
      )}
      {versions.length > 1 && (
        <div className="scene-art-versions">
          <button
            type="button"
            aria-label={t("play.sceneImage.olderVersion")}
            disabled={index >= versions.length - 1}
            onClick={() => step(1)}
          >
            ‹
          </button>
          <span>{t("play.sceneImage.version", { current: versions.length - index, total: versions.length })}</span>
          <button
            type="button"
            aria-label={t("play.sceneImage.newerVersion")}
            disabled={index <= 0}
            onClick={() => step(-1)}
          >
            ›
          </button>
        </div>
      )}
      {enlarged && selected && imageUrl && (
        <SceneImageLightbox
          image={selected}
          imageUrl={imageUrl}
          alt={alt}
          onClose={() => setEnlarged(false)}
        />
      )}
    </>
  );
}

/** Loads one image's bytes (needs the auth header) into an object URL and
 *  releases it when the image changes or the component unmounts. */
function useImageObjectUrl(runId: string, imageId: string | undefined): string | undefined {
  const [loaded, setLoaded] = useState<{ imageId: string; url: string } | undefined>(undefined);
  useEffect(() => {
    if (!imageId) {
      return;
    }
    let cancelled = false;
    let objectUrl: string | undefined;
    fetchSceneImageBlob(runId, imageId)
      .then((blob) => {
        if (cancelled) {
          return;
        }
        objectUrl = URL.createObjectURL(blob);
        setLoaded({ imageId, url: objectUrl });
      })
      .catch(() => {
        // A missing picture just leaves the placeholder; the failure is not
        // worth a banner on top of a story that is otherwise playable.
      });
    return () => {
      cancelled = true;
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
      }
    };
  }, [runId, imageId]);
  return loaded !== undefined && loaded.imageId === imageId ? loaded.url : undefined;
}
