"""Regression tests for reviewable API and AIOps module boundaries."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Literal, cast

import pytest
from fastapi.routing import APIRoute

from super_ai.aiops.graph import DiagnosticNodes, build_diagnostic_graph
from super_ai.aiops.state import AiopsDiagnosticState
from super_ai.api.routes.operations import build_operations_router
from super_ai.api.schemas import RegisterRequest

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def test_api_models_and_operational_routes_are_owned_by_domain_modules() -> None:
    app_source = (
        REPOSITORY_ROOT / "apps/backend/src/super_ai/api/app.py"
    ).read_text(encoding="utf-8")
    router = build_operations_router(
        runtime_dependency_payload=_unused_runtime_payload,
        configuration_check_payload=_unused_configuration_payload,
        mcp_client_resolver=lambda _request: _UnusedMcpClient(),
    )
    paths = {cast(APIRoute, route).path for route in router.routes}

    assert RegisterRequest(email="reviewer@example.com", displayName="Reviewer", password="x")
    assert paths == {"/health", "/metrics", "/health/mcp", "/ready", "/config/check"}
    assert "class RegisterRequest" not in app_source
    assert "@app.get(\"/health\")" not in app_source
    assert "build_operations_router" in app_source


@pytest.mark.asyncio
async def test_diagnostic_graph_keeps_plan_execute_replan_report_topology() -> None:
    async def planner(_state: AiopsDiagnosticState) -> dict[str, object]:
        return {"events": [{"type": "planner"}]}

    async def executor(_state: AiopsDiagnosticState) -> dict[str, object]:
        return {"events": [{"type": "executor"}]}

    async def replanner(_state: AiopsDiagnosticState) -> dict[str, object]:
        return {"events": [{"type": "replanner"}], "continue_execution": False}

    async def reporter(_state: AiopsDiagnosticState) -> dict[str, object]:
        return {"events": [{"type": "report"}]}

    def route_after_replanner(
        state: AiopsDiagnosticState,
    ) -> Literal["executor", "report"]:
        return "executor" if state.get("continue_execution") else "report"

    graph = build_diagnostic_graph(
        DiagnosticNodes(
            planner=planner,
            executor=executor,
            replanner=replanner,
            reporter=reporter,
            route_after_replanner=route_after_replanner,
        )
    )
    result = await graph.ainvoke({"events": [], "evidence": [], "evidence_ids": []})

    assert [event["type"] for event in result["events"]] == [
        "planner",
        "executor",
        "replanner",
        "report",
    ]


def test_boundary_modules_import_without_opening_external_connections(tmp_path: Path) -> None:
    script = """
import socket

def deny_connection(*_args, **_kwargs):
    raise AssertionError("module import attempted a network connection")

socket.create_connection = deny_connection
socket.socket.connect = deny_connection

import super_ai.aiops.graph
import super_ai.aiops.state
import super_ai.api.protocols
import super_ai.api.routes.operations
import super_ai.api.schemas
"""
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONPATH"] = str(REPOSITORY_ROOT / "apps/backend/src")
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert not list(tmp_path.iterdir())


async def _unused_runtime_payload(_request: object) -> dict[str, dict[str, object]]:
    raise AssertionError("route dependency should not run while inspecting paths")


def _unused_configuration_payload(_request: object) -> dict[str, dict[str, object]]:
    raise AssertionError("route dependency should not run while inspecting paths")


class _UnusedMcpClient:
    async def readiness(self) -> dict[str, object]:
        raise AssertionError("route dependency should not run while inspecting paths")
