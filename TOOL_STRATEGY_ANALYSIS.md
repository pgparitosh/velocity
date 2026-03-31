# Tool Strategy Analysis: Platform vs External

## Question
Should tools sit:
1. **Inside platform** (`src/velocity/tools/library/`) - ship with comprehensive suite
2. **Outside platform** (separate package/repo) - agents bring their own tools
3. **Hybrid approach** - core tools inside, extensible hooks outside

---

## Analysis Framework (Per rules.txt)

### 1. ARCHITECTURAL PRINCIPLE
- **Modularity:** How independent are tools from platform core?
- **Scalability:** How does tool count affect platform complexity?
- **Extensibility:** How easy is it to add custom/third-party tools?
- **Maintainability:** Who owns tool versions and breaking changes?

### 2. LONG-TERM MAINTAINABILITY PRIORITY
- Tool lifecycle independent of platform releases?
- Version compatibility matrix complexity?
- Dependency management strategy?
- Community contribution model?

---

## Option 1: Platform Ships with Comprehensive Tool Suite

### Structure
```
src/velocity/
├── tools/
│   ├── registry.py          (core - tool registration)
│   ├── decorators.py        (core - @tool decorator)
│   └── library/             (included tools - BIG directory)
│       ├── basic/
│       ├── data/
│       ├── formatting/
│       ├── system/
│       ├── network/
│       ├── file_ops/
│       ├── database/
│       ├── cloud/            ← AWS, GCP, Azure tools
│       ├── llm_integration/   ← Multi-model tools
│       ├── security/
│       └── ... 50+ tools
```

### Pros
✓ Zero setup for new agents (everything available immediately)
✓ Tools tested against platform SDK (quality gate)
✓ Consistent tool behavior across organization
✓ Like Claude Code - comprehensive out-of-box experience
✓ Discovery easier (centralized catalog)
✓ Version alignment (tools released with platform)

### Cons
✗ **Platform bloat:** Each release grows with new tools
✗ **Dependency hell:** Tools may have conflicting dependencies (AWS SDK, GCP, etc.)
✗ **Version coupling:** Can't use old tool version with new platform
✗ **Breaking changes:** Tool updates break agents unexpectedly
✗ **Cognitive load:** Massive tool library is overwhelming for users
✗ **Maintenance burden:** Platform team owns all tool bugs/security issues
✗ **Slow release cycles:** Can't patch a tool without full platform release
✗ **Difficult to deprecate:** Removing tools breaks existing agents
✗ **Testing overhead:** Platform test suite explodes
✗ **Opinionated:** Forces specific implementations on users

---

## Option 2: Tools Live Outside Platform (Recommended)

### Structure
```
velocity-platform/ (core)
├── src/velocity/
│   ├── tools/
│   │   ├── registry.py       (core - registration mechanism)
│   │   ├── decorators.py     (core - @tool decorator)
│   │   └── metadata.py       (core - metadata handling)
│   └── sdk.py                (agent SDK with @tool)

velocity-tools/ (separate repos)
├── velocity-tools-basic/     (maintained by core team)
│   ├── get_current_time
│   ├── perform_calculation
│   └── ...
│
├── velocity-tools-aws/       (AWS tools, owned by AWS team)
│   ├── s3_operations
│   ├── dynamodb_query
│   └── ...
│
├── velocity-tools-gcp/       (GCP tools, owned by GCP team)
│
├── velocity-tools-database/  (DB tools)
├── velocity-tools-network/   (Network tools)
└── velocity-tools-custom/    (User's proprietary tools)

Examples/Templates:
├── examples/showcase-agent-tools/
├── templates/tool-template/
└── docs/building-custom-tools.md
```

### Integration Pattern
```python
# In agent's requirements.txt or pyproject.toml
velocity-platform==1.2.0
velocity-tools-basic==1.0.0      # Explicitly declare dependencies
velocity-tools-aws==2.1.0
my-company-tools==3.5.0

# In agent code
from velocity_tools_basic import get_current_time, perform_calculation
from velocity_tools_aws import s3_read, dynamodb_query
from my_company_tools import validate_internal_api, audit_log
```

### Pros
✓ **Clean separation:** Platform is small, focused, maintainable
✓ **Independent versioning:** Update tools without releasing platform
✓ **No dependency conflicts:** Each tool package manages own deps
✓ **Flexible licensing:** Different tools can have different licenses
✓ **Ownership clarity:** Tool team owns tool, platform team owns SDK
✓ **Rapid iteration:** Ship tool patches immediately
✓ **Community-friendly:** Easy for 3rd parties to contribute tools
✓ **Opt-in model:** Agents declare what they need
✓ **Easier testing:** Small platform test suite, tools tested independently
✓ **Deprecation path:** Old tools stay available indefinitely
✓ **Cost control:** Only pay for what you use (transitive deps)

### Cons
✗ Setup overhead: Install multiple packages (but clear dependency declarations)
✗ Discovery: Harder to find available tools (mitigated by documentation)
✗ Consistency: Different teams might implement similar tools differently

---

## Option 3: Hybrid (Cherry-Picked Balanced Approach)

### Structure
```
Platform Ships With:
├── Basic/Essential Tools (no external deps)
│   ├── get_current_time
│   ├── perform_calculation
│   ├── format_json
│   └── count_words
└── Tool Ecosystem Connectors (Optional, minimal code)
    ├── aws_connector.py       (imports velocity-tools-aws dynamically)
    ├── gcp_connector.py
    ├── db_connector.py
    └── llm_connector.py

External Packages Provide:
├── velocity-tools-aws/        (comprehensive, optional)
├── velocity-tools-gcp/
├── velocity-tools-enterprise/ (company-specific)
└── ...
```

### Pros
✓ Simple agents work out-of-box (basic tools included)
✓ Advanced users can opt-in to specialized tools
✓ Platform remains lean
✓ Ecosystem can grow independently

### Cons
✗ Still maintains some tools in platform
✗ Harder to maintain parity across tool packages
✗ Connector overhead (minimal but exists)

---

## Expert Recommendation: OPTION 2 (Tools Outside)

### Rationale (Aligned with rules.txt)

#### 1. **Long-Term Maintainability**
- **Problem:** Platform grows with each tool addition
- **Solution:** Separate concerns - SDK vs tools
- **Risk:** Tool updates would force platform releases

#### 2. **Architecture: Modularity & Scalability**
- **Core:** Registry, decorators, metadata (40 KB)
- **Tools:** Independent packages (can have 100+ without platform bloat)
- **SOLID:** Single Responsibility - platform registers, doesn't implement tools

#### 3. **Security: Principle of Least Privilege**
- **Problem:** Monolithic platform = update everything or nothing
- **Solution:** Update only what you use
- **Risk:** Platform CVE forces update of tools you don't use

#### 4. **Integrity & Accuracy**
- **Honest assessment:** Platform team can't maintain AWS SDK, GCP SDK, proprietary tools equally well
- **Realistic:** Tool packages will have different maturity levels
- **Better:** Each tool owned by domain expert

#### 5. **Operational Maturity**
- **Resembles:** How Python, Node, Go ecosystems work
- **Proven:** Works for millions of developers
- **Language:** Dependency packages, not monolithic runtime

---

## Migration Path

### Phase 1 (Now): Extract Current Tools
Move `src/velocity/tools/library/` → `velocity-tools-basic` package

```python
# Before
from velocity.tools.library import get_current_time

# After
from velocity_tools_basic import get_current_time
# (Or: from velocity.tools.library if we keep backward compat)
```

### Phase 2: Create Ecosystem
Build first extension packages:
- `velocity-tools-aws`
- `velocity-tools-gcp`
- `velocity-tools-database`
- `velocity-tools-http`

### Phase 3: Community
Publish template for custom tools:
- Clear documentation
- Tool template generator
- Testing guidelines
- Security checklist

---

## Implementation: Keep Backward Compatibility

Platform can re-export tools for backward compatibility:

```python
# src/velocity/tools/library/__init__.py (wrapper)
"""
Backward compatibility layer for basic tools.
These are now maintained in velocity-tools-basic package.
"""

try:
    # Try new location first
    from velocity_tools_basic import (
        get_current_time,
        perform_calculation,
        format_data_as_json,
        count_words,
    )
except ImportError:
    # Fallback to built-in for development
    from .basic import get_current_time, perform_calculation
    from .formatting import format_data_as_json, count_words
```

---

## Recommendation Summary

**Go with Option 2: Tools Outside Platform**

### Why
1. **Principle of Least Privilege:** Don't include tools you don't need
2. **Modularity:** Tools are independent modules
3. **Maintainability:** Tool versions don't couple with platform versions
4. **Scalability:** Add 100 tools without platform impact
5. **Security:** Update only what you use
6. **Community:** Easy for 3rd parties to contribute
7. **Economics:** Reduce transitive dependencies

### Implementation
1. **Immediate:** Keep basic tools as temporary shim
2. **Short-term:** Create `velocity-tools-basic` package
3. **Medium-term:** Start `velocity-tools-aws`, etc.
4. **Long-term:** Rich ecosystem of specialized tool packages

### Fallback
If you want comprehensive out-of-box experience (like Claude Code):
- Provide `velocity-tools-bundle` meta-package that installs common tools
- Users can `pip install velocity[tools]` for everything
- Users can `pip install velocity[tools-basic]` for minimal
- Advanced: `pip install velocity[tools-aws,tools-gcp]`

---

## Claude Code Comparison

Claude Code has comprehensive tools because:
- **It's a closed system:** Anthropic maintains everything
- **SLA guarantees:** Single vendor responsible for all
- **Resource-rich:** Anthropic team is large
- **Different model:** Tools are tightly integrated with LLM

Velocity is a platform, not a specific service:
- **Open ecosystem:** Should support 3rd-party tools
- **Distributed ownership:** Different teams own different domains
- **Lightweight:** Platform is a framework, not monolithic service
- **Better model:** Explicit dependency declarations

---

## Action Items

1. **Decision:** Confirm direction with team
2. **Phase 1:** Refactor current tools as re-export shim
3. **Phase 2:** Create `velocity-tools-basic` package
4. **Documentation:** Write "Building Custom Tools" guide
5. **Migration:** Update agents to use `velocity_tools_basic` imports
6. **Backward Compat:** Maintain re-export layer for existing code
