import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, checkHealth, listRuns, setAuthHeaderProvider } from "./client";

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("client", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    setAuthHeaderProvider(null);
    vi.unstubAllGlobals();
  });

  it("returns the parsed JSON body on success", async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse(200, { status: "ok" }));

    await expect(checkHealth()).resolves.toEqual({ status: "ok" });
  });

  it("returns undefined for a 204 response instead of parsing a body", async () => {
    vi.mocked(fetch).mockResolvedValue(new Response(null, { status: 204 }));

    await expect(checkHealth()).resolves.toBeUndefined();
  });

  it("throws an ApiError carrying the backend's error envelope on failure", async () => {
    vi.mocked(fetch).mockResolvedValue(
      jsonResponse(409, { error: "run_not_active", detail: "Run ist nicht aktiv." }),
    );

    const error = await checkHealth().catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      status: 409,
      code: "run_not_active",
      message: "Run ist nicht aktiv.",
    });
  });

  it("falls back to a generic error body when the response isn't valid JSON", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response("not json", { status: 500, statusText: "Internal Server Error" }),
    );

    const error = await checkHealth().catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 500, code: "unknown_error" });
  });

  it("attaches the auth header from the injected provider to every request", async () => {
    setAuthHeaderProvider(() => ({ Authorization: "Bearer test-token" }));
    vi.mocked(fetch).mockResolvedValue(jsonResponse(200, { runs: [] }));

    await listRuns();

    const [, init] = vi.mocked(fetch).mock.calls[0];
    expect(new Headers(init?.headers).get("Authorization")).toBe("Bearer test-token");
  });
});
