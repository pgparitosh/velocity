#!/usr/bin/env python3
"""
Simple runner for the Hello Agent.
Loads the agent configuration and executes it using the Velocity platform.
Demonstrates platform features: config loading, provider management, memory, logging, cost tracking, and security.
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

# Setup platform logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

from velocity.config import get_config
from velocity.core.engine import AgentEngine
from velocity.core.llm_gateway import LLMGateway
from velocity.infra.providers.factory import create_all_providers
from velocity.memory.manager import MemoryManager

from agent import HelloAgent


async def main():
    logging.info("Starting Hello Agent with Velocity platform")
    print(f"GROQ_API_KEY from env: {os.environ.get('GROQ_API_KEY')}")
    # Load platform config (YAML + env overrides)
    config = get_config()

    # Create providers (e.g., Groq) with resilience and failover
    providers = create_all_providers(config.llm.providers)

    # Create LLM Gateway (handles retries, circuit breakers, fallbacks)
    gateway = LLMGateway(
        providers=providers,
        default_provider=config.llm.default_provider,
        fallback_chain=config.llm.fallback_chain,
    )

    # Create Memory Manager (optional; enables session context and semantic knowledge)
    memory_manager = MemoryManager() if config.infra.database.backend != "memory" else None

    # Create Engine (orchestrates LLM loop, tool execution, audit logging, cost tracking)
    engine = AgentEngine(
        llm_gateway=gateway, memory_manager=memory_manager, default_model=config.llm.default_model
    )

    # Load Agent
    agent = HelloAgent()

    # Run the agent (platform handles security checks, PII detection, and observability)
    payload = "Hello, what time is it?"
    result = await engine.run(
        agent=agent, payload=payload, tenant_id="test-tenant", request_id="test-request"
    )

    print(f"Agent Result: {result}")
    logging.info("Agent execution completed successfully")


if __name__ == "__main__":
    asyncio.run(main())
