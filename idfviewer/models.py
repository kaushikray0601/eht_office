from django.db import models


class IDFFile(models.Model):
    FORMAT_CHOICES = [
        ('IDF', 'IDF'),
        ('PCF', 'PCF'),
    ]

    project = models.ForeignKey(
        'eht.ProjectData',
        to_field='proj_id',
        db_column='project_id',
        on_delete=models.CASCADE,
        related_name='idf_files'
    )
    filename = models.CharField(max_length=255)
    source_format = models.CharField(max_length=10, choices=FORMAT_CHOICES, default='IDF')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    last_saved_at = models.DateTimeField(null=True, blank=True)
    content_signature = models.CharField(max_length=64, blank=True, default='')
    component_count = models.PositiveIntegerField(default=0)
    pipe_count = models.PositiveIntegerField(default=0)
    fitting_count = models.PositiveIntegerField(default=0)
    weld_count = models.PositiveIntegerField(default=0)
    support_count = models.PositiveIntegerField(default=0)
    marker_count = models.PositiveIntegerField(default=0)

    # Store standard global bounding boxes if needed later
    min_x = models.FloatField(null=True, blank=True)
    max_x = models.FloatField(null=True, blank=True)
    min_y = models.FloatField(null=True, blank=True)
    max_y = models.FloatField(null=True, blank=True)
    min_z = models.FloatField(null=True, blank=True)
    max_z = models.FloatField(null=True, blank=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.filename} [{self.source_format}] ({self.project.proj_id})"

    @property
    def saved_at_display(self):
        return self.last_saved_at or self.uploaded_at

    def count_breakdown(self):
        return {
            'pipes': self.pipe_count,
            'fittings': self.fitting_count,
            'welds': self.weld_count,
            'supports': self.support_count,
            'markers': self.marker_count,
        }


class IDFComponent(models.Model):
    SCENE_BUCKET_CHOICES = [
        ('pipes', 'Pipes'),
        ('fittings', 'Fittings'),
        ('welds', 'Welds'),
        ('supports', 'Supports'),
        ('markers', 'Markers'),
    ]

    idf_file = models.ForeignKey(IDFFile, on_delete=models.CASCADE, related_name='components')
    project = models.ForeignKey(
        'eht.ProjectData',
        to_field='proj_id',
        db_column='project_id',
        on_delete=models.CASCADE,
        related_name='idf_components'
    )
    
    uid = models.IntegerField()
    record_id = models.IntegerField()
    kind = models.CharField(max_length=50)
    source_format = models.CharField(max_length=10, choices=IDFFile.FORMAT_CHOICES, default='IDF')
    scene_bucket = models.CharField(max_length=20, choices=SCENE_BUCKET_CHOICES, default='fittings')
    line_id = models.CharField(max_length=100, blank=True, default='')

    # Using JSONField for flexible dynamic storage of coordinates, arrays and variable metadata
    properties = models.JSONField(default=dict)

    class Meta:
        ordering = ['idf_file', 'uid']
        indexes = [
            models.Index(fields=['project', 'line_id']),
            models.Index(fields=['kind']),
            models.Index(fields=['project', 'source_format']),
        ]

    def __str__(self):
        return f"{self.kind} [{self.source_format}] ({self.line_id})"


class IDFFileSaveEvent(models.Model):
    ACTION_CHOICES = [
        ('created', 'Created'),
        ('replaced', 'Replaced'),
    ]

    idf_file = models.ForeignKey(IDFFile, on_delete=models.CASCADE, related_name='save_events')
    project = models.ForeignKey(
        'eht.ProjectData',
        to_field='proj_id',
        db_column='project_id',
        on_delete=models.CASCADE,
        related_name='idf_file_save_events'
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    previous_component_count = models.PositiveIntegerField(default=0)
    component_count = models.PositiveIntegerField(default=0)
    previous_counts = models.JSONField(default=dict)
    current_counts = models.JSONField(default=dict)
    previous_signature = models.CharField(max_length=64, blank=True, default='')
    current_signature = models.CharField(max_length=64, blank=True, default='')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.idf_file.filename} [{self.action}]"


class ProjectAttributeMapping(models.Model):
    SOURCE_CHOICES = [
        ('PCF', 'PCF'),
    ]

    project = models.ForeignKey(
        'eht.ProjectData',
        to_field='proj_id',
        db_column='project_id',
        on_delete=models.CASCADE,
        related_name='idf_attribute_mappings'
    )
    source_format = models.CharField(max_length=10, choices=SOURCE_CHOICES, default='PCF')
    attribute_key = models.CharField(max_length=50)
    display_name = models.CharField(max_length=120)
    display_order = models.PositiveSmallIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['display_order', 'attribute_key']
        constraints = [
            models.UniqueConstraint(
                fields=['project', 'source_format', 'attribute_key'],
                name='idfviewer_unique_project_attribute_mapping',
            ),
        ]
        indexes = [
            models.Index(fields=['project', 'source_format']),
        ]

    def __str__(self):
        return f"{self.project_id} {self.attribute_key} -> {self.display_name}"


class EHTDesignElement(models.Model):
    ELEMENT_TYPES = [
        ('distribution_board', 'Distribution Board'),
        ('junction_box', 'Junction Box'),
        ('isolator', 'Isolator'),
        ('tracer_sr', 'SR Tracer'),
        ('tracer_mi', 'MI Tracer'),
        ('rtd', 'RTD'),
        ('cold_cable', 'Cold Cable'),
        ('end_termination', 'End Termination'),
        ('pipe_strap', 'Pipe Strap'),
    ]

    project = models.ForeignKey(
        'eht.ProjectData',
        to_field='proj_id',
        db_column='project_id',
        on_delete=models.CASCADE,
        related_name='idf_eht_design_elements'
    )
    idf_file = models.ForeignKey(
        IDFFile,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='eht_design_elements',
    )
    element_uid = models.CharField(max_length=64)
    element_type = models.CharField(max_length=40, choices=ELEMENT_TYPES)
    label = models.CharField(max_length=120, blank=True, default='')
    geometry = models.JSONField(default=dict)
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['project', 'idf_file', 'element_uid'],
                name='idfviewer_unique_eht_element_per_file_scope',
            ),
        ]
        indexes = [
            models.Index(fields=['project', 'idf_file']),
            models.Index(fields=['project', 'element_type']),
        ]

    def __str__(self):
        return f"{self.get_element_type_display()} {self.label or self.element_uid}"


class PlotPlanOverlay(models.Model):
    project = models.OneToOneField(
        'eht.ProjectData',
        to_field='proj_id',
        db_column='project_id',
        on_delete=models.CASCADE,
        related_name='plot_plan'
    )
    image = models.ImageField(upload_to='plot_plans/')
    scale = models.FloatField(default=1.0)
    offset_x = models.FloatField(default=0.0)
    offset_z = models.FloatField(default=0.0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Plot Plan for {self.project.proj_id}"
