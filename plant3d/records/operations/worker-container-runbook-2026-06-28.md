# plant3d Worker Container Runbook

Date: 2026-06-28

Status: spike/dev runbook; production queue/SSE still deferred

## Purpose

`plant3d` conversion must not depend on a person repeatedly running `process_plant3d_job --all`.

The agreed architecture is a modular Django app with independently scalable worker containers. For the current spike, the worker implementation is still a Django management command, but it now has a long-running mode suitable for a dedicated local terminal, process supervisor, or Docker worker role.

## Current Worker Command

Use this command for local/dev and the first worker container role:

```bash
venv/bin/python manage.py process_plant3d_job --watch
```

Useful bounded variants:

```bash
venv/bin/python manage.py process_plant3d_job --next
venv/bin/python manage.py process_plant3d_job --all
venv/bin/python manage.py process_plant3d_job --watch --max-jobs 1
venv/bin/python manage.py process_plant3d_job --watch --idle-exit-seconds 60
```

## Intended Docker Role

The first Docker deployment should run at least two container roles from the same image/codebase:

- `web`: Django HTTP/API/static role.
- `plant3d-worker`: conversion/tiling/compression role.

The worker container command should be:

```bash
venv/bin/python manage.py process_plant3d_job --watch
```

This lets the worker role receive more CPU/RAM than the web role without splitting the repository or creating a premature microservice.

## Job Claiming

`--next`, `--all`, and `--watch` now claim queued jobs before execution. This matters because a future deployment may run more than one worker container.

Current behavior:

- Jobs start as `queued`.
- Worker claims a job and marks it `running`.
- Conversion records staged progress in `ConversionJob.metrics.stage` and `ConversionJob.log`.
- Completion creates package/tile/object rows and marks progress `100`.
- Failed conversion records `failed` and `error_message`.

## Progress Expectations

Progress is staged, not continuous.

IfcOpenShell does not currently expose internal tessellation percentage to this pipeline, so a job may stay on:

```text
Parsing IFC geometry from source
```

for most of the elapsed time. That is still better than the old unexplained `5%` stall because the UI now shows the active stage.

Production-grade progress should later use SSE or WebSocket push, but polling is acceptable for the spike.

## Meshopt / gltfpack

The GLB pipeline has an optional meshopt hook. To activate it in the worker image, install `gltfpack` and either:

- put `gltfpack` on `PATH`, or
- set `PLANT3D_GLTFPACK_BIN=/path/to/gltfpack`.

Optional args:

```bash
PLANT3D_GLTFPACK_ARGS="-cc"
```

If `gltfpack` is unavailable, conversion still succeeds and records meshopt status `skipped`.

Do not adopt `gltfpack -cc` on byte savings alone. Because the GLB picking contract currently depends on `_FEATURE_ID_0`, any compressed package must also prove that feature IDs still resolve to the correct `ModelObject` metadata after compression.

Current safety behavior:

- If compressed output preserves inspectable `_FEATURE_ID_0` values and sidecar feature counts, the compressed tile is accepted.
- If compressed output removes, quantizes, compresses beyond local validation, or corrupts `_FEATURE_ID_0`, the tile falls back to the original uncompressed GLB.
- Rejected compression is recorded as `rejected_feature_id_validation`; this is a safe outcome, not a failed conversion.
- If real `gltfpack -cc` is rejected, discuss before changing strategy. Possible future paths are safer gltfpack arguments, leaving meshopt disabled, or a deliberate move toward standard glTF feature metadata.

Measure package bytes and meshopt status after conversion with:

```bash
venv/bin/python manage.py measure_plant3d_package <package_id>
```

Useful variants:

```bash
venv/bin/python manage.py measure_plant3d_package --latest 5
venv/bin/python manage.py measure_plant3d_package --source-id <source_id>
venv/bin/python manage.py measure_plant3d_package <package_id> --json
```

The measurement command reports recorded package bytes, measured geometry/sidecar/manifest bytes, tile counts, meshopt status, input/output bytes, saved bytes, saved percent, output/input ratio, compression duration, aggregate summary, and measured-vs-recorded byte drift warnings. It is the standard before/after size/time check once `gltfpack` is available in the worker image.

## IFC Parser Threads

The IfcOpenShell geometry iterator remains single-threaded when no worker option or setting is supplied:

```bash
PLANT3D_PARSER_THREADS=1
```

This preserves deterministic baseline behavior for one-off commands and tests. For local/dev conversion workers, the current recommendation is to use parser threads explicitly:

Recommended local/dev worker:

```bash
venv/bin/python manage.py process_plant3d_job --watch --parser-threads auto
```

`auto` uses `max(1, effective_cpu_count - 1)`, then applies configured thread caps and memory caps. Effective CPU count considers normal Python CPU count, Linux CPU affinity, and Docker/Linux cgroup CPU quotas where available. Memory caps consider Docker/Linux cgroup memory limits where available. A fixed positive integer is also accepted:

```bash
venv/bin/python manage.py process_plant3d_job --watch --parser-threads 4
```

For shared/small Docker hosts, use capped auto or a fixed count:

```bash
venv/bin/python manage.py process_plant3d_job --watch --parser-threads auto --parser-thread-cap 2
venv/bin/python manage.py process_plant3d_job --watch --parser-threads 2
```

The older environment-variable form still works for worker containers:

```bash
PLANT3D_PARSER_THREADS=auto venv/bin/python manage.py process_plant3d_job --watch
PLANT3D_PARSER_THREADS=auto PLANT3D_PARSER_THREAD_CAP=2 venv/bin/python manage.py process_plant3d_job --watch
```

Optional memory tuning for `auto`:

```bash
PLANT3D_PARSER_MEMORY_PER_THREAD_MB=2048
PLANT3D_PARSER_MEMORY_RESERVE_MB=1024
```

Defaults are 2048 MB per parser thread and a 1024 MB worker reserve when a cgroup memory limit is visible. These are conservative placeholders until the real large/project-global IFC gives better data.

The command-line option is preferred for local operation because the active setting is visible in the worker output and applies only to that worker process.

2026-07-01 timing evidence: KR's fresh 13.7 MB `8-SSPAU-800203.ifc` GLB run took 61,073 ms total, with `parse_ms=59,656 ms`. That means about 97.7% of conversion time is IfcOpenShell parse/tessellation, so parser-thread testing is now justified.

2026-07-01 A/B result: the same sample with `--parser-threads auto` completed in 11,826 ms total, with `parse_ms=10,411 ms`. CPU rose to about 97%, GPU stayed unchanged, and RAM stayed around 30%. This confirms threaded parsing as the recommended local/dev worker mode for current samples.

Caveats:

- More parser threads use more RAM.
- `auto` is CPU-aware and cgroup-memory-aware, but it is still a heuristic. On memory-constrained containers, prefer an explicit `--parser-thread-cap` or fixed thread count until the real large-file test validates memory behavior.
- Threaded geometry iteration may change render-package-local feature ID ordering between reconversions.
- Do not persist `feature_id` as a stable identity. Use `stable_id` / source GUID based identity for durable references.
- Record `ifcopenshell_iterator_threads` from package/job metadata when comparing conversion timings.
- The worker calls Python garbage collection after each job. This helps Python-side cleanup, but native IfcOpenShell memory and allocator fragmentation should still be handled operationally by worker recycling for very large or long-running workloads.
- For shared test machines, consider `--max-jobs 5` or a container restart policy so workers periodically exit and restart cleanly after several conversions.

## Production Gaps

Before this becomes a real production worker stack:

- Replace management-command polling with Celery/RQ/django-q or another explicit queue runner.
- Add SSE for job progress.
- Move source/render blobs to S3-compatible object storage or signed/direct URLs.
- Package `gltfpack` in the worker image if meshopt is accepted after measurement.
- Define worker CPU/RAM sizing after the 20 MB and plant-global IFC tests.
- Add retry/cancel policy and cleanup for orphaned source/render blobs.

## Manual Smoke Path

1. Start Django web server.
2. Start worker:

```bash
venv/bin/python manage.py process_plant3d_job --watch
```

3. Upload an IFC through `/plant3d/sources/upload/`.
4. Queue metadata, JSON debug, or GLB conversion from the source detail page.
5. Watch the job row progress stages.
6. Open the package viewer once the package link appears.

For the current largest sample, use:

```text
ifc/8-SSPAR-800206A.ifc
```

## Local Cleanup

Repeated IFC testing creates source rows, conversion jobs, object indexes, render packages, render tiles, and media blobs. Admin deletion is acceptable for a quick DB-only cleanup, but it does not remove stored source/render files.

Use `purge_plant3d_data` when the storage blobs should be cleaned with the database scope.

Dry-run first:

```bash
venv/bin/python manage.py purge_plant3d_data --project-id <proj_id>
venv/bin/python manage.py purge_plant3d_data --source-id <source_id>
venv/bin/python manage.py purge_plant3d_data --all
```

Then confirm only after reviewing the summary:

```bash
venv/bin/python manage.py purge_plant3d_data --project-id <proj_id> --confirm
```

Use `--keep-storage` only when deliberately deleting database rows while retaining media blobs for inspection.
