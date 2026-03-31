"""
Observability Middleware.
Automatically instruments AgentEngine execution with metrics and tracing.
"""

import time
import logging
from typing import Any

from velocity.core.context import AgentContext
from velocity.observability.metrics import MetricsService
from velocity.observability.dev import DevObservabilityPlugin

logger = logging.getLogger(__name__)


class MetricsMiddleware:
    """
    Wraps AgentEngine execution to emit metrics automatically.
    This avoids polluting the core engine logic with observability boilerplate.
    Optionally includes dev observability logging for human-readable console output.
    """

    def __init__(
        self,
        metrics_service: MetricsService,
        dev_observability: DevObservabilityPlugin | None = None,
    ):
        self.metrics = metrics_service
        self.dev_observability = dev_observability

    async def after_run(self, ctx: AgentContext, error: Exception | None = None) -> None:
        """
        Extracts metrics from the completed AgentContext and records them.
        Called by the Engine after execution finishes (success or error).
        """
        agent_id = ctx.agent_id
        tenant_id = ctx.tenant_id
        status = "ERROR" if error else "SUCCESS"

        # 1. Basic Request Metrics
        self.metrics.record_request(agent_id, tenant_id, status)
        self.metrics.record_latency(agent_id, ctx.elapsed_ms)

        # 2. Cost and Token Metrics
        if ctx.cost_usd > 0:
            self.metrics.record_cost(agent_id, tenant_id, ctx.cost_usd)

        # 3. Model Usage
        for call in ctx.llm_calls:
            self.metrics.record_tokens(
                agent_id=agent_id,
                model=call.get("model", "unknown"),
                input_tokens=call.get("input_tokens", 0),
                output_tokens=call.get("output_tokens", 0),
            )

        # 4. Tool Metrics
        for t_call in ctx.tool_calls:
            self.metrics.record_tool_call(
                agent_id=agent_id,
                tool_name=t_call.get("tool_name", "unknown"),
                success=t_call.get("success", False),
            )

        # 5. Dev Observability (if enabled)
        if self.dev_observability:
            await self.dev_observability.after_run(ctx, error)
