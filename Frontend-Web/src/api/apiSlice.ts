import { createApi, fakeBaseQuery } from "@reduxjs/toolkit/query/react";
import {
  confirmRun,
  createSceneImage,
  fetchModelHistory,
  createPromptOption,
  fetchPromptHistory,
  fetchPromptProfileCatalog,
  fetchSceneImageCapabilities,
  listAdminModels,
  listAdminPrompts,
  listRuns,
  listSceneImages,
  loadRun,
  playTurn,
  proposeRun,
  resetModelSettings,
  archivePromptOption,
  listArchivedPromptOptions,
  purgePromptOption,
  removePromptOptions,
  restorePromptOption,
  resetPrompts,
  saveModelSetting,
  savePromptText,
  startPlaythrough,
  fetchWorldTracking,
  fetchWorldTrackingStatus,
  saveWorldTracking,
} from "./client";
import { toQueryError, type QueryError } from "./queryError";
import type {
  AdminModelOverview,
  AdminModelSetting,
  AdminModelSettingList,
  AdminModelTask,
  AdminPromptKind,
  AdminPromptList,
  AdminPromptVersion,
  AdminPromptVersionList,
  CreatePromptOptionRequest,
  ConfirmRunProposalRequest,
  CreateSceneImageRequest,
  GameDocument,
  PlayTurnRequest,
  ProposeRunRequest,
  PromptProfileCatalog,
  RunProposal,
  ResetModelSettingsRequest,
  PromptOptionRef,
  RemovalResult,
  RemovePromptOptionsRequest,
  ResetPromptsRequest,
  RunSummary,
  SaveModelSettingRequest,
  SavePromptTextRequest,
  SceneImage,
  SceneImageCapabilities,
  TurnResult,
  WorldTrackingSetting,
  WorldTrackingStatus,
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
  tagTypes: ["Run", "SceneImage", "AdminPrompt", "AdminModel", "WorldTracking"],
  endpoints: (builder) => ({
    listAdminPrompts: builder.query<AdminPromptList, void>({
      queryFn: async () => {
        try {
          return { data: await listAdminPrompts() };
        } catch (error) {
          return { error: toQueryError(error, "apiSlice.listAdminPrompts") };
        }
      },
      providesTags: ["AdminPrompt"],
    }),
    listAdminModels: builder.query<AdminModelOverview, void>({
      queryFn: async () => {
        try {
          return { data: await listAdminModels() };
        } catch (error) {
          return { error: toQueryError(error, "apiSlice.listAdminModels") };
        }
      },
      providesTags: ["AdminModel"],
    }),
    worldTracking: builder.query<WorldTrackingSetting, void>({
      queryFn: async () => {
        try {
          return { data: await fetchWorldTracking() };
        } catch (error) {
          return { error: toQueryError(error, "apiSlice.worldTracking") };
        }
      },
      providesTags: ["WorldTracking"],
    }),
    saveWorldTracking: builder.mutation<WorldTrackingSetting, boolean>({
      queryFn: async (enabled) => {
        try {
          return { data: await saveWorldTracking(enabled) };
        } catch (error) {
          return { error: toQueryError(error, "apiSlice.saveWorldTracking") };
        }
      },
      invalidatesTags: ["WorldTracking"],
    }),
    worldTrackingStatus: builder.query<WorldTrackingStatus, void>({
      queryFn: async () => {
        try {
          return { data: await fetchWorldTrackingStatus() };
        } catch (error) {
          return { error: toQueryError(error, "apiSlice.worldTrackingStatus") };
        }
      },
      providesTags: ["WorldTracking"],
    }),
    modelHistory: builder.query<AdminModelSettingList, AdminModelTask>({
      queryFn: async (task) => {
        try {
          return { data: await fetchModelHistory(task) };
        } catch (error) {
          return { error: toQueryError(error, "apiSlice.modelHistory") };
        }
      },
      providesTags: ["AdminModel"],
    }),
    saveModelSetting: builder.mutation<AdminModelSetting, SaveModelSettingRequest>({
      queryFn: async (payload) => {
        try {
          return { data: await saveModelSetting(payload) };
        } catch (error) {
          return { error: toQueryError(error, "apiSlice.saveModelSetting") };
        }
      },
      invalidatesTags: ["AdminModel"],
    }),
    resetModelSettings: builder.mutation<AdminModelSettingList, ResetModelSettingsRequest>({
      queryFn: async (payload) => {
        try {
          return { data: await resetModelSettings(payload) };
        } catch (error) {
          return { error: toQueryError(error, "apiSlice.resetModelSettings") };
        }
      },
      invalidatesTags: ["AdminModel"],
    }),
    promptHistory: builder.query<AdminPromptVersionList, { kind: AdminPromptKind; key: string }>({
      queryFn: async ({ kind, key }) => {
        try {
          return { data: await fetchPromptHistory(kind, key) };
        } catch (error) {
          return { error: toQueryError(error, "apiSlice.promptHistory") };
        }
      },
      providesTags: ["AdminPrompt"],
    }),
    savePromptText: builder.mutation<AdminPromptVersion, SavePromptTextRequest>({
      queryFn: async (payload) => {
        try {
          return { data: await savePromptText(payload) };
        } catch (error) {
          return { error: toQueryError(error, "apiSlice.savePromptText") };
        }
      },
      invalidatesTags: ["AdminPrompt"],
    }),
    createPromptOption: builder.mutation<AdminPromptVersion, CreatePromptOptionRequest>({
      queryFn: async (payload) => {
        try {
          return { data: await createPromptOption(payload) };
        } catch (error) {
          return { error: toQueryError(error, "apiSlice.createPromptOption") };
        }
      },
      invalidatesTags: ["AdminPrompt"],
    }),
    archivePromptOption: builder.mutation<void, PromptOptionRef>({
      queryFn: async (payload) => {
        try {
          return { data: await archivePromptOption(payload) };
        } catch (error) {
          return { error: toQueryError(error, "apiSlice.archivePromptOption") };
        }
      },
      invalidatesTags: ["AdminPrompt"],
    }),
    restorePromptOption: builder.mutation<void, PromptOptionRef>({
      queryFn: async (payload) => {
        try {
          return { data: await restorePromptOption(payload) };
        } catch (error) {
          return { error: toQueryError(error, "apiSlice.restorePromptOption") };
        }
      },
      invalidatesTags: ["AdminPrompt"],
    }),
    purgePromptOption: builder.mutation<void, PromptOptionRef>({
      queryFn: async (payload) => {
        try {
          return { data: await purgePromptOption(payload) };
        } catch (error) {
          return { error: toQueryError(error, "apiSlice.purgePromptOption") };
        }
      },
      invalidatesTags: ["AdminPrompt"],
    }),
    removePromptOptions: builder.mutation<RemovalResult, RemovePromptOptionsRequest>({
      queryFn: async (payload) => {
        try {
          return { data: await removePromptOptions(payload) };
        } catch (error) {
          return { error: toQueryError(error, "apiSlice.removePromptOptions") };
        }
      },
      invalidatesTags: ["AdminPrompt"],
    }),
    listArchivedPromptOptions: builder.query<AdminPromptVersionList, void>({
      queryFn: async () => {
        try {
          return { data: await listArchivedPromptOptions() };
        } catch (error) {
          return { error: toQueryError(error, "apiSlice.listArchivedPromptOptions") };
        }
      },
      providesTags: ["AdminPrompt"],
    }),
    resetPrompts: builder.mutation<AdminPromptVersionList, ResetPromptsRequest>({
      queryFn: async (payload) => {
        try {
          return { data: await resetPrompts(payload) };
        } catch (error) {
          return { error: toQueryError(error, "apiSlice.resetPrompts") };
        }
      },
      invalidatesTags: ["AdminPrompt"],
    }),
    listRuns: builder.query<RunSummary[], void>({
      queryFn: async () => {
        try {
          const { runs } = await listRuns();
          return { data: runs };
        } catch (error) {
          return { error: toQueryError(error, "apiSlice.listRuns") };
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
          return { error: toQueryError(error, "apiSlice.promptProfileCatalog") };
        }
      },
    }),
    loadRun: builder.query<GameDocument, string>({
      queryFn: async (runId) => {
        try {
          const doc = await loadRun(runId);
          return { data: doc };
        } catch (error) {
          return { error: toQueryError(error, "apiSlice.loadRun") };
        }
      },
      providesTags: (_result, _error, runId) => [{ type: "Run", id: runId }],
    }),
    proposeRun: builder.mutation<RunProposal, ProposeRunRequest>({
      queryFn: async (payload) => {
        try {
          const proposal = await proposeRun(payload);
          return { data: proposal };
        } catch (error) {
          return { error: toQueryError(error, "apiSlice.proposeRun") };
        }
      },
    }),
    confirmRun: builder.mutation<GameDocument, ConfirmRunProposalRequest>({
      queryFn: async (payload) => {
        try {
          const doc = await confirmRun(payload);
          return { data: doc };
        } catch (error) {
          return { error: toQueryError(error, "apiSlice.confirmRun") };
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
          return { error: toQueryError(error, "apiSlice.startPlaythrough") };
        }
      },
      invalidatesTags: ["Run"],
    }),
    playTurn: builder.mutation<TurnResult, { runId: string; payload: PlayTurnRequest }>({
      queryFn: async ({ runId, payload }) => {
        try {
          const result = await playTurn(runId, payload);
          return { data: result };
        } catch (error) {
          return { error: toQueryError(error, "apiSlice.playTurn") };
        }
      },
      invalidatesTags: (_result, _error, { runId }) => [{ type: "Run", id: runId }],
    }),
    sceneImageCapabilities: builder.query<SceneImageCapabilities, void>({
      queryFn: async () => {
        try {
          return { data: await fetchSceneImageCapabilities() };
        } catch (error) {
          return { error: toQueryError(error, "apiSlice.sceneImageCapabilities") };
        }
      },
    }),
    listSceneImages: builder.query<SceneImage[], string>({
      queryFn: async (runId) => {
        try {
          const { images } = await listSceneImages(runId);
          return { data: images };
        } catch (error) {
          return { error: toQueryError(error, "apiSlice.listSceneImages") };
        }
      },
      providesTags: (_result, _error, runId) => [{ type: "SceneImage", id: runId }],
    }),
    createSceneImage: builder.mutation<
      SceneImage,
      { runId: string; payload: CreateSceneImageRequest }
    >({
      queryFn: async ({ runId, payload }) => {
        try {
          return { data: await createSceneImage(runId, payload) };
        } catch (error) {
          return { error: toQueryError(error, "apiSlice.createSceneImage") };
        }
      },
      invalidatesTags: (_result, _error, { runId }) => [{ type: "SceneImage", id: runId }],
    }),
  }),
});

export const {
  useListRunsQuery,
  usePromptProfileCatalogQuery,
  useLoadRunQuery,
  useProposeRunMutation,
  useConfirmRunMutation,
  useStartPlaythroughMutation,
  usePlayTurnMutation,
  useSceneImageCapabilitiesQuery,
  useListSceneImagesQuery,
  useCreateSceneImageMutation,
  useListAdminModelsQuery,
  useModelHistoryQuery,
  useSaveModelSettingMutation,
  useResetModelSettingsMutation,
  useWorldTrackingQuery,
  useSaveWorldTrackingMutation,
  useWorldTrackingStatusQuery,
  useListAdminPromptsQuery,
  usePromptHistoryQuery,
  useSavePromptTextMutation,
  useResetPromptsMutation,
  useCreatePromptOptionMutation,
  useArchivePromptOptionMutation,
  useListArchivedPromptOptionsQuery,
  usePurgePromptOptionMutation,
  useRemovePromptOptionsMutation,
  useRestorePromptOptionMutation,
} = apiSlice;
