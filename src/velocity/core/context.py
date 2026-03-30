"""
AgentContext and execution state definitions.
This module defines the central state object that flows through the platform execution engine.
"""

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class AgentContext:
    """
    The single source of truth for an agent's execution state and tracing metadata.
    
    This object is created by the AgentEngine on initiation and flows down to services
    and tools. It should primarily be mutated through its controlled methods to maintain
    invariants, particularly for cost and token tracking.
    """

    # Identity and Tracing
    request_id: str
    agent_id: str
    tenant_id: str
    session_id: str | None = None
    agent_version: str = "latest"
    user_id: str | None = None
    parent_request_id: str | None = None
    trace_id: str | None = None
    tags: dict[str, str] = field(default_factory=dict)

    # Execution State
    iteration: int = 1
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    llm_calls: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    
    # Timing (measured in seconds natively, usually converted to ms on serialization)
    _start_time: float = field(default_factory=time.monotonic, repr=False)
    _end_time: float | None = field(default=None, repr=False)

    # Budget & Cost Tracking
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tool_calls: int = 0
    cost_usd: float = 0.0

    @property
    def elapsed_ms(self) -> float:
        """Calculate the currently elapsed time in milliseconds."""
        end = self._end_time if self._end_time is not None else time.monotonic()
        return (end - self._start_time) * 1000.0

    def mark_completed(self) -> None:
        """Mark the execution as completed and freeze the timing state."""
        if self._end_time is None:
            self._end_time = time.monotonic()

    def record_llm_call(
        self, 
        model: str, 
        input_tokens: int, 
        output_tokens: int,
        call_cost_usd: float,
        latency_ms: float
    ) -> None:
        """
        Safely record an LLM call to the execution tracing context
        and increment budget trackers.
        """
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.cost_usd += call_cost_usd
        
        self.llm_calls.append({
            "iteration": self.iteration,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": call_cost_usd,
            "latency_ms": latency_ms,
            "timestamp": time.time()
        })

    def record_tool_call(
        self,
        tool_name: str,
        success: bool,
        latency_ms: float,
        error_message: str | None = None
    ) -> None:
        """Safely record a tool execution to the context tracing array."""
        self.total_tool_calls += 1
        self.tool_calls.append({
            "iteration": self.iteration,
            "tool_name": tool_name,
            "success": success,
            "latency_ms": latency_ms,
            "error_message": error_message,
            "timestamp": time.time()
        })
