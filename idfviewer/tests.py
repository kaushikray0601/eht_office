import json
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.test import SimpleTestCase, TestCase

from eht.models import ProjectData

from .analysis_utils import nearest_structure_report
from .ifc_parser import _normalize_ifc_scene, parse_multiple_ifc_uploads
from .models import EHTDesignElement, IDFComponent, IDFFile, IDFFileSaveEvent, ProjectAttributeMapping
from .parser import _collect_candidate_records, _filter_scene, _normalize_points, parse_multiple_idf_texts
from .pcf_parser import _component_to_scene_items, _normalize_scene as _normalize_pcf_scene
from .pcf_parser import _parse_document, _strip_internal as _strip_pcf_internal
from .services import build_scene_from_saved_file
from .views import analyze_nearest_structure_view, detect_pipeline_format


def _parse_scene(text):
    scene = _collect_candidate_records(text, "sample.idf")
    scene = _filter_scene(scene)
    return _normalize_points(scene)


def _parse_pcf_scene(text):
    file_meta, components, materials = _parse_document(text)
    scene = {
        "pipes": [],
        "fittings": [],
        "welds": [],
        "supports": [],
        "markers": [],
        "stats": {"total_lines": len(text.splitlines())},
    }
    next_uid = 1
    for component in components:
        scene_items, next_uid = _component_to_scene_items(next_uid, component, file_meta, materials, "sample.pcf")
        for bucket, scene_item in scene_items:
            scene[bucket].append(scene_item)
    scene = _filter_scene(scene)
    scene["stats"]["source_format"] = "PCF"
    scene = _normalize_pcf_scene(scene)
    return _strip_pcf_internal(scene)


class ParserRegressionTests(SimpleTestCase):
    def test_pipeline_ref_is_inherited_by_following_geometry_only(self):
        scene = _parse_scene(
            """
            100 2000 3000 4000 3000 3000 4000,      ,       0 ,    ,      0  1001
            -39 PREV
            -30 LINE-ABC-
            -1 01
            300 0 0 0 0 0 0
            -16 SHOULD NOT ATTACH
            100 4000 5000 6000 5000 5000 6000,      ,       0 ,    ,      0  1001
            -39 NEXT/12
            -1 34
            """
        )

        first_pipe, second_pipe = scene["pipes"]
        self.assertEqual(scene["stats"]["coordinate_unit"], "MM")
        self.assertEqual(scene["stats"]["coordinate_scale_to_m"], 0.001)
        self.assertEqual(scene["stats"]["unit_confidence"], "assumed")
        self.assertEqual(first_pipe["properties"]["pipeline_ref"], "")
        self.assertEqual(second_pipe["properties"]["pipeline_ref"], "LINE-ABC-01")
        self.assertEqual(first_pipe["properties"]["component_ref"], "PREV")
        self.assertEqual(second_pipe["properties"]["component_ref"], "NEXT/1234")

    def test_record_90_with_origin_endpoint_is_filtered_out(self):
        scene = _parse_scene(
            """
            -30 LINE-01
            90 7000 8000 9000 0 0 0 20 22,      , 2000000 ,IDFL,      0  3402
            90 7000 8000 9000 7100 8100 9100 50 9,      , 2000000 ,RP  ,      0  3002
            """
        )

        self.assertEqual(len(scene["fittings"]), 1)
        self.assertEqual(scene["fittings"][0]["properties"]["record_id"], 90)
        self.assertEqual(scene["fittings"][0]["properties"]["pipeline_ref"], "LINE-01")

    def test_pcf_parser_maps_pipeline_metadata_and_support_details(self):
        scene = _parse_pcf_scene(
            """
            UNITS-CO-ORDS         MM
            PIPELINE-REFERENCE   A09-01-LS0051-01
                PIPING-SPEC   13470
                INSULATION-SPEC   E  60 mm
                TRACING-SPEC   ELECTRIC
                ATTRIBUTE63   559-0051-LS-2"-13470-E
                ATTRIBUTE72   WATER
            PIPE
                COMPONENT-IDENTIFIER    4
                END-POINT    5474674.800    10209900.200    102650.000     2
                END-POINT    5474774.800    10209900.200    102650.000     2
                MATERIAL-IDENTIFIER 4
                CUT-PIECE-LENGTH    100.00
                TRACING ON
            SUPPORT
                CO-ORDS    5474598.800    10211995.000    102650.000     2
                SUPPORT-DIRECTION    DOWN
                SKEY    01HG
                MATERIAL-IDENTIFIER 10
                SUPPORT-TYPE    Pipe Support
                NAME    PFHSPA_SY_MT1_B_1-01-1024
                MESSAGE
                TEXT    MT1-B-1-220-380
                TEXT    PS-A0901LS0051-004
            FLOW-ARROW
                CO-ORDS    5474598.800    10211442.401    102650.000
                FLOW 2
                SKEY FLOW
            MATERIALS
            MATERIAL-IDENTIFIER    4
                ITEM-CODE PIPM0005660
                DESCRIPTION    2" Sch10S, Pipe BE ASME B36.19M smls ASTM A312 GR TP316/316L dual cert
            MATERIAL-IDENTIFIER    10
                ITEM-CODE MT1-B-1-220-380
                DESCRIPTION    MT1 - MINOR TEE POST
            """
        )

        self.assertEqual(scene["stats"]["source_format"], "PCF")
        self.assertEqual(scene["stats"]["coordinate_unit"], "MM")
        self.assertEqual(scene["stats"]["coordinate_scale_to_m"], 0.001)
        self.assertEqual(scene["stats"]["unit_confidence"], "declared")
        self.assertEqual(len(scene["pipes"]), 1)
        self.assertEqual(len(scene["supports"]), 1)
        self.assertEqual(len(scene["markers"]), 1)

        pipe_props = scene["pipes"][0]["properties"]
        self.assertEqual(pipe_props["source_format"], "PCF")
        self.assertEqual(pipe_props["pipeline_ref"], "A09-01-LS0051-01")
        self.assertEqual(pipe_props["piping_spec"], "13470")
        self.assertEqual(pipe_props["tracing_spec"], "ELECTRIC")
        self.assertTrue(pipe_props["tracing_on"])
        self.assertEqual(pipe_props["item_code"], "PIPM0005660")
        self.assertEqual(pipe_props["pipeline_metadata"]["ATTRIBUTE63"], '559-0051-LS-2"-13470-E')
        self.assertEqual(pipe_props["pipeline_metadata"]["ATTRIBUTE72"], "WATER")

        support_props = scene["supports"][0]["properties"]
        self.assertEqual(support_props["support_type"], "Pipe Support")
        self.assertEqual(support_props["support_direction"], "DOWN")
        self.assertEqual(support_props["support_code"], "MT1-B-1-220-380 | PS-A0901LS0051-004")

        marker_props = scene["markers"][0]["properties"]
        self.assertEqual(marker_props["inline_code"], "FLOW")
        self.assertEqual(marker_props["flow_value"], "2")

    def test_pcf_tee_creates_main_run_and_branch_geometry(self):
        scene = _parse_pcf_scene(
            """
            PIPELINE-REFERENCE   A09-01-LS0051-01
            TEE
                COMPONENT-IDENTIFIER    18
                END-POINT    5474598.800    10212525.601    102650.000     2    BW
                END-POINT    5474598.800    10212397.601    102650.000     2    BW
                CENTRE-POINT    5474598.800    10212461.601    102650.000
                BRANCH1-POINT    5474662.800    10212461.601    102650.000     2    BW
                SKEY    TE**
                MATERIAL-IDENTIFIER 16
            MATERIALS
            MATERIAL-IDENTIFIER    16
                ITEM-CODE TEWE0004723
                DESCRIPTION    2" Sch10S, Tee equal BW ASME B16.9 smls ASTM A403 GR WP316/316L-S
            """
        )

        self.assertEqual(len(scene["fittings"]), 2)
        roles = sorted(item["properties"].get("geometry_role") for item in scene["fittings"])
        self.assertEqual(roles, ["branch", "main_run"])
        self.assertTrue(any("branch1_point" in item["properties"] for item in scene["fittings"]))

    def test_detect_pipeline_format_recognizes_ifc(self):
        self.assertEqual(
            detect_pipeline_format("sample.ifc", "ISO-10303-21;\nFILE_SCHEMA(('IFC2X3'));"),
            "IFC",
        )

    def test_ifc_scene_normalization_builds_mesh_payload_and_disables_save(self):
        scene = {
            "pipes": [],
            "fittings": [],
            "welds": [],
            "supports": [],
            "markers": [],
            "meshes": [
                {
                    "uid": 1,
                    "record_id": 9100,
                    "kind": "IfcColumn",
                    "mesh_vertices_raw": [
                        [1000.0, 2000.0, 3000.0],
                        [2000.0, 2000.0, 3000.0],
                        [2000.0, 3000.0, 3000.0],
                    ],
                    "mesh_indices_raw": [0, 1, 2],
                    "properties": {
                        "source_format": "IFC",
                        "display_color": [0.3, 0.4, 0.5],
                    },
                }
            ],
            "stats": {"source_format": "IFC", "source_label": "IFC Scene"},
        }

        normalized = _normalize_ifc_scene(scene)

        self.assertEqual(normalized["stats"]["mesh_count"], 1)
        self.assertFalse(normalized["stats"]["save_supported"])
        self.assertEqual(normalized["stats"]["scale_factor"], 1.0)
        self.assertEqual(normalized["stats"]["coordinate_unit"], "M")
        self.assertEqual(normalized["stats"]["coordinate_scale_to_m"], 1.0)
        self.assertEqual(normalized["stats"]["unit_confidence"], "assumed")
        self.assertEqual(normalized["meshes"][0]["mesh"]["indices"], [0, 1, 2])
        self.assertEqual(len(normalized["meshes"][0]["mesh"]["positions"]), 9)

    def test_sample_ifc_parses_with_expected_meshes_and_metadata(self):
        sample_path = Path("/home/kr/mydev/eht_office/eht/4001-A51A-01.ifc")
        if not sample_path.exists():
            self.skipTest("Sample IFC file is not available in this workspace.")
        raw = sample_path.read_bytes()

        scene = parse_multiple_ifc_uploads([("4001-A51A-01.ifc", raw)], None)

        self.assertEqual(scene["stats"]["source_format"], "IFC")
        self.assertEqual(scene["stats"]["mesh_count"], 2)
        self.assertEqual(scene["stats"]["scale_factor"], 1.0)
        first = scene["meshes"][0]["properties"]
        self.assertEqual(first["ifc_class"], "IfcColumn")
        self.assertEqual(first["component_ref"], "H467")
        self.assertTrue(first["materials"])

    def test_nearest_structure_report_matches_pipeline_line_to_ifc_bounds(self):
        pipeline_scene = {
            "pipes": [
                {
                    "uid": 1,
                    "record_id": 100,
                    "kind": "Pipe",
                    "properties": {
                        "filename": "sample.idf",
                        "pipeline_ref": "LINE-100",
                        "raw_start": [1000.0, 1000.0, 1000.0],
                        "raw_end": [3000.0, 1000.0, 1000.0],
                    },
                }
            ],
            "fittings": [],
            "welds": [],
            "supports": [],
            "markers": [],
            "stats": {"source_format": "IDF"},
        }
        ifc_scene = {
            "meshes": [
                {
                    "uid": 10,
                    "properties": {
                        "ifc_class": "IfcColumn",
                        "component_ref": "COL-A",
                        "name": "Column A",
                        "storey_name": "L1",
                        "material_names": ["STEEL"],
                        "filename": "sample.ifc",
                        "raw_bounds": {
                            "min_x": 3.2,
                            "max_x": 3.4,
                            "min_y": 0.8,
                            "max_y": 1.2,
                            "min_z": 0.8,
                            "max_z": 1.2,
                        },
                    },
                }
            ]
        }

        report = nearest_structure_report(pipeline_scene, ifc_scene)

        self.assertEqual(report["summary"]["line_count"], 1)
        self.assertEqual(report["summary"]["ifc_object_count"], 1)
        self.assertEqual(len(report["results"]), 1)
        row = report["results"][0]
        self.assertEqual(row["line_label"], "LINE-100")
        self.assertEqual(row["component_ref"], "COL-A")
        self.assertAlmostEqual(row["distance_m"], 0.2, places=6)

    def test_nearest_structure_report_warns_when_coordinate_frames_are_far_apart(self):
        pipeline_scene = {
            "pipes": [
                {
                    "uid": 1,
                    "record_id": 100,
                    "kind": "Pipe",
                    "properties": {
                        "filename": "sample.idf",
                        "pipeline_ref": "LINE-200",
                        "raw_start": [1000.0, 1000.0, 1000.0],
                        "raw_end": [3000.0, 1000.0, 1000.0],
                    },
                }
            ],
            "fittings": [],
            "welds": [],
            "supports": [],
            "markers": [],
            "stats": {"source_format": "IDF"},
        }
        ifc_scene = {
            "meshes": [
                {
                    "uid": 10,
                    "properties": {
                        "ifc_class": "IfcColumn",
                        "component_ref": "COL-FAR",
                        "name": "Far Column",
                        "storey_name": "L1",
                        "material_names": ["STEEL"],
                        "filename": "sample.ifc",
                        "raw_bounds": {
                            "min_x": 5000.0,
                            "max_x": 5000.5,
                            "min_y": 5000.0,
                            "max_y": 5000.5,
                            "min_z": 100.0,
                            "max_z": 101.0,
                        },
                    },
                }
            ]
        }

        report = nearest_structure_report(pipeline_scene, ifc_scene)
        self.assertTrue(report["summary"]["warning"])


class AnalysisViewTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @patch("idfviewer.views.parse_multiple_ifc_uploads")
    def test_analyze_nearest_structure_view_returns_report(self, mock_parse_ifc):
        mock_parse_ifc.return_value = {
            "meshes": [
                {
                    "uid": 10,
                    "properties": {
                        "ifc_class": "IfcColumn",
                        "component_ref": "COL-A",
                        "name": "Column A",
                        "storey_name": "L1",
                        "material_names": ["STEEL"],
                        "filename": "sample.ifc",
                        "raw_bounds": {
                            "min_x": 3.2,
                            "max_x": 3.4,
                            "min_y": 0.8,
                            "max_y": 1.2,
                            "min_z": 0.8,
                            "max_z": 1.2,
                        },
                    },
                }
            ]
        }
        request = self.factory.post(
            "/idfviewer/analyze-nearest-structure/",
            data={
                "scene": json.dumps(make_preview_scene()),
                "ifc_files": SimpleUploadedFile("sample.ifc", b"ISO-10303-21;", content_type="application/octet-stream"),
            },
        )

        response = analyze_nearest_structure_view(request)
        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content)
        self.assertEqual(payload["summary"]["line_count"], 1)
        self.assertEqual(payload["summary"]["ifc_object_count"], 1)
        self.assertEqual(payload["results"][0]["component_ref"], "COL-A")


def make_project():
    return ProjectData.objects.create(
        proj_id="PIPE_TEST",
        min_amb_t=Decimal("0.00"),
        max_amb_t=Decimal("50.00"),
        startup_t=Decimal("10.00"),
        area_class="SAFE",
        temp_class="T3",
        voltage=Decimal("230.00"),
        max_cb_size=20,
        restrict_cb_current=Decimal("20.00"),
        vendor="THR",
        spiral_wrap_allowed=True,
        spiral_factor=Decimal("1.00"),
        valve_factor=Decimal("0.00"),
        flange_factor=Decimal("0.00"),
        support_factor=Decimal("0.00"),
        margin_on_tracer_lengths=Decimal("5.00"),
        voltage_var_factor=Decimal("1.00"),
        res_tol=Decimal("1.00"),
        termination_margin=Decimal("100.00"),
        heat_loss_sf=Decimal("1.00"),
        rtd_thrm="TI",
        wind_speed=Decimal("1.00"),
        req_local_isolator="required",
        caution_label_interval=Decimal("10.00"),
        k_factor_ccons=Decimal("1.00"),
        isolator_location="incomingOnly",
        ckt_ln=Decimal("10.00"),
        loop_ln=Decimal("10.00"),
        acc_power_density=Decimal("1.00"),
        tracer_temp_factor=Decimal("1.00"),
        alpha_for_res=Decimal("1.0000"),
        allowablevdrop=Decimal("5.00"),
    )


def make_preview_scene(filename="alpha.idf", line_id="LINE-01", component_ref="PIPE-A"):
    return {
        "pipes": [
            {
                "uid": 1,
                "record_id": 100,
                "kind": "Pipe",
                "start": [0.0, 0.0, 0.0],
                "end": [10.0, 0.0, 0.0],
                "properties": {
                    "uid": 1,
                    "record_id": 100,
                    "kind": "Pipe",
                    "filename": filename,
                    "source_format": "IDF",
                    "pipeline_ref": line_id,
                    "component_ref": component_ref,
                    "raw_start": [1000, 2000, 3000],
                    "raw_end": [2000, 2000, 3000],
                    "materials": [],
                    "notes": [],
                },
            }
        ],
        "fittings": [],
        "welds": [],
        "supports": [
            {
                "uid": 2,
                "record_id": 150,
                "kind": "Support",
                "point": [5.0, 0.0, 0.0],
                "properties": {
                    "uid": 2,
                    "record_id": 150,
                    "kind": "Support",
                    "filename": filename,
                    "source_format": "IDF",
                    "pipeline_ref": line_id,
                    "support_code": "SUP-01",
                    "raw_point": [1500, 2000, 3000],
                    "materials": [],
                    "notes": [],
                },
            }
        ],
        "markers": [],
        "stats": {
            "source_format": "IDF",
            "source_label": "IDF Scene",
            "pipe_count": 1,
            "fitting_count": 0,
            "weld_count": 0,
            "support_count": 1,
            "marker_count": 0,
        },
    }


def make_ifc_preview_scene(filename="sample.ifc"):
    return {
        "pipes": [],
        "fittings": [],
        "welds": [],
        "supports": [],
        "markers": [],
        "meshes": [
            {
                "uid": 1,
                "record_id": 9100,
                "kind": "IfcColumn",
                "mesh": {
                    "positions": [
                        -1.0, -1.0, 0.0,
                        1.0, -1.0, 0.0,
                        1.0, 1.0, 0.0,
                        -1.0, 1.0, 0.0,
                    ],
                    "indices": [0, 1, 2, 0, 2, 3],
                    "color": [0.4, 0.5, 0.8],
                },
                "properties": {
                    "source_format": "IFC",
                    "source_record": "IfcColumn",
                    "record_id": 9100,
                    "kind": "IfcColumn",
                    "filename": filename,
                    "ifc_class": "IfcColumn",
                    "global_id": "ABC123",
                    "component_ref": "H467",
                    "name": "CABLE TRAY",
                    "hierarchy_group": "IfcBuildingStorey:Level 1 / IfcColumn",
                    "spatial_path": [
                        "IfcSite:Main Site",
                        "IfcBuilding:Main Building",
                        "IfcBuildingStorey:Level 1",
                    ],
                    "materials": [{"code": "", "description": "STEEL/S355J2"}],
                    "property_sets": {"Pset_ColumnCommon": {"Reference": "H467"}},
                    "quantities": {"BaseQuantities": {"NetWeight": 11.8}},
                    "display_color": [0.4, 0.5, 0.8],
                    "raw_bounds": {
                        "min_x": 0.0,
                        "max_x": 1000.0,
                        "min_y": 0.0,
                        "max_y": 1000.0,
                        "min_z": 0.0,
                        "max_z": 100.0,
                    },
                    "notes": [],
                },
            }
        ],
        "stats": {
            "total_lines": 1,
            "source_format": "IFC",
            "source_label": "Batched IFC Scene",
            "pipe_count": 0,
            "fitting_count": 0,
            "weld_count": 0,
            "support_count": 0,
            "marker_count": 0,
            "mesh_count": 1,
            "ifc_object_count": 1,
            "save_supported": False,
        },
    }


class SavedPipelineFlowTests(TestCase):
    def setUp(self):
        self.project = make_project()
        self.user = get_user_model().objects.create_user(
            username="idfviewer-tester",
            password="safe-password-123",
        )
        self.client.force_login(self.user)

    def test_parse_multiple_idf_texts_no_longer_persists_automatically(self):
        scene = parse_multiple_idf_texts(
            [
                (
                    "sample.idf",
                    """
                    -30 LINE-01
                    100 2000 3000 4000 3000 3000 4000,      ,       0 ,    ,      0  1001
                    -39 PIPE-A
                    150 2500 3000 4000
                    -70 SUP-01
                    """,
                )
            ],
            self.project,
        )

        self.assertEqual(scene["stats"]["source_format"], "IDF")
        self.assertEqual(IDFFile.objects.count(), 0)
        self.assertEqual(IDFComponent.objects.count(), 0)

    def test_save_preview_creates_file_and_components(self):
        response = self.client.post(
            "/idfviewer/save/",
            data=json.dumps({"project_id": self.project.proj_id, "scene": make_preview_scene()}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(IDFFile.objects.count(), 1)
        self.assertEqual(IDFComponent.objects.count(), 2)
        saved_file = IDFFile.objects.get()
        self.assertEqual(saved_file.component_count, 2)
        self.assertEqual(saved_file.pipe_count, 1)
        self.assertEqual(saved_file.support_count, 1)
        self.assertEqual(IDFFileSaveEvent.objects.count(), 1)

    def test_duplicate_save_refreshes_existing_file_without_duplicate_components(self):
        first = self.client.post(
            "/idfviewer/save/",
            data=json.dumps({"project_id": self.project.proj_id, "scene": make_preview_scene()}),
            content_type="application/json",
        )
        self.assertEqual(first.status_code, 200)

        second = self.client.post(
            "/idfviewer/save/",
            data=json.dumps({"project_id": self.project.proj_id, "scene": make_preview_scene()}),
            content_type="application/json",
        )

        self.assertEqual(second.status_code, 200)
        payload = second.json()
        self.assertEqual(len(payload["refreshed"]), 1)
        self.assertEqual(IDFFile.objects.count(), 1)
        self.assertEqual(IDFComponent.objects.count(), 2)
        self.assertEqual(IDFFileSaveEvent.objects.count(), 1)

    def test_conflicting_save_requires_confirmation_then_replaces_components(self):
        original_scene = make_preview_scene()
        changed_scene = make_preview_scene(component_ref="PIPE-B")
        changed_scene["welds"] = [
            {
                "uid": 3,
                "record_id": 120,
                "kind": "Weld",
                "point": [7.0, 0.0, 0.0],
                "properties": {
                    "uid": 3,
                    "record_id": 120,
                    "kind": "Weld",
                    "filename": "alpha.idf",
                    "source_format": "IDF",
                    "pipeline_ref": "LINE-01",
                    "raw_point": [1750, 2000, 3000],
                    "materials": [],
                    "notes": [],
                },
            }
        ]
        changed_scene["stats"]["weld_count"] = 1

        self.client.post(
            "/idfviewer/save/",
            data=json.dumps({"project_id": self.project.proj_id, "scene": original_scene}),
            content_type="application/json",
        )

        conflict = self.client.post(
            "/idfviewer/save/",
            data=json.dumps({"project_id": self.project.proj_id, "scene": changed_scene}),
            content_type="application/json",
        )
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json()["conflicts"][0]["new_component_count"], 3)

        replaced = self.client.post(
            "/idfviewer/save/",
            data=json.dumps({"project_id": self.project.proj_id, "scene": changed_scene, "force": True}),
            content_type="application/json",
        )
        self.assertEqual(replaced.status_code, 200)
        saved_file = IDFFile.objects.get()
        self.assertEqual(saved_file.component_count, 3)
        self.assertEqual(saved_file.weld_count, 1)
        self.assertEqual(IDFComponent.objects.count(), 3)
        self.assertEqual(IDFFileSaveEvent.objects.count(), 2)

    def test_saved_file_can_be_rebuilt_for_viewer_and_downloaded(self):
        self.client.post(
            "/idfviewer/save/",
            data=json.dumps({"project_id": self.project.proj_id, "scene": make_preview_scene()}),
            content_type="application/json",
        )
        saved_file = IDFFile.objects.get()

        scene = build_scene_from_saved_file(saved_file)
        self.assertEqual(scene["stats"]["pipe_count"], 1)
        self.assertEqual(scene["stats"]["support_count"], 1)
        self.assertEqual(scene["stats"]["coordinate_unit"], "MM")
        self.assertEqual(scene["stats"]["coordinate_scale_to_m"], 0.001)
        self.assertEqual(len(scene["pipes"]), 1)
        self.assertEqual(len(scene["supports"]), 1)

        viewer_response = self.client.get(f"/idfviewer/saved/{saved_file.id}/")
        self.assertEqual(viewer_response.status_code, 200)
        self.assertContains(viewer_response, "Saved Dataset")

        download_response = self.client.get(f"/idfviewer/saved/{saved_file.id}/download/")
        self.assertEqual(download_response.status_code, 200)
        payload = json.loads(download_response.content)
        self.assertEqual(payload["component_count"], 2)
        self.assertEqual(len(payload["components"]), 2)

    @patch("idfviewer.views.parse_multiple_ifc_uploads")
    def test_ifc_upload_renders_preview_and_hides_save_button(self, mock_parse_ifc):
        mock_parse_ifc.return_value = make_ifc_preview_scene()
        upload = SimpleUploadedFile(
            "sample.ifc",
            b"ISO-10303-21;\nFILE_SCHEMA(('IFC2X3'));",
            content_type="application/octet-stream",
        )

        response = self.client.post(
            "/idfviewer/",
            data={"project": self.project.pk, "idf_files": [upload]},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Batched IFC Scene")
        self.assertContains(response, "IFC preview save pending backend design")
        self.assertContains(response, "IFC Objects (1)")

    def test_ifc_preview_save_is_rejected(self):
        response = self.client.post(
            "/idfviewer/save/",
            data=json.dumps({"project_id": self.project.proj_id, "scene": make_ifc_preview_scene()}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("IFC preview save is not enabled yet", response.json()["error"])

    def test_project_attribute_mappings_are_project_scoped_and_persistent(self):
        url = f"/idfviewer/projects/{self.project.proj_id}/attribute-mappings/"

        empty_response = self.client.get(url)
        self.assertEqual(empty_response.status_code, 200)
        self.assertEqual(empty_response.json()["mappings"], [])

        save_response = self.client.post(
            url,
            data=json.dumps({
                "mappings": [
                    {"attribute_key": "ATTRIBUTE63", "display_name": "Line ID"},
                    {"attribute_key": "attribute72", "display_name": "Fluid"},
                ]
            }),
            content_type="application/json",
        )

        self.assertEqual(save_response.status_code, 200)
        self.assertEqual(ProjectAttributeMapping.objects.count(), 2)
        payload = save_response.json()
        self.assertEqual(
            [(row["attribute_key"], row["display_name"]) for row in payload["mappings"]],
            [("ATTRIBUTE63", "Line ID"), ("ATTRIBUTE72", "Fluid")],
        )

        reload_response = self.client.get(url)
        self.assertEqual(reload_response.status_code, 200)
        self.assertEqual(reload_response.json()["mappings"][0]["display_name"], "Line ID")

    def test_project_attribute_mapping_rejects_invalid_attribute_key(self):
        response = self.client.post(
            f"/idfviewer/projects/{self.project.proj_id}/attribute-mappings/",
            data=json.dumps({"mappings": [{"attribute_key": "LINE_ID", "display_name": "Line ID"}]}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid attribute key", response.json()["error"])

    def test_eht_design_elements_are_project_and_file_scoped(self):
        self.client.post(
            "/idfviewer/save/",
            data=json.dumps({"project_id": self.project.proj_id, "scene": make_preview_scene()}),
            content_type="application/json",
        )
        saved_file = IDFFile.objects.get()
        url = f"/idfviewer/projects/{self.project.proj_id}/eht-elements/?file_id={saved_file.id}"

        payload = {
            "elements": [
                {
                    "element_uid": "db-1",
                    "element_type": "distribution_board",
                    "label": "DB-001",
                    "geometry": {"type": "point", "points": [[0.0, 0.0, 0.0]]},
                    "metadata": {"tag": "DB-001", "note": "Existing board"},
                },
                {
                    "element_uid": "tracer-1",
                    "element_type": "tracer_sr",
                    "label": "SR-001",
                    "geometry": {"type": "polyline", "points": [[0.0, 0.0, 0.0], [1.5, 0.0, 0.0], [1.5, 2.0, 0.0]]},
                    "metadata": {"tracer_family": "SR", "tracer_type": "Self-reg"},
                },
            ]
        }

        save_response = self.client.post(url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(save_response.status_code, 200)
        self.assertEqual(EHTDesignElement.objects.count(), 2)
        self.assertEqual(save_response.json()["count"], 2)

        reload_response = self.client.get(url)
        self.assertEqual(reload_response.status_code, 200)
        elements = reload_response.json()["elements"]
        self.assertEqual(len(elements), 2)
        self.assertEqual(elements[0]["label"], "DB-001")
        self.assertEqual(elements[1]["metadata"]["tracer_family"], "SR")
        self.assertEqual(elements[1]["geometry"]["segment_count"], 2)
        self.assertEqual(elements[1]["geometry"]["length_m"], 3.5)
        self.assertIn("tracer_sr", reload_response.json()["tool_definitions"])

        project_scope_response = self.client.get(f"/idfviewer/projects/{self.project.proj_id}/eht-elements/")
        self.assertEqual(project_scope_response.status_code, 200)
        self.assertEqual(project_scope_response.json()["elements"], [])

    def test_eht_design_elements_reject_invalid_geometry(self):
        response = self.client.post(
            f"/idfviewer/projects/{self.project.proj_id}/eht-elements/",
            data=json.dumps({
                "elements": [
                    {
                        "element_uid": "bad-1",
                        "element_type": "cold_cable",
                        "geometry": {"type": "polyline", "points": [[0.0, 0.0, 0.0]]},
                        "metadata": {},
                    }
                ]
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("polyline geometry", response.json()["error"])

    def test_eht_design_elements_validate_metadata_schema(self):
        response = self.client.post(
            f"/idfviewer/projects/{self.project.proj_id}/eht-elements/",
            data=json.dumps({
                "elements": [
                    {
                        "element_uid": "tracer-1",
                        "element_type": "tracer_sr",
                        "label": "Bad tracer",
                        "geometry": {"type": "polyline", "points": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]]},
                        "metadata": {"tracer_family": "MI"},
                    }
                ]
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Tracer Family", response.json()["error"])
