# Velocity AI Agent Platform - Agent Builder Guide

**Purpose:** This guide explains what the Velocity platform does and how to build production-ready AI agents with minimal code using the platform's infrastructure.

**Target Audience:** Developers using coding agents to build agents on the Velocity platform.

---

## Table of Contents

1. [Platform Overview](#platform-overview)
2. [What the Platform Provides](#what-the-platform-provides)
3. [Key Concepts](#key-concepts)
4. [Agent Architecture Pattern](#agent-architecture-pattern)
5. [Building Your First Agent](#building-your-first-agent)
6. [Advanced Patterns](#advanced-patterns)
7. [Configuration](#configuration)
8. [File Structure](#file-structure)
9. [Example Agents](#example-agents)

---

## Platform Overview

**Velocity** is a production-grade infrastructure platform for building, deploying, and scaling AI agents. It provides all the "boring but critical" operational concerns so developers can focus purely on agent domain logic.

### Philosophy: "Write Less Code, Achieve More"

The platform handles:
- Resilience and retries across LLM providers
- Cost tracking and budget enforcement
- Security (PII detection, injection prevention)
- Observability (metrics, traces, audit logs)
- Memory management (session state, semantic context)
- Multi-agent orchestration
- RBAC-based tool execution
- REST API and scalable deployment

You focus on:
- What your agent should do (domain logic)
- What tools it needs (tool definitions)
- How it interacts with those tools (tool execution)

---

## What the Platform Provides

### 1. **Agent Execution Engine** (`AgentEngine`)

Orchestrates the complete LLM interaction loop:
- Manages agentic iteration (think/act/observe cycles)
- Handles tool discovery and execution (sequential and parallel)
- Tracks metrics, costs, and execution timeline
- Enforces iteration limits, timeouts, and budgets
- Manages session memory (loads context automatically)

**You don't write:** Loop logic, tool orchestration, context management

### 2. **LLM Gateway** (Provider Abstraction)

Single interface to multiple LLM providers:
- Supports OpenAI, Anthropic, Groq, Google Vertex
- Automatic retries with exponential backoff
- Provider fallback chains (e.g., OpenAI → Anthropic on failure)
- Token counting and cost calculation
- Circuit breaker pattern for resilience

**You don't write:** Provider-specific code, retry logic, cost calculations

### 3. **Tool Registry & Execution** (Centralized Tool Management)

```
@tool decorator
    ↓
Automatic JSON schema generation
    ↓
RBAC permission checking
    ↓
Timeout-bounded execution
    ↓
Success/failure recording
```

**You don't write:** Schema generation, permission checks, execution bounds

### 4. **Memory Manager** (Multi-Layer Memory)

Three types of memory automatically managed:

| Memory Type | Purpose | Example |
|---|---|---|
| **Short-term** | Session conversation history | "In our conversation, we discussed..." |
| **Long-term** | Semantic knowledge retrieval | Find facts from past interactions |
| **Episodic** | Summarized interaction patterns | "You usually ask about..." |

Auto-loaded into system prompt, auto-persisted after execution.

**You don't write:** Context loading/saving, memory indexing

### 5. **Security Layer** (Data Protection)

Automatic:
- PII detection and redaction (SSN, credit cards, personal names, emails)
- Prompt injection / jailbreak detection
- Output sanitization before returning to users
- Audit trail of all security events

**You don't write:** Security checks, masking logic

### 6. **Cost & Budget Management**

Automatic:
- Per-tenant daily/monthly budget limits
- Token usage tracking per model
- Cost attribution per agent
- Hard budget enforcement (fails gracefully when exceeded)

**You don't write:** Budget checks, cost tracking

### 7. **Observability & Metrics**

Automatic collection:
- Request count, latency, cost aggregation
- Tool call success/failure rates
- Token consumption per model
- Structured logging with request tracing
- Integration with Prometheus/monitoring systems

**You don't write:** Metrics collection, logging infrastructure

### 8. **REST API** (Production Deployment)

Built-in FastAPI-based REST API:
- `POST /v1/agents/run` - Execute agent
- JWT authentication with tenant isolation
- Status polling, request tracking
- Standardized error responses

**You don't write:** API implementation, authentication

### 9. **Multi-Agent Orchestration** (Workflow Engine)

DAG-based workflow execution:
- Automatic topological sorting for parallel execution
- State passing between agents
- Conditional task execution
- Timeout and budget enforcement across workflow

**You don't write:** DAG management, dependency resolution

---

## Key Concepts

### **AgentBase** (Core Contract)

All agents inherit from `AgentBase`. You implement:

```python
from velocity.sdk import AgentBase

class MyAgent(AgentBase):
    # 1. Unique identifier
    AGENT_ID = "my-agent"
    
    # 2. (Optional) Tools from global registry
    global_tools = ["search", "calculate"]
    
    # 3. (Optional) Local agent-specific tools
    local_tools = [my_custom_tool]
    
    # 4. REQUIRED: System prompt - your agent's personality/instructions
    def system_prompt(self) -> str:
        return """You are a helpful assistant that...
        
        You have access to the following tools: search, calculate.
        Use them when needed to answer user questions."""
    
    # 5. Return tool schemas for the LLM
    def tools(self) -> list[dict]:
        schemas = []
        for tool in self.global_tools:
            schemas.append(registry.get_schema(tool))
        schemas.extend([t.__tool_metadata__.to_llm_schema() for t in self.local_tools])
        return schemas
    
    # 6. Execute the tool when LLM calls it
    async def execute_tool(self, name: str, inputs: dict, ctx: AgentContext):
        if name == "search":
            return await registry.execute(name, inputs, ctx)
        if name == "my_custom_tool":
            return await my_custom_tool(**inputs)
        raise ValueError(f"Unknown tool: {name}")
    
    # OPTIONAL: Lifecycle hooks for custom logic
    async def on_before_llm_call(self, messages, ctx):
        # Modify messages before sending to LLM (e.g., add few-shot examples)
        return messages
    
    async def on_after_tool_call(self, tool_name, result, ctx):
        # Transform tool result for LLM (e.g., extract key fields)
        return result
    
    async def on_final_result(self, result, ctx):
        # Post-process final output (e.g., format, add metadata)
        return result
    
    async def on_error(self, error, ctx):
        # Handle errors (e.g., log, fallback behavior)
        return "I encountered an error. Please try again."
    
    def parse_result(self, text, ctx):
        # Return structured output instead of just text
        return {"output": text}
```

### **@tool Decorator** (Tool Registration)

Define tools that the agent can use:

```python
from velocity.sdk import tool

@tool(
    name="search_web",
    description="Search the web for information",
    requires_permissions=["data.read"],  # RBAC scope
    timeout_seconds=10.0,                 # Execution timeout
    rate_limit_per_minute=120             # Rate limiting
)
async def search_web(query: str) -> str:
    """Search the web and return top results.
    
    Args:
        query: The search query
    
    Returns:
        Search results as formatted string
    """
    # Implementation...
    return results
```

**Automatic:**
- JSON schema generated from type hints
- Tool registered in global registry
- RBAC permissions enforced before execution
- Timeout bounds enforced during execution
- Success/failure recorded in metrics

### **AgentContext** (Execution State)

Passed to every tool call, contains execution metadata:

```python
@dataclass
class AgentContext:
    # Identity & Tracing
    request_id: str          # Unique request ID for tracing
    agent_id: str            # Which agent is running
    tenant_id: str           # Which tenant (for isolation)
    session_id: str | None   # Session ID for memory continuity
    
    # Execution State
    iteration: int           # Which iteration are we on
    tool_calls: list[dict]   # All tool calls made so far
    llm_calls: list[dict]    # All LLM calls made so far
    events: list[dict]       # All events recorded
    
    # Budget & Cost Tracking
    total_input_tokens: int
    total_output_tokens: int
    cost_usd: float
    
    # Methods
    def elapsed_ms(self) -> float          # Time elapsed
    def record_llm_call(...)               # Record LLM call
    def record_tool_call(...)              # Record tool call
```

### **ToolRegistry** (Centralized Tool Catalog)

Global registry of all available tools:

```python
from velocity.tools import ToolRegistry

registry = ToolRegistry()

# Tools are auto-registered via @tool decorator
# Retrieve in agents via:
metadata = registry.get_metadata("tool_name")
schema = registry.get_schema("tool_name")

# Execute (with RBAC, validation, timeout):
result = await registry.execute(
    "tool_name",
    inputs={"param": "value"},
    context=ctx,
    permissions=["data.read"]
)
```

### **LLMGateway** (Provider Abstraction)

Abstract interface to all LLM providers:

```python
from velocity.core.llm_gateway import LLMGateway

gateway = LLMGateway(
    providers={
        "openai": OpenAIProvider(...),
        "anthropic": AnthropicProvider(...),
        "groq": GroqProvider(...)
    },
    default_provider="openai",
    fallback_chain=["openai", "anthropic"]  # Fallback on failure
)

# Use it (platform does this automatically):
response = await gateway.call(
    ctx=context,
    system_prompt="You are...",
    tools=[...],
    messages=[...],
    model="gpt-4o"
)
```

### **MemoryManager** (Session Continuity)

Automatic session memory management:

```python
# No code needed! Platform does this automatically.
# But conceptually:

manager = MemoryManager()

# First turn
result1 = await engine.run(
    agent=agent,
    payload="What's your name?",
    session_id="user-123",
    tenant_id="tenant-1"
)

# Second turn (context auto-loaded)
result2 = await engine.run(
    agent=agent,
    payload="What did I ask before?",
    session_id="user-123",  # Same session!
    tenant_id="tenant-1"
)
# Agent automatically has access to first turn
```

---

## Agent Architecture Pattern

### Minimal Agent (Recommended)

The showcase agent demonstrates this pattern:

```
agents/
├── base.py              # MinimalAgent base class (reusable)
├── data_agent.py        # 10 lines - config only
├── processing_agent.py  # 10 lines - config only
└── analysis_agent.py    # 10 lines - config only

tools/
├── __init__.py
├── data_collection.py   # Agent-specific tools
├── processing.py
└── analysis.py

run.py                   # Workflow orchestration
```

**Key Insight:** Use a base class to eliminate duplication:

```python
# base.py
class MinimalAgent(AgentBase):
    TOOLS_CONFIG: dict[str, callable] = {}
    
    def tools(self) -> list[dict]:
        schemas = []
        for tool_func in self.TOOLS_CONFIG.values():
            schemas.append(tool_func.__tool_metadata__.to_llm_schema())
        return schemas
    
    async def execute_tool(self, name: str, inputs: dict, ctx: AgentContext):
        if name in self.TOOLS_CONFIG:
            return await self.TOOLS_CONFIG[name](**inputs)
        raise ValueError(f"Unknown tool: {name}")

# data_agent.py
from tools import get_weather, get_time, search_knowledge

class DataAgent(MinimalAgent):
    AGENT_ID = "data-agent"
    AGENT_VERSION = "1.0.0"
    PROMPT_KEY = "data-agent@v1.0.0"
    TOOLS_CONFIG = {
        "get_weather": get_weather,
        "get_time": get_time,
        "search": search_knowledge,
    }
```

**Result:** 82% code reduction while maintaining full functionality.

---

## Building Your First Agent

### Step 1: Define Tools

```python
# tools/my_tools.py
from velocity.sdk import tool

@tool(name="calculate", description="Perform math calculations")
async def calculate(expression: str) -> str:
    """Evaluate a mathematical expression safely."""
    try:
        result = eval(expression, {"__builtins__": {}})
        return f"Result: {result}"
    except Exception as e:
        return f"Error: {e}"

@tool(name="search", description="Search knowledge base")
async def search(query: str) -> str:
    """Search for information."""
    # Implementation...
    return results
```

### Step 2: Create Base Agent Class

```python
# agents/base.py
from velocity.sdk import AgentBase, AgentContext

class MinimalAgent(AgentBase):
    TOOLS_CONFIG: dict[str, callable] = {}
    
    def tools(self) -> list[dict]:
        return [
            tool.__tool_metadata__.to_llm_schema() 
            for tool in self.TOOLS_CONFIG.values()
        ]
    
    async def execute_tool(self, name: str, inputs: dict, ctx: AgentContext):
        if name in self.TOOLS_CONFIG:
            return await self.TOOLS_CONFIG[name](**inputs)
        raise ValueError(f"Unknown tool: {name}")
```

### Step 3: Implement Your Agent

```python
# agents/calculator_agent.py
from .base import MinimalAgent
from tools.my_tools import calculate, search

class CalculatorAgent(MinimalAgent):
    AGENT_ID = "calculator"
    AGENT_VERSION = "1.0.0"
    PROMPT_KEY = "calculator@v1.0.0"
    
    TOOLS_CONFIG = {
        "calculate": calculate,
        "search": search,
    }
    
    def system_prompt(self) -> str:
        return """You are a helpful math assistant.
        
You can:
- Use 'calculate' to perform mathematical operations
- Use 'search' to find mathematical concepts and definitions

Always show your work and explain your reasoning."""
```

### Step 4: Create Prompt (Optional)

```yaml
# prompts/calculator/v1.0.0.yaml
messages:
  - role: system
    content: |
      You are a helpful math assistant who explains your reasoning.
      
      When calculating:
      1. Break down the problem
      2. Use the calculate tool
      3. Explain the result
      
      Be precise and educational.
```

### Step 5: Run the Agent

```python
# run.py
import asyncio
from velocity.core.engine import AgentEngine
from velocity.core.llm_gateway import LLMGateway
from velocity.infra.providers.factory import create_all_providers
from velocity.config import get_config
from agents import CalculatorAgent

async def main():
    config = get_config()
    
    # Setup platform services
    providers = create_all_providers(config.llm.providers)
    gateway = LLMGateway(
        providers=providers,
        default_provider=config.llm.default_provider
    )
    
    engine = AgentEngine(llm_gateway=gateway)
    
    # Run agent
    result = await engine.run(
        agent=CalculatorAgent(),
        payload="What is 25 * 4 + 10?",
        tenant_id="demo",
        request_id="req-1"
    )
    
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Advanced Patterns

### Pattern 1: Using Global Tool Registry

Instead of defining tools locally, register them globally:

```python
# tools/__init__.py
from velocity.tools import ToolRegistry

# Tools auto-register via @tool decorator
# Just import them to trigger registration

from .calculations import calculate
from .search import search

# agents/my_agent.py
class MyAgent(AgentBase):
    AGENT_ID = "my-agent"
    global_tools = ["calculate", "search"]  # Reference by name!
    
    def tools(self) -> list[dict]:
        registry = ToolRegistry()
        return [
            registry.get_schema(tool_name)
            for tool_name in self.global_tools
        ]
    
    async def execute_tool(self, name: str, inputs: dict, ctx: AgentContext):
        registry = ToolRegistry()
        return await registry.execute(name, inputs, ctx)
```

### Pattern 2: Custom Lifecycle Hooks

Add domain-specific logic:

```python
class SmartAgent(MinimalAgent):
    async def on_before_llm_call(self, messages, ctx):
        # Inject few-shot examples for better performance
        if len(messages) == 1:  # First turn
            messages.append({
                "role": "user",
                "content": "Example: What is 2+2?"
            })
            messages.append({
                "role": "assistant",
                "content": "I'll calculate that for you. Let me use the calculate tool..."
            })
        return messages
    
    async def on_after_tool_call(self, tool_name, result, ctx):
        # Enrich tool result for better LLM understanding
        if tool_name == "search":
            return f"Search found: {result['top_3_results']}"
        return result
    
    async def on_final_result(self, result, ctx):
        # Add cost warning if expensive
        if ctx.cost_usd > 0.01:
            return f"{result}\n\n⚠️ Cost: ${ctx.cost_usd:.4f}"
        return result
    
    def parse_result(self, text, ctx):
        # Return structured output
        return {
            "response": text,
            "cost_usd": ctx.cost_usd,
            "iterations": ctx.iteration
        }
```

### Pattern 3: Multi-Agent Workflow

Orchestrate multiple agents:

```python
# run.py
from velocity.orchestration.workflow import DAGOrchestrator, WorkflowTask

async def run_workflow():
    engine = AgentEngine(llm_gateway=gateway)
    orchestrator = DAGOrchestrator(engine=engine)
    
    # Define workflow
    orchestrator.add_task(
        WorkflowTask(
            id="analyze",
            agent=AnalysisAgent(),
            dependencies=[]  # No dependencies
        )
    )
    orchestrator.add_task(
        WorkflowTask(
            id="write",
            agent=WriterAgent(),
            dependencies=["analyze"]  # Depends on analyze
        )
    )
    orchestrator.add_task(
        WorkflowTask(
            id="review",
            agent=ReviewerAgent(),
            dependencies=["write"]
        )
    )
    
    # Run workflow (platform handles topological sorting)
    results = await orchestrator.run(
        initial_payload={"data": "..."},
        tenant_id="tenant-1",
        request_id="req-1"
    )
    
    return results
```

### Pattern 4: Session-Based Conversation

Multi-turn conversations with automatic memory:

```python
# run.py
import asyncio

async def multi_turn_conversation():
    engine = AgentEngine(llm_gateway=gateway)
    agent = ConverterAgent()
    session_id = "user-session-123"
    
    # Turn 1: User asks question
    result1 = await engine.run(
        agent=agent,
        payload="What units can you convert?",
        session_id=session_id,
        tenant_id="tenant-1",
        request_id="req-1"
    )
    print("Agent:", result1)
    
    # Turn 2: User asks follow-up (context auto-loaded!)
    result2 = await engine.run(
        agent=agent,
        payload="Convert 100 miles to kilometers",
        session_id=session_id,
        tenant_id="tenant-1",
        request_id="req-2"
    )
    print("Agent:", result2)
    
    # Turn 3: User references previous context
    result3 = await engine.run(
        agent=agent,
        payload="What about half that distance?",  # Refers to "100 miles"
        session_id=session_id,
        tenant_id="tenant-1",
        request_id="req-3"
    )
    print("Agent:", result3)
    # Agent automatically understands "that distance" = "100 miles"
```

---

## Configuration

### Platform Configuration

Create `platform_config.yaml` at project root:

```yaml
environment: dev

llm:
  default_provider: openai
  default_model: gpt-4o-mini
  providers:
    openai:
      api_key_env: OPENAI_API_KEY
    anthropic:
      api_key_env: ANTHROPIC_API_KEY
    groq:
      api_key_env: GROQ_API_KEY

infra:
  cache:
    backend: memory          # or redis
  database:
    backend: sqlite          # or postgresql
  object_store:
    backend: local          # or s3

observability:
  dev_logging:
    enabled: true
    verbose: false
  metrics:
    enabled: true
    prometheus_port: 8000
```

### Agent Configuration (Optional)

Create `agent_config.yaml` for agent-specific settings:

```yaml
agent_id: my-agent
version: 1.0.0

model: gpt-4o
max_tokens: 4096
temperature: 0.7

budget:
  daily_limit_usd: 10.0
  monthly_limit_usd: 100.0
  per_request_limit_usd: 0.50

rate_limits:
  requests_per_minute: 60
  requests_per_hour: 1000
  burst_multiplier: 1.5

security:
  detect_pii: true
  block_injection: true
  mask_output: true
  require_permissions: true

memory:
  use_short_term: true
  use_long_term: true
  use_episodic: false
```

---

## File Structure

### Recommended Project Layout

```
my-agent-project/
├── agents/
│   ├── __init__.py                 # Export all agents
│   ├── base.py                     # MinimalAgent base class
│   ├── my_agent.py                 # Your agent
│   └── other_agent.py
│
├── tools/
│   ├── __init__.py                 # Register/import tools
│   ├── my_tools.py                 # Agent-specific tools
│   └── other_tools.py
│
├── prompts/
│   ├── my-agent/
│   │   └── v1.0.0.yaml             # Prompt file
│   └── other-agent/
│       └── v1.0.0.yaml
│
├── tests/
│   ├── test_agents.py
│   └── test_tools.py
│
├── run.py                          # Main entry point
├── platform_config.yaml            # Platform configuration
├── agent_config.yaml               # Agent configuration (optional)
├── requirements.txt
├── .env                            # API keys (local only)
└── README.md
```

### Minimal Project Layout

If you just need one agent:

```
my-agent/
├── agent.py                        # Agent definition
├── tools.py                        # Tool definitions
├── prompts.yaml                    # Agent prompt
├── run.py                          # Execution script
└── platform_config.yaml            # Platform config
```

---

## Example Agents

### Example 1: Search Agent

```python
# tools.py
from velocity.sdk import tool

@tool(name="search", description="Search knowledge base")
async def search_kb(query: str) -> str:
    """Search the knowledge base for relevant information."""
    # Implementation...
    return results

# agent.py
from velocity.sdk import AgentBase, AgentContext

class SearchAgent(AgentBase):
    AGENT_ID = "search-agent"
    
    def system_prompt(self) -> str:
        return """You are a helpful search assistant.
        
You can search our knowledge base to find information.
Always cite your sources from the search results."""
    
    def tools(self) -> list[dict]:
        return [search_kb.__tool_metadata__.to_llm_schema()]
    
    async def execute_tool(self, name: str, inputs: dict, ctx: AgentContext):
        if name == "search":
            return await search_kb(**inputs)
        raise ValueError(f"Unknown tool: {name}")
```

### Example 2: Data Processing Pipeline

```python
# agents/base.py
from velocity.sdk import AgentBase

class MinimalAgent(AgentBase):
    TOOLS_CONFIG: dict = {}
    
    def tools(self) -> list[dict]:
        return [t.__tool_metadata__.to_llm_schema() for t in self.TOOLS_CONFIG.values()]
    
    async def execute_tool(self, name: str, inputs: dict, ctx):
        if name in self.TOOLS_CONFIG:
            return await self.TOOLS_CONFIG[name](**inputs)
        raise ValueError(f"Unknown tool: {name}")

# agents/extractor.py
from .base import MinimalAgent
from tools import extract_text, parse_json

class DataExtractorAgent(MinimalAgent):
    AGENT_ID = "data-extractor"
    PROMPT_KEY = "extractor@v1.0.0"
    TOOLS_CONFIG = {
        "extract_text": extract_text,
        "parse_json": parse_json,
    }
    
    def system_prompt(self) -> str:
        return "You extract structured data from unstructured content."

# agents/analyzer.py
from .base import MinimalAgent
from tools import calculate_stats, generate_report

class DataAnalyzerAgent(MinimalAgent):
    AGENT_ID = "data-analyzer"
    PROMPT_KEY = "analyzer@v1.0.0"
    TOOLS_CONFIG = {
        "calculate_stats": calculate_stats,
        "generate_report": generate_report,
    }
    
    def system_prompt(self) -> str:
        return "You analyze structured data and generate insights."

# run.py
from velocity.orchestration.workflow import DAGOrchestrator, WorkflowTask

async def main():
    engine = AgentEngine(llm_gateway=gateway)
    dag = DAGOrchestrator(engine)
    
    # Extract → Analyze → Report
    dag.add_task(WorkflowTask("extract", DataExtractorAgent(), []))
    dag.add_task(WorkflowTask("analyze", DataAnalyzerAgent(), ["extract"]))
    
    results = await dag.run(
        initial_payload={"file": "data.txt"},
        tenant_id="tenant-1",
        request_id="req-1"
    )
```

### Example 3: Customer Support Agent

```python
# tools.py
from velocity.sdk import tool

@tool(name="search_faq", description="Search FAQ database")
async def search_faq(question: str) -> str:
    """Find matching FAQs."""
    return faq_results

@tool(name="create_ticket", description="Create support ticket")
async def create_ticket(title: str, description: str) -> str:
    """Create a support ticket."""
    return ticket_id

# agent.py
class SupportAgent(AgentBase):
    AGENT_ID = "support-agent"
    
    def system_prompt(self) -> str:
        return """You are a helpful customer support agent.
        
Your job is to:
1. Try to help customers using FAQ search
2. If the FAQ doesn't answer, create a support ticket
3. Always be polite and professional
4. Summarize the issue clearly in tickets"""
    
    def tools(self) -> list[dict]:
        return [
            search_faq.__tool_metadata__.to_llm_schema(),
            create_ticket.__tool_metadata__.to_llm_schema(),
        ]
    
    async def execute_tool(self, name: str, inputs: dict, ctx):
        if name == "search_faq":
            return await search_faq(**inputs)
        if name == "create_ticket":
            return await create_ticket(**inputs)
        raise ValueError(f"Unknown tool: {name}")
```

---

## Key Takeaways

1. **Platform Provides Plumbing:** LLM calls, tool execution, memory, security, metrics, budget - all handled automatically

2. **You Implement Logic:** System prompt, tool definitions, tool execution routing, and optional hooks

3. **Use Base Classes:** Eliminate duplication by creating a `MinimalAgent` base class for common patterns

4. **Configuration Over Code:** Swap backends, add providers, or enable features via configuration without changing agent code

5. **Minimal Code = Maximum Leverage:** A production-ready agent can be as simple as:
   ```python
   class MyAgent(MinimalAgent):
       AGENT_ID = "my-agent"
       TOOLS_CONFIG = {...}
       def system_prompt(self): return "..."
   ```

6. **Platform Handles These Problems:**
   - Provider lock-in (LLMGateway)
   - Resilience (retries, circuit breakers)
   - Cost control (budgeting, token tracking)
   - Data privacy (PII detection)
   - Session memory (auto load/save)
   - Observability (metrics, logs, traces)
   - Scaling (stateless API, DB abstraction)
   - RBAC (permission checking)

7. **Test Locally, Deploy Globally:** Use local SQLite/memory cache for development, swap to PostgreSQL/Redis in production with config change only

---

## Next Steps

1. Read `agents/base.py` in the showcase-agent for concrete example
2. Copy the pattern to your project
3. Define your tools with `@tool` decorator
4. Implement your agent by inheriting `MinimalAgent`
5. Run locally with `python run.py`
6. Deploy via REST API without code changes

For detailed API documentation, see the platform's source code:
- `src/velocity/sdk.py` - Core interfaces
- `src/velocity/core/engine.py` - Agent execution engine
- `src/velocity/tools/` - Tool system
- `src/velocity/services/` - Security, validation, audit, etc.

