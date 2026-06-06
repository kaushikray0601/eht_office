from django.contrib import admin, messages

from eht.mi_catalogue_readiness import evaluate_mi_family_readiness
from eht.models import (
    ColdCableCatalogue,
    ColdCableResult,
    ManagedProject,
    MIAlloyTempFactor,
    MICableFamily,
    MICableHeater,
    MIColdLeadOption,
    ProjectData,
    SelectedMIHeater,
    SLDNodeLayout,
)


@admin.register(ManagedProject)
class ManagedProjectAdmin(admin.ModelAdmin):
    list_display = ('proj_id', 'description', 'is_active')
    list_filter = ('is_active', 'assigned_users')
    search_fields = ('proj_id', 'description', 'assigned_users__username')
    filter_horizontal = ('assigned_users',)


@admin.register(ProjectData)
class ProjectDataAdmin(admin.ModelAdmin):
    list_display = ('proj_id', 'vendor', 'voltage', 'max_cb_size', 'cable_standard', 'cable_install_method', 'mcb_curve', 'rcd_provided')
    list_filter = ('vendor', 'max_cb_size', 'cable_standard', 'cable_install_method', 'mcb_curve', 'rcd_provided')
    search_fields = ('proj_id',)


def _cold_cable_row_ready(row):
    return (
        row.cable_standard
        and row.cable_type_code
        and row.conductor_material
        and row.insulation_type
        and row.core_count in {2, 3, 4}
        and row.conductor_size_mm2 > 0
        and row.ampacity_a > 0
        and row.ampacity_temp_ref_c < row.max_conductor_temp_c
        and row.resistance_mohm_per_m > 0
        and row.source_document
    )


@admin.action(description='Mark selected ready cold-cable rows as validated')
def mark_cold_cable_rows_validated(modeladmin, request, queryset):
    validated_count = 0
    skipped = []
    for row in queryset:
        if not _cold_cable_row_ready(row):
            skipped.append(str(row))
            continue
        if not row.is_validated:
            row.is_validated = True
            row.save(update_fields=['is_validated'])
            validated_count += 1

    if validated_count:
        modeladmin.message_user(request, f'{validated_count} cold-cable catalogue row(s) marked as validated.')
    if skipped:
        modeladmin.message_user(
            request,
            f"Skipped {len(skipped)} incomplete cold-cable row(s): {', '.join(skipped[:5])}.",
            level=messages.WARNING,
        )


@admin.action(description='Mark selected cold-cable rows as not validated')
def mark_cold_cable_rows_unvalidated(modeladmin, request, queryset):
    updated = queryset.update(is_validated=False)
    modeladmin.message_user(request, f'{updated} cold-cable catalogue row(s) marked as not validated.')


@admin.register(ColdCableCatalogue)
class ColdCableCatalogueAdmin(admin.ModelAdmin):
    list_display = (
        'cable_standard',
        'cable_type_code',
        'core_count',
        'conductor_size_mm2',
        'installation_method',
        'ampacity_a',
        'resistance_mohm_per_m',
        'is_validated',
    )
    list_filter = (
        'is_validated',
        'cable_standard',
        'conductor_material',
        'insulation_type',
        'core_count',
        'installation_method',
    )
    search_fields = ('vendor', 'catalogue_ref', 'cable_type_code', 'source_document')
    actions = (mark_cold_cable_rows_validated, mark_cold_cable_rows_unvalidated)


@admin.register(ColdCableResult)
class ColdCableResultAdmin(admin.ModelAdmin):
    list_display = (
        'project',
        'line_id',
        'branch_index',
        'sizing_status',
        'cable_4c_size_mm2',
        'cable_3c_size_mm2',
        'per_circuit_operating_current_a',
        'length_basis',
        'calculated_at',
    )
    list_filter = ('project', 'sizing_status', 'heating_cable_type', 'length_basis')
    search_fields = ('project__proj_id', 'line_id', 'line_uid')
    readonly_fields = tuple(field.name for field in ColdCableResult._meta.fields)

    def has_add_permission(self, request):
        return False


@admin.register(SLDNodeLayout)
class SLDNodeLayoutAdmin(admin.ModelAdmin):
    list_display = ('project', 'display_tag', 'component_type', 'line_id', 'branch_index', 'updated_at')
    list_filter = ('project', 'component_type')
    search_fields = ('project__proj_id', 'display_tag', 'component_id', 'line_id', 'component_uid')


class MICableHeaterInline(admin.TabularInline):
    model = MICableHeater
    extra = 0
    fields = (
        'part_number',
        'conductors',
        'resistance_ohms_m',
        'max_current_a',
        'conductor_material',
        'tcr_per_degree_c',
    )
    readonly_fields = fields
    can_delete = False
    show_change_link = True


@admin.action(description='Mark selected ready MI families as validated')
def mark_mi_families_validated(modeladmin, request, queryset):
    validated_count = 0
    skipped = []
    for family in queryset.prefetch_related('heaters__cold_lead_options'):
        report = evaluate_mi_family_readiness(family)
        if not report['ready']:
            skipped.append(f"{family.vendor} {family.family_name}")
            continue
        if not family.is_validated:
            family.is_validated = True
            family.save(update_fields=['is_validated'])
            validated_count += 1

    if validated_count:
        modeladmin.message_user(request, f'{validated_count} MI family/families marked as validated.')
    if skipped:
        modeladmin.message_user(
            request,
            f"Skipped {len(skipped)} blocked MI family/families: {', '.join(skipped)}.",
            level=messages.WARNING,
        )


@admin.action(description='Mark selected MI families as not validated')
def mark_mi_families_unvalidated(modeladmin, request, queryset):
    updated = queryset.update(is_validated=False)
    modeladmin.message_user(request, f'{updated} MI family/families marked as not validated.')


@admin.register(MICableFamily)
class MICableFamilyAdmin(admin.ModelAdmin):
    list_display = (
        'vendor',
        'family_name',
        'alloy_type',
        'max_voltage',
        'max_maintain_temp_c',
        'max_exposure_temp_c',
        'source_document',
        'is_validated',
    )
    list_filter = ('vendor', 'is_validated', 'alloy_type', 'gas_group')
    search_fields = ('family_name', 'source_document', 'zone_approval')
    actions = (mark_mi_families_validated, mark_mi_families_unvalidated)
    inlines = (MICableHeaterInline,)


class MIColdLeadOptionInline(admin.TabularInline):
    model = MIColdLeadOption
    extra = 0
    fields = ('option_code', 'length_m')


@admin.register(MICableHeater)
class MICableHeaterAdmin(admin.ModelAdmin):
    list_display = (
        'part_number',
        'family',
        'conductors',
        'resistance_ohms_m',
        'max_current_a',
        'conductor_material',
        'tcr_per_degree_c',
    )
    list_filter = ('family__vendor', 'family__family_name', 'conductor_material')
    search_fields = ('part_number', 'family__family_name', 'conductor_material')
    inlines = (MIColdLeadOptionInline,)


@admin.register(MIColdLeadOption)
class MIColdLeadOptionAdmin(admin.ModelAdmin):
    list_display = ('option_code', 'heater', 'length_m')
    list_filter = ('heater__family__vendor', 'heater__family__family_name')
    search_fields = ('option_code', 'heater__part_number')


@admin.register(MIAlloyTempFactor)
class MIAlloyTempFactorAdmin(admin.ModelAdmin):
    list_display = ('alloy_type', 'temperature_c', 'resistance_multiplier')
    list_filter = ('alloy_type',)
    search_fields = ('alloy_type',)


@admin.register(SelectedMIHeater)
class SelectedMIHeaterAdmin(admin.ModelAdmin):
    list_display = (
        'line',
        'selection_status',
        'heater',
        'cold_lead_option_code',
        'power_density_w_m',
        'current_nominal_a',
        't_class_verdict',
    )
    list_filter = ('selection_status', 't_class_verdict', 'heater__family__vendor')
    search_fields = ('line__line_id', 'heater__part_number', 'cold_lead_option_code')
    readonly_fields = tuple(field.name for field in SelectedMIHeater._meta.fields)

    def has_add_permission(self, request):
        return False
