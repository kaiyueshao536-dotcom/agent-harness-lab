"""State contract for the AIOps diagnostic graph."""

from __future__ import annotations

from operator import add
from typing import Annotated, TypedDict

from super_ai.memory.repositories import JsonDict


class AiopsDiagnosticState(TypedDict, total=False):
    owner_user_id: str
    task_id: str
    query: str
    alert: JsonDict
    accessible_knowledge_base_ids: tuple[str, ...]
    sop_hits: list[JsonDict]
    no_sop_matched: bool
    plan: list[JsonDict]
    plan_origin: str
    plan_index: int
    continue_execution: bool
    execution_failed: bool
    report_id: str
    events: Annotated[list[dict[str, object]], add]
    evidence: Annotated[list[JsonDict], add]
    evidence_ids: Annotated[list[str], add]
