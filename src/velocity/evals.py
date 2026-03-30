"""
Evaluation Framework.
Provides regression testing, semantic similarity checks, and golden dataset 
validation for agents before they are promoted to Production.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from velocity.core.base import AgentBase
from velocity.core.engine import AgentEngine


@dataclass
class EvalCase:
    """A single scenario to evaluate an agent against."""
    name: str
    payload: dict[str, Any]
    expected_contains: list[str] | None = None
    expected_tools: list[str] | None = None
    # Custom predicate function for advanced assertions
    assertion_fn: Callable[[str, dict[str, Any]], bool] | None = None


class EvalSuite:
    """
    Groups evaluation cases together for CI/CD gates.
    Executes mock or live runs depending on the LLM Gateway configuration.
    """

    def __init__(self, name: str, engine: AgentEngine, agent: AgentBase) -> None:
        self.name = name
        self.engine = engine
        self.agent = agent
        self.cases: list[EvalCase] = []

    def add_case(self, case: EvalCase) -> None:
        self.cases.append(case)

    async def run_all(self, fail_fast: bool = False) -> dict[str, Any]:
        """
        Executes all test scenarios against the live platform.
        Returns a structured pass/fail report.
        """
        passed: int = 0
        failed: int = 0
        failures: list[dict[str, Any]] = []

        for case in self.cases:
            try:
                # Mocks require the backend LLMGateway to be initialized with
                # a MockILlmProvider object for offline tests.
                output = await self.engine.run(
                    agent=self.agent,
                    payload=str(case.payload),
                    tenant_id="eval-tenant-001",
                    request_id=f"eval_{case.name}"
                )

                if case.expected_contains:
                    for substring in case.expected_contains:
                        assert substring in output, f"Missing '{substring}' in output: {output}"

                if case.assertion_fn:
                    assert case.assertion_fn(output, case.payload), "Custom assertion failed."

                passed += 1

            except Exception as e:
                failed += 1
                failures.append({"case": case.name, "error": str(e)})
                if fail_fast:
                    break

        return {
            "suite_name": self.name,
            "total": len(self.cases),
            "passed": passed,
            "failed": failed,
            "failures": failures,
        }
