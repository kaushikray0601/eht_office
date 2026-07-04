import copy
import io
import json
import os
import struct
import tempfile
from decimal import Decimal
from unittest.mock import patch

from django.core.management import call_command, CommandError
from django.core.exceptions import SuspiciousFileOperation, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase, override_settings
from django.urls import reverse

from eht.models import ManagedProject, ProjectData

from .models import ConversionJob, ModelObject, RenderPackage, RenderTile, SourceModel
from .parsers.ifc import (
    _cpu_count_from_cgroup_v1,
    _cpu_count_from_cgroup_v2,
    _memory_bytes_from_cgroup_v1,
    _memory_bytes_from_cgroup_v2,
    _thread_cap_from_memory_limit,
    configured_ifc_iterator_thread_count,
    extract_ifc_length_unit_stats,
)
from .services import (
    create_source_model_from_upload,
    extract_ifc_unit_hints,
    queue_ifc_geometry_conversion,
    queue_ifc_glb_conversion,
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


def glb_json_chunk(glb_bytes):
    magic, version, _length = struct.unpack_from("<III", glb_bytes, 0)
    if magic != 0x46546C67 or version != 2:
        raise AssertionError("Not a GLB v2 payload.")
    chunk_length, chunk_type = struct.unpack_from("<I4s", glb_bytes, 12)
    if chunk_type != b"JSON":
        raise AssertionError("First GLB chunk is not JSON.")
    return json.loads(glb_bytes[20:20 + chunk_length].decode("utf-8"))


def glb_json_and_bin_chunks(glb_bytes):
    gltf = glb_json_chunk(glb_bytes)
    first_chunk_length = struct.unpack_from("<I", glb_bytes, 12)[0]
    second_chunk_offset = 20 + first_chunk_length
    chunk_length, chunk_type = struct.unpack_from("<I4s", glb_bytes, second_chunk_offset)
    if chunk_type != b"BIN\x00":
        raise AssertionError("Second GLB chunk is not BIN.")
    bin_offset = second_chunk_offset + 8
    return gltf, glb_bytes[bin_offset:bin_offset + chunk_length]


def glb_accessor_floats(glb_bytes, accessor_index):
    gltf, bin_blob = glb_json_and_bin_chunks(glb_bytes)
    accessor = gltf["accessors"][accessor_index]
    if accessor["componentType"] != 5126:
        raise AssertionError("Accessor is not FLOAT.")
    buffer_view = gltf["bufferViews"][accessor["bufferView"]]
    byte_offset = int(buffer_view.get("byteOffset", 0)) + int(accessor.get("byteOffset", 0))
    component_count = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[accessor["type"]]
    value_count = accessor["count"] * component_count
    return struct.unpack_from("<" + "f" * value_count, bin_blob, byte_offset)


class FakeIfcEntity:
    def __init__(self, entity_name, **attributes):
        self.entity_name = entity_name
        for key, value in attributes.items():
            setattr(self, key, value)

    def is_a(self, entity_name=None):
        if entity_name is None:
            return self.entity_name
        return self.entity_name == entity_name


class FakeIfcFile:
    def __init__(self, units):
        self.units = units

    def by_type(self, entity_name):
        if entity_name == "IfcUnitAssignment":
            return [FakeIfcEntity("IfcUnitAssignment", Units=self.units)]
        return []


class FakeMeasure:
    def __init__(self, value):
        self.wrappedValue = value


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

        self.assertEqual(source.project_id, project.proj_id)
        self.assertEqual(source.source_format, "IFC")
        self.assertEqual(source.bounds["max"], [10, 20, 5])

    def test_source_model_project_reference_does_not_cascade_from_eht_project(self):
        project = create_project("P3D-NO-CASCADE")
        source = SourceModel.objects.create(
            project=project,
            display_name="Independent IFC",
            source_format="IFC",
            original_filename="independent.ifc",
            storage_key="source/P3D-NO-CASCADE/independent.ifc",
        )

        project.delete()

        source.refresh_from_db()
        self.assertEqual(source.project_id, "P3D-NO-CASCADE")

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

    def test_upload_view_replaces_prior_working_source_for_same_user_project(self):
        user = get_user_model().objects.create_user(username="plant3d-retention-user", password="pw")
        assign_project(user, self.project)
        self.client.force_login(user)

        response_1 = self.client.post(
            reverse("plant3d_source_upload"),
            {
                "project": self.project.proj_id,
                "source_file": SimpleUploadedFile("first.ifc", b"ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('IFC4'));\nENDSEC;"),
            },
        )
        first = SourceModel.objects.get()
        first_path = path_for_storage_key(first.storage_key)
        self.assertTrue(first_path.exists())

        response_2 = self.client.post(
            reverse("plant3d_source_upload"),
            {
                "project": self.project.proj_id,
                "source_file": SimpleUploadedFile("second.ifc", b"ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('IFC4'));\nENDSEC;\nDATA;\n#1=IFCPROJECT();"),
            },
        )

        self.assertEqual(response_1.status_code, 302)
        self.assertEqual(response_2.status_code, 302)
        self.assertEqual(SourceModel.objects.count(), 1)
        current = SourceModel.objects.get()
        self.assertEqual(current.original_filename, "second.ifc")
        self.assertEqual(current.uploaded_by, user)
        self.assertFalse(current.is_saved_case)
        self.assertFalse(first_path.exists())

    def test_saved_source_is_not_replaced_by_next_working_upload(self):
        user = get_user_model().objects.create_user(username="plant3d-save-user", password="pw")
        assign_project(user, self.project)
        self.client.force_login(user)
        saved = create_source_model_from_upload(
            self.project,
            SimpleUploadedFile("saved.ifc", b"ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('IFC4'));\nENDSEC;"),
            user=user,
        )

        response = self.client.post(reverse("plant3d_source_save_case", args=[saved.pk]))
        self.assertEqual(response.status_code, 302)
        saved.refresh_from_db()
        self.assertTrue(saved.is_saved_case)
        self.assertIsNotNone(saved.saved_at)

        self.client.post(
            reverse("plant3d_source_upload"),
            {
                "project": self.project.proj_id,
                "source_file": SimpleUploadedFile("working.ifc", b"ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('IFC4'));\nENDSEC;\nDATA;\n#2=IFCPROJECT();"),
            },
        )

        self.assertEqual(SourceModel.objects.count(), 2)
        self.assertTrue(SourceModel.objects.filter(pk=saved.pk, is_saved_case=True).exists())
        self.assertTrue(SourceModel.objects.filter(original_filename="working.ifc", is_saved_case=False).exists())

    def test_saved_case_limit_is_five_per_user_project(self):
        user = get_user_model().objects.create_user(username="plant3d-save-cap-user", password="pw")
        assign_project(user, self.project)
        self.client.force_login(user)
        for index in range(5):
            source = create_source_model_from_upload(
                self.project,
                SimpleUploadedFile(
                    f"saved-{index}.ifc",
                    f"ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('IFC4'));\nENDSEC;\nDATA;\n#{index + 1}=IFCPROJECT();".encode(),
                ),
                user=user,
            )
            response = self.client.post(reverse("plant3d_source_save_case", args=[source.pk]))
            self.assertEqual(response.status_code, 302)

        sixth = create_source_model_from_upload(
            self.project,
            SimpleUploadedFile("sixth.ifc", b"ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('IFC4'));\nENDSEC;\nDATA;\n#99=IFCPROJECT();"),
            user=user,
        )
        response = self.client.post(
            reverse("plant3d_source_save_case", args=[sixth.pk]),
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Only 5 saved geometry cases", response.json()["error"])
        self.assertEqual(SourceModel.objects.filter(uploaded_by=user, is_saved_case=True).count(), 5)

    def test_source_delete_view_removes_owned_source_and_storage(self):
        user = get_user_model().objects.create_user(username="plant3d-delete-owner", password="pw")
        assign_project(user, self.project)
        source = create_source_model_from_upload(
            self.project,
            SimpleUploadedFile("delete-me.ifc", b"ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('IFC4'));\nENDSEC;"),
            user=user,
        )
        source_path = path_for_storage_key(source.storage_key)
        self.assertTrue(source_path.exists())
        self.client.force_login(user)

        response = self.client.post(reverse("plant3d_source_delete", args=[source.pk]))

        self.assertEqual(response.status_code, 302)
        self.assertFalse(SourceModel.objects.filter(pk=source.pk).exists())
        self.assertFalse(source_path.exists())

    def test_source_delete_view_blocks_other_project_user_owner(self):
        owner = get_user_model().objects.create_user(username="plant3d-delete-owner-2", password="pw")
        other = get_user_model().objects.create_user(username="plant3d-delete-other", password="pw")
        assign_project(owner, self.project)
        assign_project(other, self.project)
        source = create_source_model_from_upload(
            self.project,
            SimpleUploadedFile("other-owned.ifc", b"ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('IFC4'));\nENDSEC;"),
            user=owner,
        )
        self.client.force_login(other)

        response = self.client.post(
            reverse("plant3d_source_delete", args=[source.pk]),
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertTrue(SourceModel.objects.filter(pk=source.pk).exists())

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

    def test_parser_extracts_ifc_declared_length_unit_from_unit_assignment(self):
        file = FakeIfcFile(
            [
                FakeIfcEntity("IfcSIUnit", UnitType="LENGTHUNIT", Prefix="MILLI", Name="METRE"),
                FakeIfcEntity("IfcSIUnit", UnitType="AREAUNIT", Prefix=None, Name="SQUARE_METRE"),
            ]
        )

        stats = extract_ifc_length_unit_stats(file)

        self.assertEqual(stats["ifc_declared_length_unit"], "mm")
        self.assertEqual(stats["ifc_declared_length_unit_name"], "METRE")
        self.assertEqual(stats["ifc_declared_length_unit_entity"], "IfcSIUnit")
        self.assertEqual(stats["ifc_declared_length_scale_to_m"], 0.001)

    def test_parser_extracts_conversion_based_ifc_length_unit(self):
        metre = FakeIfcEntity("IfcSIUnit", UnitType="LENGTHUNIT", Prefix=None, Name="METRE")
        conversion_factor = FakeIfcEntity(
            "IfcMeasureWithUnit",
            ValueComponent=FakeMeasure(0.3048),
            UnitComponent=metre,
        )
        file = FakeIfcFile(
            [
                FakeIfcEntity(
                    "IfcConversionBasedUnit",
                    UnitType="LENGTHUNIT",
                    Name="FOOT",
                    ConversionFactor=conversion_factor,
                )
            ]
        )

        stats = extract_ifc_length_unit_stats(file)

        self.assertEqual(stats["ifc_declared_length_unit"], "ft")
        self.assertEqual(stats["ifc_declared_length_unit_entity"], "IfcConversionBasedUnit")
        self.assertEqual(stats["ifc_declared_length_scale_to_m"], 0.3048)

    @override_settings(PLANT3D_PARSER_THREADS=None)
    def test_ifc_iterator_thread_count_defaults_to_one(self):
        with patch.dict(os.environ, {"PLANT3D_PARSER_THREADS": ""}, clear=False):
            thread_count, source = configured_ifc_iterator_thread_count()

        self.assertEqual(thread_count, 1)
        self.assertEqual(source, "default")

    @override_settings(PLANT3D_PARSER_THREADS=3)
    def test_ifc_iterator_thread_count_reads_django_setting(self):
        with patch.dict(os.environ, {"PLANT3D_PARSER_THREADS": ""}, clear=False):
            thread_count, source = configured_ifc_iterator_thread_count()

        self.assertEqual(thread_count, 3)
        self.assertEqual(source, "django_settings")

    @override_settings(PLANT3D_PARSER_THREADS=3)
    def test_ifc_iterator_thread_count_env_overrides_setting(self):
        with patch.dict(os.environ, {"PLANT3D_PARSER_THREADS": "2"}, clear=False):
            thread_count, source = configured_ifc_iterator_thread_count()

        self.assertEqual(thread_count, 2)
        self.assertEqual(source, "env")

    def test_ifc_iterator_thread_count_auto_uses_available_cpu_budget(self):
        with patch.dict(os.environ, {"PLANT3D_PARSER_THREADS": "auto"}, clear=False):
            with patch("plant3d.parsers.ifc.effective_cpu_count", return_value=8):
                with patch("plant3d.parsers.ifc.effective_memory_limit_bytes", return_value=None):
                    thread_count, source = configured_ifc_iterator_thread_count()

        self.assertEqual(thread_count, 7)
        self.assertEqual(source, "env")

    def test_ifc_iterator_thread_count_auto_respects_thread_cap(self):
        with patch.dict(
            os.environ,
            {"PLANT3D_PARSER_THREADS": "auto", "PLANT3D_PARSER_THREAD_CAP": "2"},
            clear=False,
        ):
            with patch("plant3d.parsers.ifc.effective_cpu_count", return_value=8):
                with patch("plant3d.parsers.ifc.effective_memory_limit_bytes", return_value=None):
                    thread_count, source = configured_ifc_iterator_thread_count()

        self.assertEqual(thread_count, 2)
        self.assertEqual(source, "env")

    def test_ifc_iterator_thread_count_auto_respects_cgroup_memory_limit(self):
        with patch.dict(
            os.environ,
            {
                "PLANT3D_PARSER_THREADS": "auto",
                "PLANT3D_PARSER_THREAD_CAP": "",
                "PLANT3D_PARSER_MEMORY_PER_THREAD_MB": "2048",
                "PLANT3D_PARSER_MEMORY_RESERVE_MB": "1024",
            },
            clear=False,
        ):
            with patch("plant3d.parsers.ifc.effective_cpu_count", return_value=16):
                with patch("plant3d.parsers.ifc.effective_memory_limit_bytes", return_value=5 * 1024 * 1024 * 1024):
                    thread_count, source = configured_ifc_iterator_thread_count()

        self.assertEqual(thread_count, 2)
        self.assertEqual(source, "env")

    def test_cgroup_v2_cpu_quota_count_parser(self):
        self.assertEqual(_cpu_count_from_cgroup_v2("400000 100000"), 4)
        self.assertEqual(_cpu_count_from_cgroup_v2("250000 100000"), 2)
        self.assertIsNone(_cpu_count_from_cgroup_v2("max 100000"))

    def test_cgroup_v1_cpu_quota_count_parser(self):
        self.assertEqual(_cpu_count_from_cgroup_v1("300000", "100000"), 3)
        self.assertEqual(_cpu_count_from_cgroup_v1("150000", "100000"), 1)
        self.assertIsNone(_cpu_count_from_cgroup_v1("-1", "100000"))

    def test_cgroup_memory_limit_parsers(self):
        self.assertEqual(_memory_bytes_from_cgroup_v2("5368709120"), 5 * 1024 * 1024 * 1024)
        self.assertIsNone(_memory_bytes_from_cgroup_v2("max"))
        self.assertEqual(_memory_bytes_from_cgroup_v1("3221225472"), 3 * 1024 * 1024 * 1024)
        self.assertIsNone(_memory_bytes_from_cgroup_v1(str(1 << 62)))

    def test_thread_cap_from_memory_limit_reserves_worker_memory(self):
        memory_limit = 5 * 1024 * 1024 * 1024

        cap = _thread_cap_from_memory_limit(memory_limit, per_thread_mb=2048, reserve_mb=1024)

        self.assertEqual(cap, 2)

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

    def test_purge_command_dry_runs_then_deletes_source_scope_and_storage(self):
        upload = SimpleUploadedFile(
            "purge-me.ifc",
            b"ISO-10303-21;\nHEADER;\nFILE_NAME('purge-me.ifc');\nFILE_SCHEMA(('IFC4'));\nENDSEC;\nDATA;\n#1=IFCPROJECT();\nENDSEC;",
        )
        source = create_source_model_from_upload(self.project, upload)
        _job, package = run_metadata_conversion(source)
        source_path = path_for_storage_key(source.storage_key)
        manifest_path = path_for_storage_key(package.manifest_storage_key)
        self.assertTrue(source_path.exists())
        self.assertTrue(manifest_path.exists())

        stdout = io.StringIO()
        call_command("purge_plant3d_data", source_id=[source.pk], stdout=stdout)

        self.assertIn("Dry run only", stdout.getvalue())
        self.assertTrue(SourceModel.objects.filter(pk=source.pk).exists())
        self.assertTrue(source_path.exists())
        self.assertTrue(manifest_path.exists())

        stdout = io.StringIO()
        call_command("purge_plant3d_data", source_id=[source.pk], confirm=True, stdout=stdout)

        self.assertIn("Deleted plant3d DB scope", stdout.getvalue())
        self.assertFalse(SourceModel.objects.filter(pk=source.pk).exists())
        self.assertEqual(ConversionJob.objects.count(), 0)
        self.assertEqual(RenderPackage.objects.count(), 0)
        self.assertEqual(RenderTile.objects.count(), 0)
        self.assertEqual(ModelObject.objects.count(), 0)
        self.assertFalse(source_path.exists())
        self.assertFalse(manifest_path.exists())

    def test_purge_command_requires_exactly_one_scope(self):
        with self.assertRaisesMessage(CommandError, "Choose exactly one purge scope"):
            call_command("purge_plant3d_data", verbosity=0)

    def test_upload_view_creates_source_model(self):
        user = get_user_model().objects.create_user(username="plant3d-user", password="pw")
        assign_project(user, self.project)
        self.client.force_login(user)

        response = self.client.post(
            reverse("plant3d_source_upload"),
            {
                "project": self.project.proj_id,
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
        self.assertEqual(source.project_id, self.project.proj_id)
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
                "unit_confidence": "ifcopenshell_geometry_si",
                "ifc_declared_length_units": [
                    {
                        "entity": "IfcSIUnit",
                        "unit_type": "LENGTHUNIT",
                        "name": "METRE",
                        "prefix": "MILLI",
                        "display_unit": "mm",
                        "scale_to_m": 0.001,
                        "confidence": "ifc_unit_assignment",
                    }
                ],
                "ifc_declared_length_unit": "mm",
                "ifc_declared_length_unit_name": "METRE",
                "ifc_declared_length_unit_entity": "IfcSIUnit",
                "ifc_declared_length_scale_to_m": 0.001,
                "ifc_declared_length_confidence": "ifc_unit_assignment",
                "geometry_unit": "M",
                "geometry_scale_to_m": 1.0,
                "geometry_unit_basis": "ifcopenshell_geom_iterator",
                "ifcopenshell_length_unit_setting": 1.0,
                "ifcopenshell_convert_back_units": False,
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

    def _sample_ifc_scene_many_meshes(self, count=501):
        scene = self._sample_ifc_scene()
        template = scene["meshes"][0]
        meshes = []
        for index in range(count):
            mesh = copy.deepcopy(template)
            mesh["uid"] = index + 1
            mesh["properties"]["global_id"] = f"beam-guid-{index + 1}"
            mesh["properties"]["component_ref"] = f"B-{index + 1:03d}"
            base_x = 500000.0 + index
            base_y = 2800000.0 + (index % 11)
            mesh["properties"]["raw_bounds"] = {
                "min_x": base_x,
                "max_x": base_x + 1.0,
                "min_y": base_y,
                "max_y": base_y + 1.0,
                "min_z": 100.0,
                "max_z": 101.0,
            }
            meshes.append(mesh)
        scene["meshes"] = meshes
        scene["stats"]["raw_bounds"] = {
            "min_x": 500000.0,
            "max_x": 500000.0 + count,
            "min_y": 2800000.0,
            "max_y": 2800012.0,
            "min_z": 100.0,
            "max_z": 101.0,
        }
        return scene

    def _sample_ifc_scene_large_coordinate_consistent_many_meshes(self, count=501):
        scene = self._sample_ifc_scene_many_meshes(count=count)
        min_x = 5_000_000.0
        min_y = 2_800_000.0
        min_z = 125.0
        max_x = min_x + count
        max_y = min_y + 12.0
        max_z = min_z + 1.0
        package_origin_render = [
            (min_x + max_x) / 2.0,
            (min_z + max_z) / 2.0,
            (min_y + max_y) / 2.0,
        ]

        def render_local(source_xyz):
            render_world = [source_xyz[0], source_xyz[2], source_xyz[1]]
            return [
                render_world[0] - package_origin_render[0],
                render_world[1] - package_origin_render[1],
                render_world[2] - package_origin_render[2],
            ]

        meshes = []
        for index in range(count):
            base_x = min_x + index
            base_y = min_y + (index % 11)
            bounds = {
                "min_x": base_x,
                "max_x": base_x + 1.0,
                "min_y": base_y,
                "max_y": base_y + 1.0,
                "min_z": min_z,
                "max_z": max_z,
            }
            positions = []
            for source_vertex in [
                [bounds["min_x"], bounds["min_y"], bounds["min_z"]],
                [bounds["max_x"], bounds["min_y"], bounds["min_z"]],
                [bounds["min_x"], bounds["max_y"], bounds["max_z"]],
            ]:
                positions.extend(render_local(source_vertex))
            mesh = copy.deepcopy(scene["meshes"][index])
            mesh["mesh"]["positions"] = positions
            mesh["properties"]["raw_bounds"] = bounds
            meshes.append(mesh)

        scene["meshes"] = meshes
        scene["stats"]["raw_bounds"] = {
            "min_x": min_x,
            "max_x": max_x,
            "min_y": min_y,
            "max_y": max_y,
            "min_z": min_z,
            "max_z": max_z,
        }
        return scene

    def _known_one_meter_ifc_scene(self):
        return {
            "pipes": [],
            "fittings": [],
            "welds": [],
            "supports": [],
            "markers": [],
            "meshes": [
                {
                    "uid": 1,
                    "record_id": 9200,
                    "kind": "IfcBuildingElementProxy",
                    "mesh": {
                        "positions": [
                            -0.5, -0.5, -0.5,
                            0.5, -0.5, -0.5,
                            0.5, 0.5, -0.5,
                            -0.5, 0.5, -0.5,
                            -0.5, -0.5, 0.5,
                            0.5, -0.5, 0.5,
                            0.5, 0.5, 0.5,
                            -0.5, 0.5, 0.5,
                        ],
                        "indices": [
                            0, 1, 2, 0, 2, 3,
                            4, 6, 5, 4, 7, 6,
                            0, 4, 5, 0, 5, 1,
                            1, 5, 6, 1, 6, 2,
                            2, 6, 7, 2, 7, 3,
                            3, 7, 4, 3, 4, 0,
                        ],
                        "color": [0.3, 0.6, 0.8],
                    },
                    "properties": {
                        "ifc_class": "IfcBuildingElementProxy",
                        "global_id": "known-box-guid-1",
                        "component_ref": "KNOWN-1M",
                        "name": "Known 1m Box",
                        "hierarchy_group": "Fixture / IfcBuildingElementProxy",
                        "spatial_path": ["IfcBuilding:Fixture", "IfcBuildingStorey:Validation"],
                        "raw_bounds": {
                            "min_x": 10.0,
                            "max_x": 11.0,
                            "min_y": 20.0,
                            "max_y": 21.0,
                            "min_z": 30.0,
                            "max_z": 31.0,
                        },
                    },
                }
            ],
            "stats": {
                "source_format": "IFC",
                "coordinate_unit": "M",
                "coordinate_scale_to_m": 1.0,
                "display_unit": "m",
                "unit_confidence": "ifcopenshell_geometry_si",
                "ifc_declared_length_units": [
                    {
                        "entity": "IfcSIUnit",
                        "unit_type": "LENGTHUNIT",
                        "name": "METRE",
                        "prefix": "",
                        "display_unit": "m",
                        "scale_to_m": 1.0,
                        "confidence": "ifc_unit_assignment",
                    }
                ],
                "ifc_declared_length_unit": "m",
                "ifc_declared_length_unit_name": "METRE",
                "ifc_declared_length_unit_entity": "IfcSIUnit",
                "ifc_declared_length_scale_to_m": 1.0,
                "ifc_declared_length_confidence": "ifc_unit_assignment",
                "geometry_unit": "M",
                "geometry_scale_to_m": 1.0,
                "geometry_unit_basis": "ifcopenshell_geom_iterator",
                "ifcopenshell_length_unit_setting": 1.0,
                "ifcopenshell_convert_back_units": False,
                "raw_bounds": {
                    "min_x": 10.0,
                    "max_x": 11.0,
                    "min_y": 20.0,
                    "max_y": 21.0,
                    "min_z": 30.0,
                    "max_z": 31.0,
                },
            },
        }

    def _known_one_meter_foot_declared_ifc_scene(self):
        scene = copy.deepcopy(self._known_one_meter_ifc_scene())
        scene["meshes"][0]["properties"]["global_id"] = "known-foot-box-guid-1"
        scene["meshes"][0]["properties"]["component_ref"] = "KNOWN-1M-FT"
        scene["meshes"][0]["properties"]["name"] = "Known 1m Box In Foot Declared IFC"
        scene["stats"].update(
            {
                "ifc_declared_length_units": [
                    {
                        "entity": "IfcConversionBasedUnit",
                        "unit_type": "LENGTHUNIT",
                        "name": "FOOT",
                        "display_unit": "ft",
                        "scale_to_m": 0.3048,
                        "conversion_factor": 0.3048,
                        "conversion_base_unit": {
                            "entity": "IfcSIUnit",
                            "unit_type": "LENGTHUNIT",
                            "name": "METRE",
                            "prefix": "",
                            "display_unit": "m",
                            "scale_to_m": 1.0,
                            "confidence": "ifc_unit_assignment",
                        },
                        "confidence": "ifc_unit_assignment",
                    }
                ],
                "ifc_declared_length_unit": "ft",
                "ifc_declared_length_unit_name": "FOOT",
                "ifc_declared_length_unit_entity": "IfcConversionBasedUnit",
                "ifc_declared_length_scale_to_m": 0.3048,
                "ifc_declared_length_confidence": "ifc_unit_assignment",
            }
        )
        return scene

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
        self.assertIn("process_cpu_time_ms", job.metrics)
        self.assertIn("process_cpu_to_wall_ratio", job.metrics)
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
        self.assertEqual(payload["unit_metadata"]["ifc_declared_length_unit"], "mm")
        self.assertEqual(payload["unit_metadata"]["render_coordinate_unit"], "M")
        self.assertEqual(payload["unit_metadata"]["ifcopenshell_convert_back_units"], False)
        self.assertTrue(payload["unit_warnings"])
        self.assertEqual(source.declared_unit, "MM")
        self.assertEqual(package.metadata["unit_metadata"]["ifc_declared_length_unit"], "mm")
        self.assertEqual(job.metrics["unit_metadata"]["ifc_declared_length_unit"], "mm")
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
    def test_known_one_meter_fixture_preserves_render_scale(self, mock_parse):
        mock_parse.return_value = self._known_one_meter_ifc_scene()
        source = create_source_model_from_upload(
            self.project,
            SimpleUploadedFile(
                "known-1m.ifc",
                b"ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('IFC4'));\nENDSEC;\nDATA;\n#15= IFCSIUNIT(*,.LENGTHUNIT.,$,.METRE.);\nENDSEC;",
            ),
        )

        from .services import run_ifc_geometry_conversion

        job, package = run_ifc_geometry_conversion(source)

        self.assertEqual(job.status, "completed")
        self.assertEqual(package.metadata["unit_metadata"]["render_coordinate_unit"], "M")
        self.assertEqual(package.metadata["unit_metadata"]["ifc_declared_length_unit"], "m")
        self.assertFalse(package.metadata["unit_warnings"])
        self.assertEqual(package.bounds["max_x"] - package.bounds["min_x"], 1.0)
        self.assertEqual(package.bounds["max_y"] - package.bounds["min_y"], 1.0)
        self.assertEqual(package.bounds["max_z"] - package.bounds["min_z"], 1.0)

        payload = json.loads(path_for_storage_key(package.manifest_storage_key).read_text(encoding="utf-8"))
        origin = payload["coordinate_transform"]["rtc_origin_render_xyz"]
        scale = payload["coordinate_transform"]["scale_to_m"]
        positions = payload["meshes"][0]["mesh"]["positions"]
        world_vertices = [
            [
                origin[0] + positions[index],
                origin[1] + positions[index + 1],
                origin[2] + positions[index + 2],
            ]
            for index in range(0, len(positions), 3)
        ]
        reconstructed_source = [
            [vertex[0] / scale, vertex[2] / scale, vertex[1] / scale]
            for vertex in world_vertices
        ]
        for axis in range(3):
            axis_values = [vertex[axis] for vertex in reconstructed_source]
            self.assertEqual(max(axis_values) - min(axis_values), 1.0)

    @patch("plant3d.services.parse_multiple_ifc_uploads")
    def test_foot_declared_known_one_meter_fixture_preserves_render_scale(self, mock_parse):
        mock_parse.return_value = self._known_one_meter_foot_declared_ifc_scene()
        source = create_source_model_from_upload(
            self.project,
            SimpleUploadedFile(
                "known-1m-foot-declared.ifc",
                b"ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('IFC4'));\nENDSEC;\nDATA;\n"
                b"#15= IFCSIUNIT(*,.LENGTHUNIT.,$,.METRE.);\n"
                b"#16= IFCREAL(0.3048);\n"
                b"#17= IFCMEASUREWITHUNIT(#16,#15);\n"
                b"#18= IFCCONVERSIONBASEDUNIT(#17,.LENGTHUNIT.,'FOOT',#17);\n"
                b"ENDSEC;",
            ),
        )

        from .services import run_ifc_geometry_conversion

        job, package = run_ifc_geometry_conversion(source)

        self.assertEqual(job.status, "completed")
        self.assertEqual(package.metadata["unit_metadata"]["render_coordinate_unit"], "M")
        self.assertEqual(package.metadata["unit_metadata"]["render_unit_confidence"], "ifcopenshell_geometry_si")
        self.assertEqual(package.metadata["unit_metadata"]["ifc_declared_length_unit"], "ft")
        self.assertEqual(package.metadata["unit_metadata"]["ifc_declared_length_scale_to_m"], 0.3048)
        self.assertTrue(package.metadata["unit_warnings"])
        self.assertEqual(package.bounds["max_x"] - package.bounds["min_x"], 1.0)
        self.assertEqual(package.bounds["max_y"] - package.bounds["min_y"], 1.0)
        self.assertEqual(package.bounds["max_z"] - package.bounds["min_z"], 1.0)

        payload = json.loads(path_for_storage_key(package.manifest_storage_key).read_text(encoding="utf-8"))
        origin = payload["coordinate_transform"]["rtc_origin_render_xyz"]
        scale = payload["coordinate_transform"]["scale_to_m"]
        positions = payload["meshes"][0]["mesh"]["positions"]
        world_vertices = [
            [
                origin[0] + positions[index],
                origin[1] + positions[index + 1],
                origin[2] + positions[index + 2],
            ]
            for index in range(0, len(positions), 3)
        ]
        reconstructed_source = [
            [vertex[0] / scale, vertex[2] / scale, vertex[1] / scale]
            for vertex in world_vertices
        ]
        for axis in range(3):
            axis_values = [vertex[axis] for vertex in reconstructed_source]
            self.assertEqual(max(axis_values) - min(axis_values), 1.0)

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
    def test_ifc_glb_conversion_writes_binary_tile_and_sidecar(self, mock_parse):
        mock_parse.return_value = self._sample_ifc_scene()
        source = create_source_model_from_upload(
            self.project,
            SimpleUploadedFile(
                "geometry-glb.ifc",
                b"ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('IFC4'));\nENDSEC;\nDATA;\n#15= IFCSIUNIT(*,.LENGTHUNIT.,.MILLI.,.METRE.);\nENDSEC;",
            ),
        )

        from .services import run_ifc_glb_conversion

        job, package = run_ifc_glb_conversion(source)

        self.assertEqual(job.status, "completed")
        self.assertEqual(package.package_format, "GLB")
        self.assertEqual(package.object_count, 1)
        self.assertEqual(package.tile_count, 1)
        self.assertEqual(source.model_objects.count(), 1)
        self.assertEqual(job.metrics["conversion_scope"], "ifc-glb")
        self.assertEqual(job.metrics["render_batch_count"], 1)
        self.assertEqual(job.metrics["feature_count"], 1)
        self.assertIn("process_cpu_time_ms", job.metrics)
        self.assertIn("process_cpu_to_wall_ratio", job.metrics)
        self.assertIn("timings", job.metrics)
        for timing_key in ["source_read_ms", "parse_ms", "glb_build_ms", "tile_write_ms", "db_write_ms"]:
            self.assertIn(timing_key, job.metrics["timings"])
            self.assertGreaterEqual(job.metrics["timings"][timing_key], 0)

        tile = package.tiles.get()
        self.assertEqual(tile.metadata["tile_type"], "ifc-glb")
        self.assertEqual(tile.metadata["feature_id_attribute"], "_FEATURE_ID_0")
        self.assertEqual(tile.rtc_origin, [500000.5, 100.5, 2800000.5])
        self.assertGreater(tile.byte_size, 20)
        glb_bytes = path_for_storage_key(tile.storage_key).read_bytes()
        self.assertEqual(glb_bytes[:4], b"glTF")
        gltf = glb_json_chunk(glb_bytes)
        primitive = gltf["meshes"][0]["primitives"][0]
        self.assertIn("_FEATURE_ID_0", primitive["attributes"])
        feature_accessor = gltf["accessors"][primitive["attributes"]["_FEATURE_ID_0"]]
        self.assertEqual(feature_accessor["componentType"], 5126)

        tileset_path = path_for_storage_key(package.manifest_storage_key)
        tileset = json.loads(tileset_path.read_text(encoding="utf-8"))
        self.assertEqual(tileset["asset"]["version"], "1.1")
        self.assertEqual(tileset["metadata"]["tiling_strategy"], "single-root-tile-spike")
        self.assertEqual(tileset["root"]["extras"]["tile_id"], "geometry-0001")
        self.assertEqual(tileset["root"]["extras"]["feature_id_attribute"], "_FEATURE_ID_0")
        self.assertEqual(tileset["root"]["content"]["uri"], tile.storage_key)
        self.assertEqual(package.metadata["tileset_storage_key"], package.manifest_storage_key)
        self.assertEqual(package.metadata["conversion_timings"], job.metrics["timings"])
        self.assertEqual(
            package.metadata["conversion_resource_metrics"]["process_cpu_time_ms"],
            job.metrics["process_cpu_time_ms"],
        )
        self.assertEqual(job.metrics["tileset_storage_key"], package.manifest_storage_key)

        sidecar_path = path_for_storage_key(tile.metadata["sidecar_storage_key"])
        sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
        self.assertEqual(sidecar["format"], "GLB")
        self.assertEqual(sidecar["mesh_count"], 1)
        self.assertEqual(sidecar["render_batch_count"], 1)
        self.assertEqual(sidecar["feature_id_attribute"], "_FEATURE_ID_0")
        self.assertEqual(sidecar["object_features"][0]["feature_id"], 1)
        self.assertEqual(sidecar["object_features"][0]["stable_id"], "ifc:beam-guid-1")
        self.assertEqual(sidecar["object_spans"][0]["feature_id"], 1)
        self.assertEqual(sidecar["object_spans"][0]["stable_id"], "ifc:beam-guid-1")
        self.assertEqual(sidecar["gltf_axis_convention"]["up_axis"], "Y")
        self.assertEqual(sidecar["gltf_axis_convention"]["source_to_buffer_axis_order"], ["x", "z", "y"])
        self.assertFalse(sidecar["gltf_axis_convention"]["root_transform_required"])
        self.assertEqual(sidecar["metadata"]["gltf_axis_convention"]["buffer_frame"], "render_xyz_m")
        self.assertEqual(sidecar["unit_metadata"]["ifc_declared_length_unit"], "mm")

    @patch("plant3d.services.parse_multiple_ifc_uploads")
    def test_ifc_glb_guidless_feature_stable_id_matches_indexed_object(self, mock_parse):
        scene = self._sample_ifc_scene()
        scene["meshes"][0]["properties"]["global_id"] = ""
        mock_parse.return_value = scene
        source = create_source_model_from_upload(
            self.project,
            SimpleUploadedFile(
                "guidless-glb.ifc",
                b"ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('IFC4'));\nENDSEC;",
            ),
        )

        from .services import run_ifc_glb_conversion

        _, package = run_ifc_glb_conversion(source)

        indexed_object = source.model_objects.get()
        tile = package.tiles.get()
        sidecar_path = path_for_storage_key(tile.metadata["sidecar_storage_key"])
        sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
        self.assertEqual(indexed_object.stable_id, f"ifc:{source.pk}:mesh:1")
        self.assertEqual(sidecar["object_features"][0]["stable_id"], indexed_object.stable_id)
        self.assertEqual(sidecar["object_spans"][0]["stable_id"], indexed_object.stable_id)

    @patch("plant3d.services.parse_multiple_ifc_uploads")
    def test_ifc_glb_conversion_records_meshopt_hook_when_configured(self, mock_parse):
        mock_parse.return_value = self._sample_ifc_scene()
        source = create_source_model_from_upload(
            self.project,
            SimpleUploadedFile(
                "meshopt-glb.ifc",
                b"ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('IFC4'));\nENDSEC;",
            ),
        )

        with tempfile.TemporaryDirectory() as tempdir:
            fake_gltfpack = os.path.join(tempdir, "fake_gltfpack")
            with open(fake_gltfpack, "w", encoding="utf-8") as handle:
                handle.write(
                    "#!/usr/bin/env python3\n"
                    "import shutil, sys\n"
                    "input_path = sys.argv[sys.argv.index('-i') + 1]\n"
                    "output_path = sys.argv[sys.argv.index('-o') + 1]\n"
                    "shutil.copyfile(input_path, output_path)\n"
                )
            os.chmod(fake_gltfpack, 0o755)

            from .services import run_ifc_glb_conversion

            with override_settings(PLANT3D_GLTFPACK_BIN=fake_gltfpack, PLANT3D_GLTFPACK_ARGS=[]):
                job, package = run_ifc_glb_conversion(source)

        self.assertEqual(job.status, "completed")
        self.assertTrue(package.metadata["meshopt_compression"]["enabled"])
        self.assertEqual(package.metadata["meshopt_compression"]["status"], "completed")
        tile = package.tiles.get()
        self.assertEqual(tile.metadata["compression"]["status"], "completed")
        self.assertEqual(tile.metadata["compression"]["feature_id_validation"]["status"], "passed")
        sidecar = json.loads(path_for_storage_key(tile.metadata["sidecar_storage_key"]).read_text(encoding="utf-8"))
        self.assertEqual(sidecar["compression"]["status"], "completed")
        self.assertEqual(sidecar["compression"]["feature_id_validation"]["status"], "passed")
        self.assertEqual(path_for_storage_key(tile.storage_key).read_bytes()[:4], b"glTF")

    @patch("plant3d.services.parse_multiple_ifc_uploads")
    def test_ifc_glb_conversion_rejects_meshopt_when_feature_ids_cannot_be_validated(self, mock_parse):
        mock_parse.return_value = self._sample_ifc_scene()
        source = create_source_model_from_upload(
            self.project,
            SimpleUploadedFile(
                "meshopt-invalid-feature-glb.ifc",
                b"ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('IFC4'));\nENDSEC;",
            ),
        )

        with tempfile.TemporaryDirectory() as tempdir:
            fake_gltfpack = os.path.join(tempdir, "fake_invalid_gltfpack")
            with open(fake_gltfpack, "w", encoding="utf-8") as handle:
                handle.write(
                    "#!/usr/bin/env python3\n"
                    "import sys\n"
                    "output_path = sys.argv[sys.argv.index('-o') + 1]\n"
                    "open(output_path, 'wb').write(b'not a valid glb')\n"
                )
            os.chmod(fake_gltfpack, 0o755)

            from .services import run_ifc_glb_conversion

            with override_settings(PLANT3D_GLTFPACK_BIN=fake_gltfpack, PLANT3D_GLTFPACK_ARGS=[]):
                job, package = run_ifc_glb_conversion(source)

        self.assertEqual(job.status, "completed")
        self.assertEqual(package.metadata["meshopt_compression"]["status"], "rejected_feature_id_validation")
        tile = package.tiles.get()
        compression = tile.metadata["compression"]
        self.assertEqual(compression["status"], "rejected_feature_id_validation")
        self.assertFalse(compression["feature_id_validation"]["valid"])
        self.assertEqual(compression["output_bytes"], compression["input_bytes"])
        self.assertNotEqual(compression["compressed_output_bytes"], compression["output_bytes"])
        self.assertEqual(path_for_storage_key(tile.storage_key).read_bytes()[:4], b"glTF")

        sidecar = json.loads(path_for_storage_key(tile.metadata["sidecar_storage_key"]).read_text(encoding="utf-8"))
        self.assertEqual(sidecar["compression"]["status"], "rejected_feature_id_validation")
        self.assertFalse(sidecar["compression"]["feature_id_validation"]["valid"])

        stdout = io.StringIO()
        call_command("measure_plant3d_package", str(package.pk), stdout=stdout)
        output = stdout.getvalue()
        self.assertIn("status=rejected_feature_id_validation", output)
        self.assertIn("rejected_tiles=1", output)

    @patch("plant3d.services.parse_multiple_ifc_uploads")
    def test_measure_package_command_reports_meshopt_status(self, mock_parse):
        mock_parse.return_value = self._sample_ifc_scene()
        source = create_source_model_from_upload(
            self.project,
            SimpleUploadedFile(
                "measure-meshopt-glb.ifc",
                b"ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('IFC4'));\nENDSEC;",
            ),
        )

        with tempfile.TemporaryDirectory() as tempdir:
            fake_gltfpack = os.path.join(tempdir, "fake_gltfpack")
            with open(fake_gltfpack, "w", encoding="utf-8") as handle:
                handle.write(
                    "#!/usr/bin/env python3\n"
                    "import shutil, sys\n"
                    "input_path = sys.argv[sys.argv.index('-i') + 1]\n"
                    "output_path = sys.argv[sys.argv.index('-o') + 1]\n"
                    "shutil.copyfile(input_path, output_path)\n"
                )
            os.chmod(fake_gltfpack, 0o755)

            from .services import run_ifc_glb_conversion

            with override_settings(PLANT3D_GLTFPACK_BIN=fake_gltfpack, PLANT3D_GLTFPACK_ARGS=[]):
                _, package = run_ifc_glb_conversion(source)

        stdout = io.StringIO()
        call_command("measure_plant3d_package", str(package.pk), stdout=stdout)

        output = stdout.getvalue()
        self.assertIn(f"Package {package.pk}", output)
        self.assertIn("meshopt: status=completed", output)
        self.assertIn("completed_tiles=1", output)
        self.assertIn("rejected_tiles=0", output)
        self.assertIn("ratio_output_over_input=1.0000", output)
        self.assertIn("saved_pct=0.0%", output)
        self.assertIn("timings:", output)
        self.assertIn("resources:", output)
        self.assertIn("cpu_wall_ratio=", output)
        self.assertIn("parse_ms=", output)
        self.assertIn("timing decision:", output)
        self.assertIn("dominant=", output)
        self.assertIn("Summary meshopt:", output)
        self.assertIn("Summary timings:", output)
        self.assertIn("Summary resources:", output)

        json_stdout = io.StringIO()
        call_command("measure_plant3d_package", str(package.pk), json=True, stdout=json_stdout)
        payload = json.loads(json_stdout.getvalue())
        self.assertEqual(payload["packages"][0]["package_id"], package.pk)
        self.assertEqual(payload["packages"][0]["compression"]["status"], "completed")
        self.assertEqual(payload["packages"][0]["compression"]["completed_tiles"], 1)
        self.assertEqual(payload["summary"]["packages"], 1)
        self.assertEqual(payload["summary"]["compression"]["completed_tiles"], 1)
        self.assertEqual(payload["summary"]["compression"]["rejected_tiles"], 0)
        self.assertEqual(payload["summary"]["compression"]["saved_percent"], 0.0)
        self.assertIn("parse_ms", payload["packages"][0]["conversion_timings"])
        self.assertIn("conversion_timing_breakdown", payload["packages"][0])
        self.assertIn("conversion_resource_metrics", payload["packages"][0])
        self.assertIn("process_cpu_time_ms", payload["packages"][0]["conversion_resource_metrics"])
        self.assertGreaterEqual(payload["packages"][0]["conversion_timing_breakdown"]["total_ms"], 0)
        self.assertIn("dominant_label", payload["packages"][0]["conversion_timing_breakdown"])
        self.assertIn("conversion_timing_breakdown", payload["summary"])
        self.assertIn("conversion_resource_metrics", payload["summary"])

    @patch("plant3d.services.parse_multiple_ifc_uploads")
    def test_ifc_glb_conversion_endpoint_queues_glb_job(self, mock_parse):
        mock_parse.return_value = self._sample_ifc_scene()
        user = get_user_model().objects.create_user(username="plant3d-glb-user", password="pw")
        assign_project(user, self.project)
        self.client.force_login(user)
        source = create_source_model_from_upload(
            self.project,
            SimpleUploadedFile("endpoint-glb.ifc", b"ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('IFC4'));\nENDSEC;"),
        )

        response = self.client.post(reverse("plant3d_source_ifc_glb_convert", args=[source.pk]))

        self.assertEqual(response.status_code, 202)
        payload = response.json()
        self.assertEqual(payload["job"]["job_type"], "render_package")
        job = ConversionJob.objects.get(pk=payload["job"]["id"])
        self.assertEqual(job.tool_name, "plant3d.ifc-glb")

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

    @patch("plant3d.services.parse_multiple_ifc_uploads")
    def test_management_command_processes_queued_ifc_glb_job(self, mock_parse):
        mock_parse.return_value = self._sample_ifc_scene()
        source = create_source_model_from_upload(
            self.project,
            SimpleUploadedFile("queued-glb.ifc", b"ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('IFC4'));\nENDSEC;"),
        )
        job = queue_ifc_glb_conversion(source)

        call_command("process_plant3d_job", str(job.pk), verbosity=0)

        job.refresh_from_db()
        self.assertEqual(job.status, "completed")
        self.assertEqual(job.render_packages.get().package_format, "GLB")

    def test_queue_prunes_old_terminal_conversion_jobs_per_source(self):
        source = create_source_model_from_upload(
            self.project,
            SimpleUploadedFile("job-prune.ifc", b"ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('IFC4'));\nENDSEC;"),
        )
        for index in range(14):
            ConversionJob.objects.create(
                source_model=source,
                job_type="metadata_index",
                status="completed",
                progress_percent=100,
                tool_name=f"old-{index}",
            )

        job = queue_metadata_conversion(source)

        self.assertEqual(job.status, "queued")
        self.assertEqual(source.conversion_jobs.filter(status="completed").count(), 12)
        self.assertEqual(source.conversion_jobs.count(), 13)

    @patch("plant3d.services.parse_multiple_ifc_uploads")
    def test_repeated_glb_conversion_keeps_latest_render_package_row(self, mock_parse):
        mock_parse.return_value = self._sample_ifc_scene()
        source = create_source_model_from_upload(
            self.project,
            SimpleUploadedFile("package-prune.ifc", b"ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('IFC4'));\nENDSEC;"),
        )

        from .services import run_ifc_glb_conversion

        _job_1, package_1 = run_ifc_glb_conversion(source)
        _job_2, package_2 = run_ifc_glb_conversion(source)

        self.assertFalse(RenderPackage.objects.filter(pk=package_1.pk).exists())
        self.assertTrue(RenderPackage.objects.filter(pk=package_2.pk).exists())
        self.assertEqual(source.render_packages.filter(package_format="GLB").count(), 1)

    @patch("plant3d.management.commands.process_plant3d_job.gc.collect")
    @patch("plant3d.services.parse_multiple_ifc_uploads")
    def test_management_command_collects_garbage_after_job(self, mock_parse, mock_collect):
        mock_parse.return_value = self._sample_ifc_scene()
        source = create_source_model_from_upload(
            self.project,
            SimpleUploadedFile("queued-glb-gc.ifc", b"ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('IFC4'));\nENDSEC;"),
        )
        job = queue_ifc_glb_conversion(source)

        call_command("process_plant3d_job", str(job.pk), verbosity=0)

        job.refresh_from_db()
        self.assertEqual(job.status, "completed")
        mock_collect.assert_called()

    @patch("plant3d.parsers.ifc.effective_cpu_count", return_value=5)
    @patch("plant3d.parsers.ifc.effective_memory_limit_bytes", return_value=None)
    @patch("plant3d.services.parse_multiple_ifc_uploads")
    def test_management_command_parser_threads_option_overrides_worker_run(
        self,
        mock_parse,
        _mock_memory_limit,
        _mock_cpu_count,
    ):
        source = create_source_model_from_upload(
            self.project,
            SimpleUploadedFile("queued-glb-auto.ifc", b"ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('IFC4'));\nENDSEC;"),
        )
        job = queue_ifc_glb_conversion(source)

        def parse_side_effect(*args, **kwargs):
            thread_count, source_label = configured_ifc_iterator_thread_count()
            self.assertEqual(thread_count, 4)
            self.assertEqual(source_label, "env")
            return self._sample_ifc_scene()

        mock_parse.side_effect = parse_side_effect

        call_command("process_plant3d_job", str(job.pk), parser_threads="auto", verbosity=0)

        job.refresh_from_db()
        self.assertEqual(job.status, "completed")
        self.assertEqual(job.render_packages.get().package_format, "GLB")

    @patch("plant3d.parsers.ifc.effective_cpu_count", return_value=8)
    @patch("plant3d.parsers.ifc.effective_memory_limit_bytes", return_value=None)
    @patch("plant3d.services.parse_multiple_ifc_uploads")
    def test_management_command_parser_thread_cap_limits_auto_threads(
        self,
        mock_parse,
        _mock_memory_limit,
        _mock_cpu_count,
    ):
        source = create_source_model_from_upload(
            self.project,
            SimpleUploadedFile("queued-glb-capped.ifc", b"ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('IFC4'));\nENDSEC;"),
        )
        job = queue_ifc_glb_conversion(source)

        def parse_side_effect(*args, **kwargs):
            thread_count, source_label = configured_ifc_iterator_thread_count()
            self.assertEqual(thread_count, 2)
            self.assertEqual(source_label, "env")
            return self._sample_ifc_scene()

        mock_parse.side_effect = parse_side_effect

        call_command("process_plant3d_job", str(job.pk), parser_threads="auto", parser_thread_cap="2", verbosity=0)

        job.refresh_from_db()
        self.assertEqual(job.status, "completed")
        self.assertEqual(job.render_packages.get().package_format, "GLB")

    def test_management_command_rejects_invalid_parser_threads_option(self):
        with self.assertRaises(CommandError):
            call_command("process_plant3d_job", next=True, parser_threads="not-a-thread-count", verbosity=0)

    @patch("plant3d.services.parse_multiple_ifc_uploads")
    def test_management_command_watch_claims_and_processes_queued_job(self, mock_parse):
        mock_parse.return_value = self._sample_ifc_scene()
        source = create_source_model_from_upload(
            self.project,
            SimpleUploadedFile("watch-glb.ifc", b"ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('IFC4'));\nENDSEC;"),
        )
        job = queue_ifc_glb_conversion(source)

        call_command(
            "process_plant3d_job",
            watch=True,
            poll_interval=0,
            max_jobs=1,
            verbosity=0,
        )

        job.refresh_from_db()
        self.assertEqual(job.status, "completed")
        self.assertEqual(job.render_packages.get().package_format, "GLB")
        self.assertIn("Parsing IFC geometry", job.log)
        self.assertEqual(job.metrics["stage"], "completed")

    @patch("plant3d.services.parse_multiple_ifc_uploads")
    def test_ifc_glb_job_exposes_stage_while_parser_runs(self, mock_parse):
        source = create_source_model_from_upload(
            self.project,
            SimpleUploadedFile("stage-glb.ifc", b"ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('IFC4'));\nENDSEC;"),
        )
        job = queue_ifc_glb_conversion(source)

        def parse_side_effect(*args, **kwargs):
            running_job = ConversionJob.objects.get(pk=job.pk)
            self.assertEqual(running_job.status, "running")
            self.assertEqual(running_job.progress_percent, 15)
            self.assertIn("Parsing IFC geometry", running_job.metrics["stage"])
            return self._sample_ifc_scene()

        mock_parse.side_effect = parse_side_effect

        call_command("process_plant3d_job", str(job.pk), verbosity=0)

        job.refresh_from_db()
        self.assertEqual(job.status, "completed")
        self.assertEqual(job.metrics["stage"], "completed")

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
        self.assertIn("process_plant3d_job --watch", payload["worker_hint"])
        self.assertIn("--parser-threads auto", payload["worker_hint"])
        self.assertEqual(payload["package"]["object_count"], 1)
        self.assertIn("/plant3d/packages/", payload["package"]["viewer_url"])
        self.assertIn("/plant3d/packages/", payload["package"]["json_url"])
        self.assertTrue(payload["timing_summary"])
        timing_keys = [row["key"] for row in payload["timing_summary"]]
        self.assertIn("parse_ms", timing_keys)
        self.assertIn("tile_write_ms", timing_keys)

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
        self.assertIn("private", package_response["Cache-Control"])
        self.assertIn("immutable", package_response["Cache-Control"])
        self.assertTrue(package_response["ETag"].startswith('"'))
        cached_package_response = self.client.get(
            reverse("plant3d_package_json", args=[package.pk]),
            HTTP_IF_NONE_MATCH=package_response["ETag"],
        )
        self.assertEqual(cached_package_response.status_code, 304)
        self.assertEqual(cached_package_response["ETag"], package_response["ETag"])
        package_payload = package_response.json()
        self.assertEqual(package_payload["object_count"], 1)
        self.assertEqual(package_payload["tile_count"], 1)
        self.assertEqual(len(package_payload["tiles"]), 1)
        self.assertEqual(package_payload["tiles"][0]["rtc_origin"], [500000.5, 100.5, 2800000.5])
        self.assertEqual(len(package_payload["objects"]), 1)
        self.assertEqual(package_payload["objects"][0]["stable_id"], "ifc:beam-guid-1")
        self.assertEqual(package_payload["objects"][0]["selection_summary"]["display_label"], "B-001")
        self.assertEqual(package_payload["objects"][0]["selection_summary"]["hierarchy_group"], "Level 1 / IfcBeam")
        self.assertIn("/plant3d/objects/", package_payload["objects"][0]["url"])
        self.assertIn("/plant3d/tiles/", package_payload["tiles"][0]["url"])

        object_id = source.model_objects.get().pk
        object_response = self.client.get(reverse("plant3d_model_object_json", args=[object_id]))
        self.assertEqual(object_response.status_code, 200)
        object_payload = object_response.json()
        self.assertEqual(object_payload["stable_id"], "ifc:beam-guid-1")
        self.assertEqual(object_payload["metadata"]["name"], "Beam 001")
        self.assertEqual(object_payload["selection_summary"]["display_label"], "B-001")
        self.assertEqual(object_payload["selection_summary"]["name"], "Beam 001")
        self.assertEqual(object_payload["selection_summary"]["dimensions"], {"x": 1.0, "y": 1.0, "z": 1.0})
        self.assertEqual(object_payload["selection_summary"]["dimension_unit"], "m")
        self.assertEqual(object_payload["selection_summary"]["dimension_frame"], "source_xyz")
        self.assertEqual(
            object_payload["selection_summary"]["spatial_path"],
            ["IfcBuilding:Main", "IfcBuildingStorey:Level 1"],
        )

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
    def test_glb_package_api_exposes_sidecar_and_blob_urls(self, mock_parse):
        mock_parse.return_value = self._sample_ifc_scene()
        user = get_user_model().objects.create_user(username="plant3d-glb-api-user", password="pw")
        assign_project(user, self.project)
        self.client.force_login(user)
        source = create_source_model_from_upload(
            self.project,
            SimpleUploadedFile("api-glb.ifc", b"ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('IFC4'));\nENDSEC;"),
        )

        from .services import run_ifc_glb_conversion

        _, package = run_ifc_glb_conversion(source)
        package_response = self.client.get(reverse("plant3d_package_json", args=[package.pk]))

        self.assertEqual(package_response.status_code, 200)
        package_payload = package_response.json()
        self.assertEqual(package_payload["package_format"], "GLB")
        self.assertEqual(package_payload["manifest_storage_key"], package.manifest_storage_key)
        self.assertEqual(package_payload["tileset"]["asset"]["version"], "1.1")
        self.assertEqual(package_payload["tileset"]["root"]["content"]["url"], package_payload["tiles"][0]["blob_url"])
        self.assertEqual(package_payload["tileset"]["root"]["extras"]["metadata_url"], package_payload["tiles"][0]["metadata_url"])
        self.assertEqual(package_payload["tileset"]["root"]["extras"]["feature_id_attribute"], "_FEATURE_ID_0")
        self.assertEqual(package_payload["objects"][0]["stable_id"], "ifc:beam-guid-1")
        self.assertIn("/plant3d/objects/", package_payload["objects"][0]["url"])
        self.assertIn("/plant3d/tiles/", package_payload["tiles"][0]["metadata_url"])
        self.assertIn("/plant3d/tiles/", package_payload["tiles"][0]["blob_url"])

        tile = package.tiles.get()
        sidecar_response = self.client.get(reverse("plant3d_tile_json", args=[tile.pk]))
        self.assertEqual(sidecar_response.status_code, 200)
        self.assertIn("immutable", sidecar_response["Cache-Control"])
        cached_sidecar_response = self.client.get(
            reverse("plant3d_tile_json", args=[tile.pk]),
            HTTP_IF_NONE_MATCH=sidecar_response["ETag"],
        )
        self.assertEqual(cached_sidecar_response.status_code, 304)
        sidecar_payload = sidecar_response.json()
        self.assertEqual(sidecar_payload["format"], "GLB")
        self.assertEqual(sidecar_payload["object_features"][0]["feature_id"], 1)
        self.assertEqual(sidecar_payload["object_features"][0]["stable_id"], package_payload["objects"][0]["stable_id"])

        blob_response = self.client.get(reverse("plant3d_tile_blob", args=[tile.pk]))
        self.assertEqual(blob_response.status_code, 200)
        self.assertEqual(blob_response["Content-Type"], "model/gltf-binary")
        self.assertIn("immutable", blob_response["Cache-Control"])
        cached_blob_response = self.client.get(
            reverse("plant3d_tile_blob", args=[tile.pk]),
            HTTP_IF_NONE_MATCH=blob_response["ETag"],
        )
        self.assertEqual(cached_blob_response.status_code, 304)
        self.assertEqual(blob_response.content[:4], b"glTF")

    @patch("plant3d.services.parse_multiple_ifc_uploads")
    def test_ifc_glb_conversion_splits_large_scene_into_spatial_child_tiles(self, mock_parse):
        mock_parse.return_value = self._sample_ifc_scene_many_meshes()
        user = get_user_model().objects.create_user(username="plant3d-glb-tiles-user", password="pw")
        assign_project(user, self.project)
        self.client.force_login(user)
        source = create_source_model_from_upload(
            self.project,
            SimpleUploadedFile("multi-tile-glb.ifc", b"ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('IFC4'));\nENDSEC;"),
        )

        from .services import run_ifc_glb_conversion

        job, package = run_ifc_glb_conversion(source)

        self.assertEqual(job.status, "completed")
        self.assertGreater(package.tile_count, 1)
        self.assertEqual(package.tiles.count(), package.tile_count)
        self.assertEqual(source.model_objects.count(), 501)
        self.assertEqual(job.metrics["tiling_strategy"], "source-bounds-grid")
        self.assertEqual(job.metrics["tile_count"], package.tile_count)
        self.assertEqual(len(job.metrics["tile_ids"]), package.tile_count)

        tileset = json.loads(path_for_storage_key(package.manifest_storage_key).read_text(encoding="utf-8"))
        self.assertEqual(tileset["metadata"]["tiling_strategy"], "source-bounds-grid")
        self.assertEqual(len(tileset["root"]["children"]), package.tile_count)
        self.assertNotIn("content", tileset["root"])

        package_response = self.client.get(reverse("plant3d_package_json", args=[package.pk]))
        self.assertEqual(package_response.status_code, 200)
        package_payload = package_response.json()
        children = package_payload["tileset"]["root"]["children"]
        self.assertEqual(len(children), package.tile_count)
        self.assertTrue(all(child["content"]["url"].startswith("/plant3d/tiles/") for child in children))
        self.assertTrue(all(child["extras"]["metadata_url"].startswith("/plant3d/tiles/") for child in children))

        feature_ids = []
        for tile in package.tiles.order_by("sequence"):
            sidecar = json.loads(path_for_storage_key(tile.metadata["sidecar_storage_key"]).read_text(encoding="utf-8"))
            feature_ids.extend(feature["feature_id"] for feature in sidecar["object_features"])
            self.assertEqual(tile.object_count, len(sidecar["object_features"]))
            self.assertEqual(tile.metadata["package_rtc_origin_render_xyz"], package.metadata["rtc_origin_render_xyz"])
            self.assertGreater(tile.rtc_origin[0], 499000)
            self.assertGreater(tile.rtc_origin[2], 2799000)
            glb_bytes = path_for_storage_key(tile.storage_key).read_bytes()
            gltf = glb_json_chunk(glb_bytes)
            primitive = gltf["meshes"][0]["primitives"][0]
            positions = glb_accessor_floats(glb_bytes, primitive["attributes"]["POSITION"])
            self.assertLess(max(abs(value) for value in positions), 400)
        self.assertEqual(len(feature_ids), 501)
        self.assertEqual(len(feature_ids), len(set(feature_ids)))

    @patch("plant3d.services.parse_multiple_ifc_uploads")
    def test_ifc_glb_child_tiles_keep_plant_global_coordinates_out_of_glb_positions(self, mock_parse):
        mock_parse.return_value = self._sample_ifc_scene_large_coordinate_consistent_many_meshes()
        source = create_source_model_from_upload(
            self.project,
            SimpleUploadedFile("plant-global-glb.ifc", b"ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('IFC4'));\nENDSEC;"),
        )

        from .services import run_ifc_glb_conversion

        job, package = run_ifc_glb_conversion(source)

        self.assertEqual(job.status, "completed")
        self.assertGreater(package.tile_count, 1)
        self.assertGreater(package.metadata["rtc_origin_render_xyz"][0], 4_999_000)
        self.assertLess(package.metadata["rtc_origin_render_xyz"][1], 200)
        self.assertGreater(package.metadata["rtc_origin_render_xyz"][2], 2_799_000)

        for tile in package.tiles.order_by("sequence"):
            sidecar = json.loads(path_for_storage_key(tile.metadata["sidecar_storage_key"]).read_text(encoding="utf-8"))
            raw_bounds = sidecar["raw_bounds"]
            rtc_origin = sidecar["rtc_origin_render_xyz"]
            self.assertGreater(rtc_origin[0], 4_999_000)
            self.assertLess(rtc_origin[1], 200)
            self.assertGreater(rtc_origin[2], 2_799_000)

            glb_bytes = path_for_storage_key(tile.storage_key).read_bytes()
            gltf = glb_json_chunk(glb_bytes)
            primitive = gltf["meshes"][0]["primitives"][0]
            positions = glb_accessor_floats(glb_bytes, primitive["attributes"]["POSITION"])
            local_axis_max = [
                max(abs(positions[index]) for index in range(axis, len(positions), 3))
                for axis in range(3)
            ]
            self.assertLessEqual(local_axis_max[0], (raw_bounds["max_x"] - raw_bounds["min_x"]) / 2.0 + 0.01)
            self.assertLessEqual(local_axis_max[1], (raw_bounds["max_z"] - raw_bounds["min_z"]) / 2.0 + 0.01)
            self.assertLessEqual(local_axis_max[2], (raw_bounds["max_y"] - raw_bounds["min_y"]) / 2.0 + 0.01)

            for cursor in range(0, min(len(positions), 30), 3):
                render_world = [
                    rtc_origin[0] + positions[cursor],
                    rtc_origin[1] + positions[cursor + 1],
                    rtc_origin[2] + positions[cursor + 2],
                ]
                reconstructed_source = [
                    render_world[0],
                    render_world[2],
                    render_world[1],
                ]
                self.assertGreaterEqual(reconstructed_source[0], raw_bounds["min_x"] - 0.01)
                self.assertLessEqual(reconstructed_source[0], raw_bounds["max_x"] + 0.01)
                self.assertGreaterEqual(reconstructed_source[1], raw_bounds["min_y"] - 0.01)
                self.assertLessEqual(reconstructed_source[1], raw_bounds["max_y"] + 0.01)
                self.assertGreaterEqual(reconstructed_source[2], raw_bounds["min_z"] - 0.01)
                self.assertLessEqual(reconstructed_source[2], raw_bounds["max_z"] + 0.01)

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
        self.assertContains(response, "fitSelectionBtn")
        self.assertContains(response, "clearSelectionBtn")
        self.assertContains(response, "measureToggleBtn")
        self.assertContains(response, "vertexSnapToggleBtn")
        self.assertContains(response, "scaleToggleBtn")
        self.assertContains(response, "measurementHud")
        self.assertContains(response, "viewerContextMenu")
        self.assertContains(response, "data-context-action=\"delete-draft\"")
        self.assertContains(response, "scaleHud")
        self.assertContains(response, "viewerQuickTools")
        self.assertContains(response, "quickTopBtn")
        self.assertContains(response, "quickSideBtn")
        self.assertContains(response, "plotPlanInput")
        self.assertContains(response, "plotPlanOpacity")
        self.assertContains(response, "plotPlanClearBtn")
        self.assertContains(response, "navpanel-width-toggle")
        self.assertContains(response, "sidepanel-width-toggle")
        self.assertContains(response, "navpanel-toggle")
        self.assertContains(response, "navpanel-reopen")
        self.assertContains(response, "hierarchy-content")
        self.assertContains(response, "<summary>Assets</summary>", html=True)
        self.assertContains(response, "Model Hierarchy")
        self.assertContains(response, "Reference Layers")
        self.assertContains(response, "searchFocusBtn")
        self.assertContains(response, "Filter List")
        self.assertNotContains(response, "Check All / Uncheck All")
        self.assertContains(response, "ehtToolPalette")
        self.assertContains(response, "ehtDraftList")
        self.assertContains(response, "data-eht-tool=\"distribution_board\"")
        self.assertContains(response, "data-eht-tool=\"cold_cable\"")
        self.assertContains(response, "ehtSaveLayerBtn")
        self.assertContains(response, "p3d-viewer-toolbar-group")
        self.assertContains(response, "sidepanel-toggle")
        self.assertContains(response, "sidepanel-reopen")
        self.assertContains(response, "20260703_context1")

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
        self.assertContains(response, "Process 3D Model")
        self.assertContains(response, "Save Geometry Case")
        self.assertContains(response, "Delete Source Model")
        self.assertContains(response, "Working upload")
        self.assertContains(response, "Developer actions")
        self.assertContains(response, "Queue IFC JSON Debug Conversion")
        self.assertContains(response, 'data-watch-job')
        self.assertContains(response, 'plant3d/js/source_detail.js')
        self.assertContains(response, "20260702_actions1")

    @patch("plant3d.services.parse_multiple_ifc_uploads")
    def test_source_detail_page_shows_conversion_timing_summary(self, mock_parse):
        mock_parse.return_value = self._sample_ifc_scene()
        user = get_user_model().objects.create_user(username="plant3d-source-timing-user", password="pw")
        assign_project(user, self.project)
        self.client.force_login(user)
        source = create_source_model_from_upload(
            self.project,
            SimpleUploadedFile("detail-timing.ifc", b"ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('IFC4'));\nENDSEC;"),
        )

        from .services import run_ifc_geometry_conversion

        run_ifc_geometry_conversion(source)
        response = self.client.get(reverse("plant3d_source_detail", args=[source.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Total conversion:")
        self.assertContains(response, "Timings:")
        self.assertContains(response, "IFC parse=")
        self.assertContains(response, "tile write=")

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
