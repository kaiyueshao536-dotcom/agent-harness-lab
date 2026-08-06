export type AgentTraceExecutionType = "chat" | "aiops";
export type AgentTraceStatus = "running" | "succeeded" | "failed";
export type AgentTraceSpanKind =
  | "agent"
  | "planner"
  | "executor"
  | "replanner"
  | "tool"
  | "retrieval"
  | "model"
  | "report";

export interface AgentTraceSummary {
  readonly id: string;
  readonly executionType: AgentTraceExecutionType;
  readonly resourceType: string;
  readonly resourceId: string;
  readonly requestId: string | null;
  readonly status: AgentTraceStatus;
  readonly summary: string | null;
  readonly errorCategory: string | null;
  readonly metadata: Record<string, unknown>;
  readonly startedAt: string;
  readonly completedAt: string | null;
  readonly durationMs: number | null;
}

export interface AgentTraceSpan {
  readonly id: string;
  readonly traceId: string;
  readonly parentSpanId: string | null;
  readonly externalId: string | null;
  readonly sequence: number;
  readonly kind: AgentTraceSpanKind;
  readonly name: string;
  readonly status: AgentTraceStatus;
  readonly summary: string | null;
  readonly attributes: Record<string, unknown>;
  readonly startedAt: string;
  readonly completedAt: string | null;
  readonly durationMs: number | null;
}

export interface AgentTraceListResponse {
  readonly items: readonly AgentTraceSummary[];
}

export interface AgentTraceDetailResponse {
  readonly trace: AgentTraceSummary;
  readonly spans: readonly AgentTraceSpan[];
}

export interface AgentTraceListFilters {
  readonly executionType?: AgentTraceExecutionType;
  readonly status?: AgentTraceStatus;
  readonly resourceType?: string;
  readonly resourceId?: string;
  readonly limit?: number;
}
