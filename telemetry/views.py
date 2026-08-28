import json
import uuid

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from plant3d.project_gateway import validate_project_id

from .models import SuggestionEvent


MAX_EVENTS_PER_BATCH = 50
FORBIDDEN_CONTEXT_ID_KEYS = {
    "id",
    "pk",
    "layer_id",
    "run_id",
    "node_id",
    "edge_id",
    "family_id",
    "size_id",
    "source_model_id",
    "render_package_id",
    "model_object_id",
}


def _events_rate(group, request):
    return getattr(settings, "TELEMETRY_EVENTS_RATE_LIMIT", "120/m")


def _error_response(message, status=400, *, errors=None):
    payload = {"status": "error", "error": message}
    if errors:
        payload["errors"] = errors
    return JsonResponse(payload, status=status)


def _json_body(request):
    if not request.body:
        raise ValidationError("Request body must be valid JSON.")
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValidationError("Request body must be valid JSON.")
    return payload


def _validation_payload(exc):
    if hasattr(exc, "message_dict"):
        return {
            field: [str(message) for message in messages]
            for field, messages in exc.message_dict.items()
        }
    return {"__all__": [str(message) for message in getattr(exc, "messages", [exc])]}


def _clean_text(value, field_name, max_length):
    text = str(value or "").strip()
    if not text:
        raise ValidationError({field_name: "This field is required."})
    if len(text) > max_length:
        raise ValidationError({field_name: f"Ensure this value has at most {max_length} characters."})
    return text


def _clean_optional_text(value, max_length):
    text = str(value or "").strip()
    return text[:max_length]


def _clean_uuid(value):
    if value in (None, ""):
        return uuid.uuid4()
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        raise ValidationError({"key": "Event key must be a UUID."})


def _clean_optional_uuid(value, field_name):
    if value in (None, ""):
        return None
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        raise ValidationError({field_name: "Value must be a UUID."})


def _clean_json_object(value, field_name):
    if value in (None, ""):
        return {}
    if not isinstance(value, dict):
        raise ValidationError({field_name: "Value must be an object."})
    return _strip_domain_ids(value)


def _strip_domain_ids(value):
    if isinstance(value, list):
        return [_strip_domain_ids(item) for item in value]
    if isinstance(value, dict):
        cleaned = {}
        for key, item in value.items():
            key_text = str(key)
            if key_text in FORBIDDEN_CONTEXT_ID_KEYS:
                continue
            cleaned[key_text] = _strip_domain_ids(item)
        return cleaned
    return value


def _events_from_payload(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("events"), list):
        return payload["events"]
    raise ValidationError({"events": "Request body must be a list of events or an object with an events list."})


def _event_from_payload(raw_event, user):
    if not isinstance(raw_event, dict):
        raise ValidationError({"events": "Each event must be an object."})
    project_id = validate_project_id(raw_event.get("project_id"), user)
    if not project_id:
        raise PermissionDenied("You do not have access to this telemetry project.")
    action = _clean_text(raw_event.get("action"), "action", 30)
    if action not in {choice[0] for choice in SuggestionEvent.ACTION_CHOICES}:
        raise ValidationError({"action": "Unsupported suggestion event action."})
    return SuggestionEvent(
        key=_clean_uuid(raw_event.get("key")),
        user=user,
        project_id=project_id,
        owner_module=_clean_text(raw_event.get("owner_module"), "owner_module", 40),
        suggestion_code=_clean_text(raw_event.get("suggestion_code"), "suggestion_code", 120),
        action=action,
        session_key=_clean_optional_uuid(raw_event.get("session_key"), "session_key"),
        context=_clean_json_object(raw_event.get("context", {}), "context"),
        action_detail=_clean_json_object(raw_event.get("action_detail", {}), "action_detail"),
        client=_clean_optional_text(raw_event.get("client", ""), 80),
    )


@login_required
@require_POST
@ratelimit(group="telemetry-events", key="user_or_ip", rate=_events_rate, method="POST", block=False)
def events_view(request):
    if getattr(request, "limited", False):
        return _error_response("Too many telemetry events. Please slow down.", status=429)
    try:
        payload = _json_body(request)
        raw_events = _events_from_payload(payload)[:MAX_EVENTS_PER_BATCH]
        events = [_event_from_payload(raw_event, request.user) for raw_event in raw_events]
        SuggestionEvent.objects.bulk_create(events)
    except PermissionDenied:
        raise
    except ValidationError as exc:
        return _error_response("Invalid telemetry event payload.", errors=_validation_payload(exc))
    return JsonResponse(
        {
            "status": "ok",
            "accepted": len(events),
            "keys": [str(event.key) for event in events],
        },
        status=201,
    )
