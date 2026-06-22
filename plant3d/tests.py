import json
import tempfile
from decimal import Decimal
from unittest.mock import patch

from django.core.management import call_command
from django.core.exceptions import SuspiciousFileOperation, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from eht.models import ManagedProject, ProjectData

from .models import ConversionJob, ModelObject, RenderPackage, RenderTile, SourceModel
from .services import (
    create_source_model_from_upload,
    extract_ifc_unit_hints,
    queue_ifc_geometry_conversion,
    queue_metadata_conversion,
    run_metadata_conversion,
)
from .storage import path_for_storage_key


def create_project(proj_id="P3D-TEST"):
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


class Plant3DModelTests(TestCase):
    def test_source_model_records_project_and_provenance(self):
        project = create_project()

        source = SourceModel.objects.create(
            project=project,
            display_name="Pipe rack IFC",
            source_format="IFC",
            original_filename="pipe-rack.ifc",
            storage_key="source/P3D-TEST/pipe-rack.ifc",
            content_signature="a" * 64,
            file_size_bytes=20_000_000,
            source_system="Tekla",
            declared_unit="M",
            coordinate_frame="plant-global",
            bounds={"min": [0, 0, 0], "max": [10, 20, 5]},
        )

        self.assertEqual(source.project, project)
        self.assertEqual(source.source_format, "IFC")
        self.assertEqual(source.bounds["max"], [10, 20, 5])

    def test_conversion_job_progress_is_validated(self):
        project = create_project()
        source = SourceModel.objects.create(
            project=project,
            display_name="Sample IFC",
            source_format="IFC",
            original_filename="sample.ifc",
            storage_key="source/sample.ifc",
        )

        job = ConversionJob(
            source_model=source,
            status="running",
            progress_percent=101,
        )

        with self.assertRaises(ValidationError):
            job.full_clean()

    def test_render_package_tiles_preserve_rtc_origin(self):
        project = create_project()
        source = SourceModel.objects.create(
            project=project,
            display_name="Large coordinate IFC",
            source_format="IFC",
            original_filename="large.ifc",
            storage_key="source/large.ifc",
        )
        job = ConversionJob.objects.create(
            source_model=source,
            status="completed",
            progress_percent=100,
            output_storage_prefix="render/large/",
        )
        package = RenderPackage.objects.create(
            source_model=source,
            conversion_job=job,
            package_format="TILED_JSON",
            storage_prefix="render/large/",
            manifest_storage_key="render/large/manifest.json",
            coordinate_unit="M",
            tile_count=1,
        )
        tile = RenderTile.objects.create(
            render_package=package,
            tile_id="tile-0001",
            storage_key="render/large/tile-0001.glb",
            sequence=1,
            rtc_origin_x=500000.0,
            rtc_origin_y=2800000.0,
            rtc_origin_z=100.0,
            bounds={"min": [-5, -5, 0], "max": [5, 5, 10]},
        )

        self.assertEqual(tile.rtc_origin, [500000.0, 2800000.0, 100.0])
        self.assertEqual(package.tiles.count(), 1)

    def test_render_tile_id_is_unique_per_package(self):
        project = create_project()
        source = SourceModel.objects.create(
            project=project,
            display_name="Duplicate tile IFC",
            source_format="IFC",
            original_filename="dup.ifc",
            storage_key="source/dup.ifc",
        )
        package = RenderPackage.objects.create(
            source_model=source,
            package_format="TILED_JSON",
            storage_prefix="render/dup/",
        )
        RenderTile.objects.create(render_package=package, tile_id="tile-0001", storage_key="render/dup/1.glb")

        with self.assertRaises(IntegrityError):
            RenderTile.objects.create(render_package=package, tile_id="tile-0001", storage_key="render/dup/2.glb")

    def test_model_object_stable_id_is_unique_per_source(self):
        project = create_project()
        source = SourceModel.objects.create(
            project=project,
            display_name="Indexed IFC",
            source_format="IFC",
            original_filename="indexed.ifc",
            storage_key="source/indexed.ifc",
        )
        ModelObject.objects.create(source_model=source, stable_id="ifc-guid-1", object_type="IfcBeam", tag="B-001")

        with self.assertRaises(IntegrityError):
            ModelObject.objects.create(source_model=source, stable_id="ifc-guid-1", object_type="IfcColumn")


class Plant3DIntakeTests(TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.settings_override = self.settings(MEDIA_ROOT=self.tmpdir.name)
        self.settings_override.enable()
        self.project = create_project("P3D-IN")

    def tearDown(self):
        self.settings_override.disable()
        self.tmpdir.cleanup()

    def test_upload_service_persists_source_blob_and_record(self):
        upload = SimpleUploadedFile(
            "sample.ifc",
            b"ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('IFC4'));\nENDSEC;\nDATA;\n#1=IFCPROJECT();\nENDSEC;",
        )

        source = create_source_model_from_upload(self.project, upload, source_system="Tekla")

        self.assertEqual(source.source_format, "IFC")
        self.assertEqual(source.source_system, "Tekla")
        self.assertEqual(source.file_size_bytes, upload.size)
        self.assertTrue(path_for_storage_key(source.storage_key).exists())

    def test_upload_service_reuses_duplicate_source_signature(self):
        upload_1 = SimpleUploadedFile("sample.ifc", b"ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('IFC4'));\nENDSEC;")
        upload_2 = SimpleUploadedFile("renamed.ifc", b"ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('IFC4'));\nENDSEC;")

        first = create_source_model_from_upload(self.project, upload_1)
        second = create_source_model_from_upload(self.project, upload_2, display_name="Duplicate")

        self.assertEqual(first.pk, second.pk)
        self.assertEqual(SourceModel.objects.count(), 1)

    def test_storage_key_rejects_parent_directory_segments(self):
        with self.assertRaises(SuspiciousFileOperation):
            path_for_storage_key("plant3d/../secret.txt")

    def test_ifc_unit_hints_extract_si_and_conversion_based_units(self):
        hints = extract_ifc_unit_hints(
            "\n".join(
                [
                    "#15= IFCSIUNIT(*,.LENGTHUNIT.,.MILLI.,.METRE.);",
                    "#16= IFCMEASUREWITHUNIT(IFCRATIOMEASURE(304.8),#15);",
                    "#18= IFCCONVERSIONBASEDUNIT(#17,.LENGTHUNIT.,'FOOT',#16);",
                ]
            )
        )

        self.assertEqual(hints["primary_length_display_unit"], "mm")
        self.assertEqual(hints["primary_length_scale_to_m"], 0.001)
        self.assertEqual(hints["length_si_units"][0]["entity_id"], "#15")
        self.assertEqual(hints["conversion_based_length_units"][0]["name"], "FOOT")

    def test_metadata_conversion_writes_manifest_package_and_tile(self):
        upload = SimpleUploadedFile(
            "pipe-rack.ifc",
            b"ISO-10303-21;\nHEADER;\nFILE_NAME('pipe-rack.ifc');\nFILE_SCHEMA(('IFC4'));\nENDSEC;\nDATA;\n#1=IFCPROJECT();\n#2=IFCBEAM();\n#15= IFCSIUNIT(*,.LENGTHUNIT.,.MILLI.,.METRE.);\nENDSEC;",
        )
        source = create_source_model_from_upload(self.project, upload)

        job, package = run_metadata_conversion(source)

        self.assertEqual(job.status, "completed")
        self.assertEqual(job.progress_percent, 100)
        self.assertIn("conversion_duration_ms", job.metrics)
        self.assertEqual(package.package_format, "TILED_JSON")
        self.assertEqual(package.tile_count, 1)
        self.assertEqual(package.tiles.count(), 1)

        manifest_path = path_for_storage_key(package.manifest_storage_key)
        self.assertTrue(manifest_path.exists())
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["source_model_id"], source.pk)
        self.assertEqual(manifest["source_format"], "IFC")
        self.assertEqual(manifest["ifc_entity_count_sample"], 3)
        self.assertEqual(manifest["ifc_unit_hints"]["primary_length_display_unit"], "mm")

    def test_upload_view_creates_source_model(self):
        user = get_user_model().objects.create_user(username="plant3d-user", password="pw")
        assign_project(user, self.project)
        self.client.force_login(user)

        response = self.client.post(
            reverse("plant3d_source_upload"),
            {
                "project": self.project.pk,
                "display_name": "Uploaded IFC",
                "source_system": "Sample",
                "source_file": SimpleUploadedFile(
                    "uploaded.ifc",
                    b"ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('IFC4'));\nENDSEC;",
                ),
            },
        )

        source = SourceModel.objects.get()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(source.display_name, "Uploaded IFC")
        self.assertEqual(source.project, self.project)
        self.assertTrue(path_for_storage_key(source.storage_key).exists())

    def _sample_ifc_scene(self):
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
                    "kind": "IfcBeam",
                    "mesh": {
                        "positions": [-0.5, -0.5, -0.5, 0.5, -0.5, -0.5, -0.5, 0.5, -0.5],
                        "indices": [0, 1, 2],
                        "color": [0.5, 0.5, 0.5],
                    },
                    "properties": {
                        "ifc_class": "IfcBeam",
                        "global_id": "beam-guid-1",
                        "component_ref": "B-001",
                        "name": "Beam 001",
                        "hierarchy_group": "Level 1 / IfcBeam",
                        "spatial_path": ["IfcBuilding:Main", "IfcBuildingStorey:Level 1"],
                        "raw_bounds": {
                            "min_x": 500000.0,
                            "max_x": 500001.0,
                            "min_y": 2800000.0,
                            "max_y": 2800001.0,
                            "min_z": 100.0,
                            "max_z": 101.0,
                        },
                    },
                }
            ],
            "stats": {
                "source_format": "IFC",
                "coordinate_unit": "M",
                "coordinate_scale_to_m": 1.0,
                "display_unit": "m",
                "unit_confidence": "assumed",
                "raw_bounds": {
                    "min_x": 500000.0,
                    "max_x": 500001.0,
                    "min_y": 2800000.0,
                    "max_y": 2800001.0,
                    "min_z": 100.0,
                    "max_z": 101.0,
                },
            },
        }

    @patch("plant3d.services.parse_multiple_ifc_uploads")
    def test_ifc_geometry_conversion_writes_tile_and_object_index(self, mock_parse):
        mock_parse.return_value = self._sample_ifc_scene()
        source = create_source_model_from_upload(
            self.project,
            SimpleUploadedFile(
                "geometry.ifc",
                b"ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('IFC4'));\nENDSEC;\nDATA;\n#15= IFCSIUNIT(*,.LENGTHUNIT.,.MILLI.,.METRE.);\nENDSEC;",
            ),
        )

        from .services import run_ifc_geometry_conversion

        job, package = run_ifc_geometry_conversion(source)

        self.assertEqual(job.status, "completed")
        self.assertEqual(job.metrics["mesh_count"], 1)
        self.assertIn("conversion_duration_ms", job.metrics)
        self.assertEqual(package.object_count, 1)
        self.assertEqual(package.tile_count, 1)
        self.assertEqual(package.tiles.count(), 1)
        self.assertEqual(source.model_objects.count(), 1)

        obj = source.model_objects.get()
        self.assertEqual(obj.stable_id, "ifc:beam-guid-1")
        self.assertEqual(obj.object_type, "IfcBeam")
        self.assertEqual(obj.tag, "B-001")

        tile_path = path_for_storage_key(package.manifest_storage_key)
        payload = json.loads(tile_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["tile_id"], "geometry-0001")
        self.assertEqual(payload["rtc_origin"], [500000.5, 100.5, 2800000.5])
        self.assertEqual(payload["coordinate_transform"]["origin_source_xyz"], [500000.5, 2800000.5, 100.5])
        self.assertEqual(payload["coordinate_transform"]["rtc_origin_render_xyz"], [500000.5, 100.5, 2800000.5])
        self.assertEqual(package.tiles.get().rtc_origin, [500000.5, 100.5, 2800000.5])
        self.assertEqual(payload["source_unit_hints"]["primary_length_display_unit"], "mm")
        self.assertTrue(payload["unit_warnings"])
        self.assertTrue(package.metadata["unit_warnings"])
        self.assertTrue(job.metrics["unit_warnings"])
        self.assertEqual(payload["meshes"][0]["properties"]["global_id"], "beam-guid-1")
        self.assertLess(max(abs(value) for value in payload["meshes"][0]["mesh"]["positions"]), 2.0)

        first_local_vertex = payload["meshes"][0]["mesh"]["positions"][:3]
        origin = payload["coordinate_transform"]["rtc_origin_render_xyz"]
        scale = payload["coordinate_transform"]["scale_to_m"]
        render_world = [origin[index] + first_local_vertex[index] for index in range(3)]
        reconstructed_source = [
            render_world[0] / scale,
            render_world[2] / scale,
            render_world[1] / scale,
        ]
        self.assertEqual(reconstructed_source, [500000.0, 2800000.0, 100.0])

    @patch("plant3d.services.parse_multiple_ifc_uploads")
    def test_ifc_geometry_conversion_endpoint_queues_job(self, mock_parse):
        mock_parse.return_value = self._sample_ifc_scene()
        user = get_user_model().objects.create_user(username="plant3d-geometry-user", password="pw")
        assign_project(user, self.project)
        self.client.force_login(user)
        source = create_source_model_from_upload(
            self.project,
            SimpleUploadedFile("endpoint.ifc", b"ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('IFC4'));\nENDSEC;"),
        )

        response = self.client.post(reverse("plant3d_source_ifc_geometry_convert", args=[source.pk]))

        self.assertEqual(response.status_code, 202)
        payload = response.json()
        self.assertEqual(payload["job"]["job_type"], "render_package")
        self.assertEqual(payload["job"]["status"], "queued")
        self.assertIn("/plant3d/jobs/", payload["job"]["url"])
        self.assertIn("process_plant3d_job", payload["process_hint"])
        self.assertEqual(SourceModel.objects.get(pk=source.pk).model_objects.count(), 0)

    @patch("plant3d.services.parse_multiple_ifc_uploads")
    def test_management_command_processes_queued_ifc_geometry_job(self, mock_parse):
        mock_parse.return_value = self._sample_ifc_scene()
        source = create_source_model_from_upload(
            self.project,
            SimpleUploadedFile("queued.ifc", b"ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('IFC4'));\nENDSEC;"),
        )
        job = queue_ifc_geometry_conversion(source)

        call_command("process_plant3d_job", str(job.pk), verbosity=0)

        job.refresh_from_db()
        self.assertEqual(job.status, "completed")
        self.assertEqual(job.render_packages.count(), 1)
        self.assertEqual(source.model_objects.count(), 1)

    def test_management_command_processes_all_queued_jobs(self):
        source_1 = create_source_model_from_upload(
            self.project,
            SimpleUploadedFile("metadata-1.ifc", b"ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('IFC4'));\nENDSEC;"),
        )
        source_2 = create_source_model_from_upload(
            self.project,
            SimpleUploadedFile("metadata-2.ifc", b"ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('IFC4'));\nENDSEC;\nDATA;\n#1=IFCPROJECT();"),
        )
        queue_metadata_conversion(source_1)
        queue_metadata_conversion(source_2)

        call_command("process_plant3d_job", all=True, verbosity=0)

        self.assertEqual(ConversionJob.objects.filter(status="queued").count(), 0)
        self.assertEqual(ConversionJob.objects.filter(status="completed").count(), 2)

    @patch("plant3d.services.parse_multiple_ifc_uploads")
    def test_job_json_reports_completed_package_after_command_processing(self, mock_parse):
        mock_parse.return_value = self._sample_ifc_scene()
        user = get_user_model().objects.create_user(username="plant3d-job-user", password="pw")
        assign_project(user, self.project)
        self.client.force_login(user)
        source = create_source_model_from_upload(
            self.project,
            SimpleUploadedFile("job-api.ifc", b"ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('IFC4'));\nENDSEC;"),
        )
        job = queue_ifc_geometry_conversion(source)
        call_command("process_plant3d_job", str(job.pk), verbosity=0)

        response = self.client.get(reverse("plant3d_job_json", args=[job.pk]))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "completed")
        self.assertIn("/plant3d/jobs/", payload["url"])
        self.assertEqual(payload["package"]["object_count"], 1)
        self.assertIn("/plant3d/packages/", payload["package"]["viewer_url"])
        self.assertIn("/plant3d/packages/", payload["package"]["json_url"])

    @patch("plant3d.services.parse_multiple_ifc_uploads")
    def test_package_and_tile_json_endpoints_return_render_payload(self, mock_parse):
        mock_parse.return_value = self._sample_ifc_scene()
        user = get_user_model().objects.create_user(username="plant3d-api-user", password="pw")
        assign_project(user, self.project)
        self.client.force_login(user)
        source = create_source_model_from_upload(
            self.project,
            SimpleUploadedFile("api.ifc", b"ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('IFC4'));\nENDSEC;"),
        )

        from .services import run_ifc_geometry_conversion

        _, package = run_ifc_geometry_conversion(source)
        package_response = self.client.get(reverse("plant3d_package_json", args=[package.pk]))

        self.assertEqual(package_response.status_code, 200)
        package_payload = package_response.json()
        self.assertEqual(package_payload["object_count"], 1)
        self.assertEqual(package_payload["tile_count"], 1)
        self.assertEqual(len(package_payload["tiles"]), 1)
        self.assertEqual(package_payload["tiles"][0]["rtc_origin"], [500000.5, 100.5, 2800000.5])
        self.assertEqual(len(package_payload["objects"]), 1)
        self.assertEqual(package_payload["objects"][0]["stable_id"], "ifc:beam-guid-1")
        self.assertIn("/plant3d/objects/", package_payload["objects"][0]["url"])
        self.assertIn("/plant3d/tiles/", package_payload["tiles"][0]["url"])

        object_id = source.model_objects.get().pk
        object_response = self.client.get(reverse("plant3d_model_object_json", args=[object_id]))
        self.assertEqual(object_response.status_code, 200)
        object_payload = object_response.json()
        self.assertEqual(object_payload["stable_id"], "ifc:beam-guid-1")
        self.assertEqual(object_payload["metadata"]["name"], "Beam 001")

        tile_id = package.tiles.get().pk
        tile_response = self.client.get(reverse("plant3d_tile_json", args=[tile_id]))
        self.assertEqual(tile_response.status_code, 200)
        tile_payload = tile_response.json()
        self.assertEqual(tile_payload["tile_id"], "geometry-0001")
        self.assertEqual(tile_payload["rtc_origin"], [500000.5, 100.5, 2800000.5])
        self.assertEqual(tile_payload["coordinate_transform"]["origin_source_xyz"], [500000.5, 2800000.5, 100.5])
        self.assertEqual(tile_payload["coordinate_transform"]["rtc_origin_render_xyz"], [500000.5, 100.5, 2800000.5])
        self.assertEqual(tile_payload["meshes"][0]["properties"]["global_id"], "beam-guid-1")

    @patch("plant3d.services.parse_multiple_ifc_uploads")
    def test_package_viewer_page_exposes_package_api_url(self, mock_parse):
        mock_parse.return_value = self._sample_ifc_scene()
        user = get_user_model().objects.create_user(username="plant3d-viewer-user", password="pw")
        assign_project(user, self.project)
        self.client.force_login(user)
        source = create_source_model_from_upload(
            self.project,
            SimpleUploadedFile("viewer.ifc", b"ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('IFC4'));\nENDSEC;"),
        )

        from .services import run_ifc_geometry_conversion

        _, package = run_ifc_geometry_conversion(source)
        response = self.client.get(reverse("plant3d_package_viewer", args=[package.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("plant3d_package_json", args=[package.pk]))
        self.assertContains(response, "plant3d viewer")

    def test_source_detail_page_wires_conversion_polling_script(self):
        user = get_user_model().objects.create_user(username="plant3d-source-detail-user", password="pw")
        assign_project(user, self.project)
        self.client.force_login(user)
        source = create_source_model_from_upload(
            self.project,
            SimpleUploadedFile("detail.ifc", b"ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('IFC4'));\nENDSEC;"),
        )
        queue_metadata_conversion(source)

        response = self.client.get(reverse("plant3d_source_detail", args=[source.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-conversion-form')
        self.assertContains(response, 'data-watch-job')
        self.assertContains(response, 'plant3d/js/source_detail.js')

    def test_source_json_filters_to_user_accessible_projects(self):
        user = get_user_model().objects.create_user(username="plant3d-filter-user", password="pw")
        assign_project(user, self.project)
        other_project = create_project("P3D-OTHER")
        create_source_model_from_upload(
            self.project,
            SimpleUploadedFile("visible.ifc", b"ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('IFC4'));\nENDSEC;"),
            display_name="Visible",
        )
        create_source_model_from_upload(
            other_project,
            SimpleUploadedFile("hidden.ifc", b"ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('IFC4'));\nENDSEC;"),
            display_name="Hidden",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("plant3d_source_models_json"))

        self.assertEqual(response.status_code, 200)
        names = [row["display_name"] for row in response.json()["sources"]]
        self.assertEqual(names, ["Visible"])

    def test_source_detail_blocks_unassigned_project(self):
        user = get_user_model().objects.create_user(username="plant3d-denied-user", password="pw")
        source = create_source_model_from_upload(
            self.project,
            SimpleUploadedFile("denied.ifc", b"ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('IFC4'));\nENDSEC;"),
        )
        self.client.force_login(user)

        response = self.client.get(reverse("plant3d_source_detail", args=[source.pk]))

        self.assertEqual(response.status_code, 404)

    @patch("plant3d.services.parse_multiple_ifc_uploads")
    def test_model_object_json_blocks_unassigned_project(self, mock_parse):
        mock_parse.return_value = self._sample_ifc_scene()
        source = create_source_model_from_upload(
            self.project,
            SimpleUploadedFile("object-denied.ifc", b"ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('IFC4'));\nENDSEC;"),
        )

        from .services import run_ifc_geometry_conversion

        run_ifc_geometry_conversion(source)
        obj = source.model_objects.get()
        user = get_user_model().objects.create_user(username="plant3d-object-denied", password="pw")
        self.client.force_login(user)

        response = self.client.get(reverse("plant3d_model_object_json", args=[obj.pk]))

        self.assertEqual(response.status_code, 404)
