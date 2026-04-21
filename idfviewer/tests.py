from django.test import SimpleTestCase

from .parser import _collect_candidate_records, _filter_scene, _normalize_points
from .pcf_parser import _component_to_scene_items, _normalize_scene as _normalize_pcf_scene
from .pcf_parser import _parse_document, _strip_internal as _strip_pcf_internal


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
            PIPELINE-REFERENCE   A09-01-LS0051-01
                PIPING-SPEC   13470
                INSULATION-SPEC   E  60 mm
                TRACING-SPEC   ELECTRIC
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
