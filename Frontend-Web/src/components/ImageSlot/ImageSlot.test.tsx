import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PersonIcon } from "../../icons";
import { ImageSlot } from "./ImageSlot";

describe("ImageSlot", () => {
  it("shows the placeholder label and icon when no image is set", () => {
    render(<ImageSlot label="Platzhalter · Szenenbild folgt" />);

    expect(screen.getByText("Platzhalter · Szenenbild folgt")).toBeInTheDocument();
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });

  it("renders a real image once imageUrl is provided, keeping the label out", () => {
    render(
      <ImageSlot
        imageUrl="https://example.com/marktplatz.png"
        alt="Auenfall – Alter Marktplatz"
        label="Platzhalter · Szenenbild folgt"
      />,
    );

    const img = screen.getByRole("img", { name: "Auenfall – Alter Marktplatz" });
    expect(img).toHaveAttribute("src", "https://example.com/marktplatz.png");
    expect(screen.queryByText("Platzhalter · Szenenbild folgt")).not.toBeInTheDocument();
  });

  it("accepts a custom placeholder icon (e.g. for portrait slots)", () => {
    render(<ImageSlot shape="circle" placeholderIcon={<PersonIcon data-testid="person-icon" />} />);

    expect(screen.getByTestId("person-icon")).toBeInTheDocument();
  });
});
