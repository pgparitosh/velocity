# Versioned Prompt Management

This showcase agent demonstrates the Velocity platform's production-grade prompt management system.

## Architecture

The agent uses the platform's **three-tier caching architecture** for prompts:

```
L1: In-Memory Dictionary (local node)
    ↓
L2: Redis Cache (shared across nodes) - optional
    ↓
L3: Storage Backend (Filesystem/S3 - immutable)
```

## Prompt Structure

### Directory Layout

```
prompts/
└── showcase-agent/
    ├── v1.0.0.yaml          # Specific version
    └── latest.yaml          # Latest version (copy of v1.0.0)
```

### Prompt File Format (YAML)

Each prompt file contains:

```yaml
prompt_id: showcase-agent           # Unique identifier
version: v1.0.0                     # Semantic version
content: |                          # Actual prompt template
  You are the Showcase Agent...
  {variable_name} will be injected

author: velocity-platform           # Creator for audit trail
changelog: "Description of changes" # Version history
model_hint: openai/gpt-oss-120b     # Preferred LLM model
eval_score: null                    # A/B testing metric

variables:                          # List of {placeholders}
  - agent_id
  - agent_version
  - request_id
  - session_id

metadata:                           # Custom descriptors
  purpose: platform-demonstration
  domain: general
  team: platform
```

## How It Works

### 1. Initialization (run.py)

```python
# Initialize FilePromptBackend with local storage
prompt_backend = FilePromptBackend(root_dir="./prompts")

# Create PromptLibrary with caching
prompt_library = PromptLibrary(
    storage_backend=prompt_backend,
    cache_backend=None,  # No Redis in demo
    l2_ttl_seconds=3600,
)

# Inject into agent via dependency injection
agent = ShowcaseAgent(prompt_library=prompt_library)
```

### 2. Agent Integration (agent.py)

The agent declares a version-pinned prompt reference:

```python
class ShowcaseAgent(AgentBase):
    PROMPT_REFERENCE = "showcase-agent@v1.0.0"  # Pin specific version
    
    def __init__(self, prompt_library: PromptLibrary):
        self.prompt_library = prompt_library
```

### 3. Dynamic Resolution (on_before_llm_call hook)

Before each LLM call, the agent resolves the versioned prompt with context variables:

```python
async def on_before_llm_call(self, messages: List[dict], ctx: AgentContext):
    # Resolve prompt with context-specific variables
    self._resolved_prompt = await self.prompt_library.resolve(
        reference="showcase-agent@v1.0.0",
        variables={
            "agent_id": "showcase-agent",
            "agent_version": "1.0.0",
            "request_id": ctx.request_id,
            "session_id": ctx.session_id,
        }
    )
    
    # Replace system message with resolved prompt
    if messages and messages[0].get("role") == "system":
        messages[0]["content"] = self._resolved_prompt
    
    return messages
```

## Key Features Demonstrated

### 1. **Versioning**
- Prompts are immutable once created
- Semantic versioning support (v1.0.0, v1.1.0, etc.)
- "latest" alias points to current version

### 2. **Caching**
- L1 in-memory cache prevents repeated filesystem I/O
- L2 Redis cache for multi-node deployments
- Configurable TTL for cache invalidation

### 3. **Dynamic Variables**
- Prompts use `{placeholder}` syntax for template variables
- Variables are injected at runtime based on context
- Example: `{request_id}`, `{session_id}`, `{agent_version}`

### 4. **Audit Trail**
- Author information stored with each version
- Changelog documents what changed between versions
- Metadata for categorization and A/B testing

### 5. **Multi-Backend Support**
- `FilePromptBackend` - Local filesystem (development)
- `S3PromptBackend` - AWS S3 or compatible object store (production)
- Extensible interface for custom backends

## Production Considerations

### Configuration

In `platform_config.yaml`:

```yaml
infra:
  cache:
    backend: redis          # Enable Redis caching
    ttl_seconds: 3600
  object_store:
    backend: s3             # Use S3 for production
    bucket: velocity-prompts
    region: us-east-1
```

### Multi-Version Strategy

For production, maintain multiple prompt versions:

```
prompts/
└── fraud-detection/
    ├── v1.0.0.yaml       # Original baseline
    ├── v1.1.0.yaml       # Bug fixes
    ├── v2.0.0.yaml       # Major improvement
    └── latest.yaml       # Points to v2.0.0
```

### A/B Testing

Use `eval_score` metadata for testing different versions:

```python
# Load specific version for experiment
prompt_v1 = await library.resolve("fraud-detection@v1.0.0")
prompt_v2 = await library.resolve("fraud-detection@v2.0.0")

# Track which version used in each request
ctx.metadata["prompt_version"] = "v2.0.0"
ctx.metadata["eval_score"] = 0.94
```

### Deployment Workflow

1. **Create new prompt version**
   ```bash
   cp prompts/fraud-detection/v1.0.0.yaml \
      prompts/fraud-detection/v1.1.0.yaml
   # Edit v1.1.0.yaml
   ```

2. **Update agent to use new version**
   ```python
   PROMPT_REFERENCE = "fraud-detection@v1.1.0"
   ```

3. **Deploy and monitor**
   - New agent instances use v1.1.0
   - Old instances continue with v1.0.0 (if pinned)
   - Gradual rollout reduces blast radius

## Error Handling

The agent handles prompt resolution failures gracefully:

```python
try:
    self._resolved_prompt = await self.prompt_library.resolve(
        reference=self.PROMPT_REFERENCE,
        variables={...}
    )
except Exception as e:
    logger.warning(f"Failed to load versioned prompt: {e}. Using fallback.")
    self._resolved_prompt = "You are a helpful AI assistant."
```

## Benefits

1. **Version Control** - Track prompt changes over time
2. **Zero-Downtime Rollback** - Switch versions instantly
3. **A/B Testing** - Compare prompt performance
4. **Audit Compliance** - Author and changelog for governance
5. **Performance** - Multi-tier caching for low-latency access
6. **Scalability** - S3 backend for distributed deployments

## References

- **Platform Service**: `velocity.prompts.PromptLibrary`
- **Storage Interface**: `velocity.prompts.backends.IPromptBackend`
- **Local Backend**: `velocity.prompts.backends.FilePromptBackend`
- **Cloud Backend**: `velocity.prompts.backends.S3PromptBackend`
- **Data Model**: `velocity.prompts.models.PromptVersion`

## Testing

The agent logs all prompt resolutions for monitoring:

```
Resolved prompt: showcase-agent@v1.0.0
```

This allows you to verify which prompt version is active in each request's execution logs.
