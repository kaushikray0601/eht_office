# plant3d Agreed Architecture

Date: 2026-06-22

Status: architecture agreed; ready for execution planning

## Scope

`plant3d` is the neutral 3D engineering platform for the larger EPC electrical engineering ecosystem.

It is not an EHT-specific tool. EHT design, cable engineering, cable drum optimization, cable pulling/construction management, dashboards, database workflows, approvals, and reporting will use this platform, but must not own the platform core.

`idfviewer` remains a proof-of-concept/lab app. It proved useful lessons about IDF, PCF, IFC, Three.js rendering, measurement, snapping, and EHT overlay authoring. Those lessons may be harvested, but `idfviewer` should not become the final platform foundation.

## Final Architecture Decision

The platform will be built as:

> A web-first EPC electrical 3D engineering platform implemented first as a new neutral Django app/bounded context in the current repo, deployed as a modular monolith with independently scalable conversion workers, REST APIs for normal workflows, async queue jobs for heavy model processing, self-hosted object storage for source/render blobs, Postgres for metadata/indexes, browser-side rendering through optimized tiled packages with RTC/tile-local origins, Three.js-first viewer implementation, and EHT/cable/construction modules as consumers rather than owners of the 3D core.

## Product Boundary

Core platform owns:

- Source model records and provenance.
- Conversion jobs.
- Runtime render packages.
- Render tiles/chunks.
- Stable model object index.
- Workspaces and layers.
- Layer transforms and visibility.
- View states and annotations.
- Renderer-facing package manifests.

Core platform must not own:

- EHT calculation logic.
- Cold cable engineering logic.
- SLD/topology/reporting logic.
- Cable drum optimization business rules.
- Cable pulling/construction workflow business rules.
- Vendor catalogue logic.

Engineering modules may reference platform objects and workspaces, but the platform core must not import or depend on module internals.

## Deployment Architecture

Start as one repo and one modular Django codebase, deployed as multiple container roles:

- Django web/API container.
- 3D conversion/tiling worker container(s).
- Queue/broker.
- Postgres.
- Self-hosted object storage.
- Static/viewer asset serving through Django or a static container initially.

The worker containers can be allocated additional CPU/RAM independently. This gives the 3D pipeline resource flexibility without creating a separate service/repository too early.

## Communication Pattern

Use REST for synchronous workflows:

- project/model/workspace/layer CRUD
- metadata lookup
- object selection details
- authoring save/load
- permissions and audit

Use async jobs for heavy workflows:

- source file ingestion
- IFC/IDF/PCF parsing
- conversion
- tiling
- compression
- metadata/object indexing
- future heavy route solving or optimization

Use SSE for conversion/job progress first. WebSocket is deferred until true bidirectional scene collaboration exists.

Do not introduce Kafka, event sourcing, or enterprise event-bus architecture at this stage.

## Storage Decision

Use self-hosted object storage first.

The application should use an S3-compatible or storage-abstraction pattern so that a later move to Oracle Object Storage, Amazon S3, or another managed bucket provider changes infrastructure/configuration more than application architecture.

Rules:

- Original source files live in object storage.
- Runtime render packages live in object storage.
- Postgres stores metadata, indexes, job state, workspaces, object IDs, annotations, and engineering references.
- Large geometry blobs should not live in Postgres.
- Large render files should not be proxied through Django once signed URL/direct-storage delivery is available.

## Rendering Decision

Start browser-side rendering with Three.js first because the current prototype already uses it.

Keep Babylon.js as a fallback/comparison candidate if:

- Three.js exposes renderer-level limitations.
- Babylon comparison can be performed cheaply during the spike.

Do not build a broad multi-renderer frontend abstraction now. Use a thin internal scene boundary only:

- load package/tile
- set transform
- set visibility
- set opacity/tint
- pick object
- highlight object
- focus bounds

WebGPU is a future-capable path, not a v1 dependency. WebGL2-compatible architecture remains important.

## Runtime Geometry Strategy

The browser must render optimized runtime packages, not raw CAD/BIM intelligence.

The platform should use:

- preprocessing/conversion
- spatial tiling
- batching/merged geometry
- instancing for repeated objects
- metadata fetched on demand
- non-intelligent background geometry where suitable
- selective intelligent objects for engineering workflows
- level-of-detail/proxy geometry later
- binary payloads rather than large JSON geometry for serious files

The browser should render the user's current engineering question, not the whole plant.

## Precision Requirement

RTC/tile-local origins are a foundational requirement.

The platform must track:

- source units
- display units
- source coordinate frame
- base point/origin
- axis orientation
- raw bounds
- tile-local origin
- local render coordinates
- transformed engineering coordinates

This is required because plant models may use large coordinates, and browser GPU vertex pipelines use float32 values. Without tile-local origins, large models can show jitter, z-fighting, broken snapping, and unreliable measurement.

## Source Format Decision

IFC remains the first practical structural/reference format for the spike.

Navisworks `.nwd` would be attractive as a review format, but building reliable `.nwd` support now is too difficult and would distract from the main platform goal.

IDF and PCF remain important source formats for pipeline/isometric geometry. Existing `idfviewer` parsers can be harvested later.

## Initial Technical Direction

The first execution milestone is a pipeline spike, not a polished workspace UI.

The spike should prove:

1. Source file ingestion.
2. Conversion to an optimized runtime package.
3. Tile/package metadata.
4. Browser rendering with acceptable performance.
5. Coordinate precision strategy.
6. Basic object identity/metadata lookup.

Only after the pipeline is proven should we freeze the broader production data model or build full workspace/layer UI.

## Future Exploration Points

These are intentionally deferred but recorded:

- Evaluate C++/Rust/native geometry processing if Python-first conversion becomes too slow or memory-heavy.
- Evaluate Node/web-ifc if browser-native or WASM IFC tooling becomes more suitable than Python/IfcOpenShell.
- Evaluate Babylon.js if Three.js exposes limitations.
- Revisit xeokit only as a future exploration/reference architecture, or if commercial licensing becomes justified.
- Evaluate 3D Tiles concepts or a 3D-Tiles-compatible package if spatial streaming needs become first-class.
- Evaluate Oracle Object Storage, Amazon S3, or another managed bucket provider after self-hosted storage proves the workflow.
- Evaluate WebGPU for GPU picking, culling, compute, or high-volume rendering after WebGL2-compatible foundations exist.
- Evaluate larger real EPC IFC exports beyond the first available 20 MB project IFC and public samples.
- Revisit service extraction only if polyglot runtime, release cadence, licensing isolation, or scaling pressure makes it necessary.

## Decisions From Final Discussion

- Django/Python-first for v1.
- Self-hosted storage first.
- Exclude xeokit AGPL runtime for now.
- Use available real/sample IFC files for first spike.
- Accept IFC coordinate/base-point uncertainty as a measured input.
- Create the new platform boundary now rather than adding more architecture weight to `idfviewer`.
- Use independent worker containers for heavy 3D work from the real buildout.
- Keep EHT and other engineering modules as consumers of the 3D platform.

## Open For Implementation Detail

The following are not architecture blockers:

- Exact provisional app name if `plant3d` is later renamed.
- Whether first local spike uses filesystem-backed storage before MinIO.
- Whether Babylon.js is included in the first spike or deferred.
- Exact queue implementation: Celery, RQ, or another simple worker system.
- Exact package format for first experiment: GLB/glTF, custom binary chunks, or tiled package manifest.

