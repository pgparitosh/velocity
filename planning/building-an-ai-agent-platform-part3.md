# Building an AI Agent Platform — Part 3
### Components 9–12: Audit · MCP · Orchestration · Scaling
### Plus: Building Agents on the Platform · Benefits · Alternatives · Best Practices · Mastery Check

---

## 12. Component 9: Audit & Observability

Every platform invocation creates an immutable audit record. This is not
optional — it is the foundation of debugging, compliance, cost attribution,
and continuous improvement.

### Python — Audit Logger

```python
# platform/services/audit.py

import json
import time
import hashlib
from dataclasses import dataclass, asdict
from typing import Any, Optional
import asyncpg          # PostgreSQL async driver
import boto3            # S3 for long-term immutable storage


@dataclass
class AuditRecord:
    # Immutable identity
    record_id: str
    schema_version: str = "1.0"

    # Request context
    request_id: str = ""
    parent_request_id: Optional[str] = None
    session_id: Optional[str] = None
    agent_id: str = ""
    agent_version: str = ""
    tenant_id: str = ""
    user_id: Optional[str] = None

    # Timing
    timestamp_utc: str = ""
    elapsed_ms: int = 0

    # Input (sanitised — no raw PII)
    input_type: str = ""
    input_hash: str = ""         # SHA-256 of original input for integrity

    # Execution summary
    tool_calls: list = None
    llm_calls: list = None
    iteration_count: int = 0

    # Output
    decision: Optional[str] = None
    status: str = ""
    confidence: Optional[float] = None
    human_review_required: bool = False

    # Cost
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0

    # Compliance
    regulatory_flags: list = None
    pii_detected_in_output: bool = False

    def __post_init__(self):
        if self.tool_calls is None:
            self.tool_calls = []
        if self.llm_calls is None:
            self.llm_calls = []
        if self.regulatory_flags is None:
            self.regulatory_flags = []


class AuditLogger:
    """
    Immutable audit log writer.

    Every write goes to:
    1. PostgreSQL (queryable, for recent records and compliance queries)
    2. S3 with Object Lock (WORM — tamper-proof, for long-term retention)

    NEVER delete or update audit records. Only append.
    """

    def __init__(self, pg_pool: asyncpg.Pool, s3_bucket: str):
        self._pg = pg_pool
        self._s3 = boto3.client("s3")
        self._s3_bucket = s3_bucket

    async def write(
        self, input_payload: dict, result: dict, ctx: "AgentContext"
    ):
        record = AuditRecord(
            record_id=f"AUD-{ctx.request_id}",
            request_id=ctx.request_id,
            parent_request_id=ctx.parent_request_id,
            session_id=ctx.session_id,
            agent_id=ctx.agent_id,
            agent_version=ctx.agent_version,
            tenant_id=ctx.tenant_id,
            user_id=ctx.user_id,
            timestamp_utc=time.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            elapsed_ms=ctx.elapsed_ms,
            input_type=input_payload.get("type", "unknown"),
            input_hash=hashlib.sha256(
                json.dumps(input_payload, sort_keys=True).encode()
            ).hexdigest(),
            tool_calls=ctx.tool_calls,
            llm_calls=ctx.llm_calls,
            iteration_count=ctx.iteration,
            decision=result.get("decision"),
            status=result.get("status", "ok"),
            confidence=result.get("confidence"),
            human_review_required=result.get("human_review_required", False),
            input_tokens=ctx.total_input_tokens,
            output_tokens=ctx.total_output_tokens,
            cost_usd=ctx.cost_usd,
        )

        # Write to PostgreSQL (async, non-blocking)
        await self._write_to_postgres(record)

        # Write to S3 (fire and forget — eventual durability)
        self._write_to_s3_async(record)

    async def _write_to_postgres(self, record: AuditRecord):
        sql = """
        INSERT INTO agent_audit_log (
            record_id, schema_version, request_id, parent_request_id,
            session_id, agent_id, agent_version, tenant_id, user_id,
            timestamp_utc, elapsed_ms, input_type, input_hash,
            tool_calls, llm_calls, iteration_count,
            decision, status, confidence, human_review_required,
            input_tokens, output_tokens, cost_usd, regulatory_flags
        ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,
                  $14::jsonb,$15::jsonb,$16,$17,$18,$19,$20,$21,$22,$23,$24::jsonb)
        ON CONFLICT (record_id) DO NOTHING
        """
        async with self._pg.acquire() as conn:
            await conn.execute(sql,
                record.record_id, record.schema_version, record.request_id,
                record.parent_request_id, record.session_id, record.agent_id,
                record.agent_version, record.tenant_id, record.user_id,
                record.timestamp_utc, record.elapsed_ms, record.input_type,
                record.input_hash,
                json.dumps(record.tool_calls), json.dumps(record.llm_calls),
                record.iteration_count, record.decision, record.status,
                record.confidence, record.human_review_required,
                record.input_tokens, record.output_tokens, record.cost_usd,
                json.dumps(record.regulatory_flags)
            )

    def _write_to_s3_async(self, record: AuditRecord):
        """Write to S3 with WORM (Object Lock) for tamper-proof long-term storage."""
        import threading
        def _write():
            key = f"audit/{record.agent_id}/{record.timestamp_utc[:10]}/{record.record_id}.json"
            self._s3.put_object(
                Bucket=self._s3_bucket,
                Key=key,
                Body=json.dumps(asdict(record)).encode(),
                ContentType="application/json",
                ObjectLockMode="COMPLIANCE",           # WORM — cannot delete or modify
                ObjectLockRetainUntilDate="2033-01-01T00:00:00Z"  # 7-year retention
            )
        threading.Thread(target=_write, daemon=True).start()

    # ── Compliance queries ────────────────────────────────────────────────────

    async def query_by_customer(
        self, customer_id: str, days: int = 90
    ) -> list[dict]:
        """All decisions affecting a customer — for GDPR right-of-explanation."""
        rows = await self._pg.fetch("""
            SELECT record_id, agent_id, timestamp_utc, decision,
                   confidence, human_review_required, cost_usd
            FROM agent_audit_log
            WHERE user_id = $1
              AND timestamp_utc > NOW() - INTERVAL '$2 days'
            ORDER BY timestamp_utc DESC
        """, customer_id, days)
        return [dict(r) for r in rows]

    async def query_human_review_queue(
        self, agent_id: str = None
    ) -> list[dict]:
        """All records flagged for human review that haven't been actioned."""
        sql = """
            SELECT a.record_id, a.agent_id, a.timestamp_utc,
                   a.decision, a.confidence, a.input_hash
            FROM agent_audit_log a
            LEFT JOIN human_reviews hr ON hr.audit_record_id = a.record_id
            WHERE a.human_review_required = true
              AND hr.reviewed_at IS NULL
        """
        params = []
        if agent_id:
            sql += " AND a.agent_id = $1"
            params.append(agent_id)
        sql += " ORDER BY a.timestamp_utc ASC"
        rows = await self._pg.fetch(sql, *params)
        return [dict(r) for r in rows]
```

### Observability Metrics — Prometheus + Grafana

```python
# platform/observability/metrics.py

from prometheus_client import Counter, Histogram, Gauge, Info

# ── Agent execution metrics ───────────────────────────────────────────────────

agent_requests = Counter(
    "platform_agent_requests_total",
    "Total agent invocations",
    ["agent_id", "tenant_id", "status"]
)

agent_latency = Histogram(
    "platform_agent_latency_seconds",
    "End-to-end agent latency",
    ["agent_id"],
    buckets=[0.5, 1, 2, 5, 10, 30, 60, 120]
)

agent_cost = Counter(
    "platform_agent_cost_usd_total",
    "Total LLM spend in USD",
    ["agent_id", "model", "tenant_id"]
)

agent_tool_calls = Counter(
    "platform_tool_calls_total",
    "Total tool calls",
    ["agent_id", "tool_name", "status"]
)

agent_tokens = Counter(
    "platform_tokens_total",
    "Total tokens consumed",
    ["agent_id", "model", "token_type"]  # token_type: input|output
)

# ── Quality metrics ───────────────────────────────────────────────────────────

agent_eval_score = Gauge(
    "platform_agent_eval_score",
    "Current eval suite pass rate",
    ["agent_id", "eval_suite_version"]
)

agent_human_review_rate = Gauge(
    "platform_agent_human_review_rate",
    "Fraction of decisions requiring human review",
    ["agent_id"]
)

agent_feedback_positive = Counter(
    "platform_agent_feedback_total",
    "Developer/user feedback on agent outputs",
    ["agent_id", "feedback_type"]  # feedback_type: positive|negative|wrong
)

# ── Infrastructure metrics ────────────────────────────────────────────────────

rate_limit_hits = Counter(
    "platform_rate_limit_hits_total",
    "Rate limit exceeded events",
    ["agent_id", "window"]
)

circuit_breaker_state = Gauge(
    "platform_circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=open, 2=half_open)",
    ["provider"]
)


class MetricsMiddleware:
    """Wrap AgentEngine to emit all metrics automatically."""

    def __init__(self, engine: "AgentEngine"):
        self._engine = engine

    async def run(self, agent, payload: dict, ctx: "AgentContext") -> dict:
        with agent_latency.labels(agent_id=ctx.agent_id).time():
            result = await self._engine.run(agent, payload, ctx)

        agent_requests.labels(
            agent_id=ctx.agent_id,
            tenant_id=ctx.tenant_id,
            status=result.get("status", "ok")
        ).inc()

        agent_cost.labels(
            agent_id=ctx.agent_id,
            model=ctx.llm_calls[-1]["model"] if ctx.llm_calls else "unknown",
            tenant_id=ctx.tenant_id
        ).inc(ctx.cost_usd)

        agent_tokens.labels(ctx.agent_id, "unknown", "input").inc(ctx.total_input_tokens)
        agent_tokens.labels(ctx.agent_id, "unknown", "output").inc(ctx.total_output_tokens)

        for tc in ctx.tool_calls:
            agent_tool_calls.labels(
                ctx.agent_id, tc["tool"], tc["status"]
            ).inc()

        return result
```

---

## 13. Component 10: MCP Layer (Model Context Protocol)

MCP is the emerging standard for connecting AI models to external tools
and data sources in a provider-agnostic way. Your platform should speak
MCP natively — this future-proofs your tool layer against LLM provider changes.

```
Without MCP:                         With MCP:
─────────────                        ────────────
Every tool is hardcoded for          Tools are MCP servers
Claude's tool-use format.            Any MCP-compatible LLM can use them
                                     (Claude, GPT-4, Gemini, local models)

Adding a new LLM provider:          Adding a new LLM provider:
  → Rewrite all tool schemas           → Just connect to existing MCP servers
  → Rewrite all tool executors
  → Update all agent classes
```

```python
# platform/mcp/broker.py

import json
import asyncio
from typing import Any, Optional
from dataclasses import dataclass
import httpx   # MCP servers communicate over HTTP/SSE


@dataclass
class MCPServer:
    name: str
    url: str                      # http://localhost:3001 or remote
    capabilities: list[str]       # tools, resources, prompts
    auth_token: Optional[str] = None


class MCPBroker:
    """
    Manages connections to MCP servers.
    Translates between platform's tool format and MCP protocol.
    """

    def __init__(self):
        self._servers: dict[str, MCPServer] = {}
        self._tool_map: dict[str, str] = {}    # tool_name → server_name

    def register_server(self, server: MCPServer):
        self._servers[server.name] = server

    async def discover_tools(self) -> list[dict]:
        """
        Connect to all registered MCP servers and fetch their tool lists.
        Returns tools in the platform's standard schema format.
        """
        all_tools = []
        for server in self._servers.values():
            try:
                tools = await self._fetch_server_tools(server)
                for tool in tools:
                    self._tool_map[tool["name"]] = server.name
                    all_tools.append(tool)
            except Exception as e:
                import logging
                logging.warning(f"MCP server {server.name} unreachable: {e}")
        return all_tools

    async def execute_tool(self, tool_name: str, inputs: dict) -> Any:
        """Route a tool call to the appropriate MCP server."""
        server_name = self._tool_map.get(tool_name)
        if not server_name:
            raise ToolNotFoundError(f"No MCP server found for tool: {tool_name}")

        server = self._servers[server_name]
        return await self._call_mcp_tool(server, tool_name, inputs)

    async def _fetch_server_tools(self, server: MCPServer) -> list[dict]:
        """Fetch tool list from an MCP server (MCP spec: GET /tools/list)."""
        headers = {}
        if server.auth_token:
            headers["Authorization"] = f"Bearer {server.auth_token}"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{server.url}/tools/list",
                headers=headers,
                timeout=10.0
            )
            response.raise_for_status()
            data = response.json()

        # Translate MCP format → platform format
        return [self._translate_mcp_tool(t) for t in data.get("tools", [])]

    async def _call_mcp_tool(
        self, server: MCPServer, name: str, inputs: dict
    ) -> Any:
        """Call a tool on an MCP server (MCP spec: POST /tools/call)."""
        headers = {"Content-Type": "application/json"}
        if server.auth_token:
            headers["Authorization"] = f"Bearer {server.auth_token}"

        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": name, "arguments": inputs},
            "id": 1
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{server.url}",
                json=payload,
                headers=headers,
                timeout=30.0
            )
            response.raise_for_status()
            result = response.json()

        if "error" in result:
            raise MCPToolError(f"MCP tool {name} error: {result['error']}")

        return result.get("result", {}).get("content", "")

    @staticmethod
    def _translate_mcp_tool(mcp_tool: dict) -> dict:
        """Convert MCP tool schema to platform/Anthropic tool schema."""
        return {
            "name": mcp_tool["name"],
            "description": mcp_tool.get("description", ""),
            "input_schema": mcp_tool.get("inputSchema", {
                "type": "object", "properties": {}
            })
        }


# ── Building your own MCP server (exposes your tools to any LLM) ─────────────

# platform/mcp/server.py
# A lightweight MCP server using FastAPI

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

mcp_app = FastAPI(title="Platform MCP Server")

class ToolCallRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: dict
    id: int = 1

@mcp_app.post("/")
async def handle_mcp_request(request: ToolCallRequest):
    if request.method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "result": {
                "tools": [
                    {
                        "name": "get_customer_profile",
                        "description": "Get customer profile by ID",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "customer_id": {"type": "string"}
                            },
                            "required": ["customer_id"]
                        }
                    }
                    # ... more tools
                ]
            },
            "id": request.id
        }

    if request.method == "tools/call":
        tool_name = request.params["name"]
        arguments = request.params["arguments"]
        result = await registry.execute(tool_name, arguments)
        return {
            "jsonrpc": "2.0",
            "result": {"content": str(result)},
            "id": request.id
        }

    raise HTTPException(status_code=400, detail=f"Unknown method: {request.method}")
```

---

## 14. Component 11: Orchestration Engine

Orchestration handles multi-agent workflows: parallel execution, sequential
pipelines, conditional branching, and handoffs between agents.

```python
# platform/orchestration/engine.py

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from enum import Enum


class NodeType(Enum):
    AGENT = "agent"
    PARALLEL = "parallel"
    CONDITION = "condition"
    TRANSFORM = "transform"
    HUMAN_GATE = "human_gate"


@dataclass
class WorkflowNode:
    node_id: str
    node_type: NodeType
    agent_id: Optional[str] = None        # For AGENT nodes
    children: list["WorkflowNode"] = field(default_factory=list)
    condition: Optional[Callable] = None  # For CONDITION nodes
    transform: Optional[Callable] = None  # For TRANSFORM nodes
    timeout_s: int = 120


@dataclass
class WorkflowResult:
    workflow_id: str
    status: str
    outputs: dict[str, Any] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)
    total_cost_usd: float = 0.0
    elapsed_ms: int = 0


class OrchestrationEngine:
    """
    Executes multi-agent workflows defined as a DAG (directed acyclic graph).
    """

    def __init__(self, agent_engine: "AgentEngine", agent_registry: "AgentRegistry"):
        self._engine = agent_engine
        self._agents = agent_registry

    async def run_workflow(
        self,
        root_node: WorkflowNode,
        initial_payload: dict,
        ctx: "AgentContext"
    ) -> WorkflowResult:
        workflow_id = str(uuid.uuid4())
        outputs = {}
        errors = {}
        total_cost = 0.0

        async def execute_node(node: WorkflowNode, payload: dict) -> Any:
            nonlocal total_cost

            if node.node_type == NodeType.AGENT:
                agent = self._agents.get(node.agent_id)
                node_ctx = self._child_context(ctx, node.agent_id)
                result = await self._engine.run(agent, payload, node_ctx)
                total_cost += node_ctx.cost_usd
                outputs[node.node_id] = result
                return result

            elif node.node_type == NodeType.PARALLEL:
                tasks = [execute_node(child, payload) for child in node.children]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for child, result in zip(node.children, results):
                    if isinstance(result, Exception):
                        errors[child.node_id] = str(result)
                    else:
                        outputs[child.node_id] = result
                return results

            elif node.node_type == NodeType.CONDITION:
                branch = node.condition(payload, outputs)
                if branch < len(node.children):
                    return await execute_node(node.children[branch], payload)

            elif node.node_type == NodeType.TRANSFORM:
                return node.transform(payload, outputs)

            elif node.node_type == NodeType.HUMAN_GATE:
                # Pause workflow — wait for human approval
                gate_result = await self._wait_for_human_approval(
                    workflow_id, node.node_id, payload, outputs
                )
                if not gate_result["approved"]:
                    raise WorkflowRejectedError(
                        f"Human rejected at gate {node.node_id}: {gate_result['reason']}"
                    )
                return gate_result

        import time
        t0 = time.monotonic()
        try:
            await execute_node(root_node, initial_payload)
            status = "completed"
        except WorkflowRejectedError as e:
            status = "rejected"
            errors["workflow"] = str(e)
        except Exception as e:
            status = "failed"
            errors["workflow"] = str(e)

        return WorkflowResult(
            workflow_id=workflow_id,
            status=status,
            outputs=outputs,
            errors=errors,
            total_cost_usd=total_cost,
            elapsed_ms=int((time.monotonic() - t0) * 1000)
        )

    def _child_context(self, parent: "AgentContext", agent_id: str) -> "AgentContext":
        from platform.core.engine import AgentContext
        return AgentContext(
            parent_request_id=parent.request_id,
            agent_id=agent_id,
            tenant_id=parent.tenant_id,
            user_id=parent.user_id,
            session_id=parent.session_id,
            tags=parent.tags
        )

    async def _wait_for_human_approval(
        self, workflow_id: str, gate_id: str,
        payload: dict, outputs: dict
    ) -> dict:
        """
        Creates a human review task and polls for completion.
        In production: webhook or long-poll. Here simplified to polling.
        """
        task_id = await self._create_review_task(workflow_id, gate_id, outputs)

        for _ in range(720):  # Poll for up to 1 hour
            await asyncio.sleep(5)
            status = await self._check_review_task(task_id)
            if status["completed"]:
                return status
        raise WorkflowTimeoutError(f"Human gate {gate_id} timed out after 1 hour")


# ── Example: Loan Application Workflow ───────────────────────────────────────

def build_loan_workflow() -> WorkflowNode:
    """
    Workflow:
    1. KYC Check (parallel with) Credit Check
    2. If both pass → Underwriting Agent
    3. Human Gate (for loans > $50K)
    4. Notification Agent
    """
    kyc_node = WorkflowNode("kyc", NodeType.AGENT, agent_id="kyc-agent")
    credit_node = WorkflowNode("credit", NodeType.AGENT, agent_id="credit-agent")

    parallel_checks = WorkflowNode(
        "parallel_checks", NodeType.PARALLEL,
        children=[kyc_node, credit_node]
    )

    underwriting = WorkflowNode("underwriting", NodeType.AGENT,
                                agent_id="underwriting-agent")

    human_gate = WorkflowNode(
        "large_loan_review", NodeType.HUMAN_GATE,
        condition=lambda p, o: p.get("amount", 0) > 50_000
    )

    notify = WorkflowNode("notify", NodeType.AGENT, agent_id="notification-agent")

    # Chain: parallel_checks → underwriting → (gate if large) → notify
    parallel_checks.children = [underwriting]
    underwriting.children = [human_gate, notify]

    return parallel_checks


# Running the workflow:
async def process_loan_application(application: dict, ctx: "AgentContext"):
    workflow = build_loan_workflow()
    result = await orchestration_engine.run_workflow(
        workflow, application, ctx
    )
    return result
```

---

## 15. Component 12: Scaling & Deployment

### Kubernetes Deployment — Complete Spec

```yaml
# k8s/platform/deployment.yaml

apiVersion: apps/v1
kind: Deployment
metadata:
  name: agent-platform
  namespace: ai-agents
  labels:
    app: agent-platform
    version: "1.2.0"
spec:
  replicas: 3
  selector:
    matchLabels:
      app: agent-platform
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0       # Zero-downtime deployments
  template:
    metadata:
      labels:
        app: agent-platform
    spec:
      containers:
      - name: platform
        image: your-registry/agent-platform:1.2.0
        ports:
        - containerPort: 8080
        env:
        - name: ANTHROPIC_API_KEY
          valueFrom:
            secretKeyRef:
              name: llm-secrets
              key: anthropic-key
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secrets
              key: url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: redis-secrets
              key: url
        resources:
          requests:
            cpu: "500m"
            memory: "512Mi"
          limits:
            cpu: "2000m"
            memory: "2Gi"
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: agent-platform-hpa
  namespace: ai-agents
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: agent-platform
  minReplicas: 3
  maxReplicas: 30
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 65
  - type: External
    external:
      metric:
        name: agent_queue_depth
      target:
        type: AverageValue
        averageValue: "100"     # Scale when queue > 100 items per pod
```

### FastAPI Platform API — The Developer-Facing Interface

```python
# platform/api/app.py

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Any
import uuid

from platform.core.engine import AgentEngine, AgentContext
from platform.deps import get_engine, get_agent_registry, get_auth

app = FastAPI(
    title="AI Agent Platform API",
    description="Platform API for building and running AI agents",
    version="1.2.0"
)

app.add_middleware(CORSMiddleware, allow_origins=["*"])


class RunAgentRequest(BaseModel):
    agent_id: str
    payload: dict[str, Any]
    session_id: Optional[str] = None
    tags: dict[str, str] = {}
    async_mode: bool = False       # True: return immediately, poll for result


class RunAgentResponse(BaseModel):
    request_id: str
    status: str
    result: Optional[dict] = None  # None if async_mode=True
    cost_usd: float
    elapsed_ms: int


@app.post("/v1/agents/run", response_model=RunAgentResponse)
async def run_agent(
    request: RunAgentRequest,
    background_tasks: BackgroundTasks,
    auth = Depends(get_auth),
    engine: AgentEngine = Depends(get_engine),
    registry = Depends(get_agent_registry)
):
    """
    Run an agent. This is the primary platform endpoint.

    sync mode (async_mode=false): waits for completion, returns result
    async mode (async_mode=true): returns immediately, poll /v1/agents/{id}/status
    """
    agent = registry.get(request.agent_id)
    if not agent:
        raise HTTPException(404, f"Agent '{request.agent_id}' not registered")

    ctx = AgentContext(
        agent_id=request.agent_id,
        agent_version=agent.AGENT_VERSION,
        tenant_id=auth.tenant_id,
        user_id=auth.user_id,
        session_id=request.session_id or str(uuid.uuid4()),
        tags=request.tags
    )

    if request.async_mode:
        background_tasks.add_task(engine.run, agent, request.payload, ctx)
        return RunAgentResponse(
            request_id=ctx.request_id,
            status="queued",
            cost_usd=0,
            elapsed_ms=0
        )

    result = await engine.run(agent, request.payload, ctx)
    return RunAgentResponse(
        request_id=ctx.request_id,
        status=result.get("status", "ok"),
        result=result,
        cost_usd=ctx.cost_usd,
        elapsed_ms=ctx.elapsed_ms
    )


@app.get("/v1/agents/{request_id}/status")
async def get_agent_status(request_id: str, auth = Depends(get_auth)):
    """Poll for async agent result."""
    result = await result_store.get(request_id)
    if not result:
        return {"status": "running", "request_id": request_id}
    return {"status": "completed", "request_id": request_id, "result": result}


@app.get("/v1/platform/costs")
async def get_cost_report(
    days: int = 30,
    auth = Depends(get_auth),
    cost_manager = Depends(lambda: get_cost_manager())
):
    """Get cost breakdown for this tenant."""
    return await cost_manager.get_cost_report(auth.tenant_id, days)


@app.get("/health/live")
async def liveness():
    return {"status": "alive"}


@app.get("/health/ready")
async def readiness(engine = Depends(get_engine)):
    """Check all platform dependencies."""
    checks = {
        "llm_api": await engine._llm.health_check(),
        "database": await engine._audit.health_check(),
        "cache": await engine._memory.health_check(),
    }
    all_ok = all(v["ok"] for v in checks.values())
    return {"status": "ready" if all_ok else "degraded", "checks": checks}
```

---

## 16. Building Agents on Top of the Platform

This is the payoff section. With the platform running, building a new agent
takes less than a day. Here is the complete developer experience.

### The Developer's Workflow — 5 Steps to a New Agent

```
Step 1: Define the agent config (5 minutes)
Step 2: Register the agent (10 minutes)
Step 3: Write domain tools (1-4 hours)
Step 4: Write the system prompt (2-4 hours)
Step 5: Write eval tests (2-4 hours)
Total: ~1 day for a fully production-ready agent
```

### Step 1: Agent Configuration File

```yaml
# agents/expense-approver/agent_config.yaml

agent_id: expense-approver
version: "1.0.0"
owner_team: finance-platform
description: "Reviews and approves employee expense claims based on policy"

# LLM configuration
model: claude-sonnet-4-6
max_iterations: 15
max_output_tokens: 1024

# Cost and rate limits
budget:
  daily_limit_usd: 50.0
  monthly_limit_usd: 800.0
  per_request_limit_usd: 0.30
  alert_threshold_pct: 0.80

rate_limits:
  requests_per_minute: 30
  requests_per_hour: 200

# Permissions — which tool categories this agent can use
permissions:
  - expense.read
  - expense.approve
  - expense.reject
  - employee.read
  - notification.send

# Prompt library reference
system_prompt: expense-approver-v1@v1.0.0

# Validation schemas
input_schema:
  type: object
  required: [expense_id, submitter_id]
  properties:
    expense_id: {type: string}
    submitter_id: {type: string}
    amount: {type: number, minimum: 0.01}
    category: {type: string}

output_schema:
  type: object
  required: [decision, reason]
  properties:
    decision: {type: string, enum: [APPROVE, REJECT, ESCALATE]}
    reason: {type: string}
    confidence: {type: number, minimum: 0, maximum: 1}

# Memory configuration
memory:
  short_term_ttl_s: 3600
  long_term_enabled: false      # This agent doesn't need long-term memory
  episodic_enabled: true        # Track past approvals for same submitter

# Deployment
scaling:
  min_replicas: 1
  max_replicas: 5
  scale_on_queue_depth: 50
```

### Step 2: Register the Agent

```python
# agents/expense-approver/register.py

from platform.sdk import AgentBuilder, register_agent

# AgentBuilder reads agent_config.yaml and wires everything up
@register_agent("agents/expense-approver/agent_config.yaml")
class ExpenseApproverAgent(AgentBase):

    AGENT_ID = "expense-approver"
    AGENT_VERSION = "1.0.0"

    def system_prompt(self) -> str:
        # Reference the prompt library — resolved at runtime
        return "expense-approver-v1"

    def tools(self) -> list[dict]:
        # Get schemas for all tools with the declared permissions
        return self._tool_registry.get_schemas_for_agent(self._permissions)

    async def execute_tool(self, name: str, inputs: dict, ctx: AgentContext) -> Any:
        return await self._tool_registry.execute(name, inputs, ctx, self._permissions)
```

That is the complete agent class. Everything else is handled by the platform.

### Step 3: Domain Tools

```python
# agents/expense-approver/tools.py

from platform.tools.registry import registry

@registry.register(
    name="get_expense_claim",
    description="Get full details of an expense claim including receipts and policy category",
    version="1.0.0",
    owner_team="finance-platform",
    tags=["expense", "read"],
    requires_permissions=["expense.read"],
    timeout_seconds=5
)
async def get_expense_claim(expense_id: str) -> dict:
    return await expense_db.get_claim(expense_id)


@registry.register(
    name="get_expense_policy",
    description="Get the expense policy rules for a given category and employee level",
    version="1.0.0",
    owner_team="finance-platform",
    tags=["expense", "read"],
    requires_permissions=["expense.read"],
    timeout_seconds=3
)
async def get_expense_policy(category: str, employee_level: str) -> dict:
    return await policy_db.get(category, employee_level)


@registry.register(
    name="get_employee_expense_history",
    description="Get an employee's past expense submissions and approval rate",
    version="1.0.0",
    owner_team="finance-platform",
    tags=["expense", "read"],
    requires_permissions=["expense.read", "employee.read"],
    timeout_seconds=5
)
async def get_employee_expense_history(
    submitter_id: str, months: int = 6
) -> dict:
    return await expense_db.get_history(submitter_id, months)


@registry.register(
    name="approve_expense",
    description="Approve an expense claim and trigger reimbursement",
    version="1.0.0",
    owner_team="finance-platform",
    tags=["expense", "write"],
    requires_permissions=["expense.approve"],
    timeout_seconds=10,
    retryable=False      # Approvals are not retried
)
async def approve_expense(expense_id: str, approved_amount: float, note: str) -> dict:
    return await expense_db.approve(expense_id, approved_amount, note)


@registry.register(
    name="reject_expense",
    description="Reject an expense claim with a reason",
    version="1.0.0",
    owner_team="finance-platform",
    tags=["expense", "write"],
    requires_permissions=["expense.reject"],
    timeout_seconds=10,
    retryable=False
)
async def reject_expense(expense_id: str, reason: str) -> dict:
    return await expense_db.reject(expense_id, reason)
```

### Step 4: System Prompt (Stored in Library)

```yaml
# prompts/expense-approver-v1/v1.0.0.yaml

prompt_id: expense-approver-v1
version: "1.0.0"
author: "finance-platform-team"
changelog: "Initial version"
eval_score: 0.92
variables: []

content: |
  ## Role
  You are an expense approval specialist at a mid-size technology company.
  You review employee expense claims fairly, consistently, and in accordance
  with the company expense policy.

  ## Approval Process
  1. Retrieve the full expense claim details
  2. Retrieve the relevant expense policy for this category and employee level
  3. Check the employee's recent expense history for patterns
  4. Apply the policy rules
  5. Make a decision with a clear, specific reason

  ## Policy Rules
  - Meals (per person): up to $75 for client meals, $30 for internal
  - Travel: economy class required for flights under 5 hours
  - Software: must have prior manager approval for > $200
  - Hardware: requires IT pre-approval
  - No cash purchases over $50 (must use company card)

  ## Decision Rules
  APPROVE:  Expense complies with policy. Approve the actual amount.
  REJECT:   Expense violates policy. Reject with specific policy section cited.
  ESCALATE: Expense is borderline, unusual, or > $2,000. Escalate to manager.

  ## Output Format
  {
    "decision": "APPROVE" | "REJECT" | "ESCALATE",
    "approved_amount": null or number,
    "reason": "Specific reason citing the policy section",
    "policy_sections_applied": ["list"],
    "confidence": 0.0-1.0,
    "human_review_required": true | false
  }
```

### Step 5: Eval Tests

```python
# agents/expense-approver/evals.py

from platform.evals import EvalSuite, EvalCase
from platform.evals.runner import run_evals

EXPENSE_EVALS = EvalSuite(
    agent_id="expense-approver",
    cases=[
        EvalCase(
            id="eval_001",
            description="$65 client dinner should be approved",
            input={"expense_id": "EXP-001", "submitter_id": "EMP-100"},
            mocks={
                "get_expense_claim": lambda **_: {
                    "id": "EXP-001", "category": "meals_client",
                    "amount": 65.00, "attendees": 2,
                    "receipt_attached": True
                },
                "get_expense_policy": lambda **_: {
                    "category": "meals_client", "per_person_limit": 75.00
                },
                "get_employee_expense_history": lambda **_: {
                    "total_90_days": 450.0, "approval_rate": 0.95
                }
            },
            assertions=[
                lambda r: r["decision"] == "APPROVE",
                lambda r: r["confidence"] >= 0.85,
                lambda r: r["human_review_required"] == False
            ]
        ),

        EvalCase(
            id="eval_002",
            description="$150 cash purchase should be rejected (> $50 cash limit)",
            input={"expense_id": "EXP-002", "submitter_id": "EMP-200"},
            mocks={
                "get_expense_claim": lambda **_: {
                    "id": "EXP-002", "category": "supplies",
                    "amount": 150.00, "payment_method": "cash",
                    "receipt_attached": True
                },
                "get_expense_policy": lambda **_: {
                    "max_cash_purchase": 50.00
                },
                "get_employee_expense_history": lambda **_: {"total_90_days": 200.0}
            },
            assertions=[
                lambda r: r["decision"] == "REJECT",
                lambda r: "cash" in r["reason"].lower() or "50" in r["reason"]
            ]
        ),

        EvalCase(
            id="eval_003",
            description="$3,500 expense should escalate to human",
            input={"expense_id": "EXP-003", "submitter_id": "EMP-300"},
            mocks={
                "get_expense_claim": lambda **_: {
                    "id": "EXP-003", "category": "hardware",
                    "amount": 3500.00, "it_approval": None
                },
                "get_expense_policy": lambda **_: {
                    "hardware_requires_it_approval": True
                },
                "get_employee_expense_history": lambda **_: {"total_90_days": 100.0}
            },
            assertions=[
                lambda r: r["decision"] == "ESCALATE",
                lambda r: r["human_review_required"] == True
            ]
        )
    ]
)

# Run in CI:
if __name__ == "__main__":
    results = run_evals(EXPENSE_EVALS, use_mocks=True)
    assert results.pass_rate >= 0.90, f"Eval pass rate {results.pass_rate:.0%} below threshold"
    print(f"✅ Evals passed: {results.pass_rate:.0%} ({results.passed}/{results.total})")
```

---

## 17. Benefits, Alternatives & Trade-offs

### Benefits (Quantified)

| Benefit | Without Platform | With Platform | Gain |
|---------|-----------------|---------------|------|
| Time to build new agent | 4-6 weeks | 1-3 days | 10-20x |
| Bug fix propagation | N separate PRs | 1 PR | N-1 PRs saved |
| Compliance audit readiness | Weeks of work | Run a query | Weeks saved |
| LLM cost visibility | Unknown | Real-time per-agent | - |
| Security coverage | Inconsistent | 100% of agents | - |
| New developer ramp-up | 2-3 weeks | 2-3 days | 5x |

---

### Alternatives to Building Your Own Platform

```
Option A: LangChain / LangGraph
  Pros:  Mature, large community, Python-first, many integrations
  Cons:  Abstraction leaks, hard to debug, not multi-tenant by default,
         changing APIs, heavy dependency footprint
  When:  Prototyping, small team, Python-only

Option B: Microsoft Semantic Kernel
  Pros:  C# and Python, enterprise-friendly, plugin ecosystem
  Cons:  Microsoft ecosystem assumption, less flexible
  When:  .NET-heavy organisations, Azure-centric deployments

Option C: AWS Bedrock Agents
  Pros:  Fully managed, scales automatically, integrates with AWS
  Cons:  Lock-in to AWS, limited customisation, expensive at scale
  When:  AWS-first organisations, want zero infra to manage

Option D: Build Your Own (this guide)
  Pros:  Full control, multi-provider, custom security/compliance,
         exact fit to your requirements, no vendor lock-in
  Cons:  Engineering investment, maintenance burden
  When:  >5 agents planned, compliance requirements, multi-tenant,
         need fine-grained cost and security control

Verdict: Use LangChain for prototypes. Build your own for production
         at scale if you have > 5 agents and compliance requirements.
```

---

## 18. Best Practices

### BP1: Contract-First Development

Define the platform contracts (interfaces, schemas, base classes) before
writing any implementation. Teams can build agents against mock implementations
while the platform is being built.

```
Week 1: Define interfaces (IAgent, IToolRegistry, IAuditLogger, etc.)
Week 2-4: Teams build agents against mock implementations
Week 4-8: Platform team implements real backends
Week 8: Swap mock → real. Agents work without modification.
```

### BP2: The Platform SDK Hides Complexity

Expose a simple, opinionated SDK. Platform internals are irrelevant to agent builders.

```python
# This should be the ENTIRE platform SDK a developer needs to know:

from platform.sdk import AgentBase, tool, register_agent, AgentContext

# 1. Decorate your tools
@tool("get_order", "Get order details by ID", requires=["order.read"])
async def get_order(order_id: str) -> dict: ...

# 2. Extend AgentBase
class MyAgent(AgentBase):
    AGENT_ID = "my-agent"

    def system_prompt(self): return "my-agent-prompt"
    def tools(self): return self.registry_tools()
    async def execute_tool(self, name, inputs, ctx): return await self.run_tool(name, inputs, ctx)

# 3. Register it
register_agent(MyAgent, config_path="agent_config.yaml")

# Everything else (cost, rate limiting, audit, security, memory, retry)
# is handled by the platform transparently.
```

### BP3: Treat Prompts Like Code

```
✓ Stored in version control (git)
✓ Reviewed via pull request
✓ Tagged with semantic version
✓ Tested with eval suite before promotion to 'latest'
✓ Rollback in < 60 seconds (point latest symlink to previous version)
✓ A/B tested for major changes (10% canary traffic for 24h before full rollout)
✓ Changelog maintained (why the prompt changed, not just what changed)
```

### BP4: Eval-Gated Deployments

```
CI/CD pipeline for any agent change:

code change → unit tests → eval suite → staging deploy → prod deploy
                              ↓
              if pass rate < 90%: BLOCK deployment
              if pass rate drops > 5% from baseline: BLOCK deployment
              if critical category fails: BLOCK regardless of overall %
```

### BP5: Cost Attribution is Product Requirement, Not Engineering Nice-to-Have

Every LLM call must be attributed to: agent + tenant + feature.
Without this, you cannot make intelligent cost optimisation decisions.

```python
# Every request carries its feature tag
ctx = AgentContext(
    agent_id="pr-review",
    tenant_id="eng-team-infra",
    tags={
        "feature": "security-scan",     # for cost by feature
        "pr_size": "large",             # for cost by PR size
        "triggered_by": "push"          # for cost by trigger type
    }
)

# Monthly cost report then shows:
# agent: pr-review
#   feature: security-scan  →  $340/month
#   feature: style-check    →  $120/month
#   feature: test-coverage  →  $180/month
# → Decision: security scan is worth it; style check ($120) vs. linter ($0) → switch to linter
```

---

## 19. Quick-Reference Cheat Sheet

### Platform Component Checklist

```
FOUNDATION
[ ] Core execution engine with shared agentic loop
[ ] AgentBase interface (3 methods to implement)
[ ] LLM Gateway with retry + circuit breaker + model routing
[ ] Dependency injection container (all platform services wired at startup)

TOOL LAYER
[ ] Tool Registry with decorator-based registration
[ ] Auto-schema generation from type hints
[ ] Permission-gated tool access (RBAC)
[ ] MCP server for external LLM compatibility

KNOWLEDGE
[ ] Prompt Library with versioning and A/B testing
[ ] Short-term memory (Redis, per-session)
[ ] Long-term memory (vector store, semantic search)
[ ] Episodic memory (past interaction outcomes)

SAFETY & COMPLIANCE
[ ] Rate limiter (platform + per-agent + per-tenant)
[ ] Budget manager (daily + monthly + per-request limits)
[ ] Security layer (PII masking, injection detection, RBAC)
[ ] Validation engine (input + output schema validation)
[ ] Immutable audit log (PostgreSQL + S3 WORM)

OBSERVABILITY
[ ] Prometheus metrics (latency, cost, tokens, decisions)
[ ] Grafana dashboards (per-agent, per-tenant, platform-wide)
[ ] Eval dashboard (accuracy over time)
[ ] Cost attribution reports

ORCHESTRATION & SCALE
[ ] Multi-agent workflow engine (DAG execution)
[ ] Human-in-the-loop gates
[ ] Kubernetes deployment specs (HPA auto-scaling)
[ ] Platform REST API (/v1/agents/run, /v1/costs, /health)
[ ] Developer SDK (AgentBase, @tool decorator, register_agent)
```

### Technology Stack Reference

| Component | Python Option | C# Option | Cloud-Managed Option |
|-----------|--------------|-----------|---------------------|
| LLM Client | anthropic SDK | Anthropic .NET | AWS Bedrock |
| Short-term memory | Redis (aioredis) | StackExchange.Redis | ElastiCache |
| Long-term memory | Qdrant / pgvector | Qdrant .NET | Pinecone |
| Audit DB | PostgreSQL (asyncpg) | Npgsql / EF Core | RDS PostgreSQL |
| Rate limiter | Redis sorted set | Same | Same |
| Prompt storage | S3 + Redis cache | Same | S3 + ElastiCache |
| Metrics | Prometheus + Grafana | Same | CloudWatch |
| API framework | FastAPI | ASP.NET Core | AWS API Gateway |
| Task queue | Celery + Redis | Hangfire | SQS |
| Container orchestration | Kubernetes | Same | EKS / AKS / GKE |
| Secret management | HashiCorp Vault | Same | AWS Secrets Manager |

---

## 20. Mastery Check

**Question 1 (Beginner):**
Why should you build a platform instead of letting each team build their own agent independently? Give 3 concrete engineering reasons.

> **Answer:**
> (1) **Bug propagation:** A bug in retry logic (e.g., not handling HTTP 429 correctly) exists in every independently-built agent. With a platform, fix it once — all agents get the fix on next deploy.
>
> (2) **Security consistency:** Without a platform, teams forget PII masking, injection detection, or permission checks. On the platform, these are applied automatically to 100% of agents — the developer cannot accidentally skip them.
>
> (3) **Time to ship:** The first agent might take 4 weeks to build (including retry, cost tracking, audit logging, rate limiting). The second agent on a platform takes 1 day. The platform investment pays back after ~3 agents.

---

**Question 2 (Intermediate):**
Explain the difference between short-term, long-term, and episodic memory. Give a concrete use case for each in a customer support agent.

> **Answer:**
> **Short-term (conversation):** What was said earlier in this conversation. Use case: customer says "my order is delayed" in turn 1, then asks "can I get a refund?" in turn 3. Short-term memory ensures the agent knows which order they're talking about without the customer repeating it.
>
> **Long-term (semantic):** Facts remembered across all conversations, retrieved by semantic search. Use case: a previous conversation established "customer X prefers SMS notifications, not email." This preference is retrieved automatically the next time this customer contacts support, without them needing to state it again.
>
> **Episodic:** Past interaction outcomes. Use case: "this customer has contacted us 4 times about the same issue, all resolved by issuing a refund." The agent can see this pattern and proactively offer the refund rather than going through the full troubleshooting loop again.

---

**Question 3 (Advanced):**
Your platform's circuit breaker opens (LLM API is down). You have 500 queued agent requests. What is your degraded operation strategy? How do you recover?

> **Answer:**
> **During outage (circuit open):**
>
> *Tiered degradation:*
> - Low-stakes agents (FAQ answers, status checks): return cached responses or pre-computed answers from the last 24h.
> - Medium-stakes (PR reviews, CI diagnosis): queue requests; process when circuit closes.
> - High-stakes (fraud blocks, incident response): route to rule-based fallback engine for critical decisions. Log every fallback for human review.
>
> *User-facing:* Return 503 with `Retry-After: 60` header. Do NOT silently fail or return wrong answers.
>
> **Recovery:**
> 1. Circuit enters HALF_OPEN after `recovery_timeout_s` (60s default).
> 2. One test request is allowed through.
> 3. If successful → CLOSED: drain queue in rate-limited bursts (not all 500 at once — that would cause another 429 storm).
> 4. If failed → back to OPEN for another 60s.
>
> *Queue draining:* Process at 80% of normal rate limit for the first 10 minutes to clear backlog without triggering new throttling.

---

**Question 4 (Expert):**
Design the multi-tenancy model for a platform that serves 20 internal teams. Each team should be able to build agents, see only their own costs and audit logs, and not be able to noisy-neighbour each other's LLM quota. What data model, isolation strategy, and API design do you use?

> **Answer:**
> **Tenant model:**
> ```
> Tenant = a team (e.g., "fraud-team", "devops-team")
> Each tenant has: tenant_id, rate_limit_config, budget_config, allowed_agents
> ```
>
> **Data isolation:**
> - Audit logs: `tenant_id` column, Row Level Security (RLS) in PostgreSQL ensures queries can only see their own tenant's records. No shared query results.
> - Cost tracking: Redis keys include `tenant_id` — `cost:daily:{agent_id}:{tenant_id}:{date}`.
> - Memory: Short-term keys scoped to `mem:short:{tenant_id}:{session_id}`. Vector store namespaced by tenant.
>
> **Rate limit isolation (noisy neighbour prevention):**
> - Three-level rate limiting: platform-wide (total LLM quota) → per-tenant (team's allocation) → per-agent.
> - Platform-wide limit = sum of all tenant limits × 0.8 (safety headroom).
> - Tenant A exhausting their quota does NOT affect Tenant B's quota — separate Redis keys.
>
> **API design:**
> - JWT token contains `tenant_id` claim — all API calls are automatically scoped.
> - `/v1/agents/run` — runs the agent under the caller's tenant context.
> - `/v1/platform/costs` — returns ONLY the calling tenant's costs.
> - `/v1/platform/audit` — returns ONLY the calling tenant's audit logs.
> - Platform admin endpoint (separate auth): `/internal/admin/all-tenants/costs` — accessible only by platform team.

---

**Question 5 (Expert):**
A developer on your platform is building an agent that needs to call 3 external APIs. One of these APIs is slow (avg 2s), one is expensive (each call costs $0.10), and one is unreliable (5% failure rate). Design the tool implementation strategy for each.

> **Answer:**
> **Slow API (avg 2s):**
> - Implement result caching in Redis: TTL matched to data freshness requirement (e.g., stock price: 30s TTL; company address: 24h TTL).
> - For calls that CAN'T be cached: configure the orchestration engine to call this tool in parallel with other tools, not sequentially. `asyncio.gather()` makes parallel calls free.
> - Set `timeout_seconds=5` in tool registration — fail fast rather than blocking the agent loop for 20+ seconds.
> - Pre-warm cache during off-peak hours for predictable queries.
>
> **Expensive API ($0.10/call):**
> - Aggressive caching: SHA-256 hash of inputs → cached result. Any identical call hits cache.
> - Budget guard: register a `pre_tool_call` hook that checks if the agent's remaining budget can afford this call. Decline if it would push over the per-request limit.
> - Batching: if the agent might call this tool 3 times with similar inputs, add a `batch_call` variant that fetches multiple results in one API call.
> - Report in cost dashboard separately: tag these calls with `tool_type: expensive_external` for cost attribution.
>
> **Unreliable API (5% failure rate):**
> - Mark as `retryable=True` in tool registration.
> - The platform's tool executor applies exponential backoff: retry up to 3 times (5% failure → 0.25% failure after 3 attempts with backoff).
> - Add a fallback: if all 3 retries fail, return a structured `{"status": "unavailable", "cached_result": <last_known_value>}` — the agent can reason about this gracefully rather than crashing.
> - Monitor failure rate with a Prometheus counter; alert if rate > 10% (may indicate an API outage worth investigating).

---

*End of Document — Part 3 of 3*

---
**Generated by the Teacher skill**
**Topic: Building an AI Agent Platform (Technical Guide)**
**Parts: 3 · Sections: 20 · Code examples: 60+ · Production patterns: 30+**
**Languages: Python + C# throughout**
**Last updated: 2026-03-23**
