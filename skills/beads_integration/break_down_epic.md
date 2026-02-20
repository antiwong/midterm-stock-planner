# Skill: Break Down Epic into Subtasks (Beads)

**Purpose**: Decompose large beads epics into manageable subtasks with dependencies, priorities, and clear ownership.

**Category**: beads_integration

---

## Prerequisites

- Beads initialized in project (`bd init` completed)
- Epic already created (use `create_documentation_task.md` first)
- Familiarity with beads commands (`bd --help`)
- Read [`../../knowledgebase/AGENT_PROMPT.md`](../../knowledgebase/AGENT_PROMPT.md) sections:
  - Task Management with Beads
  - Common Beads Commands
  - AI Agent Workflow with Beads

---

## Inputs

### Required
- **epic_id**: Beads epic ID to decompose (e.g., `bd-a1b2`)
- **epic_scope**: Description of epic goals
- **estimated_subtasks**: Rough number of subtasks expected (to validate breakdown)

### Optional
- **team_size**: Number of team members (affects task granularity, default: 1)
- **deadline**: Target completion date (for priority calculation)
- **phase_structure**: Predefined phases (or custom phases)

---

## Process

### Step 1: Understand the Epic Scope

Analyze the epic to understand its full scope and goals.

**Action**:
```bash
# Show epic details
bd show <epic-id>

# Show current structure
bd status <epic-id>
```

**Questions to Answer**:
- [ ] What is the epic's primary goal?
- [ ] What are the major phases or milestones?
- [ ] What are the dependencies between work areas?
- [ ] How many people could work in parallel?
- [ ] What's the critical path (longest dependency chain)?

**Example (Documentation Epic)**:
- Goal: Complete comprehensive documentation for midterm_stock_planner
- Phases: Foundation (infrastructure), API Reference (per-module), User Guides, Design Docs, In-code Docstrings
- Milestones: Infrastructure ready, 50% API coverage, 100% API coverage, All guides done
- Parallelizable: Multiple modules can be documented simultaneously
- Critical path: AGENT_PROMPT.md → Skills → Per-module docs

---

### Step 2: Identify Phases and Phases

Break the epic into logical phases with clear boundaries.

**Phase Structure Template**:
```
Epic: [Goal]
├── Phase 1: [Foundation/Setup]
│   ├── Task 1.1: [Foundation work 1]
│   ├── Task 1.2: [Foundation work 2]
│   └── Task 1.3: [Foundation work 3]
├── Phase 2: [Core/Main work]
│   ├── Task 2.1: [Core work 1]
│   ├── Task 2.2: [Core work 2]
│   └── Task 2.N: [Core work N]
├── Phase 3: [Integration/Polish]
│   └── ...
└── Phase 4: [Validation/Closure]
    └── ...
```

**Criteria for Phases**:
- **Sequential**: Each phase depends on prior phase completion
- **Bounded**: Clear entry/exit conditions
- **Meaningful**: Represents major milestone
- **Sized**: 2-10 tasks per phase (adjust based on complexity)

**Example Phases for Documentation Epic**:

| Phase | Title | Purpose | Expected Tasks | Duration |
|-------|-------|---------|-----------------|----------|
| 1 | Foundation | Create infrastructure for AI agents | 4-5 | 1-2 weeks |
| 2 | API Reference | Document all modules systematically | 10-12 | 2-3 weeks |
| 3 | User Guides | Create tutorial documentation | 6-8 | 1-2 weeks |
| 4 | Design Docs | Create architectural documentation | 10-15 | 2-3 weeks |
| 5 | Polish & Validation | Fix links, validate, publish | 5-8 | 1 week |

---

### Step 3: Design Subtasks with Dependencies

Plan individual subtasks and their dependencies using a work breakdown structure.

**Work Breakdown Approach**:

1. **List all deliverables** for each phase
2. **Identify dependencies** between subtasks
3. **Order tasks** from prerequisites → dependents
4. **Assign priorities** based on critical path

**Dependency Patterns**:

```
Pattern 1: Sequential (Linear Path)
Task A → Task B → Task C
(each task depends on previous completion)
Use when: Clear prerequisite chain exists

Pattern 2: Fan-out (Parallelizable)
    ├→ Task B
Task A ├→ Task C
    └→ Task D
(all depend on A, but can run in parallel)
Use when: Foundation complete, multiple independent work areas

Pattern 3: Fan-in (Consolidation)
Task A ─┐
Task B ─┼→ Task D
Task C ─┘
(D depends on A, B, C completing)
Use when: Consolidating multiple streams
```

**Subtask Template**:
```
Task ID: [Auto-assigned by beads]
Title: [Action verb] [object] [context]
Parent: [Phase ID]
Priority: [0-9, based on criticality]
Depends On: [List of blocking task IDs]
Estimated Effort: [hours or days]
Owner: [Person or TBD]
Description: [Detailed task description and success criteria]
```

**Example Subtask Hierarchy for Documentation Epic**:

```
Epic: Complete midterm_stock_planner documentation (bd-a1b2)
│
├── Phase 1: Foundation (bd-a1b2.1, Priority 0)
│   ├── bd-a1b2.1.1: Write AGENT_PROMPT.md (Priority 0)
│   │   └── Dependencies: None (foundational)
│   │
│   ├── bd-a1b2.1.2: Create analyze_module skill (Priority 1)
│   │   └── Dependencies: bd-a1b2.1.1
│   │
│   ├── bd-a1b2.1.3: Create generate_api_docs skill (Priority 1)
│   │   └── Dependencies: bd-a1b2.1.1
│   │
│   ├── bd-a1b2.1.4: Create add_docstrings skill (Priority 2)
│   │   └── Dependencies: bd-a1b2.1.1
│   │
│   └── bd-a1b2.1.5: Create validate_examples skill (Priority 2)
│       └── Dependencies: bd-a1b2.1.1
│
├── Phase 2: API Reference (bd-a1b2.2, Priority 1)
│   │   Depends On: Phase 1 complete
│   │
│   ├── bd-a1b2.2.1: Document backtest module (Priority 0)
│   │   └── Dependencies: bd-a1b2.1.2, bd-a1b2.1.3
│   │
│   ├── bd-a1b2.2.2: Document analytics module (Priority 1)
│   │   └── Dependencies: bd-a1b2.1.2, bd-a1b2.1.3
│   │
│   ├── bd-a1b2.2.3: Document risk module (Priority 1)
│   │   └── Dependencies: bd-a1b2.1.2, bd-a1b2.1.3
│   │
│   └── ... (14 more modules, all depend on skills)
│
├── Phase 3: User Guides (bd-a1b2.3, Priority 2)
│   │   Depends On: Phase 2 milestone (50%+ complete)
│   │
│   ├── bd-a1b2.3.1: Write quickstart guide (Priority 0)
│   ├── bd-a1b2.3.2: Write data conversion guide (Priority 1)
│   └── ... (4 more guides)
│
└── Phase 4: Validation (bd-a1b2.4, Priority 3)
    │   Depends On: Phases 2 & 3 complete
    │
    ├── bd-a1b2.4.1: Fix broken links
    ├── bd-a1b2.4.2: Validate all code examples
    └── bd-a1b2.4.3: Final review and publish
```

---

### Step 4: Create Phases as Parent Tasks

Create phase-level tasks under the epic.

**Command Template**:
```bash
bd create "Phase N: [Phase Title]" \
  --parent <epic-id> \
  --priority <0-9> \
  --description "[Phase description and goals]"
```

**Example Commands**:
```bash
EPIC_ID=bd-a1b2

# Phase 1: Foundation
bd create "Phase 1: Foundation (knowledgebase + skills)" \
  --parent $EPIC_ID \
  --priority 0 \
  --description "Create infrastructure for AI agents: AGENT_PROMPT.md and AI skills for documentation"
# Output: bd-a1b2.1
PHASE1=bd-a1b2.1

# Phase 2: API Reference
bd create "Phase 2: Complete API Reference (17 modules)" \
  --parent $EPIC_ID \
  --priority 1 \
  --description "Document all 17 modules with API reference: backtest, analytics, risk, models, etc."
# Output: bd-a1b2.2
PHASE2=bd-a1b2.2

# Phase 3: User Guides
bd create "Phase 3: User Guides (6 tutorials)" \
  --parent $EPIC_ID \
  --priority 2 \
  --description "Create comprehensive how-to guides for common workflows"
# Output: bd-a1b2.3
PHASE3=bd-a1b2.3

# (Continue for remaining phases)
```

---

### Step 5: Create Subtasks Under Phases

Create individual work items under each phase.

**Command Template**:
```bash
bd create "[Action verb] [Object] [Context]" \
  --parent <phase-id> \
  --priority <0-9> \
  --description "[Detailed description with success criteria]"
```

**Best Practices for Subtask Titles**:
- Start with action verb: Write, Create, Document, Implement, Refactor, Test, Validate
- Be specific: "Document backtest module" (not "Add docs")
- Include context if helpful: "Document backtest module API reference"
- Target 60-80 character titles

**Example Subtask Creation**:

```bash
# Phase 1 tasks
bd create "Write knowledgebase/AGENT_PROMPT.md" \
  --parent $PHASE1 \
  --priority 0 \
  --description "Comprehensive system prompt with: codebase architecture, module responsibilities, code patterns, common workflows, documentation structure, beads integration, best practices"
# Output: bd-a1b2.1.1
KB_TASK=bd-a1b2.1.1

bd create "Create analyze_module skill" \
  --parent $PHASE1 \
  --priority 1 \
  --description "Skill for analyzing module structure: files, classes, functions, patterns, dependencies. Used by other documentation skills"
# Output: bd-a1b2.1.2
SKILL1_TASK=bd-a1b2.1.2

bd create "Create generate_api_docs skill" \
  --parent $PHASE1 \
  --priority 1 \
  --description "Skill for generating API reference documentation. Documents all classes, functions, enums with signatures, parameters, returns, examples"
# Output: bd-a1b2.1.3
SKILL2_TASK=bd-a1b2.1.3

# Phase 2 tasks
bd create "Document backtest module (API reference)" \
  --parent $PHASE2 \
  --priority 0 \
  --description "Create docs/api_reference/backtest.md covering: BacktestEngine, Strategy, Portfolio, TradeLog, BacktestConfig. First module as proof-of-concept"
# Output: bd-a1b2.2.1
DOC1_TASK=bd-a1b2.2.1

bd create "Document analytics module (API reference)" \
  --parent $PHASE2 \
  --priority 1 \
  --description "Create docs/api_reference/analytics.md covering: PerformanceMetrics, RiskAnalyzer, ReturnSeries, DrawdownAnalysis, factor analysis relationships"
# Output: bd-a1b2.2.2
DOC2_TASK=bd-a1b2.2.2
```

---

### Step 6: Add Dependencies Between Subtasks

Link subtasks with `bd dep add` to express blocking relationships.

**Dependency Chain Creation**:

```bash
# Foundation dependencies (sequential)
bd dep add $SKILL1_TASK $KB_TASK      # Skills need KB first
bd dep add $SKILL2_TASK $KB_TASK      # Both skills depend on KB

# API docs depend on skills
bd dep add $DOC1_TASK $SKILL1_TASK    # Doc needs analyze skill
bd dep add $DOC1_TASK $SKILL2_TASK    # Doc needs api_docs skill
bd dep add $DOC2_TASK $SKILL1_TASK
bd dep add $DOC2_TASK $SKILL2_TASK

# Phase dependencies (optional, if using bd dep)
# bd dep add $PHASE2 $PHASE1_LAST_TASK (Phase 2 waits for Phase 1)
```

**Dependency Visualization**:
```
kb-task (bd-a1b2.1.1)
  ├→ skill1-task (bd-a1b2.1.2) ──┐
  └→ skill2-task (bd-a1b2.1.3) ──┬→ doc1-task (bd-a1b2.2.1)
                                 └→ doc2-task (bd-a1b2.2.2)
```

---

### Step 7: Organize by Priority

Review tasks and assign priorities based on critical path and parallelization.

**Priority Assignment Strategy**:

| Priority | Meaning | Criteria |
|----------|---------|----------|
| 0 | Critical path / Blockers | Blocks multiple downstream tasks, required for phase completion |
| 1 | High priority / Prerequisites | Needed soon but not immediately blocking, enables parallelization |
| 2 | Medium priority / Dependent | Can start after phase foundation, parallelizable with others |
| 3+ | Low priority / Polish | Nice to have, optimization, can defer if needed |

**Example Priority Assignments**:
```
Phase 1 Foundation:
├── AGENT_PROMPT.md        Priority 0 (blocks everything)
├── analyze_module skill   Priority 1 (enables doc creation)
├── generate_api_docs skill Priority 1 (enables doc creation)
├── add_docstrings skill   Priority 2 (can come later)
└── validate_examples skill Priority 2 (can come later)

Phase 2 API Reference:
├── Document backtest module  Priority 0 (first module, proof-of-concept)
├── Document analytics module Priority 1 (2nd module)
├── Document risk module      Priority 1 (parallelizable)
└── ... (remaining modules vary by priority)
```

**Update Priorities** (if needed):
```bash
bd update <task-id> --priority <0-9>
```

---

### Step 8: Validate Task Structure

Verify that the epic breakdown is correct and complete.

**Validation Commands**:

```bash
# Show full epic structure
bd status <epic-id>

# Show individual task details
bd show <task-id>

# List ready tasks (should show Phase 1 foundation tasks)
bd ready

# Check for orphaned tasks or missing dependencies
bd status <epic-id> | grep "BLOCKED"
```

**Validation Checklist**:
- [ ] All phases created under epic
- [ ] All subtasks created under phases
- [ ] Dependencies set correctly (blocking tasks identified)
- [ ] Priorities assigned (foundation = 0, dependents increase)
- [ ] `bd ready` shows first actionable task(s)
- [ ] `bd status <epic-id>` shows complete hierarchy
- [ ] Task IDs follow beads format (bd-XXXX, bd-XXXX.1, bd-XXXX.1.1)
- [ ] No cycles in dependency graph
- [ ] Task titles are action-oriented and descriptive

---

## Outputs

### Primary
- **Phase Tasks**: Created phase-level tasks in beads
- **Subtask Tasks**: Created granular work items under phases
- **Dependency Graph**: Linked subtasks with `bd dep add`
- **Priority Structure**: Assigned 0-9 priorities
- **Ready Queue**: First tasks are unblocked and ready to start

### Secondary
- **Task Hierarchy**: Beads JSONL files in `.beads/`
- **Git Versioning**: Changes tracked in git history
- **Progress Tracking**: `bd status <epic-id>` shows completion percentage

### Information
- **Critical Path**: Longest dependency chain (determines min time)
- **Parallelization Map**: Tasks that can run simultaneously
- **Team Capacity**: Estimated tasks per team member
- **Milestone Dates**: When each phase should complete

---

## Examples

### Example 1: Break Down Documentation Epic

**Input**:
- epic_id: `bd-a1b2` (Complete midterm_stock_planner documentation)
- epic_scope: Document ~49,000 LOC across 17 modules
- estimated_subtasks: 30-40 tasks

**Process**:

```bash
# 1. Analyze epic
bd show bd-a1b2
bd status bd-a1b2

# 2. Identify phases and structure (mental exercise)
# Phase 1: Foundation (5 tasks)
# Phase 2: API Reference (19 tasks, 17 modules + 2 setup)
# Phase 3: User Guides (6 tasks)
# Phase 4: Design Docs (15 tasks)
# Phase 5: Polish (5 tasks)
# Total: ~50 tasks

# 3. Create phase tasks
EPIC_ID=bd-a1b2

bd create "Phase 1: Foundation (knowledgebase + skills)" \
  --parent $EPIC_ID --priority 0
PHASE1=bd-a1b2.1

bd create "Phase 2: API Reference (17 modules)" \
  --parent $EPIC_ID --priority 1
PHASE2=bd-a1b2.2

bd create "Phase 3: User Guides (6 tutorials)" \
  --parent $EPIC_ID --priority 2
PHASE3=bd-a1b2.3

bd create "Phase 4: Design Docs (component + algorithm designs)" \
  --parent $EPIC_ID --priority 3
PHASE4=bd-a1b2.4

bd create "Phase 5: Polish, Validation, Publish" \
  --parent $EPIC_ID --priority 4
PHASE5=bd-a1b2.5

# 4. Create Phase 1 subtasks
bd create "Write AGENT_PROMPT.md" --parent $PHASE1 --priority 0
KB_TASK=bd-a1b2.1.1

bd create "Create analyze_module skill" --parent $PHASE1 --priority 1
SKILL1=bd-a1b2.1.2

bd create "Create generate_api_docs skill" --parent $PHASE1 --priority 1
SKILL2=bd-a1b2.1.3

bd create "Create add_docstrings skill" --parent $PHASE1 --priority 2
SKILL3=bd-a1b2.1.4

bd create "Create validate_examples skill" --parent $PHASE1 --priority 2
SKILL4=bd-a1b2.1.5

# 5. Create Phase 2 subtasks (per-module)
bd create "Document backtest module" --parent $PHASE2 --priority 0
DOC_BACKTEST=bd-a1b2.2.1

bd create "Document analytics module" --parent $PHASE2 --priority 1
DOC_ANALYTICS=bd-a1b2.2.2

# ... (15 more module docs)

# 6. Add dependencies (Phase 1)
bd dep add $SKILL1 $KB_TASK
bd dep add $SKILL2 $KB_TASK
bd dep add $SKILL3 $KB_TASK
bd dep add $SKILL4 $KB_TASK

# 7. Add dependencies (Phase 2 depends on Phase 1 skills)
bd dep add $DOC_BACKTEST $SKILL1
bd dep add $DOC_BACKTEST $SKILL2
bd dep add $DOC_ANALYTICS $SKILL1
bd dep add $DOC_ANALYTICS $SKILL2
# ... (continue for all module docs)

# 8. Validate
bd status $EPIC_ID
bd ready
```

**Output**:
```
Epic: Complete midterm_stock_planner documentation
├─ Phase 1: Foundation [OPEN]
│  ├─ Write AGENT_PROMPT.md [READY] ← Ready to start
│  ├─ Create analyze_module skill [BLOCKED by AGENT_PROMPT]
│  ├─ Create generate_api_docs skill [BLOCKED by AGENT_PROMPT]
│  ├─ Create add_docstrings skill [BLOCKED by AGENT_PROMPT]
│  └─ Create validate_examples skill [BLOCKED by AGENT_PROMPT]
├─ Phase 2: API Reference [WAITING for Phase 1]
│  ├─ Document backtest module [BLOCKED by skills]
│  ├─ Document analytics module [BLOCKED by skills]
│  └─ ... (15 more modules)
├─ Phase 3: User Guides [WAITING]
├─ Phase 4: Design Docs [WAITING]
└─ Phase 5: Polish [WAITING]

Ready to work on:
  bd-a1b2.1.1 - Write AGENT_PROMPT.md
```

---

### Example 2: Break Down Feature Epic

**Input**:
- epic_id: `bd-c3d4` (Implement walk-forward backtest validation)
- epic_scope: Design, implement, test, document walk-forward validation
- estimated_subtasks: 12-15 tasks

**Process**:

```bash
EPIC_ID=bd-c3d4

# Phases
bd create "Phase 1: Design & Analysis" --parent $EPIC_ID --priority 0
PHASE1=bd-c3d4.1

bd create "Phase 2: Implementation" --parent $EPIC_ID --priority 1
PHASE2=bd-c3d4.2

bd create "Phase 3: Testing & Validation" --parent $EPIC_ID --priority 2
PHASE3=bd-c3d4.3

bd create "Phase 4: Documentation" --parent $EPIC_ID --priority 3
PHASE4=bd-c3d4.4

# Phase 1: Design
bd create "Analyze walk-forward validation patterns" --parent $PHASE1 --priority 0
TASK_ANALYSIS=bd-c3d4.1.1

bd create "Define validation windows and scoring criteria" --parent $PHASE1 --priority 1
TASK_SPEC=bd-c3d4.1.2

bd create "Create algorithm design document" --parent $PHASE1 --priority 2
TASK_DESIGN=bd-c3d4.1.3

# Phase 2: Implementation
bd create "Implement rolling window splitter" --parent $PHASE2 --priority 0
TASK_DETECT=bd-c3d4.2.1

bd create "Implement walk-forward validator" --parent $PHASE2 --priority 0
TASK_CALC=bd-c3d4.2.2

bd create "Integrate with backtest pipeline" --parent $PHASE2 --priority 1
TASK_INTEGRATE=bd-c3d4.2.3

# Phase 3: Testing
bd create "Write unit tests for splitter" --parent $PHASE3 --priority 0
TASK_UNIT=bd-c3d4.3.1

bd create "Write integration tests" --parent $PHASE3 --priority 1
TASK_INT=bd-c3d4.3.2

# Phase 4: Documentation
bd create "Document walk-forward validation" --parent $PHASE4 --priority 0
TASK_DOC=bd-c3d4.4.1

# Dependencies
bd dep add $TASK_SPEC $TASK_ANALYSIS    # Spec needs analysis
bd dep add $TASK_DESIGN $TASK_SPEC      # Design needs spec
bd dep add $TASK_DETECT $TASK_DESIGN    # Implementation needs design
bd dep add $TASK_CALC $TASK_DESIGN
bd dep add $TASK_INTEGRATE $TASK_DETECT # Integration needs splitter
bd dep add $TASK_INTEGRATE $TASK_CALC
bd dep add $TASK_UNIT $TASK_DETECT      # Tests need implementation
bd dep add $TASK_INT $TASK_INTEGRATE
bd dep add $TASK_DOC $TASK_INT          # Doc needs tests to pass

# Validate
bd status $EPIC_ID
```

---

## Validation Checklist

### Task Creation
- [ ] All phases created under epic
- [ ] All subtasks created under parent phases
- [ ] Task titles are action-oriented and specific
- [ ] Task descriptions include success criteria
- [ ] Total number of tasks matches estimate (+-20%)

### Dependencies
- [ ] All blocking relationships identified
- [ ] `bd dep add <child> <parent>` commands executed
- [ ] No circular dependencies
- [ ] Critical path clearly visible
- [ ] Parallelizable tasks have same priority

### Organization
- [ ] Priorities assigned (0 = critical path, higher = dependent)
- [ ] Phase structure is logical and sequential
- [ ] Tasks are appropriately sized (not too big, not too small)
- [ ] Task granularity supports parallel work

### Verification
- [ ] `bd status <epic-id>` shows complete hierarchy
- [ ] `bd ready` shows correct first task(s)
- [ ] `bd show <task-id>` shows dependencies
- [ ] No orphaned tasks
- [ ] Task IDs follow hierarchy (bd-XXXX.N.M format)

---

## Related Skills

### Prerequisites
- [`create_documentation_task.md`](create_documentation_task.md) - Create epic first

### Follow-ups
- [`update_task_progress.md`](update_task_progress.md) - Update task status during work
- [`manage_queries.md`](../project_management/manage_queries.md) - Query beads for status

### Related
- [`../documentation/generate_api_docs.md`](../documentation/generate_api_docs.md) - Execute documentation tasks
- [`../code_exploration/analyze_module.md`](../code_exploration/analyze_module.md) - Analyze module structure

---

## Beads Quick Reference

### Commands for Breaking Down Epics

```bash
# Show epic structure
bd show <epic-id>
bd status <epic-id>

# Create phase task
bd create "Phase N: [Title]" \
  --parent <epic-id> \
  --priority <0-9>

# Create subtask
bd create "[Action] [Object]" \
  --parent <phase-id> \
  --priority <0-9>

# Add dependency (child depends on parent)
bd dep add <child-id> <parent-id>

# List ready tasks (no blockers)
bd ready

# Show task with dependencies
bd show <task-id>
```

### Priority Guidelines

| Priority | Use For |
|----------|---------|
| 0 | Critical path, immediate blockers |
| 1 | High priority, enables parallelization |
| 2 | Medium priority, can start after foundation |
| 3+ | Lower priority, optimization, can defer |

---

**Last Updated**: 2026-02-20
**Version**: 1.2
