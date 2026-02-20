# Prompt: Generate Algorithm Design

Use this when creating or refining an **algorithm design** (`2_component_designs/algorithms/[algorithm_name].md`).

---

## Context to Provide

- **Module name** (e.g. FMS, VCU, Mission Control)
- **Algorithm name** and **one-line purpose**
- **Inputs**: source, description
- **Outputs**: destination, description
- **Algorithm steps**: 3–10 numbered steps (conditions, formulas, and actions)
- **Config parameters** (name, default, range, effect)
- **Error handling**: 2–5 cases (condition → action; recovery if any)
- **Component(s)** that use this algorithm
- **Safety relevance** (yes/no; if yes, ASIL and brief rationale)

---

## Instructions for the Writer (or LLM)

Generate an algorithm design that includes:

1. **Header**  
   Document ID `[MODULE]-CD-ALG-[ALG]-001`, Version, Date, Classification. Add **Safety Classification** only if the algorithm is safety-relevant.

2. **1. Overview**  
   - 1.1 Purpose: 1–2 sentences.  
   - 1.2 Scope: 2–4 bullets (e.g. signals, data types, or subsystems covered).

3. **2. Inputs and Outputs**  
   One table: Input | Source | Output | Destination.

4. **3. Algorithm**  
   3–10 numbered steps. Each: **Bold step name**, then description with conditions and actions. Include formulas if needed (inline or block).

5. **4. Configuration Parameters**  
   Table: Parameter, Default, Range, Effect. Omit if there are none.

6. **5. Error Handling**  
   Bullet list or short paragraphs: **[Case]**: [Condition] → [Action]; [recovery].  
   Include NaN/Inf or invalid-input handling unless not applicable.

7. **6. Related**  
   Links to: `algorithm_designs.md`, the component(s) that use it, `software_design.md` (optional).

8. **Footer**  
   Document Status, Last Updated, Next Review Date, Version, Classification.

---

## Rules

- Keep the doc **focused on the algorithm**; component-level wiring and Mermaid stay in the component design.  
- Use **tables** for I/O and config.  
- Use **relative links**: `../../algorithm_designs.md`, `../[component].md`.  
- If safety-relevant, state **ASIL and rationale** in the header.
