"""Agent implementations and shared CrewAI LLM configuration."""

from collections.abc import Sequence
from typing import Any

from app.config import Settings, get_settings


class UnconfiguredLLM:
    """Placeholder used when an LLM client cannot be initialized yet."""

    def __init__(self, name: str, reason: str) -> None:
        self.name = name
        self.reason = reason

    @property
    def message(self) -> str:
        return f"{self.name} is not configured: {self.reason}"

    def __getattr__(self, _name: str) -> Any:
        raise RuntimeError(self.message)


def _openai_api_key(settings: Settings) -> str | None:
    if settings.openai_api_key is None:
        return None
    return settings.openai_api_key.get_secret_value().strip() or None


def _anthropic_api_key(settings: Settings) -> str | None:
    if settings.anthropic_api_key is None:
        return None
    return settings.anthropic_api_key.get_secret_value().strip() or None


def _make_chat_openai(model: str, temperature: float, max_tokens: int) -> Any:
    settings = get_settings()
    kwargs: dict[str, Any] = {
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    api_key = _openai_api_key(settings)
    if api_key is not None:
        kwargs["api_key"] = api_key

    try:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(**kwargs)
    except Exception as exc:
        return UnconfiguredLLM(model, str(exc))


def _make_chat_anthropic(model: str, temperature: float) -> Any:
    settings = get_settings()
    kwargs: dict[str, Any] = {
        "model": model,
        "temperature": temperature,
    }
    api_key = _anthropic_api_key(settings)
    if api_key is not None:
        kwargs["api_key"] = api_key

    try:
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(**kwargs)
    except Exception as exc:
        return UnconfiguredLLM(model, str(exc))


llm_fast = _make_chat_openai(model="gpt-4o-mini", temperature=0.0, max_tokens=2000)
llm_powerful = _make_chat_openai(model="gpt-4o", temperature=0.1, max_tokens=4000)
llm_claude = _make_chat_anthropic(model="claude-sonnet-4-6", temperature=0.1)


def make_agent(
    role: str,
    goal: str,
    backstory: str,
    tools: Sequence[Any] | None,
    llm: Any,
) -> Any:
    """Create a CrewAI agent with shared safety defaults."""
    if isinstance(llm, UnconfiguredLLM):
        raise RuntimeError(llm.message)

    from crewai import Agent

    settings = get_settings()
    return Agent(
        role=role,
        goal=goal,
        backstory=backstory,
        tools=list(tools or []),
        llm=llm,
        verbose=False,
        max_iter=5,
        memory=False,
    )


from app.agents.code_analysis_agent import CodeAnalysisAgent, create_code_analysis_agent
from app.agents.dependency_agent import DependencyAgent, create_dependency_agent
from app.agents.orchestrator import SoftwareEngineeringOrchestrator
from app.agents.readme_agent import ReadmeAgent, create_readme_agent
from app.agents.refactor_agent import RefactorAgent, create_refactor_agent
from app.agents.retrieval_agent import RetrievalAgent, create_retrieval_agent
from app.agents.review_agent import ReviewAgent, create_review_agent
from app.agents.security_agent import SecurityAgent, SecurityFinding, create_security_agent
from app.agents.test_gen_agent import TestGenerationAgent, create_test_generation_agent

__all__ = [
    "CodeAnalysisAgent",
    "DependencyAgent",
    "ReadmeAgent",
    "RefactorAgent",
    "RetrievalAgent",
    "ReviewAgent",
    "SecurityAgent",
    "SecurityFinding",
    "SoftwareEngineeringOrchestrator",
    "TestGenerationAgent",
    "UnconfiguredLLM",
    "create_code_analysis_agent",
    "create_dependency_agent",
    "create_readme_agent",
    "create_refactor_agent",
    "create_retrieval_agent",
    "create_review_agent",
    "create_security_agent",
    "create_test_generation_agent",
    "llm_claude",
    "llm_fast",
    "llm_powerful",
    "make_agent",
]
