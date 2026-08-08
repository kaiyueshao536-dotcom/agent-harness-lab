<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import { Beaker, CheckCircle2, GitCompare, Play, Plus, XCircle } from "lucide-vue-next";

import type {
  AgentTraceSummary,
  EvaluationCaseInput,
  EvaluationRule,
  EvaluationRuleKind
} from "@agent-py/api-contracts";

import AppEmptyState from "../components/AppEmptyState.vue";
import AppErrorState from "../components/AppErrorState.vue";
import AppLoadingState from "../components/AppLoadingState.vue";
import { createTraceClient } from "../traces/traceClient";
import { useEvaluationStore } from "../stores/evaluations";

const evaluations = useEvaluationStore();
const traces = ref<readonly AgentTraceSummary[]>([]);
const showCreate = ref(false);
const datasetName = ref("核心 Agent 回归集");
const datasetVersion = ref("v1");
const datasetDescription = ref("用真实 P1 Trace 验证回答质量、工具使用、引用和延迟。");
const minPassRate = ref(1);
const minAverageScore = ref(0.8);
const maxDurationRegressionPercent = ref<number | null>(20);
const stagedCases = ref<EvaluationCaseInput[]>([]);
const stagedRules = ref<EvaluationRule[]>([]);
const caseName = ref("");
const caseExecutionType = ref<"chat" | "aiops">("chat");
const caseInputSummary = ref("");
const ruleKind = ref<EvaluationRuleKind>("trace_succeeded");
const ruleValue = ref("");
const ruleThreshold = ref(1);
const traceBindings = reactive<Record<string, string>>({});
const candidateLabel = ref("P2 candidate");
const baselineRunId = ref("");

const valueRuleKinds = new Set<EvaluationRuleKind>([
  "contains_all",
  "excludes_all",
  "required_tools"
]);
const thresholdRuleKinds = new Set<EvaluationRuleKind>([
  "min_references",
  "max_duration_ms",
  "max_tool_calls"
]);
const canRun = computed(() => {
  const cases = evaluations.selectedDataset?.cases ?? [];
  return cases.length > 0 && cases.every((item) => Boolean(traceBindings[item.id]));
});

onMounted(() => {
  void Promise.all([
    evaluations.initialize(),
    createTraceClient().listTraces({ limit: 100 }).then((value) => {
      traces.value = value.items;
    })
  ]).catch(() => undefined);
});

onBeforeUnmount(() => evaluations.reset());

function run(operation: () => Promise<unknown>): void {
  void operation().catch(() => undefined);
}

function tracesFor(executionType: "chat" | "aiops"): readonly AgentTraceSummary[] {
  return traces.value.filter((trace) => trace.executionType === executionType);
}

function buildRule(): EvaluationRule | null {
  if (valueRuleKinds.has(ruleKind.value)) {
    const values = ruleValue.value.split(",").map((value) => value.trim()).filter(Boolean);
    if (values.length === 0) return null;
    return { kind: ruleKind.value, values, threshold: null, description: "" };
  }
  if (thresholdRuleKinds.has(ruleKind.value)) {
    return { kind: ruleKind.value, values: [], threshold: ruleThreshold.value, description: "" };
  }
  return { kind: "trace_succeeded", values: [], threshold: null, description: "" };
}

function addRule(): void {
  const rule = buildRule();
  if (rule === null) return;
  stagedRules.value = [...stagedRules.value, rule];
  ruleKind.value = "trace_succeeded";
  ruleValue.value = "";
}

function addCase(): void {
  const currentRule = buildRule();
  const rules = stagedRules.value.length > 0
    ? stagedRules.value
    : (currentRule === null ? [] : [currentRule]);
  if (
    rules.length === 0
    || caseName.value.trim() === ""
    || caseInputSummary.value.trim() === ""
  ) return;
  stagedCases.value = [...stagedCases.value, {
    name: caseName.value.trim(),
    executionType: caseExecutionType.value,
    inputSummary: caseInputSummary.value.trim(),
    rules: [...rules]
  }];
  caseName.value = "";
  caseInputSummary.value = "";
  stagedRules.value = [];
  ruleKind.value = "trace_succeeded";
  ruleValue.value = "";
}

async function createDataset(): Promise<void> {
  if (stagedCases.value.length === 0) return;
  await evaluations.createDataset({
    name: datasetName.value,
    version: datasetVersion.value,
    description: datasetDescription.value,
    gate: {
      minPassRate: minPassRate.value,
      minAverageScore: minAverageScore.value,
      maxDurationRegressionPercent: maxDurationRegressionPercent.value
    },
    cases: stagedCases.value
  });
  showCreate.value = false;
  stagedCases.value = [];
  stagedRules.value = [];
}

async function selectDataset(datasetId: string): Promise<void> {
  Object.keys(traceBindings).forEach((key) => delete traceBindings[key]);
  baselineRunId.value = "";
  await evaluations.selectDataset(datasetId);
}

async function submitRun(): Promise<void> {
  await evaluations.runDataset({
    candidateLabel: candidateLabel.value,
    traceBindings: { ...traceBindings },
    ...(baselineRunId.value === "" ? {} : { baselineRunId: baselineRunId.value })
  });
}

function percentage(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function delta(value: number | null | undefined, suffix = ""): string {
  if (value === undefined || value === null) return "—";
  const prefix = value > 0 ? "+" : "";
  return `${prefix}${value}${suffix}`;
}

function caseNameFor(caseId: string): string {
  return evaluations.selectedDataset?.cases.find((item) => item.id === caseId)?.name ?? caseId;
}
</script>

<template>
  <section class="evaluation-view" aria-label="自动评测工作台">
    <aside class="evaluation-view__catalog">
      <header>
        <div><p>Evaluation Harness</p><h2>自动评测</h2></div>
        <button type="button" @click="showCreate = !showCreate"><Plus :size="17" /> 新建版本</button>
      </header>
      <AppLoadingState v-if="evaluations.isLoading && evaluations.datasets.length === 0" label="正在加载评测集" />
      <AppErrorState v-else-if="evaluations.errorMessage && evaluations.datasets.length === 0" :message="evaluations.errorMessage" :can-retry="true" @retry="run(evaluations.initialize)" />
      <AppEmptyState v-else-if="evaluations.datasets.length === 0" title="还没有评测集" detail="创建一个不可变版本，用真实 Agent Trace 建立回归基线。" />
      <ol v-else>
        <li v-for="dataset in evaluations.datasets" :key="dataset.id">
          <button type="button" :class="{ active: evaluations.selectedDataset?.id === dataset.id }" @click="run(() => selectDataset(dataset.id))">
            <strong>{{ dataset.name }}</strong><span>{{ dataset.version }} · {{ dataset.caseCount }} cases</span>
          </button>
        </li>
      </ol>
    </aside>

    <main class="evaluation-view__main">
      <section v-if="showCreate" class="evaluation-card evaluation-create">
        <header><div><p>Immutable dataset</p><h2>创建评测集版本</h2></div></header>
        <div class="evaluation-grid">
          <label>名称<input v-model="datasetName" /></label>
          <label>版本<input v-model="datasetVersion" /></label>
          <label class="wide">说明<textarea v-model="datasetDescription" rows="2" /></label>
          <label>最低通过率<input v-model.number="minPassRate" type="number" min="0" max="1" step="0.05" /></label>
          <label>最低平均分<input v-model.number="minAverageScore" type="number" min="0" max="1" step="0.05" /></label>
          <label>最大耗时回退 %<input v-model.number="maxDurationRegressionPercent" type="number" min="0" /></label>
        </div>
        <div class="case-builder">
          <div class="rule-staging">
            <button class="secondary" type="button" @click="addRule"><Plus :size="15" /> 暂存当前规则</button>
            <ol v-if="stagedRules.length > 0">
              <li v-for="(item, index) in stagedRules" :key="`${item.kind}-${index}`">
                {{ index + 1 }}. {{ item.kind }}
              </li>
            </ol>
          </div>
          <h3>添加案例</h3>
          <div class="evaluation-grid">
            <label>案例名<input v-model="caseName" placeholder="知识库回答包含出处" /></label>
            <label>执行类型<select v-model="caseExecutionType"><option value="chat">Chat</option><option value="aiops">AIOps</option></select></label>
            <label class="wide">输入摘要<input v-model="caseInputSummary" placeholder="只记录任务摘要，不复制完整提示词" /></label>
            <label>规则<select v-model="ruleKind"><option value="trace_succeeded">Trace 成功</option><option value="contains_all">包含全部文本</option><option value="excludes_all">排除全部文本</option><option value="required_tools">必须调用工具</option><option value="min_references">最少引用数</option><option value="max_duration_ms">最大耗时 ms</option><option value="max_tool_calls">最大工具数</option></select></label>
            <label v-if="valueRuleKinds.has(ruleKind)">期望值（逗号分隔）<input v-model="ruleValue" /></label>
            <label v-if="thresholdRuleKinds.has(ruleKind)">阈值<input v-model.number="ruleThreshold" type="number" min="0" /></label>
          </div>
          <button class="secondary" type="button" @click="addCase"><Plus :size="15" /> 暂存案例</button>
          <ul class="staged-cases"><li v-for="(item, index) in stagedCases" :key="`${item.name}-${index}`"><strong>{{ item.name }}</strong><span>{{ item.executionType }} · {{ item.rules[0]?.kind }}</span></li></ul>
        </div>
        <button class="primary" type="button" :disabled="stagedCases.length === 0 || evaluations.isLoading" @click="run(createDataset)">保存不可变版本</button>
      </section>

      <template v-if="evaluations.selectedDataset">
        <section class="evaluation-card dataset-hero">
          <div><p>Dataset {{ evaluations.selectedDataset.version }}</p><h1>{{ evaluations.selectedDataset.name }}</h1><span>{{ evaluations.selectedDataset.description }}</span></div>
          <dl><div><dt>案例</dt><dd>{{ evaluations.selectedDataset.caseCount }}</dd></div><div><dt>通过率门禁</dt><dd>{{ percentage(evaluations.selectedDataset.gate.minPassRate) }}</dd></div><div><dt>平均分门禁</dt><dd>{{ percentage(evaluations.selectedDataset.gate.minAverageScore) }}</dd></div></dl>
        </section>

        <section class="evaluation-card">
          <header><div><p>Trace replay</p><h2>绑定真实 Trace 并运行</h2></div><span>不会再次调用模型或 CLS</span></header>
          <div class="binding-list">
            <label v-for="item in evaluations.selectedDataset.cases" :key="item.id">
              <span><strong>{{ item.sequence }}. {{ item.name }}</strong><small>{{ item.executionType }} · {{ item.inputSummary }}</small></span>
              <select v-model="traceBindings[item.id]"><option value="">选择 Trace（成功或失败）</option><option v-for="trace in tracesFor(item.executionType)" :key="trace.id" :value="trace.id">[{{ trace.status }}] {{ trace.summary || trace.resourceId }} · {{ trace.durationMs ?? '—' }} ms</option></select>
            </label>
          </div>
          <div class="run-controls"><label>候选版本<input v-model="candidateLabel" /></label><label>对比基线<select v-model="baselineRunId"><option value="">不对比</option><option v-for="runItem in evaluations.runs" :key="runItem.id" :value="runItem.id">{{ runItem.candidateLabel }} · {{ percentage(runItem.averageScore) }}</option></select></label><button class="primary" type="button" :disabled="!canRun || evaluations.isRunning" @click="run(submitRun)"><Play :size="16" /> {{ evaluations.isRunning ? '评测中…' : '运行评测' }}</button></div>
        </section>

        <section v-if="evaluations.report" class="evaluation-card report">
          <header><div><p>Evaluation report</p><h2>{{ evaluations.report.run.candidateLabel }}</h2></div><span class="gate" :data-status="evaluations.report.run.gateStatus">{{ evaluations.report.run.gateStatus === 'passed' ? '门禁通过' : '门禁失败' }}</span></header>
          <div class="report-metrics"><article><CheckCircle2 :size="17" /><span>通过率</span><strong>{{ percentage(evaluations.report.run.passRate) }}</strong></article><article><Beaker :size="17" /><span>平均分</span><strong>{{ percentage(evaluations.report.run.averageScore) }}</strong></article><article><GitCompare :size="17" /><span>平均耗时</span><strong>{{ Math.round(evaluations.report.run.averageDurationMs ?? 0) }} ms</strong></article><article><span>工具调用</span><strong>{{ evaluations.report.run.totalToolCalls }}</strong></article></div>
          <section v-if="evaluations.report.run.baselineRunId" class="baseline-delta" aria-label="相对基线变化">
            <header><GitCompare :size="16" /><strong>相对基线</strong><code>{{ evaluations.report.run.baselineRunId }}</code></header>
            <dl>
              <div><dt>通过率</dt><dd>{{ delta(evaluations.report.run.baselineDelta.passRatePoints, ' pt') }}</dd></div>
              <div><dt>平均分</dt><dd>{{ delta(evaluations.report.run.baselineDelta.averageScorePoints, ' pt') }}</dd></div>
              <div><dt>耗时</dt><dd>{{ delta(evaluations.report.run.baselineDelta.durationPercent, '%') }}</dd></div>
              <div><dt>工具调用</dt><dd>{{ delta(evaluations.report.run.baselineDelta.toolCallCount) }}</dd></div>
            </dl>
          </section>
          <ul v-if="evaluations.report.run.gateFailures.length" class="gate-failures"><li v-for="failure in evaluations.report.run.gateFailures" :key="failure">{{ failure }}</li></ul>
          <div class="case-results"><article v-for="result in evaluations.report.results" :key="result.id"><header><span><CheckCircle2 v-if="result.status === 'passed'" :size="18" /><XCircle v-else :size="18" /><strong>{{ caseNameFor(result.caseId) }}</strong></span><b>{{ percentage(result.score) }}</b></header><p>{{ result.outputSummary || '无输出摘要' }}</p><ul><li v-for="check in result.checks" :key="check.kind"><span>{{ check.kind }}</span><strong :data-status="check.passed ? 'passed' : 'failed'">{{ check.passed ? '通过' : '失败' }}</strong><small>期望 {{ check.expected }}；实际 {{ check.actual }}</small></li></ul><RouterLink :to="{ path: '/traces', query: { traceId: result.traceId } }">查看 Trace {{ result.traceId }}</RouterLink></article></div>
        </section>
      </template>
      <AppEmptyState v-else-if="!showCreate" title="选择或创建评测集" detail="评测集按版本永久保存；每次运行都可以指定一个同数据集基线。" />
    </main>
  </section>
</template>

<style scoped>
.evaluation-view { display: grid; grid-template-columns: 19rem minmax(44rem, 1fr); height: 100%; min-height: 0; background: var(--surface); }
.evaluation-view__catalog { background: var(--surface-raised); border-right: 1px solid var(--line); overflow: auto; }
.evaluation-view__catalog > header, .evaluation-card > header { align-items: center; display: flex; justify-content: space-between; }
.evaluation-view__catalog > header { padding: 1.2rem; border-bottom: 1px solid var(--line); }
.evaluation-view p { color: var(--text-tertiary); font-size: .68rem; font-weight: 750; letter-spacing: .06em; margin: 0 0 .25rem; text-transform: uppercase; }
.evaluation-view h1, .evaluation-view h2, .evaluation-view h3 { margin: 0; }
.evaluation-view__catalog header button, .secondary, .primary { align-items: center; border-radius: .45rem; display: inline-flex; gap: .35rem; min-height: 2.35rem; padding: 0 .75rem; }
.evaluation-view__catalog ol { list-style: none; margin: 0; padding: 0; }
.evaluation-view__catalog li { border-bottom: 1px solid var(--line); }
.evaluation-view__catalog li button { display: grid; gap: .3rem; padding: .9rem 1.2rem; text-align: left; width: 100%; }
.evaluation-view__catalog li button.active { background: var(--surface-selected); box-shadow: inset 3px 0 var(--accent); }
.evaluation-view__catalog li span { color: var(--text-tertiary); font-size: .72rem; }
.evaluation-view__main { overflow: auto; padding: 1.5rem; }
.evaluation-card { background: var(--surface-raised); border: 1px solid var(--line); border-radius: .7rem; margin-bottom: 1rem; padding: 1.2rem; }
.evaluation-card > header { border-bottom: 1px solid var(--line); margin-bottom: 1rem; padding-bottom: .85rem; }
.evaluation-card > header > span { color: var(--text-tertiary); font-size: .72rem; }
.evaluation-grid { display: grid; gap: .8rem; grid-template-columns: repeat(3, minmax(0, 1fr)); }
.evaluation-grid .wide { grid-column: span 2; }
label { color: var(--text-secondary); display: grid; font-size: .72rem; gap: .35rem; }
input, select, textarea { background: var(--surface); border: 1px solid var(--line-strong); border-radius: .4rem; color: var(--text-primary); min-height: 2.35rem; padding: .45rem .6rem; width: 100%; }
.case-builder { border-top: 1px solid var(--line); margin-top: 1rem; padding-top: 1rem; }
.case-builder h3 { font-size: .9rem; margin-bottom: .7rem; }
.rule-staging { align-items: center; display: flex; gap: .75rem; justify-content: flex-end; }
.rule-staging .secondary { margin-top: 0; }
.rule-staging ol { color: var(--text-secondary); display: flex; flex-wrap: wrap; font-size: .7rem; gap: .8rem; margin: 0; }
.secondary { border: 1px solid var(--line-strong); margin-top: .75rem; }
.primary { background: var(--accent-strong); color: white; font-weight: 700; justify-content: center; }
.evaluation-create > .primary { margin-top: 1rem; }
.staged-cases { display: flex; flex-wrap: wrap; gap: .5rem; list-style: none; padding: .7rem 0 0; }
.staged-cases li { background: var(--surface); border: 1px solid var(--line); border-radius: .45rem; display: grid; font-size: .72rem; gap: .15rem; padding: .5rem .65rem; }
.staged-cases span { color: var(--text-tertiary); }
.dataset-hero { align-items: center; display: flex; justify-content: space-between; }
.dataset-hero h1 { font-size: 1.35rem; margin-bottom: .3rem; }
.dataset-hero > div > span { color: var(--text-secondary); font-size: .8rem; }
.dataset-hero dl { display: flex; gap: 1.8rem; margin: 0; }
.dataset-hero dl div { display: grid; gap: .2rem; }
.dataset-hero dt { color: var(--text-tertiary); font-size: .67rem; }
.dataset-hero dd { font-size: 1rem; font-weight: 750; margin: 0; }
.binding-list { display: grid; gap: .65rem; }
.binding-list label { align-items: center; background: var(--surface); border: 1px solid var(--line); border-radius: .45rem; display: grid; gap: 1rem; grid-template-columns: minmax(16rem, 1fr) minmax(20rem, 1.2fr); padding: .7rem; }
.binding-list label > span { display: grid; gap: .25rem; }
.binding-list small { color: var(--text-tertiary); }
.run-controls { align-items: end; border-top: 1px solid var(--line); display: grid; gap: .8rem; grid-template-columns: 1fr 1fr auto; margin-top: 1rem; padding-top: 1rem; }
.report .gate { border-radius: 999px; font-weight: 750; padding: .35rem .65rem; }
.gate[data-status="passed"], [data-status="passed"] { background: var(--status-success-bg); color: var(--status-success-text); }
.gate[data-status="failed"], [data-status="failed"] { background: var(--status-danger-bg); color: var(--status-danger-text); }
.report-metrics { display: grid; grid-template-columns: repeat(4, 1fr); }
.report-metrics article { border-right: 1px solid var(--line); display: grid; gap: .25rem; padding: .6rem 1rem; }
.report-metrics article:last-child { border: 0; }
.report-metrics span { color: var(--text-tertiary); font-size: .68rem; }
.baseline-delta { background: var(--surface); border: 1px solid var(--line); margin-top: 1rem; padding: .75rem; }
.baseline-delta > header { align-items: center; display: flex; gap: .45rem; }
.baseline-delta > header code { color: var(--text-tertiary); font-size: .66rem; margin-left: auto; }
.baseline-delta dl { display: grid; grid-template-columns: repeat(4, 1fr); margin: .7rem 0 0; }
.baseline-delta dl div { border-right: 1px solid var(--line); display: grid; gap: .2rem; padding: 0 .65rem; }
.baseline-delta dl div:last-child { border: 0; }
.baseline-delta dt { color: var(--text-tertiary); font-size: .66rem; }
.baseline-delta dd { font-size: .86rem; font-weight: 750; margin: 0; }
.gate-failures { background: var(--status-danger-bg); color: var(--status-danger-text); margin: 1rem 0; padding: .7rem 2rem; }
.case-results { display: grid; gap: .8rem; margin-top: 1rem; }
.case-results > article { border: 1px solid var(--line); border-radius: .5rem; padding: .8rem; }
.case-results article > header, .case-results article > header span { align-items: center; display: flex; gap: .45rem; justify-content: space-between; }
.case-results article > p { color: var(--text-secondary); font-size: .76rem; }
.case-results ul { list-style: none; padding: 0; }
.case-results li { align-items: center; border-top: 1px solid var(--line); display: grid; font-size: .7rem; gap: .7rem; grid-template-columns: 10rem 4rem 1fr; padding: .45rem 0; }
.case-results li small { color: var(--text-tertiary); }
.case-results a { color: var(--accent-strong); font-size: .72rem; }
button:disabled { cursor: not-allowed; opacity: .5; }
</style>
