# Skill: Manage Requirements

**Purpose**: Generate, trace, and gap-analyse software requirements for Hyperception and its submodules.

**Category**: documentation / validation

---

## Prerequisites

- Familiarity with the Hyperception architecture (see `CLAUDE.md`, `ARCHITECTURE.md`)
- Access to submodule source code (cloned in `~/Documents/code/`)
- Requirements design document: `docs/requirements/REQUIREMENTS_DESIGN.md`

---

## Modes

This skill operates in three modes, selected by the first argument:

| Mode | Invocation | Purpose |
|------|------------|---------|
| **generate** | `/requirements generate <subsystem>` | Extract requirements from source code |
| **trace** | `/requirements trace <REQ-ID>` | Find code locations implementing a requirement |
| **gap** | `/requirements gap <subsystem>` | Find undocumented behavior and missing requirements |

---

## Inputs

### Mode: generate

- **Required**:
  - `subsystem`: Subsystem name or code (e.g., `tracking`, `TRK`, `sensor_synchroniser`, `SSY`)

- **Optional**:
  - `scope`: Requirement types to generate (default: all — FR, IR, PR, CR, SR, NR)
  - `output_path`: Override output file path (default: per REQUIREMENTS_DESIGN.md layout)

### Mode: trace

- **Required**:
  - `req_id`: Requirement ID to trace (e.g., `REQ-TRK-FR-001`)

- **Optional**:
  - `depth`: Trace depth — `shallow` (direct reference only) or `deep` (follow call chain) (default: `shallow`)

### Mode: gap

- **Required**:
  - `subsystem`: Subsystem name or code

- **Optional**:
  - `focus`: Focus area — `config` (uncovered parameters), `behavior` (undocumented logic), `thresholds` (hardcoded values), `all` (default: `all`)

---

## Subsystem Name Resolution

The skill accepts either full names or 3-letter codes:

| Full Name | Code | Requirements File |
|-----------|------|-------------------|
| `system` | `SYS` | `docs/requirements/00_system_requirements.md` |
| `sensor_frontend` | `SFE` | `docs/requirements/01_sensor_frontend.md` |
| `ground_filtering` | `GND` | `docs/requirements/02_ground_filtering.md` |
| `clustering` | `CLU` | `docs/requirements/03_clustering.md` |
| `camera_lidar` | `CAM` | `docs/requirements/04_camera_lidar_association.md` |
| `tracking` | `TRK` | `docs/requirements/05_tracking.md` |
| `bev_fusion` | `BEV` | `docs/requirements/06_bev_fusion.md` |
| `dds_output` | `DDS` | `docs/requirements/07_dds_output.md` |
| `visualization` | `VIS` | `docs/requirements/08_visualization.md` |
| `perception_lidar_filter` | `PLF` | `docs/requirements/submodules/perception_lidar_filter.md` |
| `sensor_synchroniser` | `SSY` | `docs/requirements/submodules/sensor_synchroniser.md` |
| `new_imm_ukf` | `IMM` | `docs/requirements/submodules/new_imm_ukf.md` |
| `perception_deskew` | `DSK` | `docs/requirements/submodules/perception_deskew.md` |
| `nvdecoder` | `NVD` | `docs/requirements/submodules/nvdecoder.md` |
| `vis_detector` | `DET` | `docs/requirements/submodules/vis_detector.md` |

---

## Process

### Mode: generate

#### Step 1: Identify Source Files

Determine the primary source files for the target subsystem using the mapping in `REQUIREMENTS_DESIGN.md` section 4.2.

For submodules, use the cloned repos at `~/Documents/code/<submodule>/`.

#### Step 2: Read and Analyse Source Code

For each source file:

1. **Functional behaviour** — Identify what each function/method does, its inputs and outputs
2. **Configuration parameters** — Extract all YAML/INI reads with parameter names, types, defaults
3. **Interfaces** — Document ROS topic subscriptions/publications, DDS types, shared memory, function signatures
4. **Thresholds** — Capture hardcoded numeric constants and configurable limits
5. **Guards and safety** — Identify bounds checks, null guards, timeout handling, fallback paths
6. **Performance constraints** — Identify timing requirements, threading, GPU usage, memory allocation

#### Step 3: Draft Requirements

For each identified behaviour, write a formal requirement using the template:

```markdown
### REQ-<CODE>-<TYPE>-<NNN>: <Title>
- **Priority**: Must | Should | May
- **Description**: The <subsystem> shall <formal statement>.
- **Rationale**: <Why this exists — from comments, naming, or design context>
- **Source**: `<file>:<line>` — <brief context>
- **Config**: `<yaml.path>` (type: `<type>`, default: `<value>`, range: `[min, max]`) — if applicable
- **Verification**: <unit test | integration test | field test | inspection>
- **Status**: Implemented | Partial | Not Implemented
```

Rules for writing requirements:
- One behaviour per requirement (atomic)
- Use "shall" for mandatory, "should" for recommended, "may" for optional
- Reference specific config parameters with their YAML path
- Include the source file and line number
- Assign sequential numbers within each type (FR-001, FR-002, ...)

#### Step 4: Organise by Type

Group requirements into sections per the document template:
1. Functional Requirements (FR)
2. Interface Requirements (IR)
3. Performance Requirements (PR)
4. Configuration Requirements (CR)
5. Safety Requirements (SR)
6. Non-Functional Requirements (NR)

#### Step 5: Write Dependencies Section

Document:
- Upstream dependencies (what this subsystem needs from others)
- Downstream dependencies (what depends on this subsystem)

#### Step 6: Write Output File

Write the complete requirements document to the appropriate path per the folder layout in `REQUIREMENTS_DESIGN.md`.

#### Step 7: Update Traceability Matrix

Append new requirements to `docs/requirements/traceability_matrix.md`.

---

### Mode: trace

#### Step 1: Parse Requirement ID

Extract subsystem code, type, and number from the REQ-ID.

#### Step 2: Read Requirement

Load the requirement from the appropriate requirements document. Extract the `Source` field.

#### Step 3: Navigate to Code

Read the source file at the referenced line number. For `depth=deep`:
- Follow function calls from the referenced location
- Use LSP (goToDefinition, findReferences) where available
- Build a call chain showing all code paths that implement the requirement

#### Step 4: Report

Output:
- Requirement text
- Primary source location (file:line)
- Call chain (if depth=deep)
- Related configuration parameters
- Related test cases (if found in `test/`)

---

### Mode: gap

#### Step 1: Load Existing Requirements

Read the requirements document for the target subsystem. Build a set of all documented behaviours.

#### Step 2: Analyse Source Code

Read all source files for the subsystem. For each focus area:

**config** — Find all YAML/INI parameter reads. Flag any parameter not covered by a CR requirement.

**behavior** — Identify all public functions, conditional branches, and state transitions. Flag any behaviour not covered by an FR requirement.

**thresholds** — Find all hardcoded numeric constants (magic numbers). Flag any constant not documented in a requirement or configuration.

**all** — Run all three analyses.

#### Step 3: Report Gaps

Output a gap report:

```markdown
## Gap Analysis: <Subsystem>
**Date**: YYYY-MM-DD
**Scope**: <focus area>

### Undocumented Configuration Parameters
| Parameter | File:Line | Type | Default |
|-----------|-----------|------|---------|
| `param_name` | `file.cpp:123` | float | 0.5 |

### Undocumented Behaviour
| Function | File:Line | Description |
|----------|-----------|-------------|
| `functionName()` | `file.cpp:456` | Brief description of what it does |

### Hardcoded Thresholds
| Value | File:Line | Context |
|-------|-----------|---------|
| `0.3` | `file.cpp:789` | Used as distance threshold in ... |

### Recommended New Requirements
- REQ-<CODE>-CR-NNN: <suggested requirement for undocumented config>
- REQ-<CODE>-FR-NNN: <suggested requirement for undocumented behaviour>
```

---

## Outputs

### Mode: generate
- **Primary**: `docs/requirements/<NN>_<subsystem>.md` or `docs/requirements/submodules/<submodule>.md`
- **Secondary**: Updated `docs/requirements/traceability_matrix.md`

### Mode: trace
- **Primary**: Console output with code locations and call chain

### Mode: gap
- **Primary**: Console output with gap report
- **Secondary**: Suggested new requirements (can be appended to requirements doc)

---

## Examples

### Example 1: Generate Tracking Requirements

```
/requirements generate tracking
```

**Process**:
1. Read `src/hyperception.cpp` (trackingChunk, ~lines 7750-8050)
2. Read `config/hyperception.yaml` (tracking section)
3. Read `externs/new_imm_ukf/` source
4. Extract: association logic, age management, prediction, dynamic classification
5. Write `docs/requirements/05_tracking.md` with ~30-50 requirements

### Example 2: Trace a Specific Requirement

```
/requirements trace REQ-TRK-FR-001
```

**Output**:
```
REQ-TRK-FR-001: Track identity persistence
  The tracker shall maintain track identity for up to max_age missed detections.

Primary: hyperception.cpp:7850 — age check in trackingChunk
  if (track.n_seen == 0 && age > max_age_) { removeTrack(track); }

Config: tracking.max_age (int, default: 5)
Test: test/test_tracking.cpp:45
```

### Example 3: Gap Analysis for Ground Filtering

```
/requirements gap ground_filtering
```

**Output**:
```
## Gap Analysis: Ground Filtering (GND)

### Undocumented Configuration Parameters
| Parameter | File:Line | Type | Default |
|-----------|-----------|------|---------|
| ground_filter.z_tolerance | ground_filter.cpp:89 | float | 0.15 |

### Hardcoded Thresholds
| Value | File:Line | Context |
|-------|-----------|---------|
| 0.02 | ego_ground_filter.cpp:134 | Minimum height delta |

### Recommended New Requirements
- REQ-GND-CR-010: z_tolerance configuration parameter
- REQ-GND-FR-008: Minimum height delta guard
```

---

## Validation

### For generate mode:
- [ ] All public functions have corresponding FR requirements
- [ ] All YAML/INI parameters have corresponding CR requirements
- [ ] All ROS/DDS interfaces have corresponding IR requirements
- [ ] All timing constraints have corresponding PR requirements
- [ ] All guards/limits have corresponding SR requirements
- [ ] Every requirement has a Source field with file:line
- [ ] Every requirement uses RFC 2119 keywords (shall/should/may)
- [ ] Requirement IDs are sequential within each type
- [ ] Document follows the template in REQUIREMENTS_DESIGN.md

### For trace mode:
- [ ] Source file and line number are valid and accessible
- [ ] Code at referenced location matches the requirement description
- [ ] Call chain (if deep) is complete and accurate

### For gap mode:
- [ ] All YAML parameter reads are accounted for
- [ ] All hardcoded constants are flagged
- [ ] Suggested requirements follow the ID convention

---

## Related Skills

### Prerequisites
- `code_exploration/analyze_module.md` — Understand module structure first
- `av_domains/analyze_perception_module.md` — AV-specific analysis

### Follow-ups
- `validation/check_doc_coverage.md` — Verify documentation completeness
- `beads_integration/create_documentation_task.md` — Track requirements work

### Related
- `documentation/generate_component_design.md` — Component design documents
- `documentation/generate_algorithm_design.md` — Algorithm design documents

---

## Source File Locations

### Hyperception Core
All paths relative to hyperception repository root.

| Subsystem | Primary Files |
|-----------|---------------|
| System | `src/hyperception.cpp`, `include/hyperception/hyperception.hpp`, `config/hyperception.yaml` |
| Sensor Front-End | `src/hyperception.cpp` (processSensors, process) |
| Ground Filtering | `src/ground_filter.cpp`, `src/ego_ground_filter.cpp` |
| Clustering | `lib/CVC_cluster.cpp`, `lib/dbscan_cluster.hpp`, `lib/dbscan_grid_cluster.hpp` |
| Camera-LiDAR | `src/hyperception_camelid.cpp` |
| Tracking | `src/hyperception.cpp` (trackingChunk, computeTrackStats) |
| BEV Fusion | `src/hyperception_bevfusion.cpp` |
| DDS Output | `src/dds_handler.cpp` |
| Visualization | `src/hyperception_vis.cpp` |

### Submodules
All paths relative to `~/Documents/code/<submodule>/`.

| Submodule | Primary Files |
|-----------|---------------|
| perception_lidar_filter | `src/lidar-voxelization.cu`, `src/prefilter_gpu.cu`, `src/ground_filter_gpu.cu`, `src/curber_gpu.cu`, `src/fusefilter_gpu.cu` |
| sensor_synchroniser | `src/sensor_synchroniser.cpp`, `lib/threadpool.cpp` |
| new_imm_ukf | `src/IMM_UKF.cpp`, `src/UKF.cpp` |
| perception_deskew | `src/imu_odom_deskew.cpp` |
| nvdecoder | `src/nvdecoder.cu` |
| vis_detector | `src/detector.cpp`, `src/yolo_detector.cpp` |

---

**Last Updated**: 2026-02-16
**Version**: 1.0
