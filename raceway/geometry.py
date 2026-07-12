import math


MIN_SEGMENT_LENGTH_M = 0.000001
PLAN_BEND_COSINE_LIMIT = 0.996


def point_from_node(node):
    return {
        "x": float(node.source_x_m),
        "y": float(node.source_y_m),
        "z": float(node.source_z_m),
    }


def distance(left, right):
    dx = left["x"] - right["x"]
    dy = left["y"] - right["y"]
    dz = left["z"] - right["z"]
    return math.sqrt((dx * dx) + (dy * dy) + (dz * dz))


def plan_bend_angle_deg(previous_node, node, next_node):
    in_x = float(node.source_x_m) - float(previous_node.source_x_m)
    in_y = float(node.source_y_m) - float(previous_node.source_y_m)
    out_x = float(next_node.source_x_m) - float(node.source_x_m)
    out_y = float(next_node.source_y_m) - float(node.source_y_m)
    in_plan = math.hypot(in_x, in_y)
    out_plan = math.hypot(out_x, out_y)
    if in_plan < MIN_SEGMENT_LENGTH_M or out_plan < MIN_SEGMENT_LENGTH_M:
        return None
    cosine = ((in_x * out_x) + (in_y * out_y)) / (in_plan * out_plan)
    cosine = max(-1.0, min(1.0, cosine))
    if cosine >= PLAN_BEND_COSINE_LIMIT:
        return None
    return math.degrees(math.acos(cosine))


def is_plan_bend(previous_node, node, next_node):
    return plan_bend_angle_deg(previous_node, node, next_node) is not None


def interpolate(start, end, ratio):
    return start + (end - start) * ratio


def normalize_bounds(bounds):
    if not isinstance(bounds, dict):
        return None
    if all(key in bounds for key in ("min_x", "max_x", "min_y", "max_y", "min_z", "max_z")):
        try:
            return _bounds_from_axis_values(
                bounds["min_x"],
                bounds["max_x"],
                bounds["min_y"],
                bounds["max_y"],
                bounds["min_z"],
                bounds["max_z"],
            )
        except (TypeError, ValueError):
            return None
    if isinstance(bounds.get("min"), (list, tuple)) and isinstance(bounds.get("max"), (list, tuple)):
        if len(bounds["min"]) >= 3 and len(bounds["max"]) >= 3:
            try:
                return _bounds_from_axis_values(
                    bounds["min"][0],
                    bounds["max"][0],
                    bounds["min"][1],
                    bounds["max"][1],
                    bounds["min"][2],
                    bounds["max"][2],
                )
            except (TypeError, ValueError):
                return None
    if isinstance(bounds.get("min"), dict) and isinstance(bounds.get("max"), dict):
        try:
            return _bounds_from_axis_values(
                bounds["min"]["x"],
                bounds["max"]["x"],
                bounds["min"]["y"],
                bounds["max"]["y"],
                bounds["min"]["z"],
                bounds["max"]["z"],
            )
        except (KeyError, TypeError, ValueError):
            return None
    return None


def bounds_from_points(points, *, margin_m=0.0):
    valid_points = [
        {
            "x": float(point["x"]),
            "y": float(point["y"]),
            "z": float(point["z"]),
        }
        for point in points
    ]
    return inflate_bounds(
        {
            "min_x": min(point["x"] for point in valid_points),
            "max_x": max(point["x"] for point in valid_points),
            "min_y": min(point["y"] for point in valid_points),
            "max_y": max(point["y"] for point in valid_points),
            "min_z": min(point["z"] for point in valid_points),
            "max_z": max(point["z"] for point in valid_points),
        },
        margin_m,
    )


def inflate_bounds(bounds, margin_m):
    normalized = normalize_bounds(bounds)
    if normalized is None:
        return None
    margin = max(float(margin_m or 0.0), 0.0)
    return {
        "min_x": normalized["min_x"] - margin,
        "max_x": normalized["max_x"] + margin,
        "min_y": normalized["min_y"] - margin,
        "max_y": normalized["max_y"] + margin,
        "min_z": normalized["min_z"] - margin,
        "max_z": normalized["max_z"] + margin,
    }


def bounds_intersect(left, right):
    left_bounds = normalize_bounds(left)
    right_bounds = normalize_bounds(right)
    if left_bounds is None or right_bounds is None:
        return False
    return (
        left_bounds["min_x"] <= right_bounds["max_x"]
        and left_bounds["max_x"] >= right_bounds["min_x"]
        and left_bounds["min_y"] <= right_bounds["max_y"]
        and left_bounds["max_y"] >= right_bounds["min_y"]
        and left_bounds["min_z"] <= right_bounds["max_z"]
        and left_bounds["max_z"] >= right_bounds["min_z"]
    )


def bounds_gap(left, right):
    left_bounds = normalize_bounds(left)
    right_bounds = normalize_bounds(right)
    if left_bounds is None or right_bounds is None:
        return None
    gaps = []
    for axis in ("x", "y", "z"):
        left_min = left_bounds[f"min_{axis}"]
        left_max = left_bounds[f"max_{axis}"]
        right_min = right_bounds[f"min_{axis}"]
        right_max = right_bounds[f"max_{axis}"]
        if left_max < right_min:
            gaps.append(right_min - left_max)
        elif right_max < left_min:
            gaps.append(left_min - right_max)
        else:
            gaps.append(0.0)
    return math.sqrt(sum(gap * gap for gap in gaps))


def point_to_segment_distance(point, start, end):
    vector = {
        "x": end["x"] - start["x"],
        "y": end["y"] - start["y"],
        "z": end["z"] - start["z"],
    }
    length_sq = (vector["x"] * vector["x"]) + (vector["y"] * vector["y"]) + (vector["z"] * vector["z"])
    if length_sq < MIN_SEGMENT_LENGTH_M:
        return distance(point, start), dict(start)
    ratio = (
        ((point["x"] - start["x"]) * vector["x"])
        + ((point["y"] - start["y"]) * vector["y"])
        + ((point["z"] - start["z"]) * vector["z"])
    ) / length_sq
    ratio = max(0.0, min(1.0, ratio))
    target_point = {
        "x": interpolate(start["x"], end["x"], ratio),
        "y": interpolate(start["y"], end["y"], ratio),
        "z": interpolate(start["z"], end["z"], ratio),
    }
    return distance(point, target_point), target_point


def bounds_center(bounds):
    normalized = normalize_bounds(bounds)
    if normalized is None:
        return None
    return {
        "x": (normalized["min_x"] + normalized["max_x"]) / 2.0,
        "y": (normalized["min_y"] + normalized["max_y"]) / 2.0,
        "z": (normalized["min_z"] + normalized["max_z"]) / 2.0,
    }


def _bounds_from_axis_values(min_x, max_x, min_y, max_y, min_z, max_z):
    x_values = sorted([float(min_x), float(max_x)])
    y_values = sorted([float(min_y), float(max_y)])
    z_values = sorted([float(min_z), float(max_z)])
    return {
        "min_x": x_values[0],
        "max_x": x_values[1],
        "min_y": y_values[0],
        "max_y": y_values[1],
        "min_z": z_values[0],
        "max_z": z_values[1],
    }
