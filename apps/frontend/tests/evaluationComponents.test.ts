// @vitest-environment jsdom

import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { EvaluationClient } from "../src/evaluations/evaluationClient";
import {
  setEvaluationClientFactoryForTests
} from "../src/stores/evaluations";
import EvaluationView from "../src/views/EvaluationView.vue";

afterEach(() => {
  setEvaluationClientFactoryForTests(null);
  vi.unstubAllGlobals();
});

describe("Evaluation workspace", () => {
  it("renders gate metrics, failed checks, and a Trace link", async () => {
    setEvaluationClientFactoryForTests(() => fakeClient());
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({
      ok: true,
      data: { items: [trace()] },
      meta: { requestId: "request-1" }
    }), { status: 200, headers: { "content-type": "application/json" } })));
    setActivePinia(createPinia());

    const wrapper = mount(EvaluationView, {
      global: {
        stubs: { RouterLink: { template: "<a><slot /></a>" } }
      }
    });
    await flushPromises();

    expect(wrapper.text()).toContain("Core regression");
    expect(wrapper.text()).toContain("门禁失败");
    expect(wrapper.text()).toContain("Missing reference");
    expect(wrapper.text()).toContain("相对基线");
    expect(wrapper.text()).toContain("+5 pt");
    expect(wrapper.text()).toContain("查看 Trace trace-1");
    expect(wrapper.findAll("select").length).toBeGreaterThan(1);
  });
});

function fakeClient(): EvaluationClient {
  const dataset = {
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
      executionType: "chat" as const,
      inputSummary: "answer with evidence",
      rules: [{
        kind: "min_references" as const,
        values: [],
        threshold: 1,
        description: ""
      }]
    }]
  };
  const run = {
    id: "run-1",
    datasetId: "dataset-1",
    candidateLabel: "P2 candidate",
    baselineRunId: "baseline-run",
    status: "completed" as const,
    gateStatus: "failed" as const,
    passRate: 0,
    averageScore: 0,
    averageDurationMs: 120,
    totalToolCalls: 1,
    baselineDelta: {
      passRatePoints: 5,
      averageScorePoints: 2,
      durationPercent: -10,
      toolCallCount: 0
    },
    gateFailures: ["pass rate 0% is below 100%"],
    createdAt: "2026-08-06T00:00:00Z",
    completedAt: "2026-08-06T00:00:01Z"
  };
  const report = {
    run,
    results: [{
      id: "result-1",
      caseId: "case-1",
      sequence: 1,
      traceId: "trace-1",
      status: "failed" as const,
      score: 0,
      outputSummary: "Missing reference",
      metrics: { durationMs: 120 },
      checks: [{
        kind: "min_references" as const,
        passed: false,
        expected: ">=1",
        actual: "0"
      }]
    }]
  };
  return {
    createDataset: async () => dataset,
    getDataset: async () => dataset,
    listDatasets: async () => ({ items: [dataset] }),
    listRuns: async () => ({ items: [run] }),
    getRun: async () => report,
    runDataset: async () => report
  };
}

function trace() {
  return {
    id: "trace-1",
    executionType: "chat",
    resourceType: "chat_session",
    resourceId: "session-1",
    requestId: null,
    status: "succeeded",
    summary: "Chat completed",
    errorCategory: null,
    metadata: {},
    startedAt: "2026-08-06T00:00:00Z",
    completedAt: "2026-08-06T00:00:01Z",
    durationMs: 1000
  };
}
