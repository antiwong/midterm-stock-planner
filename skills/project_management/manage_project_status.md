# Skill: Manage Project Status

**Purpose**: Track and update project documentation status, tasks, and progress metrics

**Category**: project_management

---

## Prerequisites

- Project root directory exists
- Basic understanding of project structure

## Inputs

- **Required**:
  - `project_root`: Root directory path of the project
  - `action`: Action to perform (`init`, `update`, `report`)

- **Optional**:
  - `module_name`: Specific module to update (default: all modules)
  - `status`: New status value (`pending`, `in_progress`, `complete`)
  - `notes`: Additional notes about progress

---

## Process

### Step 1: Initialize Project Status File

Create `PROJECT_STATUS.md` if it doesn't exist.

```bash
# Check if status file exists
ls PROJECT_STATUS.md

# If not exists, create template
```

**Template Structure**:
```markdown
# Project Documentation Status

**Project**: [Project Name]
**Version**: [Version]
**Last Updated**: [Date]

---

## Overall Progress

| Phase | Status | Progress | Notes |
|-------|--------|----------|-------|
| Phase 1: Foundation | ✅ Complete | 100% | Knowledge base, skills, initial docs |
| Phase 2: API Reference | 🔄 In Progress | 60% | 10/17 modules documented |
| Phase 3: User Guides | ⏳ Pending | 0% | Not started |
| Phase 4: Design Docs | ⏳ Pending | 0% | Not started |

**Overall Completion**: 40% (Phase 1 + 60% of Phase 2)

---

## Module Documentation Status

| Module | Files | LOC | API Docs | Docstrings | Examples | Status |
|--------|-------|-----|----------|------------|----------|--------|
| app | 8 | ~1,200 | ✅ | ⏳ | ✅ | Complete |
| analytics | 10 | ~1,800 | ✅ | ⏳ | ✅ | Complete |
| analysis | 9 | ~1,600 | ✅ | ⏳ | ✅ | Complete |
| backtest | 7 | ~1,400 | ✅ | ⏳ | ✅ | Complete |
| models | 6 | ~1,100 | ✅ | ⏳ | ✅ | Complete |
| features | 5 | ~900 | ✅ | ⏳ | ✅ | Complete |
| indicators | 8 | ~1,300 | ✅ | ⏳ | ✅ | Complete |
| sentiment | 4 | ~700 | ✅ | ⏳ | ✅ | Complete |
| risk | 6 | ~1,050 | ✅ | ⏳ | ✅ | Complete |
| fundamental | 5 | ~850 | ✅ | ⏳ | ✅ | Complete |
| data | 7 | ~1,200 | 🔄 | ⏳ | ⏳ | In Progress |
| config | 3 | ~400 | 🔄 | ⏳ | ⏳ | In Progress |
| validation | 4 | ~600 | ⏳ | ⏳ | ⏳ | Pending |
| explain | 5 | ~800 | ⏳ | ⏳ | ⏳ | Pending |
| visualization | 12 | ~2,100 | ⏳ | ⏳ | ⏳ | Pending |
| strategies | 6 | ~1,000 | ⏳ | ⏳ | ⏳ | Pending |
| exceptions | 2 | ~250 | ⏳ | ⏳ | ⏳ | Pending |

---

## Metrics

- **Total Modules**: 17
- **Documented**: 10 (59%)
- **In Progress**: 2 (12%)
- **Pending**: 5 (29%)
- **Lines of Documentation**: ~6,500
- **Code Examples**: ~65

---

## Active Tasks

### High Priority
- [ ] Complete data module documentation
- [ ] Complete config module documentation
- [ ] Review and validate all completed docs

### Medium Priority
- [ ] Document visualization module
- [ ] Document strategies module

### Low Priority
- [ ] Add docstrings to source files
- [ ] Create user guides

---

## Blockers

| Blocker | Impact | Status | Resolution |
|---------|--------|--------|------------|
| Missing function imports in risk module | Medium | Open | See queries.md Q9 |
| Unclear threshold rationale for sentiment scoring | Low | Open | See queries.md Q12 |

---

## Recent Updates

**2026-02-06**:
- Completed fundamental module documentation (850 lines)
- Started data module
- Added 4 queries to queries.md

**2026-02-05**:
- Completed risk module documentation (615 lines)
- Updated README.md with progress indicators

---

**Status Legend**:
- ✅ Complete
- 🔄 In Progress
- ⏳ Pending
- ❌ Blocked
```

### Step 2: Update Module Status

When a module is completed or progress changes:

```python
# Read PROJECT_STATUS.md
# Find the module row in the table
# Update status, checkmarks, and percentages
# Update "Last Updated" timestamp
```

**Example Update**:
```markdown
# Before
| data | 7 | ~1,200 | 🔄 | ⏳ | ⏳ | In Progress |

# After
| data | 7 | ~1,200 | ✅ | ⏳ | ✅ | Complete |
```

### Step 3: Update Overall Progress

Recalculate completion percentages:

```python
# Count modules by status
total_modules = 17
completed = 10
in_progress = 2
pending = 5

# Calculate percentage
completion_pct = (completed / total_modules) * 100  # 59%

# Update table
Phase 2: API Reference | 🔄 In Progress | 59% | 10/17 modules documented
```

### Step 4: Add Recent Update Entry

Add a dated entry to "Recent Updates" section:

```markdown
**2026-02-06**:
- Completed analytics module documentation (850 lines)
- Updated tracking files
- Added 4 new queries to queries.md
```

### Step 5: Update Metrics

Recalculate and update metrics:

```python
# Count:
# - Total modules
# - Documented modules
# - In progress modules
# - Pending modules
# - Total lines of documentation (use wc -l doc/api_reference/*.md)
# - Total code examples (grep -c "```python" doc/api_reference/*.md)
```

### Step 6: Update Blockers (if any)

Add or update blocker entries:

```markdown
| Blocker | Impact | Status | Resolution |
|---------|--------|--------|------------|
| New blocker description | High/Medium/Low | Open | Action items or reference |
```

---

## Outputs

- **Primary**:
  - File: `PROJECT_STATUS.md`
  - Content: Comprehensive project documentation status

- **Updates**:
  - Module status table
  - Progress percentages
  - Metrics
  - Recent updates log

---

## Examples

### Example 1: Initialize New Project

**Input**:
```
project_root: /path/to/new-stock-project
action: init
```

**Process**:
1. Create PROJECT_STATUS.md from template
2. Identify modules from src/ directory
3. Set all modules to "Pending"
4. Initialize metrics to 0%

**Output**:
```
Created: PROJECT_STATUS.md
Status: 0/17 modules documented (0%)
```

### Example 2: Update Module to Complete

**Input**:
```
project_root: /path/to/project
action: update
module_name: app
status: complete
notes: "Documented 4 classes, 15 methods, added 8 examples"
```

**Process**:
1. Read PROJECT_STATUS.md
2. Find "app" row in module table
3. Update status column to ✅
4. Update API Docs, Examples to ✅
5. Add entry to Recent Updates
6. Recalculate percentages

**Output**:
```
Updated: app module → Complete
Progress: 1/17 modules (6%)
Added: Recent update entry for 2026-02-06
```

### Example 3: Generate Progress Report

**Input**:
```
project_root: /path/to/project
action: report
```

**Process**:
1. Read PROJECT_STATUS.md
2. Extract metrics
3. Generate summary report

**Output**:
```
Project Documentation Progress Report
======================================
Project: midterm_stock_planner v3.11.2
Generated: 2026-02-06

Overall Progress: 60%
- Phase 1: ✅ Complete (100%)
- Phase 2: 🔄 In Progress (59%)
- Phase 3: ⏳ Pending (0%)
- Phase 4: ⏳ Pending (0%)

Module Status:
- Completed: 10/17 (59%)
- In Progress: 2/17 (12%)
- Pending: 5/17 (29%)

Documentation Metrics:
- Lines Written: ~6,500
- Code Examples: ~65
- Queries Outstanding: 12

Top Priorities:
1. Complete data module
2. Complete config module
3. Document visualization module
```

---

## Validation

- [ ] PROJECT_STATUS.md exists and is well-formed
- [ ] All modules are listed in the table
- [ ] Percentages sum correctly
- [ ] Recent updates are chronological (newest first)
- [ ] Metrics match actual file counts
- [ ] Status symbols are consistent (✅ 🔄 ⏳ ❌)

---

## Related Skills

- **Prerequisites**: None (this is often the first skill to run)
- **Follow-ups**:
  - `manage_changelog.md` - Track changes over time
  - `update_readme.md` - Update project README with status
  - `manage_queries.md` - Track outstanding questions
- **Alternatives**: Beads task tracking (`beads_integration/` skills)

---

## Tips

1. **Update Frequently**: Update PROJECT_STATUS.md after completing each module (not in batches)
2. **Be Specific**: Add notes about what was completed (e.g., "4 classes, 15 methods")
3. **Track Blockers**: Document blockers immediately when discovered
4. **Reference Queries**: Link blockers to specific queries (e.g., "See queries.md Q9")
5. **Calculate Accurately**: Use automated tools to count lines/examples rather than estimating

---

**Last Updated**: 2026-02-06
**Version**: 1.0
