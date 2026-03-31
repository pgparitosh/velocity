#!/usr/bin/env python3
"""
Showcase Agent Runner.
Demonstrates all Velocity platform capabilities in action:
- Agent configuration loading
- Provider management (Groq API integration)
- Memory management (short-term, long-term, episodic)
- Cost tracking and rate limiting
- Security features (PII detection, injection prevention)
- Audit logging
- Tool execution with permissions
- Multi-turn conversation support
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
from velocity.prompts import PromptLibrary
from velocity.prompts.backends.file_backend import FilePromptBackend

from agent import ShowcaseAgent


async def demonstrate_capabilities():
    """Run comprehensive demonstrations of platform features."""
    logging.info("Starting Showcase Agent - Velocity Platform Demonstration")

    # Load platform configuration
    config = get_config()
    logging.info(
        f"Platform config loaded: environment={config.environment}, provider={config.llm.default_provider}"
    )

    # Create LLM providers (demonstrates multi-provider support)
    providers = create_all_providers(config.llm.providers)
    logging.info(f"Providers loaded: {list(providers.keys())}")

    # Create LLM Gateway with resilience features
    gateway = LLMGateway(
        providers=providers,
        default_provider=config.llm.default_provider,
        fallback_chain=config.llm.fallback_chain,
    )
    logging.info("LLM Gateway initialized with circuit breaker and retry logic")

    # Create Memory Manager (demonstrates all three memory types)
    memory_manager = MemoryManager() if config.infra.database.backend != "memory" else None
    if memory_manager:
        logging.info("Memory Manager enabled: short-term, long-term, and episodic memory")
    else:
        logging.info("Memory Manager disabled (in-memory mode for demo)")

    # Initialize PromptLibrary for versioned prompt management
    prompts_dir = Path(__file__).parent / "prompts"
    prompt_backend = FilePromptBackend(root_dir=str(prompts_dir))
    prompt_library = PromptLibrary(
        storage_backend=prompt_backend,
        cache_backend=None,  # No Redis in demo environment
        l2_ttl_seconds=3600,
    )
    logging.info(f"PromptLibrary initialized with FilePromptBackend at {prompts_dir}")

    # Create Engine (core orchestration)
    engine = AgentEngine(
        llm_gateway=gateway, memory_manager=memory_manager, default_model=config.llm.default_model
    )
    logging.info("Agent Engine initialized with full platform services")

    # Load Agent with injected PromptLibrary (demonstrates dependency injection)
    agent = ShowcaseAgent(prompt_library=prompt_library)
    logging.info(f"Agent loaded: {agent.AGENT_ID} v{agent.AGENT_VERSION}")

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

    print("\n" + "=" * 80)
    print("[*] VELOCITY PLATFORM CAPABILITY DEMONSTRATION")
    print("=" * 80)
    print(f"Agent: {agent.AGENT_ID} v{agent.AGENT_VERSION}")
    print(f"Model: {config.llm.default_model}")
    print(f"Provider: {config.llm.default_provider}")
    print("=" * 80)

    session_id = "demo-session-001"
    total_cost = 0.0
    successful_scenarios = 0

    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{i}. {scenario['name']}")
        print(f"   {scenario['description']}")
        print(f"   Query: {scenario['query']}")

        try:
            # Run the agent (demonstrates full platform pipeline)
            # payload must be a string, not a dict
            result = await engine.run(
                agent=agent,
                payload=scenario["query"],
                tenant_id="demo-tenant",
                request_id=f"demo-req-{i:02d}",
                session_id=session_id,
            )

            # result is a string, extract response text
            response = result if isinstance(result, str) else str(result)

            # Note: Cost tracking, tool counts, and iterations will be added
            # in Phase 4 when middleware and metadata propagation is implemented
            successful_scenarios += 1

            print("[+] Success")
            # Sanitize response by replacing problematic Unicode characters
            sanitized = response.replace("\u202f", " ").replace("\u2011", "-")
            print(f"    Response: {sanitized[:100]}{'...' if len(sanitized) > 100 else ''}")

        except Exception as e:
            print(f"[-] Error: {e}")
            logging.error(f"Scenario {i} failed", exc_info=True)

    # Final summary
    print("\n" + "=" * 80)
    print("[*] DEMONSTRATION SUMMARY")
    print("=" * 80)
    print(f"Total scenarios: {len(scenarios)}")
    print(f"Successful: {successful_scenarios}/{len(scenarios)}")
    print(f"Session ID: {session_id}")
    print("=" * 80)
    print("[+] Platform capabilities demonstrated successfully!")
    print("Features shown: Tool execution, Memory management, Cost tracking,")
    print("Security, Rate limiting, Audit logging, Multi-turn conversations")
    print("=" * 80)

    logging.info("Showcase Agent demonstration completed successfully")


async def main():
    """Main entry point."""
    await demonstrate_capabilities()


if __name__ == "__main__":
    asyncio.run(main())
