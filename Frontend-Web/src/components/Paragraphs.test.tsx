import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Paragraphs } from "./Paragraphs";

describe("Paragraphs", () => {
  it("splits blank-line-separated text into separate paragraphs", () => {
    const { container } = render(<Paragraphs text={"Erster Absatz.\n\nZweiter Absatz."} />);

    const paragraphs = container.querySelectorAll("p");
    expect(paragraphs).toHaveLength(2);
    expect(paragraphs[0]).toHaveTextContent("Erster Absatz.");
    expect(paragraphs[1]).toHaveTextContent("Zweiter Absatz.");
  });

  it("falls back to single newlines when there is no blank line", () => {
    const { container } = render(<Paragraphs text={"Erste Zeile.\nZweite Zeile."} />);

    expect(container.querySelectorAll("p")).toHaveLength(2);
  });

  it("renders text with no line breaks as one paragraph", () => {
    const { container } = render(<Paragraphs text="Alles in einer Zeile." />);

    const paragraphs = container.querySelectorAll("p");
    expect(paragraphs).toHaveLength(1);
    expect(paragraphs[0]).toHaveTextContent("Alles in einer Zeile.");
  });

  it("renders nothing for empty/whitespace-only text", () => {
    const { container } = render(<Paragraphs text={"   \n\n  "} />);

    expect(container.querySelectorAll("p")).toHaveLength(0);
  });
});
