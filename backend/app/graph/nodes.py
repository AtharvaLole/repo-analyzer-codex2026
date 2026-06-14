"""LangGraph node functions."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, cast

from loguru import logger

from app.agents import llm_fast, llm_powerful
from app.agents.security_agent import SecurityAgent
from app.config import get_settings
from app.crews.qa_crew import QACrew, QAResult
from app.crews.readme_crew import ReadmeCrew
from app.graph.state import AgentState, Intent
from app.rag.retriever import HybridRetriever, SearchResult

VALID_INTENTS: set[Intent] = {"qa", "readme", "security", "tests", "refactor", "explain", "unknown"}


async def intent_router(state: AgentState) -> AgentState:
    """Classify the user's query and select active agents."""
    query = state["user_query"]
    prompt = (
        "Classify this query into exactly one category: qa, readme, security, tests, "
        f"refactor, explain, unknown. Query: {query}. Respond with only the category word."
    )
    try:
        raw_intent = await _invoke_llm_text(llm_fast, prompt)
        intent = _normalize_intent(raw_intent)
    except Exception as exc:
        logger.warning("Intent routing LLM failed; using heuristic fallback: {}", exc)
        intent = _heuristic_intent(query)

    return cast(
        AgentState,
        {
            "intent": intent,
            "active_agents": _active_agents_for_intent(intent),
            "completed_steps": ["intent_router"],
        },
    )


async def retrieval_node(state: AgentState) -> AgentState:
    """Retrieve repository code context with hybrid search."""
    try:
        results = await HybridRetriever(settings=get_settings()).hybrid_search(
            repo_id=state["repo_id"],
            query=state["user_query"],
            top_k=8,
        )
        serialized = [result.model_dump() for result in results]
        return cast(
            AgentState,
            {
                "retrieval_results": serialized,
                "agent_outputs": [_format_retrieval_output(results)],
                "completed_steps": ["retrieval"],
            },
        )
    except Exception as exc:
        return _error_update("retrieval", exc)


async def code_analysis_node(state: AgentState) -> AgentState:
    """Run the Q&A crew for QA/explain intents or synthesize analysis from retrieved context."""
    try:
        if state["intent"] in {"qa", "explain"}:
            result = await QACrew(settings=get_settings()).run(
                repo_id=state["repo_id"],
                question=state["user_query"],
            )
            return cast(
                AgentState,
                {
                    "code_analysis": result.answer,
                    "citations": [citation.model_dump() for citation in result.citations],
                    "confidence": result.confidence,
                    "agent_outputs": [result.answer],
                    "completed_steps": ["code_analysis"],
                },
            )

        analysis = await _analysis_from_retrieval(state)
        citations = _citations_from_retrieval(state.get("retrieval_results", []))
        return cast(
            AgentState,
            {
                "code_analysis": analysis,
                "citations": citations,
                "agent_outputs": [analysis],
                "completed_steps": ["code_analysis"],
            },
        )
    except Exception as exc:
        return _error_update("code_analysis", exc)


async def security_node(state: AgentState) -> AgentState:
    """Run static security review against the checked-out repository."""
    try:
        settings = get_settings()
        repo_path = (settings.repos_base_dir / state["repo_id"]).resolve()
        findings = await SecurityAgent().run(repo_path)
        serialized = [
            {
                "scanner": finding.scanner,
                "severity": finding.severity,
                "message": finding.message,
                "file_path": finding.file_path,
            }
            for finding in findings
        ]
        output = _format_security_findings(serialized)
        return cast(
            AgentState,
            {
                "security_findings": serialized,
                "agent_outputs": [output],
                "completed_steps": ["security"],
            },
        )
    except Exception as exc:
        return _error_update("security", exc)


async def readme_node(state: AgentState) -> AgentState:
    """Generate a README using the README crew."""
    try:
        result = await ReadmeCrew(settings=get_settings()).run(repo_id=state["repo_id"])
        return cast(
            AgentState,
            {
                "final_answer": result.content,
                "confidence": result.confidence,
                "agent_outputs": [result.content],
                "completed_steps": ["readme"],
            },
        )
    except Exception as exc:
        return _error_update("readme", exc)


async def review_node(state: AgentState) -> AgentState:
    """Aggregate agent outputs and run the final review agent."""
    try:
        aggregate = _aggregate_outputs(state)
        reviewed = await _run_review_agent(state, aggregate)
        return cast(
            AgentState,
            {
                "final_answer": reviewed,
                "confidence": _extract_confidence(reviewed, state.get("confidence", 70)),
                "completed_steps": ["review"],
            },
        )
    except Exception as exc:
        return _error_update("review", exc)


async def error_node(state: AgentState) -> AgentState:
    """Log workflow errors and produce a user-friendly response."""
    error = state.get("error") or "Unknown workflow error"
    logger.error("Workflow failed for repo {}: {}", state.get("repo_id"), error)
    return cast(
        AgentState,
        {
            "final_answer": (
                "I could not complete that repository workflow. "
                "Please verify the repository is indexed and try again."
            ),
            "confidence": 0,
            "completed_steps": ["error"],
        },
    )


async def retrieve_context(state: AgentState) -> AgentState:
    """Backward-compatible wrapper for the old graph node name."""
    return await retrieval_node(state)


async def synthesize_answer(state: AgentState) -> AgentState:
    """Backward-compatible wrapper for the old graph node name."""
    return await review_node(state)


async def _invoke_llm_text(llm: Any, prompt: str) -> str:
    ainvoke = getattr(llm, "ainvoke", None)
    if ainvoke is not None:
        response = await ainvoke(prompt)
    else:
        invoke = getattr(llm, "invoke")
        response = await asyncio.to_thread(invoke, prompt)
    content = getattr(response, "content", response)
    if isinstance(content, list):
        return " ".join(str(item) for item in content)
    return str(content)


async def _analysis_from_retrieval(state: AgentState) -> str:
    retrieval_results = state.get("retrieval_results", [])
    if not retrieval_results:
        return "No relevant indexed code was found for this request."

    context = "\n\n".join(
        (
            f"FILE: {result.get('file_path')} "
            f"(lines {result.get('start_line')}-{result.get('end_line')})\n"
            f"{result.get('content', '')}"
        )
        for result in retrieval_results[:6]
    )
    prompt = (
        f"User query: {state['user_query']}\n"
        f"Intent: {state['intent']}\n\n"
        "Use the retrieved code below to provide a concise, grounded engineering answer. "
        "Cite file paths and line numbers when making claims.\n\n"
        f"{context}"
    )
    try:
        return await _invoke_llm_text(llm_powerful, prompt)
    except Exception:
        return _fallback_analysis(state)


async def _run_review_agent(state: AgentState, aggregate: str) -> str:
    if not aggregate.strip():
        return "No agent output was produced for review."

    try:
        from crewai import Crew, Process, Task

        from app.agents import create_review_agent

        review_agent = create_review_agent(state["repo_id"])
        task = Task(
            description=(
                "Review the following agent outputs for accuracy, grounding, and completeness. "
                "Return the final answer and include a confidence score from 0-100.\n\n"
                f"User query: {state['user_query']}\n\n{aggregate}"
            ),
            expected_output="Final reviewed answer with confidence score.",
            agent=review_agent,
        )
        crew = Crew(agents=[review_agent], tasks=[task], process=Process.sequential, verbose=False)
        output = await asyncio.to_thread(crew.kickoff)
        return _crew_output_to_text(output)
    except Exception as exc:
        logger.warning("Review agent failed; returning aggregate output: {}", exc)
        return _append_confidence_if_missing(aggregate, state.get("confidence", 70))


def _normalize_intent(value: str) -> Intent:
    token = value.strip().lower().split()[0] if value.strip() else "unknown"
    return token if token in VALID_INTENTS else "unknown"  # type: ignore[return-value]


def _heuristic_intent(query: str) -> Intent:
    lowered = query.lower()
    if "readme" in lowered or "documentation" in lowered:
        return "readme"
    if any(term in lowered for term in ("security", "vulnerab", "owasp", "secret", "xss", "sql injection")):
        return "security"
    if any(term in lowered for term in ("test", "pytest", "jest", "junit", "coverage")):
        return "tests"
    if any(term in lowered for term in ("refactor", "code smell", "duplicate", "clean code")):
        return "refactor"
    if any(term in lowered for term in ("explain", "how does", "walk me through", "architecture")):
        return "explain"
    if lowered.strip():
        return "qa"
    return "unknown"


def _active_agents_for_intent(intent: Intent) -> list[str]:
    mapping: dict[Intent, list[str]] = {
        "qa": ["retrieval_agent", "code_analysis_agent", "review_agent"],
        "explain": ["retrieval_agent", "code_analysis_agent", "review_agent"],
        "readme": ["code_analysis_agent", "dependency_agent", "readme_agent", "review_agent"],
        "security": ["retrieval_agent", "security_agent", "review_agent"],
        "tests": ["retrieval_agent", "code_analysis_agent", "review_agent"],
        "refactor": ["retrieval_agent", "code_analysis_agent", "review_agent"],
        "unknown": ["retrieval_agent", "code_analysis_agent", "review_agent"],
    }
    return mapping[intent]


def _format_retrieval_output(results: list[SearchResult]) -> str:
    if not results:
        return "No relevant code chunks were retrieved."
    return "\n\n".join(
        (
            f"FILE: {result.file_path} (lines {result.start_line}-{result.end_line})\n"
            f"{result.content}"
        )
        for result in results
    )


def _citations_from_retrieval(results: list[dict]) -> list[dict]:
    return [
        {
            "file_path": str(result.get("file_path", "")),
            "start_line": int(result.get("start_line", 1)),
            "end_line": int(result.get("end_line", result.get("start_line", 1))),
            "snippet": str(result.get("content", ""))[:1_500],
            "relevance": f"{result.get('search_type', 'hybrid')}:{float(result.get('score', 0.0)):.4f}",
        }
        for result in results
    ]


def _format_security_findings(findings: list[dict]) -> str:
    if not findings:
        return "No security findings were reported by the configured scanners."
    return "\n\n".join(
        (
            f"[{finding.get('severity', 'unknown')}] {finding.get('scanner', 'scanner')}\n"
            f"{finding.get('file_path') or '<repo>'}: {finding.get('message', '')}"
        )
        for finding in findings
    )


def _aggregate_outputs(state: AgentState) -> str:
    outputs = [output for output in state.get("agent_outputs", []) if output.strip()]
    if state.get("code_analysis"):
        outputs.append(state["code_analysis"])
    if state.get("security_findings"):
        outputs.append(_format_security_findings(state["security_findings"]))
    if state.get("final_answer"):
        outputs.append(state["final_answer"])
    return "\n\n---\n\n".join(outputs)


def _fallback_analysis(state: AgentState) -> str:
    retrieval_results = state.get("retrieval_results", [])
    lines = [
        f"Intent: {state['intent']}",
        f"Query: {state['user_query']}",
        "",
        "Relevant code references:",
    ]
    for result in retrieval_results[:6]:
        lines.append(
            f"- {result.get('file_path')}:{result.get('start_line')}-{result.get('end_line')}",
        )
    return "\n".join(lines)


def _crew_output_to_text(output: Any) -> str:
    for attribute in ("raw", "result", "output"):
        value = getattr(output, attribute, None)
        if isinstance(value, str) and value.strip():
            return value
    return str(output)


def _extract_confidence(content: str, default: int) -> int:
    import re

    match = re.search(r"confidence(?:\s+score)?\D{0,20}(\d{1,3})", content, flags=re.IGNORECASE)
    if match is None:
        return max(0, min(100, default))
    return max(0, min(100, int(match.group(1))))


def _append_confidence_if_missing(content: str, confidence: int) -> str:
    if "confidence" in content.lower():
        return content
    return f"{content}\n\nConfidence score: {max(0, min(100, confidence))}"


def _error_update(step: str, exc: Exception) -> AgentState:
    logger.exception("{} node failed", step)
    return cast(
        AgentState,
        {
            "error": f"{step}: {exc}",
            "completed_steps": [step],
        },
    )


__all__ = [
    "code_analysis_node",
    "error_node",
    "intent_router",
    "readme_node",
    "retrieval_node",
    "retrieve_context",
    "review_node",
    "security_node",
    "synthesize_answer",
]
