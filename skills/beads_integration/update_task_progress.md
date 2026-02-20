# Skill: Update Task Progress (Beads)

**Purpose**: Track progress on beads tasks with status updates and notes. Keep tasks synchronized with actual work state.

**Category**: beads_integration

---

## Prerequisites

- Beads initialized in project (`bd init` completed)
- Task already created and claimed (use `create_documentation_task.md` first)
- Familiarity with beads commands (`bd --help`)
- Read [`../../knowledgebase/AGENT_PROMPT.md`](../../knowledgebase/AGENT_PROMPT.md) sections:
  - Task Management with Beads
  - Common Beads Commands
  - AI Agent Workflow with Beads

---

## Inputs

### Required
- **task_id**: Beads task ID to update (e.g., `bd-a1b2.1.2`)
- **status**: New task status from:
  - `in_progress` - Currently working on task
  - `blocked` - Task is blocked by dependencies or external blockers
  - `done` - Task fully complete (100% finished)
  - `cancelled` - Task cancelled (no longer needed)

### Optional
- **notes**: Progress update or blocker description
  - For `in_progress`: What you've done, what's next
  - For `blocked`: Clear description of the blocker
  - For `done`: Summary of completion, key results
  - For `cancelled`: Reason for cancellation

---

## Process

### Step 1: Understand Task Status States

**Status Lifecycle**:
```
OPEN (fresh)
  ↓
READY (no blockers)
  ↓
in_progress (claimed, work started)
  ├→ blocked (external blocker encountered)
  │  ├→ in_progress (blocker resolved, resume work)
  │  └→ cancelled (abandoned due to blocker)
  └→ done (work complete)
```

**Key Principles**:
- Only mark task as `done` when 100% complete
- Never mark `done` if tests fail or errors remain
- Use `blocked` if blocked by dependencies or external issues
- Use `cancelled` only for work that's no longer needed

---

### Step 2: Check Task Status

Before updating, verify the current task state.

**Command**:
```bash
bd show <task-id>
```

**Output includes**:
- Task ID, title, description
- Current status
- Parent and child tasks
- Dependencies (blockers)
- Notes from previous updates
- Claimed by (if applicable)

**Example**:
```bash
$ bd show bd-a1b2.1.2
ID:            bd-a1b2.1.2
Title:         Create generate_api_docs skill
Status:        in_progress
Parent:        bd-a1b2.1
Dependencies:  bd-a1b2.1.1 (Write AGENT_PROMPT.md)
Notes:         Working on skill structure
Claimed by:    claude-agent
```

---

### Step 3: Update Task Status

Use `bd update` to change task status.

**Basic Command Syntax**:
```bash
bd update <task-id> --status <new-status> [--note "message"]
```

**Common Status Updates**:

#### 3a. Mark as In Progress (Starting Work)
```bash
bd update <task-id> --status in_progress \
  --note "Starting work on this task"
```

Use this when:
- Starting work on a claimed task
- Resuming work after a break

#### 3b. Add Progress Notes (During Work)
```bash
bd update <task-id> --note "Completed X, working on Y next"
```

Use this to:
- Document what you've completed
- Explain what's next
- Record decisions made
- Note any challenges encountered

**Guidelines for Progress Notes**:
- Be specific (what was done, not just "working on it")
- Keep notes concise but informative
- Update frequently (every hour or after major milestones)
- Include blockers or decisions that affect timeline

**Example Progress Updates**:
```bash
# Good: Specific and actionable
bd update bd-a1b2.1.2 --note "Analyzed module structure, identified 3 key classes to document"

# Good: Clear next steps
bd update bd-a1b2.1.2 --note "API reference outline complete, now writing detailed examples"

# Good: Decision documentation
bd update bd-a1b2.1.2 --note "Switched to Google-style docstrings per project convention"

# Bad: Vague
bd update bd-a1b2.1.2 --note "still working"
```

#### 3c. Mark as Blocked (Encountered Blocker)
```bash
bd update <task-id> --status blocked \
  --note "Blocked by: <clear description of blocker>"
```

Use this when:
- Hit a dependency that's not ready
- External dependency required (data, tool, decision)
- Waiting for review or feedback
- Technical blocker discovered

**Blocker Note Format**:
```
Blocked by: [What is blocking work?]
Expected resolution: [When will it be resolved?]
Workaround: [Any temporary workaround, if available]
```

**Examples**:
```bash
# Blocked by dependency
bd update bd-a1b2.1.3 --status blocked \
  --note "Blocked by: bd-a1b2.1.2 (generate_api_docs skill) not yet complete. Expected: 2026-02-10"

# Blocked by external resource
bd update bd-a1b2.2.1 --status blocked \
  --note "Blocked by: Need backtest module source code review. Waiting for feedback from team."

# Blocked by technical issue
bd update bd-a1b2.1.4 --status blocked \
  --note "Blocked by: Python import error in analytics module. Created separate task bd-a1b2.4.1 to fix."
```

#### 3d. Mark as Done (Completion)
```bash
bd update <task-id> --status done \
  --note "Completed: [Summary of what was done]"
```

Use this ONLY when:
- All work items are 100% complete
- All tests pass
- All reviewers satisfied
- All deliverables checked
- No known issues remain

**Completion Note Format**:
```
Completed: [What was delivered]
Key results: [Specific outputs, metrics, or achievements]
Files created: [List of new files or modifications]
Tests: [Pass/Fail status]
```

**Examples**:
```bash
# Good: Complete with details
bd update bd-a1b2.1.1 --status done \
  --note "Completed: AGENT_PROMPT.md written with full project context. Key results: 450+ lines covering architecture, workflows, and references. File: knowledgebase/AGENT_PROMPT.md. All sections verified."

# Good: Specific deliverables
bd update bd-a1b2.1.2 --status done \
  --note "Completed: generate_api_docs skill created. Files: skills/documentation/generate_api_docs.md. Tested with analytics module documentation. All prerequisites and process steps documented."

# Bad: Vague completion
bd update bd-a1b2.1.1 --status done --note "done"
```

#### 3e. Mark as Cancelled (No Longer Needed)
```bash
bd update <task-id> --status cancelled \
  --note "Cancelled because: <reason>"
```

Use this when:
- Task scope changed and no longer needed
- Duplicate of another task
- Requirements no longer apply
- Project priorities shifted

---

### Step 4: Handle Task Dependencies

If you encounter blockers from task dependencies:

**Check Dependencies**:
```bash
bd show <task-id> | grep -i depend
```

**Handling Blockers**:

**Option 1: Task is Genuinely Ready**
If the dependency should be marked as done, coordinate with team:
```bash
bd update <blocking-task-id> --status done
```

**Option 2: Create New Blocker Task**
If the blocker is a sub-issue:
```bash
bd create "Fix blocker for <original-task>" \
  --parent <epic-id> \
  --priority 0 \
  --description "Blocker preventing <original-task-id>: <blocker description>"
```

Then mark original as blocked:
```bash
bd update <original-task-id> --status blocked \
  --note "Blocked by new task bd-xxxx to resolve <blocker>"
```

**Option 3: Create Workaround**
Document the workaround:
```bash
bd update <task-id> --note "Proceeding with workaround: <description>. Related task: <blocker-id>"
```

---

### Step 5: Verify Status Update

After updating, verify the change was recorded correctly.

**Command**:
```bash
bd show <task-id>
```

**Verification**:
- [ ] Status changed to requested value
- [ ] Note recorded with update timestamp
- [ ] Parent/child relationships intact
- [ ] Dependencies unchanged (unless intentional)

---

## Outputs

### Primary
- **Updated Task Record**: Task status and notes stored in `.beads/` JSONL files
- **Git History**: Beads changes recorded in git commits
- **Status Tracking**: History of all status updates for the task

### Secondary
- **Progress Visibility**: Team can track task progress via `bd show`
- **Blocker Documentation**: Clear record of what's blocking work
- **Completion Records**: Audit trail of completed work

---

## Examples

### Example 1: In-Progress Task with Progress Notes

**Scenario**: Working on API documentation task, making steady progress

**Session 1 - Start Work**:
```bash
$ bd update bd-a1b2.2.1 --status in_progress \
  --note "Starting API reference for backtest module. Analyzing source files."

# Output: Task bd-a1b2.2.1 updated
```

**Session 2 - Mid-Progress**:
```bash
$ bd show bd-a1b2.2.1
# ... shows in_progress status

$ bd update bd-a1b2.2.1 --note "Completed class documentation (Map, Lane, Divider). Working on methods documentation next."

# Output: Progress note added
```

**Session 3 - Nearly Done**:
```bash
$ bd update bd-a1b2.2.1 --note "All classes documented. Working on examples and cross-references. Est. 1-2 hours remaining."
```

**Session 4 - Completion**:
```bash
$ bd update bd-a1b2.2.1 --status done \
  --note "Completed: Backtest module API reference (docs/api_reference/backtest.md). All 8 classes documented with 15+ code examples. 2,100+ lines. Tests: All references verified. Ready for review."

# Output: Task bd-a1b2.2.1 status changed to done
```

---

### Example 2: Task Blocked by Dependency

**Scenario**: Task depends on another incomplete task

**Initial Status**:
```bash
$ bd show bd-a1b2.1.3
Status: open
Note: waiting to start
```

**Hit Blocker**:
```bash
$ bd update bd-a1b2.1.3 --status blocked \
  --note "Blocked by: bd-a1b2.1.1 (analytics module analysis) not yet complete. Cannot document without understanding module. Expected resolution: 2026-02-08"

# Output: Task bd-a1b2.1.3 marked as blocked
```

**Blocker Resolved**:
```bash
$ bd show bd-a1b2.1.1
Status: done

$ bd update bd-a1b2.1.3 --status in_progress \
  --note "Blocker bd-a1b2.1.1 now complete. Resuming work on documentation."

# Output: Task bd-a1b2.1.3 status changed to in_progress
```

---

### Example 3: Task with Technical Blocker

**Scenario**: Encountered technical issue requiring additional work

**Hit Issue**:
```bash
$ bd update bd-a1b2.3.2 --status blocked \
  --note "Blocked by: Technical issue - analytics module imports failing. Cannot proceed with testing. Creating subtask bd-a1b2.3.2.1 to debug."
```

**Created Subtask**:
```bash
# Create blocker task
$ bd create "Debug: Fix analytics module import error" \
  --parent bd-a1b2.3.2 \
  --priority 0 \
  --description "scene.py failing to import due to missing dependency"

# Output: bd-a1b2.3.2.1

# Update original with blocker
$ bd update bd-a1b2.3.2 --note "Created blocker task bd-a1b2.3.2.1 to resolve import error"
```

---

### Example 4: Cancelled Task

**Scenario**: Requirements changed, task no longer needed

**Initial Decision**:
```bash
$ bd show bd-a1b2.4.3
Status: in_progress
Title: Create custom visualization module
```

**Requirements Changed**:
```bash
$ bd update bd-a1b2.4.3 --status cancelled \
  --note "Cancelled because: Team decided to use existing matplotlib wrapper instead of custom module. Duplicate effort. Replaced by bd-a1b2.4.4 (integrate matplotlib)"

# Output: Task bd-a1b2.4.3 marked as cancelled
```

---

## Validation Checklist

Before marking a task as `done`, verify:

- [ ] **Status Reflects Reality**: Task status matches actual work state
- [ ] **Notes Explain What Was Done**: Clear description of deliverables
- [ ] **All Outputs Complete**: Verify files created, code written, tests run
- [ ] **No Blockers Remain**: Confirm task is fully unblocked
- [ ] **Quality Standards Met**: Code/docs meet project standards
- [ ] **Tests Pass**: All tests passing, no errors
- [ ] **Review Requirements Met**: If applicable, review completed
- [ ] **Dependencies Satisfied**: Child tasks can proceed
- [ ] **Documentation Updated**: Related docs/READMEs updated if needed
- [ ] **Commit/Version**: Changes committed to git if applicable

---

### Validation for Blocked Tasks

- [ ] **Blocker Clearly Documented**: Note explains exactly what's blocking
- [ ] **Expected Timeline**: Note includes when blocker will resolve
- [ ] **Dependency Chain Clear**: If blocked by another task, that task ID is referenced
- [ ] **No Self-Blockers**: Task doesn't block itself through dependencies

---

### Validation for Progress Notes

- [ ] **Specific, Not Vague**: Note describes specific work, not just "working on it"
- [ ] **Actionable**: Next reader understands what to do next
- [ ] **Honest About Progress**: Realistic assessment, not over/understating
- [ ] **Timestamped Naturally**: Update adds to story of progress

---

## Related Skills

### Prerequisites
- [`create_documentation_task.md`](create_documentation_task.md) - Create beads tasks first

### Follow-ups
- [`break_down_epic.md`](break_down_epic.md) - Decompose epics into subtasks
- Project-specific skills in `../documentation/`, `../code_exploration/`, etc.

### Related
- Beads documentation: https://github.com/steveyegge/beads

---

## Beads Quick Reference

### Status Update Commands
```bash
# Mark as in progress
bd update <task-id> --status in_progress

# Add progress note
bd update <task-id> --note "what was done"

# Mark as blocked
bd update <task-id> --status blocked --note "blocker description"

# Mark as done
bd update <task-id> --status done --note "completion summary"

# Mark as cancelled
bd update <task-id> --status cancelled --note "reason"

# Show task details
bd show <task-id>

# List ready tasks (no blockers)
bd ready

# Show task tree
bd status <epic-id>
```

### Task Status Meanings
```
open      - Created but not yet started
in_progress - Work in progress
blocked   - Waiting for blocker to resolve
done      - Work complete
cancelled - No longer needed
```

---

**Last Updated**: 2026-02-12
**Version**: 1.2
