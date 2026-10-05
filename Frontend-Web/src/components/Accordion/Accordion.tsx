import { useId, useState } from "react";
import type { ReactNode } from "react";
import { ChevronDownIcon } from "../../icons";
import "./Accordion.css";

export interface AccordionProps {
  /** Accessible name of the whole item; also what the header shows as title. */
  title: string;
  /** Short muted line next to the title, e.g. the current value. */
  summary?: ReactNode;
  /** Badges shown in the header, visible while collapsed. */
  badges?: ReactNode;
  defaultOpen?: boolean;
  children: ReactNode;
}

/**
 * A collapsible item: the header is a button that toggles the body, which is
 * only rendered while open (so collapsed items cost nothing and their
 * controls are not reachable). Collapsed by default.
 */
export function Accordion({ title, summary, badges, defaultOpen = false, children }: AccordionProps) {
  const [open, setOpen] = useState(defaultOpen);
  const bodyId = useId();

  return (
    <article className="accordion" aria-label={title}>
      <button
        type="button"
        className="accordion-header"
        aria-expanded={open}
        aria-controls={bodyId}
        onClick={() => setOpen((value) => !value)}
      >
        <ChevronDownIcon className={open ? "accordion-chevron accordion-chevron--open" : "accordion-chevron"} />
        <span className="accordion-title">{title}</span>
        {badges}
        {summary && <span className="accordion-summary">{summary}</span>}
      </button>
      {open && (
        <div className="accordion-body" id={bodyId}>
          {children}
        </div>
      )}
    </article>
  );
}
