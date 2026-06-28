import posixpath
from pathlib import Path

from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation


def safe_name(name):
    clean = Path(str(name or "upload.bin")).name.strip()
    return clean or "upload.bin"


def source_storage_key(project_id, signature, filename):
    return posixpath.join("plant3d", "source", str(project_id), signature[:16], safe_name(filename))


def render_manifest_storage_key(source_id):
    return posixpath.join("plant3d", "render", str(source_id), "manifest.json")


def path_for_storage_key(storage_key):
    parts = [part for part in str(storage_key).split("/") if part]
    if any(part in {".", ".."} for part in parts):
        raise SuspiciousFileOperation("Invalid plant3d storage key.")

    root = Path(settings.MEDIA_ROOT).resolve()
    path = root.joinpath(*parts).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise SuspiciousFileOperation("Plant3d storage key escapes MEDIA_ROOT.") from exc
    return path


def exists(storage_key):
    return path_for_storage_key(storage_key).exists()


def read_bytes(storage_key, limit_bytes=None):
    path = path_for_storage_key(storage_key)
    with path.open("rb") as handle:
        return handle.read(limit_bytes) if limit_bytes is not None else handle.read()


def read_text(storage_key):
    return path_for_storage_key(storage_key).read_text(encoding="utf-8")


def stat_size(storage_key):
    return path_for_storage_key(storage_key).stat().st_size


def write_bytes(storage_key, data):
    path = path_for_storage_key(storage_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def write_text(storage_key, text):
    path = path_for_storage_key(storage_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path
