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

export function PlusIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} {...props}>
      <path d="M12 5v14M5 12h14" />
    </svg>
  );
}

export function TrashIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.6} {...props}>
      <path d="M5 7h14M9.5 7V5a1.5 1.5 0 0 1 1.5-1.5h2A1.5 1.5 0 0 1 14.5 5v2M7 7l1 12.5A1.5 1.5 0 0 0 9.5 21h5a1.5 1.5 0 0 0 1.5-1.5L17 7" />
    </svg>
  );
}

export function CompassIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.4} {...props}>
      <circle cx="12" cy="12" r="9.2" />
      <path d="M15.2 8.8 l-4.4 2 -2 4.4 4.4-2z" />
    </svg>
  );
}

export function SignInIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7} {...props}>
      <circle cx="12" cy="8" r="3.4" />
      <path d="M4.8 19.8c1.1-4 3.7-6.2 7.2-6.2s6.1 2.2 7.2 6.2" />
    </svg>
  );
}

export function BookIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.6} {...props}>
      <path d="M4 5.5c2-1 5-1 7 0v13c-2-1-5-1-7 0z" />
      <path d="M20 5.5c-2-1-5-1-7 0v13c2-1 5-1 7 0z" />
    </svg>
  );
}

export function DarkFantasyIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.6} {...props}>
      <path d="M12 3v3M12 18v3M4.2 12H3M21 12h-1.2M6 6l1.6 1.6M16.4 16.4 18 18M18 6l-1.6 1.6M7.6 16.4 6 18" />
      <circle cx="12" cy="12" r="3.6" />
    </svg>
  );
}

export function FantasyIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.6} {...props}>
      <path d="M12 21s-7-4.4-9.4-9.2C1.2 8.3 3.4 5 6.8 5c2.1 0 3.6 1.2 5.2 3 1.6-1.8 3.1-3 5.2-3 3.4 0 5.6 3.3 4.2 6.8C19 16.6 12 21 12 21z" />
    </svg>
  );
}

export function SciFiIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.6} {...props}>
      <path d="M12 2.5c2.7 2.6 4 6 4 9.7 0 2.4-.6 4.4-1.4 6l-2.6 3.3-2.6-3.3c-.8-1.6-1.4-3.6-1.4-6 0-3.7 1.3-7.1 4-9.7z" />
      <circle cx="12" cy="10.5" r="1.7" />
      <path d="M8 18.5 5.5 21M16 18.5 18.5 21" />
    </svg>
  );
}

export function MysteryIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.6} {...props}>
      <circle cx="10.5" cy="10.5" r="6.5" />
      <path d="M20 20l-4.8-4.8" />
    </svg>
  );
}

export function SteampunkIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.6} {...props}>
      <circle cx="12" cy="12" r="3.2" />
      <path d="M12 3.5v2.4M12 18.1v2.4M20.5 12h-2.4M5.9 12H3.5M17.8 6.2l-1.7 1.7M7.9 16.1l-1.7 1.7M17.8 17.8l-1.7-1.7M7.9 7.9 6.2 6.2" />
    </svg>
  );
}
