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


class IDFComponent(models.Model):
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
