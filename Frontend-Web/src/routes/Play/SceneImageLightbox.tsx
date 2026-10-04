import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import type { SceneImage } from "../../api/types";
import "./SceneImageLightbox.css";

/** The scene picture at full size, with the generation details (prompts, model,
 *  seed) folded away underneath for debugging. Closes on Escape or a click on
 *  the backdrop. */
export function SceneImageLightbox({
  image,
  imageUrl,
  alt,
  onClose,
}: {
  image: SceneImage;
  imageUrl: string;
  alt: string;
  onClose: () => void;
}) {
  const { t } = useTranslation();

  useEffect(() => {
    function handleKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onClose();
      }
    }
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [onClose]);

  const refine = image.refine
    ? t("play.sceneImage.debug.refineOn", {
        model: image.refine_model ?? "—",
        strength: image.refine_strength.toFixed(2),
      })
    : t("play.sceneImage.debug.refineOff");

  return (
    <div className="scene-lightbox" onClick={onClose}>
      <div
        className="scene-lightbox__body"
        role="dialog"
        aria-modal="true"
        aria-label={alt}
        onClick={(event) => event.stopPropagation()}
      >
        <button
          type="button"
          className="scene-lightbox__close"
          aria-label={t("play.sceneImage.close")}
          onClick={onClose}
        >
          ×
        </button>
        <img className="scene-lightbox__img" src={imageUrl} alt={alt} />
        <details className="scene-lightbox__debug">
          <summary>{t("play.sceneImage.debug.summary")}</summary>
          <dl>
            <dt>{t("play.sceneImage.debug.prompt")}</dt>
            <dd>{image.prompt ?? "—"}</dd>
            <dt>{t("play.sceneImage.debug.compactPrompt")}</dt>
            <dd>{image.compact_prompt ?? "—"}</dd>
            <dt>{t("play.sceneImage.debug.model")}</dt>
            <dd>{image.model ?? "—"}</dd>
            <dt>{t("play.sceneImage.debug.refine")}</dt>
            <dd>{refine}</dd>
            <dt>{t("play.sceneImage.debug.seed")}</dt>
            <dd>{image.seed}</dd>
            <dt>{t("play.sceneImage.debug.size")}</dt>
            <dd>
              {image.width} × {image.height}
            </dd>
          </dl>
        </details>
      </div>
    </div>
  );
}
