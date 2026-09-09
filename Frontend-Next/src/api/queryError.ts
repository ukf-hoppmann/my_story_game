import { ApiError } from "./client";

/** Serializable error shape used across every RTK Query endpoint. */
export interface QueryError {
  status: number;
  code: string;
  message: string;
}

/** Normalizes anything a client.ts call can throw into a QueryError, so RTK
 *  Query endpoints never leak a raw exception into the Redux store. */
export function toQueryError(error: unknown): QueryError {
  if (error instanceof ApiError) {
    return { status: error.status, code: error.code, message: error.message };
  }
  if (error instanceof Error) {
    return { status: 0, code: "unknown_error", message: error.message };
  }
  return { status: 0, code: "unknown_error", message: "Unbekannter Fehler." };
}
