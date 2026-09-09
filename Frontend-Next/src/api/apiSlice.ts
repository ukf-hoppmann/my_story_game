import { createApi, fakeBaseQuery } from "@reduxjs/toolkit/query/react";
import { listRuns } from "./client";
import { toQueryError, type QueryError } from "./queryError";
import type { RunSummary } from "./types";

/**
 * Central RTK Query API slice. `client.ts` stays the actual transport (fetch
 * wrapper, auth-header injection, error normalization) — each endpoint here
 * is a thin `queryFn` around one of its typed functions, so RTK Query only
 * adds caching/hooks/tags on top rather than reimplementing the request
 * layer. New endpoints get added here as later roadmap steps need them.
 */
export const apiSlice = createApi({
  reducerPath: "api",
  baseQuery: fakeBaseQuery<QueryError>(),
  tagTypes: ["Run"],
  endpoints: (builder) => ({
    listRuns: builder.query<RunSummary[], void>({
      queryFn: async () => {
        try {
          const { runs } = await listRuns();
          return { data: runs };
        } catch (error) {
          return { error: toQueryError(error) };
        }
      },
      providesTags: ["Run"],
    }),
  }),
});

export const { useListRunsQuery } = apiSlice;
