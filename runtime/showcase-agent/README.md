# Velocity Showcase Agent

A comprehensive demonstration of the Velocity AI Agent Platform's capabilities, featuring:

- **Versioned Prompt Management**: Demonstrates the PromptLibrary with 3-tier caching (memory, Redis, storage)
- **Platform-Level Development Observability**: Automatic human-readable console logging in dev environments (no agent code needed)
- **Automatic Metrics Collection**: Platform-provided metrics without agent instrumentation
- **Production-Ready Architecture**: Clean separation between agent logic and platform observability
- **Multiple Tool Integration**: 8 production-ready tools with proper error handling
- **Extensible Design**: Works with any agent - dev observability is a platform capability

## Quick Start

### Prerequisites

- Python 3.10+
- Velocity platform installed and configured
- GROQ API key in `.env` file

### Running the Agent

```bash
# Run with platform dev observability enabled (default in dev environment)
python run.py

# Run WITHOUT dev observability console output
export VELOCITY_DEV_LOGGING=false
python run.py

# Run with verbose output (show detailed inputs/outputs)
export VELOCITY_DEV_LOGGING_VERBOSE=true
python run.py
```

## Platform-Level Development Observability

The Velocity platform now provides **development observability as a core platform capability**. This means:

### Key Benefits

1. **Works with ANY Agent**: No agent-specific code or configuration needed
2. **Zero Instrumentation**: Agent code stays clean - platform handles all logging automatically
3. **Easy Toggle**: Enable/disable via environment variable or config file
4. **Human-Readable Output**: Formatted console logging perfect for development debugging
5. **Real-Time Metrics**: Actual LLM calls, tokens, costs, and latencies logged immediately

### How It Works

```
Agent Execution:
  ↓
AgentEngine.run() executes
  ├── Records metrics in AgentContext (tokens, cost, latency, tool calls)
  └── Marks execution as complete
  ↓
MetricsMiddleware.after_run() is called
  ├── Logs structured metrics (key=value pairs)
  └── Calls DevObservabilityPlugin.after_run() if enabled
  ↓
DevObservabilityPlugin logs to console:
  ├── All LLM calls (model, tokens, cost, latency)
  ├── All tool calls (name, success, latency)
  ├── Execution context and metrics
  └── Session summary
```

### Configuration

**Option 1: Environment Variables** (highest priority)
```bash
# Enable dev observability
export VELOCITY_DEV_LOGGING=true

# Disable dev observability
export VELOCITY_DEV_LOGGING=false

# Enable verbose output (shows inputs/outputs)
export VELOCITY_DEV_LOGGING_VERBOSE=true
```

**Option 2: platform_config.yaml**
```yaml
# Velocity Platform Configuration
environment: dev

observability:
  dev_logging:
    enabled: true          # Enable dev console logging
    verbose: false         # Show detailed inputs/outputs
```

### Console Output Example

```
================================================================================
[EXECUTION 1]
================================================================================
  [LLM] Model: openai/gpt-oss-120b
        Input tokens:  634
        Output tokens: 35
        Total tokens:  669
        Cost: $0.000000
        Latency: 969ms
        
  [TOOL] [+] get_current_time
         Status: SUCCESS
         Latency: 0ms

────────────────────────────────────────────────────────────────────────────────
EXECUTION SUMMARY
────────────────────────────────────────────────────────────────────────────────

[Request Details]
  Request ID: dev-demo-01
  Agent ID: showcase-agent
  Tenant ID: demo-tenant
  Session ID: dev-demo-001
  Iteration: 2

[Execution Metrics]
  LLM Calls: 2
  Tool Calls: 1

[Token Usage]
  Input Tokens: 1,334
  Output Tokens: 78
  Total Tokens: 1,412

[Cost & Performance]
  Total Cost: $0.000000
  Total Latency: 3282ms
```

## Architecture

### Agent Components

1. **agent.py**: ShowcaseAgent implementation
   - Tools: Time, calculations, weather, knowledge base search, random numbers, system health, formatting, word counting
   - Hooks: Prompt resolution, tool execution, error handling
   - **No observability code needed** - platform handles it automatically

2. **tools.py**: Production-ready tool definitions
   - Each tool uses `@tool` decorator with metadata
   - Proper error handling and validation
   - Async execution support

3. **run.py**: Main runner
   - Initializes platform services (MetricsService, DevObservabilityPlugin, AuditLogger)
   - Creates engine with middleware (automatic observability)
   - Runs 3 demonstration scenarios
   - **No agent-specific callbacks or wrappers needed**

### Platform Services

1. **MetricsService**: Records performance metrics
   - Requests, latency, cost, tokens, tool calls
   - Structured logging to logger

2. **MetricsMiddleware**: Hooks into execution lifecycle
   - Extracts metrics from AgentContext
   - Calls dev observability plugin if enabled

3. **DevObservabilityPlugin**: Platform-level dev logging
   - Logs real-time metrics to console
   - Works with any agent automatically
   - Configurable via environment variables

### Prompt Management

Versioned prompts are stored in `prompts/showcase-agent/`:
- `v1.0.0.yaml`: Full versioned prompt with template variables
- `latest.yaml`: Alias to the latest version

The agent uses `PromptLibrary` to resolve prompts at runtime with context variables.

See [PROMPT_MANAGEMENT.md](PROMPT_MANAGEMENT.md) for detailed documentation.

## Available Tools

The agent has access to 8 tools:

| Tool | Description | Example |
|------|-------------|---------|
| `get_current_time` | Returns current date/time | "What time is it?" |
| `perform_calculation` | Performs arithmetic operations | "Calculate 15 + 27" |
| `get_weather_data` | Retrieves weather information | "What's the weather in London?" |
| `search_knowledge_base` | Searches a knowledge base | "Find information about AI" |
| `generate_random_number` | Generates random numbers | "Pick a random number" |
| `system_health_check` | Checks system status | "Is the system healthy?" |
| `format_data_as_json` | Formats data as JSON | "Convert to JSON" |
| `count_words` | Counts words in text | "How many words?" |

## Demonstration Scenarios

The runner executes 3 scenarios to showcase the platform's capabilities:

1. **Time Query**: "What time is it right now?"
   - Demonstrates simple tool usage
   - Single LLM call with tool execution

2. **Math Calculation**: "Calculate 15 + 27 and multiply by 3"
   - Demonstrates multi-step reasoning
   - Multiple LLM calls and tool invocations

3. **Weather**: "What's the weather in London?"
   - Demonstrates context-aware responses
   - Tool execution with realistic latency

## Key Differences from Agent-Specific Observability

**Old Approach (Agent-Specific):**
- Required custom dev_observability.py file in each agent directory
- Needed context callbacks in agent code
- Not reusable across agents
- Extra complexity for agents

**New Approach (Platform-Level):**
- ✅ Single DevObservabilityPlugin in platform
- ✅ Works automatically with any agent
- ✅ Integrated with MetricsMiddleware
- ✅ No agent code changes needed
- ✅ Configured via platform_config.yaml or environment variables
- ✅ Scales to unlimited agents without duplication

## Environment Variables

```bash
# Enable/disable dev observability
VELOCITY_DEV_LOGGING=true|false (default: true in dev environment)

# Enable verbose mode
VELOCITY_DEV_LOGGING_VERBOSE=true|false (default: false)

# LLM Configuration
GROQ_API_KEY=<your-api-key>
```

## File Structure

```
showcase-agent/
├── README.md                    # This file
├── agent.py                     # ShowcaseAgent (clean, no observability code)
├── tools.py                     # Tool definitions
├── run.py                       # Main runner (simple, no observability setup)
├── agent_config.yaml            # Agent configuration
├── PROMPT_MANAGEMENT.md         # Prompt versioning guide
├── OBSERVABILITY_GUIDE.md       # Platform observability documentation
└── prompts/
    └── showcase-agent/
        ├── v1.0.0.yaml          # Versioned prompt
        └── latest.yaml          # Latest version alias

Platform Services (automatically used):
src/velocity/observability/
├── metrics.py                   # MetricsService
├── middleware.py                # MetricsMiddleware
├── dev.py                       # DevObservabilityPlugin (NEW)
└── factory.py                   # Plugin factory (NEW)
```

## Development vs Production

### Development (environment: dev)
- **Dev Observability**: ON by default (toggle with VELOCITY_DEV_LOGGING)
- **Console Output**: Human-readable, formatted
- **Metrics**: Structured to logger (key=value pairs)
- **Use Case**: Debugging, development, testing

### Production (environment: prod)
- **Dev Observability**: Automatically OFF (not in dev environment)
- **Metrics**: Exported to Prometheus, Datadog, CloudWatch
- **Audit Trail**: Persisted to database, S3, or event streams
- **Use Case**: Monitoring, compliance, analytics

## Understanding the Platform Flow

The dev observability integrates seamlessly with the platform:

```
1. Agent initialization
   └── No observability configuration needed

2. Engine.run() executes agent
   ├── Creates AgentContext
   ├── Records LLM calls with tokens/cost/latency
   ├── Records tool calls with success/latency
   └── Marks execution complete

3. MetricsMiddleware.after_run() is called
   ├── Extracts metrics from context
   ├── Logs structured metrics via logger
   └── Calls DevObservabilityPlugin.after_run()

4. DevObservabilityPlugin (if enabled)
   ├── Logs all LLM calls to console
   ├── Logs all tool calls to console
   ├── Logs execution summary
   └── Accumulates session statistics

5. Response is returned to client
   └── All metrics automatically captured
```

## Troubleshooting

### Dev Observability Not Showing

Check the following in order:

1. **Environment is 'dev'**: `platform_config.yaml` must have `environment: dev`
2. **Dev logging enabled**: Check `VELOCITY_DEV_LOGGING` is not set to "false"
3. **Middleware is created**: Ensure `MetricsMiddleware` is initialized with dev plugin
4. **Engine has middleware**: Engine must be created with `middleware=metrics_middleware`

### Structured Metrics But No Console Output

This is normal when dev observability is disabled:
- `VELOCITY_DEV_LOGGING=false` will show only structured metrics
- The platform is still collecting all observability data
- Set `VELOCITY_DEV_LOGGING=true` to see formatted console output

### Missing LLM Calls

Ensure:
1. `GROQ_API_KEY` is set in `.env`
2. Network connectivity is available
3. Groq API quota is not exceeded

## Next Steps

1. **Use with your own agents**: Simply initialize with MetricsMiddleware containing dev plugin
2. **Configure per environment**: Use platform_config.yaml for production settings
3. **Monitor in production**: Connect to Prometheus, Datadog, or CloudWatch
4. **Integrate with other services**: Audit logger connects to database, S3, event streams

## References

- [Velocity Documentation](https://velocity.platform)
- [PROMPT_MANAGEMENT.md](PROMPT_MANAGEMENT.md) - Detailed prompt versioning guide
- [OBSERVABILITY_GUIDE.md](OBSERVABILITY_GUIDE.md) - Platform observability documentation
- Platform source: `src/velocity/observability/`
