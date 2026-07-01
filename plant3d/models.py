from django.core.validators import MaxValueValidator, MinValueValidator
from django.conf import settings
from django.db import models


class SourceModel(models.Model):
    SOURCE_FORMAT_CHOICES = [
        ("IFC", "IFC"),
        ("IDF", "IDF"),
        ("PCF", "PCF"),
        ("OTHER", "Other"),
    ]

    project = models.ForeignKey(
        "eht.ProjectData",
        to_field="proj_id",
        db_column="project_id",
        on_delete=models.CASCADE,
        related_name="plant3d_source_models",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="plant3d_source_models",
    )
    display_name = models.CharField(max_length=255)
    source_format = models.CharField(max_length=20, choices=SOURCE_FORMAT_CHOICES)
    original_filename = models.CharField(max_length=255)
    storage_key = models.CharField(max_length=500)
    content_signature = models.CharField(max_length=64, blank=True, default="")
    file_size_bytes = models.BigIntegerField(default=0)
    source_system = models.CharField(max_length=80, blank=True, default="")
    declared_unit = models.CharField(max_length=30, blank=True, default="")
    coordinate_frame = models.CharField(max_length=80, blank=True, default="")
    bounds = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    is_saved_case = models.BooleanField(default=False)
    saved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["project", "source_format"]),
            models.Index(fields=["project", "content_signature"]),
            models.Index(fields=["project", "uploaded_by", "is_saved_case"]),
        ]

    def __str__(self):
        return f"{self.display_name} [{self.source_format}]"


class ConversionJob(models.Model):
    STATUS_CHOICES = [
        ("queued", "Queued"),
        ("running", "Running"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    ]

    JOB_TYPE_CHOICES = [
        ("render_package", "Render Package"),
        ("metadata_index", "Metadata Index"),
    ]

    source_model = models.ForeignKey(SourceModel, on_delete=models.CASCADE, related_name="conversion_jobs")
    job_type = models.CharField(max_length=40, choices=JOB_TYPE_CHOICES, default="render_package")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="queued")
    progress_percent = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    tool_name = models.CharField(max_length=80, blank=True, default="")
    tool_version = models.CharField(max_length=80, blank=True, default="")
    input_storage_key = models.CharField(max_length=500, blank=True, default="")
    output_storage_prefix = models.CharField(max_length=500, blank=True, default="")
    log = models.TextField(blank=True, default="")
    error_message = models.TextField(blank=True, default="")
    metrics = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["source_model", "status"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self):
        return f"{self.source_model.display_name} {self.job_type} [{self.status}]"


class RenderPackage(models.Model):
    PACKAGE_FORMAT_CHOICES = [
        ("GLB", "GLB"),
        ("GLTF", "glTF"),
        ("TILED_JSON", "Tiled JSON Manifest"),
        ("CUSTOM", "Custom"),
    ]

    source_model = models.ForeignKey(SourceModel, on_delete=models.CASCADE, related_name="render_packages")
    conversion_job = models.ForeignKey(
        ConversionJob,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="render_packages",
    )
    package_format = models.CharField(max_length=30, choices=PACKAGE_FORMAT_CHOICES)
    storage_prefix = models.CharField(max_length=500)
    manifest_storage_key = models.CharField(max_length=500, blank=True, default="")
    object_count = models.PositiveIntegerField(default=0)
    tile_count = models.PositiveIntegerField(default=0)
    byte_size = models.BigIntegerField(default=0)
    coordinate_unit = models.CharField(max_length=30, blank=True, default="")
    coordinate_frame = models.CharField(max_length=80, blank=True, default="")
    bounds = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["source_model", "package_format"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.source_model.display_name} render package [{self.package_format}]"


class RenderTile(models.Model):
    render_package = models.ForeignKey(RenderPackage, on_delete=models.CASCADE, related_name="tiles")
    tile_id = models.CharField(max_length=120)
    storage_key = models.CharField(max_length=500)
    sequence = models.PositiveIntegerField(default=0)
    rtc_origin_x = models.FloatField(default=0.0)
    rtc_origin_y = models.FloatField(default=0.0)
    rtc_origin_z = models.FloatField(default=0.0)
    bounds = models.JSONField(default=dict, blank=True)
    object_count = models.PositiveIntegerField(default=0)
    byte_size = models.BigIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["render_package", "sequence", "id"]
        constraints = [
            models.UniqueConstraint(fields=["render_package", "tile_id"], name="plant3d_unique_tile_per_package"),
        ]
        indexes = [
            models.Index(fields=["render_package", "sequence"]),
        ]

    def __str__(self):
        return f"{self.render_package_id}:{self.tile_id}"

    @property
    def rtc_origin(self):
        return [self.rtc_origin_x, self.rtc_origin_y, self.rtc_origin_z]


class ModelObject(models.Model):
    source_model = models.ForeignKey(SourceModel, on_delete=models.CASCADE, related_name="model_objects")
    render_package = models.ForeignKey(
        RenderPackage,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="model_objects",
    )
    render_tile = models.ForeignKey(
        RenderTile,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="model_objects",
    )
    stable_id = models.CharField(max_length=160)
    source_object_id = models.CharField(max_length=160, blank=True, default="")
    object_type = models.CharField(max_length=80, blank=True, default="")
    tag = models.CharField(max_length=160, blank=True, default="")
    line_id = models.CharField(max_length=160, blank=True, default="")
    bounds = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["source_model", "stable_id"]
        constraints = [
            models.UniqueConstraint(fields=["source_model", "stable_id"], name="plant3d_unique_object_per_source"),
        ]
        indexes = [
            models.Index(fields=["source_model", "object_type"]),
            models.Index(fields=["source_model", "tag"]),
            models.Index(fields=["source_model", "line_id"]),
        ]

    def __str__(self):
        label = self.tag or self.line_id or self.source_object_id or self.stable_id
        return f"{label} [{self.object_type or 'object'}]"
