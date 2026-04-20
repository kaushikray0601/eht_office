from django.test import SimpleTestCase

from .parser import _collect_candidate_records, _filter_scene, _normalize_points


def _parse_scene(text):
    scene = _collect_candidate_records(text, "sample.idf")
    scene = _filter_scene(scene)
    return _normalize_points(scene)


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
