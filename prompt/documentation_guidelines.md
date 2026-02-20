# Documentation Guidelines for midterm_stock_planner Module Design

**Purpose**: Folder structure, document types, and formatting for design documentation. Use when creating or reviewing design docs.

---

## 1. Design Folder Structure

Each module has a `design/` folder with this layout:

```
[Module]/design/
├── README.md                 # Design index
├── 0_system_overview.md
├── system_architecture.md
├── system_context.md
├── software_design.md
├── interface_design.md
├── data_flow.md
├── 3_data_structures.md
├── algorithm_designs.md      # Links to 2_component_designs/algorithms/
└── 2_component_designs/
    ├── README.md             # Component index
    ├── _template_component_design.md
    ├── [component].md
    └── algorithms/
        ├── README.md         # Algorithm index
        ├── _template_algorithm_design.md
        └── [algorithm].md
```

---

## 2. Document Types

| Type | Location | Content |
|------|----------|---------|
| **Component design** | `2_component_designs/[name].md` | Overview, I/O, processing flow (Mermaid + steps), config, error handling, related. References algorithms. |
| **Algorithm design** | `2_component_designs/algorithms/[name].md` | Overview, I/O table, algorithm steps, config, error handling, related. |

---

## 3. Naming and IDs

- **Component ID**: `MSP-CD-[COMPONENT]-001` (e.g. `MSP-CD-BACKTEST-001`)
- **Algorithm ID**: `MSP-CD-ALG-[ALG]-001` (e.g. `MSP-CD-ALG-WALKFORWARD-001`)
- **Filenames**: `snake_case` (e.g. `walk_forward_backtest.md`, `risk_parity_allocation.md`)

---

## 4. Formatting Rules

- **Markdown**: Use tables for inputs, outputs, config, error cases.
- **Mermaid**: Use for flowcharts and state machines. Prefer `camelCase` or `snake_case` for node IDs; avoid spaces.
- **Links**: Use relative paths: `[System Architecture](../../system_architecture.md)`, `[Algorithm](algorithms/algorithm_name.md)`.
- **Footer**: Include Document Status, Last Updated, Next Review Date, Version, Classification.

---

## 5. Requirements and Other Docs (if `docs/` exists)

| Document | Typical content |
|----------|-----------------|
| `requirements.md` | IEEE 830-style SRS: purpose, scope, specific requirements, interfaces, appendices |
| `interface_specification.md` | APIs, data contracts, configuration schemas |
| `test_specification.md` | Strategy, unit/integration/system tests, environment |

---

## 6. Standards

- **Traceability**: In Related, link to algorithms, components, `system_architecture.md`, `software_design.md`.
- **Code Examples**: Include Python code examples where relevant for API documentation.
