# Skill: Update README

**Purpose**: Update project README.md with documentation status, progress, and navigation links

**Category**: project_management

---

## Prerequisites

- Project root directory exists
- README.md exists (or will be created from template)
- Documentation structure is established

## Inputs

- **Required**:
  - `project_root`: Root directory path of the project
  - `action`: Action to perform (`init`, `update`, `status`, `links`)

- **Optional**:
  - `section`: Specific section to update (`quickstart`, `documentation`, `architecture`, `status`)
  - `progress_pct`: Overall documentation progress percentage
  - `phase_status`: Status of current phase

---

## Process

### Step 1: Identify README Structure

Standard README.md structure for AV projects:

```markdown
# [Project Name]

**Version**: [Version]
**Python**: [Required Python version]
**Status**: [Development/Production/Beta]
**Documentation**: [Links to doc folders]

[Brief description - 1-2 sentences]

---

## 🚀 Quick Start

[Installation and basic usage]

---

## 📚 Documentation

### For Developers
[Links to API reference, user guides, design docs with status indicators]

### For AI Agents
[Links to knowledge base, skills, prompts]

---

## 🏗️ Architecture

[System overview, module breakdown]

---

## 🔧 Development

[Development setup, testing, contributing]

---

## 📊 Project Status

[Documentation progress, completed modules, current phase]

---

## 📝 License

[License information]
```

### Step 2: Update Documentation Status Section

Update the "📚 Documentation" section with current progress:

```markdown
## 📚 Documentation

### For Developers

| Resource | Purpose | Status |
|----------|---------|--------|
| **[API Reference](doc/api_reference/)** | Function/class reference | ✅ 10/10 modules (100%) |
| **[User Guides](doc/user_guides/)** | Step-by-step tutorials | ⏳ Coming soon |
| **[Design Documentation](doc/design/)** | Architecture details | ⏳ Coming soon |

**Start here**: [doc/README.md](doc/README.md) - Documentation hub

### For AI Agents

| Resource | Purpose |
|----------|---------|
| **[AGENT_PROMPT.md](knowledgebase/AGENT_PROMPT.md)** | Complete system prompt |
| **[Module Summaries](knowledgebase/module_summaries.md)** | Quick module reference |
| **[Glossary](knowledgebase/glossary.md)** | Domain terminology |
| **[Skills](skills/)** | Task-oriented guides |

**Start here**: [knowledgebase/README.md](knowledgebase/README.md)
```

**Status Indicators**:
- ✅ Complete
- 🔄 In Progress (X%)
- ⏳ Pending / Coming soon
- ❌ Blocked

### Step 3: Update Project Status Section

Add or update a "📊 Project Status" section:

```markdown
## 📊 Project Status

### Documentation Progress

**Overall**: 65% complete

| Phase | Status | Progress |
|-------|--------|----------|
| Phase 1: Foundation | ✅ Complete | 100% |
| Phase 2: API Reference | ✅ Complete | 100% (10/10 modules) |
| Phase 3: User Guides | 🔄 In Progress | 33% (2/6 guides) |
| Phase 4: Design Docs | ⏳ Pending | 0% |

### Recent Updates

**2026-02-06**:
- ✅ Completed Phase 2: All 17 modules documented (~8,500 lines)
- 🔄 Started Phase 3: Quickstart guide in progress
- 📝 Added 12 queries to queries.md for clarification

**2026-02-05**:
- ✅ Completed risk module documentation (620 lines)
- ✅ Completed visualization module documentation (800 lines)

### Next Milestones

- [ ] Complete Phase 3: User Guides (target: 2026-02-10)
- [ ] Begin Phase 4: Design Documentation
- [ ] Add docstrings to source files (80% coverage target)

See [PROJECT_STATUS.md](PROJECT_STATUS.md) for detailed progress tracking.
```

### Step 4: Update Architecture Section

Ensure module list is up-to-date:

```markdown
## 🏗️ Architecture

### System Overview

```
[project-name] (XX files, ~XX,XXX LOC)
│
├── module1/     → [Brief description]
├── module2/     → [Brief description]
├── module3/     → [Brief description]
└── ...
```

### Module Breakdown

| Module | Files | LOC | Status | Purpose |
|--------|-------|-----|--------|---------|
| module1 | 12 | ~1,500 | ✅ | [Brief purpose] |
| module2 | 15 | ~2,200 | ✅ | [Brief purpose] |
| ... | ... | ... | ... | ... |

**Total**: XX files, ~XX,XXX lines of code
```

### Step 5: Add/Update Links

Verify all documentation links work:

```bash
# Check for broken links in README.md
# Common link patterns:
# - [Text](doc/folder/file.md)
# - [Text](knowledgebase/file.md)
# - [Text](skills/category/file.md)

# Verify files exist
ls doc/api_reference/README.md
ls knowledgebase/AGENT_PROMPT.md
ls skills/README.md
```

### Step 6: Update Version and Dates

Update version number and last updated date:

```markdown
# [Project Name]

**Version**: 1.7.0  <!-- Update this -->
**Last Updated**: 2026-02-06  <!-- Update this -->
```

---

## Outputs

- **Primary**:
  - File: `README.md`
  - Content: Updated project overview with current documentation status

- **Updates**:
  - Documentation status table
  - Progress percentages
  - Recent updates
  - Module breakdown
  - Links to documentation

---

## Examples

### Example 1: Initialize README for New Project

**Input**:
```
project_root: /path/to/new-av-project
action: init
```

**Process**:
1. Create README.md from template
2. Populate project name and basic info
3. Create placeholder sections
4. Set all progress to 0%

**Output**:
```
Created: README.md
Sections: Quick Start, Documentation, Architecture, Status
Status: 0% (no documentation yet)
```

### Example 2: Update Documentation Status

**Input**:
```
project_root: /path/to/project
action: status
progress_pct: 60
phase_status: "Phase 2: 6/10 modules"
```

**Process**:
1. Read README.md
2. Find "📚 Documentation" section
3. Update API Reference status line
4. Update progress percentage
5. Save file

**Output**:
```
Updated README.md:
- API Reference: 6/10 modules (60%)
- Overall progress: 60%
```

### Example 3: Update Links After Restructuring

**Input**:
```
project_root: /path/to/project
action: links
```

**Process**:
1. Read README.md
2. Extract all markdown links
3. Verify target files exist
4. Update broken links
5. Report status

**Output**:
```
Checked 25 links in README.md:
- Valid: 23 (92%)
- Broken: 2 (8%)
  - doc/user_guides/quickstart.md (not yet created)
  - doc/design/architecture.md (not yet created)

Updated: Changed "Coming soon" status for broken links
```

### Example 4: Add Recent Update Entry

**Input**:
```
project_root: /path/to/project
action: update
section: status
update_text: "Completed visualization module documentation (800 lines)"
```

**Process**:
1. Read README.md
2. Find "### Recent Updates" subsection
3. Add dated entry at top (newest first)
4. Save file

**Output**:
```
Added to README.md → Recent Updates:

**2026-02-06**:
- ✅ Completed visualization module documentation (800 lines)
```

---

## Validation

- [ ] README.md exists and is well-formed
- [ ] All sections are present (Quick Start, Documentation, Architecture, Status)
- [ ] Documentation status table is accurate
- [ ] Progress percentages match PROJECT_STATUS.md
- [ ] All documentation links are valid
- [ ] Recent updates are chronological (newest first)
- [ ] Version number matches pyproject.toml
- [ ] Last updated date is current

---

## Related Skills

- **Prerequisites**:
  - `manage_project_status.md` - Get accurate progress data
  - `manage_changelog.md` - Get recent changes for updates section
- **Follow-ups**: None (README is typically the last thing updated)
- **Alternatives**: None (README.md is standard)

---

## Tips

1. **Update After Milestones**: Update README after completing each phase or major module
2. **Keep It High-Level**: README is an overview, not detailed documentation
3. **Maintain Links**: Verify links work, especially after restructuring
4. **Show Progress**: Use status indicators (✅ 🔄 ⏳) for visual clarity
5. **Highlight Recent Work**: Add recent updates to keep README fresh
6. **Link to Details**: Point to PROJECT_STATUS.md, CHANGELOG.md for full details
7. **Be Consistent**: Use same status symbols across all documentation

---

## README Template for New AV Projects

```markdown
# [Project Name]

**Version**: 0.1.0
**Python**: ≥3.9
**Status**: Development
**Documentation**: [doc/](doc/) | [Knowledge Base](knowledgebase/) | [Skills](skills/)

[One sentence: What does this project do?]

[One sentence: Why does it exist?]

---

## 🚀 Quick Start

### Installation

```bash
git clone <repository-url>
cd <project-name>

# Install with uv (recommended)
uv sync

# Or with pip
pip install -e .
```

### Basic Usage

```python
# Show a simple example (3-5 lines)
from project_name import MainClass

obj = MainClass(config="config.yaml")
result = obj.process(data)
```

**→ See [Quickstart Guide](doc/user_guides/quickstart.md) for detailed tutorial**

---

## 📚 Documentation

### For Developers

| Resource | Purpose | Status |
|----------|---------|--------|
| **[API Reference](doc/api_reference/)** | Function/class reference | ⏳ 0/X modules |
| **[User Guides](doc/user_guides/)** | Step-by-step tutorials | ⏳ Coming soon |
| **[Design Documentation](doc/design/)** | Architecture details | ⏳ Coming soon |

**Start here**: [doc/README.md](doc/README.md)

### For AI Agents

| Resource | Purpose |
|----------|---------|
| **[AGENT_PROMPT.md](knowledgebase/AGENT_PROMPT.md)** | Complete system prompt |
| **[Module Summaries](knowledgebase/module_summaries.md)** | Quick reference |
| **[Glossary](knowledgebase/glossary.md)** | Domain terminology |
| **[Skills](skills/)** | Task-oriented guides |

**Start here**: [knowledgebase/README.md](knowledgebase/README.md)

---

## 🏗️ Architecture

### System Overview

```
<project-name> (XX files, ~X,XXX LOC)
│
├── module1/     → [Purpose]
├── module2/     → [Purpose]
└── ...
```

### Module Breakdown

| Module | Files | LOC | Purpose |
|--------|-------|-----|---------|
| module1 | X | ~XXX | [Purpose] |
| module2 | X | ~XXX | [Purpose] |

---

## 🔧 Development

### Setup

```bash
# Install development dependencies
uv sync --all-extras

# Run tests
pytest

# Run linters
ruff check .
mypy .
```

### Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 📊 Project Status

### Documentation Progress

**Overall**: 0% complete

| Phase | Status | Progress |
|-------|--------|----------|
| Phase 1: Foundation | ⏳ Pending | 0% |
| Phase 2: API Reference | ⏳ Pending | 0% |
| Phase 3: User Guides | ⏳ Pending | 0% |
| Phase 4: Design Docs | ⏳ Pending | 0% |

See [PROJECT_STATUS.md](PROJECT_STATUS.md) for details.

---

## 📝 License

[License type and link]

---

**Last Updated**: [Date]
```

---

**Last Updated**: 2026-02-06
**Version**: 1.0
