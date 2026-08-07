<script setup lang="ts">
import { computed, inject, onBeforeUnmount, onMounted } from "vue";
import { routeLocationKey } from "vue-router";
import { RefreshCw, Timer, Workflow, Wrench } from "lucide-vue-next";

import type { AgentTraceExecutionType, AgentTraceStatus } from "@agent-py/api-contracts";

import AgentTraceTimeline from "../components/AgentTraceTimeline.vue";
import AppEmptyState from "../components/AppEmptyState.vue";
import AppErrorState from "../components/AppErrorState.vue";
import AppLoadingState from "../components/AppLoadingState.vue";
import { useTraceStore } from "../stores/traces";

const traces = useTraceStore();
const route = inject(routeLocationKey, null);
const spanCount = computed(() => traces.detail?.spans.length ?? 0);
const toolCount = computed(
  () => traces.detail?.spans.filter((span) => span.kind === "tool").length ?? 0
);
const failedSpanCount = computed(
  () => traces.detail?.spans.filter((span) => span.status === "failed").length ?? 0
);

onMounted(() => {
  void traces.initialize().then(async () => {
    const traceId = route?.query.traceId;
    if (typeof traceId === "string" && traceId !== traces.selectedTraceId) {
      await traces.selectTrace(traceId);
    }
  }).catch(() => undefined);
});

onBeforeUnmount(() => {
  traces.reset();
});

function run(operation: () => Promise<unknown>): void {
  void operation().catch(() => undefined);
}

function applyFilters(): void {
  run(traces.applyFilters);
}

function updateExecutionType(event: Event): void {
  traces.setExecutionType((event.target as HTMLSelectElement).value as AgentTraceExecutionType | "");
  applyFilters();
}

function updateStatus(event: Event): void {
  traces.setStatus((event.target as HTMLSelectElement).value as AgentTraceStatus | "");
  applyFilters();
}

function statusLabel(status: AgentTraceStatus): string {
  return { running: "执行中", succeeded: "成功", failed: "失败" }[status];
}

function executionLabel(executionType: AgentTraceExecutionType): string {
  return executionType === "chat" ? "Chat" : "AIOps";
}

function formatTimestamp(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "short",
    timeStyle: "medium",
    hour12: false
  }).format(new Date(value));
}
</script>

<template>
  <section class="trace-view" aria-label="Agent 执行追踪工作台">
    <aside class="trace-view__catalog">
      <header>
        <div>
          <p>Agent Trace</p>
          <h2>执行记录</h2>
        </div>
        <button type="button" title="刷新执行记录" :disabled="traces.isLoadingList" @click="run(traces.refresh)">
          <RefreshCw :size="17" aria-hidden="true" />
        </button>
      </header>

      <form class="trace-view__filters" aria-label="Trace 筛选" @submit.prevent="applyFilters">
        <label>
          <span>执行类型</span>
          <select :value="traces.executionType" @change="updateExecutionType">
            <option value="">全部类型</option>
            <option value="chat">Chat</option>
            <option value="aiops">AIOps</option>
          </select>
        </label>
        <label>
          <span>执行状态</span>
          <select :value="traces.status" @change="updateStatus">
            <option value="">全部状态</option>
            <option value="running">执行中</option>
            <option value="succeeded">成功</option>
            <option value="failed">失败</option>
          </select>
        </label>
      </form>

      <AppLoadingState v-if="traces.isLoadingList && traces.traces.length === 0" label="正在加载 Trace" />
      <AppErrorState
        v-else-if="traces.errorMessage && traces.traces.length === 0"
        :can-retry="true"
        :message="traces.errorMessage"
        @retry="run(traces.initialize)"
      />
      <AppEmptyState
        v-else-if="traces.traces.length === 0"
        title="还没有执行记录"
        detail="运行一次 Chat 或 AIOps 任务后，Trace 会自动出现在这里。"
      />
      <ol v-else class="trace-view__list">
        <li v-for="trace in traces.traces" :key="trace.id">
          <button
            type="button"
            :class="{ 'trace-view__trace--active': traces.selectedTraceId === trace.id }"
            @click="run(() => traces.selectTrace(trace.id))"
          >
            <span class="trace-view__trace-heading">
              <strong>{{ executionLabel(trace.executionType) }}</strong>
              <span :data-status="trace.status">{{ statusLabel(trace.status) }}</span>
            </span>
            <span class="trace-view__resource">{{ trace.resourceType }} · {{ trace.resourceId }}</span>
            <small>{{ formatTimestamp(trace.startedAt) }} · {{ trace.durationMs ?? "—" }} ms</small>
          </button>
        </li>
      </ol>
    </aside>

    <main class="trace-view__detail">
      <AppLoadingState v-if="traces.isLoadingDetail" label="正在加载 Trace 详情" />
      <template v-else-if="traces.detail">
        <header class="trace-view__hero">
          <span class="trace-view__hero-icon"><Workflow :size="20" aria-hidden="true" /></span>
          <div>
            <p>{{ executionLabel(traces.detail.trace.executionType) }} · {{ traces.detail.trace.resourceType }}</p>
            <h2>{{ traces.detail.trace.summary || traces.detail.trace.resourceId }}</h2>
            <code>{{ traces.detail.trace.id }}</code>
          </div>
          <span class="trace-view__hero-status" :data-status="traces.detail.trace.status">
            {{ statusLabel(traces.detail.trace.status) }}
          </span>
        </header>

        <section class="trace-view__metrics" aria-label="Trace 指标摘要">
          <article><Workflow :size="17" /><span>Span 数量</span><strong>{{ spanCount }}</strong></article>
          <article><Wrench :size="17" /><span>工具调用</span><strong>{{ toolCount }}</strong></article>
          <article><Timer :size="17" /><span>总耗时</span><strong>{{ traces.detail.trace.durationMs ?? "—" }} ms</strong></article>
          <article><span class="trace-view__failure-mark">!</span><span>失败 Span</span><strong>{{ failedSpanCount }}</strong></article>
        </section>

        <section class="trace-view__context" aria-label="Trace 上下文">
          <div><span>资源</span><code>{{ traces.detail.trace.resourceId }}</code></div>
          <div><span>Request ID</span><code>{{ traces.detail.trace.requestId ?? "—" }}</code></div>
          <div><span>开始时间</span><strong>{{ formatTimestamp(traces.detail.trace.startedAt) }}</strong></div>
          <div><span>错误类别</span><strong>{{ traces.detail.trace.errorCategory ?? "无" }}</strong></div>
        </section>

        <section class="trace-view__timeline-panel">
          <header><div><p>Execution timeline</p><h3>Span 时间线</h3></div><span>按 sequence 升序</span></header>
          <AgentTraceTimeline :spans="traces.detail.spans" />
        </section>
      </template>
      <AppEmptyState v-else title="选择一条 Trace" detail="从左侧选择执行记录，查看完整的有序 Span 时间线。" />
    </main>
  </section>
</template>

<style scoped>
.trace-view { background: var(--surface-raised); display: grid; grid-template-columns: minmax(20rem, 0.72fr) minmax(34rem, 1.8fr); height: 100%; min-height: 0; overflow: hidden; }
.trace-view__catalog { border-right: 1px solid var(--line); display: grid; grid-template-rows: auto auto minmax(0, 1fr); min-height: 0; overflow: hidden; }
.trace-view__catalog > header { align-items: center; display: flex; justify-content: space-between; padding: 1.2rem; }
.trace-view__catalog header p, .trace-view__hero p, .trace-view__timeline-panel header p { color: var(--text-tertiary); font-size: 0.68rem; font-weight: 750; letter-spacing: 0.04em; margin: 0 0 0.22rem; text-transform: uppercase; }
.trace-view__catalog h2, .trace-view__hero h2, .trace-view__timeline-panel h3 { margin: 0; }
.trace-view__catalog h2 { font-size: 1.05rem; }
.trace-view__catalog > header button { align-items: center; border: 1px solid var(--line-strong); border-radius: 0.45rem; display: inline-flex; height: 2.25rem; justify-content: center; width: 2.25rem; }
.trace-view__filters { border-bottom: 1px solid var(--line); border-top: 1px solid var(--line); display: grid; gap: 0.6rem; grid-template-columns: 1fr 1fr; padding: 0.85rem 1.2rem; }
.trace-view__filters label { display: grid; gap: 0.3rem; }
.trace-view__filters label span { color: var(--text-tertiary); font-size: 0.68rem; font-weight: 700; }
.trace-view__filters select { background: var(--surface-raised); border: 1px solid var(--line-strong); border-radius: 0.4rem; color: var(--text-primary); min-height: 2.2rem; padding: 0 0.45rem; width: 100%; }
.trace-view__catalog > :deep(.loading-state), .trace-view__catalog > :deep(.empty-state), .trace-view__catalog > :deep(.error-state) { margin: 1.2rem; }
.trace-view__list { list-style: none; margin: 0; overflow: auto; padding: 0; }
.trace-view__list li { border-bottom: 1px solid var(--line); }
.trace-view__list button { display: grid; gap: 0.5rem; padding: 0.9rem 1.2rem; text-align: left; width: 100%; }
.trace-view__list button:hover { background: var(--surface-hover); }
.trace-view__trace--active { background: var(--surface-selected) !important; box-shadow: inset 3px 0 var(--accent); }
.trace-view__trace-heading { align-items: center; display: flex; justify-content: space-between; }
.trace-view__trace-heading strong { font-size: 0.82rem; }
.trace-view__trace-heading > span, .trace-view__hero-status { border-radius: 999px; font-size: 0.66rem; font-weight: 750; padding: 0.2rem 0.48rem; }
[data-status="succeeded"] { background: var(--status-success-bg); color: var(--status-success-text); }
[data-status="failed"] { background: var(--status-danger-bg); color: var(--status-danger-text); }
[data-status="running"] { background: var(--status-running-bg); color: var(--status-running-text); }
.trace-view__resource { color: var(--text-secondary); font-size: 0.76rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.trace-view__list small { color: var(--text-tertiary); font-size: 0.67rem; }
.trace-view__detail { min-height: 0; overflow: auto; padding: clamp(1.2rem, 3vw, 2.5rem); }
.trace-view__detail > :deep(.loading-state), .trace-view__detail > :deep(.empty-state) { margin: 2rem auto; }
.trace-view__hero { align-items: center; display: grid; gap: 1rem; grid-template-columns: auto minmax(0, 1fr) auto; }
.trace-view__hero-icon { align-items: center; background: var(--accent-soft); border: 1px solid var(--accent-border); border-radius: 0.65rem; color: var(--accent-strong); display: inline-flex; height: 2.8rem; justify-content: center; width: 2.8rem; }
.trace-view__hero h2 { font-size: 1.25rem; margin-bottom: 0.35rem; }
.trace-view__hero code { color: var(--text-tertiary); font-size: 0.7rem; }
.trace-view__metrics { border: 1px solid var(--line); display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); margin-top: 1.6rem; }
.trace-view__metrics article { align-items: center; border-right: 1px solid var(--line); display: grid; gap: 0.25rem 0.55rem; grid-template-columns: auto minmax(0, 1fr); padding: 0.85rem; }
.trace-view__metrics article:last-child { border-right: 0; }
.trace-view__metrics svg, .trace-view__failure-mark { color: var(--accent-strong); grid-row: span 2; }
.trace-view__failure-mark { font-size: 1rem; font-weight: 850; text-align: center; width: 1.05rem; }
.trace-view__metrics span { color: var(--text-tertiary); font-size: 0.68rem; }
.trace-view__metrics strong { font-size: 0.92rem; }
.trace-view__context { background: var(--surface); border: 1px solid var(--line); border-top: 0; display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); }
.trace-view__context div { display: grid; gap: 0.35rem; min-width: 0; padding: 0.75rem 0.85rem; }
.trace-view__context span { color: var(--text-tertiary); font-size: 0.66rem; }
.trace-view__context code, .trace-view__context strong { font-size: 0.72rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.trace-view__timeline-panel { margin-top: 1.8rem; }
.trace-view__timeline-panel > header { align-items: end; border-bottom: 1px solid var(--line); display: flex; justify-content: space-between; margin-bottom: 1rem; padding-bottom: 0.75rem; }
.trace-view__timeline-panel h3 { font-size: 1rem; }
.trace-view__timeline-panel > header > span { color: var(--text-tertiary); font-size: 0.68rem; }
@media (max-width: 1180px) { .trace-view { grid-template-columns: minmax(18rem, 0.8fr) minmax(28rem, 1.4fr); } .trace-view__metrics, .trace-view__context { grid-template-columns: repeat(2, minmax(0, 1fr)); } .trace-view__metrics article:nth-child(2) { border-right: 0; } .trace-view__metrics article:nth-child(-n+2) { border-bottom: 1px solid var(--line); } }
</style>
