"""Liveness, readiness, configuration, and process-metric routes."""
# pyright: reportUnusedFunction=false

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Protocol

from fastapi import APIRouter, Request

from super_ai.foundation import get_foundation_info

from ..responses import success_response


class McpReadinessClient(Protocol):
    async def readiness(self) -> dict[str, object]: ...


RuntimeDependencyPayload = Callable[
    [Request], Awaitable[dict[str, dict[str, object]]]
]
ConfigurationCheckPayload = Callable[[Request], dict[str, dict[str, object]]]
McpClientResolver = Callable[[Request], McpReadinessClient]


def build_operations_router(
    *,
    runtime_dependency_payload: RuntimeDependencyPayload,
    configuration_check_payload: ConfigurationCheckPayload,
    mcp_client_resolver: McpClientResolver,
) -> APIRouter:
    """Build operational routes without owning application dependencies."""
    router = APIRouter(tags=["operations"])

    @router.get("/health")
    async def health(request: Request) -> object:
        foundation = get_foundation_info()
        return success_response(
            request,
            {
                "service": foundation.service,
                "status": foundation.status,
                "version": foundation.version,
            },
        )

    @router.get("/metrics")
    async def metrics(request: Request) -> object:
        snapshot = request.app.state.request_metrics.snapshot()
        average = (
            snapshot.total_latency_ms / snapshot.request_count if snapshot.request_count else 0.0
        )
        return success_response(
            request,
            {
                "requestCount": snapshot.request_count,
                "failureCount": snapshot.failure_count,
                "averageLatencyMs": round(average, 3),
            },
        )

    @router.get("/health/mcp")
    async def mcp_health(request: Request) -> object:
        result = await mcp_client_resolver(request).readiness()
        return success_response(request, result, status_code=200 if result["ok"] else 503)

    @router.get("/ready")
    async def ready(request: Request) -> object:
        dependencies = await runtime_dependency_payload(request)
        is_ready = all(bool(component["ok"]) for component in dependencies.values())
        return success_response(
            request,
            {"status": "ready" if is_ready else "degraded", "dependencies": dependencies},
            status_code=200 if is_ready else 503,
        )

    @router.get("/config/check")
    async def config_check(request: Request) -> object:
        configuration = configuration_check_payload(request)
        dependencies = await runtime_dependency_payload(request)
        is_valid = all(bool(component["valid"]) for component in configuration.values())
        is_ready = all(bool(component["ok"]) for component in dependencies.values())
        return success_response(
            request,
            {
                "status": "ready" if is_valid and is_ready else "degraded",
                "configuration": configuration,
                "dependencies": dependencies,
            },
            status_code=200 if is_valid and is_ready else 503,
        )

    return router
