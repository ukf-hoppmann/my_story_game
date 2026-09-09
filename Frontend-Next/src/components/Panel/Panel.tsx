import type { HTMLAttributes, ReactNode } from "react";
import "./Panel.css";

export interface PanelProps extends HTMLAttributes<HTMLElement> {
  title: string;
  icon: ReactNode;
  children: ReactNode;
}

/**
 * Bordered card used for the Play-screen sidebar sections (Aktuelles Ziel,
 * Weltwissen, Figuren) and reusable anywhere else a titled, icon-labeled
 * card is needed.
 */
export function Panel({ title, icon, children, className, ...rest }: PanelProps) {
  const classes = ["panel", className].filter(Boolean).join(" ");

  return (
    <section className={classes} {...rest}>
      <div className="panel-head">
        {icon}
        <h3>{title}</h3>
      </div>
      {children}
    </section>
  );
}
