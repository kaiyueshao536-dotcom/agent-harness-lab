"""HTTP request models shared by the API route modules."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from super_ai.evaluation.models import EvaluationRule


class RegisterRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    email: str
    display_name: str = Field(alias="displayName")
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class CreateChatSessionRequest(BaseModel):
    title: str | None = None


class AppendChatMessageRequest(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    metadata: dict[str, object] = Field(default_factory=dict)


class StreamChatMessageRequest(BaseModel):
    content: str
    metadata: dict[str, object] = Field(default_factory=dict)


class UpdateChatMemoryRequest(BaseModel):
    mode: Literal["every_30_turns", "context_70_percent", "manual"]


class UpdateChatAssemblyConfigurationRequest(BaseModel):
    system_prompt_id: str = Field(alias="systemPromptId")
    skill_ids: list[str] = Field(alias="skillIds")


class CreateChatPromptRequest(BaseModel):
    label: str
    content: str


class UpdateChatPromptRequest(BaseModel):
    label: str
    content: str


class CreateAiopsDiagnosticRequest(BaseModel):
    query: str
    alert: dict[str, object] = Field(default_factory=dict)


class UpsertFeedbackRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    target_type: Literal["chat_message", "citation", "diagnostic_step", "diagnostic_report"] = (
        Field(alias="targetType")
    )
    target_id: str = Field(alias="targetId", min_length=1, max_length=160)
    subject_id: str | None = Field(default=None, alias="subjectId", max_length=160)
    rating: Literal["positive", "negative"]
    reason: str | None = Field(default=None, max_length=80)
    comment: str | None = Field(default=None, max_length=2000)
    correction: str | None = Field(default=None, max_length=4000)


class McpConnectionMutationRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(min_length=1, max_length=120)
    transport: Literal["sse", "streamable_http"]
    url: str = Field(min_length=1, max_length=2048)
    enabled: bool = True
    timeout_seconds: int = Field(default=15, alias="timeoutSeconds", ge=1, le=300)
    retries: int = Field(default=1, ge=0, le=5)


class EvaluationGateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    min_pass_rate: float = Field(default=1.0, alias="minPassRate", ge=0.0, le=1.0)
    min_average_score: float = Field(default=1.0, alias="minAverageScore", ge=0.0, le=1.0)
    max_duration_regression_percent: float | None = Field(
        default=None,
        alias="maxDurationRegressionPercent",
        ge=0.0,
    )


class EvaluationCaseRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    name: str = Field(min_length=1, max_length=160)
    execution_type: Literal["chat", "aiops"] = Field(alias="executionType")
    input_summary: str = Field(alias="inputSummary", min_length=1, max_length=500)
    rules: list[EvaluationRule] = Field(min_length=1, max_length=20)


class CreateEvaluationDatasetRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    name: str = Field(min_length=1, max_length=160)
    version: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=2000)
    gate: EvaluationGateRequest
    cases: list[EvaluationCaseRequest] = Field(min_length=1, max_length=100)


class RunEvaluationRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    candidate_label: str = Field(alias="candidateLabel", min_length=1, max_length=160)
    baseline_run_id: str | None = Field(default=None, alias="baselineRunId", max_length=80)
    trace_bindings: dict[str, str] = Field(alias="traceBindings", min_length=1, max_length=100)
