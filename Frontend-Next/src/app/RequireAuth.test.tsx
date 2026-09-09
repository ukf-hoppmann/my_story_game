import { render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as auth from "../api/auth";
import { RequireAuth } from "./RequireAuth";

function renderGate() {
  const router = createMemoryRouter([
    {
      element: <RequireAuth />,
      children: [{ path: "/", element: <div>Geschützter Inhalt</div> }],
    },
  ]);
  render(<RouterProvider router={router} />);
}

describe("RequireAuth", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows a loading state before auth resolves", () => {
    vi.spyOn(auth, "ensureAuth").mockReturnValue(new Promise(() => {}));
    renderGate();

    expect(screen.getByText("Anmeldung wird geprüft …")).toBeInTheDocument();
  });

  it("renders the protected route once auth resolves", async () => {
    vi.spyOn(auth, "ensureAuth").mockResolvedValue(undefined);
    renderGate();

    expect(await screen.findByText("Geschützter Inhalt")).toBeInTheDocument();
  });

  it("shows an error state if auth fails", async () => {
    vi.spyOn(auth, "ensureAuth").mockRejectedValue(new Error("login failed"));
    renderGate();

    expect(
      await screen.findByText("Anmeldung fehlgeschlagen. Bitte lade die Seite neu."),
    ).toBeInTheDocument();
  });
});
