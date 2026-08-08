// @vitest-environment jsdom

import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { AiopsDiagnosticEvidenceChain, AiopsDiagnosticStep, AiopsDiagnosticSummary, SseEvent } from "@agent-py/api-contracts";

import AiopsEvidenceChain from "../src/components/AiopsEvidenceChain.vue";
import AiopsCaseLibrary from "../src/components/AiopsCaseLibrary.vue";
import AiopsReportPanel from "../src/components/AiopsReportPanel.vue";
import AiopsRunForm from "../src/components/AiopsRunForm.vue";
import AiopsTimeline from "../src/components/AiopsTimeline.vue";

beforeEach(() => {
  setActivePinia(createPinia());
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ ok: true, data: { items: [] } }), {
    headers: { "Content-Type": "application/json" },
    status: 200
  })));
});

describe("AIOps components", () => {
  it("validates optional alert context before creating a diagnosis", async () => {
    const wrapper = mount(AiopsRunForm, { props: { disabled: false, isRunning: false } });
    await wrapper.get('textarea[aria-label="诊断问题"]').setValue("Inspect latency");
    await wrapper.get('textarea[aria-label="告警上下文"]') .setValue("{not-json");
    await wrapper.get('button[type="submit"]').trigger("submit");

    expect(wrapper.text()).toContain("有效的 JSON 对象");
    expect(wrapper.emitted("run")).toBeUndefined();
  });

  it("renders a readable execution chain with collapsed tool summaries and no raw JSON", () => {
    const event: SseEvent = {
      id: "event_1",
      type: "tool.call",
      channel: "aiops",
      timestamp: "2026-07-10T00:00:01.000Z",
      toolCall: { id: "tool_1", name: "SearchLog", status: "completed", output: { raw: "x".repeat(400) } }
    };
    const chain: AiopsDiagnosticEvidenceChain = {
      task: diagnostic(),
      steps: [
        { id: "step_1", taskId: "diagnostic_1", sequence: 1, phase: "planner", status: "completed", payload: { noSopMatched: false, retrievalContext: { policy: "sop-only", query: "WorkerCpuHigh", filters: { metadata: { knowledgeType: "sop" } }, allowedKnowledgeTypes: ["sop"], excludedKnowledgeTypes: ["diagnostic-case", "document"], selected: [{ documentId: "doc_sop", source: "worker-cpu-sop.md", knowledgeType: "sop", score: 0.9567 }], fallbackReason: null }, plan: [{ tool: "SearchLog", purpose: "查询告警窗口日志" }] }, createdAt: "2026-07-10T00:00:00.000Z" },
        { id: "step_2", taskId: "diagnostic_1", sequence: 2, phase: "executor", status: "completed", payload: { tool: "SearchLog", planStep: { purpose: "查询告警窗口日志" } }, createdAt: "2026-07-10T00:00:01.000Z" },
        { id: "step_3", taskId: "diagnostic_1", sequence: 3, phase: "replanner", status: "completed", payload: { decision: "report", planIndex: 1, planLength: 1, executionFailed: false }, createdAt: "2026-07-10T00:00:02.000Z" }
      ],
      toolCalls: [{
        id: "tool_1", ownerUserId: "user_1", sessionId: null, diagnosticTaskId: "diagnostic_1", toolName: "SearchLog", status: "completed", arguments: {},
        resultSummary: JSON.stringify({ recordCount: 20, records: [{ timestamp: "2026-07-10 08:00:00", level: "ERROR", service: "checkout", event: "timeout", message: "request timeout", latency_ms: 2450 }] }),
        errorMessage: null, startedAt: "2026-07-10T00:00:01.000Z", completedAt: "2026-07-10T00:00:02.000Z", durationMs: 1000, createdAt: "2026-07-10T00:00:01.000Z"
      }],
      executions: [{
        ordinal: 1, traceId: "trace_1", status: "succeeded", summary: "completed",
        startedAt: "2026-07-10T00:00:00.000Z", completedAt: "2026-07-10T00:00:02.000Z", durationMs: 2000,
        stepIds: ["step_1", "step_2", "step_3"], toolCallIds: ["tool_1"]
      }],
      evidence: [{ id: "evidence_1", taskId: "diagnostic_1", stepId: "step_2", toolCallId: "tool_1", kind: "log", source: "SearchLog", summary: "RAW_EVIDENCE_MARKER", payload: { raw: "RAW_PAYLOAD_MARKER" }, createdAt: "2026-07-10T00:00:01.000Z" }],
      reports: [{ id: "report_1", title: "Diagnostic report", content: "Persisted report body.", payload: {}, evidenceIds: ["evidence_1"], createdAt: "2026-07-10T00:00:02.000Z" }],
      reportEvidenceLinks: [{ id: "link_1", taskId: "diagnostic_1", reportId: "report_1", evidenceId: "evidence_1", createdAt: "2026-07-10T00:00:02.000Z" }],
      checkpoints: []
    };

    const timeline = mount(AiopsTimeline, { props: { events: [event], isRunning: true } });
    expect(timeline.text()).toContain("诊断过程");
    expect(timeline.text()).toContain("已完成");
    expect(timeline.text()).toContain("SearchLog");
    expect(timeline.text()).not.toContain("raw");
    expect(timeline.text()).not.toContain("x".repeat(400));
    const execution = mount(AiopsEvidenceChain, { props: { chain } });
    expect(execution.text()).toContain("Planner · 生成 1 步诊断计划");
    expect(execution.text()).toContain("Executor · 查询告警窗口日志");
    expect(execution.text()).toContain("Replanner · 证据汇总完成，进入报告");
    expect(execution.text()).toContain("检索策略：SOP-only（仅正式 SOP）");
    expect(execution.text()).toContain("排除 diagnostic-case、document");
    expect(execution.text()).toContain("worker-cpu-sop.md · 角色 sop · 分数 0.9567");
    expect(execution.text()).toContain("历史诊断案例未进入本次规划上下文");
    expect(execution.text()).toContain("共返回 20 条日志");
    expect(execution.text()).toContain("request timeout");
    expect(execution.findAll("details")).toHaveLength(1);
    expect(execution.get("details").attributes("open")).toBeUndefined();
    expect(execution.text()).not.toContain("recordCount");
    expect(execution.text()).not.toContain("RAW_EVIDENCE_MARKER");
    expect(execution.text()).not.toContain("RAW_PAYLOAD_MARKER");
    expect(execution.text()).not.toContain("evidence_1");
    expect(execution.text()).not.toContain("Persisted report body");
  });

  it("explains an SOP retrieval fallback without breaking older step payloads", () => {
    const chain: AiopsDiagnosticEvidenceChain = {
      task: diagnostic(),
      steps: [{
        id: "step_fallback",
        taskId: "diagnostic_1",
        sequence: 1,
        phase: "planner",
        status: "completed",
        payload: {
          noSopMatched: true,
          retrievalContext: {
            policy: "sop-only",
            query: "UnknownAlert",
            filters: { metadata: { knowledgeType: "sop" } },
            allowedKnowledgeTypes: ["sop"],
            excludedKnowledgeTypes: ["diagnostic-case", "document"],
            selected: [],
            fallbackReason: "未命中正式 SOP，已退化为通用证据收集计划。"
          },
          plan: []
        },
        createdAt: "2026-07-10T00:00:00.000Z"
      }],
      toolCalls: [],
      executions: [],
      evidence: [],
      reports: [],
      reportEvidenceLinks: [],
      checkpoints: []
    };

    const fallback = mount(AiopsEvidenceChain, { props: { chain } });
    expect(fallback.text()).toContain("命中来源：0 个");
    expect(fallback.text()).toContain("退化原因：未命中正式 SOP");

    const legacyStep: AiopsDiagnosticStep = {
      ...chain.steps[0]!,
      payload: { noSopMatched: true, plan: [] }
    };
    const legacy = mount(AiopsEvidenceChain, {
      props: { chain: { ...chain, steps: [legacyStep] } }
    });
    expect(legacy.text()).toContain("未命中 SOP");
    expect(legacy.text()).not.toContain("检索策略：SOP-only");
  });

  it("separates accumulated retry history into per-trace executions", () => {
    const toolCalls = Array.from({ length: 6 }, (_, index) => ({
      id: `tool_${index + 1}`,
      ownerUserId: "user_1",
      sessionId: null,
      diagnosticTaskId: "diagnostic_1",
      toolName: index % 2 === 0 ? "knowledge_retrieval" : "SearchLog",
      status: index < 4 ? "failed" as const : "completed" as const,
      arguments: {},
      resultSummary: null,
      errorMessage: index < 4 ? "safe failure" : null,
      startedAt: `2026-08-08T23:${40 + index}:00.000Z`,
      completedAt: `2026-08-08T23:${40 + index}:01.000Z`,
      durationMs: 1000,
      createdAt: `2026-08-08T23:${40 + index}:00.000Z`
    }));
    const chain: AiopsDiagnosticEvidenceChain = {
      task: diagnostic(),
      steps: [],
      toolCalls,
      executions: [1, 2, 3].map((ordinal) => ({
        ordinal,
        traceId: `trace_${ordinal}`,
        status: ordinal < 3 ? "failed" : "succeeded",
        summary: ordinal < 3 ? "failed" : "recovered",
        startedAt: `2026-08-08T23:${40 + ordinal}:00.000Z`,
        completedAt: `2026-08-08T23:${40 + ordinal}:30.000Z`,
        durationMs: 80000 + ordinal,
        stepIds: [],
        toolCallIds: [`tool_${ordinal * 2 - 1}`, `tool_${ordinal * 2}`]
      })),
      evidence: [],
      reports: [],
      reportEvidenceLinks: [],
      checkpoints: []
    };

    const wrapper = mount(AiopsEvidenceChain, { props: { chain } });

    expect(wrapper.text()).toContain("跨 3 次执行累计 6 次工具调用");
    expect(wrapper.text()).toContain("第 1 次执行");
    expect(wrapper.text()).toContain("第 2 次执行");
    expect(wrapper.text()).toContain("第 3 次执行");
    expect(wrapper.text()).toContain("trace_3");
    expect(wrapper.findAll(".aiops-execution__group")).toHaveLength(3);
    expect(
      wrapper.findAll(".aiops-execution__meta").every((item) => item.text().includes("2 次工具调用"))
    ).toBe(true);
  });

  it("renders a persisted Markdown report as the center reading surface", () => {
    const wrapper = mount(AiopsReportPanel, {
      props: {
        report: {
          id: "report_1",
          title: "告警分析报告",
          content: "# 告警分析报告\n\n## 📋 活跃告警清单\n\n| 告警 | 级别 |\n|---|---|\n| CPU高 | 严重 |\n\n## 📊 结论\n\n需要继续核实。",
          createdAt: "2026-07-10T00:00:02.000Z"
        },
        isRunning: false,
        hasTask: true,
        taskFailed: false
      }
    });

    expect(wrapper.text()).toContain("最终诊断报告");
    expect(wrapper.text()).toContain("已沉淀");
    expect(wrapper.text()).toContain("活跃告警清单");
    expect(wrapper.find("table").exists()).toBe(true);
    expect(wrapper.find(".markdown-content--report").exists()).toBe(true);
  });

  it("explains report generation while a diagnosis is running", () => {
    const wrapper = mount(AiopsReportPanel, {
      props: { report: null, isRunning: true, hasTask: true, taskFailed: false }
    });

    expect(wrapper.text()).toContain("生成中");
    expect(wrapper.text()).toContain("正在等待诊断证据汇总");
  });

  it("offers one explicit retry action for a recoverable failed diagnosis", async () => {
    const wrapper = mount(AiopsReportPanel, {
      props: {
        report: null,
        isRunning: false,
        hasTask: true,
        taskFailed: true,
        canRetry: true,
        retrying: false
      }
    });

    const retry = wrapper.get("button.aiops-report__retry");
    expect(retry.text()).toContain("重试本次诊断");
    await retry.trigger("click");
    expect(wrapper.emitted("retry")).toEqual([[]]);
  });

  it("keeps the retry action visible when a failed diagnosis has a degraded report", async () => {
    const wrapper = mount(AiopsReportPanel, {
      props: {
        report: {
          id: "report_failed",
          title: "告警分析报告",
          content: "# 告警分析报告\n\n证据不足，无法确认根因。",
          createdAt: "2026-08-08T00:00:02.000Z"
        },
        isRunning: false,
        hasTask: true,
        taskFailed: true,
        canRetry: true,
        retrying: false
      }
    });

    expect(wrapper.text()).toContain("失败后的降级报告");
    expect(wrapper.text()).not.toContain("已沉淀");
    expect(wrapper.text()).toContain("证据不足，无法确认根因");
    const retry = wrapper.get("button.aiops-report__retry");
    await retry.trigger("click");
    expect(wrapper.emitted("retry")).toEqual([[]]);
  });

  it("lists a server-backed diagnosis case and selects its task", async () => {
    const longSummary = `# 告警分析报告\n\n${"长报告内容".repeat(80)}`;
    const wrapper = mount(AiopsCaseLibrary, {
      props: {
        cases: [{
          id: "case_1", ownerUserId: "user_1", taskId: "diagnostic_1", reportId: "report_1", documentId: "doc_1", indexTaskId: "index_1", alertName: "CheckoutLatencyHigh", service: "checkout", keywords: ["checkout", "latency"], rootCause: "", remediation: "", summary: longSummary, evidenceIds: ["evidence_1"], createdAt: "2026-07-10T00:00:00Z"
        }]
      }
    });

    expect(wrapper.text()).toContain("CheckoutLatencyHigh");
    expect(wrapper.text()).toContain("长报告内容");
    expect(wrapper.text()).not.toContain(longSummary);
    await wrapper.get("button").trigger("click");
    expect(wrapper.emitted("select")).toEqual([["diagnostic_1"]]);
    await wrapper.get('button[title="打开生成的知识文档"]').trigger("click");
    expect(wrapper.emitted("open-document")).toEqual([["doc_1"]]);
  });
});

function diagnostic(): AiopsDiagnosticSummary {
  return {
    id: "diagnostic_1",
    ownerUserId: "user_1",
    status: "succeeded",
    query: "Inspect latency",
    inputPayload: {},
    resultPayload: {},
    createdAt: "2026-07-10T00:00:00.000Z",
    updatedAt: "2026-07-10T00:00:02.000Z",
    completedAt: "2026-07-10T00:00:02.000Z",
    reports: []
  };
}
