# Prompts for Design Documentation

**Warning**: All work on this project is managed through [beads](https://github.com/steveyegge/beads). Run `bd ready` to find available documentation tasks.

Use these with the **templates** folder to create and maintain design documents (component designs, algorithm designs) for midterm_stock_planner.

## For Document Generation

| File | Use |
|------|-----|
| **[documentation_guidelines.md](documentation_guidelines.md)** | Folder structure, document types, naming, and formatting. Read first. |
| **[generate_component_design.md](generate_component_design.md)** | Prompt/checklist to write or generate a **component design** (`2_component_designs/[name].md`). |
| **[generate_algorithm_design.md](generate_algorithm_design.md)** | Prompt/checklist to write or generate an **algorithm design** (`2_component_designs/algorithms/[name].md`). |

## Suggested workflow

**For AI Agents (using beads)**:
1. **`bd ready`** - Find available documentation tasks
2. **`bd update <task-id> --claim --status in_progress`** - Claim task
3. Read **documentation_guidelines.md**
4. Read **[../knowledgebase/AGENT_PROMPT.md](../knowledgebase/AGENT_PROMPT.md)** for project context
5. Use **generate_component_design.md** or **generate_algorithm_design.md** with your context
6. Create design document in `docs/design/2_component_designs/` or `.../algorithms/`
7. **`bd update <task-id> --status done`** - Mark complete

**For Manual Work**:
1. Read **documentation_guidelines.md**
2. Use **generate_component_design.md** or **generate_algorithm_design.md** with your context (I/O, steps, config, errors, related docs)
3. Copy from `templates/design_folder_template/2_component_designs/` or `.../algorithms/` and fill using the generated structure

## Other

- **_archive/** — Older prompts (COMBINED_GUIDELINES, DD, job descriptions, dev workflow). Not needed for design documentation.
