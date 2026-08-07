import type {
  CreateEvaluationDatasetRequest,
  EvaluationDatasetDetail,
  EvaluationDatasetListResponse,
  EvaluationRunDetailResponse,
  EvaluationRunListResponse,
  RunEvaluationRequest
} from "@agent-py/api-contracts";

import { createApiClient } from "../api/apiClient";
import { AUTH_TOKEN_STORAGE_KEY } from "../authClient";
import { API_BASE_URL } from "../config";

export interface EvaluationClient {
  createDataset(payload: CreateEvaluationDatasetRequest): Promise<EvaluationDatasetDetail>;
  getDataset(datasetId: string): Promise<EvaluationDatasetDetail>;
  listDatasets(): Promise<EvaluationDatasetListResponse>;
  listRuns(datasetId?: string): Promise<EvaluationRunListResponse>;
  getRun(runId: string): Promise<EvaluationRunDetailResponse>;
  runDataset(datasetId: string, payload: RunEvaluationRequest): Promise<EvaluationRunDetailResponse>;
}

export interface CreateEvaluationClientOptions {
  readonly baseUrl?: string;
  readonly fetchImpl?: typeof fetch;
  readonly getAccessToken?: () => string | null;
}

export function createEvaluationClient(
  options: CreateEvaluationClientOptions = {}
): EvaluationClient {
  const getAccessToken = options.getAccessToken
    ?? (() => window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY));
  const api = createApiClient({
    baseUrl: options.baseUrl ?? API_BASE_URL,
    ...(options.fetchImpl === undefined ? {} : { fetchImpl: options.fetchImpl }),
    getAccessToken
  });
  return {
    createDataset: (payload) => api.request("/evaluations/datasets", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
    getDataset: (datasetId) => api.request(`/evaluations/datasets/${encodeURIComponent(datasetId)}`),
    listDatasets: () => api.request("/evaluations/datasets"),
    listRuns: (datasetId) => api.request(
      `/evaluations/runs${datasetId === undefined ? "" : `?datasetId=${encodeURIComponent(datasetId)}`}`
    ),
    getRun: (runId) => api.request(`/evaluations/runs/${encodeURIComponent(runId)}`),
    runDataset: (datasetId, payload) => api.request(
      `/evaluations/datasets/${encodeURIComponent(datasetId)}/runs`,
      { method: "POST", body: JSON.stringify(payload) }
    )
  };
}
