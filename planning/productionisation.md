# Velocity Platform — Productionisation & Consumption Strategy

## Overview

This document details how the Velocity platform moves from code to production, how agent teams consume it, and how the platform is operated at scale.

---

## 1. Distribution Model

Velocity is distributed as a **PyPI package**:

```bash
pip install velocity-platform
```

This gives agent teams:
- The SDK (`AgentBase`, `@tool`, `register_agent`, `AgentContext`)
- The CLI (`velocity init`, `velocity run`, `velocity test`, `velocity deploy`)
- All platform services (cost, rate limiting, security, audit, memory, etc.)
- In-memory backends for local development (zero external dependencies)

### Versioning

```
velocity-platform==1.0.0    # Stable releases (semver)
velocity-platform==1.1.0b1  # Beta releases for early feedback
```

- **Major version**: Breaking changes to `AgentBase` contract or `agent_config.yaml` schema
- **Minor version**: New features, new providers, new tool capabilities
- **Patch version**: Bug fixes, security patches, pricing table updates

---

## 2. Three Consumption Models

### Model A: SDK Import (Python agents — recommended)

```
┌─────────────────────────────────────────────┐
│ Agent Process                               │
│                                             │
│  from velocity.sdk import AgentBase, tool   │
│                                             │
│  class MyAgent(AgentBase):                  │
│      ...                                    │
│                                             │
│  ┌───────────────────────────────────────┐  │
│  │ Velocity Platform (embedded)          │  │
│  │ Engine · LLM Gateway · Audit · Cost   │  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

**How it works:**
1. Agent team installs `velocity-platform` via pip
2. Agent code imports and extends `AgentBase`
3. Platform boots inside the agent's process
4. All services (LLM calls, audit, cost) run in-process
5. Agent team deploys their own container

**Best for:** Teams that want full control over their deployment.

### Model B: HTTP API (Language-agnostic)

```
┌──────────────┐         ┌────────────────────────┐
│ Agent Code   │  HTTP   │ Velocity Platform API  │
│ (any lang)   │────────>│ POST /v1/agents/run    │
│              │<────────│                        │
└──────────────┘         │ Engine · Gateway · ... │
                         └────────────────────────┘
```

**How it works:**
1. Platform team deploys Velocity as a standalone service
2. Agents call `POST /v1/agents/run` with their agent_id and payload
3. Agent code can be in **any language** (Python, C#, Go, JS, etc.)
4. Platform handles everything: LLM calls, tools, memory, audit, cost

**Best for:** Non-Python teams, microservice architectures, centralised control.

### Model C: Platform-Hosted (Fully managed)

```
┌────────────────────────────┐      ┌───────────────────────────┐
│ Agent Developer            │      │ Velocity Platform         │
│                            │      │                           │
│ Pushes:                    │      │ Builds, deploys, hosts:   │
│  - agent_config.yaml       │─────>│  - Agent container        │
│  - agent.py                │      │  - Auto-scaling           │
│  - tools.py                │      │  - Monitoring             │
│  - prompts/*.yaml          │      │  - Cost dashboards        │
└────────────────────────────┘      └───────────────────────────┘
```

**How it works:**
1. Developer creates agent artifacts (config, code, prompts, evals)
2. Pushes to agent registry (Git repo or API)
3. Platform CI/CD builds, tests (eval gate), and deploys automatically
4. Agent is live at `POST /v1/agents/run {"agent_id": "my-agent"}`

**Best for:** Organisations wanting a PaaS-like experience for agents.

---

## 3. Agent Developer Workflow (End-to-End)

```
 ① SCAFFOLD        ② DEVELOP           ③ TEST             ④ DEPLOY           ⑤ MONITOR
┌──────────┐     ┌──────────────┐    ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ velocity  │     │ Write:       │    │ velocity     │   │ velocity     │   │ Grafana      │
│ init      │────>│  agent.py    │───>│ test         │──>│ deploy       │──>│ dashboards   │
│ my-agent  │     │  tools.py    │    │ my-agent     │   │ my-agent     │   │              │
│           │     │  prompts/    │    │              │   │              │   │ Cost / Audit  │
│ Scaffolds │     │  evals.py    │    │ Eval gate:   │   │ Rolling      │   │ / Latency /  │
│ all files │     │  config.yaml │    │ ≥90% pass    │   │ update       │   │ Errors       │
└──────────┘     └──────────────┘    └──────────────┘   └──────────────┘   └──────────────┘
```

### Step-by-step:

**① Scaffold:**
```bash
velocity init expense-approver
# Creates:
#   expense-approver/
#   ├── agent_config.yaml      # Pre-filled template
#   ├── agent.py               # AgentBase skeleton
#   ├── tools.py               # Example tool with @tool decorator
#   ├── evals.py               # Example eval test
#   └── prompts/
#       └── v1.0.0.yaml        # Prompt template
```

**② Develop:** Write domain-specific code only. Platform handles everything else.

**③ Test:**
```bash
velocity test expense-approver          # Run eval suite (mocked LLM)
velocity test expense-approver --live   # Run with real LLM (integration)
```

**④ Deploy:**
```bash
velocity deploy expense-approver --env staging   # Deploy to staging
velocity deploy expense-approver --env prod      # Deploy to production
```

**⑤ Monitor:**
```bash
velocity costs --agent expense-approver --days 7
velocity audit --agent expense-approver --last 100
```

---

## 4. Platform Configuration

### `platform_config.yaml` — The Single Source of Truth

```yaml
# Platform-wide configuration
platform:
  name: velocity
  version: "1.0.0"
  environment: production        # dev | staging | production

# Multi-tenancy
tenancy:
  enabled: true
  auth:
    provider: jwt                # jwt | api_key | oauth2
    jwt_secret_env: JWT_SECRET
    jwt_issuer: velocity-platform

# LLM Providers (fully provider-agnostic)
llm:
  default_provider: openai
  default_model: gpt-4o
  max_retries: 4
  circuit_breaker:
    failure_threshold: 5
    recovery_timeout_s: 60
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
      api_key_env: CUSTOM_API_KEY
      models: [llama3, mistral]
  fallback_chain: [openai, anthropic, google]

# Infrastructure (config-driven, plug-and-play)
infra:
  cache:
    backend: redis               # redis | memory
    redis_url: ${REDIS_URL}
  database:
    backend: postgresql          # postgresql | mysql | sqlite
    connection_string: ${DATABASE_URL}
    pool_size: 20
  vector_store:
    backend: qdrant              # qdrant | pgvector | memory
    qdrant_url: ${QDRANT_URL}
    collection_prefix: velocity_
  object_store:
    backend: s3                  # s3 | azure_blob | gcs | local
    s3_bucket: ${S3_BUCKET}
    s3_region: us-east-1
  event_stream:
    backend: redis_streams       # redis_streams | memory
    redis_url: ${REDIS_URL}

# Platform-wide defaults (overridable per agent)
defaults:
  max_iterations: 25
  max_output_tokens: 2048
  rate_limits:
    requests_per_minute: 60
    requests_per_hour: 500
  budget:
    daily_limit_usd: 100.0
    monthly_limit_usd: 2000.0

# Observability
observability:
  metrics:
    enabled: true
    prometheus_port: 9090
  audit:
    postgres_enabled: true
    s3_worm_enabled: true
    s3_retention_years: 7
```

### Local Development Override

```yaml
# platform_config.dev.yaml — zero external dependencies
platform:
  environment: dev

infra:
  cache:
    backend: memory
  database:
    backend: sqlite
    connection_string: "sqlite:///velocity_dev.db"
  vector_store:
    backend: memory
  object_store:
    backend: local
    local_path: ./data/storage
  event_stream:
    backend: memory

observability:
  metrics:
    enabled: false
  audit:
    postgres_enabled: false
    s3_worm_enabled: false
```

---

## 5. Deployment Architecture

### Development (Local)

```bash
velocity run my-agent                    # Uses in-memory backends
# or
docker compose -f deploy/docker/docker-compose.yml up   # Full stack locally
```

### Staging / Production (Kubernetes)

```
Internet → Load Balancer → Ingress Controller
                                ↓
                    ┌─────────────────────────┐
                    │ Velocity Platform Pods   │
                    │ (3-30 replicas, HPA)     │
                    │   FastAPI + Uvicorn      │
                    └────┬──────┬──────┬──────┘
                         │      │      │
            ┌────────────┘      │      └────────────┐
            ↓                   ↓                    ↓
    Redis Cluster        PostgreSQL           Qdrant Cluster
    (cache, rate         (audit, config)      (vector memory)
     limits, events)     + Read Replicas
```

### Key Deployment Properties

| Property | Implementation |
|----------|---------------|
| Zero-downtime deploys | Rolling update (maxSurge: 1, maxUnavailable: 0) |
| Auto-scaling | HPA: CPU 65% or queue depth > 100 items/pod |
| Health checks | `/health/live` (liveness), `/health/ready` (readiness) |
| Secret management | K8s Secrets / HashiCorp Vault / cloud-native |
| Configuration | ConfigMap from `platform_config.yaml` |
| Logging | Structured JSON → stdout → collected by Fluentd/CloudWatch |
| Tracing | OpenTelemetry spans with `request_id` correlation |

---

## 6. CI/CD Pipeline

```
┌──────┐   ┌──────┐   ┌────────┐   ┌────────┐   ┌──────┐   ┌─────────┐   ┌──────┐
│ Push │──>│ Lint │──>│ Type   │──>│ Unit   │──>│ Intg │──>│ Eval    │──>│Build │
│      │   │ ruff │   │ Check  │   │ Tests  │   │ Tests│   │ Suite   │   │ PyPI │
│      │   │      │   │ mypy   │   │ pytest │   │      │   │ ≥90%    │   │  +   │
│      │   │      │   │        │   │ 90%cov │   │      │   │ pass    │   │Docker│
└──────┘   └──────┘   └────────┘   └────────┘   └──────┘   └─────────┘   └──────┘
                                                                              │
                                                              ┌───────────────┘
                                                              ↓
                                                    ┌──────────────────┐
                                                    │ Deploy (staging) │
                                                    │ Smoke tests      │
                                                    │ Deploy (prod)    │
                                                    └──────────────────┘
```

### Deployment gates:

| Gate | Condition | Blocks on Failure |
|------|-----------|-------------------|
| Lint | Zero ruff violations | Yes |
| Types | Zero mypy errors | Yes |
| Unit tests | 90%+ pass, 90%+ coverage | Yes |
| Integration | All infra tests pass (Docker) | Yes |
| Eval suite | ≥90% pass rate | Yes |
| Eval regression | Pass rate drop ≤5% from baseline | Yes |
| Critical evals | All critical-tagged cases pass | Yes |

---

## 7. Operational Runbook

### Monitoring Dashboards (Grafana)

**Dashboard 1: Platform Overview**
- Total agent invocations (rate, by status)
- P50/P95/P99 latency
- Active circuit breaker states
- Error rates by agent and type

**Dashboard 2: Cost & Budget**
- Daily/monthly LLM spend (by agent, tenant, model)
- Budget utilisation % per tenant
- Cost per request trending
- Model routing distribution

**Dashboard 3: Agent Health**
- Per-agent latency and error rates
- Tool call success/failure rates
- Eval score trending over time
- Human review queue depth

**Dashboard 4: Security & Compliance**
- PII detection events
- Injection attempt blocks
- Permission denials
- Audit log write latency

### Alerting Rules

| Alert | Condition | Severity |
|-------|-----------|----------|
| Circuit breaker open | Any provider circuit opens | Critical |
| Budget exceeded | Tenant hits daily limit | Warning |
| Budget approaching | Tenant at 80% of daily limit | Info |
| Eval score drop | Agent eval drops >5% | Warning |
| High error rate | Agent error rate >10% for 5 min | Critical |
| Audit write failure | Audit log write fails | Critical |
| Rate limit storm | >100 rate limit hits in 1 min | Warning |

---

## 8. How Agents Stay Outside the Platform

The platform is a **service layer** — agents don't need to be inside it.

```
PLATFORM BOUNDARY
─────────────────────────────────────────────────────
│                                                   │
│  Velocity Platform                                │
│  (deployed as a service or imported as a library) │
│                                                   │
│  Provides:                                        │
│    ✓ LLM access (provider-agnostic)               │
│    ✓ Tool registry & execution                    │
│    ✓ Memory (short/long/episodic)                 │
│    ✓ Cost tracking & budgets                      │
│    ✓ Rate limiting                                │
│    ✓ Security (PII, injection, RBAC)              │
│    ✓ Audit logging                                │
│    ✓ Observability                                │
│                                                   │
─────────────────────────────────────────────────────

AGENT BOUNDARY (external, owned by product teams)
─────────────────────────────────────────────────────
│                                                   │
│  My Agent                                         │
│  (deployed independently, any language)           │
│                                                   │
│  Owns:                                            │
│    ✓ System prompt (what it knows)                │
│    ✓ Domain tools (what it can do)                │
│    ✓ Business logic (how it decides)              │
│    ✓ Agent config (how it behaves)                │
│                                                   │
│  Consumes platform via:                           │
│    • pip install velocity-platform (Python)       │
│    • POST /v1/agents/run (any language)           │
│                                                   │
─────────────────────────────────────────────────────
```

### Separation of Concerns

| Concern | Who Owns It | Where It Lives |
|---------|-------------|----------------|
| LLM retry logic | Platform | `velocity.core.llm_gateway` |
| Domain prompt | Agent team | `prompts/v1.0.0.yaml` |
| Cost tracking | Platform | `velocity.services.cost` |
| "Get customer" tool | Agent team | `tools.py` |
| PII masking | Platform | `velocity.services.security` |
| Agent config | Agent team | `agent_config.yaml` |
| Rate limiting | Platform | `velocity.services.rate_limiter` |
| Decision logic | Agent team | Defined by prompt + tools |
| Audit logging | Platform | `velocity.services.audit` |
| Deployment | Platform (or agent team) | K8s / Docker |

---

## 9. Scaling Strategy

### Phase 1 (1-5 agents): Single Deployment
- One Velocity instance (3 replicas)
- All agents registered in the same process
- Shared Redis, PostgreSQL, Qdrant
- Cost: ~$200/month infra

### Phase 2 (5-20 agents): Dedicated Namespaces
- Agents grouped by team/tenant in K8s namespaces
- Shared platform services, dedicated rate limit quotas
- Separate Grafana dashboards per team
- Cost: ~$800/month infra

### Phase 3 (20+ agents): Federated Platform
- Multiple Velocity instances (one per business unit)
- Shared control plane (cost reporting, audit, admin)
- Independent data planes (agents, tools, memory)
- Cross-cluster observability via centralised Prometheus
- Cost: scales linearly with usage

---

## 10. Security Checklist for Production

```
PRE-LAUNCH
[ ] All API endpoints require JWT authentication
[ ] Tenant isolation verified (cross-tenant data leak test)
[ ] PII masking active and tested with real PII patterns
[ ] Prompt injection detection active
[ ] RBAC permissions configured for all agents
[ ] Audit logging writing to PostgreSQL + S3 WORM
[ ] S3 Object Lock enabled (COMPLIANCE mode, 7-year retention)
[ ] Database Row Level Security enabled
[ ] Secret management configured (no plaintext keys)
[ ] Rate limits configured per tenant and agent

ONGOING
[ ] Security scan in CI/CD (Bandit, Safety)
[ ] Dependency vulnerability scanning (Dependabot / Snyk)
[ ] Quarterly access review of agent permissions
[ ] Monthly audit log review for anomalies
[ ] Annual penetration test of platform API
```

---

## Summary

| Aspect | Approach |
|--------|----------|
| **Distribution** | PyPI package: `pip install velocity-platform` |
| **Consumption** | SDK import (Python) or HTTP API (any language) |
| **Config** | Single `platform_config.yaml` — all infra is plug-and-play |
| **Local dev** | `velocity run` with in-memory backends, zero dependencies |
| **Staging/Prod** | Kubernetes with HPA, Redis, PostgreSQL, Qdrant |
| **CI/CD** | Eval-gated deployments — agents can't ship if evals fail |
| **Multi-tenancy** | Core feature — data, cost, rate limits isolated per tenant |
| **LLM providers** | Any provider via config — Anthropic, OpenAI, Google, custom |
| **Monitoring** | Prometheus + Grafana dashboards + structured alerting |
| **Agents** | Stay outside the platform — own only domain logic |
