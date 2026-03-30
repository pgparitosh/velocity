# Velocity - High-Performance AI Agent Platform

Velocity is a production-grade infrastructure layer for building, deploying, and scaling AI agents. It provides the "boring" but critical parts of agentic systems—security, observability, cost control, and memory—so you can focus on domain logic.

## 🚀 Key Features

*   **Layered Architecture**: Decouples infrastructure from agent logic (Platform vs. SDK).
*   **Safety & Compliance**: PII masking, injection detection, and dual-write WORM audit logs.
*   **Cost Management**: Token budgeting, model routing, and cost attribution per tenant/agent.
*   **Memory Management**: Short-term session state, long-term semantic memory (Vector Store), and episodic summaries.
*   **Model Context Protocol (MCP)**: Native support for MCP servers for external tool discovery.
*   **Production API**: FastAPI-based REST interface with JWT authentication and Prometheus metrics.

## 📦 Installation

Velocity requires Python 3.12+ and can be installed via pip:

```bash
pip install velocity-platform
```

## 🛠️ Usage Example

Define your agent by inheriting from `AgentBase`:

```python
from velocity.sdk import AgentBase, AgentContext, tool

class MyAgent(AgentBase):
    AGENT_ID = "support-agent"

    def system_prompt(self) -> str:
        return "You are a helpful support assistant."

    def tools(self) -> list:
        return [my_tool.__tool_metadata__.to_llm_schema()]

    async def execute_tool(self, name, inputs, ctx):
        if name == "my_tool":
            return await my_tool(**inputs)
```

## 🔋 Platform Capabilities

### Infrastructure Backends
Velocity is configuration-driven. Swap backends via `platform_config.yaml`:
*   **Cache**: Redis / In-Memory
*   **Database**: PostgreSQL / SQLite
*   **Vector Store**: Qdrant / In-Memory
*   **Object Store**: S3 / Local Filesystem

### Observability
All agent executions are instrumented with:
*   **Prometheus Metrics**: Latency, Cost, Token Count, Tool Performance.
*   **Audit Logs**: Complete, immutable records of all interactions.
*   **Traces**: Full request context and execution timeline.

## 📖 Documentation & Examples

*   **[Getting Started](docs/getting-started.md)**: Your first 5 minutes with Velocity.
*   **[Architecture Guide](docs/architecture.md)**: Deep dive into the tiered platform layers.
*   **[Example Agent](examples/hello-agent/)**: A complete hello-world implementation.

## 🏗️ Building & Publishing

Velocity uses `hatch` for builds.

```bash
# Build the package
python -m build

# Or using hatch directly
hatch build
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
