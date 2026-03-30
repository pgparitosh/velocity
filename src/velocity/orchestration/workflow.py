"""
DAG (Directed Acyclic Graph) workflow orchestrator for multi-agent systems.

Handles routing state outputs from one agent to the inputs of another, 
evaluating conditionals dynamically, and running isolated branches concurrently.
"""

import asyncio
import logging
from collections.abc import Callable
from typing import Any

from velocity.core.base import AgentBase
from velocity.core.engine import AgentEngine
from velocity.exceptions import VelocityError

logger = logging.getLogger(__name__)


class WorkflowTask:
    """A single node within the Multi-Agent DAG."""
    def __init__(
        self, 
        id: str, 
        agent: AgentBase, 
        dependencies: list[str] | None = None,
        condition: Callable[[dict[str, Any]], bool] | None = None
    ) -> None:
        self.id = id
        self.agent = agent
        self.dependencies = dependencies or []
        # Optional predicate determining if this agent should run based on overall payload state
        self.condition = condition


class DAGOrchestrator:
    """
    Executes a graph of Agent invocations securely.
    Ensures tasks are run in topological order, parallelizing branches where data dependencies allow.
    """

    def __init__(self, engine: AgentEngine):
        self.engine = engine
        self._tasks: dict[str, WorkflowTask] = {}

    def add_task(self, task: WorkflowTask) -> None:
        if task.id in self._tasks:
            raise ValueError(f"Task with ID {task.id} already exists in DAG.")
        self._tasks[task.id] = task

    def _get_topological_groups(self) -> list[list[WorkflowTask]]:
        """
        Kahn's algorithm adaptation to group tasks by dependency levels.
        Identifies independent nodes that can be awaited simultaneously via asyncio.gather.
        """
        in_degree: dict[str, int] = {t_id: 0 for t_id in self._tasks}
        graph: dict[str, list[str]] = {t_id: [] for t_id in self._tasks}

        for t_id, task in self._tasks.items():
            for dep in task.dependencies:
                if dep not in self._tasks:
                    raise VelocityError(f"Task {t_id} depends on unknown task {dep}.")
                graph[dep].append(t_id)
                in_degree[t_id] += 1

        queue = [t_id for t_id, deg in in_degree.items() if deg == 0]
        levels = []

        while queue:
            current_level = queue[:]
            levels.append([self._tasks[t_id] for t_id in current_level])
            queue = []
            
            for ready_task in current_level:
                for dependent in graph[ready_task]:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)

        if sum(len(lvl) for lvl in levels) != len(self._tasks):
            raise VelocityError("Cyclic dependency detected in agent workflow DAG.")

        return levels

    async def run(self, initial_payload: dict[str, Any], tenant_id: str, request_id: str) -> dict[str, Any]:
        """
        Execute the compiled Multi-Agent mesh.
        Flows the `shared_state` downwards through subsequent execution tiers.
        """
        execution_levels = self._get_topological_groups()
        shared_state = initial_payload.copy()
        
        for level_idx, parallel_tasks in enumerate(execution_levels):
            logger.debug(f"Executing DAG Level {level_idx} ({len(parallel_tasks)} parallel agents)")
            
            async def run_task(task: WorkflowTask) -> tuple[str, Any]:
                if task.condition and not task.condition(shared_state):
                    logger.debug(f"Task {task.id} skipped due to condition predicate.")
                    return task.id, None
                    
                # We serialize the aggregated shared_state as the payload string for simplistic data-passing here
                # In more advanced iterations, Pydantic DTOs govern this handoff.
                state_json = str(shared_state) 
                
                result = await self.engine.run(
                    agent=task.agent,
                    payload=state_json,
                    tenant_id=tenant_id,
                    request_id=f"{request_id}_{task.id}",
                )
                return task.id, result

            # Run all independent agents at this DAG depth simultaneously
            results = await asyncio.gather(*(run_task(t) for t in parallel_tasks), return_exceptions=True)
            
            for res in results:
                if isinstance(res, BaseException):
                    raise VelocityError("Fatal error encountered in execution group.") from res
                
                result_tuple: tuple[str, Any] = res
                task_id, output = result_tuple
                if output is not None:
                    # Update global shared state for the next tier of dependents
                    shared_state[task_id] = output

        return shared_state
