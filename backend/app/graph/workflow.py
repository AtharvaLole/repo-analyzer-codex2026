"""LangGraph workflow assembly."""

from __future__ import annotations

from typing import Any, cast

from langgraph.graph import END, StateGraph

from app.graph.nodes import (
    code_analysis_node,
    error_node,
    intent_router,
    readme_node,
    retrieval_node,
    review_node,
    security_node,
)
from app.graph.state import AgentState


def route_from_intent(state: AgentState) -> str:
    """Route from the intent node to the first workflow action."""
    if state.get("error"):
        return "error"
    if state["intent"] == "readme":
        return "readme"
    return "retrieval"


def route_after_retrieval(state: AgentState) -> str:
    """Route retrieved context based on intent."""
    if state.get("error"):
        return "error"
    if state["intent"] == "security":
        return "security"
    return "code_analysis"


def route_after_code_analysis(state: AgentState) -> str:
    """Route code analysis output to review unless an error occurred."""
    return "error" if state.get("error") else "review"


def route_after_security(state: AgentState) -> str:
    """Route security output to review unless an error occurred."""
    return "error" if state.get("error") else "review"


def route_after_terminal_node(state: AgentState) -> str:
    """Finish successful terminal nodes or send errors to the error node."""
    return "error" if state.get("error") else "end"


def build_graph() -> StateGraph:
    """Build the uncompiled multi-agent repository workflow graph."""
    state_graph = StateGraph(AgentState)
    state_graph.add_node("intent_router", intent_router)
    state_graph.add_node("retrieval_node", retrieval_node)
    state_graph.add_node("code_analysis_node", code_analysis_node)
    state_graph.add_node("security_node", security_node)
    state_graph.add_node("readme_node", readme_node)
    state_graph.add_node("review_node", review_node)
    state_graph.add_node("error_node", error_node)

    state_graph.set_entry_point("intent_router")
    state_graph.add_conditional_edges(
        "intent_router",
        route_from_intent,
        {
            "retrieval": "retrieval_node",
            "readme": "readme_node",
            "error": "error_node",
        },
    )
    state_graph.add_conditional_edges(
        "retrieval_node",
        route_after_retrieval,
        {
            "code_analysis": "code_analysis_node",
            "security": "security_node",
            "error": "error_node",
        },
    )
    state_graph.add_conditional_edges(
        "code_analysis_node",
        route_after_code_analysis,
        {
            "review": "review_node",
            "error": "error_node",
        },
    )
    state_graph.add_conditional_edges(
        "security_node",
        route_after_security,
        {
            "review": "review_node",
            "error": "error_node",
        },
    )
    state_graph.add_conditional_edges(
        "readme_node",
        route_after_terminal_node,
        {
            "end": END,
            "error": "error_node",
        },
    )
    state_graph.add_conditional_edges(
        "review_node",
        route_after_terminal_node,
        {
            "end": END,
            "error": "error_node",
        },
    )
    state_graph.add_edge("error_node", END)
    return state_graph


graph = build_graph()
workflow = graph.compile()


def build_workflow() -> Any:
    """Return the compiled multi-agent repository workflow."""
    return workflow


async def run_workflow(repo_id: str, query: str) -> AgentState:
    """Run the compiled workflow for a repository query."""
    initial_state: AgentState = {
        "repo_id": repo_id,
        "user_query": query,
        "intent": "unknown",
        "retrieval_results": [],
        "code_analysis": "",
        "security_findings": [],
        "agent_outputs": [],
        "final_answer": "",
        "citations": [],
        "confidence": 0,
        "error": None,
        "active_agents": [],
        "completed_steps": [],
    }
    result = await workflow.ainvoke(initial_state)
    return cast(AgentState, result)


__all__ = [
    "build_graph",
    "build_workflow",
    "graph",
    "route_after_code_analysis",
    "route_after_retrieval",
    "route_after_security",
    "route_after_terminal_node",
    "route_from_intent",
    "run_workflow",
    "workflow",
]
