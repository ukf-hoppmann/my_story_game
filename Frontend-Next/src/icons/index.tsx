import type { SVGProps } from "react";

/**
 * Small line-icon set shared by the UI primitives, matching the visual
 * language established in the approved mockups. New icons get added here as
 * later roadmap steps (nav rail, wizard, sidebar panels) need them.
 */

export function ArrowRightIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} {...props}>
      <path d="M5 12h14M13 6l6 6-6 6" />
    </svg>
  );
}

export function ImagePlaceholderIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.6} {...props}>
      <rect x="3.5" y="4.5" width="17" height="15" rx="1.6" />
      <circle cx="8.3" cy="9.3" r="1.6" />
      <path d="M4 16.5l4.8-4.8 3.2 3.2 3.7-4.6 5 6.2" />
    </svg>
  );
}

export function PersonIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.6} {...props}>
      <circle cx="12" cy="8.5" r="3.3" />
      <path d="M5.2 19.5c1-3.6 3.4-5.6 6.8-5.6s5.8 2 6.8 5.6" />
    </svg>
  );
}
