import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PersonIcon } from "../../icons";
import { Panel } from "./Panel";

describe("Panel", () => {
  it("renders the title, icon and content", () => {
    render(
      <Panel title="Figuren" icon={<PersonIcon data-testid="icon" />}>
        <p>Bran, der Wirt</p>
      </Panel>,
    );

    expect(screen.getByRole("heading", { name: "Figuren" })).toBeInTheDocument();
    expect(screen.getByTestId("icon")).toBeInTheDocument();
    expect(screen.getByText("Bran, der Wirt")).toBeInTheDocument();
  });
});
