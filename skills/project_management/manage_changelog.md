# Skill: Manage Changelog

**Purpose**: Track all documentation changes in a structured changelog following Keep a Changelog format

**Category**: project_management

---

## Prerequisites

- Project root directory exists
- Basic understanding of semantic versioning

## Inputs

- **Required**:
  - `project_root`: Root directory path of the project
  - `action`: Action to perform (`init`, `add`, `release`)

- **Optional**:
  - `version`: Version number for release (default: Unreleased)
  - `change_type`: Type of change (`added`, `changed`, `deprecated`, `removed`, `fixed`, `security`)
  - `description`: Description of the change

---

## Process

### Step 1: Initialize Changelog

Create `CHANGELOG.md` if it doesn't exist, following [Keep a Changelog](https://keepachangelog.com/) format.

```bash
# Check if changelog exists
ls CHANGELOG.md

# If not exists, create from template
```

**Template Structure**:
```markdown
# Changelog

All notable changes to the midterm_stock_planner documentation will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial changelog

---

## How to Use This Changelog

### For AI Agents
- **Before starting work**: Read [Unreleased] to see recent changes
- **After completing work**: Add your changes to [Unreleased] section
- **Use proper categories**: Added, Changed, Deprecated, Removed, Fixed, Security

### For Developers
- Check [Unreleased] to see what's new since last release
- Review version history to understand documentation evolution

### Categories

- **Added**: New documentation, examples, or sections
- **Changed**: Updates to existing documentation
- **Deprecated**: Documentation marked for removal
- **Removed**: Deleted documentation or files
- **Fixed**: Corrections to errors or typos
- **Security**: Security-related documentation changes

---

## [Unreleased]

### Added
- Nothing yet

### Changed
- Nothing yet

### Fixed
- Nothing yet

---

## [1.0.0] - 2026-02-06

### Added
- Initial project documentation structure
- Knowledge base with AGENT_PROMPT.md (991 lines)
- Skills folder with 8 task-oriented guides
- API reference for 17 modules (~8,500 lines)
  - app module (450 lines)
  - analytics module (680 lines)
  - analysis module (520 lines)
  - backtest module (750 lines)
  - models module (600 lines)
  - features module (550 lines)
  - indicators module (480 lines)
  - sentiment module (350 lines)
  - risk module (620 lines)
  - fundamental module (400 lines)
  - data module (380 lines)
  - config module (250 lines)
  - validation module (320 lines)
  - explain module (450 lines)
  - visualization module (800 lines)
  - strategies module (550 lines)
  - exceptions module (150 lines)
- Project README with quickstart guide
- queries.md with 12 outstanding questions

### Changed
- N/A (initial release)

### Fixed
- N/A (initial release)

---

[Unreleased]: https://github.com/org/repo/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/org/repo/releases/tag/v1.0.0
```

### Step 2: Add Change Entry

Add a new entry to the [Unreleased] section under the appropriate category.

**Categories**:
- **Added**: New files, sections, documentation
- **Changed**: Updates to existing content
- **Deprecated**: Marked for removal
- **Removed**: Deleted content
- **Fixed**: Corrections, typos, errors
- **Security**: Security-related changes

**Format**:
```markdown
### Added
- New entry here
- Another new entry
```

### Step 3: Write Descriptive Entries

Follow these guidelines for good changelog entries:

**Good Examples**:
```markdown
### Added
- API reference for visualization module (800 lines) with portfolio chart examples
- 15 code examples to backtest module documentation
- Skill: manage_project_status.md for tracking documentation progress

### Changed
- Updated AGENT_PROMPT.md with generic template for reusability (was project-specific)
- Revised risk module documentation to clarify VaR and CVaR calculations
- Improved code examples in analytics module with error handling

### Fixed
- Corrected typo in models module: "predcit_rankings" → "predict_rankings"
- Fixed broken link in README.md to docs/user_guides/
- Resolved inconsistent heading levels in backtest.md
```

**Bad Examples** (avoid these):
```markdown
### Added
- Updated docs  # Too vague
- Fixed stuff   # Not descriptive
- Various changes to files  # No details
```

### Step 4: Group Related Changes

Group multiple related changes together:

```markdown
### Added
- Complete documentation for risk module:
  - 9 risk metric functions with formulas
  - 6 portfolio constraint checks with thresholds
  - Risk scoring formula and weighting system
  - Batch portfolio evaluation example
```

### Step 5: Create Release Entry (when releasing)

When releasing a new version:

1. Copy [Unreleased] section
2. Rename to version number and date
3. Clear [Unreleased] section
4. Update comparison links

```markdown
## [1.1.0] - 2026-02-10

### Added
[Content from Unreleased]

### Changed
[Content from Unreleased]

### Fixed
[Content from Unreleased]

---

## [Unreleased]

### Added
- Nothing yet

### Changed
- Nothing yet

### Fixed
- Nothing yet

---

[Unreleased]: https://github.com/org/repo/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/org/repo/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/org/repo/releases/tag/v1.0.0
```

---

## Outputs

- **Primary**:
  - File: `CHANGELOG.md`
  - Content: Structured changelog with all documentation changes

- **Updates**:
  - [Unreleased] section with new entries
  - Version sections (on release)
  - Comparison links (on release)

---

## Examples

### Example 1: Initialize Changelog

**Input**:
```
project_root: /path/to/new-project
action: init
version: 1.0.0
```

**Process**:
1. Create CHANGELOG.md from template
2. Set initial version to 1.0.0
3. Add placeholder entries

**Output**:
```
Created: CHANGELOG.md
Initial version: 1.0.0
Status: Ready for tracking changes
```

### Example 2: Add Documentation Change

**Input**:
```
project_root: /path/to/project
action: add
change_type: added
description: "API reference for backtest module (750 lines) with 4 classes and 8 examples"
```

**Process**:
1. Read CHANGELOG.md
2. Find [Unreleased] → ### Added section
3. Append new entry with bullet point
4. Save file

**Output**:
```
Added to CHANGELOG.md [Unreleased] → Added:
- API reference for backtest module (750 lines) with 4 classes and 8 examples
```

### Example 3: Fix Documentation Error

**Input**:
```
project_root: /path/to/project
action: add
change_type: fixed
description: "Corrected risk module: VaR = Value at Risk (not Variance at Runtime)"
```

**Process**:
1. Read CHANGELOG.md
2. Find [Unreleased] → ### Fixed section
3. Append entry
4. Save file

**Output**:
```
Added to CHANGELOG.md [Unreleased] → Fixed:
- Corrected risk module: VaR = Value at Risk (not Variance at Runtime)
```

### Example 4: Create Release

**Input**:
```
project_root: /path/to/project
action: release
version: 1.1.0
```

**Process**:
1. Read CHANGELOG.md
2. Copy [Unreleased] content
3. Create new section: ## [1.1.0] - 2026-02-10
4. Paste content into new section
5. Clear [Unreleased] section
6. Update comparison links
7. Save file

**Output**:
```
Created: [1.1.0] - 2026-02-10
Moved 15 changes from [Unreleased]
Reset [Unreleased] section
Updated comparison links
```

---

## Validation

- [ ] CHANGELOG.md follows Keep a Changelog format
- [ ] All entries are in [Unreleased] section (or released version)
- [ ] Entries use proper categories (Added, Changed, Fixed, etc.)
- [ ] Entries are descriptive and specific
- [ ] Version numbers follow semantic versioning (MAJOR.MINOR.PATCH)
- [ ] Dates are in ISO 8601 format (YYYY-MM-DD)
- [ ] Comparison links are correct

---

## Related Skills

- **Prerequisites**: `manage_project_status.md` (optional, but recommended)
- **Follow-ups**:
  - `update_readme.md` - Update README with changelog reference
- **Alternatives**: Git commit messages (but less structured)

---

## Tips

1. **Update Immediately**: Add changelog entries right after making changes (not in batches)
2. **Be Specific**: Include line counts, file names, module names
3. **Group Logically**: Related changes go together under same bullet
4. **Link to Issues**: Reference queries.md entries when fixing issues (e.g., "Fixed Q9: Added missing imports")
5. **Use Past Tense**: "Added", "Changed", "Fixed" (not "Add", "Change", "Fix")
6. **Quantify**: Include numbers (e.g., "15 examples", "1,000 lines", "9 metrics")

---

## Semantic Versioning Guidelines

For documentation versions:

- **MAJOR** (X.0.0): Complete documentation restructuring, major changes
- **MINOR** (x.Y.0): New module documentation, new user guides, new design docs
- **PATCH** (x.y.Z): Bug fixes, typo corrections, minor updates

**Examples**:
- `1.0.0` → `1.1.0`: Added API reference for 5 new modules
- `1.1.0` → `1.1.1`: Fixed typos in 3 modules
- `1.1.1` → `2.0.0`: Restructured entire documentation from scratch

---

**Last Updated**: 2026-02-06
**Version**: 1.0
