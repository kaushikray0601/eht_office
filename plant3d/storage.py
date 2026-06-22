import posixpath
from pathlib import Path

from django.conf import settings


def plant3d_storage_root():
    return Path(settings.MEDIA_ROOT) / "plant3d"


def safe_name(name):
    clean = Path(str(name or "upload.bin")).name.strip()
    return clean or "upload.bin"


def source_storage_key(project_id, signature, filename):
    return posixpath.join("plant3d", "source", str(project_id), signature[:16], safe_name(filename))


def render_manifest_storage_key(source_id):
    return posixpath.join("plant3d", "render", str(source_id), "manifest.json")


def path_for_storage_key(storage_key):
    parts = [part for part in str(storage_key).split("/") if part]
    return Path(settings.MEDIA_ROOT).joinpath(*parts)


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

