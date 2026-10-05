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
    fakeKeycloak.onTokenExpired = undefined;
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it("checks for an existing session silently (check-sso, PKCE) instead of redirecting", async () => {
    const { checkSession, resetAuthForTests } = await import("./auth");
    resetAuthForTests();

    await expect(checkSession()).resolves.toBe(true);

    expect(fakeKeycloak.init).toHaveBeenCalledWith({
      onLoad: "check-sso",
      silentCheckSsoRedirectUri: `${window.location.origin}/silent-check-sso.html`,
      pkceMethod: "S256",
    });
    expect(fakeKeycloak.login).not.toHaveBeenCalled();
  });

  it("reports no session when Keycloak finds none, without wiring the auth header", async () => {
    const { checkSession, resetAuthForTests } = await import("./auth");
    resetAuthForTests();
    fakeKeycloak.init.mockResolvedValueOnce(false);

    await expect(checkSession()).resolves.toBe(false);
    expect(fakeKeycloak.onTokenExpired).toBeUndefined();
    expect(fakeKeycloak.login).not.toHaveBeenCalled();
  });

  it("wires the auth header provider so every API request carries the bearer token", async () => {
    const { checkSession, resetAuthForTests } = await import("./auth");
    const { checkHealth } = await import("./client");
    resetAuthForTests();

    await checkSession();
    await checkHealth();

    const [, init] = vi.mocked(fetch).mock.calls[0];
    expect(new Headers(init?.headers).get("Authorization")).toBe("Bearer test-token");
  });

  it("proactively refreshes the token on expiry, falling back to login() on failure", async () => {
    const { checkSession, resetAuthForTests } = await import("./auth");
    resetAuthForTests();
    await checkSession();

    fakeKeycloak.updateToken.mockRejectedValueOnce(new Error("expired"));
    fakeKeycloak.onTokenExpired?.();
    await vi.waitFor(() => expect(fakeKeycloak.login).toHaveBeenCalled());
  });

  it("reads the display name from the parsed token", async () => {
    const { currentUsername } = await import("./auth");

    expect(currentUsername()).toBe("erzaehlerin");
  });

  it("logs out through Keycloak and returns to the Landing page", async () => {
    const { logout } = await import("./auth");

    logout();

    expect(fakeKeycloak.logout).toHaveBeenCalledWith({ redirectUri: `${window.location.origin}/` });
  });

  it("delegates login() to the underlying Keycloak client (TASK-030 re-login action)", async () => {
    const { login } = await import("./auth");

    login();

    expect(fakeKeycloak.login).toHaveBeenCalledOnce();
  });

  it("ensureAuth resolves without a redirect when a session exists", async () => {
    const { ensureAuth, resetAuthForTests } = await import("./auth");
    resetAuthForTests();

    await ensureAuth();

    expect(fakeKeycloak.login).not.toHaveBeenCalled();
  });

  it("ensureAuth redirects to the login and never settles when there is no session", async () => {
    const { ensureAuth, resetAuthForTests } = await import("./auth");
    resetAuthForTests();
    fakeKeycloak.init.mockResolvedValueOnce(false);

    let settled = false;
    void ensureAuth().then(() => {
      settled = true;
    });
    await vi.waitFor(() => expect(fakeKeycloak.login).toHaveBeenCalledOnce());
    await Promise.resolve();

    expect(settled).toBe(false);
  });

  it("runs Keycloak's init only once across multiple calls", async () => {
    const { ensureAuth, checkSession, resetAuthForTests } = await import("./auth");
    resetAuthForTests();

    await Promise.all([ensureAuth(), ensureAuth(), checkSession()]);

    expect(fakeKeycloak.init).toHaveBeenCalledTimes(1);
  });
});
