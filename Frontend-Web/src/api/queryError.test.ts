import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "./client";
import * as client from "./client";
import { toQueryError } from "./queryError";

describe("toQueryError", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("maps a 401 ApiError to session_expired and does not report it", () => {
    vi.spyOn(client, "reportFrontendError").mockResolvedValue(undefined);

    const result = toQueryError(
      new ApiError(401, { error: "unauthorized", detail: "Nicht angemeldet." }),
      "apiSlice.listRuns",
    );

    expect(result).toEqual({ status: 401, code: "session_expired", message: "Nicht angemeldet." });
    expect(client.reportFrontendError).not.toHaveBeenCalled();
  });

  it("passes through any other ApiError unchanged, without reporting it", () => {
    vi.spyOn(client, "reportFrontendError").mockResolvedValue(undefined);

    const result = toQueryError(
      new ApiError(409, { error: "revision_conflict", detail: "Konflikt." }),
      "apiSlice.playTurn",
    );

    expect(result).toEqual({ status: 409, code: "revision_conflict", message: "Konflikt." });
    expect(client.reportFrontendError).not.toHaveBeenCalled();
  });

  it("classifies a non-ApiError as a tooling error and reports it to the backend", () => {
    vi.spyOn(client, "reportFrontendError").mockResolvedValue(undefined);

    const result = toQueryError(new Error("Failed to fetch"), "wizard.handleCreateProposal");

    expect(result).toEqual({ status: 0, code: "tooling_error", message: "Failed to fetch" });
    expect(client.reportFrontendError).toHaveBeenCalledWith({
      source: "wizard.handleCreateProposal",
      message: "Failed to fetch",
      url: expect.any(String),
      user_agent: expect.any(String),
    });
  });

  it("never lets a failing report throw out of toQueryError", () => {
    vi.spyOn(client, "reportFrontendError").mockRejectedValue(new ApiError(401, { error: "unauthorized", detail: "x" }));

    expect(() => toQueryError(new Error("boom"), "wizard.handleCreateProposal")).not.toThrow();
  });

  it("classifies a non-Error thrown value as a tooling error too", () => {
    vi.spyOn(client, "reportFrontendError").mockResolvedValue(undefined);

    const result = toQueryError("just a string", "wizard.handleCreateProposal");

    expect(result.code).toBe("tooling_error");
    expect(result.status).toBe(0);
  });
});
