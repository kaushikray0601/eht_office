from django.contrib import admin

from eht.models import ManagedProject, ProjectData, SLDNodeLayout


@admin.register(ManagedProject)
class ManagedProjectAdmin(admin.ModelAdmin):
    list_display = ('proj_id', 'description', 'is_active')
    list_filter = ('is_active', 'assigned_users')
    search_fields = ('proj_id', 'description', 'assigned_users__username')
    filter_horizontal = ('assigned_users',)


@admin.register(ProjectData)
class ProjectDataAdmin(admin.ModelAdmin):
    list_display = ('proj_id', 'vendor', 'voltage', 'max_cb_size')
    list_filter = ('vendor', 'max_cb_size')
    search_fields = ('proj_id',)


@admin.register(SLDNodeLayout)
class SLDNodeLayoutAdmin(admin.ModelAdmin):
    list_display = ('project', 'display_tag', 'component_type', 'line_id', 'branch_index', 'updated_at')
    list_filter = ('project', 'component_type')
    search_fields = ('project__proj_id', 'display_tag', 'component_id', 'line_id', 'component_uid')
