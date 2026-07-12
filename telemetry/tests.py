import json
import uuid
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from eht.models import ManagedProject, ProjectData

from .models import SuggestionEvent


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


def json_body(payload):
    return json.dumps(payload)


class SuggestionTelemetryApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="telemetry-user", password="pw")
        self.project = create_project("TEL-P1")
        assign_project(self.user, self.project)
        self.client.force_login(self.user)

    def test_events_endpoint_stores_batch_with_project_access_and_uuid_keys(self):
        event_key = uuid.uuid4()

        response = self.client.post(
            reverse("telemetry:events"),
            data=json_body(
                {
                    "events": [
                        {
                            "key": str(event_key),
                            "project_id": self.project.proj_id,
                            "owner_module": "raceway",
                            "suggestion_code": "raceway.graph.near_miss_endpoint",
                            "action": "shown",
                            "context": {
                                "run_id": 42,
                                "run_key": str(uuid.uuid4()),
                                "node_id": 1001,
                                "node_keys": [str(uuid.uuid4())],
                                "values": {"distance_m": 0.05, "layer_id": 91},
                            },
                            "action_detail": {"source_model_id": 55, "elapsed_ms": 25},
                            "client": "raceway-overlay@20260712_raceway20",
                        }
                    ]
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["accepted"], 1)
        event = SuggestionEvent.objects.get()
        self.assertEqual(event.key, event_key)
        self.assertEqual(event.project_id, self.project.proj_id)
        self.assertEqual(event.user, self.user)
        self.assertEqual(event.owner_module, "raceway")
        self.assertEqual(event.suggestion_code, "raceway.graph.near_miss_endpoint")
        self.assertEqual(event.action, SuggestionEvent.ACTION_SHOWN)
        self.assertIn("run_key", event.context)
        self.assertIn("node_keys", event.context)
        self.assertNotIn("run_id", event.context)
        self.assertNotIn("node_id", event.context)
        self.assertNotIn("layer_id", event.context["values"])
        self.assertNotIn("source_model_id", event.action_detail)

    def test_events_endpoint_rejects_inaccessible_project(self):
        other_project = create_project("TEL-HIDDEN")

        response = self.client.post(
            reverse("telemetry:events"),
            data=json_body(
                [
                    {
                        "project_id": other_project.proj_id,
                        "owner_module": "raceway",
                        "suggestion_code": "raceway.ortho.axis_lock",
                        "action": "shown",
                    }
                ]
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(SuggestionEvent.objects.exists())

    def test_events_endpoint_requires_valid_action(self):
        response = self.client.post(
            reverse("telemetry:events"),
            data=json_body(
                {
                    "events": [
                        {
                            "project_id": self.project.proj_id,
                            "owner_module": "raceway",
                            "suggestion_code": "raceway.ortho.axis_lock",
                            "action": "surprised",
                        }
                    ]
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("action", response.json()["errors"])
        self.assertFalse(SuggestionEvent.objects.exists())

    def test_events_endpoint_caps_batch_size(self):
        events = [
            {
                "project_id": self.project.proj_id,
                "owner_module": "raceway",
                "suggestion_code": "raceway.ortho.axis_lock",
                "action": "shown",
            }
            for _index in range(55)
        ]

        response = self.client.post(
            reverse("telemetry:events"),
            data=json_body({"events": events}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["accepted"], 50)
        self.assertEqual(SuggestionEvent.objects.count(), 50)
