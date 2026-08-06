import { createPinia, setActivePinia } from "pinia";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { AgentTraceDetailResponse, AgentTraceSummary } from "@agent-py/api-contracts";

import type { TraceClient } from "../src/traces/traceClient";
import { setTraceClientFactoryForTests, useTraceStore } from "../src/stores/traces";

afterEach(() => setTraceClientFactoryForTests(null));

describe("Trace store", () => {
  it("loads the newest Trace and its ordered detail", async () => {
    const client = fakeClient();
    setTraceClientFactoryForTests(() => client);
    setActivePinia(createPinia());
    const store = useTraceStore();

    await store.initialize();

    expect(store.traces.map((trace) => trace.id)).toEqual(["trace_1", "trace_2"]);
    expect(store.selectedTraceId).toBe("trace_1");
    expect(store.detail?.spans.map((span) => span.sequence)).toEqual([1, 2]);
  });

  it("applies execution and status filters and clears stale detail for an empty result", async () => {
    const client = fakeClient({ empty: true });
    setTraceClientFactoryForTests(() => client);
    setActivePinia(createPinia());
    const store = useTraceStore();
    store.setExecutionType("aiops");
    store.setStatus("failed");

    await store.applyFilters();

    expect(client.listTraces).toHaveBeenCalledWith({
      executionType: "aiops",
      status: "failed",
      limit: 100
    });
    expect(store.traces).toEqual([]);
    expect(store.detail).toBeNull();
    expect(store.selectedTraceId).toBeNull();
  });
});

function fakeClient(options: { readonly empty?: boolean } = {}): TraceClient & {
  readonly listTraces: ReturnType<typeof vi.fn>;
} {
  return {
    getTrace: vi.fn(async (traceId: string) => detail(traceId)),
    listTraces: vi.fn(async () => ({
      items: options.empty === true ? [] : [trace(), trace({ id: "trace_2", executionType: "aiops" })]
    }))
  };
}

function trace(overrides: Partial<AgentTraceSummary> = {}): AgentTraceSummary {
  return {
    id: "trace_1",
    executionType: "chat",
    resourceType: "chat_session",
    resourceId: "chat_1",
    requestId: "req_1",
    status: "succeeded",
    summary: "Chat completed",
    errorCategory: null,
    metadata: {},
    startedAt: "2026-08-06T00:00:00.000Z",
    completedAt: "2026-08-06T00:00:01.000Z",
    durationMs: 1000,
    ...overrides
  };
}

function detail(traceId = "trace_1"): AgentTraceDetailResponse {
  const traceValue = trace({ id: traceId });
  return {
    trace: traceValue,
    spans: [
      {
        id: "span_1",
        traceId,
        parentSpanId: null,
        externalId: null,
        sequence: 1,
        kind: "agent",
        name: "chat.agent",
        status: "succeeded",
        summary: "Agent completed",
        attributes: {},
        startedAt: traceValue.startedAt,
        completedAt: traceValue.completedAt,
        durationMs: 1000
      },
      {
        id: "span_2",
        traceId,
        parentSpanId: "span_1",
        externalId: "tool_1",
        sequence: 2,
        kind: "tool",
        name: "knowledge_retrieval",
        status: "succeeded",
        summary: "Retrieved 2 references",
        attributes: { credential: "[REDACTED]" },
        startedAt: traceValue.startedAt,
        completedAt: traceValue.completedAt,
        durationMs: 120
      }
    ]
  };
}
