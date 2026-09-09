import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { Chip } from "./Chip";

describe("Chip", () => {
  it("renders as a plain action chip without toggle semantics by default", () => {
    render(<Chip>Umsehen</Chip>);

    const chip = screen.getByRole("button", { name: "Umsehen" });
    expect(chip).not.toHaveClass("chip--selected");
    expect(chip).not.toHaveAttribute("aria-pressed");
  });

  it("shows the selected state for a chosen option", () => {
    render(<Chip selected>Dark Fantasy</Chip>);

    const chip = screen.getByRole("button", { name: "Dark Fantasy" });
    expect(chip).toHaveClass("chip--selected");
    expect(chip).toHaveAttribute("aria-pressed", "true");
  });

  it("shows the unselected state for an available option", () => {
    render(<Chip selected={false}>Fantasy</Chip>);

    const chip = screen.getByRole("button", { name: "Fantasy" });
    expect(chip).not.toHaveClass("chip--selected");
    expect(chip).toHaveAttribute("aria-pressed", "false");
  });

  it("calls onClick when clicked", async () => {
    const onClick = vi.fn();
    render(<Chip onClick={onClick}>Hinweise prüfen</Chip>);

    await userEvent.click(screen.getByRole("button", { name: "Hinweise prüfen" }));

    expect(onClick).toHaveBeenCalledOnce();
  });
});
