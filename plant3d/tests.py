import json
import tempfile
from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from eht.models import ProjectData

from .models import ConversionJob, ModelObject, RenderPackage, RenderTile, SourceModel
from .services import create_source_model_from_upload, run_metadata_conversion
from .storage import path_for_storage_key


def create_project(proj_id="P3D-TEST"):
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

    def test_metadata_conversion_writes_manifest_package_and_tile(self):
        upload = SimpleUploadedFile(
            "pipe-rack.ifc",
            b"ISO-10303-21;\nHEADER;\nFILE_NAME('pipe-rack.ifc');\nFILE_SCHEMA(('IFC4'));\nENDSEC;\nDATA;\n#1=IFCPROJECT();\n#2=IFCBEAM();\nENDSEC;",
        )
        source = create_source_model_from_upload(self.project, upload)

        job, package = run_metadata_conversion(source)

        self.assertEqual(job.status, "completed")
        self.assertEqual(job.progress_percent, 100)
        self.assertEqual(package.package_format, "TILED_JSON")
        self.assertEqual(package.tile_count, 1)
        self.assertEqual(package.tiles.count(), 1)

        manifest_path = path_for_storage_key(package.manifest_storage_key)
        self.assertTrue(manifest_path.exists())
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["source_model_id"], source.pk)
        self.assertEqual(manifest["source_format"], "IFC")
        self.assertEqual(manifest["ifc_entity_count_sample"], 2)

    def test_upload_view_creates_source_model(self):
        user = get_user_model().objects.create_user(username="plant3d-user", password="pw")
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
                        "positions": [0, 0, 0, 1, 0, 0, 0, 1, 0],
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
            SimpleUploadedFile("geometry.ifc", b"ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('IFC4'));\nENDSEC;"),
        )

        from .services import run_ifc_geometry_conversion

        job, package = run_ifc_geometry_conversion(source)

        self.assertEqual(job.status, "completed")
        self.assertEqual(job.metrics["mesh_count"], 1)
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
        self.assertEqual(payload["meshes"][0]["properties"]["global_id"], "beam-guid-1")

    @patch("plant3d.services.parse_multiple_ifc_uploads")
    def test_ifc_geometry_conversion_endpoint_returns_package_payload(self, mock_parse):
        mock_parse.return_value = self._sample_ifc_scene()
        user = get_user_model().objects.create_user(username="plant3d-geometry-user", password="pw")
        self.client.force_login(user)
        source = create_source_model_from_upload(
            self.project,
            SimpleUploadedFile("endpoint.ifc", b"ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('IFC4'));\nENDSEC;"),
        )

        response = self.client.post(reverse("plant3d_source_ifc_geometry_convert", args=[source.pk]))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["job"]["status"], "completed")
        self.assertEqual(payload["package"]["object_count"], 1)
        self.assertEqual(SourceModel.objects.get(pk=source.pk).model_objects.count(), 1)
