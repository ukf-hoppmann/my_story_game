import { useCallback, useState } from "react";
import { ApiError } from "./client";

export type ApiRequestState<T> =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; data: T }
  | { status: "error"; error: ApiError | Error };

/**
 * Wraps one async API action with a discriminated-union loading state.
 * The MVP intentionally leaves caching and revalidation to a later frontend
 * increment.
 */
export function useApiRequest<Args extends unknown[], T>(
  action: (...args: Args) => Promise<T>,
): [ApiRequestState<T>, (...args: Args) => Promise<T | undefined>] {
  const [state, setState] = useState<ApiRequestState<T>>({ status: "idle" });

  const run = useCallback(
    async (...args: Args) => {
      setState({ status: "loading" });
      try {
        const data = await action(...args);
        setState({ status: "success", data });
        return data;
      } catch (error) {
        setState({
          status: "error",
          error: error instanceof Error ? error : new Error(String(error)),
        });
        return undefined;
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );

  return [state, run];
}

export function errorMessage(error: ApiError | Error): string {
  if (error instanceof ApiError) {
    return error.body.detail || `Fehler: ${error.code}`;
  }
  return error.message || "Unbekannter Fehler.";
}
