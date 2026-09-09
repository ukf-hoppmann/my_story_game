import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// `keycloak-js`'s real client performs a browser redirect — mock it with a
// minimal fake that lets us drive `onTokenExpired`/`token`/`tokenParsed`
// directly, so these tests never touch the network or the DOM location.
const fakeKeycloak = {
  init: vi.fn().mockResolvedValue(true),
  updateToken: vi.fn().mockResolvedValue(true),
  login: vi.fn(),
  logout: vi.fn(),
  token: "test-token",
  tokenParsed: { preferred_username: "erzaehlerin" } as Record<string, unknown> | undefined,
  onTokenExpired: undefined as (() => void) | undefined,
};

vi.mock("keycloak-js", () => ({
  default: vi.fn(function FakeKeycloak() {
    return fakeKeycloak;
  }),
}));

describe("auth", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({}), { status: 200 })));
    fakeKeycloak.tokenParsed = { preferred_username: "erzaehlerin" };
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it("initializes Keycloak with login-required and PKCE", async () => {
    const { initAuth } = await import("./auth");

    await initAuth();

    expect(fakeKeycloak.init).toHaveBeenCalledWith({
      onLoad: "login-required",
      pkceMethod: "S256",
    });
  });

  it("wires the auth header provider so every API request carries the bearer token", async () => {
    const { initAuth } = await import("./auth");
    const { checkHealth } = await import("./client");

    await initAuth();
    await checkHealth();

    const [, init] = vi.mocked(fetch).mock.calls[0];
    expect(new Headers(init?.headers).get("Authorization")).toBe("Bearer test-token");
  });

  it("proactively refreshes the token on expiry, falling back to login() on failure", async () => {
    const { initAuth } = await import("./auth");
    await initAuth();

    fakeKeycloak.updateToken.mockRejectedValueOnce(new Error("expired"));
    fakeKeycloak.onTokenExpired?.();
    await vi.waitFor(() => expect(fakeKeycloak.login).toHaveBeenCalled());
  });

  it("reads the display name from the parsed token", async () => {
    const { currentUsername } = await import("./auth");

    expect(currentUsername()).toBe("erzaehlerin");
  });

  it("delegates logout() to the underlying Keycloak client", async () => {
    const { logout } = await import("./auth");

    logout();

    expect(fakeKeycloak.logout).toHaveBeenCalledOnce();
  });
});
