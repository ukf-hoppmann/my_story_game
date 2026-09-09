import type { ButtonHTMLAttributes, ReactNode } from "react";
import "./Chip.css";

export interface ChipProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  /**
   * Whether this is a toggleable option that is currently chosen (e.g.
   * selected genre/tone). Omit entirely for a stateless action chip (e.g.
   * "Umsehen") — leaving it unset avoids advertising toggle-button
   * semantics for a plain action trigger.
   */
  selected?: boolean;
  icon?: ReactNode;
  children: ReactNode;
}

/**
 * Pill-shaped option/action control. Used both for stateless quick actions
 * (e.g. "Umsehen") and for toggleable option pickers (e.g. Genre/Ton in the
 * story wizard) via the `selected` flag.
 */
export function Chip({ selected, icon, children, className, type = "button", ...rest }: ChipProps) {
  const classes = ["chip", selected && "chip--selected", className].filter(Boolean).join(" ");

  return (
    <button
      type={type}
      className={classes}
      aria-pressed={selected === undefined ? undefined : selected}
      {...rest}
    >
      {icon}
      {children}
    </button>
  );
}
