import { computed, ref } from "vue";
import { defineStore } from "pinia";

import type {
  AgentTraceDetailResponse,
  AgentTraceExecutionType,
  AgentTraceListFilters,
  AgentTraceStatus,
  AgentTraceSummary
} from "@agent-py/api-contracts";

import { createTraceClient, type TraceClient } from "../traces/traceClient";
import { toUserFacingError } from "../ui/userFacingError";
import { useFeedbackStore } from "./feedback";

let clientFactory: () => TraceClient = createTraceClient;

export function setTraceClientFactoryForTests(factory: (() => TraceClient) | null): void {
  clientFactory = factory ?? createTraceClient;
}

export const useTraceStore = defineStore("traces", () => {
  const client = clientFactory();
  const traces = ref<readonly AgentTraceSummary[]>([]);
  const selectedTraceId = ref<string | null>(null);
  const detail = ref<AgentTraceDetailResponse | null>(null);
  const executionType = ref<AgentTraceExecutionType | "">("");
  const status = ref<AgentTraceStatus | "">("");
  const isLoadingList = ref(false);
  const isLoadingDetail = ref(false);
  const errorMessage = ref<string | null>(null);

  const filters = computed<AgentTraceListFilters>(() => ({
    ...(executionType.value === "" ? {} : { executionType: executionType.value }),
    ...(status.value === "" ? {} : { status: status.value }),
    limit: 100
  }));

  function reportError(error: unknown): void {
    const message = toUserFacingError(error);
    errorMessage.value = message;
    useFeedbackStore().showError(message);
  }

  async function loadDetail(traceId: string): Promise<void> {
    isLoadingDetail.value = true;
    errorMessage.value = null;
    selectedTraceId.value = traceId;
    try {
      detail.value = await client.getTrace(traceId);
    } catch (error) {
      detail.value = null;
      reportError(error);
      throw error;
    } finally {
      isLoadingDetail.value = false;
    }
  }

  async function loadList(options: { readonly preserveSelection?: boolean } = {}): Promise<void> {
    isLoadingList.value = true;
    errorMessage.value = null;
    try {
      const response = await client.listTraces(filters.value);
      traces.value = response.items;
      const selectedExists = response.items.some((trace) => trace.id === selectedTraceId.value);
      const nextId = options.preserveSelection === true && selectedExists
        ? selectedTraceId.value
        : response.items[0]?.id ?? null;
      selectedTraceId.value = nextId;
      if (nextId === null) {
        detail.value = null;
      } else {
        await loadDetail(nextId);
      }
    } catch (error) {
      traces.value = [];
      selectedTraceId.value = null;
      detail.value = null;
      reportError(error);
      throw error;
    } finally {
      isLoadingList.value = false;
    }
  }

  function reset(): void {
    traces.value = [];
    selectedTraceId.value = null;
    detail.value = null;
    executionType.value = "";
    status.value = "";
    isLoadingList.value = false;
    isLoadingDetail.value = false;
    errorMessage.value = null;
  }

  return {
    detail,
    errorMessage,
    executionType,
    filters,
    isLoadingDetail,
    isLoadingList,
    selectedTraceId,
    status,
    traces,
    initialize: () => loadList(),
    refresh: () => loadList({ preserveSelection: true }),
    selectTrace: loadDetail,
    setExecutionType: (value: AgentTraceExecutionType | "") => {
      executionType.value = value;
    },
    setStatus: (value: AgentTraceStatus | "") => {
      status.value = value;
    },
    applyFilters: () => loadList(),
    reset
  };
});
