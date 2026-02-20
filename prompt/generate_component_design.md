# Prompt: Generate Component Design

Use this when creating or refining a **component design** (`2_component_designs/[component_name].md`).

---

## Context to Provide

- **Module name** (e.g. FMS, VCU, Control)
- **Component name** and **one-line purpose**
- **Inputs**: source, type, frequency
- **Outputs**: destination, type, frequency
- **Main algorithm or processing** (name and 3–7 high-level steps)
- **Algorithm file** (if any): `algorithms/[algorithm_name].md`
- **Config parameters** (name, default, range, effect) — if any
- **Error cases** (condition, handling, recovery) — at least 2–3
- **Related components and design docs**

---

## Instructions for the Writer (or LLM)

Generate a component design that includes:

1. **Header**  
   Document ID `[MODULE]-CD-[COMPONENT]-001`, Version, Date, Classification, Prepared by, Approved by. Add Safety Classification only if safety-relevant.

2. **1. Overview**  
   - 1.1 Purpose: 1–2 sentences.  
   - 1.2 Scope: 3–5 bullet points (purpose, I/O, algorithm, config, error handling).

3. **2. Inputs and Outputs**  
   Tables with: Input/Output Name, Data Type, Source/Destination, Frequency, Description.

4. **3. Detailed Algorithm**  
   - 3.1 **Mermaid flowchart**: Start → Validate → Core processing → Output; include invalid/error path.  
   - 3.2 **Algorithm steps**: 3–7 numbered steps. First or last line:  
     `(see [Algorithm Name](algorithms/[file].md) for full detail)`  
     Add **Performance** (e.g. &lt;10ms) and optionally **Safety** if needed.

5. **4. Configuration Parameters**  
   Table: Parameter, Default, Range, Effect. Omit if the component has no tunable parameters.

6. **5. Error Handling**  
   Table: Error Case, Condition, Handling, Recovery.

7. **6. Related Documents**  
   - 6.1 Algorithm: link to `algorithms/[algorithm].md`.  
   - 6.2 Related component(s).  
   - 6.3 `system_architecture.md`, `software_design.md`.

8. **Footer**  
   Document Status, Last Updated, Next Review Date, Version, Classification.

---

## Rules

- Do **not** duplicate the full algorithm; reference it.  
- Do **not** add extra sections (e.g. Relevant Files, Side Effects) unless the template is explicitly extended.  
- Use **tables** for I/O, config, and error handling.  
- Use **relative links** for all internal references.
