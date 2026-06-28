import json
import struct
from collections import OrderedDict

import numpy as np


GL_ARRAY_BUFFER = 34962
GL_ELEMENT_ARRAY_BUFFER = 34963
GL_FLOAT = 5126
GL_UNSIGNED_SHORT = 5123
GL_UNSIGNED_INT = 5125


def _align4(data, pad_byte=b"\x00"):
    remainder = len(data) % 4
    if remainder:
        data += pad_byte * (4 - remainder)
    return data


def _color_key(mesh):
    color = ((mesh.get("mesh") or {}).get("color") or [0.45, 0.55, 0.72])[:3]
    return tuple(round(float(value or 0), 4) for value in color)


def _default_mesh_stable_id(mesh):
    properties = mesh.get("properties") or {}
    global_id = str(properties.get("global_id") or "").strip()
    if global_id:
        return f"ifc:{global_id}"
    return str(mesh.get("uid") or "")


def _compute_normals(positions, indices):
    positions_array = np.asarray(positions, dtype=np.float32).reshape((-1, 3))
    normals = np.zeros_like(positions_array, dtype=np.float32)
    if not len(positions_array) or len(indices) < 3:
        return normals.reshape(-1)

    triangle_count = len(indices) // 3
    triangles = np.asarray(indices[: triangle_count * 3], dtype=np.int64).reshape((-1, 3))
    valid = np.all((triangles >= 0) & (triangles < len(positions_array)), axis=1)
    if not np.any(valid):
        normals[:, 2] = 1.0
        return normals.reshape(-1)

    triangles = triangles[valid]
    a = positions_array[triangles[:, 0]]
    b = positions_array[triangles[:, 1]]
    c = positions_array[triangles[:, 2]]
    face_normals = np.cross(b - a, c - a).astype(np.float32, copy=False)
    np.add.at(normals, triangles[:, 0], face_normals)
    np.add.at(normals, triangles[:, 1], face_normals)
    np.add.at(normals, triangles[:, 2], face_normals)

    lengths = np.linalg.norm(normals, axis=1)
    nonzero = lengths > 0
    normals[nonzero] = normals[nonzero] / lengths[nonzero, None]
    normals[~nonzero] = np.array([0.0, 0.0, 1.0], dtype=np.float32)
    return normals.reshape(-1)


def _pack_f32(values):
    return np.asarray(values, dtype="<f4").tobytes()


def _pack_indices(values, component_type):
    if component_type == GL_UNSIGNED_SHORT:
        return np.asarray(values, dtype="<u2").tobytes()
    return np.asarray(values, dtype="<u4").tobytes()


def _bounds_for_positions(positions):
    if not positions:
        return [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]
    positions_array = np.asarray(positions, dtype=np.float32).reshape((-1, 3))
    return positions_array.min(axis=0).astype(float).tolist(), positions_array.max(axis=0).astype(float).tolist()


def build_glb_from_meshes(meshes, metadata=None, stable_id_resolver=None, feature_id_offset=0):
    stable_id_resolver = stable_id_resolver or _default_mesh_stable_id
    buckets = OrderedDict()
    object_spans = []
    object_features = []
    for mesh in meshes:
        mesh_data = mesh.get("mesh") or {}
        positions = mesh_data.get("positions") or []
        indices = mesh_data.get("indices") or []
        if not positions or not indices:
            continue

        key = _color_key(mesh)
        bucket = buckets.setdefault(key, {"positions": [], "indices": [], "feature_ids": [], "objects": []})
        vertex_offset = len(bucket["positions"]) // 3
        first_index = len(bucket["indices"])
        vertex_count = len(positions) // 3
        feature_id = int(feature_id_offset or 0) + len(object_features) + 1
        stable_id = stable_id_resolver(mesh)
        bucket["positions"].extend(float(value or 0.0) for value in positions)
        bucket["indices"].extend(int(index) + vertex_offset for index in indices)
        bucket["feature_ids"].extend([feature_id] * vertex_count)
        span = {
            "feature_id": feature_id,
            "stable_id": stable_id,
            "uid": mesh.get("uid"),
            "object_type": (mesh.get("properties") or {}).get("ifc_class") or mesh.get("kind") or "",
            "bucket_color": list(key),
            "first_index": first_index,
            "index_count": len(indices),
            "vertex_offset": vertex_offset,
            "vertex_count": vertex_count,
        }
        bucket["objects"].append(span)
        object_spans.append(span)
        object_features.append(
            {
                "feature_id": feature_id,
                "stable_id": stable_id,
                "source_object_id": (mesh.get("properties") or {}).get("global_id") or mesh.get("uid") or "",
                "object_type": span["object_type"],
            }
        )

    bin_blob = b""
    buffer_views = []
    accessors = []
    meshes_json = []
    nodes = []
    materials = []

    def append_view(blob, target):
        nonlocal bin_blob
        bin_blob = _align4(bin_blob)
        byte_offset = len(bin_blob)
        bin_blob += blob
        view_index = len(buffer_views)
        buffer_views.append(
            {
                "buffer": 0,
                "byteOffset": byte_offset,
                "byteLength": len(blob),
                "target": target,
            }
        )
        return view_index

    for color, bucket in buckets.items():
        positions = bucket["positions"]
        indices = bucket["indices"]
        feature_ids = bucket["feature_ids"]
        normals = _compute_normals(positions, indices)
        min_pos, max_pos = _bounds_for_positions(positions)
        index_component_type = GL_UNSIGNED_SHORT if indices and max(indices) <= 65535 else GL_UNSIGNED_INT

        position_view = append_view(_pack_f32(positions), GL_ARRAY_BUFFER)
        normal_view = append_view(_pack_f32(normals), GL_ARRAY_BUFFER)
        feature_view = append_view(_pack_f32(feature_ids), GL_ARRAY_BUFFER)
        index_view = append_view(_pack_indices(indices, index_component_type), GL_ELEMENT_ARRAY_BUFFER)

        position_accessor = len(accessors)
        accessors.append(
            {
                "bufferView": position_view,
                "componentType": GL_FLOAT,
                "count": len(positions) // 3,
                "type": "VEC3",
                "min": min_pos,
                "max": max_pos,
            }
        )
        normal_accessor = len(accessors)
        accessors.append(
            {
                "bufferView": normal_view,
                "componentType": GL_FLOAT,
                "count": len(normals) // 3,
                "type": "VEC3",
            }
        )
        feature_accessor = len(accessors)
        accessors.append(
            {
                "bufferView": feature_view,
                "componentType": GL_FLOAT,
                "count": len(feature_ids),
                "type": "SCALAR",
                "min": [min(feature_ids)] if feature_ids else [0],
                "max": [max(feature_ids)] if feature_ids else [0],
            }
        )
        index_accessor = len(accessors)
        accessors.append(
            {
                "bufferView": index_view,
                "componentType": index_component_type,
                "count": len(indices),
                "type": "SCALAR",
            }
        )

        material_index = len(materials)
        materials.append(
            {
                "name": f"color_{material_index:03d}",
                "pbrMetallicRoughness": {
                    "baseColorFactor": [color[0], color[1], color[2], 1.0],
                    "metallicFactor": 0.05,
                    "roughnessFactor": 0.75,
                },
                "doubleSided": True,
            }
        )
        mesh_index = len(meshes_json)
        meshes_json.append(
            {
                "name": f"bucket_{mesh_index:03d}",
                "primitives": [
                    {
                        "attributes": {
                            "POSITION": position_accessor,
                            "NORMAL": normal_accessor,
                            "_FEATURE_ID_0": feature_accessor,
                        },
                        "indices": index_accessor,
                        "material": material_index,
                        "mode": 4,
                    }
                ],
            }
        )
        nodes.append({"mesh": mesh_index, "name": f"bucket_{mesh_index:03d}"})

    gltf = {
        "asset": {"version": "2.0", "generator": "plant3d.glb"},
        "scene": 0,
        "scenes": [{"nodes": list(range(len(nodes)))}],
        "nodes": nodes,
        "meshes": meshes_json,
        "materials": materials,
        "buffers": [{"byteLength": len(bin_blob)}],
        "bufferViews": buffer_views,
        "accessors": accessors,
    }
    if metadata:
        gltf["extras"] = metadata

    json_blob = _align4(json.dumps(gltf, separators=(",", ":")).encode("utf-8"), b" ")
    bin_blob = _align4(bin_blob)
    length = 12 + 8 + len(json_blob) + 8 + len(bin_blob)
    glb = b"".join(
        [
            struct.pack("<III", 0x46546C67, 2, length),
            struct.pack("<I4s", len(json_blob), b"JSON"),
            json_blob,
            struct.pack("<I4s", len(bin_blob), b"BIN\x00"),
            bin_blob,
        ]
    )
    sidecar = {
        "format": "GLB",
        "mesh_count": len(meshes),
        "render_batch_count": len(buckets),
        "feature_id_attribute": "_FEATURE_ID_0",
        "object_features": object_features,
        "object_spans": object_spans,
        "metadata": metadata or {},
    }
    return glb, sidecar
