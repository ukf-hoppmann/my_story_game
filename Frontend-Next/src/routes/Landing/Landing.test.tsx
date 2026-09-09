import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { Landing } from "./Landing";

function renderLanding() {
  const router = createMemoryRouter(
    [
      { path: "/", element: <Landing /> },
      { path: "/new", element: <div>Wizard-Route</div> },
      { path: "/library", element: <div>Bibliothek-Route</div> },
    ],
    { initialEntries: ["/"] },
  );
  render(<RouterProvider router={router} />);
}

describe("Landing", () => {
  it("renders the headline and all five genres", () => {
    renderLanding();

    expect(
      screen.getByRole("heading", { name: "Geschichten, die deinen Entscheidungen folgen." }),
    ).toBeInTheDocument();

    for (const genre of ["Dark Fantasy", "Fantasy", "Science Fiction", "Mystery", "Steampunk"]) {
      expect(screen.getByText(genre)).toBeInTheDocument();
    }
  });

  it("navigates to the wizard when starting a new story", async () => {
    renderLanding();

    await userEvent.click(screen.getByRole("button", { name: /Neue Geschichte beginnen/ }));

    expect(await screen.findByText("Wizard-Route")).toBeInTheDocument();
  });

  it("navigates to the library when opening existing stories", async () => {
    renderLanding();

    await userEvent.click(screen.getByRole("button", { name: /Deine Geschichten/ }));

    expect(await screen.findByText("Bibliothek-Route")).toBeInTheDocument();
  });
});
