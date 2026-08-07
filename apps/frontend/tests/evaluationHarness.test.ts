import { createPinia, setActivePinia } from "pinia";
import { afterEach, describe, expect, it, vi } from "vitest";

import type {
  EvaluationDatasetDetail,
  EvaluationRunDetailResponse
} from "@agent-py/api-contracts";

import { createEvaluationClient } from "../src/evaluations/evaluationClient";
import type { EvaluationClient } from "../src/evaluations/evaluationClient";
import {
  setEvaluationClientFactoryForTests,
  useEvaluationStore
} from "../src/stores/evaluations";

afterEach(() => setEvaluationClientFactoryForTests(null));

describe("Evaluation Harness client and store", () => {
  it("serializes immutable datasets and case-to-trace bindings", async () => {
    const requests: Array<{ input: string; init: RequestInit }> = [];
    const client = createEvaluationClient({
      baseUrl: "http://127.0.0.1:8000",
      getAccessToken: () => "token",
      fetchImpl: async (input, init) => {
        requests.push({ input: input.toString(), init: init ?? {} });
        return new Response(JSON.stringify({
          ok: true,
          data: input.toString().endsWith("/runs") ? report() : dataset(),
          meta: { requestId: "request-1" }
        }), { status: 200, headers: { "content-type": "application/json" } });
      }
    });

    await client.createDataset({
      name: "core",
      version: "v1",
      description: "",
      gate: { minPassRate: 1, minAverageScore: 1, maxDurationRegressionPercent: null },
      cases: dataset().cases
    });
    await client.runDataset("dataset-1", {
      candidateLabel: "P2",
      traceBindings: { "case-1": "trace-1" }
    });

    expect(requests[0]?.input).toBe("http://127.0.0.1:8000/evaluations/datasets");
    expect(JSON.parse(String(requests[1]?.init.body)).traceBindings).toEqual({
      "case-1": "trace-1"
    });
    expect(new Headers(requests[1]?.init.headers).get("Authorization")).toBe("Bearer token");
  });

  it("loads the newest report and refreshes runs after evaluation", async () => {
    const client = fakeClient();
    setEvaluationClientFactoryForTests(() => client);
    setActivePinia(createPinia());
    const store = useEvaluationStore();

    await store.initialize();
    await store.runDataset({
      candidateLabel: "P2",
      traceBindings: { "case-1": "trace-1" }
    });

    expect(store.selectedDataset?.id).toBe("dataset-1");
    expect(store.report?.run.gateStatus).toBe("passed");
    expect(client.runDataset).toHaveBeenCalledWith("dataset-1", {
      candidateLabel: "P2",
      traceBindings: { "case-1": "trace-1" }
    });
  });
});

function fakeClient(): EvaluationClient & { readonly runDataset: ReturnType<typeof vi.fn> } {
  return {
    createDataset: vi.fn(async () => dataset()),
    getDataset: vi.fn(async () => dataset()),
    listDatasets: vi.fn(async () => ({ items: [dataset()] })),
    listRuns: vi.fn(async () => ({ items: [report().run] })),
    getRun: vi.fn(async () => report()),
    runDataset: vi.fn(async () => report())
  };
}

function dataset(): EvaluationDatasetDetail {
  return {
    id: "dataset-1",
    name: "Core regression",
    version: "v1",
    description: "Trace-backed",
    gate: { minPassRate: 1, minAverageScore: 1, maxDurationRegressionPercent: null },
    caseCount: 1,
    createdAt: "2026-08-06T00:00:00Z",
    cases: [{
      id: "case-1",
      sequence: 1,
      name: "Grounded chat",
      executionType: "chat",
      inputSummary: "answer with evidence",
      rules: [{
        kind: "trace_succeeded",
        values: [],
        threshold: null,
        description: ""
      }]
    }]
  };
}

function report(): EvaluationRunDetailResponse {
  return {
    run: {
      id: "run-1",
      datasetId: "dataset-1",
      candidateLabel: "P2",
      baselineRunId: null,
      status: "completed",
      gateStatus: "passed",
      passRate: 1,
      averageScore: 1,
      averageDurationMs: 100,
      totalToolCalls: 1,
      baselineDelta: {},
      gateFailures: [],
      createdAt: "2026-08-06T00:00:00Z",
      completedAt: "2026-08-06T00:00:01Z"
    },
    results: [{
      id: "result-1",
      caseId: "case-1",
      sequence: 1,
      traceId: "trace-1",
      status: "passed",
      score: 1,
      outputSummary: "safe summary",
      metrics: { durationMs: 100 },
      checks: [{
        kind: "trace_succeeded",
        passed: true,
        expected: "succeeded",
        actual: "succeeded"
      }]
    }]
  };
}
