import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  useCreateSceneImageMutation,
  useListSceneImagesQuery,
  useSceneImageCapabilitiesQuery,
} from "../../api/apiSlice";
import { fetchSceneImageBlob } from "../../api/client";
import type { CreateSceneImageRequest } from "../../api/types";
import { Button } from "../../components/Button/Button";
import { ErrorBanner } from "../../components/ErrorBanner/ErrorBanner";
import { ImageSlot } from "../../components/ImageSlot/ImageSlot";
import "./SceneArt.css";

const POLL_MS = 2000;

/** The scene picture: a placeholder (or the latest generated image) plus, only
 *  where the backend reports the feature as enabled, the controls to generate
 *  a new one. A disabled or unreachable feature leaves just the placeholder. */
export function SceneArt({ runId, name }: { runId: string; name: string }) {
  const { t } = useTranslation();
  const capabilitiesQuery = useSceneImageCapabilitiesQuery();
  const capabilities = capabilitiesQuery.data;
  const enabled = capabilities?.enabled === true;

  const list = useListSceneImagesQuery(runId, { skip: !enabled });
  const latest = list.data?.[0];
  const latestReady = list.data?.find((image) => image.status === "ready");
  const latestPending = latest?.status === "pending";
  const { refetch: refetchImages } = list;
  useEffect(() => {
    if (!latestPending) {
      return;
    }
    const timer = setInterval(() => void refetchImages(), POLL_MS);
    return () => clearInterval(timer);
  }, [latestPending, refetchImages]);

  const [createSceneImage, createState] = useCreateSceneImageMutation();
  const [model, setModel] = useState<string | undefined>(undefined);
  const [refine, setRefine] = useState<boolean | undefined>(undefined);
  const [strength, setStrength] = useState<number | undefined>(undefined);

  const imageUrl = useImageObjectUrl(runId, latestReady?.image_id);
  const pending = createState.isLoading || latest?.status === "pending";

  const effectiveRefine = refine ?? capabilities?.default_refine ?? false;
  const effectiveStrength = strength ?? capabilities?.default_refine_strength ?? 0.35;
  const effectiveModel = model ?? capabilities?.default_model ?? "";

  function handleGenerate() {
    const payload: CreateSceneImageRequest = {};
    if (model !== undefined) {
      payload.model = model;
    }
    if (refine !== undefined) {
      payload.refine = refine;
    }
    if (strength !== undefined) {
      payload.refine_strength = strength;
    }
    void createSceneImage({ runId, payload });
  }

  return (
    <>
      <ImageSlot
        className="play-scene-art"
        label={t("play.sceneArtPlaceholder")}
        imageUrl={imageUrl}
        alt={latestReady ? t("play.sceneImage.alt", { turn: latestReady.turn_sequence }) : name}
      />
      {enabled && capabilities && (
        <div className="scene-art-controls">
          <Button variant="ghost" disabled={pending} onClick={handleGenerate}>
            {pending ? t("play.sceneImage.generating") : t("play.sceneImage.generate")}
          </Button>
          <details className="scene-art-options">
            <summary>{t("play.sceneImage.options")}</summary>
            {capabilities.model_listing_failed && (
              <p className="scene-art-note">{t("play.sceneImage.modelListingFailed")}</p>
            )}
            {capabilities.models.length > 1 && (
              <label className="scene-art-field">
                {t("play.sceneImage.model")}
                <select value={effectiveModel} onChange={(event) => setModel(event.target.value)}>
                  {capabilities.models.map((option) => (
                    <option key={option.name} value={option.name}>
                      {option.name}
                    </option>
                  ))}
                </select>
              </label>
            )}
            {capabilities.refine_models.length > 0 && (
              <>
                <label className="scene-art-field scene-art-field--inline">
                  <input
                    type="checkbox"
                    checked={effectiveRefine}
                    onChange={(event) => setRefine(event.target.checked)}
                  />
                  {t("play.sceneImage.refine")}
                </label>
                {effectiveRefine && (
                  <label className="scene-art-field">
                    {t("play.sceneImage.refineStrength", { value: effectiveStrength.toFixed(2) })}
                    <input
                      type="range"
                      min={capabilities.min_refine_strength ?? 0.1}
                      max={capabilities.max_refine_strength ?? 0.8}
                      step={0.05}
                      value={effectiveStrength}
                      onChange={(event) => setStrength(Number(event.target.value))}
                    />
                  </label>
                )}
              </>
            )}
          </details>
          <ErrorBanner
            error={createState.error}
            fallbackKey="play.sceneImage.createError"
            className="scene-art-error"
          />
          {latest?.status === "failed" && (
            <p className="scene-art-error">
              {latest.error_message
                ? t("play.sceneImage.failed", { message: latest.error_message })
                : t("play.sceneImage.failedFallback")}
            </p>
          )}
        </div>
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
