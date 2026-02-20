# Skill: Create Documentation Task (Beads)

**Purpose**: Create a beads task for documentation work with proper dependencies and metadata.

**Category**: beads_integration

---

## Prerequisites

- Beads installed and initialized (`bd init` completed)
- Familiarity with beads commands (`bd --help`)
- Read [`../../knowledgebase/AGENT_PROMPT.md`](../../knowledgebase/AGENT_PROMPT.md) section on beads

---

## Inputs

### Required
- **task_title**: Short task description (e.g., "Document backtest module")
- **task_type**: Type of task
  - `epic` - High-level multi-week effort
  - `phase` - Collection of related tasks (1-2 weeks)
  - `task` - Individual work item (hours to days)

### Optional
- **parent_id**: Parent task ID (for hierarchical tasks)
- **description**: Detailed task description
- **priority**: Priority level (0 = highest, default: 1)
- **dependencies**: List of task IDs this task depends on

---

## Process

### Step 1: Determine Task Hierarchy

Decide where this task fits in the hierarchy.

**Documentation Epic Structure**:
```
Documentation Epic (bd-<epic-id>)
├── Phase 1: Foundation
│   ├── Create knowledge base
│   ├── Create skills
│   └── Document backtest module
├── Phase 2: API Reference
│   └── ... (per-module tasks)
├── Phase 3: User Guides
│   └── ... (per-guide tasks)
```

**Task Levels**:
- **Epic**: "Complete midterm_stock_planner documentation"
- **Phase**: "Phase 1: Foundation", "Phase 2: API Reference"
- **Task**: "Document backtest module", "Create analyze_module skill"

---

### Step 2: Create Task

Use `bd create` command to create the task.

**Basic Command**:
```bash
bd create "Task title" [--flags]
```

**Common Flags**:
- `--epic`: Create as epic (high-level)
- `--parent <id>`: Set parent task
- `--priority <0-9>`: Set priority (0 = highest)
- `--description "text"`: Add detailed description

---

### Step 3: Create Epic (if starting new project)

Create the top-level epic.

**Command**:
```bash
bd create "Complete midterm_stock_planner documentation" \
  --description "Comprehensive documentation for ~49,000 LOC stock analysis application covering API reference, user guides, design docs, and docstrings for 17 modules" \
  --priority 0 \
  --epic
```

**Output**: Returns epic ID (e.g., `bd-a1b2c3`)

**Save**: Save epic ID for creating child tasks
```bash
EPIC_ID=<epic-id-from-output>
echo $EPIC_ID
```

---

### Step 4: Create Phase Tasks

Create phase tasks under the epic.

**Commands**:
```bash
# Phase 1
bd create "Phase 1: Foundation (knowledgebase + skills + core API)" \
  --parent $EPIC_ID \
  --priority 0 \
  --description "Create infrastructure for AI agents to systematically document"

# Save Phase 1 ID
PHASE1_ID=<phase1-id>

# Phase 2
bd create "Phase 2: Complete API Reference" \
  --parent $EPIC_ID \
  --priority 1

# Phase 3
bd create "Phase 3: User Guides & Design Docs" \
  --parent $EPIC_ID \
  --priority 2

# ... (more phases)
```

---

### Step 5: Create Granular Tasks

Create specific work items under phases.

**Example Tasks for Phase 1**:
```bash
# Knowledge base tasks
bd create "Write knowledgebase/AGENT_PROMPT.md" \
  --parent $PHASE1_ID \
  --priority 0 \
  --description "Comprehensive system prompt with codebase context"

KB_TASK_ID=<task-id>

# Skills tasks
bd create "Create skills/documentation/generate_api_docs.md" \
  --parent $PHASE1_ID \
  --priority 1 \
  --description "Skill for generating API reference docs"

SKILL_TASK_ID=<task-id>

# API doc task
bd create "Document backtest module (docs/api_reference/backtest.md)" \
  --parent $PHASE1_ID \
  --priority 2 \
  --description "First API reference as proof of concept"

DOC_TASK_ID=<task-id>
```

---

### Step 6: Add Task Dependencies

Link tasks with dependencies using `bd dep add`.

**Command Syntax**:
```bash
bd dep add <child-task-id> <parent-dependency-id>
```

**Meaning**: Child task depends on (is blocked by) parent dependency

**Example Dependencies**:
```bash
# Skills need knowledge base first
bd dep add $SKILL_TASK_ID $KB_TASK_ID

# API docs need skills first
bd dep add $DOC_TASK_ID $SKILL_TASK_ID
```

**Dependency Graph**:
```
KB_TASK → SKILL_TASK → DOC_TASK
(must complete in order)
```

---

### Step 7: Verify Task Structure

Check that tasks are created correctly.

**Commands**:
```bash
# Show task details
bd show <task-id>

# Show task tree
bd status $EPIC_ID

# List ready tasks (no blockers)
bd ready
```

**Validate**:
- [ ] Epic exists with all phases as children
- [ ] Each phase has granular tasks
- [ ] Dependencies are set correctly
- [ ] `bd ready` shows first task(s) to work on

---

## Outputs

### Primary
- **Epic ID**: Top-level task ID
- **Phase IDs**: Phase task IDs
- **Task IDs**: Granular work item IDs
- **Dependency Graph**: Tasks linked with dependencies

### Secondary
- **Beads Files**: `.beads/` directory with JSONL task files
- **Git History**: Beads tasks are git-versioned

---

## Examples

### Example 1: Create Complete Task Hierarchy

**Input**:
- task_title: "Complete midterm_stock_planner documentation"
- task_type: `epic`

**Process**:
```bash
# 1. Create epic
bd create "Complete midterm_stock_planner documentation" \
  --description "Comprehensive documentation for ~49,000 LOC stock analysis application" \
  --priority 0 \
  --epic

# Output: Created task bd-a1b2
EPIC_ID=bd-a1b2

# 2. Create Phase 1
bd create "Phase 1: Foundation" \
  --parent $EPIC_ID \
  --priority 0

# Output: Created task bd-a1b2.1
PHASE1_ID=bd-a1b2.1

# 3. Create Phase 1 tasks
bd create "Write AGENT_PROMPT.md" --parent $PHASE1_ID --priority 0
# Output: bd-a1b2.1.1
KB_TASK=bd-a1b2.1.1

bd create "Create generate_api_docs skill" --parent $PHASE1_ID --priority 1
# Output: bd-a1b2.1.2
SKILL_TASK=bd-a1b2.1.2

bd create "Document backtest module" --parent $PHASE1_ID --priority 2
# Output: bd-a1b2.1.3
DOC_TASK=bd-a1b2.1.3

# 4. Add dependencies
bd dep add $SKILL_TASK $KB_TASK
bd dep add $DOC_TASK $SKILL_TASK

# 5. Verify
bd status $EPIC_ID
```

**Output**:
```
Epic: Complete midterm_stock_planner documentation
├─ Phase 1: Foundation [OPEN]
│  ├─ Write AGENT_PROMPT.md [OPEN, READY]
│  ├─ Create generate_api_docs skill [OPEN, BLOCKED]
│  └─ Document backtest module [OPEN, BLOCKED]
```

**Ready Tasks**:
```bash
bd ready
# Output: bd-a1b2.1.1 - Write AGENT_PROMPT.md
```

---

## Validation

- [ ] Epic created with correct description
- [ ] All phases created under epic
- [ ] All granular tasks created under phases
- [ ] Dependencies set correctly (child depends on parent)
- [ ] `bd status <epic-id>` shows full hierarchy
- [ ] `bd ready` shows first actionable task(s)
- [ ] Task IDs follow hierarchy (bd-a1b2.1.1, bd-a1b2.1.2, etc.)

---

## Related Skills

### Prerequisites
- None (this is typically the first beads skill used)

### Follow-ups
- [`update_task_progress.md`](update_task_progress.md) - Update task status
- [`break_down_epic.md`](break_down_epic.md) - Break large epics into subtasks

### Related
- [`../documentation/generate_api_docs.md`](../documentation/generate_api_docs.md) - Execute documentation tasks

---

## Beads Quick Reference

### Essential Commands
```bash
# Create task
bd create "Title" [--parent <id>] [--priority 0-9] [--epic]

# Show task details
bd show <task-id>

# List ready tasks (no blockers)
bd ready

# Claim and start task
bd update <task-id> --claim --status in_progress

# Complete task
bd update <task-id> --status done

# Add dependency (child depends on parent)
bd dep add <child-id> <parent-id>

# Show task tree
bd status <epic-id>

# Help
bd --help
```

---

**Last Updated**: 2026-02-06
**Version**: 1.0
