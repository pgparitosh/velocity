# Tool Architecture: Visual Comparison

## Current State (Platform Ships Tools)

```
┌─────────────────────────────────────────────────────────┐
│         VELOCITY PLATFORM PACKAGE (monolithic)          │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │ CORE (Required)                                 │   │
│  │  - registry.py                                  │   │
│  │  - decorators.py                                │   │
│  │  - metadata.py                                  │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │ TOOLS (Bundled, Optional but included)          │   │
│  │  - basic/       (get_time, calc)                │   │
│  │  - data/        (weather, kb_search)            │   │
│  │  - formatting/  (json, word_count)              │   │
│  │  - system/      (health_check)                  │   │
│  │  - [Could grow to 50+ tools]                    │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
└─────────────────────────────────────────────────────────┘

Installation:
  pip install velocity

Agent Usage:
  from velocity.tools.library import get_current_time
  
Problem:
  - Platform grows with each tool
  - All tools released with platform
  - Breaking change in one tool affects all users
  - Dependency conflicts possible (AWS SDK, GCP SDK)
  - Hard to remove deprecated tools
```

---

## Recommended: Tool Ecosystem (Option 2)

```
┌──────────────────────────────────┐
│   VELOCITY PLATFORM (Small)      │
├──────────────────────────────────┤
│                                  │
│  ┌──────────────────────────┐   │
│  │ CORE ONLY (Required)     │   │
│  │  - registry.py           │   │
│  │  - decorators.py         │   │
│  │  - metadata.py (15 KB)   │   │
│  │  - schema_gen.py         │   │
│  │  - sdk.py with @tool     │   │
│  └──────────────────────────┘   │
│                                  │
└──────────────────────────────────┘
         │
         │ Extends via import
         │
    ┌────┴────────────────────────────────────────────┐
    │                                                  │
┌───▼──────────────────┐   ┌──────────────────────┐   │
│ VELOCITY-TOOLS-BASIC │   │ VELOCITY-TOOLS-AWS   │   │
├──────────────────────┤   ├──────────────────────┤   │
│ (Maintained by core) │   │ (AWS team maintains) │   │
│                      │   │                      │   │
│ - get_current_time   │   │ - s3_read/write      │   │
│ - perform_calc       │   │ - dynamodb_query     │   │
│ - format_json        │   │ - lambda_invoke      │   │
│ - count_words        │   │ - ec2_operations     │   │
└──────────────────────┘   └──────────────────────┘
         │                         │
         │ (pip install)           │ (pip install)
         │                         │
    ┌────┴──────────────────────┬──┴───────────────┐
    │                           │                  │
    v                           v                  v
┌─────────────────┐    ┌──────────────────┐  ┌──────────────┐
│ AGENT 1         │    │ AGENT 2          │  │ AGENT 3      │
├─────────────────┤    ├──────────────────┤  ├──────────────┤
│ requirements:   │    │ requirements:    │  │ requirements:│
│ - velocity      │    │ - velocity       │  │ - velocity   │
│ - velocity-     │    │ - velocity-      │  │ - velocity-  │
│   tools-basic   │    │   tools-basic    │  │   tools-aws  │
│                 │    │ - velocity-      │  │ - v-tools-   │
│ imports:        │    │   tools-aws      │  │   database   │
│ get_time,       │    │                  │  │              │
│ perform_calc    │    │ imports:         │  │ imports:     │
│                 │    │ get_time,        │  │ s3_read,     │
│                 │    │ s3_read          │  │ db_query     │
└─────────────────┘    └──────────────────┘  └──────────────┘

Installation:
  Agent 1: pip install velocity velocity-tools-basic
  Agent 2: pip install velocity velocity-tools-basic velocity-tools-aws
  Agent 3: pip install velocity velocity-tools-aws velocity-tools-database

Benefits:
  ✓ Platform stays small (15-20 KB core)
  ✓ Tools versioned independently
  ✓ Each team owns their tools
  ✓ No dependency conflicts
  ✓ Easy to add custom tools
  ✓ Community contributions scale
```

---

## Dependency Graph Comparison

### Option 1: Platform + Tools (Monolithic)

```
Agent
  │
  ├─ velocity[1.2.0]
  │   ├─ tools.registry
  │   ├─ tools.library
  │   │   ├─ basic (no extra deps)
  │   │   ├─ data → requests, httpx
  │   │   ├─ system → psutil, platform
  │   │   ├─ [if included: aws → boto3, botocore, urllib3]
  │   │   ├─ [if included: gcp → google-cloud-storage, grpc]
  │   │   └─ [if included: db → sqlalchemy, psycopg2, mysql.connector]
  │   └─ ...other platform deps
  │
Problem: All deps installed even if tools not used
Risk: boto3 update breaks your platform
Cost: Download 50MB for 100KB tool library
```

### Option 2: Platform + Tool Packages (Modular)

```
Agent 1 (basic):
  ├─ velocity[1.2.0]
  │   ├─ tools.registry
  │   └─ ...other platform deps
  │
  └─ velocity-tools-basic[1.0.0]
      ├─ get_current_time (no deps)
      └─ perform_calculation (no deps)

Agent 2 (with AWS):
  ├─ velocity[1.2.0]
  │   └─ ...platform deps
  │
  ├─ velocity-tools-basic[1.0.0]
  │
  └─ velocity-tools-aws[2.1.0]
      └─ boto3, botocore (only if you use it)

Benefits:
  ✓ Agent 1: Small footprint
  ✓ Agent 2: Explicitly declares what it needs
  ✓ Update aws tools independently
  ✓ Update platform independently
```

---

## Scenario: Breaking Change

### Scenario: AWS SDK Major Version Update (e.g., boto3 4.0)

#### Option 1: Monolithic (BAD)

```
Timeline:
  - boto3 4.0 released (breaking changes)
  - AWS SDK team updates velocity-tools-aws code
  - Must release velocity 1.3.0 (entire platform)
  - All users must upgrade platform even if they don't use AWS
  - Delay: 2-4 weeks for compatibility testing
  - Risk: One tool update forces full platform update
```

#### Option 2: Modular (GOOD)

```
Timeline:
  - boto3 4.0 released
  - AWS SDK team patches velocity-tools-aws[2.2.0]
  - Release immediately (independent package)
  - Only AWS users update their requirements
  - Other users unaffected
  - Delay: 2-3 days
  - Risk: Isolated to AWS tooling only
```

---

## Feature Velocity Comparison

### Option 1: New AWS Tools via Platform

```
1. AWS team develops tool (s3_batch_operations)
2. Submit PR to velocity platform repo
3. Code review by platform team (unfamiliar with AWS domain)
4. Integrate into src/velocity/tools/library/aws/
5. Update tests, docs
6. Wait for next platform release (1-2 months)
7. Ship in velocity 2.5.0

Time: 6-10 weeks
Pain: Blocking other tools
Risk: General platform review delays tool release
```

### Option 2: New AWS Tools via velocity-tools-aws

```
1. AWS team develops tool (s3_batch_operations)
2. Submit PR to velocity-tools-aws repo
3. Code review by AWS team (domain experts)
4. Ship as velocity-tools-aws[2.5.0]

Time: 1-2 weeks
Pain: None (independent team)
Risk: None (isolated package)
```

---

## Migration Strategy

### Step 1: Create Shim Layer (Backward Compatible)

```python
# src/velocity/tools/library/__init__.py
"""
Backward compatibility shim.
Tools are now in separate velocity-tools-* packages.
This re-exports for existing code.
"""

# Try new location first
try:
    from velocity_tools_basic import (
        get_current_time,
        perform_calculation,
        format_data_as_json,
        count_words,
    )
except ImportError:
    # Fallback for development
    from .basic import get_current_time, perform_calculation
    from .formatting import format_data_as_json, count_words

__all__ = [
    "get_current_time",
    "perform_calculation",
    "format_data_as_json",
    "count_words",
]

# Deprecation notice
import warnings
warnings.warn(
    "Importing from velocity.tools.library is deprecated. "
    "Use 'from velocity_tools_basic import ...' instead. "
    "This shim will be removed in velocity 2.0.",
    DeprecationWarning,
    stacklevel=2
)
```

### Step 2: Create velocity-tools-basic Package

```
velocity-tools-basic/
├── setup.py
├── README.md
├── src/velocity_tools_basic/
│   ├── __init__.py
│   ├── basic.py           (get_current_time, perform_calculation)
│   ├── formatting.py      (format_json, count_words)
│   └── data.py            (weather, kb_search)
├── tests/
│   └── test_tools.py
└── pyproject.toml
```

### Step 3: Update Agent Usage

```python
# Before
from velocity.tools.library import get_current_time

# After (preferred)
from velocity_tools_basic import get_current_time

# Still works (backward compat) but shows deprecation warning
from velocity.tools.library import get_current_time
```

### Step 4: Expand Ecosystem

```
velocity-tools-aws/
velocity-tools-gcp/
velocity-tools-database/
velocity-tools-http/
velocity-tools-enterprise/ (company-specific)
...
```

---

## Comparison Matrix

| Dimension | Option 1 (Monolithic) | Option 2 (Ecosystem) |
|-----------|----------------------|----------------------|
| **Platform Size** | 500+ KB | 20 KB |
| **Tool Update Speed** | 4-6 weeks (platform cycle) | 1-2 weeks (independent) |
| **Dependency Conflicts** | High (all tools included) | Low (explicit opt-in) |
| **Breaking Changes** | Force upgrade entire platform | Update only what you need |
| **Out-of-Box Experience** | Excellent (everything included) | Good (install what you need) |
| **Custom Tools** | Hard (must modify platform) | Easy (separate package) |
| **Community Contributions** | Difficult (large surface) | Easy (small surface) |
| **Testing Overhead** | Massive (test all tools) | Manageable (tool-specific) |
| **Deprecated Tools** | Stuck forever | Remove from maintenance |
| **Long-Term Maintenance** | High burden | Distributed |

---

## Recommendation: OPTION 2 with Fallback to Option 3

### Immediate: Extract Tools to Shim

Keep backward compatibility layer:
```
src/velocity/tools/library/  (re-exports from velocity-tools-basic)
  └─ Deprecation warnings
  └─ Falls back to local copies for dev
```

### Short-term: Create velocity-tools-basic

First separate package:
```
pip install velocity-tools-basic
from velocity_tools_basic import get_current_time
```

### Medium-term: Build Ecosystem

Start foundation packages:
```
velocity-tools-aws
velocity-tools-database
velocity-tools-http
```

### Long-term: Community Tools

Enable third-party:
```
company-internal-tools
industry-specific-tools
llm-provider-tools
```

### Fallback if Needed: Bundle Package

If users want "everything included":
```
pip install velocity[full]    # Installs all tools
pip install velocity[basic]   # Just essentials
pip install velocity[aws]     # Platform + AWS tools
```

This meta-package approach gives Claude Code experience for those who want it,
while keeping platform lean for those who don't.

---

## Summary

**Your instinct is correct:** Tools should sit outside the platform.

**Reasons (Per rules.txt):**
1. **Modularity:** Clear separation of concerns
2. **Scalability:** Add 1000 tools without platform bloat
3. **Maintainability:** Each tool owned by domain expert
4. **Long-term:** Avoid version coupling trap
5. **Security:** Update only what you use
6. **Ecosystem:** Support community contributions at scale

**Implementation:** Use Option 2 (Tools Outside) with backward compatibility shim
for 6-12 months, then Phase 1: Create velocity-tools-basic.
