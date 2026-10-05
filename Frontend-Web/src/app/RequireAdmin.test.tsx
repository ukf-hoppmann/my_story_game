import { render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as auth from "../api/auth";
import { RequireAdmin } from "./RequireAdmin";

function renderGate() {
  const router = createMemoryRouter(
    [{ element: <RequireAdmin />, children: [{ path: "/settings", element: <div>Geheim</div> }] }],
    { initialEntries: ["/settings"] },
  );
  render(<RouterProvider router={router} />);
}

describe("RequireAdmin", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the child route for an admin", () => {
    vi.spyOn(auth, "isAdmin").mockReturnValue(true);

    renderGate();

    expect(screen.getByText("Geheim")).toBeInTheDocument();
  });

  it("shows a no-access message to everyone else", () => {
    vi.spyOn(auth, "isAdmin").mockReturnValue(false);

    renderGate();

    expect(screen.queryByText("Geheim")).not.toBeInTheDocument();
    expect(screen.getByText("Dafür fehlt dir die Berechtigung.")).toBeInTheDocument();
  });
});
