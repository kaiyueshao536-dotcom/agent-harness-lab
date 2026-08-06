// @vitest-environment jsdom

import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, describe, expect, it } from "vitest";

import type { AgentTraceDetailResponse } from "@agent-py/api-contracts";

import AgentTraceTimeline from "../src/components/AgentTraceTimeline.vue";
import TraceView from "../src/views/TraceView.vue";
import { setTraceClientFactoryForTests } from "../src/stores/traces";

afterEach(() => setTraceClientFactoryForTests(null));

describe("Trace workspace", () => {
  it("renders spans by sequence without exposing raw attributes", () => {
    const detail = traceDetail();
    const wrapper = mount(AgentTraceTimeline, { props: { spans: [...detail.spans].reverse() } });

    expect(wrapper.findAll("li").map((item) => item.text())).toEqual([
      expect.stringContaining("#1"),
      expect.stringContaining("#2")
    ]);
    expect(wrapper.text()).toContain("knowledge_retrieval");
    expect(wrapper.text()).toContain("Retrieved 2 references");
    expect(wrapper.text()).not.toContain("RAW_SECRET_ATTRIBUTE");
  });

  it("renders real list data, metrics, filters, and selected Trace detail", async () => {
    const detail = traceDetail();
    setTraceClientFactoryForTests(() => ({
      getTrace: async () => detail,
      listTraces: async () => ({ items: [detail.trace] })
    }));
    setActivePinia(createPinia());
    const wrapper = mount(TraceView);
    await flushPromises();

    expect(wrapper.text()).toContain("执行记录");
    expect(wrapper.text()).toContain("Chat completed");
    expect(wrapper.text()).toContain("Span 数量");
    expect(wrapper.text()).toContain("工具调用");
    expect(wrapper.text()).toContain("span_2");
    expect(wrapper.findAll("select")).toHaveLength(2);
  });

  it("shows a truthful empty state when the API returns no traces", async () => {
    setTraceClientFactoryForTests(() => ({
      getTrace: async () => traceDetail(),
      listTraces: async () => ({ items: [] })
    }));
    setActivePinia(createPinia());
    const wrapper = mount(TraceView);
    await flushPromises();

    expect(wrapper.text()).toContain("还没有执行记录");
    expect(wrapper.text()).toContain("运行一次 Chat 或 AIOps 任务后");
  });
});

function traceDetail(): AgentTraceDetailResponse {
  return {
    trace: {
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
      durationMs: 1000
    },
    spans: [
      {
        id: "span_1",
        traceId: "trace_1",
        parentSpanId: null,
        externalId: null,
        sequence: 1,
        kind: "agent",
        name: "chat.agent",
        status: "succeeded",
        summary: "Agent completed",
        attributes: {},
        startedAt: "2026-08-06T00:00:00.000Z",
        completedAt: "2026-08-06T00:00:01.000Z",
        durationMs: 1000
      },
      {
        id: "span_2",
        traceId: "trace_1",
        parentSpanId: "span_1",
        externalId: "tool_1",
        sequence: 2,
        kind: "tool",
        name: "knowledge_retrieval",
        status: "succeeded",
        summary: "Retrieved 2 references",
        attributes: { raw: "RAW_SECRET_ATTRIBUTE" },
        startedAt: "2026-08-06T00:00:00.100Z",
        completedAt: "2026-08-06T00:00:00.220Z",
        durationMs: 120
      }
    ]
  };
}
