import { ref } from "vue";
import { defineStore } from "pinia";

import type {
  CreateEvaluationDatasetRequest,
  EvaluationDatasetDetail,
  EvaluationDatasetSummary,
  EvaluationRunDetailResponse,
  EvaluationRunSummary,
  RunEvaluationRequest
} from "@agent-py/api-contracts";

import { createEvaluationClient, type EvaluationClient } from "../evaluations/evaluationClient";
import { toUserFacingError } from "../ui/userFacingError";
import { useFeedbackStore } from "./feedback";

let clientFactory: () => EvaluationClient = createEvaluationClient;

export function setEvaluationClientFactoryForTests(
  factory: (() => EvaluationClient) | null
): void {
  clientFactory = factory ?? createEvaluationClient;
}

export const useEvaluationStore = defineStore("evaluations", () => {
  const client = clientFactory();
  const datasets = ref<readonly EvaluationDatasetSummary[]>([]);
  const selectedDataset = ref<EvaluationDatasetDetail | null>(null);
  const runs = ref<readonly EvaluationRunSummary[]>([]);
  const report = ref<EvaluationRunDetailResponse | null>(null);
  const isLoading = ref(false);
  const isRunning = ref(false);
  const errorMessage = ref<string | null>(null);

  function reportError(error: unknown): void {
    const message = toUserFacingError(error);
    errorMessage.value = message;
    useFeedbackStore().showError(message);
  }

  async function selectDataset(datasetId: string): Promise<void> {
    errorMessage.value = null;
    const [dataset, runResponse] = await Promise.all([
      client.getDataset(datasetId),
      client.listRuns(datasetId)
    ]);
    selectedDataset.value = dataset;
    runs.value = runResponse.items;
    report.value = runResponse.items[0] === undefined
      ? null
      : await client.getRun(runResponse.items[0].id);
  }

  async function initialize(): Promise<void> {
    isLoading.value = true;
    errorMessage.value = null;
    try {
      const response = await client.listDatasets();
      datasets.value = response.items;
      if (response.items[0] !== undefined) await selectDataset(response.items[0].id);
    } catch (error) {
      reportError(error);
      throw error;
    } finally {
      isLoading.value = false;
    }
  }

  async function createDataset(payload: CreateEvaluationDatasetRequest): Promise<void> {
    isLoading.value = true;
    errorMessage.value = null;
    try {
      const created = await client.createDataset(payload);
      datasets.value = (await client.listDatasets()).items;
      selectedDataset.value = created;
      runs.value = [];
      report.value = null;
    } catch (error) {
      reportError(error);
      throw error;
    } finally {
      isLoading.value = false;
    }
  }

  async function runDataset(payload: RunEvaluationRequest): Promise<void> {
    if (selectedDataset.value === null) return;
    isRunning.value = true;
    errorMessage.value = null;
    try {
      report.value = await client.runDataset(selectedDataset.value.id, payload);
      runs.value = (await client.listRuns(selectedDataset.value.id)).items;
    } catch (error) {
      reportError(error);
      throw error;
    } finally {
      isRunning.value = false;
    }
  }

  async function selectRun(runId: string): Promise<void> {
    report.value = await client.getRun(runId);
  }

  function reset(): void {
    datasets.value = [];
    selectedDataset.value = null;
    runs.value = [];
    report.value = null;
    isLoading.value = false;
    isRunning.value = false;
    errorMessage.value = null;
  }

  return {
    datasets,
    selectedDataset,
    runs,
    report,
    isLoading,
    isRunning,
    errorMessage,
    initialize,
    createDataset,
    selectDataset,
    runDataset,
    selectRun,
    reset
  };
});
