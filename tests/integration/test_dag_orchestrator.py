from unittest.mock import AsyncMock, MagicMock

import pytest

from velocity.core.base import AgentBase
from velocity.core.engine import AgentEngine
from velocity.orchestration.workflow import DAGOrchestrator, WorkflowTask


class MockAgent(AgentBase):
    def __init__(self, agent_id="mock"):
        self.AGENT_ID = agent_id
    def system_prompt(self): return "prompt"
    def tools(self): return []
    async def execute_tool(self, n, i, c): return "res"

@pytest.fixture
def mock_engine():
    engine = MagicMock(spec=AgentEngine)
    engine.run = AsyncMock()
    return engine

@pytest.mark.asyncio
async def test_dag_parallel_execution(mock_engine):
    orch = DAGOrchestrator(engine=mock_engine)
    
    agent_a = MockAgent("agent_a")
    agent_b = MockAgent("agent_b")
    agent_c = MockAgent("agent_c")
    
    # A and B are independent, C depends on both
    task_a = WorkflowTask(id="A", agent=agent_a)
    task_b = WorkflowTask(id="B", agent=agent_b)
    task_c = WorkflowTask(id="C", agent=agent_c, dependencies=["A", "B"])
    
    orch.add_task(task_a)
    orch.add_task(task_b)
    orch.add_task(task_c)
    
    mock_engine.run.side_effect = ["Result A", "Result B", "Result C"]
    
    result = await orch.run(initial_payload={"start": True}, tenant_id="t1", request_id="r1")
    
    assert result["A"] == "Result A"
    assert result["B"] == "Result B"
    assert result["C"] == "Result C"
    assert mock_engine.run.call_count == 3

@pytest.mark.asyncio
async def test_dag_conditional_skipping(mock_engine):
    orch = DAGOrchestrator(engine=mock_engine)
    agent_a = MockAgent("agent_a")
    
    # Only run if 'should_run' is True in state
    task_a = WorkflowTask(
        id="A", 
        agent=agent_a, 
        condition=lambda state: state.get("should_run") is True
    )
    orch.add_task(task_a)
    
    # Case 1: Should Skip
    result_skip = await orch.run({"should_run": False}, "t1", "r1")
    assert "A" not in result_skip
    assert mock_engine.run.call_count == 0
    
    # Case 2: Should Run
    mock_engine.run.return_value = "Done"
    result_run = await orch.run({"should_run": True}, "t1", "r2")
    assert result_run["A"] == "Done"
    assert mock_engine.run.call_count == 1
