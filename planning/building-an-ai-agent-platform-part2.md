# Building an AI Agent Platform — Part 2
### Components 4–8: Memory · Cost · Rate Limiting · Security · Validation

---

## 7. Component 4: Memory Management

An agent without memory is an amnesiac. Every turn starts from zero.
Real agents need three kinds of memory:

```
SHORT-TERM (Conversation Memory)
  What was said in THIS conversation.
  Lives in Redis. Expires after inactivity.
  Used for: multi-turn chat, context continuity.
  Max size: trimmed to fit context window.

LONG-TERM (Persistent Memory)
  Facts learned across ALL conversations.
  "Customer X prefers email contact"
  "This codebase uses dependency injection, not service locator"
  Lives in a vector database. Searched by semantic similarity.
  Used for: personalisation, learned preferences, institutional knowledge.

EPISODIC (Event Memory)
  Past interactions and their outcomes.
  "Last time we ran a fraud investigation on this customer, we found X"
  Lives in structured storage. Retrieved by query.
  Used for: avoiding repeating past mistakes, learning patterns.
```

### Python — Memory Manager

```python
# platform/memory/manager.py

import json
import time
import hashlib
from typing import Optional
import redis.asyncio as aioredis
from dataclasses import dataclass, field

# Vector DB client — swap for Pinecone, Weaviate, pgvector, Qdrant
from platform.memory.vector_store import VectorStore
from platform.memory.embedder import TextEmbedder


@dataclass
class MemoryEntry:
    content: str
    agent_id: str
    session_id: Optional[str]
    customer_id: Optional[str]
    timestamp: float = field(default_factory=time.time)
    tags: list[str] = field(default_factory=list)
    entry_id: str = ""

    def __post_init__(self):
        if not self.entry_id:
            self.entry_id = hashlib.sha256(
                f"{self.content}{self.timestamp}".encode()
            ).hexdigest()[:16]


class MemoryManager:
    """
    Unified interface for all agent memory types.
    Platform manages storage backends — agents just call load/save/retrieve.
    """

    SHORT_TERM_TTL = 3600        # 1 hour
    MAX_SHORT_TERM_TURNS = 20    # Keep last 20 messages
    MAX_CONTEXT_TOKENS = 4000    # Prune when exceeding this

    def __init__(
        self,
        cache: aioredis.Redis,
        vector_store: VectorStore,
        embedder: TextEmbedder
    ):
        self._cache = cache
        self._vector = vector_store
        self._embedder = embedder

    # ── Short-term (conversation) memory ─────────────────────────────────────

    async def load_short_term(self, session_id: str) -> list[dict]:
        """Load conversation history for a session."""
        raw = await self._cache.get(f"mem:short:{session_id}")
        if not raw:
            return []
        messages = json.loads(raw)
        return self._prune_to_budget(messages)

    async def save_short_term(
        self, session_id: str,
        messages: list[dict], last_result: dict
    ):
        """Append the latest exchange and save."""
        existing = await self.load_short_term(session_id)

        # Append assistant response
        assistant_text = last_result.get("output") or last_result.get("response_to_customer", "")
        if assistant_text:
            existing.append({"role": "assistant", "content": assistant_text})

        # Keep only the most recent turns
        if len(existing) > self.MAX_SHORT_TERM_TURNS * 2:
            existing = self._summarise_and_trim(existing)

        await self._cache.setex(
            f"mem:short:{session_id}",
            self.SHORT_TERM_TTL,
            json.dumps(existing)
        )

    # ── Long-term (semantic) memory ───────────────────────────────────────────

    async def remember(self, entry: MemoryEntry):
        """Store a fact in long-term memory."""
        embedding = await self._embedder.embed(entry.content)
        await self._vector.upsert(
            id=entry.entry_id,
            vector=embedding,
            metadata={
                "content": entry.content,
                "agent_id": entry.agent_id,
                "session_id": entry.session_id,
                "customer_id": entry.customer_id,
                "timestamp": entry.timestamp,
                "tags": entry.tags
            }
        )

    async def retrieve_relevant(
        self, query: str, ctx: "AgentContext",
        top_k: int = 3, score_threshold: float = 0.75
    ) -> Optional[str]:
        """
        Find the most semantically relevant memories for the current query.
        Returns None if no relevant memories found.
        """
        if not query:
            return None

        embedding = await self._embedder.embed(query)
        results = await self._vector.query(
            vector=embedding,
            top_k=top_k,
            filter={
                "agent_id": ctx.agent_id,
                # Optionally scope to customer
                **({"customer_id": ctx.user_id} if ctx.user_id else {})
            }
        )

        relevant = [r for r in results if r.score >= score_threshold]
        if not relevant:
            return None

        context_parts = [f"- {r.metadata['content']}" for r in relevant]
        return "\n".join(context_parts)

    # ── Episodic memory ───────────────────────────────────────────────────────

    async def get_past_episodes(
        self, customer_id: str, agent_id: str, limit: int = 5
    ) -> list[dict]:
        """Retrieve past interaction summaries for this customer."""
        raw = await self._cache.lrange(
            f"mem:episodic:{agent_id}:{customer_id}", 0, limit - 1
        )
        return [json.loads(r) for r in raw]

    async def record_episode(
        self, customer_id: str, agent_id: str,
        summary: str, outcome: str, metadata: dict
    ):
        """Record the outcome of this interaction for future reference."""
        episode = {
            "summary": summary,
            "outcome": outcome,
            "timestamp": time.time(),
            **metadata
        }
        key = f"mem:episodic:{agent_id}:{customer_id}"
        await self._cache.lpush(key, json.dumps(episode))
        await self._cache.ltrim(key, 0, 99)   # Keep last 100 episodes
        await self._cache.expire(key, 86400 * 90)  # 90 days TTL

    # ── Utilities ──────────────────────────────────────────────────────────────

    def _prune_to_budget(self, messages: list[dict]) -> list[dict]:
        """Remove oldest messages when approaching token budget."""
        token_estimate = sum(len(m["content"]) // 4 for m in messages)
        while token_estimate > self.MAX_CONTEXT_TOKENS and len(messages) > 2:
            removed = messages.pop(0)  # Remove oldest
            token_estimate -= len(removed["content"]) // 4
        return messages

    def _summarise_and_trim(self, messages: list[dict]) -> list[dict]:
        """Summarise the early part of a long conversation."""
        keep_recent = messages[-10:]   # Always keep last 10
        to_summarise = messages[:-10]

        summary = f"[Earlier in this conversation: {len(to_summarise)} messages covering {', '.join(set(m['role'] for m in to_summarise))} exchanges]"

        return [{"role": "system", "content": summary}] + keep_recent
```

### C# — Memory Manager

```csharp
// Platform/Memory/MemoryManager.cs

public class MemoryManager : IMemoryManager
{
    private readonly IDatabase _cache;
    private readonly IVectorStore _vector;
    private readonly ITextEmbedder _embedder;

    private const int ShortTermTtlSeconds = 3600;
    private const int MaxShortTermTurns = 20;
    private const float RelevanceThreshold = 0.75f;

    public async Task<List<ChatMessage>> LoadShortTermAsync(
        string sessionId, CancellationToken ct = default)
    {
        var raw = await _cache.StringGetAsync($"mem:short:{sessionId}");
        if (raw.IsNull) return new List<ChatMessage>();

        var messages = JsonSerializer.Deserialize<List<ChatMessage>>(raw!)!;
        return PruneToTokenBudget(messages);
    }

    public async Task SaveShortTermAsync(
        string sessionId, List<ChatMessage> messages,
        AgentResult result, CancellationToken ct = default)
    {
        if (!string.IsNullOrEmpty(result.Output))
            messages.Add(new ChatMessage("assistant", result.Output));

        if (messages.Count > MaxShortTermTurns * 2)
            messages = TrimOldMessages(messages);

        await _cache.StringSetAsync(
            $"mem:short:{sessionId}",
            JsonSerializer.Serialize(messages),
            TimeSpan.FromSeconds(ShortTermTtlSeconds)
        );
    }

    public async Task<string?> RetrieveRelevantAsync(
        string query, AgentContext ctx,
        CancellationToken ct = default)
    {
        if (string.IsNullOrWhiteSpace(query)) return null;

        var embedding = await _embedder.EmbedAsync(query, ct);
        var results = await _vector.QueryAsync(embedding, topK: 3, filter: new()
        {
            ["agent_id"] = ctx.AgentId,
        }, ct);

        var relevant = results.Where(r => r.Score >= RelevanceThreshold).ToList();
        if (!relevant.Any()) return null;

        return string.Join("\n", relevant.Select(r => $"- {r.Metadata["content"]}"));
    }

    public async Task RememberAsync(MemoryEntry entry, CancellationToken ct = default)
    {
        var embedding = await _embedder.EmbedAsync(entry.Content, ct);
        await _vector.UpsertAsync(entry.Id, embedding, new()
        {
            ["content"] = entry.Content,
            ["agent_id"] = entry.AgentId,
            ["customer_id"] = entry.CustomerId ?? "",
            ["timestamp"] = entry.Timestamp.ToString("O")
        }, ct);
    }

    private static List<ChatMessage> PruneToTokenBudget(List<ChatMessage> messages)
    {
        var tokenBudget = 4000;
        var tokenCount = messages.Sum(m => m.Content.Length / 4);
        while (tokenCount > tokenBudget && messages.Count > 2)
        {
            tokenCount -= messages[0].Content.Length / 4;
            messages.RemoveAt(0);
        }
        return messages;
    }
}
```

---

## 8. Component 5: Cost Management & Model Routing

This is the component that keeps you from a $50,000 surprise on your
cloud bill at the end of the month. Every token must be attributed,
budgeted, and optimised.

### Python — Cost Manager

```python
# platform/services/cost.py

import time
import json
from dataclasses import dataclass, field
from typing import Optional
import redis.asyncio as aioredis


# Pricing table — update when provider prices change
MODEL_PRICING = {
    # Claude models (per 1M tokens)
    "claude-opus-4-6":              {"input": 15.00,  "output": 75.00},
    "claude-sonnet-4-6":            {"input": 3.00,   "output": 15.00},
    "claude-haiku-4-5-20251001":    {"input": 0.80,   "output": 4.00},
    # OpenAI models (for provider-agnostic platforms)
    "gpt-4o":                       {"input": 2.50,   "output": 10.00},
    "gpt-4o-mini":                  {"input": 0.15,   "output": 0.60},
}

# Model routing rules: task complexity → cheapest sufficient model
ROUTING_RULES = [
    # (condition_fn, model)
    (lambda ctx: ctx.tags.get("task_type") == "classification",   "claude-haiku-4-5-20251001"),
    (lambda ctx: ctx.tags.get("task_type") == "extraction",       "claude-haiku-4-5-20251001"),
    (lambda ctx: ctx.tags.get("task_type") == "summarisation",    "claude-sonnet-4-6"),
    (lambda ctx: ctx.tags.get("task_type") == "reasoning",        "claude-sonnet-4-6"),
    (lambda ctx: ctx.tags.get("task_type") == "deep_analysis",    "claude-opus-4-6"),
]


@dataclass
class BudgetConfig:
    agent_id: str
    tenant_id: str
    daily_limit_usd: float
    monthly_limit_usd: float
    per_request_limit_usd: float
    alert_threshold_pct: float = 0.80   # Alert at 80% of daily limit
    hard_stop_at_limit: bool = True


class CostManager:
    """
    Track, attribute, and enforce cost budgets across all agents and tenants.
    """

    def __init__(self, cache: aioredis.Redis, budget_store: "BudgetStore"):
        self._cache = cache
        self._budgets = budget_store

    @staticmethod
    def calculate(model: str, input_tokens: int, output_tokens: int) -> float:
        pricing = MODEL_PRICING.get(model, MODEL_PRICING["claude-sonnet-4-6"])
        return (input_tokens / 1_000_000 * pricing["input"]) + \
               (output_tokens / 1_000_000 * pricing["output"])

    def route_model(self, ctx: "AgentContext", default: str) -> str:
        """Apply routing rules to select the cheapest model for the task."""
        for condition, model in ROUTING_RULES:
            try:
                if condition(ctx):
                    return model
            except Exception:
                pass
        return default

    async def check_budget(self, agent_id: str, tenant_id: str):
        """Raises BudgetExceededError if over limit. Called before each request."""
        budget = await self._budgets.get(agent_id, tenant_id)
        if not budget:
            return  # No budget configured → unlimited

        today_spend = await self._get_daily_spend(agent_id, tenant_id)
        monthly_spend = await self._get_monthly_spend(agent_id, tenant_id)

        if budget.hard_stop_at_limit:
            if today_spend >= budget.daily_limit_usd:
                raise BudgetExceededError(
                    f"Agent {agent_id} exceeded daily budget: "
                    f"${today_spend:.2f} / ${budget.daily_limit_usd:.2f}"
                )
            if monthly_spend >= budget.monthly_limit_usd:
                raise BudgetExceededError(
                    f"Agent {agent_id} exceeded monthly budget"
                )

        # Send alert if approaching limit
        if today_spend >= budget.daily_limit_usd * budget.alert_threshold_pct:
            await self._send_budget_alert(agent_id, today_spend, budget.daily_limit_usd)

    async def record(self, ctx: "AgentContext"):
        """Record the cost of a completed request. Called after every execution."""
        cost = ctx.cost_usd
        today_key = f"cost:daily:{ctx.agent_id}:{ctx.tenant_id}:{self._today()}"
        month_key = f"cost:monthly:{ctx.agent_id}:{ctx.tenant_id}:{self._month()}"

        pipe = self._cache.pipeline()
        pipe.incrbyfloat(today_key, cost)
        pipe.expire(today_key, 86400 * 2)       # Keep 2 days
        pipe.incrbyfloat(month_key, cost)
        pipe.expire(month_key, 86400 * 35)      # Keep 35 days
        await pipe.execute()

        # Write to time-series DB for reporting
        await self._write_cost_record(ctx, cost)

    async def get_cost_report(
        self, tenant_id: str, days: int = 30
    ) -> dict:
        """Generate a cost breakdown report for a tenant."""
        # Query time-series data
        records = await self._query_cost_history(tenant_id, days)
        by_agent = {}
        for r in records:
            by_agent.setdefault(r["agent_id"], {"total": 0, "requests": 0})
            by_agent[r["agent_id"]]["total"] += r["cost_usd"]
            by_agent[r["agent_id"]]["requests"] += 1

        return {
            "tenant_id": tenant_id,
            "period_days": days,
            "total_usd": sum(v["total"] for v in by_agent.values()),
            "by_agent": by_agent,
            "avg_cost_per_request": {
                k: v["total"] / v["requests"]
                for k, v in by_agent.items()
            }
        }

    async def _get_daily_spend(self, agent_id: str, tenant_id: str) -> float:
        raw = await self._cache.get(f"cost:daily:{agent_id}:{tenant_id}:{self._today()}")
        return float(raw) if raw else 0.0

    async def _get_monthly_spend(self, agent_id: str, tenant_id: str) -> float:
        raw = await self._cache.get(f"cost:monthly:{agent_id}:{tenant_id}:{self._month()}")
        return float(raw) if raw else 0.0

    async def _send_budget_alert(self, agent_id: str, spent: float, limit: float):
        pct = (spent / limit) * 100
        # Push to alerting system (PagerDuty, Slack, etc.)
        print(f"⚠️ BUDGET ALERT: {agent_id} at {pct:.0f}% of daily budget (${spent:.2f}/${limit:.2f})")

    @staticmethod
    def _today() -> str:
        return time.strftime("%Y-%m-%d")

    @staticmethod
    def _month() -> str:
        return time.strftime("%Y-%m")
```

---

## 9. Component 6: Rate Limiting

Rate limiting protects the LLM API from abuse and your bill from runaway
agents. It operates at three levels simultaneously.

```
Level 1: Platform-wide rate limit
  Total calls/minute across ALL agents → protects LLM API quota

Level 2: Per-agent rate limit
  Each agent has its own calls/minute allowance → noisy neighbour prevention

Level 3: Per-tenant/user rate limit
  Each customer/team has a calls/minute allowance → fair usage
```

### Python — Token Bucket Rate Limiter

```python
# platform/services/rate_limiter.py

import time
import redis.asyncio as aioredis
from dataclasses import dataclass


@dataclass
class RateLimitConfig:
    requests_per_minute: int
    requests_per_hour: int
    burst_multiplier: float = 1.5   # Allow brief bursts up to 150% of per-minute rate


class RateLimiter:
    """
    Sliding window rate limiter using Redis.
    Thread-safe, distributed (works across multiple server instances).
    """

    def __init__(self, cache: aioredis.Redis):
        self._cache = cache

        # Default limits (configurable per agent in agent_config.yaml)
        self._default_config = RateLimitConfig(
            requests_per_minute=60,
            requests_per_hour=500
        )
        self._configs: dict[str, RateLimitConfig] = {}

    def configure(self, agent_id: str, config: RateLimitConfig):
        self._configs[agent_id] = config

    async def check_and_consume(self, agent_id: str, tenant_id: str):
        """
        Check if this request is within rate limits and consume a token.
        Raises RateLimitExceededError if limit exceeded.
        """
        cfg = self._configs.get(agent_id, self._default_config)
        now = time.time()

        # Check both minute and hour windows simultaneously
        await self._check_window(
            f"rl:agent:{agent_id}:min",
            window_s=60,
            limit=cfg.requests_per_minute,
            now=now
        )
        await self._check_window(
            f"rl:agent:{agent_id}:hour",
            window_s=3600,
            limit=cfg.requests_per_hour,
            now=now
        )
        await self._check_window(
            f"rl:tenant:{tenant_id}:min",
            window_s=60,
            limit=cfg.requests_per_minute * 5,  # Tenants get 5x agent limit
            now=now
        )

    async def _check_window(
        self, key: str, window_s: int,
        limit: int, now: float
    ):
        """Sliding window using Redis sorted set."""
        window_start = now - window_s

        # Lua script for atomic check-and-increment
        script = """
        local key = KEYS[1]
        local window_start = ARGV[1]
        local now = ARGV[2]
        local limit = tonumber(ARGV[3])
        local window_s = tonumber(ARGV[4])

        -- Remove old entries outside the window
        redis.call('ZREMRANGEBYSCORE', key, '-inf', window_start)

        -- Count current requests in window
        local count = redis.call('ZCARD', key)

        if count >= limit then
            return -1  -- Over limit
        end

        -- Add this request
        redis.call('ZADD', key, now, now .. math.random())
        redis.call('EXPIRE', key, window_s + 1)

        return limit - count - 1  -- Remaining tokens
        """

        remaining = await self._cache.eval(
            script, 1, key,
            str(window_start), str(now), str(limit), str(window_s)
        )

        if remaining < 0:
            retry_after = window_s - (now - window_start)
            raise RateLimitExceededError(
                f"Rate limit exceeded for {key}. "
                f"Retry after {retry_after:.0f}s"
            )

    async def get_remaining(self, agent_id: str) -> dict:
        """Return remaining quota for debugging/monitoring."""
        now = time.time()
        cfg = self._configs.get(agent_id, self._default_config)

        min_count = await self._cache.zcount(
            f"rl:agent:{agent_id}:min", now - 60, now
        )
        hour_count = await self._cache.zcount(
            f"rl:agent:{agent_id}:hour", now - 3600, now
        )

        return {
            "per_minute": {"limit": cfg.requests_per_minute, "used": min_count,
                           "remaining": max(0, cfg.requests_per_minute - min_count)},
            "per_hour": {"limit": cfg.requests_per_hour, "used": hour_count,
                         "remaining": max(0, cfg.requests_per_hour - hour_count)}
        }
```

---

## 10. Component 7: Security Layer

Security is not optional in a platform. Every agent inherits the platform's
security controls automatically. Agent developers don't need to think about
them — they just work.

```python
# platform/services/security.py

import re
import json
import hashlib
from typing import Any
from dataclasses import dataclass

# PII patterns — extend for your jurisdiction (GDPR, CCPA, HIPAA)
PII_PATTERNS = [
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),           "***-**-****",   "SSN"),
    (re.compile(r"\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b"),
                                                       "****-****-****-****", "CREDIT_CARD"),
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
                                                       "[EMAIL]",       "EMAIL"),
    (re.compile(r"\b\d{3}[\s\-.]?\d{3}[\s\-.]?\d{4}\b"), "[PHONE]",   "PHONE"),
    (re.compile(r"\b(?:password|passwd|pwd|secret|api_key|token)\s*[:=]\s*\S+",
                re.IGNORECASE),                        "[REDACTED]",    "CREDENTIAL"),
]

# Tool call restrictions — tools in these categories require special permissions
RESTRICTED_TOOLS = {
    "financial.write":    ["transfer_funds", "issue_refund", "modify_credit_limit"],
    "pii.read":           ["get_customer_ssn", "get_full_credit_report"],
    "infrastructure":     ["deploy_service", "restart_server", "modify_firewall"],
    "admin":              ["create_user", "delete_user", "assign_role"],
}

# Prompt injection patterns — block these in user inputs and tool results
INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+a?n?\s+\w+", re.IGNORECASE),
    re.compile(r"(system|assistant)\s*:\s*", re.IGNORECASE),
    re.compile(r"<\s*(system|instruction)\s*>", re.IGNORECASE),
]


class SecurityLayer:
    """
    Platform security enforcement. Applied automatically to all agents.
    """

    def __init__(self, allowed_tool_categories: dict[str, list[str]] = None):
        self._permissions_store: dict[str, list[str]] = {}  # agent_id → permissions
        self._allowed_tool_categories = allowed_tool_categories or {}

    def register_agent_permissions(self, agent_id: str, permissions: list[str]):
        self._permissions_store[agent_id] = permissions

    async def validate_input(self, payload: dict, ctx: "AgentContext"):
        """
        Validate and sanitise incoming payload before it reaches the agent.
        Checks: payload size, injection attempts, PII in input.
        """
        payload_str = json.dumps(payload)

        # 1. Size check — prevent context stuffing attacks
        if len(payload_str) > 100_000:
            raise SecurityValidationError("Payload too large (max 100KB)")

        # 2. Injection detection in user-provided strings
        for val in self._extract_strings(payload):
            for pattern in INJECTION_PATTERNS:
                if pattern.search(val):
                    raise SecurityValidationError(
                        f"Potential prompt injection detected in input"
                    )

    async def validate_tool_call(
        self, tool_name: str,
        inputs: dict, ctx: "AgentContext"
    ):
        """
        Validate a tool call before execution.
        Checks: permission, input sanitisation, injection in tool inputs.
        """
        agent_permissions = self._permissions_store.get(ctx.agent_id, [])

        # Check if this tool requires special permissions
        for category, tools in RESTRICTED_TOOLS.items():
            if tool_name in tools and category not in agent_permissions:
                raise ToolSecurityError(
                    f"Tool '{tool_name}' requires permission '{category}' "
                    f"which agent '{ctx.agent_id}' does not have"
                )

        # Check tool inputs for injection attempts
        for val in self._extract_strings(inputs):
            for pattern in INJECTION_PATTERNS:
                if pattern.search(val):
                    raise ToolSecurityError(
                        f"Injection pattern detected in tool '{tool_name}' inputs"
                    )

    async def sanitise_output(self, result: dict, ctx: "AgentContext"):
        """
        Scan agent output for PII before returning to caller.
        Masks any PII found. Logs a warning when PII is detected.
        """
        result_str = json.dumps(result)
        masked, findings = self.mask_pii(result_str)

        if findings:
            import logging
            logging.warning(
                f"PII detected in agent output [{ctx.request_id}]: {findings}"
            )
            # Replace the output with masked version
            result.update(json.loads(masked))

    @staticmethod
    def mask_pii(text: str) -> tuple[str, list[str]]:
        """Mask all PII in a string. Returns (masked_text, list_of_pii_types_found)."""
        findings = []
        for pattern, replacement, pii_type in PII_PATTERNS:
            if pattern.search(text):
                text = pattern.sub(replacement, text)
                findings.append(pii_type)
        return text, findings

    @staticmethod
    def hash_pii(value: str) -> str:
        """One-way hash of a PII value for logging (enables correlation without exposure)."""
        return hashlib.sha256(value.encode()).hexdigest()[:16]

    @staticmethod
    def _extract_strings(obj: Any) -> list[str]:
        """Recursively extract all string values from a nested dict/list."""
        strings = []
        if isinstance(obj, str):
            strings.append(obj)
        elif isinstance(obj, dict):
            for v in obj.values():
                strings.extend(SecurityLayer._extract_strings(v))
        elif isinstance(obj, list):
            for item in obj:
                strings.extend(SecurityLayer._extract_strings(item))
        return strings
```

### C# — Security Layer

```csharp
// Platform/Security/SecurityLayer.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;

namespace AgentPlatform.Security
{
    public class SecurityLayer : ISecurityLayer
    {
        private static readonly (Regex Pattern, string Replacement, string PiiType)[] PiiPatterns =
        {
            (new Regex(@"\b\d{3}-\d{2}-\d{4}\b"), "***-**-****", "SSN"),
            (new Regex(@"\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b"),
             "****-****-****-****", "CREDIT_CARD"),
            (new Regex(@"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
             "[EMAIL]", "EMAIL"),
        };

        private static readonly Regex[] InjectionPatterns =
        {
            new Regex(@"ignore\s+(all\s+)?previous\s+instructions", RegexOptions.IgnoreCase),
            new Regex(@"you\s+are\s+now\s+a?n?\s+\w+", RegexOptions.IgnoreCase),
            new Regex(@"<\s*(system|instruction)\s*>", RegexOptions.IgnoreCase),
        };

        private readonly Dictionary<string, HashSet<string>> _agentPermissions = new();

        public void RegisterAgentPermissions(string agentId, IEnumerable<string> permissions) =>
            _agentPermissions[agentId] = new HashSet<string>(permissions);

        public Task ValidateInputAsync(
            Dictionary<string, object> payload,
            AgentContext ctx, CancellationToken ct = default)
        {
            var payloadStr = JsonSerializer.Serialize(payload);
            if (payloadStr.Length > 100_000)
                throw new SecurityValidationException("Payload too large");

            foreach (var str in ExtractStrings(payload))
                foreach (var pattern in InjectionPatterns)
                    if (pattern.IsMatch(str))
                        throw new SecurityValidationException(
                            "Prompt injection detected in input");

            return Task.CompletedTask;
        }

        public Task ValidateToolCallAsync(
            string toolName, Dictionary<string, object> inputs,
            AgentContext ctx, CancellationToken ct = default)
        {
            // Check restricted tool permissions
            var restrictedCategories = GetRequiredCategories(toolName);
            var agentPerms = _agentPermissions.GetValueOrDefault(ctx.AgentId, new());

            foreach (var category in restrictedCategories)
                if (!agentPerms.Contains(category))
                    throw new ToolSecurityException(toolName,
                        $"Requires permission '{category}'");

            // Injection check on tool inputs
            foreach (var str in ExtractStrings(inputs))
                foreach (var pattern in InjectionPatterns)
                    if (pattern.IsMatch(str))
                        throw new ToolSecurityException(toolName,
                            "Injection pattern in tool inputs");

            return Task.CompletedTask;
        }

        public Task SanitiseOutputAsync(
            AgentResult result, AgentContext ctx,
            CancellationToken ct = default)
        {
            if (result.Output == null) return Task.CompletedTask;

            var (masked, findings) = MaskPii(result.Output);
            if (findings.Any())
            {
                // Log warning — PII in output
                result.Output = masked;
            }
            return Task.CompletedTask;
        }

        public static (string Masked, List<string> Findings) MaskPii(string text)
        {
            var findings = new List<string>();
            foreach (var (pattern, replacement, piiType) in PiiPatterns)
            {
                if (pattern.IsMatch(text))
                {
                    text = pattern.Replace(text, replacement);
                    findings.Add(piiType);
                }
            }
            return (text, findings);
        }

        private static IEnumerable<string> GetRequiredCategories(string toolName)
        {
            var restricted = new Dictionary<string, string[]>
            {
                ["transfer_funds"] = new[] { "financial.write" },
                ["deploy_service"] = new[] { "infrastructure" },
                ["delete_user"] = new[] { "admin" },
            };
            return restricted.TryGetValue(toolName, out var cats) ? cats : Array.Empty<string>();
        }

        private static IEnumerable<string> ExtractStrings(object obj) =>
            obj switch
            {
                string s => new[] { s },
                Dictionary<string, object> d => d.Values.SelectMany(ExtractStrings),
                IEnumerable<object> e => e.SelectMany(ExtractStrings),
                _ => Array.Empty<string>()
            };
    }
}
```

---

## 11. Component 8: Validation Engine

The validation engine ensures data quality at the boundaries of every agent
invocation — input and output. It catches malformed data before it corrupts
downstream systems.

```python
# platform/services/validation.py

from typing import Any
import jsonschema
from dataclasses import dataclass, field
from pydantic import BaseModel, validator, ValidationError


@dataclass
class AgentSchema:
    """Schema definition for an agent's inputs and outputs."""
    agent_id: str
    input_schema: dict           # JSON Schema for input validation
    output_schema: dict          # JSON Schema for output validation
    output_model: type = None    # Optional Pydantic model for output


class ValidationEngine:
    """
    Central schema registry and validator.
    Agents register their schemas; the engine validates all I/O.
    """

    def __init__(self):
        self._schemas: dict[str, AgentSchema] = {}

    def register(self, schema: AgentSchema):
        self._schemas[schema.agent_id] = schema

    async def validate_input(self, agent_id: str, payload: dict):
        schema = self._schemas.get(agent_id)
        if not schema or not schema.input_schema:
            return  # No schema defined → pass through

        try:
            jsonschema.validate(payload, schema.input_schema)
        except jsonschema.ValidationError as e:
            raise InputValidationError(
                f"Agent {agent_id} input validation failed: "
                f"'{e.json_path}': {e.message}"
            )

    async def validate_output(self, agent_id: str, result: dict):
        schema = self._schemas.get(agent_id)
        if not schema:
            return

        if schema.output_schema:
            try:
                jsonschema.validate(result, schema.output_schema)
            except jsonschema.ValidationError as e:
                # Log but don't block — output validation is advisory
                import logging
                logging.warning(
                    f"Agent {agent_id} output schema violation: {e.message}"
                )

        if schema.output_model:
            try:
                schema.output_model(**result)
            except ValidationError as e:
                import logging
                logging.warning(f"Agent {agent_id} output model violation: {e}")


# Example: registering schemas for the fraud agent

class FraudAgentInput(BaseModel):
    transaction_id: str
    customer_id: str
    amount: float
    currency: str = "USD"

    @validator("amount")
    def amount_positive(cls, v):
        if v <= 0:
            raise ValueError("Amount must be positive")
        return v


class FraudAgentOutput(BaseModel):
    decision: str
    fraud_score: int
    confidence: float
    human_review_required: bool

    @validator("decision")
    def valid_decision(cls, v):
        if v not in ["APPROVE", "REVIEW", "BLOCK", "ESCALATE"]:
            raise ValueError(f"Invalid decision: {v}")
        return v

    @validator("fraud_score")
    def score_range(cls, v):
        if not 0 <= v <= 100:
            raise ValueError("Fraud score must be 0-100")
        return v


# Register in platform startup:
validation_engine.register(AgentSchema(
    agent_id="fraud-agent",
    input_schema={
        "type": "object",
        "required": ["transaction_id", "customer_id", "amount"],
        "properties": {
            "transaction_id": {"type": "string", "minLength": 1},
            "customer_id": {"type": "string", "minLength": 1},
            "amount": {"type": "number", "minimum": 0.01},
            "currency": {"type": "string", "pattern": "^[A-Z]{3}$"}
        }
    },
    output_schema={},
    output_model=FraudAgentOutput
))
```

---

*Continues in Part 3 →*
