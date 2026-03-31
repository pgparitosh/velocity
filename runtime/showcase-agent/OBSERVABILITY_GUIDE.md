# Platform-Provided Observability & Auditing

## Overview

The Velocity platform provides **comprehensive built-in observability** for all agent operations. Agents **do not need to include manual logging** - the platform automatically captures:

- **Metrics**: Requests, latency, costs, tokens, tool calls, model selection
- **Audit Logs**: Complete execution trail with all metadata
- **Security Events**: PII detection, validation, injection attempts
- **Cost Tracking**: Token counting, USD cost calculation, budget enforcement
- **Request Tracing**: Correlation IDs for distributed tracing

## Architecture

### Platform Observability Stack

```
Agent Execution
    ↓
[AgentContext] ← Automatically tracks metrics
    ↓
    ├─→ [MetricsService] → [Logger with structured metrics]
    │       ↓
    │   [MetricsMiddleware] (hooks after each execution)
    │       ↓
    │   metric=platform_agent_requests_total agent=X tenant=Y status=SUCCESS
    │   metric=platform_agent_latency_ms agent=X value=234
    │   metric=platform_agent_cost_usd_total agent=X value=0.0045
    │   metric=platform_tokens_total agent=X model=Y type=input value=412
    │
    └─→ [AuditLogger] → [Persistence]
            ↓
        ├─→ PostgreSQL: velocity_audit_logs table
        ├─→ S3: audit/{tenant}/{agent}/{request}.json (WORM)
        └─→ Event Stream: velocity.audit.completed topic
```

## Automatic Metrics Collection

The platform automatically records these metrics **without any agent code involvement**:

### 1. Request Metrics
```
metric=platform_agent_requests_total 
  agent=showcase-agent 
  tenant=demo-tenant 
  status=SUCCESS
```
- Tracks every agent invocation
- Status: SUCCESS, ERROR, or TIMEOUT
- Per-agent and per-tenant visibility

### 2. Latency Metrics
```
metric=platform_agent_latency_ms 
  agent=showcase-agent 
  value=234.567
```
- End-to-end execution time
- Used for performance SLO tracking
- Distribution available for percentile analysis

### 3. Cost Metrics
```
metric=platform_agent_cost_usd_total 
  agent=showcase-agent 
  tenant=demo-tenant 
  value=0.00453
```
- Automatic token-to-cost calculation
- Uses provider-specific pricing
- Supports budget enforcement

### 4. Token Metrics
```
metric=platform_tokens_total 
  agent=showcase-agent 
  model=openai/gpt-oss-120b 
  type=input 
  value=412
metric=platform_tokens_total 
  agent=showcase-agent 
  model=openai/gpt-oss-120b 
  type=output 
  value=187
```
- Tracks input and output tokens separately
- Per-model breakdown
- Used for capacity planning

### 5. Tool Call Metrics
```
metric=platform_tool_calls_total 
  agent=showcase-agent 
  tool=get_current_time 
  status=success
metric=platform_tool_calls_total 
  agent=showcase-agent 
  tool=perform_calculation 
  status=success
```
- Success/failure rates per tool
- Tool utilization tracking
- Helps identify problematic tools

## Audit Logging

### What Gets Logged

Every agent session completion is logged with:

```json
{
  "request_id": "demo-req-001",
  "tenant_id": "demo-tenant",
  "agent_id": "showcase-agent",
  "session_id": "demo-session-001",
  "trace_id": "...distributed-tracing-id",
  
  "iteration": 3,
  "start_time": 1711875812.123,
  "end_time": 1711875815.456,
  "elapsed_ms": 3333.0,
  
  "metrics": {
    "llm_calls": 3,
    "tool_calls": 5,
    "input_tokens": 1247,
    "output_tokens": 534,
    "cost_usd": 0.00891
  },
  
  "tags": {
    "task_type": "general",
    "priority": "normal"
  },
  
  "events": [
    {
      "type": "security_masking",
      "entities_found": 2,
      "entity_types": ["email", "phone"]
    }
  ],
  
  "status": "SUCCESS",
  "error_msg": null
}
```

### Storage Backends

#### 1. PostgreSQL (Best for Queries)
```sql
SELECT request_id, agent_id, elapsed_ms, cost_usd
FROM velocity_audit_logs
WHERE tenant_id = 'demo-tenant' 
  AND created_at > NOW() - INTERVAL '7 days'
ORDER BY created_at DESC;
```
- Full-text search support
- Fast filtering and aggregation
- Ideal for compliance queries

#### 2. S3 WORM (Write-Once-Read-Many)
```
s3://audit-bucket/
  audit/
    demo-tenant/
      showcase-agent/
        demo-req-001.json
        demo-req-002.json
        demo-req-003.json
```
- Immutable compliance archive
- No query support (archival only)
- Perfect for regulatory requirements

#### 3. Event Stream (Real-time)
```
Topic: velocity.audit.completed
Payload: Same JSON structure above
```
- Real-time event processing
- Stream to data lake, SIEM, etc.
- For real-time dashboards and alerts

## Implementation in Showcase Agent

### No Manual Logging Needed

The agent code **does not include logger.info() calls** for observability:

```python
# BEFORE (manual logging):
async def execute_tool(self, name: str, inputs: dict, ctx: AgentContext) -> Any:
    logger.info(f"Executing tool '{name}'")  # ← Manual logging
    result = await tool_map[name](**inputs)
    logger.info(f"Tool '{name}' executed successfully")  # ← Manual logging
    return result

# AFTER (platform handles it):
async def execute_tool(self, name: str, inputs: dict, ctx: AgentContext) -> Any:
    # No logging needed - platform records:
    # - Tool invocation
    # - Success/failure
    # - Latency
    # - Any errors
    result = await tool_map[name](**inputs)
    return result
```

### Platform Integration Points

The platform automatically hooks into these execution points:

1. **LLMGateway.call()** - Records LLM metrics
   - Model and provider
   - Input/output tokens
   - Latency
   - Cost

2. **AgentEngine._execute_single_tool()** - Records tool metrics
   - Tool name
   - Success/failure
   - Latency
   - Exceptions

3. **AuditLogger.log_session_completion()** - Records full audit trail
   - Called after execution completes
   - Writes to all configured backends
   - Includes all context metadata

4. **MetricsMiddleware.after_run()** - Emits structured metrics
   - Called after execution
   - Extracts metrics from AgentContext
   - Emits to logger (Prometheus in production)

## Configuration

### Enable/Disable Audit Backends

In `platform_config.yaml`:

```yaml
services:
  audit:
    backends:
      postgresql:
        enabled: true
        connection_string: postgresql://localhost/velocity
      
      s3:
        enabled: true
        bucket: company-audit-logs
        region: us-west-2
      
      event_stream:
        enabled: true
        broker: kafka://kafka:9092
        topic: velocity.audit.completed
    
    retention_years: 7  # GDPR/HIPAA compliance
```

### Metrics Output Configuration

```yaml
observability:
  metrics:
    format: structured_logs  # or 'prometheus' in production
    log_level: INFO          # Only log metrics, not debug logs
    
  tracing:
    enabled: true
    sample_rate: 1.0         # 100% sampling (adjust in production)
    exporter: jaeger         # or 'datadog', 'honeycomb', etc.
```

## Accessing Audit Data

### Development (Query PostgreSQL)

```python
from velocity.services.audit.logger import AuditLogger
from velocity.infra import PostgreSQLBackend

backend = PostgreSQLBackend(connection_string=...)
records = await backend.query_records(
    tenant_id="demo-tenant",
    agent_id="showcase-agent",
    limit=100
)

for record in records:
    print(f"Request {record['request_id']}: {record['status']}")
    print(f"  Cost: ${record['metrics']['cost_usd']:.4f}")
    print(f"  Tokens: {record['metrics']['input_tokens']} in, "
          f"{record['metrics']['output_tokens']} out")
    print(f"  Latency: {record['elapsed_ms']:.0f}ms")
```

### Production (Query Data Lake)

```sql
-- Athena/BigQuery query
SELECT 
  date(created_at) as execution_date,
  agent_id,
  COUNT(*) as invocations,
  AVG(CAST(metrics.cost_usd AS DOUBLE)) as avg_cost_per_request,
  SUM(CAST(metrics.input_tokens AS BIGINT)) as total_input_tokens,
  SUM(CAST(metrics.output_tokens AS BIGINT)) as total_output_tokens
FROM velocity_audit_logs
WHERE tenant_id = 'demo-tenant'
  AND created_at >= DATE_SUB(CURRENT_DATE, INTERVAL 30 DAY)
  AND status = 'SUCCESS'
GROUP BY 1, 2
ORDER BY 1 DESC, 3 DESC;
```

### Real-time (Stream Processing)

```python
# Subscribe to audit events
kafka_stream = KafkaConsumer('velocity.audit.completed')

for message in kafka_stream:
    audit_record = json.loads(message.value)
    
    # Update real-time dashboards
    update_cost_dashboard(audit_record['metrics']['cost_usd'])
    
    # Trigger alerts if needed
    if audit_record['metrics']['cost_usd'] > 1.00:
        send_alert(f"High cost request: {audit_record['request_id']}")
```

## Security & Compliance

### PII Detection & Masking

Platform automatically detects and masks:
- Social Security Numbers (SSN)
- Credit Card numbers
- Email addresses
- Phone numbers
- Personal names (optional)

Recorded in audit logs as:
```json
{
  "events": [
    {
      "type": "security_masking",
      "entities_found": 3,
      "entity_types": ["ssn", "email", "phone"],
      "request_id": "demo-req-001"
    }
  ]
}
```

### Request Tracing

Full distributed tracing support:
```
request_id: demo-req-001          ← API request identifier
session_id: demo-session-001      ← User session across turns
trace_id: d90c4917-...            ← Distributed tracing ID
parent_request_id: demo-req-000   ← Parent request (if nested)
```

Used to:
- Correlate logs across services
- Track request lifecycle
- Debug multi-step workflows
- Implement rate limiting per session

## Best Practices

### 1. Don't Log Manually
✗ BAD:
```python
logger.info(f"Tool execution: {tool_name}")
logger.info(f"Cost: {cost_usd}")
```

✓ GOOD:
```python
# Platform logs automatically
result = await tool_map[tool_name](**inputs)
return result
```

### 2. Use AgentContext Tags for Custom Metadata
✗ BAD:
```python
logger.info(f"priority={priority}")  # Lost if manual logging disabled
```

✓ GOOD:
```python
ctx.tags["priority"] = priority  # Automatically persisted in audit trail
ctx.tags["user_segment"] = "premium"
ctx.tags["experiment_group"] = "variant_b"
```

### 3. Rely on Automatic Cost Tracking
✗ BAD:
```python
estimated_cost = tokens * RATE
logger.info(f"Estimated cost: {estimated_cost}")
```

✓ GOOD:
```python
# Platform calculates exact cost from provider responses
# Accurate to token and provider pricing
```

### 4. Use Request IDs for Debugging
✓ GOOD:
```python
# Share request_id with users for support
print(f"Your request ID: {ctx.request_id}")
print(f"Trace this request: https://dashboard.example.com/trace/{ctx.request_id}")
```

## Metrics in Production

### Prometheus Export

In production, MetricsService emits to Prometheus:

```promql
# Query: Total requests by agent
sum by (agent) (rate(platform_agent_requests_total[5m]))

# Query: Average latency by agent
histogram_quantile(0.95, 
  sum by (agent) (rate(platform_agent_latency_ms_bucket[5m]))
)

# Query: Total cost breakdown
sum by (agent, tenant) (platform_agent_cost_usd_total)

# Query: Token consumption trend
sum by (agent, type) (rate(platform_tokens_total[5m]))
```

### Grafana Dashboards

Pre-built dashboards available:
- Agent Performance (latency, requests, errors)
- Cost Analysis (by agent, tenant, model)
- Token Consumption (input/output breakdown)
- Tool Execution (success rates, latencies)
- Security Events (PII detections, injections blocked)

## Troubleshooting

### Missing Metrics

If metrics aren't appearing:

1. Check MetricsService initialization
2. Verify MetricsMiddleware is registered
3. Check logging level (should be INFO)
4. Inspect logger output for metric lines

### Audit Logs Not Persisting

1. Verify AuditLogger backends are configured
2. Check database connectivity (PostgreSQL)
3. Verify S3 permissions (S3 backend)
4. Check message broker connectivity (Event Stream)

### High Audit Log Volume

1. Consider sampling for dev environments
2. Archive older logs to S3
3. Use retention policies (default 7 years)
4. Filter by tenant for specific analysis

## References

- **MetricsService**: `velocity.observability.metrics.MetricsService`
- **MetricsMiddleware**: `velocity.observability.middleware.MetricsMiddleware`
- **AuditLogger**: `velocity.services.audit.logger.AuditLogger`
- **AgentContext**: `velocity.core.context.AgentContext`
- **Configuration**: `platform_config.yaml` (infra, services sections)
