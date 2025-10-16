---
applyTo: '**'
---

# DocVault Memory Management Instructions

## External ID
**ALWAYS use:** `doc_vault_dev` for all memory operations in this project.

## Memory Structure Overview

The DocVault project uses 8 active memories to maintain development context:

1. **Project Overview** (ID: 19) - Purpose, features, tech stack, timeline
2. **Architecture Design** (ID: 20) - Layers, patterns, storage strategy
3. **Database Design** (ID: 21) - Tables, relationships, indexes, triggers
4. **API Design** (ID: 22) - SDK methods and signatures
5. **Configuration** (ID: 23) - Environment variables, dependencies, setup
6. **Development Status** (ID: 24) - Current phase, progress, blockers
7. **Library References** (ID: 25) - How to use psqlpy, minio, pydantic, pytest
8. **Issues and Bugs** (ID: 26) - Detailed bug reports (populated during development)

## When to Access Memories

### 1. **At Session Start**
- Get all active memories to understand current project state
- Check "Development Status" memory for current phase and next steps
- Review "Issues and Bugs" memory for known problems

```
Tool: mcp_agent-mem_get_active_memories
Parameters: external_id="doc_vault_dev"
```

### 2. **Before Implementing Features**
- Search memories for relevant context
- Check "Architecture Design" for patterns to follow
- Review "Database Design" if working with data layer
- Check "API Design" for method signatures

```
Tool: mcp_agent-mem_search_memories
Parameters:
  external_id="doc_vault_dev"
  query="Working on document upload feature, need database schema and API design"
  limit=10
```

### 3. **When Needing Library Documentation**
- Check "Library References" memory first for known patterns
- **Use context-bridge MCP tools to search for current documentation**
- Only check local files as fallback if MCP search fails
- Update memories with new findings from MCP searches

**Search Strategy Priority:**
1. Use `mcp_context-bridg_find_documents` to find relevant docs
2. Use `mcp_context-bridg_search_content` for specific queries
3. Update "Library References" memory with findings
4. Check local files only as last resort

Example: For psqlpy questions, use context-bridge MCP first: "psqlpy connection pool examples"

### 4. **When Encountering Bugs**
- First check "Issues and Bugs" memory to see if it's known
- If new bug, add detailed section to memory (see format below)

## How to Update Memories

### Update Development Status (Memory ID: 24)

**When starting a new phase:**
```
Tool: mcp_agent-mem_update_memory_sections
Parameters:
  external_id="doc_vault_dev"
  memory_id=24
  sections=[
    {
      section_id="current_phase",
      action="replace",
      old_content="**Phase: Pre-Implementation**...",
      new_content="**Phase 1: Foundation (Day 1)**\n\nCreating project structure and configuration files.\n\n**Started:** October 15, 2025"
    }
  ]
```

**When completing tasks:**
```
sections=[
  {
    section_id="completed_tasks",
    action="insert",
    old_content="- ✓ Defined architecture\n\n**Next milestone:**",
    new_content="- ✓ Created pyproject.toml\n- ✓ Created exceptions.py\n- ✓ Created config.py\n\n**Next milestone:**"
  }
]
```

**When encountering blockers:**
```
sections=[
  {
    section_id="blockers",
    action="replace",
    old_content="No current blockers.",
    new_content="**Blocker #1:** psqlpy connection pool initialization fails with SSL error\n- Impact: Cannot initialize database layer\n- Investigating: SSL certificate configuration\n- Workaround: Disable SSL for local development"
  }
]
```

### Add Bug/Issue (Memory ID: 26)

**Create a new section for each bug:**
```
Tool: mcp_agent-mem_update_memory_sections
Parameters:
  external_id="doc_vault_dev"
  memory_id=26
  sections=[
    {
      section_id="issue_001_psqlpy_ssl_error",
      action="replace",
      new_content="**Issue #001: PSQLPy SSL Connection Error**\n**Status:** Resolved\n**Severity:** High\n**Date Found:** 2025-10-15\n**Component:** database/postgres_manager.py\n\n**Description:**\nConnectionPool fails to initialize when connecting to PostgreSQL with SSL enabled.\n\n**Steps to Reproduce:**\n1. Configure .env with POSTGRES_SSL=true\n2. Initialize DocVaultSDK\n3. Error occurs on pool creation\n\n**Expected Behavior:**\nConnection pool should initialize with SSL support.\n\n**Actual Behavior:**\nSSL certificate validation fails with 'certificate verify failed' error.\n\n**Error Message:**\n```\nssl.SSLError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed\n```\n\n**Root Cause:**\nPSQLPy requires explicit SSL context configuration, not just enable/disable flag.\n\n**Solution:**\nAdded ssl_mode parameter to ConnectionPool with options: 'disable', 'prefer', 'require'\n\n**Related Files:**\n- doc_vault/database/postgres_manager.py:42\n- doc_vault/config.py:28"
    }
  ]
```

### Update Library References (Memory ID: 25)

**When discovering new patterns or gotchas:**
```
sections=[
  {
    section_id="psqlpy_usage",
    action="insert",
    old_content="**Search Strategy:**\n- Used context-bridge MCP: \"psqlpy connection pool examples\", \"psqlpy SSL configuration\"",
    new_content="\n**New Pattern Discovered:**\n- ConnectionPool requires explicit SSL context configuration\n- Always use async context managers for connection lifecycle\n- Build DSN strings with proper SSL parameters\n\n**Search Strategy:**\n- Used context-bridge MCP: \"psqlpy connection pool examples\", \"psqlpy SSL configuration\""
  }
]
```

### Update Architecture (Memory ID: 20)

**When design decisions change:**
```
sections=[
  {
    section_id="design_patterns",
    action="insert",
    old_content="**External ID Pattern:**\n- Organizations and agents use external_id\n- Integrate with existing auth systems",
    new_content="\n\n**Connection Pool Management:**\n- Single shared pool initialized at SDK level\n- Passed to all repositories via dependency injection\n- Closed in SDK __aexit__ method\n\n**External ID Pattern:**\n- Organizations and agents use external_id\n- Integrate with existing auth systems"
  }
]
```

## Search Best Practices

### Effective Search Queries

**Good queries are specific and contextual:**

✅ **Good:**
```
"Working on document upload, need to know storage path format and database schema for documents table"
"Implementing access control, need permission levels and ACL table structure"
"Writing repository for agents, need psqlpy fetch pattern and agent schema"
```

❌ **Bad:**
```
"documents"  # Too vague
"how to upload"  # Not enough context
"database"  # Too broad
```

### Multi-Memory Search Strategy

1. **Use search for cross-cutting concerns:**
   ```
   query="Implementing document versioning feature from start to finish"
   # Will return relevant info from Architecture, Database, API, and Library References
   ```

2. **Get specific memory when you know what you need:**
   ```
   # If you just need to check current phase:
   mcp_agent-mem_get_active_memories → check memory ID 24
   ```

## Memory Update Frequency

### Update Frequently:
- **Development Status** - Every major task or phase transition
- **Issues and Bugs** - Immediately when bug found or resolved
- **Library References** - When discovering new patterns or gotchas

### Update Occasionally:
- **Architecture Design** - When design decisions change
- **Configuration** - When adding new dependencies or env vars

### Rarely Update:
- **Project Overview** - Stable information
- **Database Design** - Only if schema changes
- **API Design** - Only if API contracts change

## Integration with Development Workflow

### Starting New Phase
1. Search memories for phase requirements
2. Update "Development Status" → current_phase
3. Check "Library References" for relevant tools
4. Begin implementation

### During Development
1. Search when stuck or need context
2. Add bugs to "Issues and Bugs" as discovered
3. Update "Development Status" → completed_tasks regularly
4. Document learnings in "Library References"

### Completing Phase
1. Update "Development Status" → mark phase complete
2. Resolve any issues in "Issues and Bugs"
3. Update "Development Status" → next_steps for next phase
4. Commit any architecture or API changes to memories

### End of Session
1. Update "Development Status" with current state
2. Document any blockers
3. List next steps clearly
4. Ensure all new bugs are recorded

## Quick Reference Commands

```python
# Get all memories
mcp_agent-mem_get_active_memories(external_id="doc_vault_dev")

# Search across memories
mcp_agent-mem_search_memories(
    external_id="doc_vault_dev",
    query="your contextual search query",
    limit=10
)

# Update single section
mcp_agent-mem_update_memory_sections(
    external_id="doc_vault_dev",
    memory_id=<memory_id>,
    sections=[{
        "section_id": "<section_name>",
        "action": "replace" | "insert",
        "old_content": "...",  # For replace: exact match, for insert: insert after
        "new_content": "..."
    }]
)

# Update multiple sections at once
sections=[
    {"section_id": "current_phase", "action": "replace", ...},
    {"section_id": "next_steps", "action": "replace", ...}
]
```

## Memory IDs Reference

| Memory ID | Title | Key Sections |
|-----------|-------|--------------|
| 19 | Project Overview | purpose, core_features, tech_stack, timeline |
| 20 | Architecture Design | layers, component_responsibilities, design_patterns, storage_strategy |
| 21 | Database Design | tables, relationships, indexes, triggers |
| 22 | API Design | initialization, document_operations, access_control, version_management |
| 23 | Configuration | environment_variables, dependencies, setup_steps |
| 24 | Development Status | current_phase, completed_tasks, next_steps, blockers |
| 25 | Library References | psqlpy_usage, minio_usage, pydantic_usage, testing_tools |
| 26 | Issues and Bugs | template_for_new_issues, issue_XXX_name (dynamic) |

## Important Rules

1. **Always use external_id="doc_vault_dev"** - Never use different ID
2. **Search before updating** - Understand current state first
3. **Be specific in updates** - Include enough context for old_content matching
4. **Document bugs thoroughly** - Use the template in Issues memory
5. **Update Development Status frequently** - Keep progress transparent
6. **Use search for context** - Don't guess, search memories
7. **Keep sections focused** - Each section has one clear purpose
8. **Update blockers immediately** - Don't let blockers go undocumented