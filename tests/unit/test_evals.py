from unittest.mock import AsyncMock, MagicMock

import pytest

from velocity.core.base import AgentBase
from velocity.core.engine import AgentEngine
from velocity.evals import EvalCase, EvalSuite


class MockAgent(AgentBase):
    def system_prompt(self): return "prompt"
    def tools(self): return []
    async def execute_tool(self, n, i, c): return "res"

@pytest.fixture
def mock_engine():
    engine = MagicMock(spec=AgentEngine)
    engine.run = AsyncMock()
    return engine

@pytest.mark.asyncio
async def test_eval_suite_success(mock_engine):
    agent = MockAgent()
    suite = EvalSuite("Test Suite", engine=mock_engine, agent=agent)
    
    # Case 1: Simple string contains
    case1 = EvalCase(
        name="hello_check",
        payload={"query": "say hello"},
        expected_contains=["Hello"]
    )
    suite.add_case(case1)
    
    mock_engine.run.return_value = "Hello, world!"
    
    report = await suite.run_all()
    assert report["passed"] == 1
    assert report["total"] == 1
    assert len(report["failures"]) == 0

@pytest.mark.asyncio
async def test_eval_suite_failure(mock_engine):
    agent = MockAgent()
    suite = EvalSuite("Fail Suite", engine=mock_engine, agent=agent)
    
    case1 = EvalCase(
        name="fail_check",
        payload={"query": "test"},
        expected_contains=["Missing"]
    )
    suite.add_case(case1)
    
    mock_engine.run.return_value = "Not here"
    
    report = await suite.run_all()
    assert report["passed"] == 0
    assert report["failed"] == 1
    assert "Missing" in report["failures"][0]["error"]

@pytest.mark.asyncio
async def test_eval_suite_assertion_fn(mock_engine):
    agent = MockAgent()
    suite = EvalSuite("Assert Suite", engine=mock_engine, agent=agent)
    
    def my_assert(output, payload):
        return len(output) > 5
        
    case1 = EvalCase(
        name="fn_check",
        payload={"query": "test"},
        assertion_fn=my_assert
    )
    suite.add_case(case1)
    
    # Case 1: Passes (len > 5)
    mock_engine.run.return_value = "123456"
    report_pass = await suite.run_all()
    assert report_pass["passed"] == 1
    
    # Case 2: Fails (len <= 5)
    mock_engine.run.return_value = "123"
    report_fail = await suite.run_all()
    assert report_fail["passed"] == 0
