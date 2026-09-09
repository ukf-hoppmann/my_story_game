import type { HTMLAttributes, ReactNode } from "react";
import { ImagePlaceholderIcon } from "../../icons";
import "./ImageSlot.css";

export interface ImageSlotProps extends HTMLAttributes<HTMLDivElement> {
  /** Once a real image URL exists (scene illustration, character portrait,
   *  ...), pass it here — the slot swaps to a plain <img> with no other
   *  structural change needed at the call site. */
  imageUrl?: string;
  alt?: string;
  /** "rect" for scene illustrations, "circle" for character portraits. */
  shape?: "rect" | "circle";
  /** Placeholder icon shown when no image is set yet (defaults to a generic
   *  image icon; pass e.g. a person icon for portrait slots). */
  placeholderIcon?: ReactNode;
  /** Placeholder label. Only rendered for the "rect" shape — the "circle"
   *  shape has no room for text. */
  label?: string;
}

/**
 * The reusable "image not generated yet" placeholder pattern established in
 * the approved mockups (scene illustrations, character portraits). Renders a
 * clearly-marked placeholder until `imageUrl` is supplied, at which point it
 * renders the real image with the exact same layout footprint.
 */
export function ImageSlot({
  imageUrl,
  alt = "",
  shape = "rect",
  placeholderIcon,
  label = "Platzhalter · Bild folgt",
  className,
  ...rest
}: ImageSlotProps) {
  const classes = ["image-slot", `image-slot--${shape}`, className]
    .filter(Boolean)
    .join(" ");

  if (imageUrl) {
    return (
      <div className={classes} {...rest}>
        <img className="image-slot__img" src={imageUrl} alt={alt} />
      </div>
    );
  }

  return (
    <div className={classes} {...rest}>
      <span className="image-slot__note">
        {placeholderIcon ?? <ImagePlaceholderIcon />}
        <span>{label}</span>
      </span>
    </div>
  );
}
