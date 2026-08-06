<script setup lang="ts">
import { computed } from "vue";
import { Bot, BrainCircuit, Database, FileText, Wrench } from "lucide-vue-next";

import type { AgentTraceSpan, AgentTraceSpanKind } from "@agent-py/api-contracts";

const props = defineProps<{ readonly spans: readonly AgentTraceSpan[] }>();

const orderedSpans = computed(() => [...props.spans].sort((left, right) => left.sequence - right.sequence));

const labels: Record<AgentTraceSpanKind, string> = {
  agent: "Agent",
  planner: "规划",
  executor: "执行",
  replanner: "重规划",
  tool: "工具",
  retrieval: "检索",
  model: "模型",
  report: "报告"
};

function iconFor(kind: AgentTraceSpanKind) {
  if (kind === "tool") return Wrench;
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
    <li v-for="span in orderedSpans" :key="span.id" class="trace-timeline__item">
      <span class="trace-timeline__marker" aria-hidden="true">
        <component :is="iconFor(span.kind)" :size="16" />
      </span>
      <article>
        <header>
          <span class="trace-timeline__sequence">#{{ span.sequence }}</span>
          <strong>{{ span.name }}</strong>
          <span class="trace-timeline__kind">{{ labels[span.kind] }}</span>
          <span class="trace-timeline__status" :data-status="span.status">
            {{ statusLabel(span.status) }}
          </span>
        </header>
        <p v-if="span.summary">{{ span.summary }}</p>
        <footer>
          <span>{{ span.durationMs === null ? "尚未结束" : `${span.durationMs} ms` }}</span>
          <code>{{ span.id }}</code>
        </footer>
      </article>
    </li>
  </ol>
  <p v-else class="trace-timeline__empty">该 Trace 暂无 Span 记录。</p>
</template>

<style scoped>
.trace-timeline { list-style: none; margin: 0; padding: 0.2rem 0 1rem; }
.trace-timeline__item { display: grid; gap: 0.8rem; grid-template-columns: 2rem minmax(0, 1fr); position: relative; }
.trace-timeline__item:not(:last-child)::before { background: var(--line); bottom: 0; content: ""; left: 0.96rem; position: absolute; top: 2rem; width: 1px; }
.trace-timeline__marker { align-items: center; background: var(--surface); border: 1px solid var(--line-strong); border-radius: 50%; color: var(--accent-strong); display: inline-flex; height: 2rem; justify-content: center; position: relative; width: 2rem; z-index: 1; }
.trace-timeline article { border-bottom: 1px solid var(--line); min-width: 0; padding: 0.2rem 0 1.1rem; }
.trace-timeline header { align-items: center; display: flex; flex-wrap: wrap; gap: 0.45rem; }
.trace-timeline header strong { font-size: 0.88rem; }
.trace-timeline__sequence, .trace-timeline__kind, .trace-timeline__status { border-radius: 999px; font-size: 0.66rem; font-weight: 700; padding: 0.18rem 0.42rem; }
.trace-timeline__sequence, .trace-timeline__kind { background: var(--surface-muted); color: var(--text-secondary); }
.trace-timeline__status[data-status="succeeded"] { background: var(--status-success-bg); color: var(--status-success-text); }
.trace-timeline__status[data-status="failed"] { background: var(--status-danger-bg); color: var(--status-danger-text); }
.trace-timeline__status[data-status="running"] { background: var(--status-running-bg); color: var(--status-running-text); }
.trace-timeline p { color: var(--text-secondary); font-size: 0.78rem; line-height: 1.55; margin: 0.55rem 0; }
.trace-timeline footer { color: var(--text-tertiary); display: flex; font-size: 0.68rem; gap: 0.75rem; justify-content: space-between; }
.trace-timeline code { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.trace-timeline__empty { color: var(--text-tertiary); font-size: 0.82rem; padding: 2rem; text-align: center; }
</style>
