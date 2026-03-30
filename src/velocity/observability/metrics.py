"""
Observability Metrics.
Defines the standard set of platform indicators for tracking 
performance, cost, and usage.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class MetricsService:
    """
    Abstract metrics collector.
    In production, this would emit to Prometheus via prometheus_client.
    In development, it emits to the standard logger as structured data.
    """

    def record_request(self, agent_id: str, tenant_id: str, status: str) -> None:
        """Track agent invocation counts."""
        logger.info(f"metric=platform_agent_requests_total agent={agent_id} tenant={tenant_id} status={status}")

    def record_latency(self, agent_id: str, latency_ms: float) -> None:
        """Track execution time distributions."""
        logger.info(f"metric=platform_agent_latency_ms agent={agent_id} value={latency_ms}")

    def record_cost(self, agent_id: str, tenant_id: str, cost_usd: float) -> None:
        """Track cumulative LLM spend categorization."""
        logger.info(f"metric=platform_agent_cost_usd_total agent={agent_id} tenant={tenant_id} value={cost_usd}")

    def record_tool_call(self, agent_id: str, tool_name: str, success: bool) -> None:
        """Track tool invocation success/failure rates."""
        status = "success" if success else "failure"
        logger.info(f"metric=platform_tool_calls_total agent={agent_id} tool={tool_name} status={status}")

    def record_tokens(self, agent_id: str, model: str, input_tokens: int, output_tokens: int) -> None:
        """Track token consumption by model and agent."""
        logger.info(f"metric=platform_tokens_total agent={agent_id} model={model} type=input value={input_tokens}")
        logger.info(f"metric=platform_tokens_total agent={agent_id} model={model} type=output value={output_tokens}")
