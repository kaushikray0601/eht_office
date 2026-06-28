import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from django.conf import settings


def gltfpack_command():
    configured = getattr(settings, "PLANT3D_GLTFPACK_BIN", "") or os.environ.get("PLANT3D_GLTFPACK_BIN", "")
    if configured:
        return configured
    return shutil.which("gltfpack") or ""


def gltfpack_args():
    configured = getattr(settings, "PLANT3D_GLTFPACK_ARGS", None)
    if configured is None:
        configured = os.environ.get("PLANT3D_GLTFPACK_ARGS", "-cc")
    if isinstance(configured, str):
        return [part for part in configured.split() if part]
    return list(configured)


def compress_glb_meshopt(glb_bytes, timeout_seconds=120):
    command = gltfpack_command()
    if not command:
        return glb_bytes, {
            "enabled": False,
            "status": "skipped",
            "reason": "gltfpack_not_available",
            "input_bytes": len(glb_bytes),
            "output_bytes": len(glb_bytes),
        }

    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="plant3d_meshopt_") as tempdir:
        temp_path = Path(tempdir)
        input_path = temp_path / "input.glb"
        output_path = temp_path / "output.glb"
        input_path.write_bytes(glb_bytes)
        try:
            process = subprocess.run(
                [command, "-i", str(input_path), "-o", str(output_path), *gltfpack_args()],
                check=False,
                capture_output=True,
                timeout=timeout_seconds,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            return glb_bytes, {
                "enabled": True,
                "status": "failed",
                "reason": str(exc),
                "input_bytes": len(glb_bytes),
                "output_bytes": len(glb_bytes),
                "duration_ms": round((time.perf_counter() - started) * 1000),
            }
        if process.returncode != 0 or not output_path.exists():
            stderr = process.stderr.decode("utf-8", errors="replace").strip()
            stdout = process.stdout.decode("utf-8", errors="replace").strip()
            return glb_bytes, {
                "enabled": True,
                "status": "failed",
                "reason": stderr or stdout or f"gltfpack exited {process.returncode}",
                "input_bytes": len(glb_bytes),
                "output_bytes": len(glb_bytes),
                "duration_ms": round((time.perf_counter() - started) * 1000),
            }

        compressed = output_path.read_bytes()
        return compressed, {
            "enabled": True,
            "status": "completed",
            "tool": "gltfpack",
            "command": command,
            "args": gltfpack_args(),
            "input_bytes": len(glb_bytes),
            "output_bytes": len(compressed),
            "ratio": round(len(compressed) / len(glb_bytes), 4) if glb_bytes else 1.0,
            "duration_ms": round((time.perf_counter() - started) * 1000),
        }
