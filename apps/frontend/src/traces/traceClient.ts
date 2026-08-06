import type {
  AgentTraceDetailResponse,
  AgentTraceListFilters,
  AgentTraceListResponse
} from "@agent-py/api-contracts";

import { createApiClient } from "../api/apiClient";
import { AUTH_TOKEN_STORAGE_KEY } from "../authClient";
import { API_BASE_URL } from "../config";

export interface TraceClient {
  getTrace(traceId: string): Promise<AgentTraceDetailResponse>;
  listTraces(filters?: AgentTraceListFilters): Promise<AgentTraceListResponse>;
}

export interface CreateTraceClientOptions {
  readonly baseUrl?: string;
  readonly fetchImpl?: typeof fetch;
  readonly getAccessToken?: () => string | null;
}

export function createTraceClient(options: CreateTraceClientOptions = {}): TraceClient {
  const getAccessToken = options.getAccessToken
    ?? (() => window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY));
  const api = createApiClient({
    baseUrl: options.baseUrl ?? API_BASE_URL,
    ...(options.fetchImpl === undefined ? {} : { fetchImpl: options.fetchImpl }),
    getAccessToken
  });

  return {
    getTrace: (traceId) =>
      api.request<AgentTraceDetailResponse>(`/agent-traces/${encodeURIComponent(traceId)}`),
    listTraces: (filters = {}) => {
      const query = new URLSearchParams();
      if (filters.executionType !== undefined) {
        query.set("executionType", filters.executionType);
      }
      if (filters.status !== undefined) query.set("status", filters.status);
      if (filters.resourceType !== undefined) query.set("resourceType", filters.resourceType);
      if (filters.resourceId !== undefined) query.set("resourceId", filters.resourceId);
      if (filters.limit !== undefined) query.set("limit", String(filters.limit));
      const suffix = query.size === 0 ? "" : `?${query.toString()}`;
      return api.request<AgentTraceListResponse>(`/agent-traces${suffix}`);
    }
  };
}
