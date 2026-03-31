#!/usr/bin/env python3
"""
Showcase Agent Workflow Runner - Ultra-minimal orchestration.

Write less code, achieve more with the platform:
- Platform handles: observability, prompts, lifecycle, memory, security
- Runners only define: workflow structure and orchestration

This runner simply:
1. Sets up platform services (in ~15 lines)
2. Instantiates agents (0 lines - they're just config)
3. Defines workflow DAG (3 tasks, 2 dependencies)
4. Runs it (1 line)
5. Displays results (platform provides all metrics)
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(message)s")

from velocity.config import get_config
from velocity.core.engine import AgentEngine
from velocity.core.llm_gateway import LLMGateway
from velocity.orchestration.workflow import WorkflowTask, DAGOrchestrator
from velocity.infra.providers.factory import create_all_providers
from velocity.memory.manager import MemoryManager
from velocity.prompts import PromptLibrary
from velocity.prompts.backends.file_backend import FilePromptBackend
from velocity.observability.metrics import MetricsService
from velocity.observability.middleware import MetricsMiddleware
from velocity.observability.factory import create_dev_observability_plugin
from velocity.services.audit.logger import AuditLogger

from agents import DataAgent, ProcessingAgent, AnalysisAgent


async def setup_platform():
    """Initialize platform services (DI pattern)."""
    config = get_config()

    print("\n" + "=" * 80)
    print("VELOCITY MULTI-AGENT WORKFLOW")
    print("=" * 80)
    print(f"\nConfiguration: {config.environment}")
    print(f"LLM: {config.llm.default_provider} / {config.llm.default_model}\n")

    # Platform services
    providers = create_all_providers(config.llm.providers)
    gateway = LLMGateway(
        providers=providers,
        default_provider=config.llm.default_provider,
        fallback_chain=config.llm.fallback_chain,
    )

    memory_manager = MemoryManager() if config.infra.database.backend != "memory" else None
    metrics_service = MetricsService()
    dev_observability = create_dev_observability_plugin(config.__dict__)
    metrics_middleware = MetricsMiddleware(
        metrics_service=metrics_service,
        dev_observability=dev_observability,
    )
    audit_logger = AuditLogger(db_backend=None, s3_backend=None, event_stream=None)

    engine = AgentEngine(
        llm_gateway=gateway,
        memory_manager=memory_manager,
        default_model=config.llm.default_model,
        middleware=metrics_middleware,
    )

    # Prompt library
    prompts_dir = Path(__file__).parent / "prompts"
    prompt_backend = FilePromptBackend(root_dir=str(prompts_dir))
    prompt_library = PromptLibrary(
        storage_backend=prompt_backend,
        cache_backend=None,
        l2_ttl_seconds=3600,
    )
    engine.prompt_library = prompt_library

    return engine, dev_observability


async def run_workflow():
    """
    Define and execute multi-agent workflow.

    Workflow:
        DataAgent (collect)
            ↓
        ProcessingAgent (process)
            ↓
        AnalysisAgent (analyze)
    """
    engine, dev_observability = await setup_platform()

    # Agents are minimal config objects
    agents = {
        "data": DataAgent(),
        "processing": ProcessingAgent(),
        "analysis": AnalysisAgent(),
    }

    print("[Workflow Structure]")
    print("  data_collect (no deps)")
    print("      ↓")
    print("  process_data (→ data_collect)")
    print("      ↓")
    print("  analyze_results (→ process_data)")
    print()

    # Build DAG
    orchestrator = DAGOrchestrator(engine=engine)

    orchestrator.add_task(WorkflowTask(id="data_collect", agent=agents["data"], dependencies=[]))
    orchestrator.add_task(
        WorkflowTask(id="process_data", agent=agents["processing"], dependencies=["data_collect"])
    )
    orchestrator.add_task(
        WorkflowTask(id="analyze_results", agent=agents["analysis"], dependencies=["process_data"])
    )

    # Execute
    print(f"\n{'*' * 80}")
    print("EXECUTING WORKFLOW")
    print(f"{'*' * 80}\n")

    try:
        result = await orchestrator.run(
            initial_payload={"workflow": "multi-stage", "description": "Collect, process, analyze"},
            tenant_id="demo-tenant",
            request_id="workflow-001",
        )

        print("\n[WORKFLOW RESULTS]")
        for task_id in ["data_collect", "process_data", "analyze_results"]:
            if task_id in result:
                print(f"  {task_id}: {str(result[task_id])[:100]}...")

        # Platform-provided metrics
        if dev_observability:
            summary = dev_observability.get_session_summary()
            print(f"\n[METRICS]")
            print(f"  Requests: {summary['total_requests']}")
            print(f"  Tokens: {summary['total_tokens']:,}")
            print(f"  Cost: ${summary['total_cost_usd']:.6f}")
            print(f"  Latency: {summary['total_latency_ms']:.0f}ms")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 80)
    print("✓ Workflow execution completed")
    print("=" * 80 + "\n")


async def main():
    await run_workflow()


if __name__ == "__main__":
    asyncio.run(main())
