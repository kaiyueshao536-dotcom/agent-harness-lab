"""LangGraph assembly separated from diagnostic node implementation."""
# pyright: reportMissingTypeStubs=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportArgumentType=false

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Literal

from langgraph.graph import END, START, StateGraph

from .state import AiopsDiagnosticState

DiagnosticNode = Callable[[AiopsDiagnosticState], Awaitable[dict[str, object]]]
DiagnosticRouter = Callable[[AiopsDiagnosticState], Literal["executor", "report"]]


@dataclass(frozen=True, slots=True)
class DiagnosticNodes:
    """Node callbacks required by the Plan-Execute-Replan-Report graph."""

    planner: DiagnosticNode
    executor: DiagnosticNode
    replanner: DiagnosticNode
    reporter: DiagnosticNode
    route_after_replanner: DiagnosticRouter


def build_diagnostic_graph(nodes: DiagnosticNodes) -> Any:
    """Compile the fixed diagnostic topology around injected node behavior."""
    graph = StateGraph(AiopsDiagnosticState)
    graph.add_node("planner", nodes.planner)
    graph.add_node("executor", nodes.executor)
    graph.add_node("replanner", nodes.replanner)
    graph.add_node("report", nodes.reporter)
    graph.add_edge(START, "planner")
    graph.add_edge("planner", "executor")
    graph.add_edge("executor", "replanner")
    graph.add_conditional_edges(
        "replanner",
        nodes.route_after_replanner,
        {"executor": "executor", "report": "report"},
    )
    graph.add_edge("report", END)
    return graph.compile()
