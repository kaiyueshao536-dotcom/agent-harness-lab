<script setup lang="ts">
import { computed } from "vue";
import { Bot, BrainCircuit, Database, FileText, RefreshCw, Wrench } from "lucide-vue-next";

import type { AgentTraceSpan, AgentTraceSpanKind } from "@agent-py/api-contracts";

interface TimelineSpan {
  readonly span: AgentTraceSpan;
  readonly depth: number;
  readonly attemptLabel: string | null;
  readonly attemptCountLabel: string | null;
  readonly errorCategory: string | null;
}

const props = defineProps<{ readonly spans: readonly AgentTraceSpan[] }>();

const orderedSpans = computed<TimelineSpan[]>(() => {
  const spans = [...props.spans].sort((left, right) => left.sequence - right.sequence);
  const spansById = new Map(spans.map((span) => [span.id, span]));
  return spans.map((span) => ({
    span,
    depth: spanDepth(span, spansById),
    attemptLabel: attemptLabel(span),
    attemptCountLabel: attemptCountLabel(span),
    errorCategory: safeString(span.attributes.errorCategory)
  }));
});

const labels: Record<AgentTraceSpanKind, string> = {
  agent: "Agent",
  planner: "规划",
  executor: "执行",
  replanner: "重规划",
  tool: "工具",
  attempt: "尝试",
  retrieval: "检索",
  model: "模型",
  report: "报告"
};

function spanDepth(span: AgentTraceSpan, spansById: ReadonlyMap<string, AgentTraceSpan>): number {
  let current = span;
  let depth = 0;
  const visited = new Set([span.id]);
  while (current.parentSpanId !== null) {
    const parent = spansById.get(current.parentSpanId);
    if (parent === undefined || visited.has(parent.id)) return 0;
    visited.add(parent.id);
    current = parent;
    depth += 1;
  }
  return depth;
}

function safeInteger(value: unknown): number | null {
  return typeof value === "number" && Number.isSafeInteger(value) && value > 0 ? value : null;
}

function safeString(value: unknown): string | null {
  return typeof value === "string" && value.trim().length > 0 ? value.trim() : null;
}

function attemptLabel(span: AgentTraceSpan): string | null {
  if (span.kind !== "attempt") return null;
  const attemptNumber = safeInteger(span.attributes.attemptNumber);
  const maxAttempts = safeInteger(span.attributes.maxAttempts);
  return attemptNumber !== null && maxAttempts !== null
    ? `第 ${attemptNumber}/${maxAttempts} 次尝试`
    : "连接尝试";
}

function attemptCountLabel(span: AgentTraceSpan): string | null {
  if (span.kind !== "tool") return null;
  const attemptCount = safeInteger(span.attributes.attemptCount);
  return attemptCount === null ? null : `共 ${attemptCount} 次 Attempt`;
}

function iconFor(kind: AgentTraceSpanKind) {
  if (kind === "tool") return Wrench;
  if (kind === "attempt") return RefreshCw;
  if (kind === "retrieval") return Database;
  if (kind === "report") return FileText;
  if (kind === "model" || kind === "planner" || kind === "replanner") return BrainCircuit;
  return Bot;
}

function statusLabel(status: AgentTraceSpan["status"]): string {
  return { running: "执行中", succeeded: "成功", failed: "失败" }[status];
}
</script>

<template>
  <ol v-if="orderedSpans.length > 0" class="trace-timeline" aria-label="Span 执行时间线">
    <li
      v-for="item in orderedSpans"
      :key="item.span.id"
      class="trace-timeline__item"
      :data-depth="item.depth"
      :data-parent-span-id="item.span.parentSpanId ?? undefined"
      :style="{ '--trace-depth': item.depth }"
    >
      <span v-if="item.depth > 0" class="trace-timeline__branch" aria-hidden="true">
        {{ "↳".repeat(item.depth) }}
      </span>
      <span class="trace-timeline__marker" aria-hidden="true">
        <component :is="iconFor(item.span.kind)" :size="16" />
      </span>
      <article>
        <header>
          <span class="trace-timeline__sequence">#{{ item.span.sequence }}</span>
          <strong>{{ item.span.name }}</strong>
          <span class="trace-timeline__kind">{{ labels[item.span.kind] }}</span>
          <span class="trace-timeline__status" :data-status="item.span.status">
            {{ statusLabel(item.span.status) }}
          </span>
        </header>
        <div v-if="item.attemptLabel || item.attemptCountLabel || item.errorCategory" class="trace-timeline__metadata">
          <span v-if="item.attemptLabel">{{ item.attemptLabel }}</span>
          <span v-if="item.attemptCountLabel">{{ item.attemptCountLabel }}</span>
          <span v-if="item.errorCategory">错误类别：{{ item.errorCategory }}</span>
        </div>
        <p v-if="item.span.summary">{{ item.span.summary }}</p>
        <footer>
          <span>{{ item.span.durationMs === null ? "尚未结束" : `${item.span.durationMs} ms` }}</span>
          <code>{{ item.span.id }}</code>
        </footer>
      </article>
    </li>
  </ol>
  <p v-else class="trace-timeline__empty">该 Trace 暂无 Span 记录。</p>
</template>

<style scoped>
.trace-timeline { list-style: none; margin: 0; padding: 0.2rem 0 1rem; overflow-x: auto; }
.trace-timeline__item { --trace-depth: 0; display: grid; gap: 0.8rem; grid-template-columns: 2rem minmax(0, 1fr); margin-inline-start: calc(var(--trace-depth) * 1.5rem); min-width: 28rem; position: relative; transition: margin 120ms ease; }
.trace-timeline__item:not(:last-child)::before { background: var(--line); bottom: 0; content: ""; left: 0.96rem; position: absolute; top: 2rem; width: 1px; }
.trace-timeline__branch { color: var(--text-tertiary); font-size: 1rem; left: -1.15rem; letter-spacing: -0.25rem; position: absolute; top: 0.45rem; transform: translateX(calc((var(--trace-depth) - 1) * -0.7rem)); }
.trace-timeline__marker { align-items: center; background: var(--surface); border: 1px solid var(--line-strong); border-radius: 50%; color: var(--accent-strong); display: inline-flex; height: 2rem; justify-content: center; position: relative; width: 2rem; z-index: 1; }
.trace-timeline article { border-bottom: 1px solid var(--line); min-width: 0; padding: 0.2rem 0 1.1rem; }
.trace-timeline header { align-items: center; display: flex; flex-wrap: wrap; gap: 0.45rem; }
.trace-timeline header strong { font-size: 0.88rem; }
.trace-timeline__sequence, .trace-timeline__kind, .trace-timeline__status, .trace-timeline__metadata span { border-radius: 999px; font-size: 0.66rem; font-weight: 700; padding: 0.18rem 0.42rem; }
.trace-timeline__sequence, .trace-timeline__kind { background: var(--surface-muted); color: var(--text-secondary); }
.trace-timeline__status[data-status="succeeded"] { background: var(--status-success-bg); color: var(--status-success-text); }
.trace-timeline__status[data-status="failed"] { background: var(--status-danger-bg); color: var(--status-danger-text); }
.trace-timeline__status[data-status="running"] { background: var(--status-running-bg); color: var(--status-running-text); }
.trace-timeline__metadata { display: flex; flex-wrap: wrap; gap: 0.4rem; margin-top: 0.55rem; }
.trace-timeline__metadata span { background: var(--surface-muted); color: var(--text-secondary); }
.trace-timeline p { color: var(--text-secondary); font-size: 0.78rem; line-height: 1.55; margin: 0.55rem 0; }
.trace-timeline footer { color: var(--text-tertiary); display: flex; font-size: 0.68rem; gap: 0.75rem; justify-content: space-between; }
.trace-timeline code { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.trace-timeline__empty { color: var(--text-tertiary); font-size: 0.82rem; padding: 2rem; text-align: center; }
@media (prefers-reduced-motion: reduce) { .trace-timeline__item { transition: none; } }
</style>
