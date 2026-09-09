/**
 * Turns a prompt-profile option id (e.g. "dark_fantasy") into a display
 * label ("Dark Fantasy"). The catalog's `description` field is a full
 * sentence meant for help text, not a button label — this is what badges
 * show instead.
 */
export function formatOptionLabel(id: string): string {
  return id
    .split("_")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}
