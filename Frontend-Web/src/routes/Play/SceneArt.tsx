import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useCreateSceneImageMutation } from "../../api/apiSlice";
import type { CreateSceneImageRequest } from "../../api/types";
import { Button } from "../../components/Button/Button";
import { ErrorBanner } from "../../components/ErrorBanner/ErrorBanner";
import { SceneImageView } from "./SceneImageView";
import { useSceneImages, versionsInEffectAt } from "./sceneImages";
import "./SceneArt.css";

const POLL_MS = 2000;

/** The scene picture in the flowing-text view: the picture that is in effect
 *  at `turn` (the newest one without a turn), or a placeholder, plus the
 *  controls to generate a new one. */
export function SceneArt({ runId, name, turn }: { runId: string; name: string; turn?: number }) {
  const { images } = useSceneImages(runId);
  return (
    <>
      <SceneImageView
        runId={runId}
        versions={versionsInEffectAt(images, turn)}
        fallbackAlt={name}
        className="play-scene-art"
      />
      <SceneImageControls runId={runId} />
    </>
  );
}

/** Generating controls — rendered only where the backend reports the feature
 *  as enabled; a disabled or unreachable feature leaves nothing. Also polls
 *  while an image is pending, so it must be mounted exactly once per screen. */
export function SceneImageControls({ runId }: { runId: string }) {
  const { t } = useTranslation();
  const { capabilities, enabled, images, refetch } = useSceneImages(runId);
  const latest = images[0];
  const latestPending = latest?.status === "pending";
  useEffect(() => {
    if (!latestPending) {
      return;
    }
    const timer = setInterval(() => void refetch(), POLL_MS);
    return () => clearInterval(timer);
  }, [latestPending, refetch]);

  const [createSceneImage, createState] = useCreateSceneImageMutation();
  const [model, setModel] = useState<string | undefined>(undefined);
  const [refine, setRefine] = useState<boolean | undefined>(undefined);
  const [strength, setStrength] = useState<number | undefined>(undefined);

  if (!enabled || !capabilities) {
    return null;
  }

  const pending = createState.isLoading || latestPending;
  const effectiveRefine = refine ?? capabilities.default_refine;
  const effectiveStrength = strength ?? capabilities.default_refine_strength ?? 0.35;
  const effectiveModel = model ?? capabilities.default_model ?? "";

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
  );
}
