# Decision 0001 - plant3d Platform Architecture

Date: 2026-06-22

## Status

Accepted for execution planning.

## Decision

Create `plant3d` as the new neutral 3D engineering platform boundary.

Use a web-first architecture:

- modular Django app/bounded context in the current repo
- independent conversion/tiling worker containers
- REST APIs for normal workflows
- async queue jobs for heavy model processing
- SSE for job progress
- self-hosted object storage for source and render blobs
- Postgres for metadata and indexes
- browser-side rendering of optimized tiled packages
- RTC/tile-local origins for coordinate precision
- Three.js-first viewer spike

Do not promote `idfviewer` into the final platform. Treat it as a proof-of-concept and harvest useful parser/viewer lessons later.

Do not make EHT, cable, construction, or other engineering modules owners of the 3D core. They will consume the platform through stable model/object/workspace references.

## Rationale

The product goal is a larger EPC electrical engineering ecosystem, not an EHT-only viewer. A desktop-first platform would complicate deployment, collaboration, approvals, dashboards, construction status, and future cloud workflows.

A strict microservice architecture is premature. Independent worker containers provide the resource scaling needed for heavy 3D conversion while keeping the codebase manageable until real workload pressure proves a service split is needed.

## Consequences

- First execution work should be a pipeline spike, not a polished workspace UI.
- Source files and render packages should be treated as blobs, not database rows.
- Large geometry must be converted, tiled, and optimized before browser rendering.
- Future C++/Rust/native/Node conversion services remain possible behind queue and object-storage boundaries.
- AGPL runtime dependencies such as xeokit are excluded for now, but may be revisited through commercial licensing or future review.

