import { createApi, fakeBaseQuery } from "@reduxjs/toolkit/query/react";
import {
  confirmRun,
  fetchPromptProfileCatalog,
  listRuns,
  proposeRun,
  startPlaythrough,
} from "./client";
import { toQueryError, type QueryError } from "./queryError";
import type {
  ConfirmRunProposalRequest,
  GameDocument,
  ProposeRunRequest,
  PromptProfileCatalog,
  RunProposal,
  RunSummary,
} from "./types";

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
    promptProfileCatalog: builder.query<PromptProfileCatalog, void>({
      queryFn: async () => {
        try {
          const catalog = await fetchPromptProfileCatalog();
          return { data: catalog };
        } catch (error) {
          return { error: toQueryError(error) };
        }
      },
    }),
    proposeRun: builder.mutation<RunProposal, ProposeRunRequest>({
      queryFn: async (payload) => {
        try {
          const proposal = await proposeRun(payload);
          return { data: proposal };
        } catch (error) {
          return { error: toQueryError(error) };
        }
      },
    }),
    confirmRun: builder.mutation<GameDocument, ConfirmRunProposalRequest>({
      queryFn: async (payload) => {
        try {
          const doc = await confirmRun(payload);
          return { data: doc };
        } catch (error) {
          return { error: toQueryError(error) };
        }
      },
      invalidatesTags: ["Run"],
    }),
    startPlaythrough: builder.mutation<GameDocument, string>({
      queryFn: async (runId) => {
        try {
          const doc = await startPlaythrough(runId);
          return { data: doc };
        } catch (error) {
          return { error: toQueryError(error) };
        }
      },
      invalidatesTags: ["Run"],
    }),
  }),
});

export const {
  useListRunsQuery,
  usePromptProfileCatalogQuery,
  useProposeRunMutation,
  useConfirmRunMutation,
  useStartPlaythroughMutation,
} = apiSlice;
