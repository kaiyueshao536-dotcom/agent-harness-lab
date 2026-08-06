"""Dependency protocols accepted by the FastAPI composition root."""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Sequence
from typing import Protocol

from super_ai.memory.repositories import DiagnosticTaskRecord
from super_ai.vector_store import MilvusHealthCheckResult, VectorChunkRecord


class AiopsDiagnosticRunner(Protocol):
    def stream(
        self,
        *,
        task: DiagnosticTaskRecord,
        accessible_knowledge_base_ids: Sequence[str],
    ) -> AsyncIterator[dict[str, object]]:
        """Stream one persisted AIOps diagnostic execution."""
        ...


class MilvusHealthCheckProvider(Protocol):
    def health_check(self) -> MilvusHealthCheckResult:
        """Return Milvus readiness/config status."""
        ...


class DocumentVectorStoreProvider(MilvusHealthCheckProvider, Protocol):
    def initialize(self) -> None:
        """Ensure vector collection/indexes exist before document writes."""
        ...

    def delete_document_chunks(
        self,
        *,
        tenant_id: str,
        knowledge_base_id: str,
        document_id: str,
    ) -> None:
        """Delete Milvus chunks for a scoped document."""
        ...

    def insert_chunks(self, chunks: Sequence[VectorChunkRecord]) -> None:
        """Insert Milvus chunks for document indexing."""
        ...


class DocumentIndexTaskScheduler(Protocol):
    def schedule(self, *, owner_user_id: str, task_id: str) -> Awaitable[None] | None:
        """Schedule a persisted index task without blocking the request."""
        ...
