# Diagram Platform Target Architecture

Date: 2026-04-23

Status: Target-state reference architecture

## 1. Architecture Summary

The target architecture is a layered diagram platform:

1. `diagram_core`
2. `diagram_conventions`
3. domain adapters and source systems

This keeps the editor and graph infrastructure shared while allowing engineering rules to remain domain-specific.

## 2. Target Architecture Diagram

```text
                                +----------------------------------+
                                |        User Interface Shell      |
                                | workspaces / tabs / review / UX  |
                                +----------------+-----------------+
                                                 |
                                                 v
                     +----------------------------------------------------------+
                     |                     diagram_core                         |
                     |----------------------------------------------------------|
                     | graph document model                                     |
                     | canvas/editor runtime                                    |
                     | node/edge/group/layer primitives                         |
                     | select / drag / zoom / snap / align / connect            |
                     | layout persistence contract                              |
                     | versioning / audit hooks                                 |
                     | export pipeline: JSON / PNG / PDF / print                |
                     | renderer abstraction                                     |
                     +----------------------+-----------------------------------+
                                            |
                                            v
                     +----------------------------------------------------------+
                     |                 diagram_conventions                      |
                     |----------------------------------------------------------|
                     | EPC visual language                                      |
                     | title blocks / legends / sheet framing                   |
                     | standard symbol registration contract                    |
                     | line styles / typography / print rules                   |
                     | drafting presets and document templates                  |
                     +-----------+------------------+---------------------------+
                                 |                  | 
                +----------------+                  +-----------------+
                |                                                     |
                v                                                     v
   +-----------------------------+                     +-----------------------------+
   |       eht_diagrams          |                     |   power_system_diagrams     |
   |-----------------------------|                     |-----------------------------|
   | EHT SLD graph translator    |                     | network graph translator    |
   | EHT symbol pack             |                     | study symbol pack           |
   | EHT validation rules        |                     | load flow / SC overlays     |
   | EHT auto-layout             |                     | study validations           |
   | EHT inspector panels        |                     | study inspectors            |
   +--------------+--------------+                     +--------------+--------------+
                  |                                                     |
                  v                                                     v
   +-----------------------------+                     +-----------------------------+
   |      EHT source models      |                     |  pandapower + power models  |
   |-----------------------------|                     |-----------------------------|
   | ProjectData                 |                     | network data                |
   | HeatTracingInput            |                     | study results               |
   | PowerDistributionBranch     |                     | fault/load-flow outputs     |
   | SLDNodeLayout               |                     | scenario metadata           |
   +-----------------------------+                     +-----------------------------+

                                 +----------------------------------+
                                 |        cable_diagrams            |
                                 |----------------------------------|
                                 | cable block graph translator     |
                                 | cable symbol pack                |
                                 | cable sizing / routing metadata  |
                                 | cable logic validations          |
                                 +----------------+-----------------+
                                                  |
                                                  v
                                 +----------------------------------+
                                 |     cable source models/tool     |
                                 +----------------------------------+
```

## 3. Layer Responsibilities

### 3.1 `diagram_core`

Owns:
- diagram document schema
- graph primitives
- editor interaction model
- layout save/load contract
- rendering lifecycle
- generic commands and toolbar actions
- export/print pipeline

Must not own:
- EHT business rules
- power-study calculations
- cable-design semantics
- domain-specific validation logic

### 3.2 `diagram_conventions`

Owns:
- professional look and feel
- standard symbols contract
- common sheet framing and presentation patterns
- print/export defaults
- reusable visual tokens

Must not own:
- source-data calculations
- module-specific topology rules

### 3.3 Domain Adapters

Own:
- transformation from source data to graph document
- domain property schema
- domain-specific validations
- domain-specific layout strategy
- module-specific commands and overlays

## 4. Data Flow

### 4.1 Generated Diagram Flow

```text
Domain source data
  -> domain translator
  -> normalized graph document
  -> diagram_core renderer/editor
  -> persisted layout/version state
  -> exports / presentation
```

### 4.2 User Edit Flow

```text
User interaction in diagram_core
  -> command/event model
  -> graph/layout delta
  -> domain validation
  -> persisted document state
  -> optional write-back to source systems where allowed
```

### 4.3 Study/Analysis Overlay Flow

```text
Domain calculation engine
  -> overlay/result payload
  -> domain adapter
  -> styled highlights/annotations in diagram_core
```

## 5. Canonical Contracts

The following contracts should be stable and reused across domains:

### 5.1 Graph Document
- `document_id`
- `document_type`
- `version`
- `nodes`
- `edges`
- `groups`
- `layers`
- `layout`
- `annotations`
- `meta`

### 5.2 Node Contract
- stable internal id
- display label
- type
- symbol key
- geometry/layout
- domain metadata
- references back to source data

### 5.3 Edge Contract
- stable internal id
- source id
- target id
- edge type
- routing/style
- domain metadata

### 5.4 Persistence Contract
- generated baseline
- user layout overrides
- optional user topology overrides
- version metadata
- audit fields

## 6. EHT-Specific Mapping To Target Architecture

Current EHT already provides seeds for the target architecture:
- generated graph payload: [eht/sld_payload.py](/home/kr/mydev/eht_office/eht/sld_payload.py:162)
- persisted layout: [eht/sld_layout.py](/home/kr/mydev/eht_office/eht/sld_layout.py:35)
- validation: [eht/sld_validation.py](/home/kr/mydev/eht_office/eht/sld_validation.py:117)
- rendering/editor shell: [static/js/sld_workspace.js](/home/kr/mydev/eht_office/static/js/sld_workspace.js:1)

This makes EHT the correct first extraction candidate for the shared platform.

## 7. Target Non-Functional Expectations

The platform should be designed for:
- deterministic rendering
- stable internal IDs
- recoverable save/load behavior
- partial updates without whole-document corruption
- large-project browsing
- multi-export capability
- testable graph generation and validation
- future collaboration/audit support

## 8. Architecture Decisions For The First Build Window

For the next implementation window:
- keep EHT source-of-truth in `eht`
- do not build a separate repo or microservice yet
- extract reusable frontend/backend diagram services only when boundaries are clear
- treat current EHT SLD as the pilot implementation of the larger platform

## 9. Success Criteria

We should consider the architecture direction validated when:
- EHT SLD uses a stable graph contract
- layout persistence is robust and incremental-safe
- the old prototype route is retired
- at least one additional module can reuse the editor/render/persistence shell with a different domain adapter
