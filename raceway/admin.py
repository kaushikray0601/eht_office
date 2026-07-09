from django.contrib import admin

from .models import RacewayFamily, RacewayLayer, RacewayNode, RacewayRun, RacewaySize


class RacewaySizeInline(admin.TabularInline):
    model = RacewaySize
    extra = 0
    fields = ("width_mm", "depth_mm", "weight_kg_per_m", "is_active")


@admin.register(RacewayFamily)
class RacewayFamilyAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "kind", "material", "standard_basis", "is_active", "is_validated")
    list_filter = ("kind", "material", "standard_basis", "is_active", "is_validated")
    search_fields = ("code", "name", "material")
    inlines = [RacewaySizeInline]


@admin.register(RacewaySize)
class RacewaySizeAdmin(admin.ModelAdmin):
    list_display = ("family", "width_mm", "depth_mm", "weight_kg_per_m", "is_active")
    list_filter = ("family__kind", "is_active")
    search_fields = ("family__code", "family__name")


class RacewayNodeInline(admin.TabularInline):
    model = RacewayNode
    extra = 0
    fields = ("sequence", "node_kind", "source_x_m", "source_y_m", "source_z_m")


@admin.register(RacewayLayer)
class RacewayLayerAdmin(admin.ModelAdmin):
    list_display = ("name", "project_id", "status", "revision", "source_model_id", "render_package_id", "created_by", "updated_at")
    list_filter = ("status", "project_id")
    search_fields = ("name", "project_id", "description")


@admin.register(RacewayRun)
class RacewayRunAdmin(admin.ModelAdmin):
    list_display = ("tag", "layer", "family", "size", "service_class", "status", "coordinate_frame", "updated_at")
    list_filter = ("service_class", "status", "family__kind")
    search_fields = ("tag", "key", "layer__name", "layer__project_id")
    readonly_fields = ("key",)
    inlines = [RacewayNodeInline]


@admin.register(RacewayNode)
class RacewayNodeAdmin(admin.ModelAdmin):
    list_display = ("run", "sequence", "node_kind", "source_x_m", "source_y_m", "source_z_m")
    list_filter = ("node_kind",)
    search_fields = ("key", "run__tag", "run__layer__project_id")
    readonly_fields = ("key",)
