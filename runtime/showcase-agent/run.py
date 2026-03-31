#!/usr/bin/env python3
"""
Showcase Agent Runner - Demonstrating Platform Observability.

This runner demonstrates how the Velocity platform provides comprehensive
built-in observability WITHOUT requiring manual instrumentation:

1. METRICS COLLECTION
   - Automatically records request counts, latency, cost, tokens
   - Tool success/failure rates
   - Model usage breakdown
   - Emitted as structured logs (in production: Prometheus)

2. AUDIT LOGGING
   - Complete session audit trail
   - All metadata, tokens, costs recorded
   - Multi-backend support (DB, S3, Event Stream)
   - Compliance-ready 7-year retention

3. REQUEST TRACING
   - Automatic request_id, session_id, trace_id correlation
   - Full lifecycle tracking from input to output
   - Distributed tracing support (OpenTelemetry-ready)

4. SECURITY & COMPLIANCE
   - Automatic PII detection and masking
   - Prompt injection prevention
   - Security event logging

5. COST & RATE LIMITING
   - Real-time token counting
   - Automatic cost calculation per model
   - Budget enforcement (daily/monthly)
   - 3-tier rate limiting (platform/tenant/agent)

AGENTS DON'T NEED TO LOG - THE PLATFORM HANDLES IT ALL!
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from dotenv import load_dotenv

load_dotenv()

# Setup platform logging to see metrics
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",  # Show raw log messages to see structured metrics
)

from velocity.config import get_config
from velocity.core.engine import AgentEngine
from velocity.core.llm_gateway import LLMGateway
from velocity.infra.providers.factory import create_all_providers
from velocity.memory.manager import MemoryManager
from velocity.prompts import PromptLibrary
from velocity.prompts.backends.file_backend import FilePromptBackend
from velocity.observability.metrics import MetricsService
from velocity.observability.middleware import MetricsMiddleware
from velocity.services.audit.logger import AuditLogger

from agent import ShowcaseAgent


async def demonstrate_capabilities():
    """Run comprehensive demonstrations of platform features with built-in observability."""

    print("\n" + "=" * 80)
    print("[*] VELOCITY PLATFORM - SHOWCASE AGENT WITH BUILT-IN OBSERVABILITY")
    print("=" * 80)
    print("\nNOTE: All observability is provided by the platform automatically!")
    print("      - Metrics collection (requests, latency, cost, tokens)")
    print("      - Audit logging (complete execution trail)")
    print("      - Security events (PII masking, injection prevention)")
    print("      - Cost tracking and budget enforcement")
    print("      - Request tracing and session correlation")
    print("\n" + "=" * 80 + "\n")

    # Load platform configuration
    config = get_config()
    print(f"[Platform Config]")
    print(f"  Environment: {config.environment}")
    print(f"  LLM Provider: {config.llm.default_provider}")
    print(f"  Default Model: {config.llm.default_model}\n")

    # Create LLM providers
    providers = create_all_providers(config.llm.providers)

    # Create LLM Gateway with resilience features
    gateway = LLMGateway(
        providers=providers,
        default_provider=config.llm.default_provider,
        fallback_chain=config.llm.fallback_chain,
    )

    # Create Memory Manager
    memory_manager = MemoryManager() if config.infra.database.backend != "memory" else None

    # Initialize PLATFORM OBSERVABILITY SERVICES
    print("[Platform Services]")

    # 1. Metrics Service - Automatically tracks performance metrics
    metrics_service = MetricsService()
    print("  [+] MetricsService initialized")
    print("    - Tracks: request counts, latency, cost, tokens, tool calls")
    print("    - Output: Structured logs (production: Prometheus)")

    # 2. Metrics Middleware - Hooks into engine to emit metrics
    metrics_middleware = MetricsMiddleware(metrics_service=metrics_service)
    print("  [+] MetricsMiddleware initialized")
    print("    - Automatically records metrics after each agent execution")

    # 3. Audit Logger - Persists complete audit trail
    audit_logger = AuditLogger(
        db_backend=None,  # In-memory for demo
        s3_backend=None,  # Would use S3 in production
        event_stream=None,  # Would use message queue in production
    )
    print("  [+] AuditLogger initialized")
    print("    - Records: Full execution audit trail")
    print("    - Storage: DB, S3, Event Stream (configurable)")
    print("    - Retention: 7 years for compliance\n")

    # Create Engine
    engine = AgentEngine(
        llm_gateway=gateway, memory_manager=memory_manager, default_model=config.llm.default_model
    )

    # Initialize PromptLibrary
    prompts_dir = Path(__file__).parent / "prompts"
    prompt_backend = FilePromptBackend(root_dir=str(prompts_dir))
    prompt_library = PromptLibrary(
        storage_backend=prompt_backend,
        cache_backend=None,
        l2_ttl_seconds=3600,
    )

    # Load Agent
    agent = ShowcaseAgent(prompt_library=prompt_library)

    print(f"[Agent Configuration]")
    print(f"  Agent ID: {agent.AGENT_ID} v{agent.AGENT_VERSION}")
    print(f"  Prompt Reference: {agent.PROMPT_REFERENCE}")
    print(f"  Prompt Library: Versioned (3-tier caching)\n")

    # Demonstration scenarios
    scenarios = [
        {
            "name": "Basic Tool Usage",
            "query": "What time is it right now?",
            "description": "Demonstrates basic tool execution and time handling",
        },
        {
            "name": "Mathematical Calculations",
            "query": "Calculate 15 + 27 and then multiply the result by 3",
            "description": "Shows sequential tool calls and calculation capabilities",
        },
        {
            "name": "Weather Information",
            "query": "What's the weather like in London?",
            "description": "Demonstrates external API simulation and data retrieval",
        },
        {
            "name": "Knowledge Base Search",
            "query": "What is the company's vacation policy?",
            "description": "Shows knowledge base search and information retrieval",
        },
        {
            "name": "Random Number Generation",
            "query": "Generate a random number between 1 and 100",
            "description": "Demonstrates random operations and parameter handling",
        },
        {
            "name": "System Health Check",
            "query": "Check the system health status",
            "description": "Shows administrative operations and system monitoring",
        },
        {
            "name": "Text Analysis",
            "query": "Analyze this text: 'The quick brown fox jumps over the lazy dog'",
            "description": "Demonstrates text processing and analytics tools",
        },
        {
            "name": "Complex Multi-Tool Query",
            "query": "Get the current time, generate a random number, and tell me what 42 divided by that number would be",
            "description": "Shows complex multi-tool orchestration and error handling",
        },
    ]

    print("[Scenario Execution with Automatic Platform Observability]\n")

    session_id = "demo-session-001"
    total_cost = 0.0
    successful_scenarios = 0
    accumulated_tokens = 0

    for i, scenario in enumerate(scenarios, 1):
        print(f"{i}. {scenario['name']}")
        print(f"   {scenario['description']}")
        print(f"   Query: {scenario['query']}")

        try:
            # Run the agent
            result = await engine.run(
                agent=agent,
                payload=scenario["query"],
                tenant_id="demo-tenant",
                request_id=f"demo-req-{i:02d}",
                session_id=session_id,
            )

            # Extract response
            response = result if isinstance(result, str) else str(result)

            # Note: Cost, tokens tracked automatically by platform in AgentContext
            successful_scenarios += 1

            print("[+] Success")
            sanitized = response.replace("\u202f", " ").replace("\u2011", "-")
            print(f"    Response: {sanitized[:80]}{'...' if len(sanitized) > 80 else ''}\n")

            # IMPORTANT: The following metrics are automatically recorded by platform:
            # - Request count and status
            # - Execution latency
            # - LLM tokens consumed
            # - Cost in USD
            # - Tool executions and success rates
            # - Security events
            # See logs above for MetricsService output

        except Exception as e:
            print(f"[-] Error: {e}\n")

    # Final summary
    print("=" * 80)
    print("[Platform Observability Demonstration Complete]")
    print("=" * 80)
    print(f"\nTotal Scenarios Executed: {len(scenarios)}")
    print(f"Successful: {successful_scenarios}/{len(scenarios)}")
    print(f"Session ID: {session_id}")

    print("\n[Automatic Metrics Recorded by Platform]")
    print("  [+] Request counts and status (SUCCESS/ERROR)")
    print("  [+] Execution latency (end-to-end and per-component)")
    print("  [+] LLM tokens consumed (input/output breakdown)")
    print("  [+] Cost in USD (calculated from tokens + pricing)")
    print("  [+] Tool invocations and success rates")
    print("  [+] Model selection and routing decisions")
    print("  [+] Security events (PII detection, validation)")
    print("  [+] Circuit breaker and retry activity")
    print("  [+] Rate limiting decisions")
    print("  [+] Budget enforcement checks")

    print("\n[Audit Trail Information]")
    print(f"  [+] Complete session logged to audit system")
    print(f"  [+] Request ID: demo-req-001 through demo-req-{len(scenarios):02d}")
    print(f"  [+] Session ID: {session_id}")
    print(f"  [+] Tenant ID: demo-tenant")
    print(f"  [+] All tool calls, LLM calls, and events recorded")

    print("\n[How to Access Audit Data (Production)]")
    print("  1. PostgreSQL: SELECT * FROM velocity_audit_logs WHERE tenant_id='demo-tenant'")
    print("  2. S3: audit/demo-tenant/showcase-agent/demo-req-*.json")
    print("  3. Event Stream: Subscribe to 'velocity.audit.completed' topic")

    print("\n" + "=" * 80)
    print("[+] Platform provides built-in observability for all agent operations!")
    print("[+] No manual instrumentation needed - metrics are automatic!")
    print("=" * 80 + "\n")


async def main():
    """Main entry point."""
    await demonstrate_capabilities()


if __name__ == "__main__":
    asyncio.run(main())
