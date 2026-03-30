# Velocity Platform Architecture

Velocity is designed as a layered platform that separates infrastructure concerns from agent domain logic.

## 1. System Architecture (Layered View)

Velocity is composed of four primary layers:

### Layer 1: Infrastructure (Plug-and-Play)
- **Cache**: Redis or In-Memory (for local dev).
- **Database**: PostgreSQL or SQLite.
- **Vector Store**: Qdrant or In-Memory.
- **Object Store**: S3 or Local Filesystem.
- **Event Stream**: Redis Streams.

### Layer 2: Platform Services (Cross-Cutting Middleware)
- **Cost Manager**: Budget enforcement, model routing, and cost attribution.
- **Rate Limiter**: Sliding window fair-usage enforcement (3-level).
- **Security Layer**: PII detection, prompt injection blocking, and RBAC checks.
- **Validation Engine**: JSON Schema validation for inputs and outputs.
- **Audit Logger**: Immutable, dual-write to DB and S3 WORM storage.
- **Event Bus**: Central platform-wide event broadcasting.

### Layer 3: Core Engine
- **AgentEngine**: The central execution orchestrator.
- **LLM Gateway**: Provider-agnostic access with retry logic and failovers.
- **Tool Registry**: Manages discovery and execution of platform tools.
- **Prompt Library**: Versioned, cached, and A/B testable prompt storage.
- **Memory Manager**: Short-term, long-term, and episodic context management.
- **Orchestration Engine**: Multi-agent DAG execution and human-in-the-loop gates.
- **MCP Broker**: Routing to external Model Context Protocol (MCP) servers.

### Layer 4: Agent SDK (Developer Facing)
- **AgentBase**: Abstract class that defined the agent contract.
- **@tool decorator**: Simple registration of domain-specific tools.
- **AgentBuilder**: Automated wiring of agents from YAML configurations.
- **CLI Tooling**: `velocity init`, `run`, `test`, and `deploy`.

## 2. Request Lifecycle

1. **Authentication**: JWT token verify and tenant extraction.
2. **Pre-flight Checks**: Rate limit, Security scan, and Budget verify.
3. **Setup**: Resolve system prompt from library and load history from memory.
4. **Execution Loop**: The agentic loop handles tool calls and LLM turns iteratively.
5. **Post-flight**: Write audit log, record costs, and sanitize output.

## 3. Deployment Philosophy

- **Python-First**: Native Python SDK for high-performance agent building.
- **Stateless API**: The platform is horizontally scalable via Kubernetes.
- **Configuration-Driven**: Infrastructure is swapped via YAML without code changes.
