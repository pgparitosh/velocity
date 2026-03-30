# Velocity Platform — Architecture & Diagrams

## 1. System Architecture (Layered View)

```mermaid
graph TB
    subgraph "LAYER 4: Agent SDK"
        SDK["AgentBase · @tool · AgentBuilder<br/>agent_config.yaml · CLI"]
    end

    subgraph "LAYER 3: Core Engine"
        ENGINE["AgentEngine<br/>Execution Loop"]
        LLM["LLM Gateway<br/>Provider-Agnostic · Retry · Circuit Breaker"]
        TOOLS["Tool Registry<br/>Register · Discover · Execute"]
        PROMPTS["Prompt Library<br/>Version · Cache · A/B Test"]
        MEMORY["Memory Manager<br/>Short · Long · Episodic"]
        ORCH["Orchestration Engine<br/>DAG · Parallel · Human Gate"]
        MCP["MCP Broker<br/>Protocol Translation"]
        EVAL["Eval Framework<br/>Suite · Runner · CI Gate"]
    end

    subgraph "LAYER 2: Platform Services"
        COST["Cost Manager<br/>Budget · Routing · Attribution"]
        RATE["Rate Limiter<br/>Sliding Window · 3-Level"]
        SEC["Security Layer<br/>PII · Injection · RBAC"]
        VAL["Validation Engine<br/>Input · Output · Schema"]
        AUDIT["Audit Logger<br/>Immutable · Dual-Write"]
        EVENTS["Event Bus<br/>Platform Events"]
        METRICS["Observability<br/>Prometheus · Grafana"]
    end

    subgraph "LAYER 1: Infrastructure"
        REDIS["Cache<br/>Redis / In-Memory"]
        PG["Database<br/>Any SQL (config-driven)"]
        VECTOR["Vector Store<br/>Qdrant / pgvector"]
        S3["Object Store<br/>S3 / Local FS"]
        RSTREAM["Event Stream<br/>Redis Streams"]
    end

    SDK --> ENGINE
    ENGINE --> LLM
    ENGINE --> TOOLS
    ENGINE --> PROMPTS
    ENGINE --> MEMORY
    ENGINE --> ORCH
    ENGINE --> MCP
    ENGINE --> EVAL

    ENGINE --> COST
    ENGINE --> RATE
    ENGINE --> SEC
    ENGINE --> VAL
    ENGINE --> AUDIT
    ENGINE --> EVENTS
    ENGINE --> METRICS

    COST --> REDIS
    RATE --> REDIS
    MEMORY --> REDIS
    MEMORY --> VECTOR
    AUDIT --> PG
    AUDIT --> S3
    PROMPTS --> S3
    PROMPTS --> REDIS
    EVENTS --> RSTREAM
    LLM -.->|"Any LLM Provider"| EXTLLM["Anthropic / OpenAI / Google<br/>Azure / Custom (Ollama, vLLM)"]
```

---

## 2. Request Lifecycle (Single Agent Execution)

```mermaid
sequenceDiagram
    participant Client
    participant API as Platform API
    participant Engine as AgentEngine
    participant Rate as RateLimiter
    participant Sec as SecurityLayer
    participant Val as ValidationEngine
    participant Cost as CostManager
    participant Prompt as PromptLibrary
    participant Mem as MemoryManager
    participant LLM as LLMGateway
    participant Tool as ToolRegistry
    participant Audit as AuditLogger

    Client->>API: POST /v1/agents/run
    API->>API: JWT Auth + Tenant Extract
    API->>Engine: engine.run(agent, payload, ctx)

    Note over Engine: ── Pre-flight ──
    Engine->>Rate: check_and_consume(agent_id, tenant_id)
    Engine->>Sec: validate_input(payload, ctx)
    Engine->>Val: validate_input(agent_id, payload)
    Engine->>Cost: check_budget(agent_id, tenant_id)

    Note over Engine: ── Setup ──
    Engine->>Prompt: resolve(agent.system_prompt())
    Prompt-->>Engine: rendered prompt text
    Engine->>Mem: load_short_term(session_id)
    Mem-->>Engine: conversation history

    Note over Engine: ── Agentic Loop ──
    loop Until end_turn or max_iterations
        Engine->>Mem: retrieve_relevant(query, ctx)
        Mem-->>Engine: semantic memory context
        Engine->>LLM: call(system_prompt, tools, messages, ctx)
        LLM-->>Engine: response

        alt response.stop_reason == "tool_use"
            Engine->>Sec: validate_tool_call(name, inputs, ctx)
            Engine->>Tool: execute(name, inputs, ctx)
            Tool-->>Engine: tool result
        else response.stop_reason == "end_turn"
            Note over Engine: Parse result, exit loop
        end
    end

    Note over Engine: ── Post-flight ──
    Engine->>Audit: write(payload, result, ctx)
    Engine->>Cost: record(ctx)
    Engine->>Mem: save_short_term(session_id, messages)
    Engine->>Sec: sanitise_output(result, ctx)
    Engine->>Val: validate_output(agent_id, result)

    Engine-->>API: result
    API-->>Client: RunAgentResponse
```

---

## 3. Multi-Agent Orchestration Flow

```mermaid
graph TD
    START["Initial Payload"] --> PAR{"PARALLEL<br/>Node"}

    PAR --> KYC["KYC Agent"]
    PAR --> CREDIT["Credit Agent"]

    KYC --> MERGE{"TRANSFORM<br/>Merge Results"}
    CREDIT --> MERGE

    MERGE --> COND{"CONDITION<br/>Both Passed?"}

    COND -->|Yes| UW["Underwriting Agent"]
    COND -->|No| REJECT["Return: Rejected"]

    UW --> GATE{"HUMAN_GATE<br/>Amount > $50K?"}

    GATE -->|Approved| NOTIFY["Notification Agent"]
    GATE -->|Rejected| REJECT2["Return: Rejected by Human"]

    NOTIFY --> DONE["Return: Completed"]

    style PAR fill:#4a9eff,color:#fff
    style COND fill:#ff9f43,color:#fff
    style GATE fill:#e74c3c,color:#fff
    style MERGE fill:#2ecc71,color:#fff
    style KYC fill:#6c5ce7,color:#fff
    style CREDIT fill:#6c5ce7,color:#fff
    style UW fill:#6c5ce7,color:#fff
    style NOTIFY fill:#6c5ce7,color:#fff
```

---

## 4. LLM Gateway Resilience

```mermaid
stateDiagram-v2
    [*] --> CLOSED: Initial State

    CLOSED --> CLOSED: Success (reset failure count)
    CLOSED --> OPEN: Failure count >= threshold (5)

    OPEN --> HALF_OPEN: After recovery_timeout (60s)
    OPEN --> OPEN: All requests fail-fast

    HALF_OPEN --> CLOSED: Test request succeeds
    HALF_OPEN --> OPEN: Test request fails

    state CLOSED {
        [*] --> NormalFlow
        NormalFlow --> Retry: Retryable error (429, 503)
        Retry --> NormalFlow: Retry succeeds
        Retry --> IncrementFailure: All retries exhausted
        NormalFlow --> ModelFallback: 429 on retry 2+
        ModelFallback --> NormalFlow: Fallback succeeds
    }
```

---

## 5. Data Flow Architecture

```mermaid
graph LR
    subgraph "Hot Path (Real-time)"
        REQ["Agent Request"] --> REDIS_RL["Redis<br/>Rate Limits"]
        REQ --> REDIS_COST["Redis<br/>Cost Counters"]
        REQ --> REDIS_MEM["Redis<br/>Short-term Memory"]
        REQ --> REDIS_CACHE["Redis<br/>Prompt Cache"]
    end

    subgraph "Warm Path (Near Real-time)"
        REQ --> PG["PostgreSQL<br/>Audit Logs"]
        REQ --> VECTOR_DB["Vector DB<br/>Long-term Memory"]
        REQ --> PROM["Prometheus<br/>Metrics"]
    end

    subgraph "Cold Path (Async)"
        PG --> S3_AUDIT["S3 WORM<br/>Immutable Audit"]
        PROM --> GRAFANA["Grafana<br/>Dashboards"]
        REQ --> STREAM["Event Stream<br/>Platform Events"]
    end

    style REDIS_RL fill:#e74c3c,color:#fff
    style REDIS_COST fill:#e74c3c,color:#fff
    style REDIS_MEM fill:#e74c3c,color:#fff
    style REDIS_CACHE fill:#e74c3c,color:#fff
    style PG fill:#3498db,color:#fff
    style VECTOR_DB fill:#9b59b6,color:#fff
    style S3_AUDIT fill:#2ecc71,color:#fff
```

---

## 6. Deployment Topology (Production)

```mermaid
graph TB
    subgraph "Edge"
        LB["Load Balancer<br/>NGINX / ALB"]
    end

    subgraph "Kubernetes Cluster"
        subgraph "Platform Pods (3-30 replicas)"
            POD1["Platform API<br/>Pod 1"]
            POD2["Platform API<br/>Pod 2"]
            POD3["Platform API<br/>Pod 3"]
        end

        subgraph "MCP Servers"
            MCP1["MCP Server<br/>Internal Tools"]
            MCP2["MCP Server<br/>External APIs"]
        end

        HPA["HPA<br/>Auto-scaler<br/>CPU 65% / Queue 100"]
    end

    subgraph "Data Layer"
        RD["Redis Cluster<br/>Cache + Rate Limits"]
        PG_PRIMARY["PostgreSQL Primary<br/>Audit + Config"]
        PG_REPLICA["PostgreSQL Replica<br/>Read Queries"]
        QD["Qdrant<br/>Vector Memory"]
    end

    subgraph "External"
        CLAUDE["Anthropic API"]
        OAI["OpenAI API"]
        S3_STORE["S3<br/>Prompts + Audit Archive"]
    end

    LB --> POD1
    LB --> POD2
    LB --> POD3
    HPA -.-> POD1
    HPA -.-> POD2
    HPA -.-> POD3

    POD1 --> RD
    POD1 --> PG_PRIMARY
    POD1 --> QD
    POD1 --> CLAUDE
    POD1 --> MCP1

    PG_PRIMARY --> PG_REPLICA
    PG_PRIMARY --> S3_STORE
```

---

## 7. Security Architecture

```mermaid
graph TD
    INPUT["Incoming Request"] --> AUTH["JWT Authentication<br/>Tenant Extraction"]
    AUTH --> SIZE["Payload Size Check<br/>Max 100KB"]
    SIZE --> INJECT_IN["Injection Detection<br/>Input Scanning"]
    INJECT_IN --> SCHEMA_IN["Input Schema Validation<br/>JSON Schema"]

    SCHEMA_IN --> ENGINE["Agent Execution"]

    ENGINE --> TOOL_PERM["Tool Permission Check<br/>RBAC"]
    TOOL_PERM --> INJECT_TOOL["Injection Detection<br/>Tool Input Scanning"]
    INJECT_TOOL --> TOOL_EXEC["Tool Execution<br/>Sandboxed + Timeout"]

    ENGINE --> PII_OUT["PII Detection<br/>Output Scanning"]
    PII_OUT --> SCHEMA_OUT["Output Schema Validation<br/>Advisory"]
    SCHEMA_OUT --> RESPONSE["Sanitized Response"]

    style AUTH fill:#e74c3c,color:#fff
    style INJECT_IN fill:#e74c3c,color:#fff
    style INJECT_TOOL fill:#e74c3c,color:#fff
    style TOOL_PERM fill:#e74c3c,color:#fff
    style PII_OUT fill:#e74c3c,color:#fff
```

---

## 8. Multi-Tenancy Isolation Model

```mermaid
graph TB
    subgraph "Tenant A (Fraud Team)"
        A_AGENT["Fraud Agent"]
        A_RATE["Rate Limit: 100 rpm"]
        A_BUDGET["Budget: $500/day"]
        A_AUDIT["Audit (RLS filtered)"]
    end

    subgraph "Tenant B (DevOps Team)"
        B_AGENT["PR Review Agent"]
        B_RATE["Rate Limit: 60 rpm"]
        B_BUDGET["Budget: $200/day"]
        B_AUDIT["Audit (RLS filtered)"]
    end

    subgraph "Shared Platform"
        PLATFORM["AgentEngine<br/>(Shared Instance)"]
        REDIS_ISO["Redis<br/>Tenant-scoped keys<br/>rl:tenant:{id}:*<br/>cost:daily:{id}:*"]
        PG_RLS["PostgreSQL<br/>Row Level Security<br/>tenant_id column"]
    end

    A_AGENT --> PLATFORM
    B_AGENT --> PLATFORM
    PLATFORM --> REDIS_ISO
    PLATFORM --> PG_RLS
    A_AUDIT -.-> PG_RLS
    B_AUDIT -.-> PG_RLS
```

**Isolation guarantees:**
- Rate limits: separate Redis keys per tenant — Tenant A exhausting quota does NOT affect Tenant B
- Cost tracking: separate daily/monthly counters per tenant
- Audit logs: PostgreSQL Row Level Security — tenants see only their own records
- Memory: short-term keys scoped to `mem:short:{tenant_id}:{session_id}`

---

## 9. Agent Developer Experience Flow

```mermaid
graph LR
    DEV["Developer"] -->|"velocity init my-agent"| SCAFFOLD["Scaffolds:<br/>agent_config.yaml<br/>agent.py<br/>tools.py<br/>evals.py<br/>prompts/v1.0.0.yaml"]

    SCAFFOLD -->|"Write domain code"| CODE["Implement:<br/>3 methods<br/>+ domain tools<br/>+ system prompt"]

    CODE -->|"velocity test my-agent"| TEST["Run eval suite<br/>Pass rate ≥ 90%?"]

    TEST -->|Pass| DEPLOY["velocity deploy<br/>→ Platform registers agent<br/>→ K8s rolling update"]
    TEST -->|Fail| CODE

    DEPLOY --> LIVE["Agent is live at<br/>POST /v1/agents/run<br/>{'agent_id': 'my-agent'}"]

    style DEV fill:#6c5ce7,color:#fff
    style LIVE fill:#2ecc71,color:#fff
```

---

## Technology Stack Summary

| Layer | Component | Dev/Local | Production |
|-------|-----------|-----------|------------|
| Runtime | Python | 3.12+ | 3.12+ (containerized) |
| API Framework | FastAPI | uvicorn (hot-reload) | gunicorn + uvicorn workers |
| Cache | Redis | In-memory dict | Redis Cluster |
| Database | PostgreSQL | SQLite | PostgreSQL 16 + RLS |
| Vector DB | Vector Store | In-memory list | Qdrant / pgvector |
| Object Store | S3 | Local filesystem | S3 + Object Lock |
| Metrics | Prometheus | Console export | Prometheus + Grafana |
| Container | Docker | docker-compose | Kubernetes (EKS/AKS/GKE) |
| LLM Provider | Any (provider-agnostic) | All configured providers | Multi-provider + fallback chains |
| CI/CD | GitHub Actions | Local pytest | lint → type-check → test → eval → deploy |
