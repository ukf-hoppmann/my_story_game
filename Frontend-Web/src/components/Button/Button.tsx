import type { ButtonHTMLAttributes, ReactNode } from "react";
import "./Button.css";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "ghost";
  icon?: ReactNode;
  children: ReactNode;
}

/**
 * Shared button primitive. "primary" is the wine-red call-to-action
 * (submit a turn, start a story); "ghost" is the bordered secondary action.
 */
export function Button({
  variant = "primary",
  icon,
  children,
  className,
  type = "button",
  ...rest
}: ButtonProps) {
  const classes = ["button", `button--${variant}`, className].filter(Boolean).join(" ");

  return (
    <button type={type} className={classes} {...rest}>
      {children}
      {icon}
    </button>
  );
}
