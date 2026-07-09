import math
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


SOURCE_COORDINATE_FRAME = "source_xyz_m"


def _is_finite(value):
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


class RacewayFamily(models.Model):
    KIND_CHOICES = [
        ("ladder", "Ladder"),
        ("perforated_tray", "Perforated tray"),
        ("solid_tray", "Solid tray"),
        ("mesh_tray", "Mesh tray"),
        ("trunking", "Trunking"),
        ("sleeve", "Sleeve"),
    ]

    code = models.SlugField(max_length=80, unique=True)
    name = models.CharField(max_length=160)
    kind = models.CharField(max_length=40, choices=KIND_CHOICES)
    material = models.CharField(max_length=80, default="HDG steel")
    standard_length_mm = models.PositiveIntegerField(default=3000, validators=[MinValueValidator(1)])
    standard_basis = models.CharField(max_length=80, default="IEC 61537")
    profile = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    is_validated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]
        indexes = [
            models.Index(fields=["kind", "is_active"]),
            models.Index(fields=["standard_basis"]),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"


class RacewaySize(models.Model):
    family = models.ForeignKey(RacewayFamily, on_delete=models.PROTECT, related_name="sizes")
    width_mm = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    depth_mm = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    weight_kg_per_m = models.FloatField(null=True, blank=True)
    load_span_table = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["family__code", "width_mm", "depth_mm"]
        constraints = [
            models.UniqueConstraint(fields=["family", "width_mm", "depth_mm"], name="raceway_unique_size_per_family"),
        ]
        indexes = [
            models.Index(fields=["family", "is_active"]),
        ]

    def clean(self):
        super().clean()
        if self.weight_kg_per_m is not None and (
            not _is_finite(self.weight_kg_per_m) or float(self.weight_kg_per_m) < 0
        ):
            raise ValidationError({"weight_kg_per_m": "Weight per metre must be a finite non-negative value."})

    def __str__(self):
        return f"{self.family.code} {self.width_mm}x{self.depth_mm} mm"


class RacewayLayer(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("active", "Active"),
        ("superseded", "Superseded"),
    ]

    project_id = models.CharField(max_length=80, db_index=True)
    source_model_id = models.PositiveBigIntegerField(null=True, blank=True, db_index=True)
    render_package_id = models.PositiveBigIntegerField(null=True, blank=True, db_index=True)
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    revision = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    metadata = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="raceway_layers",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["project_id", "-updated_at", "-id"]
        indexes = [
            models.Index(fields=["project_id", "status"]),
            models.Index(fields=["project_id", "source_model_id"]),
            models.Index(fields=["project_id", "render_package_id"]),
        ]

    def __str__(self):
        return f"{self.project_id} - {self.name}"


class RacewayRun(models.Model):
    SERVICE_CLASS_CHOICES = [
        ("power", "Power"),
        ("control", "Control"),
        ("instrument", "Instrument"),
        ("telecom", "Telecom"),
        ("other", "Other"),
    ]
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("committed", "Committed"),
        ("superseded", "Superseded"),
    ]

    layer = models.ForeignKey(RacewayLayer, on_delete=models.CASCADE, related_name="runs")
    key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    tag = models.CharField(max_length=120, blank=True, default="")
    family = models.ForeignKey(RacewayFamily, on_delete=models.PROTECT, related_name="runs")
    size = models.ForeignKey(RacewaySize, on_delete=models.PROTECT, related_name="runs")
    service_class = models.CharField(max_length=30, choices=SERVICE_CLASS_CHOICES, default="power")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    coordinate_frame = models.CharField(max_length=40, default=SOURCE_COORDINATE_FRAME)
    elevation_m = models.FloatField(null=True, blank=True)
    source_model_id = models.PositiveBigIntegerField(null=True, blank=True, db_index=True)
    render_package_id = models.PositiveBigIntegerField(null=True, blank=True, db_index=True)
    validation_summary = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["layer", "tag", "id"]
        indexes = [
            models.Index(fields=["layer", "status"]),
            models.Index(fields=["service_class"]),
            models.Index(fields=["source_model_id", "render_package_id"]),
        ]

    def clean(self):
        super().clean()
        if self.size_id and self.family_id and self.size.family_id != self.family_id:
            raise ValidationError({"size": "Raceway size must belong to the selected family."})
        if self.coordinate_frame != SOURCE_COORDINATE_FRAME:
            raise ValidationError({"coordinate_frame": f"Coordinate frame must be {SOURCE_COORDINATE_FRAME}."})
        if self.elevation_m is not None and not _is_finite(self.elevation_m):
            raise ValidationError({"elevation_m": "Elevation must be a finite metre value."})

    def __str__(self):
        label = self.tag or str(self.key)
        return f"{label} [{self.service_class}]"


class RacewayNode(models.Model):
    KIND_CHOICES = [
        ("endpoint", "Endpoint"),
        ("bend", "Bend"),
        ("branch", "Branch"),
        ("riser", "Riser"),
        ("intermediate", "Intermediate"),
    ]

    run = models.ForeignKey(RacewayRun, on_delete=models.CASCADE, related_name="nodes")
    key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    sequence = models.PositiveIntegerField()
    node_kind = models.CharField(max_length=30, choices=KIND_CHOICES, default="intermediate")
    source_x_m = models.FloatField()
    source_y_m = models.FloatField()
    source_z_m = models.FloatField()
    anchor = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["run", "sequence", "id"]
        constraints = [
            models.UniqueConstraint(fields=["run", "sequence"], name="raceway_unique_node_sequence_per_run"),
        ]
        indexes = [
            models.Index(fields=["run", "sequence"]),
        ]

    def clean(self):
        super().clean()
        errors = {}
        for field_name in ("source_x_m", "source_y_m", "source_z_m"):
            if not _is_finite(getattr(self, field_name)):
                errors[field_name] = "Coordinate must be a finite source/world metre value."
        if self.anchor and not isinstance(self.anchor, dict):
            errors["anchor"] = "Anchor must be an object."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.run_id}:{self.sequence}"
