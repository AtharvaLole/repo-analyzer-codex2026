"""LangGraph state definitions."""

import operator
from typing import Annotated, Literal, TypedDict

Intent = Literal["qa", "readme", "security", "tests", "refactor", "explain", "unknown"]


class AgentState(TypedDict):
    """Shared workflow state for multi-agent repository workflows."""

    repo_id: str
    user_query: str
    intent: Intent
    retrieval_results: list[dict]
    code_analysis: str
    security_findings: list[dict]
    agent_outputs: Annotated[list[str], operator.add]
    final_answer: str
    citations: list[dict]
    confidence: int
    error: str | None
    active_agents: list[str]
    completed_steps: Annotated[list[str], operator.add]


GraphState = AgentState

__all__ = ["AgentState", "GraphState", "Intent"]
