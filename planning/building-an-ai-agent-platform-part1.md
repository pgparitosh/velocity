# Building an AI Agent Platform: The Ultimate Technical Guide
### For Platform Engineers Enabling Teams to Build AI Agents at Scale
#### Python · C# · Architecture · Components · Best Practices

---

> **Who is this for?**
> You are a platform or infrastructure engineer. Your organisation has built a
> few AI agents and realised that every team is reinventing the same wheel:
> LLM clients, retry logic, cost tracking, audit logging, tool registration.
> You want to build a shared platform — a foundation that any developer can
> stand on to build production-grade agents in days, not months.
> This guide gives you every component, in both Python and C#, with real code.

---

## Table of Contents

**Part 1 (this file)**
1. [Why a Platform?](#1-why-a-platform)
2. [Core Concepts](#2-core-concepts)
3. [Platform Architecture Overview](#3-platform-architecture-overview)
4. [Component 1: Core Execution Engine](#4-component-1-core-execution-engine)
5. [Component 2: Tool Registry & Framework](#5-component-2-tool-registry--framework)
6. [Component 3: Prompt Library](#6-component-3-prompt-library)

**Part 2** → `building-an-ai-agent-platform-part2.md`
7. Component 4: Memory Management
8. Component 5: Cost Management & Model Routing
9. Component 6: Rate Limiting
10. Component 7: Security Layer
11. Component 8: Validation Layer

**Part 3** → `building-an-ai-agent-platform-part3.md`
12. Component 9: Audit & Observability
13. Component 10: MCP Layer
14. Component 11: Orchestration Engine
15. Component 12: Scaling & Deployment
16. Building Agents on Top of the Platform
17. Benefits, Alternatives & Trade-offs
18. Best Practices
19. Cheat Sheet
20. Mastery Check

---

## 1. Why a Platform?

### The Problem Every Scaling AI Team Hits

Your team builds Agent A (PR reviewer). It works. Another team builds Agent B
(incident responder). Then Agent C (fraud detector). By Agent D, you notice:

```
Agent A:  Has its own retry logic. Uses hardcoded model name. Logs to stdout.
          No cost tracking. No rate limiting. Audit log is a print statement.

Agent B:  Different retry logic. Different model client. No audit log at all.
          Prompt is a 400-line string in the middle of main.py.

Agent C:  Someone added cost tracking — but it's copy-pasted from Agent A.
          Now it's diverged. The bug that was fixed in A was never fixed in C.

Agent D:  New developer joins. Asks: "How do I build an agent?" Gets pointed
          to 3 different codebases with 3 different patterns. Writes a 4th.
```

This is the **agent sprawl problem**. It looks like this in numbers:

| Without Platform | With Platform |
|-----------------|---------------|
| 6 weeks to build a new agent | 3 days to build a new agent |
| Bug fixed in 5 places separately | Bug fixed once, all agents get the fix |
| 4 different retry strategies | 1 battle-tested retry strategy |
| No visibility into total LLM cost | Real-time cost dashboard across all agents |
| Compliance audit: impossible | Compliance audit: run a query |
| New developer ramp-up: 3 weeks | New developer ramp-up: 2 days |

---

### What a Platform Gives You

Think of it like AWS vs. running your own data centre.

**Without the platform:** Every agent team manages their own:
- LLM connection pool
- Retry and circuit breaker logic
- Prompt version control
- Cost tracking
- Audit logging
- Secret management
- Rate limiting
- Tool execution sandbox

**With the platform:** Every agent team gets all of this for free.
They write only what is unique to their agent: the system prompt and the tools.

```
Platform (built once, maintained by platform team):
  ├── Core execution engine
  ├── Tool registry
  ├── Prompt library
  ├── Memory management
  ├── Cost management & model routing
  ├── Rate limiting
  ├── Security layer
  ├── Validation framework
  ├── Audit & observability
  ├── MCP layer
  ├── Orchestration engine
  └── Deployment scaffolding

Agent (built by product teams, using the platform):
  ├── system_prompt.yaml       ← what the agent knows
  ├── tools/my_domain_tool.py  ← what the agent can do
  └── agent_config.yaml        ← how the agent behaves
```

---

## 2. Core Concepts

### Concept 1: The Platform as a Set of Contracts

A platform does not dictate how agents are built. It defines **contracts**
(interfaces, schemas, base classes) that agents must conform to in order to
get platform services for free.

**Real-life analogy:** A USB standard. You don't know what device will plug in —
but if it conforms to the USB spec, it gets power, data transfer, and
compatibility with any USB hub. The device maker doesn't build their own power supply.

```
Platform contract:
  - "Implement these 3 methods and you get: retries, cost tracking, audit logs,
    rate limiting, security scanning, and observability for free."

Agent implementor's job:
  - Implement: get_system_prompt(), get_tools(), execute_tool()
  - That's it.
```

### Concept 2: Horizontal vs. Vertical Concerns

```
VERTICAL (agent-specific — each team owns):
  ├── Domain system prompt ("You are a fraud analyst...")
  ├── Domain tools (get_fraud_score, block_transaction)
  └── Domain decision logic (approve/block/escalate)

HORIZONTAL (cross-cutting — platform owns):
  ├── How the LLM is called (connection pool, retry, timeout)
  ├── How prompts are versioned and loaded
  ├── How tools are registered and sandboxed
  ├── How costs are tracked and attributed
  ├── How rate limits are enforced
  ├── How audit records are written
  └── How the agent is deployed and scaled
```

### Concept 3: Extension Points

The platform defines where agent teams can plug in their code.
Everything else is locked down and managed by the platform.

```
Extension Point 1: Tool Registration
  → Register any function as an agent tool via decorator

Extension Point 2: System Prompt
  → Store in prompt library, reference by name and version

Extension Point 3: Agent Configuration
  → YAML file defining model, limits, behaviours

Extension Point 4: Event Hooks
  → Subscribe to platform events (on_tool_call, on_decision, on_error)

Extension Point 5: Custom Validators
  → Add domain-specific input/output validation rules
```

---

## 3. Platform Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AI AGENT PLATFORM                                  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                      AGENT SDK (client-facing)                       │  │
│  │  @agent decorator · AgentBuilder · ToolKit · PromptRef               │  │
│  └────────────────────────────────────┬─────────────────────────────────┘  │
│                                        │                                    │
│  ┌─────────────────────────────────────▼───────────────────────────────┐   │
│  │                    CORE EXECUTION ENGINE                            │   │
│  │  AgentRunner · AgentContext · LoopController · StopConditions       │   │
│  └──────┬──────────┬──────────┬──────────┬──────────┬─────────────────┘   │
│         │          │          │          │          │                       │
│  ┌──────▼──┐ ┌─────▼──┐ ┌───▼────┐ ┌──▼─────┐ ┌──▼──────────┐          │
│  │  LLM    │ │ TOOL   │ │MEMORY  │ │PROMPT  │ │ORCHESTRATION│          │
│  │GATEWAY  │ │REGISTRY│ │MANAGER │ │LIBRARY │ │  ENGINE     │          │
│  │         │ │        │ │        │ │        │ │             │          │
│  │Model    │ │Register│ │Short   │ │Version │ │Multi-agent  │          │
│  │routing  │ │Discover│ │Long    │ │Template│ │DAG          │          │
│  │Retry    │ │Validate│ │Episodic│ │Testing │ │Handoff      │          │
│  │Pool     │ │Execute │ │        │ │        │ │             │          │
│  └──────┬──┘ └────────┘ └────────┘ └────────┘ └─────────────┘          │
│         │                                                                   │
│  ┌──────▼──────────────────────────────────────────────────────────────┐   │
│  │                   PLATFORM SERVICES LAYER                          │   │
│  │  CostManager · RateLimiter · SecurityLayer · ValidationEngine      │   │
│  │  AuditLogger · MCPBroker · EventBus · SecretVault                  │   │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                   INFRASTRUCTURE LAYER                              │  │
│  │  PostgreSQL (audit) · Redis (cache/rate limit) · S3 (prompts)      │  │
│  │  Vector DB (memory) · Kafka (events) · Kubernetes (runtime)        │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Component 1: Core Execution Engine

The execution engine is the heart of the platform. It owns the agent loop,
manages context, and calls every other platform service.

### Python Implementation

```python
# platform/core/engine.py

from __future__ import annotations
import asyncio
import time
import uuid
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Optional, AsyncIterator
from abc import ABC, abstractmethod

import anthropic

from platform.services.cost import CostManager
from platform.services.rate_limiter import RateLimiter
from platform.services.audit import AuditLogger
from platform.services.security import SecurityLayer
from platform.services.validation import ValidationEngine
from platform.prompts.library import PromptLibrary
from platform.memory.manager import MemoryManager

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# CONTEXT — the single object that flows through the entire agent execution
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class AgentContext:
    """
    The execution context for a single agent invocation.
    Created at the start of each run. Never modified by tools directly —
    only the engine modifies it through controlled methods.
    """
    # Identity
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: Optional[str] = None
    agent_id: str = ""
    agent_version: str = ""
    tenant_id: str = ""          # For multi-tenant platforms
    user_id: Optional[str] = None

    # Execution state
    start_time: float = field(default_factory=time.monotonic)
    iteration: int = 0
    tool_calls: list[dict] = field(default_factory=list)
    llm_calls: list[dict] = field(default_factory=list)
    events: list[dict] = field(default_factory=list)

    # Budget tracking
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tool_calls: int = 0

    # Metadata for audit and tracing
    trace_id: Optional[str] = None
    parent_request_id: Optional[str] = None   # For sub-agents
    tags: dict[str, str] = field(default_factory=dict)

    @property
    def elapsed_ms(self) -> int:
        return int((time.monotonic() - self.start_time) * 1000)

    @property
    def cost_usd(self) -> float:
        return CostManager.calculate(
            self.agent_id,
            self.total_input_tokens,
            self.total_output_tokens
        )

    def record_tool_call(self, tool: str, status: str, latency_ms: int):
        self.tool_calls.append({
            "tool": tool, "status": status,
            "latency_ms": latency_ms, "iteration": self.iteration
        })
        self.total_tool_calls += 1

    def record_llm_call(self, model: str, input_tok: int, output_tok: int, latency_ms: int):
        self.llm_calls.append({
            "model": model, "input_tokens": input_tok,
            "output_tokens": output_tok, "latency_ms": latency_ms,
            "iteration": self.iteration
        })
        self.total_input_tokens += input_tok
        self.total_output_tokens += output_tok


# ─────────────────────────────────────────────────────────────────────────────
# AGENT INTERFACE — what every agent must implement
# ─────────────────────────────────────────────────────────────────────────────

class AgentBase(ABC):
    """
    Base class every agent extends. Implement 3 methods. Get everything else free.
    """

    # Required — agent teams override these
    AGENT_ID: str = ""
    AGENT_VERSION: str = "1.0.0"

    @abstractmethod
    def system_prompt(self) -> str:
        """Return the agent's system prompt. Or return a PromptRef to use the library."""
        ...

    @abstractmethod
    def tools(self) -> list[dict]:
        """Return the OpenAI/Anthropic tool schema list."""
        ...

    @abstractmethod
    async def execute_tool(self, name: str, inputs: dict, ctx: AgentContext) -> Any:
        """Execute a tool call and return its result."""
        ...

    # Optional hooks — agents override these for custom behaviour
    async def on_before_llm_call(self, messages: list, ctx: AgentContext) -> list:
        """Hook: modify messages before each LLM call. Return modified messages."""
        return messages

    async def on_after_tool_call(self, tool: str, result: Any, ctx: AgentContext) -> Any:
        """Hook: post-process tool result before returning to LLM. Return modified result."""
        return result

    async def on_final_result(self, result: dict, ctx: AgentContext) -> dict:
        """Hook: post-process the final result. Return modified result."""
        return result

    def parse_result(self, text: str, ctx: AgentContext) -> dict:
        """Parse the LLM's final text into a structured result. Override for custom parsing."""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"output": text}


# ─────────────────────────────────────────────────────────────────────────────
# ENGINE — the core execution loop
# ─────────────────────────────────────────────────────────────────────────────

class AgentEngine:
    """
    The platform's core execution engine.
    Instantiated once at startup. Shared across all agents.
    """

    def __init__(
        self,
        llm_gateway: "LLMGateway",
        cost_manager: CostManager,
        rate_limiter: RateLimiter,
        audit_logger: AuditLogger,
        security: SecurityLayer,
        validator: ValidationEngine,
        memory: MemoryManager,
        prompt_library: PromptLibrary,
        max_iterations: int = 25,
    ):
        self._llm = llm_gateway
        self._cost = cost_manager
        self._rate = rate_limiter
        self._audit = audit_logger
        self._security = security
        self._validator = validator
        self._memory = memory
        self._prompts = prompt_library
        self._max_iterations = max_iterations

    async def run(self, agent: AgentBase, payload: dict, ctx: AgentContext) -> dict:
        """
        Run an agent to completion. This is the ONLY entry point.
        Every platform service is invoked from here.
        """

        # ── Pre-flight checks ─────────────────────────────────────────
        await self._rate.check_and_consume(ctx.agent_id, ctx.tenant_id)
        await self._security.validate_input(payload, ctx)
        await self._validator.validate_input(agent.AGENT_ID, payload)
        await self._cost.check_budget(ctx.agent_id, ctx.tenant_id)

        # ── Resolve system prompt ──────────────────────────────────────
        system_prompt = await self._prompts.resolve(agent.system_prompt())

        # ── Load conversation memory ───────────────────────────────────
        history = await self._memory.load_short_term(ctx.session_id) if ctx.session_id else []

        # ── Build initial messages ─────────────────────────────────────
        messages = history + [{"role": "user", "content": json.dumps(payload, indent=2)}]

        result = None
        try:
            result = await self._run_loop(agent, system_prompt, messages, ctx)
        except BudgetExceededError as e:
            result = self._budget_exceeded_response(ctx, str(e))
        except Exception as e:
            logger.error(f"Engine error [{ctx.request_id}]: {e}", exc_info=True)
            result = self._error_response(ctx, str(e))
        finally:
            # ── Post-flight ────────────────────────────────────────────
            await self._audit.write(payload, result or {}, ctx)
            await self._cost.record(ctx)
            if ctx.session_id:
                await self._memory.save_short_term(ctx.session_id, messages, result)

        result = await agent.on_final_result(result, ctx)
        await self._security.sanitise_output(result, ctx)
        await self._validator.validate_output(agent.AGENT_ID, result)
        return result

    async def _run_loop(
        self, agent: AgentBase, system_prompt: str,
        messages: list, ctx: AgentContext
    ) -> dict:

        while ctx.iteration < self._max_iterations:
            ctx.iteration += 1

            # Agent hook: modify messages before LLM call
            messages = await agent.on_before_llm_call(messages, ctx)

            # Inject long-term memory context if available
            if memory_context := await self._memory.retrieve_relevant(
                messages[-1]["content"], ctx
            ):
                messages = self._inject_memory(messages, memory_context)

            # LLM call via gateway (handles retry, pooling, fallback)
            response = await self._llm.call(
                system_prompt=system_prompt,
                tools=agent.tools(),
                messages=messages,
                ctx=ctx
            )

            if response.stop_reason == "end_turn":
                text = next((b.text for b in response.content if hasattr(b, "text")), "{}")
                return agent.parse_result(text, ctx)

            if response.stop_reason == "tool_use":
                tool_results = await self._execute_tool_calls(agent, response.content, ctx)
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})

        # Max iterations reached
        logger.warning(f"Max iterations reached [{ctx.request_id}]")
        return {"status": "max_iterations_reached", "partial": True}

    async def _execute_tool_calls(
        self, agent: AgentBase,
        content_blocks: list, ctx: AgentContext
    ) -> list:
        """Execute all tool calls, optionally in parallel for independent tools."""

        tool_uses = [b for b in content_blocks if b.type == "tool_use"]

        async def run_one(block) -> dict:
            t0 = time.monotonic()
            try:
                # Security: validate tool inputs before execution
                await self._security.validate_tool_call(block.name, block.input, ctx)

                result = await agent.execute_tool(block.name, block.input, ctx)
                result = await agent.on_after_tool_call(block.name, result, ctx)
                status = "ok"
            except ToolSecurityError as e:
                result = f"SECURITY_BLOCK: {e}"
                status = "security_blocked"
            except Exception as e:
                result = f"TOOL_ERROR: {e}"
                status = "error"
                logger.warning(f"Tool {block.name} failed: {e}")

            latency = int((time.monotonic() - t0) * 1000)
            ctx.record_tool_call(block.name, status, latency)

            return {
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": str(result)
            }

        # Run all tool calls concurrently (platform handles parallelism automatically)
        results = await asyncio.gather(*[run_one(b) for b in tool_uses])
        return list(results)

    def _inject_memory(self, messages: list, memory_context: str) -> list:
        """Prepend relevant long-term memory to the last user message."""
        last = messages[-1]
        if last["role"] == "user":
            messages[-1] = {
                "role": "user",
                "content": f"[Relevant context from memory]:\n{memory_context}\n\n[Request]:\n{last['content']}"
            }
        return messages

    def _budget_exceeded_response(self, ctx: AgentContext, reason: str) -> dict:
        return {"status": "budget_exceeded", "reason": reason,
                "request_id": ctx.request_id, "cost_so_far_usd": ctx.cost_usd}

    def _error_response(self, ctx: AgentContext, reason: str) -> dict:
        return {"status": "error", "reason": reason, "request_id": ctx.request_id}
```

---

### C# Implementation — Core Engine

```csharp
// Platform/Core/AgentEngine.cs

using System;
using System.Collections.Generic;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;

namespace AgentPlatform.Core
{
    /// <summary>
    /// Central execution engine. Registered as a singleton in DI.
    /// Every agent invocation flows through here.
    /// </summary>
    public class AgentEngine
    {
        private readonly ILlmGateway _llmGateway;
        private readonly ICostManager _costManager;
        private readonly IRateLimiter _rateLimiter;
        private readonly IAuditLogger _auditLogger;
        private readonly ISecurityLayer _security;
        private readonly IValidationEngine _validator;
        private readonly IMemoryManager _memory;
        private readonly IPromptLibrary _promptLibrary;
        private readonly ILogger<AgentEngine> _logger;
        private const int MaxIterations = 25;

        public AgentEngine(
            ILlmGateway llmGateway, ICostManager costManager,
            IRateLimiter rateLimiter, IAuditLogger auditLogger,
            ISecurityLayer security, IValidationEngine validator,
            IMemoryManager memory, IPromptLibrary promptLibrary,
            ILogger<AgentEngine> logger)
        {
            _llmGateway = llmGateway;
            _costManager = costManager;
            _rateLimiter = rateLimiter;
            _auditLogger = auditLogger;
            _security = security;
            _validator = validator;
            _memory = memory;
            _promptLibrary = promptLibrary;
            _logger = logger;
        }

        public async Task<AgentResult> RunAsync(
            IAgent agent,
            Dictionary<string, object> payload,
            AgentContext ctx,
            CancellationToken ct = default)
        {
            // Pre-flight
            await _rateLimiter.CheckAndConsumeAsync(ctx.AgentId, ctx.TenantId, ct);
            await _security.ValidateInputAsync(payload, ctx, ct);
            await _validator.ValidateInputAsync(agent.AgentId, payload, ct);
            await _costManager.CheckBudgetAsync(ctx.AgentId, ctx.TenantId, ct);

            var systemPrompt = await _promptLibrary.ResolveAsync(agent.SystemPrompt());
            var history = ctx.SessionId != null
                ? await _memory.LoadShortTermAsync(ctx.SessionId, ct)
                : new List<ChatMessage>();

            var messages = new List<ChatMessage>(history)
            {
                new ChatMessage("user", JsonSerializer.Serialize(payload))
            };

            AgentResult result;
            try
            {
                result = await RunLoopAsync(agent, systemPrompt, messages, ctx, ct);
            }
            catch (BudgetExceededException ex)
            {
                result = AgentResult.BudgetExceeded(ctx, ex.Message);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Engine error [{RequestId}]", ctx.RequestId);
                result = AgentResult.Error(ctx, ex.Message);
            }
            finally
            {
                await _auditLogger.WriteAsync(payload, result, ctx, ct);
                await _costManager.RecordAsync(ctx, ct);
                if (ctx.SessionId != null)
                    await _memory.SaveShortTermAsync(ctx.SessionId, messages, result, ct);
            }

            result = await agent.OnFinalResultAsync(result, ctx);
            await _security.SanitiseOutputAsync(result, ctx, ct);
            await _validator.ValidateOutputAsync(agent.AgentId, result, ct);
            return result;
        }

        private async Task<AgentResult> RunLoopAsync(
            IAgent agent, string systemPrompt,
            List<ChatMessage> messages, AgentContext ctx,
            CancellationToken ct)
        {
            for (int i = 0; i < MaxIterations; i++)
            {
                ctx.Iteration = i + 1;
                messages = await agent.OnBeforeLlmCallAsync(messages, ctx);

                var memCtx = await _memory.RetrieveRelevantAsync(
                    messages[^1].Content, ctx, ct);
                if (memCtx != null)
                    messages = InjectMemory(messages, memCtx);

                var response = await _llmGateway.CallAsync(
                    systemPrompt, agent.Tools(), messages, ctx, ct);

                if (response.StopReason == "end_turn")
                {
                    var text = response.GetText();
                    return agent.ParseResult(text, ctx);
                }

                if (response.StopReason == "tool_use")
                {
                    var toolResults = await ExecuteToolCallsAsync(agent, response, ctx, ct);
                    messages.Add(new ChatMessage("assistant", response.Content));
                    messages.Add(new ChatMessage("user", toolResults));
                }
            }

            return AgentResult.MaxIterationsReached(ctx);
        }

        private async Task<object> ExecuteToolCallsAsync(
            IAgent agent, LlmResponse response,
            AgentContext ctx, CancellationToken ct)
        {
            var tasks = response.ToolUseBlocks.Select(async block =>
            {
                var t0 = DateTime.UtcNow;
                string result;
                string status;
                try
                {
                    await _security.ValidateToolCallAsync(block.Name, block.Input, ctx, ct);
                    var raw = await agent.ExecuteToolAsync(block.Name, block.Input, ctx);
                    result = JsonSerializer.Serialize(raw);
                    status = "ok";
                }
                catch (ToolSecurityException ex)
                {
                    result = $"SECURITY_BLOCK: {ex.Message}";
                    status = "security_blocked";
                }
                catch (Exception ex)
                {
                    result = $"TOOL_ERROR: {ex.Message}";
                    status = "error";
                    _logger.LogWarning("Tool {Tool} failed: {Error}", block.Name, ex.Message);
                }

                ctx.RecordToolCall(block.Name, status,
                    (int)(DateTime.UtcNow - t0).TotalMilliseconds);

                return new ToolResult(block.Id, result);
            });

            return await Task.WhenAll(tasks);
        }

        private List<ChatMessage> InjectMemory(List<ChatMessage> msgs, string context)
        {
            var last = msgs[^1];
            if (last.Role == "user")
                msgs[^1] = new ChatMessage("user",
                    $"[Memory Context]:\n{context}\n\n[Request]:\n{last.Content}");
            return msgs;
        }
    }

    // ── AgentContext ────────────────────────────────────────────────────────

    public class AgentContext
    {
        public string RequestId { get; } = Guid.NewGuid().ToString();
        public string? SessionId { get; init; }
        public string AgentId { get; init; } = "";
        public string AgentVersion { get; init; } = "";
        public string TenantId { get; init; } = "";
        public string? UserId { get; init; }
        public int Iteration { get; set; }
        public DateTime StartTime { get; } = DateTime.UtcNow;
        public List<ToolCallRecord> ToolCalls { get; } = new();
        public List<LlmCallRecord> LlmCalls { get; } = new();
        public int TotalInputTokens { get; private set; }
        public int TotalOutputTokens { get; private set; }
        public Dictionary<string, string> Tags { get; init; } = new();

        public int ElapsedMs => (int)(DateTime.UtcNow - StartTime).TotalMilliseconds;

        public void RecordToolCall(string tool, string status, int latencyMs) =>
            ToolCalls.Add(new(tool, status, latencyMs, Iteration));

        public void RecordLlmCall(string model, int inputTok, int outputTok, int latencyMs)
        {
            LlmCalls.Add(new(model, inputTok, outputTok, latencyMs));
            TotalInputTokens += inputTok;
            TotalOutputTokens += outputTok;
        }
    }

    // ── IAgent contract ─────────────────────────────────────────────────────

    public interface IAgent
    {
        string AgentId { get; }
        string AgentVersion { get; }
        string SystemPrompt();
        IReadOnlyList<ToolSchema> Tools();
        Task<object> ExecuteToolAsync(string name, Dictionary<string, object> inputs, AgentContext ctx);
        Task<List<ChatMessage>> OnBeforeLlmCallAsync(List<ChatMessage> messages, AgentContext ctx)
            => Task.FromResult(messages);   // default: pass-through
        Task<AgentResult> OnFinalResultAsync(AgentResult result, AgentContext ctx)
            => Task.FromResult(result);     // default: pass-through
        AgentResult ParseResult(string text, AgentContext ctx);
    }
}
```

---

### LLM Gateway — The Resilient LLM Client

The gateway abstracts the LLM provider behind a resilient interface with:
retries, exponential backoff, circuit breaker, and model fallback.

```python
# platform/core/llm_gateway.py

import asyncio
import time
import random
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional
import anthropic
from anthropic import APIStatusError, APIConnectionError, APITimeoutError

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"       # Normal — all requests pass
    OPEN = "open"           # Tripped — all requests fail fast
    HALF_OPEN = "half_open" # Testing — one request passes to check recovery


@dataclass
class CircuitBreaker:
    """
    Circuit breaker pattern for the LLM API.
    Prevents cascading failures when the LLM API is degraded.
    """
    failure_threshold: int = 5       # Open after 5 consecutive failures
    recovery_timeout_s: float = 60.0 # Try again after 60 seconds
    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _failures: int = field(default=0, init=False)
    _last_failure_time: float = field(default=0.0, init=False)

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if time.monotonic() - self._last_failure_time > self.recovery_timeout_s:
                self._state = CircuitState.HALF_OPEN
        return self._state

    def record_success(self):
        self._failures = 0
        self._state = CircuitState.CLOSED

    def record_failure(self):
        self._failures += 1
        self._last_failure_time = time.monotonic()
        if self._failures >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.error("Circuit breaker OPENED — LLM API appears degraded")


class LLMGateway:
    """
    Platform's single LLM access point.
    Every agent call goes through here. Never access the LLM client directly.

    Provides:
    - Connection pooling
    - Exponential backoff retry
    - Circuit breaker
    - Model fallback (primary → secondary)
    - Token tracking
    - Streaming support
    """

    RETRY_STATUS_CODES = {429, 529, 503, 502}
    MAX_RETRIES = 4

    def __init__(self, primary_model: str, fallback_model: Optional[str] = None):
        self._client = anthropic.AsyncAnthropic()
        self._primary_model = primary_model
        self._fallback_model = fallback_model
        self._circuit = CircuitBreaker()
        self._model_registry: dict[str, str] = {}  # agent_id → model override

    def register_model_override(self, agent_id: str, model: str):
        """Allow agents to specify a preferred model. Platform can override for cost reasons."""
        self._model_registry[agent_id] = model

    def resolve_model(self, ctx: "AgentContext") -> str:
        """Model routing: agent preference → agent config → platform default."""
        return self._model_registry.get(ctx.agent_id, self._primary_model)

    async def call(
        self, system_prompt: str, tools: list,
        messages: list, ctx: "AgentContext"
    ) -> anthropic.types.Message:

        if self._circuit.state == CircuitState.OPEN:
            raise LLMUnavailableError("Circuit breaker is OPEN — LLM API unavailable")

        model = self.resolve_model(ctx)

        for attempt in range(self.MAX_RETRIES):
            try:
                t0 = time.monotonic()
                response = await self._client.messages.create(
                    model=model,
                    max_tokens=2048,
                    system=[{
                        "type": "text",
                        "text": system_prompt,
                        "cache_control": {"type": "ephemeral"}
                    }],
                    tools=tools,
                    messages=messages
                )
                latency_ms = int((time.monotonic() - t0) * 1000)
                ctx.record_llm_call(
                    model,
                    response.usage.input_tokens,
                    response.usage.output_tokens,
                    latency_ms
                )
                self._circuit.record_success()
                return response

            except APIStatusError as e:
                if e.status_code in self.RETRY_STATUS_CODES and attempt < self.MAX_RETRIES - 1:
                    wait = self._backoff(attempt)
                    logger.warning(f"LLM {e.status_code}, retry {attempt+1} in {wait:.1f}s")
                    await asyncio.sleep(wait)
                    # On 429 with fallback, switch model
                    if e.status_code == 429 and self._fallback_model and attempt == 1:
                        model = self._fallback_model
                        logger.info(f"Switched to fallback model: {model}")
                    continue
                self._circuit.record_failure()
                raise

            except (APIConnectionError, APITimeoutError) as e:
                if attempt < self.MAX_RETRIES - 1:
                    wait = self._backoff(attempt)
                    logger.warning(f"LLM connection error, retry {attempt+1} in {wait:.1f}s")
                    await asyncio.sleep(wait)
                    continue
                self._circuit.record_failure()
                raise

        raise LLMMaxRetriesError(f"LLM call failed after {self.MAX_RETRIES} attempts")

    @staticmethod
    def _backoff(attempt: int) -> float:
        """Exponential backoff with jitter: 1s, 2s, 4s, 8s (+/- 20% jitter)."""
        base = 2 ** attempt
        jitter = base * 0.2 * random.random()
        return base + jitter
```

---

## 5. Component 2: Tool Registry & Framework

The Tool Registry is the platform's catalogue of capabilities.
Any developer registers a tool once. Every agent can discover and use it.

### The Problem Without a Registry

```
Without registry:                With registry:
─────────────────               ──────────────────────
Every agent defines its own     Tools are registered centrally:
"get_customer" tool schema.       @platform.tool("get_customer")
The schema in Agent A differs     def get_customer(customer_id: str) -> Customer:
from Agent B. Subtle bugs.          ...
                                  ↑ Schema auto-generated from type hints
                                    Versioned. Tested. Shared by all agents.
```

### Python — Tool Registry

```python
# platform/tools/registry.py

import inspect
import json
from typing import Any, Callable, get_type_hints, Optional
from dataclasses import dataclass, field
from functools import wraps
import jsonschema

from platform.services.security import SecurityLayer
from platform.services.audit import AuditLogger


@dataclass
class ToolMetadata:
    name: str
    description: str
    version: str
    owner_team: str
    tags: list[str]
    requires_permissions: list[str]     # RBAC: which agent permissions are needed
    rate_limit_per_minute: int = 60
    timeout_seconds: int = 30
    retryable: bool = True
    input_schema: dict = field(default_factory=dict)
    output_schema: dict = field(default_factory=dict)
    handler: Optional[Callable] = None

    def to_llm_schema(self) -> dict:
        """Convert to the format LLMs expect."""
        return {
            "name": self.name,
            "description": f"{self.description} [v{self.version}]",
            "input_schema": self.input_schema
        }


class ToolRegistry:
    """
    Central catalogue of all platform tools.
    Singleton — one instance per deployment.
    """

    def __init__(self, security: SecurityLayer, audit: AuditLogger):
        self._tools: dict[str, ToolMetadata] = {}
        self._security = security
        self._audit = audit

    def register(
        self,
        name: str,
        description: str,
        version: str = "1.0.0",
        owner_team: str = "platform",
        tags: list[str] = None,
        requires_permissions: list[str] = None,
        rate_limit_per_minute: int = 60,
        timeout_seconds: int = 30,
        retryable: bool = True
    ):
        """Decorator to register a function as a platform tool."""

        def decorator(fn: Callable) -> Callable:
            # Auto-generate schema from Python type hints
            input_schema = _schema_from_hints(fn)

            meta = ToolMetadata(
                name=name,
                description=description,
                version=version,
                owner_team=owner_team,
                tags=tags or [],
                requires_permissions=requires_permissions or [],
                rate_limit_per_minute=rate_limit_per_minute,
                timeout_seconds=timeout_seconds,
                retryable=retryable,
                input_schema=input_schema,
                handler=fn
            )
            self._tools[name] = meta

            @wraps(fn)
            async def wrapper(*args, **kwargs):
                return await fn(*args, **kwargs)

            wrapper._tool_meta = meta
            return wrapper

        return decorator

    def get(self, name: str) -> ToolMetadata:
        if name not in self._tools:
            raise ToolNotFoundError(f"Tool '{name}' not found in registry")
        return self._tools[name]

    def get_schemas_for_agent(self, agent_permissions: list[str]) -> list[dict]:
        """Return LLM-ready schemas for tools this agent has permission to use."""
        return [
            meta.to_llm_schema()
            for meta in self._tools.values()
            if all(p in agent_permissions for p in meta.requires_permissions)
        ]

    async def execute(
        self, name: str, inputs: dict,
        ctx: "AgentContext", agent_permissions: list[str]
    ) -> Any:
        """
        Execute a registered tool with full platform services applied:
        - Permission check
        - Input validation
        - Rate limiting
        - Timeout
        - Retry
        - Audit logging
        """
        meta = self.get(name)

        # Permission check
        missing = [p for p in meta.requires_permissions if p not in agent_permissions]
        if missing:
            raise ToolPermissionError(f"Tool {name} requires permissions: {missing}")

        # Input validation against schema
        try:
            jsonschema.validate(inputs, meta.input_schema)
        except jsonschema.ValidationError as e:
            raise ToolInputValidationError(f"Tool {name} input invalid: {e.message}")

        # Execute with timeout
        import asyncio
        try:
            result = await asyncio.wait_for(
                meta.handler(**inputs),
                timeout=meta.timeout_seconds
            )
        except asyncio.TimeoutError:
            raise ToolTimeoutError(f"Tool {name} timed out after {meta.timeout_seconds}s")

        return result

    def list_tools(self, tag: str = None) -> list[ToolMetadata]:
        tools = list(self._tools.values())
        if tag:
            tools = [t for t in tools if tag in t.tags]
        return tools


def _schema_from_hints(fn: Callable) -> dict:
    """Auto-generate JSON Schema from Python type hints."""
    hints = get_type_hints(fn)
    sig = inspect.signature(fn)

    properties = {}
    required = []

    type_map = {
        str: {"type": "string"},
        int: {"type": "integer"},
        float: {"type": "number"},
        bool: {"type": "boolean"},
        list: {"type": "array"},
        dict: {"type": "object"},
    }

    for param_name, param in sig.parameters.items():
        if param_name in ("self", "ctx"):
            continue
        hint = hints.get(param_name, str)
        schema_type = type_map.get(hint, {"type": "string"})
        properties[param_name] = schema_type
        if param.default is inspect.Parameter.empty:
            required.append(param_name)

    return {
        "type": "object",
        "properties": properties,
        "required": required
    }
```

### Using the Registry — Developer Experience

```python
# tools/customer_tools.py  (written by a product team)

from platform.tools.registry import ToolRegistry
from platform.deps import get_registry  # DI-injected singleton

registry = get_registry()

@registry.register(
    name="get_customer_profile",
    description="Get full customer profile including tier, preferences, and account status",
    version="2.1.0",
    owner_team="customer-platform",
    tags=["customer", "read"],
    requires_permissions=["customer.read"],
    rate_limit_per_minute=200,
    timeout_seconds=5
)
async def get_customer_profile(customer_id: str) -> dict:
    # This is just a regular async function — no agent-specific code
    return await customer_db.get(customer_id)


@registry.register(
    name="update_customer_tier",
    description="Update a customer's service tier (standard/premium/enterprise)",
    version="1.0.0",
    owner_team="customer-platform",
    tags=["customer", "write"],
    requires_permissions=["customer.write", "tier.modify"],  # Requires TWO permissions
    rate_limit_per_minute=20,
    timeout_seconds=10,
    retryable=False  # Write operations are not retried
)
async def update_customer_tier(customer_id: str, new_tier: str) -> dict:
    return await customer_db.update_tier(customer_id, new_tier)


# Now ANY agent can use these tools — just request them by name:

class CustomerSupportAgent(AgentBase):
    AGENT_ID = "customer-support"

    def tools(self) -> list[dict]:
        # Gets schemas for all tools this agent has permission to use
        return registry.get_schemas_for_agent(
            agent_permissions=["customer.read"]  # This agent can only read
        )
        # Returns: [get_customer_profile schema]
        # Does NOT return: update_customer_tier (requires customer.write)

    async def execute_tool(self, name, inputs, ctx):
        return await registry.execute(
            name, inputs, ctx,
            agent_permissions=["customer.read"]
        )
```

### C# Tool Registry

```csharp
// Platform/Tools/ToolRegistry.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Text.Json;
using System.Threading.Tasks;

namespace AgentPlatform.Tools
{
    [AttributeUsage(AttributeTargets.Method)]
    public class PlatformToolAttribute : Attribute
    {
        public string Name { get; set; } = "";
        public string Description { get; set; } = "";
        public string Version { get; set; } = "1.0.0";
        public string OwnerTeam { get; set; } = "";
        public string[] Tags { get; set; } = Array.Empty<string>();
        public string[] RequiresPermissions { get; set; } = Array.Empty<string>();
        public int RateLimitPerMinute { get; set; } = 60;
        public int TimeoutSeconds { get; set; } = 30;
        public bool Retryable { get; set; } = true;
    }

    public class ToolRegistry
    {
        private readonly Dictionary<string, RegisteredTool> _tools = new();
        private readonly ISecurityLayer _security;

        public ToolRegistry(ISecurityLayer security) => _security = security;

        /// <summary>
        /// Scan an assembly for all methods decorated with [PlatformTool].
        /// Call this at startup: registry.ScanAssembly(typeof(CustomerTools).Assembly)
        /// </summary>
        public void ScanAssembly(Assembly assembly)
        {
            foreach (var type in assembly.GetTypes())
            {
                var instance = Activator.CreateInstance(type);
                foreach (var method in type.GetMethods())
                {
                    var attr = method.GetCustomAttribute<PlatformToolAttribute>();
                    if (attr == null) continue;

                    var schema = SchemaGenerator.FromMethod(method);
                    _tools[attr.Name] = new RegisteredTool
                    {
                        Metadata = new ToolMetadata(attr, schema),
                        Handler = (inputs) => (Task<object>)method.Invoke(instance,
                            MapInputs(inputs, method))!
                    };
                }
            }
        }

        public IReadOnlyList<ToolSchema> GetSchemasForAgent(IEnumerable<string> permissions)
        {
            var permSet = new HashSet<string>(permissions);
            return _tools.Values
                .Where(t => t.Metadata.RequiresPermissions.All(p => permSet.Contains(p)))
                .Select(t => t.Metadata.ToLlmSchema())
                .ToList();
        }

        public async Task<object> ExecuteAsync(
            string name, Dictionary<string, object> inputs,
            AgentContext ctx, IEnumerable<string> agentPermissions)
        {
            if (!_tools.TryGetValue(name, out var tool))
                throw new ToolNotFoundException(name);

            var permSet = new HashSet<string>(agentPermissions);
            var missing = tool.Metadata.RequiresPermissions
                .Where(p => !permSet.Contains(p)).ToList();
            if (missing.Any())
                throw new ToolPermissionException(name, missing);

            using var cts = new CancellationTokenSource(
                TimeSpan.FromSeconds(tool.Metadata.TimeoutSeconds));

            return await tool.Handler(inputs).WaitAsync(cts.Token);
        }
    }

    // Usage — in any tool class:
    public class CustomerTools
    {
        private readonly ICustomerRepository _repo;
        public CustomerTools(ICustomerRepository repo) => _repo = repo;

        [PlatformTool(
            Name = "get_customer_profile",
            Description = "Get full customer profile",
            Version = "2.1.0",
            OwnerTeam = "customer-platform",
            Tags = new[] { "customer", "read" },
            RequiresPermissions = new[] { "customer.read" },
            TimeoutSeconds = 5
        )]
        public async Task<object> GetCustomerProfile(string customerId)
            => await _repo.GetAsync(customerId);
    }
}
```

---

## 6. Component 3: Prompt Library

Prompts are first-class citizens of the platform — versioned, tested,
stored externally, and retrieved at runtime. Never hardcoded in agent code.

### Why a Prompt Library?

```
Without it:                          With it:
────────────                         ──────────────────
Prompt is a 400-line string          Prompt stored in S3/DB/Git
in the middle of agent.py            Versioned: fraud-agent/v2.3.0

To change the prompt:                To change the prompt:
  → Deploy new code                    → Update prompt file
  → Risk regression in any            → Run eval suite automatically
    agent that imports the file        → A/B test old vs new
  → No version history                 → Rollback in 10 seconds

To know what prompt is               Full history, diff, who changed
  running in prod: ???                 what and why
```

### Python — Prompt Library

```python
# platform/prompts/library.py

import hashlib
import yaml
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
import boto3          # For S3 storage
import redis.asyncio as redis

from platform.services.audit import AuditLogger


@dataclass
class PromptVersion:
    prompt_id: str
    version: str
    content: str
    variables: list[str]           # Variables this prompt expects: {agent_name}, {date}
    model_hint: Optional[str]      # Preferred model for this prompt
    eval_score: Optional[float]    # Latest eval score (0.0-1.0)
    author: str
    changelog: str
    created_at: str
    content_hash: str = field(init=False)

    def __post_init__(self):
        self.content_hash = hashlib.sha256(self.content.encode()).hexdigest()[:16]

    def render(self, variables: dict[str, str]) -> str:
        """Render the prompt with variable substitution."""
        result = self.content
        for key, value in variables.items():
            result = result.replace(f"{{{key}}}", value)
        return result


class PromptLibrary:
    """
    Central prompt storage with versioning, caching, and A/B testing.

    Storage hierarchy:
      1. In-memory cache (nanoseconds)
      2. Redis cache (milliseconds)
      3. S3 / Database (tens of milliseconds)
    """

    def __init__(
        self,
        storage_backend: "PromptStorageBackend",
        cache: redis.Redis,
        audit: AuditLogger,
        cache_ttl_s: int = 300
    ):
        self._storage = storage_backend
        self._cache = cache
        self._audit = audit
        self._cache_ttl = cache_ttl_s
        self._local_cache: dict[str, PromptVersion] = {}

    async def resolve(self, prompt_ref: str) -> str:
        """
        Resolve a prompt reference to rendered text.

        prompt_ref formats:
          - "my-agent-prompt"              → latest stable version
          - "my-agent-prompt@v2.3.0"       → exact version
          - "my-agent-prompt@canary"       → canary/experimental version
          - "Hello, {name}!"               → literal string (pass-through)
        """
        # Literal string — pass through
        if not self._is_ref(prompt_ref):
            return prompt_ref

        prompt_id, version = self._parse_ref(prompt_ref)
        return await self._load(prompt_id, version)

    async def render(self, prompt_ref: str, variables: dict[str, str]) -> str:
        """Resolve and render a prompt with variables."""
        prompt_id, version = self._parse_ref(prompt_ref)
        pv = await self._load_version(prompt_id, version)
        return pv.render(variables)

    async def _load(self, prompt_id: str, version: str = "latest") -> str:
        pv = await self._load_version(prompt_id, version)
        return pv.content

    async def _load_version(self, prompt_id: str, version: str) -> PromptVersion:
        cache_key = f"prompt:{prompt_id}:{version}"

        # L1: local memory cache
        if cache_key in self._local_cache:
            return self._local_cache[cache_key]

        # L2: Redis
        raw = await self._cache.get(cache_key)
        if raw:
            pv = PromptVersion(**json.loads(raw))
            self._local_cache[cache_key] = pv
            return pv

        # L3: Storage backend (S3, DB, Git)
        pv = await self._storage.load(prompt_id, version)
        if not pv:
            raise PromptNotFoundError(f"Prompt not found: {prompt_id}@{version}")

        # Populate caches
        await self._cache.setex(cache_key, self._cache_ttl, json.dumps(pv.__dict__))
        self._local_cache[cache_key] = pv
        return pv

    async def publish(self, pv: PromptVersion, set_as_latest: bool = False):
        """Publish a new prompt version. Triggers eval run before making live."""
        await self._storage.save(pv)
        await self._cache.delete(f"prompt:{pv.prompt_id}:latest")
        if set_as_latest:
            await self._storage.set_latest(pv.prompt_id, pv.version)
        await self._audit.log_prompt_change(pv)

    async def ab_test(self, prompt_id: str, traffic_pct: float = 0.1) -> str:
        """
        A/B test: serve canary version to traffic_pct of requests.
        Returns the version to use based on random sampling.
        """
        import random
        if random.random() < traffic_pct:
            return f"{prompt_id}@canary"
        return f"{prompt_id}@latest"

    @staticmethod
    def _is_ref(s: str) -> bool:
        return not s.startswith("You are") and not s.startswith("##")

    @staticmethod
    def _parse_ref(ref: str) -> tuple[str, str]:
        if "@" in ref:
            parts = ref.split("@", 1)
            return parts[0], parts[1]
        return ref, "latest"


# ── File-based backend (for local dev / git-stored prompts) ──────────────────

class FilePromptBackend:
    """Store prompts as YAML files. Good for git-tracked prompts."""

    def __init__(self, base_path: str):
        self._base = Path(base_path)

    async def load(self, prompt_id: str, version: str) -> Optional[PromptVersion]:
        # Layout: prompts/fraud-agent/v2.3.0.yaml
        #         prompts/fraud-agent/latest → symlink or alias file
        path = self._base / prompt_id / f"{version}.yaml"
        if not path.exists():
            return None

        data = yaml.safe_load(path.read_text())
        return PromptVersion(**data)

    async def save(self, pv: PromptVersion):
        path = self._base / pv.prompt_id
        path.mkdir(parents=True, exist_ok=True)
        (path / f"{pv.version}.yaml").write_text(yaml.dump(pv.__dict__))

    async def set_latest(self, prompt_id: str, version: str):
        path = self._base / prompt_id / "latest.yaml"
        path.write_text(yaml.dump({"alias": version}))
```

### Prompt File Format (YAML)

```yaml
# prompts/fraud-agent/v2.3.0.yaml

prompt_id: fraud-agent-system
version: "2.3.0"
author: "platform-team"
created_at: "2026-03-01T09:00:00Z"
changelog: "Added impossible travel detection. Raised structuring threshold to 8 transactions."
model_hint: "claude-sonnet-4-6"
eval_score: 0.94
variables:
  - bank_name
  - currency_symbol
  - ctr_threshold

content: |
  ## Role
  You are a senior fraud analyst at {bank_name}. You protect customers and
  the bank from fraud with decisive, well-reasoned actions.

  ## Currency
  All amounts are in {currency_symbol}.

  ## Thresholds
  - CTR reporting required for cash transactions exceeding {ctr_threshold}
  - Structuring: flag patterns of {structuring_count} or more sub-threshold deposits

  ## Decision Framework
  [... rest of prompt ...]
```

### Using the Prompt Library in an Agent

```python
# my_agent/fraud_agent.py

class FraudAgent(AgentBase):
    AGENT_ID = "fraud-agent"

    def system_prompt(self) -> str:
        # Option 1: Reference by ID — library resolves version at runtime
        return "fraud-agent-system"

        # Option 2: Reference with explicit version — pinned for stability
        # return "fraud-agent-system@v2.3.0"

        # Option 3: Literal string — bypasses library (use only in dev)
        # return "You are a fraud analyst..."

    async def get_rendered_prompt(self, ctx: AgentContext) -> str:
        # If the prompt has variables, render them
        return await prompt_library.render(
            "fraud-agent-system",
            variables={
                "bank_name": "National Bank",
                "currency_symbol": "$",
                "ctr_threshold": "10,000"
            }
        )
```

---

*Continues in Part 2 →*
