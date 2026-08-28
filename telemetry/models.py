import uuid

from django.conf import settings
from django.db import models


class SuggestionEvent(models.Model):
    ACTION_SHOWN = "shown"
    ACTION_ACCEPTED = "accepted"
    ACTION_REJECTED = "rejected"
    ACTION_EDITED = "edited"
    ACTION_DISMISSED = "dismissed"
    ACTION_UNRESOLVED_AT_SAVE = "unresolved_at_save"

    ACTION_CHOICES = [
        (ACTION_SHOWN, "Shown"),
        (ACTION_ACCEPTED, "Accepted"),
        (ACTION_REJECTED, "Rejected"),
        (ACTION_EDITED, "Edited"),
        (ACTION_DISMISSED, "Dismissed"),
        (ACTION_UNRESOLVED_AT_SAVE, "Unresolved at save"),
    ]

    key = models.UUIDField(default=uuid.uuid4, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="suggestion_events",
    )
    project_id = models.CharField(max_length=80, db_index=True)
    owner_module = models.CharField(max_length=40)
    suggestion_code = models.CharField(max_length=120, db_index=True)
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    session_key = models.UUIDField(null=True, blank=True, db_index=True)
    context = models.JSONField(default=dict, blank=True)
    action_detail = models.JSONField(default=dict, blank=True)
    client = models.CharField(max_length=80, blank=True, default="")

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["project_id", "suggestion_code"]),
            models.Index(fields=["suggestion_code", "action"]),
            models.Index(fields=["project_id", "session_key"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.project_id} {self.suggestion_code} {self.action}"
