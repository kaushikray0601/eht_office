import ast
import json
import os
from decimal import Decimal

from django.core.exceptions import PermissionDenied
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from eht.models import ManagedProject, ProjectData
from plant3d.models import ModelObject, RenderPackage, SourceModel

from .access import (
    accessible_project_ids,
    normalize_project_id,
    require_project_access,
    user_can_access_project,
    validate_project_id,
)
from .fittings import build_layer_fitting_projection
from .graph import GRAPH_NODE_TOLERANCE_M, NEAR_MISS_ENDPOINT_RADIUS_M, build_layer_graph, build_project_graph
from .geometry import normalize_bounds
from .models import (
    SOURCE_COORDINATE_FRAME,
    RacewayFamily,
    RacewayLayer,
    RacewayNode,
    RacewayRun,
    RacewaySize,
)
from .schedule import PLACEHOLDER_SUPPORT_SPAN_M, build_layer_schedule
from .warnings import (
    EXCESSIVE_BEND_COUNT_WARNING,
    MODEL_OBJECT_SCAN_LIMIT,
    SHORT_SEGMENT_WARNING_M,
    build_layer_warnings,
    summarize_warnings,
)


def create_project(proj_id):
    ManagedProject.objects.get_or_create(
        proj_id=proj_id,
        defaults={"description": f"Project {proj_id}", "is_active": True},
    )
    return ProjectData.objects.create(
        proj_id=proj_id,
        min_amb_t=Decimal("0.00"),
        max_amb_t=Decimal("40.00"),
        startup_t=Decimal("10.00"),
        area_class="NON-HAZ",
        temp_class="T3",
        voltage=Decimal("230.00"),
        max_cb_size=10,
        restrict_cb_current=Decimal("16.00"),
        vendor="THR",
        spiral_wrap_allowed=True,
        spiral_factor=Decimal("1.00"),
        margin_on_tracer_lengths=Decimal("5.00"),
        voltage_var_factor=Decimal("1.00"),
        res_tol=Decimal("10.00"),
        termination_margin=Decimal("100.00"),
        heat_loss_sf=Decimal("1.00"),
        wind_speed=Decimal("1.00"),
        caution_label_interval=3,
        ckt_ln=Decimal("10.00"),
        loop_ln=Decimal("10.00"),
        alpha_for_res=Decimal("1.0000"),
        allowablevdrop=Decimal("5.00"),
    )


def assign_project(user, project):
    ManagedProject.objects.get(proj_id=project.proj_id).assigned_users.add(user)


def create_family(code="TEST-LADDER-HDG"):
    return RacewayFamily.objects.create(
        code=code,
        name=f"{code} family",
        kind="ladder",
        material="HDG steel",
    )


def create_size(family=None, width_mm=300, depth_mm=100):
    return RacewaySize.objects.create(
        family=family or create_family(),
        width_mm=width_mm,
        depth_mm=depth_mm,
    )


def create_layer(project_id="RWY-SCHEMA"):
    return RacewayLayer.objects.create(
        project_id=project_id,
        source_model_id=11,
        render_package_id=22,
        name="AG tray draft",
    )


def create_run(layer=None, family=None, size=None):
    family = family or create_family()
    size = size or create_size(family=family)
    return RacewayRun.objects.create(
        layer=layer or create_layer(),
        family=family,
        size=size,
        tag="RWY-001",
        service_class="power",
        elevation_m=106.5,
        source_model_id=11,
        render_package_id=22,
    )


def create_source_and_package(project_id):
    source = SourceModel.objects.create(
        project_id=project_id,
        display_name="Raceway source",
        source_format="IFC",
        original_filename="raceway.ifc",
        storage_key="source/raceway.ifc",
    )
    package = RenderPackage.objects.create(
        source_model=source,
        package_format="GLB",
        storage_prefix="render/raceway/",
    )
    return source, package


def create_nodes(run, points, *, kinds=None):
    kinds = kinds or []
    return [
        RacewayNode.objects.create(
            run=run,
            sequence=index,
            node_kind=kinds[index] if index < len(kinds) else "intermediate",
            source_x_m=point[0],
            source_y_m=point[1],
            source_z_m=point[2],
        )
        for index, point in enumerate(points)
    ]


def json_body(payload):
    return json.dumps(payload)


class RacewaySkeletonTests(TestCase):
    def test_home_endpoint_identifies_peer_consumer_boundary(self):
        user = get_user_model().objects.create_user(username="raceway-user", password="pw")
        self.client.force_login(user)

        response = self.client.get(reverse("raceway:home"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "app": "raceway",
                "status": "ok",
                "boundary": "peer-consumer",
                "platform": "plant3d",
            },
        )

    def test_home_endpoint_requires_authentication(self):
        response = self.client.get(reverse("raceway:home"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])


class RacewayCatalogTests(TestCase):
    def test_catalog_endpoint_returns_generic_vendor_free_seed(self):
        user = get_user_model().objects.create_user(username="raceway-catalog-user", password="pw")
        self.client.force_login(user)

        response = self.client.get(reverse("raceway:catalog"))

        self.assertEqual(response.status_code, 200)
        families = {family["code"]: family for family in response.json()["families"]}
        self.assertIn("LADDER-HDG", families)
        self.assertIn("PERF-HDG", families)
        self.assertFalse(families["LADDER-HDG"]["is_validated"])
        self.assertEqual(families["LADDER-HDG"]["standard_basis"], "IEC 61537")
        self.assertEqual(
            [(size["width_mm"], size["depth_mm"]) for size in families["LADDER-HDG"]["sizes"]],
            [(300, 100), (450, 100), (600, 150)],
        )


class RacewayBoundaryTests(TestCase):
    def test_plant3d_runtime_modules_do_not_import_raceway(self):
        plant3d_root = os.path.join(os.path.dirname(__file__), "..", "plant3d")
        offenders = []
        for directory, _dirnames, filenames in os.walk(plant3d_root):
            rel_dir = os.path.relpath(directory, plant3d_root)
            path_parts = set(rel_dir.split(os.sep))
            if "__pycache__" in path_parts or "migrations" in path_parts:
                continue
            for filename in filenames:
                if not filename.endswith(".py"):
                    continue
                path = os.path.join(directory, filename)
                rel_path = os.path.relpath(path, plant3d_root)
                if rel_path == "tests.py":
                    continue
                with open(path, encoding="utf-8") as handle:
                    content = handle.read()
                if "from raceway" in content or "import raceway" in content:
                    offenders.append(rel_path)

        self.assertEqual(offenders, [])


class RacewayAccessTests(TestCase):
    def test_normalize_project_id_accepts_project_objects_and_strings(self):
        project = create_project("RWY-ACCESS-ID")

        self.assertEqual(normalize_project_id(project), "RWY-ACCESS-ID")
        self.assertEqual(normalize_project_id(" RWY-ACCESS-ID "), "RWY-ACCESS-ID")
        self.assertEqual(normalize_project_id(None), "")

    def test_accessible_project_ids_follow_plant3d_gateway_scope(self):
        user = get_user_model().objects.create_user(username="raceway-access-user", password="pw")
        accessible = create_project("RWY-ACCESS-OK")
        create_project("RWY-ACCESS-NO")
        assign_project(user, accessible)

        self.assertEqual(accessible_project_ids(user), ["RWY-ACCESS-OK"])

    def test_validate_project_id_accepts_accessible_project(self):
        user = get_user_model().objects.create_user(username="raceway-valid-user", password="pw")
        project = create_project("RWY-VALID")
        assign_project(user, project)

        self.assertEqual(validate_project_id(project.proj_id, user), "RWY-VALID")
        self.assertTrue(user_can_access_project(user, project.proj_id))
        self.assertEqual(require_project_access(project.proj_id, user), "RWY-VALID")

    def test_validate_project_id_rejects_inaccessible_project(self):
        user = get_user_model().objects.create_user(username="raceway-invalid-user", password="pw")
        project = create_project("RWY-BLOCKED")

        self.assertEqual(validate_project_id(project.proj_id, user), "")
        self.assertFalse(user_can_access_project(user, project.proj_id))
        with self.assertRaises(PermissionDenied):
            require_project_access(project.proj_id, user)

    def test_raceway_runtime_modules_do_not_import_eht_models_directly(self):
        raceway_root = os.path.dirname(__file__)
        offenders = []
        for directory, _dirnames, filenames in os.walk(raceway_root):
            rel_dir = os.path.relpath(directory, raceway_root)
            path_parts = set(rel_dir.split(os.sep))
            if "__pycache__" in path_parts or "migrations" in path_parts:
                continue
            for filename in filenames:
                if not filename.endswith(".py"):
                    continue
                path = os.path.join(directory, filename)
                rel_path = os.path.relpath(path, raceway_root)
                if rel_path == "tests.py":
                    continue
                with open(path, encoding="utf-8") as handle:
                    content = handle.read()
                tree = ast.parse(content, filename=path)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom) and (
                        node.module == "eht" or str(node.module or "").startswith("eht.")
                    ):
                        offenders.append(rel_path)
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if alias.name == "eht" or alias.name.startswith("eht."):
                                offenders.append(rel_path)

        self.assertEqual(offenders, [])

    def test_raceway_runtime_modules_do_not_import_plant3d_models_directly(self):
        raceway_root = os.path.dirname(__file__)
        offenders = []
        for directory, _dirnames, filenames in os.walk(raceway_root):
            rel_dir = os.path.relpath(directory, raceway_root)
            path_parts = set(rel_dir.split(os.sep))
            if "__pycache__" in path_parts or "migrations" in path_parts:
                continue
            for filename in filenames:
                if not filename.endswith(".py"):
                    continue
                path = os.path.join(directory, filename)
                rel_path = os.path.relpath(path, raceway_root)
                if rel_path == "tests.py":
                    continue
                with open(path, encoding="utf-8") as handle:
                    content = handle.read()
                tree = ast.parse(content, filename=path)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom) and node.module == "plant3d.models":
                        offenders.append(rel_path)
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if alias.name == "plant3d.models":
                                offenders.append(rel_path)

        self.assertEqual(offenders, [])


class RacewayModelTests(TestCase):
    def test_family_and_size_store_generic_iec_metric_catalogue_data(self):
        family = create_family()
        size = create_size(family=family, width_mm=450, depth_mm=125)

        self.assertEqual(family.standard_basis, "IEC 61537")
        self.assertFalse(family.is_validated)
        self.assertEqual(size.width_mm, 450)
        self.assertEqual(size.depth_mm, 125)

    def test_size_is_unique_per_family_width_and_depth(self):
        family = create_family()
        create_size(family=family, width_mm=300, depth_mm=100)

        with self.assertRaises(IntegrityError):
            create_size(family=family, width_mm=300, depth_mm=100)

    def test_layer_stores_loose_project_and_package_context(self):
        layer = create_layer(project_id="RWY-LOOSE")

        self.assertEqual(layer.project_id, "RWY-LOOSE")
        self.assertEqual(layer.source_model_id, 11)
        self.assertEqual(layer.render_package_id, 22)

    def test_run_and_nodes_have_stable_keys_and_source_coordinates(self):
        run = create_run()
        node = RacewayNode.objects.create(
            run=run,
            sequence=0,
            node_kind="endpoint",
            source_x_m=1000.25,
            source_y_m=2000.5,
            source_z_m=106.5,
            anchor={"owner_module": "raceway", "anchor_kind": "model_object", "stable_id": "ifc:beam-001"},
        )

        self.assertEqual(run.coordinate_frame, SOURCE_COORDINATE_FRAME)
        self.assertTrue(run.key)
        self.assertTrue(node.key)
        self.assertEqual(node.source_x_m, 1000.25)
        self.assertEqual(node.anchor["stable_id"], "ifc:beam-001")

    def test_run_rejects_size_from_another_family(self):
        layer = create_layer()
        family = create_family("LADDER-A")
        other_family = create_family("LADDER-B")
        size = create_size(family=other_family)
        run = RacewayRun(layer=layer, family=family, size=size)

        with self.assertRaises(ValidationError):
            run.full_clean()

    def test_run_rejects_non_source_coordinate_frame(self):
        run = create_run()
        run.coordinate_frame = "render_xyz_m"

        with self.assertRaises(ValidationError):
            run.full_clean()

    def test_node_rejects_non_finite_source_coordinates(self):
        run = create_run()
        node = RacewayNode(
            run=run,
            sequence=1,
            source_x_m=float("nan"),
            source_y_m=0.0,
            source_z_m=0.0,
        )

        with self.assertRaises(ValidationError):
            node.full_clean()

    def test_node_sequence_is_unique_per_run(self):
        run = create_run()
        RacewayNode.objects.create(run=run, sequence=0, source_x_m=0.0, source_y_m=0.0, source_z_m=0.0)

        with self.assertRaises(IntegrityError):
            RacewayNode.objects.create(run=run, sequence=0, source_x_m=1.0, source_y_m=0.0, source_z_m=0.0)

    def test_raceway_models_do_not_fk_to_plant3d_or_eht_models(self):
        offenders = []
        for model in [RacewayFamily, RacewaySize, RacewayLayer, RacewayRun, RacewayNode]:
            for field in model._meta.get_fields():
                remote_model = getattr(field, "related_model", None)
                if remote_model is not None and remote_model._meta.app_label in {"plant3d", "eht"}:
                    offenders.append(f"{model.__name__}.{field.name}->{remote_model._meta.label}")

        self.assertEqual(offenders, [])


class RacewayGraphProjectionTests(TestCase):
    def test_graph_projection_derives_branch_and_warns_for_unconnected_crossing(self):
        layer = create_layer(project_id="RWY-GRAPH")
        family = create_family("GRAPH-LADDER")
        size = create_size(family=family)
        trunk = create_run(layer=layer, family=family, size=size)
        trunk.tag = "RWY-TRUNK"
        trunk.save()
        create_nodes(
            trunk,
            [(0.0, 0.0, 0.0), (5.0, 0.0, 0.0), (10.0, 0.0, 0.0)],
            kinds=["endpoint", "bend", "endpoint"],
        )
        branch = create_run(layer=layer, family=family, size=size)
        branch.tag = "RWY-BRANCH"
        branch.save()
        create_nodes(branch, [(5.0, 0.0, 0.0), (5.0, 5.0, 0.0)])
        crossing = create_run(layer=layer, family=family, size=size)
        crossing.tag = "RWY-CROSS"
        crossing.save()
        create_nodes(crossing, [(2.0, -2.0, 0.0), (2.0, 2.0, 0.0)])

        graph = build_layer_graph(layer)
        payload = graph.to_payload()

        self.assertEqual(payload["tolerance_m"], GRAPH_NODE_TOLERANCE_M)
        branch_nodes = [node for node in payload["nodes"] if node["derived_kind"] == "branch"]
        self.assertEqual(len(branch_nodes), 1)
        self.assertEqual(branch_nodes[0]["degree"], 3)
        self.assertEqual(set(branch_nodes[0]["run_ids"]), {trunk.pk, branch.pk})
        warnings = [warning for warning in payload["warnings"] if warning["code"] == "raceway.graph.unconnected_crossing"]
        self.assertEqual(len(warnings), 1)
        self.assertEqual(set(warnings[0]["run_ids"]), {trunk.pk, crossing.pk})
        self.assertAlmostEqual(warnings[0]["source_point_m"]["x"], 2.0)
        self.assertAlmostEqual(warnings[0]["source_point_m"]["y"], 0.0)

    def test_graph_projection_derives_riser_from_geometry_not_persisted_kind(self):
        layer = create_layer(project_id="RWY-RISER")
        family = create_family("GRAPH-RISER-LADDER")
        size = create_size(family=family)
        run = create_run(layer=layer, family=family, size=size)
        create_nodes(
            run,
            [(0.0, 0.0, 0.0), (5.0, 0.0, 0.0), (5.0, 0.0, 2.0), (10.0, 0.0, 2.0)],
            kinds=["endpoint", "bend", "bend", "endpoint"],
        )

        graph = build_layer_graph(layer)
        payload = graph.to_payload()

        riser_edges = [edge for edge in payload["edges"] if edge["is_riser"]]
        self.assertEqual(len(riser_edges), 1)
        riser_members = [
            member
            for node in payload["nodes"]
            for member in node["members"]
            if member["sequence"] in {1, 2}
        ]
        self.assertEqual({member["persisted_kind"] for member in riser_members}, {"bend"})
        self.assertEqual({member["derived_kind"] for member in riser_members}, {"riser"})
        self.assertIn("riser", {node["derived_kind"] for node in payload["nodes"]})

    def test_project_graph_projection_is_project_scoped(self):
        family = create_family("GRAPH-SCOPE-LADDER")
        size = create_size(family=family)
        included_layer = create_layer(project_id="RWY-GRAPH-IN")
        excluded_layer = create_layer(project_id="RWY-GRAPH-OUT")
        included_run = create_run(layer=included_layer, family=family, size=size)
        excluded_run = create_run(layer=excluded_layer, family=family, size=size)
        create_nodes(included_run, [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0)])
        create_nodes(excluded_run, [(10.0, 0.0, 0.0), (11.0, 0.0, 0.0)])

        graph = build_project_graph("RWY-GRAPH-IN")
        run_ids = {
            edge["run_id"]
            for edge in graph.to_payload()["edges"]
        }

        self.assertEqual(run_ids, {included_run.pk})

    def test_graph_projection_warns_when_endpoint_nearly_misses_another_run(self):
        layer = create_layer(project_id="RWY-NEAR-MISS")
        family = create_family("GRAPH-NEAR-LADDER")
        size = create_size(family=family)
        trunk = create_run(layer=layer, family=family, size=size)
        trunk.tag = "RWY-TRUNK"
        trunk.save()
        create_nodes(trunk, [(0.0, 0.0, 0.0), (10.0, 0.0, 0.0)])
        branch = create_run(layer=layer, family=family, size=size)
        branch.tag = "RWY-BRANCH"
        branch.save()
        create_nodes(branch, [(5.0, 0.12, 0.0), (5.0, 3.0, 0.0)])

        payload = build_layer_graph(layer).to_payload()
        warnings = [warning for warning in payload["warnings"] if warning["code"] == "raceway.graph.near_miss_endpoint"]

        self.assertEqual(payload["near_miss_endpoint_radius_m"], NEAR_MISS_ENDPOINT_RADIUS_M)
        self.assertEqual(len(warnings), 1)
        self.assertEqual(warnings[0]["endpoint_run_id"], branch.pk)
        self.assertEqual(warnings[0]["target_run_id"], trunk.pk)
        self.assertEqual(warnings[0]["target_kind"], "edge")
        self.assertAlmostEqual(warnings[0]["distance_m"], 0.12)
        self.assertLess(GRAPH_NODE_TOLERANCE_M, warnings[0]["distance_m"])
        self.assertLess(warnings[0]["distance_m"], NEAR_MISS_ENDPOINT_RADIUS_M)


class RacewayGeometryHelperTests(TestCase):
    def test_normalize_bounds_accepts_plant3d_and_legacy_shapes(self):
        self.assertEqual(
            normalize_bounds({"min_x": 5, "max_x": 1, "min_y": 0, "max_y": 2, "min_z": -1, "max_z": 3}),
            {"min_x": 1.0, "max_x": 5.0, "min_y": 0.0, "max_y": 2.0, "min_z": -1.0, "max_z": 3.0},
        )
        self.assertEqual(
            normalize_bounds({"min": [0, 1, 2], "max": [3, 4, 5]}),
            {"min_x": 0.0, "max_x": 3.0, "min_y": 1.0, "max_y": 4.0, "min_z": 2.0, "max_z": 5.0},
        )
        self.assertEqual(
            normalize_bounds({"min": {"x": 0, "y": 1, "z": 2}, "max": {"x": 3, "y": 4, "z": 5}}),
            {"min_x": 0.0, "max_x": 3.0, "min_y": 1.0, "max_y": 4.0, "min_z": 2.0, "max_z": 5.0},
        )
        self.assertIsNone(normalize_bounds({"min_x": 0, "max_x": 1}))


class RacewayWarningProjectionTests(TestCase):
    def test_layer_warnings_standardize_route_catalog_and_context_notices(self):
        layer = RacewayLayer.objects.create(project_id="RWY-WARN", name="Warning draft")
        family = create_family("WARN-LADDER")
        family.is_active = False
        family.save()
        size = create_size(family=family)
        run = create_run(layer=layer, family=family, size=size)
        create_nodes(run, [(0.0, 0.0, 0.0), (SHORT_SEGMENT_WARNING_M / 2, 0.0, 0.0)])

        warnings = build_layer_warnings(layer)
        codes = {warning["code"] for warning in warnings}
        summary = summarize_warnings(warnings)

        self.assertIn("raceway.warning.unknown_coordinate_context", codes)
        self.assertIn("raceway.warning.inactive_catalog_reference", codes)
        self.assertIn("raceway.warning.short_segment", codes)
        self.assertIn("raceway.warning.support_span_placeholder_basis", codes)
        short_warning = next(warning for warning in warnings if warning["code"] == "raceway.warning.short_segment")
        self.assertEqual(short_warning["source"], "route")
        self.assertEqual(short_warning["object_type"], "segment")
        self.assertEqual(short_warning["run_id"], run.pk)
        self.assertAlmostEqual(short_warning["values"]["threshold_m"], SHORT_SEGMENT_WARNING_M)
        self.assertGreaterEqual(summary["warning"], 3)
        self.assertEqual(summary["info"], 1)

    def test_layer_warnings_flag_excessive_plan_bends(self):
        layer = create_layer(project_id="RWY-WARN-BENDS")
        family = create_family("WARN-BEND-LADDER")
        size = create_size(family=family)
        run = create_run(layer=layer, family=family, size=size)
        points = [
            (0.0, 0.0, 0.0),
            (1.0, 0.0, 0.0),
            (1.0, 1.0, 0.0),
            (2.0, 1.0, 0.0),
            (2.0, 2.0, 0.0),
            (3.0, 2.0, 0.0),
            (3.0, 3.0, 0.0),
            (4.0, 3.0, 0.0),
            (4.0, 4.0, 0.0),
            (5.0, 4.0, 0.0),
            (5.0, 5.0, 0.0),
        ]
        create_nodes(run, points)

        warnings = build_layer_warnings(layer)
        excessive_warning = next(
            warning for warning in warnings if warning["code"] == "raceway.warning.excessive_bends"
        )

        self.assertEqual(excessive_warning["values"]["threshold"], EXCESSIVE_BEND_COUNT_WARNING)
        self.assertGreater(excessive_warning["values"]["plan_bend_count"], EXCESSIVE_BEND_COUNT_WARNING)

    def test_layer_warnings_flag_rough_model_object_aabb_clash(self):
        project_id = "RWY-WARN-CLASH"
        source, package = create_source_and_package(project_id)
        layer = RacewayLayer.objects.create(
            project_id=project_id,
            source_model_id=source.pk,
            render_package_id=package.pk,
            name="Clash draft",
        )
        family = create_family("WARN-CLASH-LADDER")
        size = create_size(family=family, width_mm=300, depth_mm=100)
        run = create_run(layer=layer, family=family, size=size)
        create_nodes(run, [(0.0, 0.0, 0.0), (2.0, 0.0, 0.0)])
        ModelObject.objects.create(
            source_model=source,
            render_package=package,
            stable_id="ifc-beam-clash",
            source_object_id="Beam-001",
            object_type="IfcBeam",
            tag="B-001",
            bounds={
                "min_x": 0.9,
                "max_x": 1.1,
                "min_y": -0.05,
                "max_y": 0.05,
                "min_z": -0.05,
                "max_z": 0.05,
            },
        )

        warnings = build_layer_warnings(layer)
        clash_warning = next(warning for warning in warnings if warning["code"] == "raceway.warning.model_clash_aabb")

        self.assertEqual(clash_warning["source"], "model_envelope")
        self.assertEqual(clash_warning["object_type"], "segment")
        self.assertEqual(clash_warning["values"]["method"], "aabb")
        self.assertEqual(clash_warning["values"]["object_stable_id"], "ifc-beam-clash")
        self.assertEqual(clash_warning["values"]["object_label"], "B-001")
        self.assertIn("raceway_bounds", clash_warning["values"])
        self.assertNotIn("model_object_id", clash_warning["values"])

    def test_layer_warnings_flag_rough_model_clearance_band(self):
        project_id = "RWY-WARN-CLEARANCE"
        source, package = create_source_and_package(project_id)
        layer = RacewayLayer.objects.create(
            project_id=project_id,
            source_model_id=source.pk,
            render_package_id=package.pk,
            name="Clearance draft",
        )
        family = create_family("WARN-CLEARANCE-LADDER")
        size = create_size(family=family, width_mm=300, depth_mm=100)
        run = create_run(layer=layer, family=family, size=size)
        create_nodes(run, [(0.0, 0.0, 0.0), (2.0, 0.0, 0.0)])
        ModelObject.objects.create(
            source_model=source,
            render_package=package,
            stable_id="ifc-pipe-near",
            source_object_id="Pipe-001",
            object_type="IfcPipeSegment",
            bounds={
                "min_x": 0.9,
                "max_x": 1.1,
                "min_y": 0.21,
                "max_y": 0.25,
                "min_z": -0.05,
                "max_z": 0.05,
            },
        )

        warnings = build_layer_warnings(layer)
        clearance_warning = next(
            warning for warning in warnings if warning["code"] == "raceway.warning.model_clearance_aabb"
        )

        self.assertAlmostEqual(clearance_warning["values"]["clearance_m"], 0.10)
        self.assertLessEqual(clearance_warning["values"]["gap_m"], 0.10)
        self.assertEqual(clearance_warning["values"]["object_stable_id"], "ifc-pipe-near")

    def test_layer_warnings_sort_by_explicit_severity_rank(self):
        layer = RacewayLayer.objects.create(project_id="RWY-WARN-SORT", name="Sort draft")
        family = create_family("WARN-SORT-LADDER")
        size = create_size(family=family)
        run = create_run(layer=layer, family=family, size=size)
        create_nodes(run, [(0.0, 0.0, 0.0), (SHORT_SEGMENT_WARNING_M / 2, 0.0, 0.0)])

        severities = [warning["severity"] for warning in build_layer_warnings(layer)]

        self.assertLess(severities.index("warning"), severities.index("info"))

    def test_layer_warnings_report_when_model_object_scan_is_limited(self):
        project_id = "RWY-WARN-SCAN-LIMIT"
        source, package = create_source_and_package(project_id)
        layer = RacewayLayer.objects.create(
            project_id=project_id,
            source_model_id=source.pk,
            render_package_id=package.pk,
            name="Scan limit draft",
        )
        ModelObject.objects.bulk_create(
            [
                ModelObject(
                    source_model=source,
                    render_package=package,
                    stable_id=f"ifc-object-{index:04d}",
                    bounds={
                        "min_x": index,
                        "max_x": index + 0.1,
                        "min_y": 0.0,
                        "max_y": 0.1,
                        "min_z": 0.0,
                        "max_z": 0.1,
                    },
                )
                for index in range(MODEL_OBJECT_SCAN_LIMIT + 1)
            ]
        )

        warnings = build_layer_warnings(layer)
        limited_warning = next(
            warning for warning in warnings if warning["code"] == "raceway.warning.model_clash_scan_limited"
        )

        self.assertEqual(limited_warning["values"]["scan_limit"], MODEL_OBJECT_SCAN_LIMIT)


class RacewayScheduleProjectionTests(TestCase):
    def test_layer_schedule_splits_segments_and_counts_placeholders(self):
        layer = create_layer(project_id="RWY-SCHEDULE")
        family = create_family("SCHED-LADDER")
        size = create_size(family=family, width_mm=450, depth_mm=100)
        run = create_run(layer=layer, family=family, size=size)
        run.tag = "RWY-SCHED-1"
        run.save()
        create_nodes(run, [(0.0, 0.0, 0.0), (3.0, 0.0, 0.0), (3.0, 4.0, 0.0), (3.0, 4.0, 2.0)])

        schedule = build_layer_schedule(layer)

        self.assertEqual(len(schedule["segments"]), 3)
        self.assertAlmostEqual(schedule["totals"]["length_m"], 9.0)
        self.assertAlmostEqual(schedule["totals"]["horizontal_length_m"], 7.0)
        self.assertAlmostEqual(schedule["totals"]["riser_length_m"], 2.0)
        self.assertEqual(schedule["totals"]["support_placeholders"], 4)
        self.assertEqual(schedule["totals"]["piece_count_estimate"], 3)
        self.assertAlmostEqual(schedule["totals"]["offcut_m_estimate"], 0.0)
        self.assertEqual(schedule["totals"]["plan_bend_count"], 1)
        self.assertEqual(schedule["totals"]["riser_count"], 1)
        self.assertEqual(schedule["fitting_placeholders"]["counts"]["plan_bends"], {"plan_bend_46_90": 1})
        self.assertEqual(schedule["fitting_placeholders"]["counts"]["risers"], {"riser_up": 1})
        run_summary = schedule["runs"][0]
        self.assertEqual(run_summary["run_key"], str(run.key))
        self.assertEqual(run_summary["family_code"], "SCHED-LADDER")
        self.assertEqual(run_summary["size_label"], "450 x 100 mm")
        self.assertEqual(run_summary["standard_length_mm"], 3000)
        self.assertEqual(run_summary["piece_count_estimate"], 3)
        self.assertAlmostEqual(run_summary["offcut_m_estimate"], 0.0)
        self.assertEqual(run_summary["support_span_m"], PLACEHOLDER_SUPPORT_SPAN_M)
        self.assertEqual(run_summary["support_placeholders"], 4)
        bend = schedule["fitting_placeholders"]["plan_bends"][0]
        self.assertEqual(bend["node_key"], str(run.nodes.order_by("sequence")[1].key))
        self.assertEqual(bend["category"], "plan_bend_46_90")
        self.assertAlmostEqual(bend["angle_deg"], 90.0)
        assumption_codes = {assumption["code"] for assumption in schedule["assumptions"]}
        self.assertIn("raceway.schedule.traceability", assumption_codes)
        self.assertIn("raceway.schedule.support_placeholder", assumption_codes)
        self.assertIn("raceway.schedule.standard_length_piece_estimate", assumption_codes)
        self.assertIn("raceway.schedule.junction_placeholder_deferred", assumption_codes)
        self.assertEqual(schedule["project_id"], "RWY-SCHEDULE")
        self.assertEqual(schedule["layer_id"], layer.pk)
        self.assertTrue(schedule["generated_at"])
        self.assertEqual(schedule["graph_warnings"]["total"], 0)
        self.assertEqual(schedule["warning_summary"]["warning"], 0)
        self.assertEqual(schedule["warning_summary"]["info"], 1)
        self.assertEqual(
            schedule["warning_summary"]["by_code"]["raceway.warning.support_span_placeholder_basis"],
            1,
        )

    def test_layer_schedule_groups_by_family_size_and_service(self):
        layer = create_layer(project_id="RWY-SCHEDULE-GROUP")
        family = create_family("SCHED-GROUP-LADDER")
        size = create_size(family=family, width_mm=300, depth_mm=100)
        power_run = create_run(layer=layer, family=family, size=size)
        power_run.tag = "RWY-PWR"
        power_run.service_class = "power"
        power_run.save()
        control_run = create_run(layer=layer, family=family, size=size)
        control_run.tag = "RWY-CTL"
        control_run.service_class = "control"
        control_run.save()
        create_nodes(power_run, [(0.0, 0.0, 0.0), (4.0, 0.0, 0.0)])
        create_nodes(control_run, [(0.0, 1.0, 0.0), (2.0, 1.0, 0.0)])

        schedule = build_layer_schedule(layer)
        groups = {group["service_class"]: group for group in schedule["groups"]}

        self.assertEqual(set(groups), {"power", "control"})
        self.assertAlmostEqual(groups["power"]["length_m"], 4.0)
        self.assertAlmostEqual(groups["control"]["length_m"], 2.0)
        self.assertEqual(groups["power"]["support_placeholders"], 3)
        self.assertEqual(groups["control"]["support_placeholders"], 2)
        self.assertEqual(groups["power"]["piece_count_estimate"], 2)
        self.assertAlmostEqual(groups["power"]["offcut_m_estimate"], 2.0)
        self.assertEqual(groups["control"]["piece_count_estimate"], 1)
        self.assertAlmostEqual(groups["control"]["offcut_m_estimate"], 1.0)


class RacewayFittingProjectionTests(TestCase):
    def test_layer_fitting_projection_derives_plan_bend_and_riser_placeholders(self):
        layer = create_layer(project_id="RWY-FITTINGS")
        family = create_family("FIT-LADDER")
        size = create_size(family=family, width_mm=450, depth_mm=100)
        run = create_run(layer=layer, family=family, size=size)
        run.tag = "RWY-FIT-1"
        run.save()
        create_nodes(run, [(0.0, 0.0, 0.0), (3.0, 0.0, 0.0), (3.0, 4.0, 0.0), (3.0, 4.0, 2.0)])

        projection = build_layer_fitting_projection(layer)
        items_by_kind = {item["kind"]: item for item in projection["items"]}

        self.assertEqual(projection["projection"], "raceway.fittings.v0")
        self.assertEqual(projection["status"], "derived_placeholder")
        self.assertEqual(projection["counts"]["by_kind"]["plan_bend"], 1)
        self.assertEqual(projection["counts"]["by_kind"]["riser"], 1)
        self.assertEqual(projection["counts"]["requires_catalogue_validation"], 2)
        self.assertEqual(items_by_kind["plan_bend"]["category"], "plan_bend_46_90")
        self.assertAlmostEqual(items_by_kind["plan_bend"]["angle_deg"], 90.0)
        self.assertFalse(items_by_kind["plan_bend"]["requires_face_alignment"])
        self.assertEqual(items_by_kind["riser"]["category"], "riser_up")
        self.assertTrue(items_by_kind["riser"]["requires_face_alignment"])
        self.assertEqual(items_by_kind["riser"]["face_alignment"]["status"], "required_not_modelled")
        assumption_codes = {assumption["code"] for assumption in projection["assumptions"]}
        self.assertIn("raceway.fittings.route_as_truth", assumption_codes)
        self.assertIn("raceway.fittings.face_alignment_deferred", assumption_codes)
        self.assertIn("raceway.fittings.tee_cross_deferred", assumption_codes)

    def test_layer_fitting_projection_flags_unequal_size_reducer_candidate_at_connected_node(self):
        layer = create_layer(project_id="RWY-FITTINGS-REDUCER")
        family = create_family("FIT-RED-LADDER")
        small = create_size(family=family, width_mm=300, depth_mm=100)
        large = create_size(family=family, width_mm=600, depth_mm=100)
        small_run = create_run(layer=layer, family=family, size=small)
        small_run.tag = "RWY-SMALL"
        small_run.save()
        large_run = create_run(layer=layer, family=family, size=large)
        large_run.tag = "RWY-LARGE"
        large_run.save()
        create_nodes(small_run, [(0.0, 0.0, 0.0), (3.0, 0.0, 0.0)])
        create_nodes(large_run, [(3.0, 0.0, 0.0), (6.0, 0.0, 0.0)])

        projection = build_layer_fitting_projection(layer)
        reducer = next(item for item in projection["items"] if item["kind"] == "reducer_candidate")

        self.assertEqual(reducer["category"], "width_reducer")
        self.assertEqual(reducer["graph_node_kind"], "junction")
        self.assertEqual({group["width_mm"] for group in reducer["size_groups"]}, {300, 600})
        self.assertEqual({member["run_tag"] for member in reducer["members"]}, {"RWY-SMALL", "RWY-LARGE"})
        self.assertTrue(reducer["requires_face_alignment"])
        self.assertEqual(projection["counts"]["by_kind"]["reducer_candidate"], 1)
        self.assertEqual(projection["graph_summary"]["junction_node_count"], 1)


class RacewayApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="raceway-api-user", password="pw")
        self.project = create_project("RWY-API")
        assign_project(self.user, self.project)
        self.source, self.package = create_source_and_package(self.project.proj_id)
        self.family = create_family("API-LADDER")
        self.size = create_size(family=self.family, width_mm=300, depth_mm=100)
        self.client.force_login(self.user)

    def test_layer_create_and_list_validate_project_and_package_context(self):
        response = self.client.post(
            reverse("raceway:layer_collection", args=[self.project.proj_id]),
            data=json_body(
                {
                    "name": "AG tray layer",
                    "description": "First raceway draft",
                    "source_model_id": self.source.pk,
                    "render_package_id": self.package.pk,
                    "metadata": {"area": "A1"},
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        layer_payload = response.json()["layer"]
        self.assertEqual(layer_payload["project_id"], self.project.proj_id)
        self.assertEqual(layer_payload["source_model_id"], self.source.pk)
        self.assertEqual(layer_payload["render_package_id"], self.package.pk)
        self.assertEqual(layer_payload["created_by_id"], self.user.pk)
        self.assertNotIn("storage_key", layer_payload)

        list_response = self.client.get(reverse("raceway:layer_collection", args=[self.project.proj_id]))

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.json()["layers"]), 1)
        self.assertEqual(list_response.json()["layers"][0]["name"], "AG tray layer")

    def test_layer_create_rejects_inaccessible_project(self):
        other_user = get_user_model().objects.create_user(username="raceway-api-other", password="pw")
        self.client.force_login(other_user)

        response = self.client.post(
            reverse("raceway:layer_collection", args=[self.project.proj_id]),
            data=json_body({"name": "Blocked"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(RacewayLayer.objects.filter(name="Blocked").exists())

    def test_layer_create_rejects_inaccessible_source_model(self):
        other_project = create_project("RWY-API-HIDDEN")
        hidden_source, _hidden_package = create_source_and_package(other_project.proj_id)

        response = self.client.post(
            reverse("raceway:layer_collection", args=[self.project.proj_id]),
            data=json_body({"name": "Bad source", "source_model_id": hidden_source.pk}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("source_model_id", response.json()["errors"])

    def test_layer_graph_endpoint_returns_project_scoped_projection(self):
        layer = create_layer(project_id=self.project.proj_id)
        run = create_run(layer=layer, family=self.family, size=self.size)
        create_nodes(run, [(0.0, 0.0, 0.0), (5.0, 0.0, 0.0), (5.0, 3.0, 0.0)])

        response = self.client.get(reverse("raceway:layer_graph", args=[layer.pk]))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["layer"]["project_id"], self.project.proj_id)
        self.assertEqual(payload["graph"]["tolerance_m"], GRAPH_NODE_TOLERANCE_M)
        self.assertEqual(len(payload["graph"]["edges"]), 2)
        self.assertIn("bend", {node["derived_kind"] for node in payload["graph"]["nodes"]})

        other_user = get_user_model().objects.create_user(username="raceway-graph-blocked", password="pw")
        self.client.force_login(other_user)
        blocked_response = self.client.get(reverse("raceway:layer_graph", args=[layer.pk]))

        self.assertEqual(blocked_response.status_code, 403)

    def test_layer_schedule_endpoint_returns_project_scoped_quantities(self):
        layer = create_layer(project_id=self.project.proj_id)
        run = create_run(layer=layer, family=self.family, size=self.size)
        run.tag = "RWY-API-SCHED"
        run.save()
        create_nodes(run, [(0.0, 0.0, 0.0), (6.0, 0.0, 0.0), (6.0, 2.0, 0.0)])

        response = self.client.get(reverse("raceway:layer_schedule", args=[layer.pk]))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["layer"]["project_id"], self.project.proj_id)
        self.assertAlmostEqual(payload["schedule"]["totals"]["length_m"], 8.0)
        self.assertEqual(payload["schedule"]["totals"]["plan_bend_count"], 1)
        self.assertEqual(payload["schedule"]["totals"]["piece_count_estimate"], 3)
        self.assertAlmostEqual(payload["schedule"]["totals"]["offcut_m_estimate"], 1.0)
        self.assertEqual(payload["schedule"]["groups"][0]["family_code"], "API-LADDER")
        self.assertEqual(payload["schedule"]["project_id"], self.project.proj_id)
        self.assertIn("raceway.schedule.support_placeholder", {item["code"] for item in payload["schedule"]["assumptions"]})

        other_user = get_user_model().objects.create_user(username="raceway-schedule-blocked", password="pw")
        self.client.force_login(other_user)
        blocked_response = self.client.get(reverse("raceway:layer_schedule", args=[layer.pk]))

        self.assertEqual(blocked_response.status_code, 403)

    def test_layer_fittings_endpoint_returns_project_scoped_projection(self):
        layer = create_layer(project_id=self.project.proj_id)
        run = create_run(layer=layer, family=self.family, size=self.size)
        run.tag = "RWY-API-FIT"
        run.save()
        create_nodes(run, [(0.0, 0.0, 0.0), (4.0, 0.0, 0.0), (4.0, 2.0, 0.0), (4.0, 2.0, 1.0)])

        response = self.client.get(reverse("raceway:layer_fittings", args=[layer.pk]))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["layer"]["project_id"], self.project.proj_id)
        self.assertEqual(payload["fittings"]["projection"], "raceway.fittings.v0")
        self.assertEqual(payload["fittings"]["counts"]["by_kind"]["plan_bend"], 1)
        self.assertEqual(payload["fittings"]["counts"]["by_kind"]["riser"], 1)
        self.assertEqual(payload["fittings"]["project_id"], self.project.proj_id)

        other_user = get_user_model().objects.create_user(username="raceway-fittings-blocked", password="pw")
        self.client.force_login(other_user)
        blocked_response = self.client.get(reverse("raceway:layer_fittings", args=[layer.pk]))

        self.assertEqual(blocked_response.status_code, 403)

    def test_layer_schedule_csv_endpoint_uses_same_schedule_payload_shape(self):
        layer = create_layer(project_id=self.project.proj_id)
        run = create_run(layer=layer, family=self.family, size=self.size)
        run.tag = "RWY-CSV"
        run.save()
        create_nodes(run, [(0.0, 0.0, 0.0), (3.0, 0.0, 0.0), (3.0, 3.0, 0.0)])

        response = self.client.get(reverse("raceway:layer_schedule_csv", args=[layer.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("raceway-layer-", response["Content-Disposition"])
        csv_text = response.content.decode("utf-8")
        self.assertIn("Raceway Schedule", csv_text)
        self.assertIn("Assumptions", csv_text)
        self.assertIn("Totals", csv_text)
        self.assertIn("Fitting Placeholders", csv_text)
        self.assertIn("Validation Warnings", csv_text)
        self.assertIn("Warning Summary", csv_text)
        self.assertIn("Graph Warning Counts", csv_text)
        self.assertIn("Grouped Quantities", csv_text)
        self.assertIn("RWY-CSV", csv_text)
        self.assertIn("Piece Estimate", csv_text)

    def test_run_create_update_delete_and_node_replace_workflow(self):
        layer = create_layer(project_id=self.project.proj_id)
        layer.source_model_id = self.source.pk
        layer.render_package_id = self.package.pk
        layer.save()

        run_response = self.client.post(
            reverse("raceway:layer_runs", args=[layer.pk]),
            data=json_body(
                {
                    "tag": "RWY-101",
                    "family_id": self.family.pk,
                    "size_id": self.size.pk,
                    "service_class": "power",
                    "elevation_m": 106.5,
                    "metadata": {
                        "route_basis": "manual",
                        "orientation": {"preset": "roll_right"},
                    },
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(run_response.status_code, 201)
        run_payload = run_response.json()["run"]
        self.assertEqual(run_payload["coordinate_frame"], SOURCE_COORDINATE_FRAME)
        self.assertTrue(run_payload["key"])
        self.assertEqual(run_payload["family"]["code"], "API-LADDER")
        self.assertEqual(run_payload["family"]["kind"], "ladder")
        self.assertEqual(run_payload["size"]["width_mm"], 300)
        self.assertEqual(run_payload["size"]["depth_mm"], 100)
        self.assertEqual(run_payload["metadata"]["orientation"]["schema"], "raceway.orientation.v0")
        self.assertEqual(run_payload["metadata"]["orientation"]["preset"], "roll_right")
        self.assertEqual(run_payload["metadata"]["orientation"]["quarter_turns"], 1)
        run_id = run_payload["id"]

        node_response = self.client.put(
            reverse("raceway:run_nodes", args=[run_id]),
            data=json_body(
                {
                    "nodes": [
                        {
                            "sequence": 0,
                            "node_kind": "endpoint",
                            "source_x_m": 1000.0,
                            "source_y_m": 2000.0,
                            "source_z_m": 106.5,
                            "anchor": {
                                "owner_module": "raceway",
                                "anchor_kind": "model_object",
                                "source_model_id": self.source.pk,
                                "render_package_id": self.package.pk,
                                "stable_id": "ifc:start",
                                "label": "Start support",
                            },
                        },
                        {
                            "sequence": 1,
                            "node_kind": "bend",
                            "source_x_m": 1010.0,
                            "source_y_m": 2000.0,
                            "source_z_m": 106.5,
                        },
                    ],
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(node_response.status_code, 200)
        nodes = node_response.json()["nodes"]
        self.assertEqual(len(nodes), 2)
        self.assertEqual(nodes[0]["sequence"], 0)
        self.assertNotIn("render_cache", nodes[0])
        self.assertEqual(nodes[0]["anchor"]["stable_id"], "ifc:start")
        self.assertNotIn("feature_id", nodes[0]["anchor"])

        detail_response = self.client.get(reverse("raceway:run_detail", args=[run_id]))
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(len(detail_response.json()["run"]["nodes"]), 2)

        collection_response = self.client.get(f"{reverse('raceway:layer_runs', args=[layer.pk])}?include_nodes=1")
        self.assertEqual(collection_response.status_code, 200)
        self.assertEqual(len(collection_response.json()["runs"][0]["nodes"]), 2)
        self.assertEqual(collection_response.json()["runs"][0]["size"]["width_mm"], 300)

        patch_response = self.client.patch(
            reverse("raceway:run_detail", args=[run_id]),
            data=json_body({"tag": "RWY-101A", "status": "committed"}),
            content_type="application/json",
        )
        self.assertEqual(patch_response.status_code, 200)
        self.assertEqual(patch_response.json()["run"]["tag"], "RWY-101A")
        self.assertEqual(patch_response.json()["run"]["status"], "committed")

        delete_response = self.client.delete(reverse("raceway:run_detail", args=[run_id]))
        self.assertEqual(delete_response.status_code, 200)
        self.assertFalse(RacewayRun.objects.filter(pk=run_id).exists())

    def test_run_rejects_unsupported_orientation_preset(self):
        layer = create_layer(project_id=self.project.proj_id)
        response = self.client.post(
            reverse("raceway:layer_runs", args=[layer.pk]),
            data=json_body(
                {
                    "tag": "RWY-BAD-ORIENT",
                    "family_id": self.family.pk,
                    "size_id": self.size.pk,
                    "service_class": "power",
                    "metadata": {"orientation": {"preset": "diagonal_magic"}},
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("metadata.orientation.preset", response.json()["errors"])

    def test_run_create_rejects_family_size_mismatch(self):
        layer = create_layer(project_id=self.project.proj_id)
        layer.source_model_id = self.source.pk
        layer.render_package_id = self.package.pk
        layer.save()
        other_family = create_family("API-OTHER")
        other_size = create_size(family=other_family)

        response = self.client.post(
            reverse("raceway:layer_runs", args=[layer.pk]),
            data=json_body({"family_id": self.family.pk, "size_id": other_size.pk}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("size", response.json()["errors"])

    def test_node_replace_rejects_invalid_coordinates_without_deleting_existing_nodes(self):
        run = create_run(layer=create_layer(project_id=self.project.proj_id), family=self.family, size=self.size)
        RacewayNode.objects.create(run=run, sequence=0, source_x_m=1.0, source_y_m=2.0, source_z_m=3.0)

        response = self.client.put(
            reverse("raceway:run_nodes", args=[run.pk]),
            data=json_body({"nodes": [{"sequence": 0, "source_x_m": "not-a-number", "source_y_m": 0, "source_z_m": 0}]}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(list(run.nodes.values_list("source_x_m", flat=True)), [1.0])

    def test_node_replace_rejects_unstable_anchor_payload_without_deleting_existing_nodes(self):
        layer = create_layer(project_id=self.project.proj_id)
        layer.source_model_id = self.source.pk
        layer.render_package_id = self.package.pk
        layer.save()
        run = create_run(layer=layer, family=self.family, size=self.size)
        run.source_model_id = self.source.pk
        run.render_package_id = self.package.pk
        run.save()
        RacewayNode.objects.create(run=run, sequence=0, source_x_m=1.0, source_y_m=2.0, source_z_m=3.0)

        response = self.client.put(
            reverse("raceway:run_nodes", args=[run.pk]),
            data=json_body(
                {
                    "nodes": [
                        {
                            "sequence": 0,
                            "source_x_m": 1.0,
                            "source_y_m": 2.0,
                            "source_z_m": 3.0,
                            "anchor": {
                                "owner_module": "raceway",
                                "anchor_kind": "model_object",
                                "source_model_id": self.source.pk,
                                "stable_id": "ifc:beam-001",
                                "feature_id": 77,
                            },
                        },
                        {
                            "sequence": 1,
                            "source_x_m": 2.0,
                            "source_y_m": 2.0,
                            "source_z_m": 3.0,
                        },
                    ],
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("anchor", response.json()["errors"])
        self.assertEqual(list(run.nodes.values_list("source_x_m", flat=True)), [1.0])

    def test_node_replace_preserves_existing_node_keys_when_client_sends_them(self):
        run = create_run(layer=create_layer(project_id=self.project.proj_id), family=self.family, size=self.size)
        first = RacewayNode.objects.create(run=run, sequence=0, source_x_m=1.0, source_y_m=0.0, source_z_m=0.0)
        second = RacewayNode.objects.create(run=run, sequence=1, source_x_m=2.0, source_y_m=0.0, source_z_m=0.0)

        response = self.client.put(
            reverse("raceway:run_nodes", args=[run.pk]),
            data=json_body(
                {
                    "nodes": [
                        {
                            "key": str(second.key),
                            "sequence": 0,
                            "source_x_m": 2.0,
                            "source_y_m": 1.0,
                            "source_z_m": 0.0,
                        },
                        {
                            "key": str(first.key),
                            "sequence": 1,
                            "source_x_m": 1.0,
                            "source_y_m": 1.0,
                            "source_z_m": 0.0,
                        },
                        {
                            "sequence": 2,
                            "source_x_m": 3.0,
                            "source_y_m": 1.0,
                            "source_z_m": 0.0,
                        },
                    ],
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        returned_keys = [node["key"] for node in response.json()["nodes"]]
        self.assertEqual(returned_keys[:2], [str(second.key), str(first.key)])
        self.assertNotIn(returned_keys[2], {str(first.key), str(second.key)})
        self.assertEqual(
            list(run.nodes.order_by("sequence").values_list("key", flat=True))[:2],
            [second.key, first.key],
        )

    def test_node_replace_rejects_node_key_from_another_run_without_deleting_existing_nodes(self):
        run = create_run(layer=create_layer(project_id=self.project.proj_id), family=self.family, size=self.size)
        existing = RacewayNode.objects.create(run=run, sequence=0, source_x_m=1.0, source_y_m=0.0, source_z_m=0.0)
        other_run = create_run(layer=run.layer, family=self.family, size=self.size)
        foreign = RacewayNode.objects.create(run=other_run, sequence=0, source_x_m=9.0, source_y_m=0.0, source_z_m=0.0)

        response = self.client.put(
            reverse("raceway:run_nodes", args=[run.pk]),
            data=json_body(
                {
                    "nodes": [
                        {
                            "key": str(foreign.key),
                            "sequence": 0,
                            "source_x_m": 2.0,
                            "source_y_m": 0.0,
                            "source_z_m": 0.0,
                        },
                        {
                            "sequence": 1,
                            "source_x_m": 3.0,
                            "source_y_m": 0.0,
                            "source_z_m": 0.0,
                        },
                    ],
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("nodes", response.json()["errors"])
        self.assertEqual(list(run.nodes.values_list("key", flat=True)), [existing.key])

    def test_node_replace_requires_two_ordered_nodes_without_deleting_existing_nodes(self):
        run = create_run(layer=create_layer(project_id=self.project.proj_id), family=self.family, size=self.size)
        RacewayNode.objects.create(run=run, sequence=0, source_x_m=1.0, source_y_m=2.0, source_z_m=3.0)

        response = self.client.put(
            reverse("raceway:run_nodes", args=[run.pk]),
            data=json_body({"nodes": [{"sequence": 0, "source_x_m": 2.0, "source_y_m": 3.0, "source_z_m": 4.0}]}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("nodes", response.json()["errors"])
        self.assertEqual(list(run.nodes.values_list("source_x_m", flat=True)), [1.0])

    def test_layer_delete_removes_owned_layer(self):
        layer = create_layer(project_id=self.project.proj_id)

        response = self.client.delete(reverse("raceway:layer_detail", args=[layer.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(RacewayLayer.objects.filter(pk=layer.pk).exists())


class RacewayStaticAssetTests(TestCase):
    def test_raceway_overlay_registers_external_viewer_layer(self):
        script_path = os.path.join(
            os.path.dirname(__file__),
            "static",
            "raceway",
            "js",
            "raceway_overlay.js",
        )

        with open(script_path, encoding="utf-8") as script:
            content = script.read()

        self.assertIn("RACEWAY_LAYER_ID = 'raceway-overlay'", content)
        self.assertIn("window.plant3dViewerLayers", content)
        self.assertIn("registry.register", content)
        self.assertIn("owner: 'raceway'", content)
        self.assertIn("createGroup: true", content)
        self.assertIn("plant3dviewer:layers-ready", content)
        self.assertIn("plant3dviewer:runtime-ready", content)
        self.assertIn("Raceway Draft", content)
        self.assertIn("racewayFamilySelect", content)
        self.assertIn("racewaySizeSelect", content)
        self.assertIn("racewayServiceSelect", content)
        self.assertIn("racewayOrientationSelect", content)
        self.assertIn("racewayElevationInput", content)
        self.assertIn("racewayOrthoInput", content)
        self.assertIn("const ORIENTATION_SCHEMA = 'raceway.orientation.v0'", content)
        self.assertIn("function normalizedOrientation", content)
        self.assertIn("function rollBasisAroundTangent", content)
        self.assertIn("orientation: runOrientation(run)", content)
        self.assertIn("if (node.key) payload.key = node.key", content)
        self.assertIn("racewaySegmentDirectionSelect", content)
        self.assertIn("racewaySegmentLengthInput", content)
        self.assertIn("CATALOG_URL = '/raceway/catalog/'", content)
        self.assertIn("function loadCatalog", content)
        self.assertIn("function loadSavedRaceways", content)
        self.assertIn("function reloadSavedRaceways", content)
        self.assertIn("function saveDrafts", content)
        self.assertIn("function deleteActiveRun", content)
        self.assertIn("function racewayMeasurementSnapObjects", content)
        self.assertIn("getMeasurementSnapObjects: racewayMeasurementSnapObjects", content)
        self.assertIn("measurementSnapTarget", content)
        self.assertIn("function loadGraphProjection", content)
        self.assertIn("function graphWarningsHtml", content)
        self.assertIn("function loadScheduleProjection", content)
        self.assertIn("function scheduleWarnings", content)
        self.assertIn("function selectScheduleWarning", content)
        self.assertIn("function focusScheduleWarningTarget", content)
        self.assertIn("function racewayNoticeBadgeCount", content)
        self.assertIn("racewayWarningBadge", content)
        self.assertIn("function loadFittingProjection", content)
        self.assertIn("function fittingSummaryHtml", content)
        self.assertIn("function scheduleSummaryHtml", content)
        self.assertIn("function scheduleWarningRowsHtml", content)
        self.assertIn("warning-segment-highlight", content)
        self.assertIn("function openScheduleCsv", content)
        self.assertIn("function localWarningsHtml", content)
        self.assertIn("function validationWarningLabel", content)
        self.assertIn("TELEMETRY_EVENTS_URL", content)
        self.assertIn("function queueTelemetryEvent", content)
        self.assertIn("function flushTelemetryEvents", content)
        self.assertIn("function recordVisibleWarningTelemetry", content)
        self.assertIn("function recordOrthoTelemetry", content)
        self.assertIn("unresolved_at_save", content)
        self.assertIn("raceway.ortho.axis_lock", content)
        self.assertIn("TELEMETRY_FORBIDDEN_ID_KEYS", content)
        self.assertIn("function sanitizeAnchorForPersistence", content)
        self.assertIn("function attachSelectedModelToNode", content)
        self.assertIn("function clearSelectedNodeAnchor", content)
        self.assertIn("function selectRacewayNodeFromEvent", content)
        self.assertIn("function connectSelectedNodeFromEvent", content)
        self.assertIn("function beginConnectNode", content)
        self.assertIn("function continueRun", content)
        self.assertIn("function undoRacewayEdit", content)
        self.assertIn("function redoRacewayEdit", content)
        self.assertIn("function racewayShortcutActionForEvent", content)
        self.assertIn("function racewayShortcutAvailableForAction", content)
        self.assertIn("function handleRacewayKeyboardShortcut", content)
        self.assertIn("function orthoAdjustedPoint", content)
        self.assertIn("function addTypedSegment", content)
        self.assertIn("function segmentDirectionOptionsHtml", content)
        self.assertIn("function riserCount", content)
        self.assertIn("function addRiserPlaceholder", content)
        self.assertIn("data-raceway-action=\"continue-run\"", content)
        self.assertIn("data-raceway-action=\"redo\"", content)
        self.assertIn("data-raceway-action=\"add-segment\"", content)
        self.assertIn("data-raceway-action=\"select-node-mode\"", content)
        self.assertIn("data-raceway-action=\"connect-node\"", content)
        self.assertIn("data-raceway-action=\"anchor-node\"", content)
        self.assertIn("data-raceway-action=\"clear-anchor\"", content)
        self.assertIn("data-raceway-action=\"save\"", content)
        self.assertIn("data-raceway-action=\"reload\"", content)
        self.assertIn("data-raceway-action=\"refresh-graph\"", content)
        self.assertIn("data-raceway-action=\"refresh-schedule\"", content)
        self.assertIn("data-raceway-action=\"refresh-fittings\"", content)
        self.assertIn("data-raceway-action=\"select-warning\"", content)
        self.assertIn("data-raceway-action=\"open-schedule-csv\"", content)
        self.assertIn("data-raceway-action=\"delete-run\"", content)
        self.assertIn("data-raceway-action=\"toggle-surfaces\"", content)
        self.assertIn("racewayGraphWarnings", content)
        self.assertIn("racewayScheduleSummary", content)
        self.assertIn("registerInteraction", content)
        self.assertIn("function beginRun", content)
        self.assertIn("function finishRun", content)
        self.assertIn("function addNodeFromEvent", content)
        self.assertIn("function moveSelectedNodeFromEvent", content)
        self.assertIn("function deleteSelectedNode", content)
        self.assertIn("document.addEventListener('keydown', handleRacewayKeyboardShortcut)", content)
        self.assertIn("Ctrl+Z", content)
        self.assertIn("Ctrl+Shift+Z", content)
        self.assertIn("Connect Node", content)
        self.assertIn("Refresh Graph", content)
        self.assertIn("Refresh Schedule", content)
        self.assertIn("toggle-ortho", content)
        self.assertIn("Ortho drawing assist", content)
        self.assertIn("pointOnSourceElevationFromViewerEvent", content)
        self.assertIn("function renderTrayPreview", content)
        self.assertIn("function addRunProxyFaceMesh", content)
        self.assertIn("function addSegmentProxyFaces", content)
        self.assertIn("function addProxyQuad", content)
        self.assertIn("function addSegmentPreview", content)
        self.assertIn("function addBendPlaceholder", content)
        self.assertIn("function sourceFrameOffsetPoint", content)
        self.assertIn("function segmentCornerPoints", content)
        self.assertNotIn("function applyRunElevation", content)
        self.assertIn("'side-rail'", content)
        self.assertIn("'solid-3-plane-proxy'", content)
        self.assertIn("'rung'", content)
        self.assertIn("'node-hit-target'", content)
        self.assertIn("PROXY_BOTTOM_SHADE", content)
        self.assertIn("PROXY_SIDE_SHADE", content)
        self.assertIn("vertexColors: true", content)
        self.assertIn("showProxyFaces", content)
        self.assertIn("if (state.showProxyFaces) addRunProxyFaceMesh", content)
        self.assertIn("screenScaledObjects: true", content)
        self.assertIn("NODE_HANDLE_SCREEN_PX", content)
        self.assertIn("function updateRacewayScreenScale", content)
        self.assertIn("raceway-validation-warning", content)
        self.assertIn("'riser-placeholder'", content)
        self.assertIn("'bend-placeholder'", content)
        self.assertIn("Shift+V", content)
        self.assertLess(content.index('id="racewayInspector"'), content.index('id="racewaySummary"'))
