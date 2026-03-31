"""
Showcase Agent Implementation.
Comprehensive agent demonstrating all Velocity platform capabilities:
- Multi-tool execution with permissions
- Memory management (short-term, long-term, episodic)
- Security features (PII detection, injection prevention)
- Cost tracking and rate limiting
- Audit logging
- Error handling and hooks
- Complex workflows and decision making
- Versioned prompt management using platform PromptLibrary
"""

import logging
import json
from typing import Any, List, Dict
from velocity.sdk import AgentBase, AgentContext
from velocity.prompts import PromptLibrary

# Import our tools
from tools import (
    get_current_time,
    perform_calculation,
    get_weather_data,
    search_knowledge_base,
    generate_random_number,
    system_health_check,
    format_data_as_json,
    count_words,
)

logger = logging.getLogger(__name__)


class ShowcaseAgent(AgentBase):
    """
    Comprehensive agent showcasing all platform capabilities.

    This agent can handle various types of queries:
    - Time and scheduling questions
    - Mathematical calculations
    - Weather information
    - Knowledge base searches
    - Random number generation
    - System health checks
    - Data formatting
    - Text analysis

    Demonstrates:
    - Tool routing and execution
    - Memory context injection
    - Security and permission handling
    - Cost and rate limit awareness
    - Audit logging
    - Error recovery
    - Multi-turn conversation continuity
    - Versioned prompt management using PromptLibrary
    """

    AGENT_ID = "showcase-agent"
    AGENT_VERSION = "1.0.0"
    PROMPT_REFERENCE = "showcase-agent@v1.0.0"  # Version-pinned prompt reference

    def __init__(self, prompt_library: PromptLibrary):
        """
        Initialize agent with injected PromptLibrary for versioned prompt management.

        Args:
            prompt_library: PromptLibrary instance for resolving versioned prompts
        """
        self.prompt_library = prompt_library
        self._resolved_prompt = None  # Cache resolved prompt with variables

    def system_prompt(self) -> str:
        """
        Return static prompt reference.

        Note: The actual versioned prompt is resolved in on_before_llm_call()
        since that's where we have access to context variables for template rendering.
        """
        return f"[PROMPT: {self.PROMPT_REFERENCE}]"

    def tools(self) -> List[dict]:
        """Return all available tools with their schemas."""
        return [
            get_current_time.__tool_metadata__.to_llm_schema(),
            perform_calculation.__tool_metadata__.to_llm_schema(),
            get_weather_data.__tool_metadata__.to_llm_schema(),
            search_knowledge_base.__tool_metadata__.to_llm_schema(),
            generate_random_number.__tool_metadata__.to_llm_schema(),
            system_health_check.__tool_metadata__.to_llm_schema(),
            format_data_as_json.__tool_metadata__.to_llm_schema(),
            count_words.__tool_metadata__.to_llm_schema(),
        ]

    async def execute_tool(self, name: str, inputs: dict, ctx: AgentContext) -> Any:
        """Route tool calls to appropriate handlers with logging."""
        logger.info(f"Executing tool '{name}' with inputs: {inputs}")

        tool_map = {
            "get_current_time": get_current_time,
            "perform_calculation": perform_calculation,
            "get_weather_data": get_weather_data,
            "search_knowledge_base": search_knowledge_base,
            "generate_random_number": generate_random_number,
            "system_health_check": system_health_check,
            "format_data_as_json": format_data_as_json,
            "count_words": count_words,
        }

        if name not in tool_map:
            raise ValueError(f"Unknown tool: {name}")

        try:
            # Call the tool function
            if name == "count_words":
                result = await tool_map[name](**inputs)
            elif name == "format_data_as_json":
                result = await tool_map[name](**inputs)
            elif name == "search_knowledge_base":
                # Handle optional max_results parameter
                max_results = inputs.get("max_results", 5)
                result = await tool_map[name](inputs["query"], max_results)
            elif name == "generate_random_number":
                # Handle optional parameters
                min_val = inputs.get("min_value", 1)
                max_val = inputs.get("max_value", 100)
                result = await tool_map[name](min_val, max_val)
            elif name == "perform_calculation":
                result = await tool_map[name](inputs["operation"], inputs["a"], inputs["b"])
            else:
                # Tools with single required parameter
                result = await tool_map[name](**inputs)

            logger.info(f"Tool '{name}' executed successfully")
            return result

        except Exception as e:
            logger.error(f"Tool '{name}' failed: {e}")
            raise

    async def on_before_llm_call(self, messages: List[dict], ctx: AgentContext) -> List[dict]:
        """
        Pre-LLM hook: Resolve versioned prompt from PromptLibrary with context variables.

        This demonstrates the platform's prompt management capabilities:
        - Loads prompt from versioned library
        - Injects context-specific variables
        - Maintains prompt versioning and audit trail
        """
        logger.debug("Pre-LLM call hook: resolving versioned prompt from library")

        # Resolve prompt with context variables (demonstrates dynamic variable rendering)
        try:
            self._resolved_prompt = await self.prompt_library.resolve(
                reference=self.PROMPT_REFERENCE,
                variables={
                    "agent_id": self.AGENT_ID,
                    "agent_version": self.AGENT_VERSION,
                    "request_id": ctx.request_id,
                    "session_id": ctx.session_id or "new",
                },
            )
            logger.info(f"Resolved prompt: {self.PROMPT_REFERENCE}")
        except Exception as e:
            logger.warning(f"Failed to load versioned prompt: {e}. Using fallback.")
            self._resolved_prompt = f"You are {self.AGENT_ID}, an AI assistant."

        # Replace system message with resolved prompt
        if messages and messages[0].get("role") == "system":
            messages[0]["content"] = self._resolved_prompt
        else:
            messages.insert(0, {"role": "system", "content": self._resolved_prompt})

        # Add system information about platform capabilities
        system_info = {
            "role": "system",
            "content": (
                f"Platform Context: Agent {ctx.agent_id} v{ctx.agent_version}, "
                f"Request {ctx.request_id}, Iteration {ctx.iteration}, "
                f"Session {ctx.session_id or 'new'}"
            ),
        }

        # Insert platform context after main system prompt
        messages.insert(1, system_info)

        return messages

    async def on_after_tool_call(self, tool_name: str, result: Any, ctx: AgentContext) -> Any:
        """Post-tool hook: validate results and add metadata."""
        logger.debug(f"Post-tool hook for '{tool_name}': processing result")

        # Add execution metadata to results
        if isinstance(result, dict) and "processed_at" not in result:
            result["execution_metadata"] = {
                "tool": tool_name,
                "agent_version": ctx.agent_version,
                "iteration": ctx.iteration,
                "request_id": ctx.request_id,
            }

        return result

    async def on_final_result(self, result: Any, ctx: AgentContext) -> Any:
        """Final result hook: add platform attribution and metrics."""
        logger.info("Final result processing: adding platform metadata")

        if isinstance(result, dict):
            result["platform_metadata"] = {
                "agent_id": ctx.agent_id,
                "version": ctx.agent_version,
                "request_id": ctx.request_id,
                "elapsed_ms": ctx.elapsed_ms,
                "cost_usd": ctx.cost_usd,
                "tools_used": len(ctx.tool_calls),
                "iterations": ctx.iteration,
            }

        return result

    def parse_result(self, text: str, ctx: AgentContext) -> dict:
        """Parse LLM output with enhanced error handling."""
        try:
            # Try to parse as JSON first
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        # Fall back to text response
        return {"response": text, "confidence": 0.8, "parsing_method": "text_fallback"}

    async def on_error(self, error: Exception, ctx: AgentContext) -> None:
        """Error handling hook: log detailed error information."""
        logger.error(
            f"Agent error in request {ctx.request_id}: {error}",
            exc_info=True,
            extra={
                "agent_id": ctx.agent_id,
                "iteration": ctx.iteration,
                "tool_calls": len(ctx.tool_calls),
                "elapsed_ms": ctx.elapsed_ms,
            },
        )
