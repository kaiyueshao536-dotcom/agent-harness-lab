import type { AgentTraceExecutionType } from "./traces";

export type EvaluationRuleKind =
  | "contains_all"
  | "excludes_all"
  | "required_tools"
  | "min_references"
  | "max_duration_ms"
  | "max_tool_calls"
  | "trace_succeeded";

export interface EvaluationRule {
  readonly kind: EvaluationRuleKind;
  readonly values: readonly string[];
  readonly threshold: number | null;
  readonly description: string;
}

export interface EvaluationGate {
  readonly minPassRate: number;
  readonly minAverageScore: number;
  readonly maxDurationRegressionPercent: number | null;
}

export interface EvaluationCaseInput {
  readonly name: string;
  readonly executionType: AgentTraceExecutionType;
  readonly inputSummary: string;
  readonly rules: readonly EvaluationRule[];
}

export interface EvaluationCase extends EvaluationCaseInput {
  readonly id: string;
  readonly sequence: number;
}

export interface EvaluationDatasetSummary {
  readonly id: string;
  readonly name: string;
  readonly version: string;
  readonly description: string;
  readonly gate: EvaluationGate;
  readonly caseCount: number;
  readonly createdAt: string;
}

export interface EvaluationDatasetDetail extends EvaluationDatasetSummary {
  readonly cases: readonly EvaluationCase[];
}

export interface CreateEvaluationDatasetRequest {
  readonly name: string;
  readonly version: string;
  readonly description: string;
  readonly gate: EvaluationGate;
  readonly cases: readonly EvaluationCaseInput[];
}

export interface EvaluationBaselineDelta {
  readonly passRatePoints?: number;
  readonly averageScorePoints?: number;
  readonly durationPercent?: number | null;
  readonly toolCallCount?: number;
}

export interface EvaluationRunSummary {
  readonly id: string;
  readonly datasetId: string;
  readonly candidateLabel: string;
  readonly baselineRunId: string | null;
  readonly status: "completed";
  readonly gateStatus: "passed" | "failed";
  readonly passRate: number;
  readonly averageScore: number;
  readonly averageDurationMs: number | null;
  readonly totalToolCalls: number;
  readonly baselineDelta: EvaluationBaselineDelta;
  readonly gateFailures: readonly string[];
  readonly createdAt: string;
  readonly completedAt: string | null;
}

export interface EvaluationRuleCheck {
  readonly kind: EvaluationRuleKind;
  readonly passed: boolean;
  readonly expected: string;
  readonly actual: string;
}

export interface EvaluationCaseResult {
  readonly id: string;
  readonly caseId: string;
  readonly sequence: number;
  readonly traceId: string;
  readonly status: "passed" | "failed";
  readonly score: number;
  readonly outputSummary: string;
  readonly metrics: Readonly<Record<string, string | number | null>>;
  readonly checks: readonly EvaluationRuleCheck[];
}

export interface RunEvaluationRequest {
  readonly candidateLabel: string;
  readonly baselineRunId?: string | null;
  readonly traceBindings: Readonly<Record<string, string>>;
}

export interface EvaluationDatasetListResponse {
  readonly items: readonly EvaluationDatasetSummary[];
}

export interface EvaluationRunListResponse {
  readonly items: readonly EvaluationRunSummary[];
}

export interface EvaluationRunDetailResponse {
  readonly run: EvaluationRunSummary;
  readonly results: readonly EvaluationCaseResult[];
}
