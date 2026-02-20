# Skills - midterm_stock_planner

**Purpose**: Task-oriented, reusable guides for AI agents to perform tasks managed through [beads](https://github.com/steveyegge/beads).

**Warning**: All work on this project is managed through beads. Always start with `bd ready` to find available tasks.

---

## What Are Skills?

Skills are **step-by-step instruction guides** that AI agents follow to perform specific tasks. Each skill contains:
- **Purpose**: What the skill accomplishes
- **Prerequisites**: Required knowledge or files
- **Inputs**: Required and optional parameters
- **Process**: Numbered steps with commands and examples
- **Outputs**: What files get created or updated
- **Examples**: Sample invocations and expected results
- **Validation**: Checklist to verify success
- **Related Skills**: Dependencies and follow-up skills

Skills are **task-oriented** (not module-oriented) for maximum reusability. Agents can compose multiple skills into custom workflows.

---

## Skills Index

### Documentation Skills (`documentation/`)

| Skill | Purpose | When to Use |
|-------|---------|-------------|
| **[generate_api_docs.md](documentation/generate_api_docs.md)** | Create API reference for a module | Documenting classes/functions in a module |
| **[add_docstrings.md](documentation/add_docstrings.md)** | Add docstrings to source files | Adding in-code documentation (Google-style for Python) |
| **[generate_component_design.md](documentation/)** | Create component design document | Writing architectural documentation |
| **[generate_algorithm_design.md](documentation/)** | Create algorithm design document | Documenting complex algorithms |
| **[update_api_reference.md](documentation/)** | Update existing API documentation | Refreshing docs after code changes |
| **[generate_sar_behavior_scenario.md](documentation/generate_sar_behavior_scenario.md)** | Create SAR behavior scenario document | Documenting safety analysis for a behavior |
| **[generate_safety_interaction_diagram.md](documentation/generate_safety_interaction_diagram.md)** | Create safety interaction diagram with risk register | Documenting inter-module data flows and risks |

### Code Exploration Skills (`code_exploration/`)

| Skill | Purpose | When to Use |
|-------|---------|-------------|
| **[analyze_module.md](code_exploration/analyze_module.md)** | Understand module structure and patterns | Before documenting a module |
| **[trace_data_flow.md](code_exploration/)** | Trace data through processing pipeline | Understanding end-to-end workflows |
| **[find_dependencies.md](code_exploration/)** | Identify module dependencies | Understanding module relationships |
| **[summarize_functions.md](code_exploration/)** | Summarize function purposes | Quick overview of module capabilities |

### Project Management Skills (`project_management/`)

| Skill | Purpose | When to Use |
|-------|---------|-------------|
| **[manage_project_status.md](project_management/manage_project_status.md)** | Track documentation progress and status | Throughout project, update after milestones |
| **[manage_changelog.md](project_management/manage_changelog.md)** | Track all documentation changes | After every documentation change |
| **[manage_queries.md](project_management/manage_queries.md)** | Track questions and uncertainties | When encountering unclear items |
| **[update_readme.md](project_management/update_readme.md)** | Update project README with status | After completing phases or modules |

### Beads Integration Skills (`beads_integration/`)

| Skill | Purpose | When to Use |
|-------|---------|-------------|
| **[create_documentation_task.md](beads_integration/create_documentation_task.md)** | Create beads task for documentation | Starting a new documentation effort |
| **[break_down_epic.md](beads_integration/)** | Break epic into subtasks with dependencies | Planning large documentation projects |
| **[update_task_progress.md](beads_integration/)** | Update task status and notes | Tracking work progress |
### Requirements Engineering Skills (`requirements/`)

| Skill | Purpose | When to Use |
|-------|---------|-------------|
| **[manage_requirements.md](requirements/manage_requirements.md)** | Generate, trace, and gap-analyse software requirements | `/requirements generate <subsystem>`, `/requirements trace <REQ-ID>`, `/requirements gap <subsystem>` |

### Validation Skills (`validation/`)

| Skill | Purpose | When to Use |
|-------|---------|-------------|
| **[check_doc_coverage.md](validation/)** | Verify documentation completeness | After documenting modules |
| **[validate_examples.md](validation/)** | Test that code examples run | After adding code examples |
| **[validate_sar_document.md](validation/validate_sar_document.md)** | Validate SAR document against codebase | After creating/updating SAR documents |

---

## How to Use Skills

### For AI Agents (PRIMARY WORKFLOW)

**Every Session Must Follow This**:
1. **`bd ready`** - Find available tasks (FIRST command every session)
2. **`bd update <task-id> --claim --status in_progress`** - Claim before starting
3. **Load context** - Read [`../knowledgebase/AGENT_PROMPT.md`](../knowledgebase/AGENT_PROMPT.md)
4. **Select skill** - Choose appropriate skill from this index based on task
5. **Follow skill instructions** - Execute steps in order
6. **Validate** - Use validation skills to check quality
7. **`bd update <task-id> --status done`** - Mark complete (only when 100% done)
8. **Repeat** - Go back to step 1 for next task

**Critical**: NEVER work on tasks without claiming them first. NEVER mark tasks as done if they're incomplete.

**Example: Document the Backtest Module**
```
1. Load context: Read knowledgebase/AGENT_PROMPT.md
2. Identify task: "Document walk-forward backtest engine"
3. Select skills:
   a. code_exploration/analyze_module.md
   b. documentation/generate_api_docs.md
   c. documentation/add_docstrings.md
   d. validation/check_doc_coverage.md
4. Execute skills in order
5. Validate: Check all classes/functions documented
6. Mark complete: bd update <task-id> --status done
```

### For Human Developers

Skills can serve as:
- **Checklists** for manual documentation work
- **Templates** for consistent documentation
- **Reference** for best practices

---

## Skill Categories

### 1. Documentation Skills

**Purpose**: Create and maintain documentation files (API reference, design docs, user guides)

**Common Pattern**:
1. Analyze source code
2. Extract information (signatures, parameters, returns)
3. Write formatted documentation
4. Add code examples
5. Validate completeness

**Output**: Markdown files in `docs/`

---

### 2. Code Exploration Skills

**Purpose**: Understand codebase structure, patterns, and relationships

**Common Pattern**:
1. List files in module
2. Read source code
3. Identify patterns (classes, functions, imports)
4. Summarize findings
5. Document insights

**Output**: Analysis notes (not saved to files, used for context)

---

### 3. Beads Integration Skills (REQUIRED FOR ALL WORK)

**Purpose**: Manage ALL project tasks using beads (git-backed task tracker)

**Why Beads**:
- Persistent memory across sessions
- Dependency tracking (no working on blocked tasks)
- Multi-agent coordination
- Git-backed (version controlled in `.beads/`)
- Hash IDs prevent merge conflicts

**Commands Reference**:
```bash
bd ready              # Find tasks with no blockers
bd list               # See all tasks
bd status             # Check overall progress
bd show <task-id>     # View task details
bd create "Task"      # Create new task
bd update <id> ...    # Update task status/notes
bd dep add <a> <b>    # Add dependency (a blocks b)
```

---

### 4. Validation Skills

**Purpose**: Verify documentation quality and completeness

**Common Pattern**:
1. Check coverage (all APIs documented?)
2. Test examples (do they run?)
3. Validate links (do they work?)
4. Report findings

**Output**: Coverage reports, error lists

---

## Skill Composition

Skills can be **composed** into multi-step workflows:

### Workflow 1: Document a New Module
```
1. code_exploration/analyze_module.md
   -> Understand module structure

2. documentation/generate_api_docs.md
   -> Create docs/api_reference/<module>.md

3. documentation/add_docstrings.md
   -> Add Google-style docstrings to Python files

4. validation/check_doc_coverage.md
   -> Verify completeness
```

### Workflow 2: Create Component Design
```
1. code_exploration/analyze_module.md
   -> Understand component architecture

2. code_exploration/find_dependencies.md
   -> Identify module dependencies

3. documentation/generate_component_design.md
   -> Create docs/design/2_component_designs/<component>.md

4. Validate manually
   -> Check Document ID, Mermaid diagrams, footer
```

### Workflow 3: Large Documentation Project with Beads
```
1. beads_integration/create_documentation_task.md
   -> Create epic: "Document midterm_stock_planner"

2. beads_integration/break_down_epic.md
   -> Create subtasks for each module

3. Loop for each module:
   a. bd ready (find unblocked tasks)
   b. bd update <task-id> --claim
   c. code_exploration/analyze_module.md
   d. documentation/generate_api_docs.md
   e. documentation/add_docstrings.md
   f. validation/check_doc_coverage.md
   g. bd update <task-id> --status done

4. beads_integration/update_task_progress.md
   -> Add notes to epic with progress summary
```

---

## Creating New Skills

If you need to create a new skill, follow the template in the existing skills files. Each skill should include Purpose, Prerequisites, Inputs, Process, Outputs, Examples, Validation, and Related Skills sections.

---

## Skills Directory Structure

```
skills/
├── README.md                              # THIS FILE - Skills index
│
├── documentation/                         # Documentation creation skills
│   ├── generate_api_docs.md
│   ├── add_docstrings.md
│   ├── generate_component_design.md
│   ├── generate_algorithm_design.md
│   ├── update_api_reference.md
│   ├── generate_sar_behavior_scenario.md
│   └── generate_safety_interaction_diagram.md
│
├── code_exploration/                      # Code analysis skills
│   ├── analyze_module.md
│   ├── trace_data_flow.md
│   ├── find_dependencies.md
│   └── summarize_functions.md
│
├── beads_integration/                     # Task management skills
│   ├── create_documentation_task.md
│   ├── break_down_epic.md
│   └── update_task_progress.md
│
├── requirements/                          # Requirements engineering skills
│   └── manage_requirements.md
│
└── validation/                            # Quality check skills
    ├── check_doc_coverage.md
    ├── validate_examples.md
    └── validate_sar_document.md
```

---

## Quick Reference

### "I need to..." -> "Use this skill:"

- Understand a module before documenting -> `code_exploration/analyze_module.md`
- Create API reference for a module -> `documentation/generate_api_docs.md`
- Add docstrings to source files -> `documentation/add_docstrings.md`
- Create component design document -> `documentation/generate_component_design.md`
- Create algorithm design document -> `documentation/generate_algorithm_design.md`
- Update existing API docs -> `documentation/update_api_reference.md`
- Trace data through pipeline -> `code_exploration/trace_data_flow.md`
- Find module dependencies -> `code_exploration/find_dependencies.md`
- Create beads task -> `beads_integration/create_documentation_task.md`
- Break epic into subtasks -> `beads_integration/break_down_epic.md`
- Update task progress -> `beads_integration/update_task_progress.md`
- Verify documentation coverage -> `validation/check_doc_coverage.md`
- Test code examples -> `validation/validate_examples.md`
- Generate requirements for a subsystem -> `requirements/manage_requirements.md` (mode: generate)
- Trace a requirement to code -> `requirements/manage_requirements.md` (mode: trace)

---

## Related Documentation

- **Project Context**: See [`../knowledgebase/AGENT_PROMPT.md`](../knowledgebase/AGENT_PROMPT.md) for comprehensive project overview
- **Module Overviews**: See [`../knowledgebase/module_summaries.md`](../knowledgebase/module_summaries.md) for module responsibilities
- **Domain Terms**: See [`../knowledgebase/glossary.md`](../knowledgebase/glossary.md) for terminology
- **Documentation Guidelines**: See [`../prompt/documentation_guidelines.md`](../prompt/documentation_guidelines.md) for design doc standards
- **Beads Documentation**: See [github.com/steveyegge/beads](https://github.com/steveyegge/beads) for beads usage

---

**Last Updated**: 2026-02-20
**Version**: 3.11.2
