import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as auth from "../../api/auth";
import { ErrorBanner } from "./ErrorBanner";

describe("ErrorBanner", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders nothing when there is no error", () => {
    const { container } = render(<ErrorBanner error={undefined} fallbackKey="wizard.startError" />);

    expect(container).toBeEmptyDOMElement();
  });

  it("shows the session-expired message with a re-login button for a session_expired error", async () => {
    vi.spyOn(auth, "login").mockImplementation(() => {});

    render(
      <ErrorBanner
        error={{ status: 401, code: "session_expired", message: "Nicht angemeldet." }}
        fallbackKey="wizard.startError"
      />,
    );

    expect(screen.getByText("Du wurdest ausgeloggt, bitte melde dich erneut an.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Neu anmelden" }));
    expect(auth.login).toHaveBeenCalledOnce();
  });

  it("shows the generic tooling-error message for a tooling_error", () => {
    render(
      <ErrorBanner
        error={{ status: 0, code: "tooling_error", message: "Failed to fetch" }}
        fallbackKey="wizard.startError"
      />,
    );

    expect(
      screen.getByText("Ein technischer Fehler ist aufgetreten und wurde protokolliert. Bitte versuche es erneut."),
    ).toBeInTheDocument();
  });

  it("shows the real backend message for an unrecognized backend error code", () => {
    render(
      <ErrorBanner
        error={{ status: 500, code: "persistence_unavailable", message: "Datenbank nicht erreichbar." }}
        fallbackKey="wizard.startError"
      />,
    );

    expect(screen.getByText("Fehler: Datenbank nicht erreichbar.")).toBeInTheDocument();
  });

  it("prefers a screen-specific knownCodes override over the raw backend message", () => {
    render(
      <ErrorBanner
        error={{ status: 409, code: "run_not_active", message: "Nicht aktiv." }}
        knownCodes={{ run_not_active: "play.errors.runNotActive" }}
        fallbackKey="play.errors.generic"
      />,
    );

    expect(
      screen.getByText("Diese Geschichte läuft nicht mehr. Lade sie neu, um den aktuellen Stand zu sehen."),
    ).toBeInTheDocument();
  });

  it("falls back to the fixed fallback text when the error carries no message", () => {
    render(<ErrorBanner error={{ status: 0, code: "", message: "" }} fallbackKey="wizard.startError" />);

    expect(
      screen.getByText("Die Geschichte konnte nicht gestartet werden. Bitte versuche es erneut."),
    ).toBeInTheDocument();
  });

  it("renders inline (bare) without its own wrapping element when bare is set", () => {
    const { container } = render(
      <ErrorBanner
        error={{ status: 500, code: "x", message: "Kaputt." }}
        fallbackKey="wizard.startError"
        bare
      />,
    );

    expect(container.querySelector("p")).not.toBeInTheDocument();
    expect(screen.getByText("Fehler: Kaputt.")).toBeInTheDocument();
  });
});
