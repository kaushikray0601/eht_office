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

The measurement command reports recorded package bytes, measured geometry/sidecar/manifest bytes, tile counts, meshopt status, input/output bytes, saved bytes, and compression ratio. It is the standard before/after check once `gltfpack` is available in the worker image.

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
