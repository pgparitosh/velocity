# Velocity — AI Agent Platform: Implementation Plan

## Executive Summary

Velocity is a reusable, production-grade AI Agent Platform that enables teams to build, deploy, and scale AI agents in days instead of weeks. The platform provides shared horizontal infrastructure (LLM access, retry logic, cost tracking, audit logging, security, tool management) so that agent developers only write what is unique to their domain: the system prompt, tools, and configuration.

This document is the **detailed implementation plan** for building Velocity as a Python-first platform, designed for modularity, performance, security, testability, and productionisation from day one. Distributed as a PyPI package (`pip install velocity-platform`).

---

## Decisions Finalized

| Decision | Choice | Rationale |
|----------|--------|----------|
| **Language** | Python-first | C# SDK deferred to Phase 2 (post-MVP) |
| **LLM Providers** | Fully provider-agnostic from day one | Anthropic is just an example, not the standard. Any API provider, any platform. |
| **Infrastructure** | In-memory for dev, config-driven backends for staging/prod | Plug-and-play via configuration only — no rewriting DB operations |
| **Distribution** | PyPI package (`pip install velocity-platform`) | Clean install path for agent developers |
| **Vector DB** | pgvector (dev/staging), Qdrant (production) | Zero extra infra in dev, purpose-built perf in prod |
| **Event Streaming** | Redis Streams | Already using Redis; migrate to Kafka when volume demands it |
| **CLI** | Included from Sprint 0 | Full-proof platform with premium DX |
| **Multi-tenancy** | Core functionality from day one | Data and tenant separation is what makes this a real-world application |

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           VELOCITY PLATFORM                                  │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐   │
│  │  LAYER 4: AGENT SDK (Developer-Facing)                               │   │
│  │  AgentBase · @tool decorator · AgentBuilder · register_agent         │   │
│  │  agent_config.yaml schema · CLI tooling (velocity init/run/test)     │   │
│  └──────────────────────────────┬────────────────────────────────────────┘   │
│                                  │                                            │
│  ┌───────────────────────────────▼────────────────────────────────────────┐  │
│  │  LAYER 3: CORE ENGINE                                                  │  │
│  │  AgentEngine · AgentContext · LoopController · StopConditions          │  │
│  │  LLM Gateway (retry, circuit breaker, model routing, pooling)         │  │
│  └───┬──────┬──────┬──────┬──────┬──────┬────────────────────────────────┘  │
│      │      │      │      │      │      │                                     │
│  ┌───▼──┐┌──▼──┐┌──▼──┐┌──▼──┐┌──▼──┐┌──▼────────┐                         │
│  │TOOL  ││PRMT ││MEMY ││ORCH ││MCP  ││EVAL      │                         │
│  │REGIS ││LIBR ││MGMT ││ENGN ││BRKR ││FRAMEWORK │                         │
│  └──────┘└─────┘└─────┘└─────┘└─────┘└──────────┘                         │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐   │
│  │  LAYER 2: PLATFORM SERVICES (Cross-Cutting Middleware)                │   │
│  │  CostManager · RateLimiter · SecurityLayer · ValidationEngine         │   │
│  │  AuditLogger · EventBus · SecretVault · HealthChecker                 │   │
│  └───────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐   │
│  │  LAYER 1: INFRASTRUCTURE ABSTRACTIONS (config-driven, plug-and-play)  │   │
│  │  Cache (Redis/Memory) · DB (Any SQL via config) · VectorStore         │   │
│  │  EventStream (Redis Streams) · ObjectStore (S3/Local)                 │   │
│  └───────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Proposed Changes

### Phase 0: Project Bootstrap & Contracts (Sprint 1 — Week 1-2)

The foundation. Define every interface, establish project structure, CI/CD, and the developer experience before writing any business logic.

---

#### [NEW] Project Structure

```
velocity/
├── planning/                          # Existing planning docs
│   ├── building-an-ai-agent-platform-part1.md
│   ├── building-an-ai-agent-platform-part2.md
│   └── building-an-ai-agent-platform-part3.md
│
├── src/
│   └── velocity/                      # Main Python package
│       ├── __init__.py                # Public API surface
│       ├── py.typed                   # PEP 561 type stub marker
│       │
│       ├── core/                      # LAYER 3: Core Engine
│       │   ├── __init__.py
│       │   ├── engine.py              # AgentEngine — the execution loop
│       │   ├── context.py             # AgentContext dataclass
│       │   ├── base.py                # AgentBase abstract class (the contract)
│       │   ├── llm_gateway.py         # LLM Gateway with retry/circuit breaker
│       │   ├── circuit_breaker.py     # Circuit breaker pattern (standalone)
│       │   └── stop_conditions.py     # Max iterations, budget, timeout
│       │
│       ├── tools/                     # Tool Registry & Framework
│       │   ├── __init__.py
│       │   ├── registry.py            # ToolRegistry singleton
│       │   ├── metadata.py            # ToolMetadata dataclass
│       │   ├── schema_gen.py          # Auto-generate JSON Schema from type hints
│       │   └── decorators.py          # @tool decorator
│       │
│       ├── prompts/                   # Prompt Library
│       │   ├── __init__.py
│       │   ├── library.py             # PromptLibrary with caching
│       │   ├── models.py              # PromptVersion dataclass
│       │   ├── backends/
│       │   │   ├── __init__.py
│       │   │   ├── base.py            # Abstract backend
│       │   │   ├── file_backend.py    # YAML file-based (git-tracked prompts)
│       │   │   └── s3_backend.py      # S3 storage backend
│       │   └── renderer.py            # Variable substitution engine
│       │
│       ├── memory/                    # Memory Management
│       │   ├── __init__.py
│       │   ├── manager.py             # MemoryManager (unified interface)
│       │   ├── models.py              # MemoryEntry dataclass
│       │   ├── short_term.py          # Conversation memory (Redis-backed)
│       │   ├── long_term.py           # Semantic memory (Vector DB-backed)
│       │   ├── episodic.py            # Episode memory (structured storage)
│       │   ├── embedder.py            # TextEmbedder abstraction
│       │   └── vector_store.py        # VectorStore abstraction
│       │
│       ├── services/                  # LAYER 2: Platform Services
│       │   ├── __init__.py
│       │   ├── cost/
│       │   │   ├── __init__.py
│       │   │   ├── manager.py         # CostManager
│       │   │   ├── pricing.py         # Model pricing table
│       │   │   ├── routing.py         # Model routing rules
│       │   │   └── budget.py          # BudgetConfig + BudgetStore
│       │   ├── rate_limiter/
│       │   │   ├── __init__.py
│       │   │   ├── limiter.py         # RateLimiter (sliding window)
│       │   │   └── config.py          # RateLimitConfig
│       │   ├── security/
│       │   │   ├── __init__.py
│       │   │   ├── layer.py           # SecurityLayer
│       │   │   ├── pii.py             # PII detection + masking
│       │   │   ├── injection.py       # Prompt injection detection
│       │   │   └── permissions.py     # RBAC permission checks
│       │   ├── validation/
│       │   │   ├── __init__.py
│       │   │   ├── engine.py          # ValidationEngine
│       │   │   └── schemas.py         # AgentSchema registry
│       │   ├── audit/
│       │   │   ├── __init__.py
│       │   │   ├── logger.py          # AuditLogger
│       │   │   ├── models.py          # AuditRecord dataclass
│       │   │   └── backends/
│       │   │       ├── __init__.py
│       │   │       ├── base.py        # Abstract audit backend
│       │   │       ├── postgres.py    # PostgreSQL backend
│       │   │       ├── s3.py          # S3 WORM storage
│       │   │       └── memory.py      # In-memory (for testing)
│       │   └── events/
│       │       ├── __init__.py
│       │       └── bus.py             # EventBus (platform event system)
│       │
│       ├── orchestration/             # Multi-Agent Orchestration
│       │   ├── __init__.py
│       │   ├── engine.py              # OrchestrationEngine (DAG executor)
│       │   ├── models.py              # WorkflowNode, WorkflowResult
│       │   └── human_gate.py          # Human-in-the-loop gate
│       │
│       ├── mcp/                       # MCP Protocol Layer
│       │   ├── __init__.py
│       │   ├── broker.py              # MCPBroker (tool routing)
│       │   └── server.py              # FastAPI MCP server
│       │
│       ├── evals/                     # Evaluation Framework
│       │   ├── __init__.py
│       │   ├── suite.py               # EvalSuite, EvalCase
│       │   ├── runner.py              # EvalRunner
│       │   └── reporters.py           # Console, JSON, CI reporters
│       │
│       ├── observability/             # Metrics & Monitoring
│       │   ├── __init__.py
│       │   ├── metrics.py             # Prometheus metric definitions
│       │   └── middleware.py          # MetricsMiddleware wrapper
│       │
│       ├── infra/                     # LAYER 1: Infrastructure (config-driven)
│       │   ├── __init__.py
│       │   ├── cache.py               # ICacheBackend (Redis / In-Memory)
│       │   ├── database.py            # IDatabaseBackend (config-driven, any SQL)
│       │   ├── object_store.py        # IObjectStore (S3 / Local filesystem)
│       │   ├── event_stream.py        # IEventStream (Redis Streams)
│       │   └── config.py              # Platform configuration loader (YAML)
│       │
│       ├── api/                       # Platform REST API
│       │   ├── __init__.py
│       │   ├── app.py                 # FastAPI application
│       │   ├── routes/
│       │   │   ├── agents.py          # /v1/agents/run, /v1/agents/{id}/status
│       │   │   ├── costs.py           # /v1/platform/costs
│       │   │   ├── health.py          # /health/live, /health/ready
│       │   │   └── admin.py           # /internal/admin/* (platform admin)
│       │   ├── auth.py                # JWT auth + tenant extraction
│       │   └── middleware.py          # Request logging, CORS, error handling
│       │
│       ├── sdk/                       # Developer SDK (simplified public API)
│       │   ├── __init__.py            # Exports: AgentBase, tool, register_agent
│       │   └── builder.py            # AgentBuilder — wires agent from YAML config
│       │
│       └── exceptions.py             # All platform exception types
│
├── tests/                             # Test suite
│   ├── conftest.py                    # Shared fixtures, test infra config
│   ├── unit/                          # Fast, isolated unit tests
│   │   ├── core/
│   │   │   ├── test_engine.py
│   │   │   ├── test_context.py
│   │   │   ├── test_llm_gateway.py
│   │   │   └── test_circuit_breaker.py
│   │   ├── tools/
│   │   │   ├── test_registry.py
│   │   │   └── test_schema_gen.py
│   │   ├── prompts/
│   │   │   └── test_library.py
│   │   ├── memory/
│   │   │   ├── test_short_term.py
│   │   │   ├── test_long_term.py
│   │   │   └── test_episodic.py
│   │   ├── services/
│   │   │   ├── test_cost_manager.py
│   │   │   ├── test_rate_limiter.py
│   │   │   ├── test_security.py
│   │   │   ├── test_validation.py
│   │   │   └── test_audit.py
│   │   └── orchestration/
│   │       └── test_orchestration.py
│   ├── integration/                   # Tests against real backends
│   │   ├── test_redis_cache.py
│   │   ├── test_postgres_audit.py
│   │   └── test_llm_gateway_live.py
│   └── e2e/                           # Full agent execution tests
│       ├── test_sample_agent.py
│       └── test_multi_agent_workflow.py
│
├── examples/                          # Example agents (shipped with platform)
│   ├── hello-agent/                   # Minimal agent to demonstrate platform
│   │   ├── agent_config.yaml
│   │   ├── agent.py
│   │   └── tools.py
│   ├── expense-approver/              # Production-style example from planning docs
│   │   ├── agent_config.yaml
│   │   ├── agent.py
│   │   ├── tools.py
│   │   ├── prompts/
│   │   │   └── v1.0.0.yaml
│   │   └── evals.py
│   └── multi-agent-loan/              # Multi-agent orchestration example
│       ├── workflow.py
│       └── agents/
│
├── deploy/                            # Deployment configurations
│   ├── docker/
│   │   ├── Dockerfile                 # Platform API container
│   │   ├── Dockerfile.dev             # Dev container with hot-reload
│   │   └── docker-compose.yml         # Full local stack (Redis, Postgres, API)
│   └── k8s/
│       ├── deployment.yaml
│       ├── hpa.yaml
│       ├── service.yaml
│       └── configmap.yaml
│
├── docs/                              # Documentation
│   ├── getting-started.md
│   ├── architecture.md
│   ├── agent-developer-guide.md
│   ├── platform-admin-guide.md
│   └── api-reference.md
│
├── scripts/                           # Dev/ops scripts
│   ├── setup-dev.ps1                  # Windows dev environment setup
│   ├── setup-dev.sh                   # Linux/Mac dev environment setup
│   └── db/
│       └── migrations/
│           └── 001_create_audit_tables.sql
│
├── pyproject.toml                     # Project config, dependencies, build
├── .env.example                       # Environment variable template
├── .gitignore
├── LICENSE
└── README.md
```

> [!NOTE]
> The structure separates concerns into 4 layers: Infrastructure → Platform Services → Core Engine → Agent SDK. Each layer depends only on the layers below it. This enables independent testing, swappable backends, and clean interfaces.

---

### Phase 1: Core Engine & Contracts (Sprint 1-2 — Week 1-4)

Build the heart of the platform. Everything else plugs into this.

---

#### [NEW] [velocity/exceptions.py](file:///d:/source/repos/velocity/src/velocity/exceptions.py)

All platform exception types in a single module. Avoids circular imports and gives agents a clean set of catchable errors.

**Key exceptions:**
- `VelocityError` (base) → all platform exceptions inherit from this
- `BudgetExceededError`, `RateLimitExceededError`, `LLMUnavailableError`
- `ToolNotFoundError`, `ToolPermissionError`, `ToolTimeoutError`, `ToolInputValidationError`
- `SecurityValidationError`, `ToolSecurityError`
- `PromptNotFoundError`, `InputValidationError`
- `WorkflowRejectedError`, `WorkflowTimeoutError`

**Design decision:** Flat hierarchy with rich error context (request_id, agent_id, details dict) for debugging. Every exception serializes cleanly to JSON for API responses.

---

#### [NEW] [velocity/core/context.py](file:///d:/source/repos/velocity/src/velocity/core/context.py)

The `AgentContext` dataclass — the single object flowing through every execution.

**Key fields:**
- Identity: `request_id`, `session_id`, `agent_id`, `agent_version`, `tenant_id`, `user_id`
- Execution state: `iteration`, `tool_calls[]`, `llm_calls[]`, `events[]`
- Budget tracking: `total_input_tokens`, `total_output_tokens`, `total_tool_calls`
- Tracing: `trace_id`, `parent_request_id` (for sub-agents), `tags`
- Computed: `elapsed_ms`, `cost_usd`

**Design decisions:**
- `AgentContext` is a `@dataclass` with `slots=True` for memory efficiency
- Context is **never modified by tools directly** — only the engine modifies it through controlled methods (`record_tool_call`, `record_llm_call`)
- Includes `parent_request_id` for parent→child tracing in multi-agent workflows
- `tags` dict enables arbitrary metadata (feature, trigger type, PR size) for cost attribution

---

#### [NEW] [velocity/core/base.py](file:///d:/source/repos/velocity/src/velocity/core/base.py)

The `AgentBase` abstract class — **the contract every agent must implement**.

**3 required methods:**
1. `system_prompt() → str` — return prompt text or a PromptRef string
2. `tools() → list[dict]` — return tool schemas in LLM-format
3. `execute_tool(name, inputs, ctx) → Any` — execute a tool call

**5 optional hooks:**
1. `on_before_llm_call(messages, ctx) → messages` — modify messages before each LLM call
2. `on_after_tool_call(tool, result, ctx) → result` — post-process tool results
3. `on_final_result(result, ctx) → result` — post-process the final output
4. `parse_result(text, ctx) → dict` — parse LLM text into structured output
5. `on_error(error, ctx) → None` — custom error handling hook

**Design decision:** The base class defines the **extension points** and returns sensible defaults for all hooks. Agent developers override only what they need. This is the "USB spec" — conform to it and get all platform services for free.

---

#### [NEW] [velocity/core/circuit_breaker.py](file:///d:/source/repos/velocity/src/velocity/core/circuit_breaker.py)

Standalone circuit breaker implementation (separated from LLM Gateway for reusability).

**States:** `CLOSED` (normal) → `OPEN` (blocking) → `HALF_OPEN` (testing)
**Config:** `failure_threshold` (default 5), `recovery_timeout_s` (default 60)
**Thread safety:** Uses `threading.Lock` for state transitions

---

#### [NEW] [velocity/core/llm_gateway.py](file:///d:/source/repos/velocity/src/velocity/core/llm_gateway.py)

The platform's single LLM access point. **No agent should ever call LLM APIs directly.** Fully **provider-agnostic from day one** — Anthropic, OpenAI, Google, Azure, or any custom API.

**Capabilities:**
- Connection pooling (re-use async clients per provider)
- Exponential backoff with jitter (1s, 2s, 4s, 8s ±20%)
- Circuit breaker integration (per-provider circuit breakers)
- Model fallback (primary → secondary on 429, cross-provider fallback supported)
- Token tracking (recorded to `AgentContext`)
- Streaming support (`async for` / `AsyncIterator`)
- Provider abstraction via `ILlmProvider` protocol

**Provider abstraction layer:**
```python
class ILlmProvider(Protocol):
    """Any LLM provider implements this. The platform never calls vendor SDKs directly."""
    provider_name: str
    supported_models: list[str]
    async def call(self, system_prompt, tools, messages, model, max_tokens) -> LlmResponse: ...
    async def stream(self, system_prompt, tools, messages, model, max_tokens) -> AsyncIterator[LlmChunk]: ...
    async def health_check(self) -> bool: ...
```

**Concrete providers (all shipped from Sprint 1):**
- `AnthropicProvider` — Claude models (Opus, Sonnet, Haiku)
- `OpenAIProvider` — GPT-4o, GPT-4o-mini, o1, o3
- `GoogleProvider` — Gemini models
- `AzureOpenAIProvider` — Azure-hosted GPT models
- `CustomProvider` — any OpenAI-compatible API endpoint (Ollama, vLLM, Together, Groq, etc.)

**Provider configuration (in `platform_config.yaml`):**
```yaml
llm:
  default_provider: openai
  default_model: gpt-4o
  providers:
    anthropic:
      api_key_env: ANTHROPIC_API_KEY
      models: [claude-opus-4-6, claude-sonnet-4-6, claude-haiku-4-5-20251001]
    openai:
      api_key_env: OPENAI_API_KEY
      models: [gpt-4o, gpt-4o-mini]
    google:
      api_key_env: GOOGLE_API_KEY
      models: [gemini-2.5-pro, gemini-2.5-flash]
    custom:
      base_url: http://localhost:11434/v1
      models: [llama3, mistral]
  fallback_chain: [openai, anthropic, google]  # Cross-provider fallback
```

**Design decision:** The gateway owns model resolution: `agent preference → agent_config override → platform default`. The `CostManager` can further override via routing rules. Providers are registered via configuration — adding a new provider requires zero code changes if it's OpenAI-compatible.

---

#### [NEW] [velocity/core/engine.py](file:///d:/source/repos/velocity/src/velocity/core/engine.py)

The `AgentEngine` — the core execution loop. Instantiated **once at startup**, shared across all agents.

**Execution flow (single entry point: `engine.run()`):**
1. **Pre-flight checks:** Rate limit → Security validate input → Schema validate input → Budget check
2. **Resolve system prompt** from PromptLibrary (with caching)
3. **Load conversation memory** (short-term, if session exists)
4. **Build initial messages** (history + new user payload)
5. **Run the agentic loop:**
   - Inject long-term memory context (semantic search)
   - Call agent's `on_before_llm_call` hook
   - LLM call via Gateway (handles retry, pooling, fallback)
   - If `end_turn` → parse result, break
   - If `tool_use` → execute tool calls (parallel via `asyncio.gather`), append results, continue
   - If max iterations → return partial result
6. **Post-flight:** Write audit log → Record cost → Save short-term memory
7. **Output processing:** Agent's `on_final_result` hook → Security sanitize output → Schema validate output

**Design decisions:**
- All services injected via constructor (DI-friendly, testable with mocks)
- Tool calls run in parallel by default (`asyncio.gather`)
- Security validation happens **before tool execution** (pre-flight) and **after agent output** (PII masking)
- Budget is checked before execution, and cost is recorded after — this means a request that blows the budget mid-execution still gets logged

---

### Phase 2: Tool Layer (Sprint 2 — Week 3-4)

---

#### [NEW] velocity/tools/ package

**Tool Registry:**
- Central catalogue of all platform tools (singleton per deployment)
- Decorator-based registration: `@registry.register(name, description, ...)`
- Auto-schema generation from Python type hints via `inspect.signature` + `get_type_hints`
- Permission-gated access: tools declare `requires_permissions`, agents declare their permissions
- Tool execution with platform services: permission check → input validation → rate limiting → timeout → retry → audit logging

**ToolMetadata:**
- `name`, `description`, `version`, `owner_team`, `tags[]`
- `requires_permissions[]` — RBAC permissions needed
- `rate_limit_per_minute`, `timeout_seconds`, `retryable`
- `input_schema` (auto-generated), `output_schema` (optional)
- `handler` — the actual function

**Schema generation:**
- Maps Python types (str→string, int→integer, float→number, bool→boolean, list→array, dict→object)
- Handles `Optional[T]` → nullable field
- Handles `Literal["a", "b"]` → enum
- Handles dataclass/Pydantic models → nested object schemas
- Required fields = parameters without defaults

---

### Phase 3: Knowledge Layer (Sprint 3 — Week 5-6)

---

#### [NEW] velocity/prompts/ package

**Prompt Library:**
- Central prompt storage with versioning, caching, and A/B testing
- Three-level cache: L1 in-memory (dict) → L2 Redis → L3 storage backend (S3/file)
- Prompt references: `"my-agent"` (latest), `"my-agent@v2.3.0"` (pinned), `"my-agent@canary"` (experimental)
- Variable substitution: `{bank_name}`, `{currency}` etc.
- A/B testing: serve canary version to configurable traffic %, measure via eval scores

**Storage backends:**
- `FilePromptBackend` — YAML files in git (for dev and git-tracked prompts)
- `S3PromptBackend` — S3 bucket (for production, with caching)

**Prompt YAML format:**
```yaml
prompt_id: fraud-agent-system
version: "2.3.0"
author: "platform-team"
changelog: "Added impossible travel detection"
model_hint: "claude-sonnet-4-6"
eval_score: 0.94
variables: [bank_name, currency_symbol]
content: |
  You are a fraud analyst at {bank_name}...
```

---

#### [NEW] velocity/memory/ package

**Three memory types:**

| Type | Storage | TTL | Use Case |
|------|---------|-----|----------|
| Short-term | Redis | 1 hour (configurable) | Multi-turn conversation context |
| Long-term | Vector DB | Permanent | Facts, preferences, institutional knowledge |
| Episodic | Redis list | 90 days | Past interaction outcomes and patterns |

**Short-term memory:**
- Load/save conversation history per session
- Auto-prune to token budget (remove oldest messages when approaching limit)
- Summarize-and-trim for very long conversations (keep last 10 messages, summarize earlier ones)

**Long-term memory:**
- Store via embeddings in vector DB (Qdrant, pgvector, Pinecone)
- Retrieve top-k semantically relevant memories above a score threshold
- Scoped by `agent_id` and optionally `customer_id`

**Episodic memory:**
- Record interaction summaries with outcomes
- Retrieve past episodes for a customer/agent pair
- Capped at 100 episodes per entity

**Design decision:** `MemoryManager` is itself a thin facade over the three sub-managers. The engine calls it; agents never interact with memory directly (the platform injects relevant context automatically).

---

### Phase 4: Safety & Compliance Layer (Sprint 3-4 — Week 5-8)

---

#### [NEW] velocity/services/cost/ package

**CostManager:**
- Static pricing table for models (Anthropic, OpenAI — easily extensible)
- Model routing rules: task type → cheapest sufficient model (classification→Haiku, reasoning→Sonnet, deep analysis→Opus)
- Budget enforcement: daily + monthly + per-request limits with hard stop
- Budget alerts at configurable threshold (default 80%)
- Cost recording to Redis (daily/monthly aggregation) + time-series DB
- Cost reporting: per-agent, per-tenant, per-feature breakdown

**Design decision:** Routing rules use a `list[(condition_fn, model)]` pattern. Conditions are lambdas that inspect `ctx.tags`. This allows teams to tag requests (e.g., `task_type: classification`) and the platform automatically routes to the cheapest model.

---

#### [NEW] velocity/services/rate_limiter/ package

**Three-level rate limiting:**
1. Platform-wide — protects LLM API quota
2. Per-agent — prevents noisy neighbours
3. Per-tenant — fair usage enforcement

**Implementation:** Sliding window using Redis sorted sets + Lua script for atomic check-and-increment. This is distributed (works across multiple platform instances) and thread-safe.

**Design decision:** Use Lua scripts in Redis for atomic rate limit checks. This prevents race conditions when multiple platform instances are running. The sorted set approach gives exact sliding window counts, not approximations.

---

#### [NEW] velocity/services/security/ package

**Four security subsystems:**

1. **PII Detection & Masking** — regex-based patterns for SSN, credit cards, emails, phone numbers, credentials. Applied to agent output before returning to caller. Extensible for jurisdiction (GDPR, CCPA, HIPAA).

2. **Prompt Injection Detection** — pattern matching for common injection attempts ("ignore previous instructions", role hijacking, XML injection). Applied to both user inputs and tool results.

3. **Permission Checks (RBAC)** — agents declare permissions, tools declare required permissions. Security layer enforces the intersection. Restricted tool categories: `financial.write`, `pii.read`, `infrastructure`, `admin`.

4. **Output Sanitization** — scan agent output for PII, mask it, log a warning. This is a safety net — even if the agent's tool returns raw PII, the platform strips it.

> [!IMPORTANT]
> **Security is applied automatically** to every agent. Agent developers cannot skip, override, or bypass platform security. This is a fundamental design principle.

---

#### [NEW] velocity/services/validation/ package

**ValidationEngine:**
- Central schema registry: agents register input/output schemas
- Input validation: JSON Schema validation before tool or agent execution
- Output validation: JSON Schema + optional Pydantic model validation after execution
- Input validation failures → reject request with clear error message
- Output validation failures → **log warning but don't block** (advisory, to avoid breaking agents)

**Design decision:** Input validation is strict (reject bad data). Output validation is advisory (log but don't block). The reasoning: bad input is the caller's fault, bad output might be the LLM's creative interpretation — logging it enables improvement without breaking the agent.

---

#### [NEW] velocity/services/audit/ package

**AuditLogger:**
- Every platform invocation creates an immutable audit record
- Dual-write: PostgreSQL (queryable, recent) + S3 with Object Lock (tamper-proof, long-term)
- Never update or delete audit records — append only
- Fields: identity, timing, sanitized input hash, execution trace (tool calls, LLM calls), decision, cost, compliance flags

**AuditRecord:**
- `record_id`, `schema_version`, `request_id`, `parent_request_id`
- `agent_id`, `agent_version`, `tenant_id`, `user_id`
- `timestamp_utc`, `elapsed_ms`
- `input_hash` (SHA-256 of original input — integrity without storing raw data)
- `tool_calls[]`, `llm_calls[]`, `iteration_count`
- `decision`, `status`, `confidence`, `human_review_required`
- `input_tokens`, `output_tokens`, `cost_usd`
- `pii_detected_in_output`, `regulatory_flags[]`

**Compliance queries:**
- `query_by_customer(customer_id, days)` — GDPR right-of-explanation
- `query_human_review_queue(agent_id)` — pending human reviews
- `query_cost_report(tenant_id, days)` — cost breakdown

---

### Phase 5: Orchestration & MCP (Sprint 5 — Week 9-10)

---

#### [NEW] velocity/orchestration/ package

**OrchestrationEngine:**
- Executes multi-agent workflows defined as DAGs (directed acyclic graphs)
- Node types: `AGENT`, `PARALLEL`, `CONDITION`, `TRANSFORM`, `HUMAN_GATE`
- Each agent node creates a child context with `parent_request_id` for tracing
- Parallel nodes use `asyncio.gather` — independent agents run concurrently
- Condition nodes branch based on payload/output inspection
- Human gate nodes pause workflow, poll for human approval (webhook or long-poll)

**Design decision:** Workflows are defined in code (Python), not YAML/JSON. This gives maximum flexibility for conditions and transforms. A YAML-based workflow definition can be added as a higher-level abstraction later.

---

#### [NEW] velocity/mcp/ package

**MCPBroker:**
- Manages connections to MCP servers (external and internal)
- Tool discovery: fetch tool lists from MCP servers, translate to platform schema
- Tool execution: route tool calls to the appropriate MCP server
- Supports both local MCP servers (in-process) and remote (HTTP/SSE)

**MCP Server:**
- FastAPI-based MCP server that exposes platform tools via MCP protocol
- Supports `tools/list` and `tools/call` methods
- JSON-RPC 2.0 wire format
- This enables any MCP-compatible LLM client (Claude Desktop, etc.) to use platform tools

---

### Phase 6: Eval Framework & Observability (Sprint 5-6 — Week 9-12)

---

#### [NEW] velocity/evals/ package

**EvalSuite:**
- Define test cases with: input, mocked tools, expected assertions
- Assertions are lambdas: `lambda r: r["decision"] == "APPROVE"`
- Run in CI with `use_mocks=True` (no real LLM calls for deterministic tests)
- Run with real LLM for accuracy evaluation (tagged as integration tests)

**EvalRunner:**
- Execute eval suite, collect results
- Track pass rate over time (detect regressions)
- Block deployment if pass rate < threshold (default 90%)
- Report in console, JSON (for CI), and Grafana dashboard

---

#### [NEW] velocity/observability/ package

**Prometheus metrics:**
- `platform_agent_requests_total` (counter, by agent/tenant/status)
- `platform_agent_latency_seconds` (histogram, by agent)
- `platform_agent_cost_usd_total` (counter, by agent/model/tenant)
- `platform_tool_calls_total` (counter, by agent/tool/status)
- `platform_tokens_total` (counter, by agent/model/type)
- `platform_rate_limit_hits_total` (counter, by agent/window)
- `platform_circuit_breaker_state` (gauge, by provider)
- `platform_agent_eval_score` (gauge, by agent/eval_suite_version)

**MetricsMiddleware:**
- Wraps `AgentEngine.run()` to emit all metrics automatically
- Zero code required from agent developers

---

### Phase 7: API, SDK & Developer Experience (Sprint 6-7 — Week 11-14)

---

#### [NEW] velocity/api/ package

**FastAPI Platform API:**
- `POST /v1/agents/run` — run an agent (sync or async mode)
- `GET /v1/agents/{request_id}/status` — poll for async result
- `GET /v1/platform/costs` — cost breakdown for calling tenant
- `GET /v1/platform/audit` — audit log query
- `GET /health/live` — liveness probe
- `GET /health/ready` — readiness probe (checks all dependencies)
- `POST /internal/admin/*` — platform admin endpoints (separate auth)

**Auth:** JWT token with `tenant_id` claim. All API calls are automatically scoped to the calling tenant.

---

#### [NEW] velocity/sdk/ package

**The Developer SDK — the simplified public API:**

```python
from velocity.sdk import AgentBase, tool, register_agent, AgentContext

@tool("get_order", "Get order details by ID", requires=["order.read"])
async def get_order(order_id: str) -> dict: ...

class MyAgent(AgentBase):
    AGENT_ID = "my-agent"
    def system_prompt(self): return "my-agent-prompt"
    def tools(self): return self.registry_tools()
    async def execute_tool(self, name, inputs, ctx): return await self.run_tool(name, inputs, ctx)

register_agent(MyAgent, config_path="agent_config.yaml")
```

**AgentBuilder:**
- Reads `agent_config.yaml` and auto-wires: model, budget, rate limits, permissions, validation schemas, memory config, prompt reference
- Creates correct service instances, registers them with the platform
- Agent developer writes **zero infrastructure code**

---

#### [NEW] CLI Tooling

```
velocity init <agent-name>      # Scaffold a new agent (config, agent.py, tools.py, evals.py)
velocity run <agent-name>       # Run agent locally with hot-reload
velocity test <agent-name>      # Run eval suite
velocity deploy <agent-name>    # Deploy to platform
velocity costs [--days 30]      # View cost report
velocity audit [--agent-id X]   # Query audit logs
```

---

### Phase 8: Infrastructure & Deployment (Sprint 7-8 — Week 13-16)

---

#### [NEW] velocity/infra/ package

**Infrastructure abstractions** — swap backends via **configuration only**, no code changes:

| Abstraction | Dev/Test Backend | Production Backend |
|---|---|---|
| `ICacheBackend` | In-memory dict | Redis |
| `IDatabaseBackend` | SQLite | PostgreSQL / MySQL / Any SQL DB |
| `IObjectStore` | Local filesystem | S3 / Azure Blob / GCS |
| `IVectorStore` | In-memory list | pgvector (staging) / Qdrant (prod) |
| `IEventStream` | In-memory queue | Redis Streams |

**Configuration-driven backend switching (`platform_config.yaml`):**
```yaml
infra:
  cache:
    backend: redis           # or "memory" for dev
    redis_url: ${REDIS_URL}
  database:
    backend: postgresql      # or "sqlite" for dev
    connection_string: ${DATABASE_URL}
  vector_store:
    backend: qdrant           # or "pgvector" or "memory"
    qdrant_url: ${QDRANT_URL}
  object_store:
    backend: s3               # or "local"
    s3_bucket: ${S3_BUCKET}
  event_stream:
    backend: redis_streams    # or "memory" for dev
    redis_url: ${REDIS_URL}
```

> [!IMPORTANT]
> **Plug-and-play infrastructure.** Switching from SQLite (dev) to PostgreSQL (prod) is a single config change. The platform uses the `IDatabaseBackend` protocol everywhere — no SQL queries are rewritten. The `config.py` module reads `platform_config.yaml` and instantiates the correct backend at startup.

**Design decision:** Every infra dependency has an in-memory implementation for testing and local dev. This means developers can run the full platform locally with `velocity run` without Docker, Redis, or PostgreSQL installed. For staging/production, swap backends by changing a YAML config — zero code changes.

---

#### [NEW] deploy/ package

**Docker:**
- `Dockerfile` — production container (multi-stage build, minimal image)
- `Dockerfile.dev` — dev container with hot-reload
- `docker-compose.yml` — full local stack (Redis + PostgreSQL + Qdrant + Platform API)

**Kubernetes:**
- `deployment.yaml` — 3 replicas, rolling update (zero downtime)
- `hpa.yaml` — auto-scale 3→30 replicas based on CPU (65%) and queue depth (100 items/pod)
- `service.yaml` — ClusterIP + LoadBalancer
- `configmap.yaml` — platform configuration

**Database migrations:**
- `001_create_audit_tables.sql` — audit log schema with indexes
- Managed via Alembic (Python) or manual SQL scripts

---

## How Agents Consume the Platform (Productionisation)

### Model 1: Library/SDK Import (Recommended for Python)
```
Agents install velocity as a pip package:
  pip install velocity-platform

Agent code imports the SDK:
  from velocity.sdk import AgentBase, tool, register_agent

Agent runs within the platform's FastAPI process or their own process.
```

### Model 2: HTTP API (Recommended for non-Python agents or microservices)
```
Platform runs as a standalone service.
Agents call the REST API:
  POST /v1/agents/run
  {
    "agent_id": "my-agent",
    "payload": { ... },
    "session_id": "optional-session-id"
  }

Agent code lives outside the platform entirely.
Platform handles everything: LLM calls, tools, memory, audit, cost.
```

### Model 3: Agent Registration + Platform Hosting
```
Agent developer creates:
  1. agent_config.yaml
  2. agent.py (extends AgentBase)
  3. tools.py (domain tools)
  4. prompts/*.yaml

They push to the platform's agent registry.
Platform builds, deploys, and hosts the agent.
Agent is accessible via API: POST /v1/agents/run {"agent_id": "my-agent"}
```

---

## Implementation Sprint Plan

| Sprint | Weeks | Focus | Deliverable |
|--------|-------|-------|-------------|
| 0 | 1-2 | Bootstrap, contracts, project setup | Project structure, all interfaces, `pyproject.toml`, CI/CD skeleton |
| 1 | 3-4 | Core Engine | `AgentEngine`, `AgentContext`, `AgentBase`, `LLMGateway`, `CircuitBreaker` |
| 2 | 3-4 | Tool Layer | `ToolRegistry`, `@tool` decorator, schema generation |
| 3 | 5-6 | Knowledge Layer | `PromptLibrary`, `MemoryManager` (all 3 types) |
| 4 | 5-8 | Safety & Compliance | `CostManager`, `RateLimiter`, `SecurityLayer`, `ValidationEngine`, `AuditLogger` |
| 5 | 9-10 | Orchestration & MCP | `OrchestrationEngine`, `MCPBroker`, `MCPServer` |
| 6 | 9-12 | Eval & Observability | `EvalSuite`, `EvalRunner`, Prometheus metrics, `MetricsMiddleware` |
| 7 | 11-14 | API, SDK & DX | FastAPI API, `AgentBuilder`, CLI tooling, `velocity init/run/test` |
| 8 | 13-16 | Infra & Deployment | Docker, K8s, infra abstractions, database migrations |

> [!TIP]
> Sprints overlap intentionally. The core engine (Sprint 1) is usable with mock services from day one. Each subsequent sprint adds real implementations behind the interfaces established in Sprint 0.

---

## Verification Plan

### Automated Tests
- **Unit tests** for every module (target: 90%+ coverage)
- **Integration tests** against real Redis/PostgreSQL (in Docker via CI)
- **E2E tests** running a sample agent through the full platform pipeline
- **Eval tests** for example agents (expense-approver, hello-agent)

### CI/CD Pipeline
```
push → lint (ruff) → type check (mypy) → unit tests → integration tests → eval suite → build → deploy (staging)
```

### Manual Verification
- Run the hello-agent example end-to-end locally
- Run the expense-approver example with mocked tools
- Verify cost tracking accuracy against known inputs
- Verify audit log completeness
- Load test with 100 concurrent agent runs

---

## Multi-Tenancy Design (Core Feature)

Multi-tenancy is built into every layer from Sprint 0:

- **API Layer:** JWT tokens carry `tenant_id` claim. All queries are tenant-scoped automatically.
- **Rate Limiting:** Separate Redis keys per tenant (`rl:tenant:{id}:*`). Tenant A exhausting quota does NOT affect Tenant B.
- **Cost Tracking:** Per-tenant daily/monthly counters and budgets.
- **Audit Logs:** PostgreSQL Row Level Security (RLS) — tenants see only their own records.
- **Memory:** Short-term keys scoped to `mem:short:{tenant_id}:{session_id}`. Vector store namespaced by tenant.
- **Admin API:** Platform-wide view available only to platform admin role via `/internal/admin/*` endpoints.

> [!IMPORTANT]
> Tenant isolation is enforced at the infrastructure layer, not the application layer. This means even a buggy agent cannot accidentally access another tenant's data.
