import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ArrowRightIcon } from "../../icons";
import { Button } from "./Button";

describe("Button", () => {
  it("renders its label and applies the primary variant by default", () => {
    render(<Button>Handlung ausführen</Button>);

    const button = screen.getByRole("button", { name: "Handlung ausführen" });
    expect(button).toHaveClass("button--primary");
  });

  it("applies the ghost variant when requested", () => {
    render(<Button variant="ghost">Anmelden</Button>);

    expect(screen.getByRole("button", { name: "Anmelden" })).toHaveClass(
      "button--ghost",
    );
  });

  it("renders an optional trailing icon", () => {
    render(
      <Button icon={<ArrowRightIcon data-testid="icon" />}>Weiter</Button>,
    );

    expect(screen.getByTestId("icon")).toBeInTheDocument();
  });

  it("calls onClick when clicked", async () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Weiter</Button>);

    await userEvent.click(screen.getByRole("button", { name: "Weiter" }));

    expect(onClick).toHaveBeenCalledOnce();
  });

  it("does not fire onClick when disabled", async () => {
    const onClick = vi.fn();
    render(
      <Button onClick={onClick} disabled>
        Weiter
      </Button>,
    );

    await userEvent.click(screen.getByRole("button", { name: "Weiter" }));

    expect(onClick).not.toHaveBeenCalled();
  });
});
