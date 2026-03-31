"""
Development Observability Plugin for Velocity Platform.

Provides human-readable console logging of all observability events during development.
This is a platform-level capability available to all agents without code modification.

Configuration via platform_config.yaml:
  observability:
    dev_logging:
      enabled: true          # Enable dev console logging (default: true in dev environment)
      verbose: false         # Show inputs/outputs (default: false)
      color: true            # Use colored output (default: true)

Environment variables:
  VELOCITY_DEV_LOGGING=true|false
  VELOCITY_DEV_LOGGING_VERBOSE=true|false
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict

from velocity.core.context import AgentContext

logger = logging.getLogger(__name__)


class DevObservabilityLogger:
    """
    Logs observability events in human-readable format for development.
    Works with any agent automatically - no agent-specific code needed.
    """

    def __init__(self, enabled: bool = True, verbose: bool = False, color: bool = True):
        self.enabled = enabled
        self.verbose = verbose
        self.color = color

    def log_llm_call(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
        latency_ms: float,
    ) -> None:
        """Log an LLM call with tokens, cost, and latency."""
        if not self.enabled:
            return

        total_tokens = input_tokens + output_tokens
        log_msg = (
            f"\n  [LLM] Model: {model}\n"
            f"        Input tokens:  {input_tokens:,}\n"
            f"        Output tokens: {output_tokens:,}\n"
            f"        Total tokens:  {total_tokens:,}\n"
            f"        Cost: ${cost_usd:.6f}\n"
            f"        Latency: {latency_ms:.0f}ms"
        )
        logger.info(log_msg)

    def log_tool_call(
        self,
        tool_name: str,
        success: bool,
        latency_ms: float,
        error: str | None = None,
    ) -> None:
        """Log a tool call with success status and latency."""
        if not self.enabled:
            return

        status = "[+]" if success else "[ERROR]"
        status_text = "SUCCESS" if success else f"FAILED: {error}"

        log_msg = (
            f"\n  [TOOL] {status} {tool_name}\n"
            f"         Status: {status_text}\n"
            f"         Latency: {latency_ms:.0f}ms"
        )
        logger.info(log_msg)

    def log_execution_context(self, ctx: AgentContext) -> None:
        """Log complete execution context with all metrics."""
        if not self.enabled:
            return

        logger.info("\n" + "─" * 80)
        logger.info(f"EXECUTION SUMMARY")
        logger.info("─" * 80)

        logger.info(
            f"\n[Request Details]\n"
            f"  Request ID: {ctx.request_id}\n"
            f"  Agent ID: {ctx.agent_id}\n"
            f"  Tenant ID: {ctx.tenant_id}\n"
            f"  Session ID: {ctx.session_id or 'N/A'}\n"
            f"  Iteration: {ctx.iteration}\n"
        )

        logger.info(
            f"[Execution Metrics]\n"
            f"  LLM Calls: {len(ctx.llm_calls)}\n"
            f"  Tool Calls: {len(ctx.tool_calls)}\n"
        )

        logger.info(
            f"[Token Usage]\n"
            f"  Input Tokens: {ctx.total_input_tokens:,}\n"
            f"  Output Tokens: {ctx.total_output_tokens:,}\n"
            f"  Total Tokens: {ctx.total_input_tokens + ctx.total_output_tokens:,}\n"
        )

        logger.info(
            f"[Cost & Performance]\n"
            f"  Total Cost: ${ctx.cost_usd:.6f}\n"
            f"  Total Latency: {ctx.elapsed_ms:.0f}ms\n"
        )

        logger.info("─" * 80 + "\n")

    def log_from_context(self, ctx: AgentContext) -> None:
        """Extract and log all metrics from AgentContext."""
        if not self.enabled:
            return

        # Log all LLM calls
        for llm_call in ctx.llm_calls:
            self.log_llm_call(
                model=llm_call.get("model", "unknown"),
                input_tokens=llm_call.get("input_tokens", 0),
                output_tokens=llm_call.get("output_tokens", 0),
                cost_usd=llm_call.get("cost_usd", 0.0),
                latency_ms=llm_call.get("latency_ms", 0.0),
            )

        # Log all tool calls
        for tool_call in ctx.tool_calls:
            self.log_tool_call(
                tool_name=tool_call.get("tool_name", "unknown"),
                success=tool_call.get("success", False),
                latency_ms=tool_call.get("latency_ms", 0.0),
                error=tool_call.get("error_message"),
            )


class DevObservabilityPlugin:
    """
    Platform-level observability plugin.
    Automatically logs execution metrics in development environment.
    Works with MetricsMiddleware pattern - no agent changes needed.
    """

    def __init__(self, enabled: bool = None, verbose: bool = False):
        """
        Initialize the dev observability plugin.

        Args:
            enabled: Enable dev logging (default: True in dev environment)
            verbose: Show verbose output (default: False)
        """
        # Auto-detect from environment or use provided value
        if enabled is None:
            enabled = os.getenv("VELOCITY_DEV_LOGGING", "").lower() != "false"

        verbose = verbose or os.getenv("VELOCITY_DEV_LOGGING_VERBOSE", "").lower() == "true"

        self.logger = DevObservabilityLogger(enabled=enabled, verbose=verbose)
        self.request_count = 0
        self.total_tokens = 0
        self.total_cost = 0.0
        self.total_latency = 0.0

    async def after_run(self, ctx: AgentContext, error: Exception | None = None) -> None:
        """
        Called by MetricsMiddleware after agent execution.
        Logs all observability data from context to console.
        """
        self.request_count += 1

        # Log all metrics from context
        logger.info("\n" + "=" * 80)
        logger.info(f"[EXECUTION {self.request_count}]")
        logger.info("=" * 80)

        self.logger.log_from_context(ctx)
        self.logger.log_execution_context(ctx)

        # Track totals
        self.total_tokens += ctx.total_input_tokens + ctx.total_output_tokens
        self.total_cost += ctx.cost_usd
        self.total_latency += ctx.elapsed_ms

        if error:
            logger.error(f"[ERROR] Execution failed: {str(error)}")

    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of all executions in current session."""
        return {
            "total_requests": self.request_count,
            "total_tokens": self.total_tokens,
            "total_cost_usd": self.total_cost,
            "total_latency_ms": self.total_latency,
            "average_cost_per_request": self.total_cost / self.request_count
            if self.request_count > 0
            else 0,
        }
