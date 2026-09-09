import { render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { routes } from "./routes";

function renderAt(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  render(<RouterProvider router={router} />);
}

describe("routes", () => {
  it("renders the Landing page at /", () => {
    renderAt("/");

    expect(
      screen.getByRole("heading", { name: "Geschichten, die deinen Entscheidungen folgen." }),
    ).toBeInTheDocument();
  });

  it("renders the Bibliothek placeholder at /library", () => {
    renderAt("/library");

    expect(screen.getByText("Bibliothek folgt in Schritt 6.")).toBeInTheDocument();
  });

  it("renders the Wizard placeholder at /new", () => {
    renderAt("/new");

    expect(screen.getByText("Story-Wizard folgt in Schritt 7/8.")).toBeInTheDocument();
  });

  it("renders the Play placeholder at /stories/:runId", () => {
    renderAt("/stories/11111111-1111-1111-1111-111111111111");

    expect(screen.getByText("Play-Screen folgt in Schritt 9/10.")).toBeInTheDocument();
  });
});
