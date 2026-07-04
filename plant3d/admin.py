from django.contrib import admin

from .models import ConversionJob, ModelObject, RenderPackage, RenderTile, SourceModel


@admin.register(SourceModel)
class SourceModelAdmin(admin.ModelAdmin):
    list_display = ("display_name", "source_format", "project_id", "uploaded_by", "is_saved_case", "source_system", "created_at")
    list_filter = ("source_format", "project_id", "is_saved_case", "source_system", "created_at")
    search_fields = ("display_name", "original_filename", "storage_key", "content_signature", "uploaded_by__username")


@admin.register(ConversionJob)
class ConversionJobAdmin(admin.ModelAdmin):
    list_display = ("source_model", "job_type", "status", "progress_percent", "created_at", "completed_at")
    list_filter = ("job_type", "status", "created_at")
    search_fields = ("source_model__display_name", "tool_name", "input_storage_key", "output_storage_prefix")


class RenderTileInline(admin.TabularInline):
    model = RenderTile
    extra = 0
    fields = ("tile_id", "sequence", "storage_key", "object_count", "byte_size")


@admin.register(RenderPackage)
class RenderPackageAdmin(admin.ModelAdmin):
    list_display = ("source_model", "package_format", "tile_count", "object_count", "byte_size", "created_at")
    list_filter = ("package_format", "coordinate_unit", "created_at")
    search_fields = ("source_model__display_name", "storage_prefix", "manifest_storage_key")
    inlines = [RenderTileInline]


@admin.register(ModelObject)
class ModelObjectAdmin(admin.ModelAdmin):
    list_display = ("stable_id", "source_model", "object_type", "tag", "line_id")
    list_filter = ("object_type",)
    search_fields = ("stable_id", "source_object_id", "tag", "line_id")
