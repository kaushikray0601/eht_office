import json

from django.contrib import admin, messages
from django.utils.html import format_html

from eht.cold_cable_readiness import cold_cable_method_readiness
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
    SLDTopologyEdit,
)
from eht.sld_payload import build_project_sld_payload
from eht.sld_topology import payload_fingerprint, validate_sld_topology_invariants
from eht.sld_topology_history import (
    DELETABLE_HISTORY_STATUSES,
    compact_topology_edit_record,
    topology_edit_payload_size_kb,
)


@admin.register(ManagedProject)
class ManagedProjectAdmin(admin.ModelAdmin):
    list_display = ('proj_id', 'description', 'is_active')
    list_filter = ('is_active', 'assigned_users')
    search_fields = ('proj_id', 'description', 'assigned_users__username')
    filter_horizontal = ('assigned_users',)


@admin.register(ProjectData)
class ProjectDataAdmin(admin.ModelAdmin):
    list_display = (
        'proj_id',
        'vendor',
        'voltage',
        'max_cb_size',
        'cable_standard',
        'cable_install_method',
        'cold_cable_catalogue_readiness',
        'mcb_curve',
        'rcd_provided',
    )
    list_filter = ('vendor', 'max_cb_size', 'cable_standard', 'cable_install_method', 'mcb_curve', 'rcd_provided')
    search_fields = ('proj_id',)

    @admin.display(description='Cold-cable catalogue readiness')
    def cold_cable_catalogue_readiness(self, obj):
        readiness = cold_cable_method_readiness(
            obj.cable_standard,
            obj.cable_conductor_material,
            obj.cable_insulation_type,
        ).get(obj.cable_install_method)
        if readiness is None or readiness['status'] == 'unavailable':
            return 'No validated rows'
        if readiness['status'] == 'partial':
            missing = ', '.join(f'{core_count}C' for core_count in readiness['missing_core_counts'])
            return f"Partial: {readiness['validated_rows']} row(s), missing {missing}"
        return f"Ready: {readiness['validated_rows']} row(s)"


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
        'basis_readiness',
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

    @admin.display(description='Basis readiness')
    def basis_readiness(self, obj):
        readiness = cold_cable_method_readiness(
            obj.cable_standard,
            obj.conductor_material,
            obj.insulation_type,
        ).get(obj.installation_method)
        if readiness is None or readiness['status'] == 'unavailable':
            return 'No validated rows'
        if readiness['status'] == 'partial':
            missing = ', '.join(f'{core_count}C' for core_count in readiness['missing_core_counts'])
            return f'Missing {missing}'
        return 'Ready'


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


def _json_pretty(value):
    return json.dumps(value or {}, indent=2, sort_keys=True, default=str)


def _preformatted(value):
    return format_html(
        '<pre style="white-space: pre-wrap; max-height: 32rem; overflow: auto;">{}</pre>',
        value,
    )


@admin.register(SLDTopologyEdit)
class SLDTopologyEditAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'project',
        'edit_type',
        'status',
        'operation_count',
        'compacted_status',
        'payload_size',
        'history_payload_compacted_status',
        'baseline_changed_status',
        'validation_status',
        'created_by',
        'created_at',
    )
    list_filter = ('project', 'status', 'edit_type', 'created_at')
    search_fields = ('project__proj_id', 'edit_type', 'status', 'created_by__username', 'remarks')
    date_hierarchy = 'created_at'
    readonly_fields = (
        'project',
        'edit_type',
        'status',
        'created_by',
        'remarks',
        'baseline_fingerprint',
        'current_baseline_fingerprint',
        'baseline_changed_status',
        'operation_count',
        'compacted_status',
        'payload_size',
        'history_payload_compacted_status',
        'chain_audit_summary',
        'operation_history',
        'replay_diagnostic',
        'validation_summary_pretty',
        'edit_payload_pretty',
        'generated_snapshot_pretty',
        'created_at',
        'updated_at',
    )
    fieldsets = (
        ('Edit', {
            'fields': (
                'project',
                'edit_type',
                'status',
                'created_by',
                'remarks',
                'created_at',
                'updated_at',
            ),
        }),
        ('Replay And Audit', {
            'fields': (
                'baseline_fingerprint',
                'current_baseline_fingerprint',
                'baseline_changed_status',
                'operation_count',
                'compacted_status',
                'payload_size',
                'history_payload_compacted_status',
                'chain_audit_summary',
                'operation_history',
                'replay_diagnostic',
            ),
        }),
        ('Validation And Payload', {
            'classes': ('collapse',),
            'fields': (
                'validation_summary_pretty',
                'edit_payload_pretty',
                'generated_snapshot_pretty',
            ),
        }),
    )
    actions = (
        'compact_selected_history_records',
        'emergency_delete_selected_non_active_history_records',
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.user.has_perm('eht.change_sldtopologyedit')

    def has_delete_permission(self, request, obj=None):
        if not request.user.has_perm('eht.delete_sldtopologyedit'):
            return False
        if obj is None:
            return True
        return obj.status in DELETABLE_HISTORY_STATUSES

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop('delete_selected', None)
        return actions

    def _operations(self, obj):
        operations = (obj.edit_payload or {}).get('topology_operations')
        return operations if isinstance(operations, list) else []

    def _operation_audit_summary(self, obj):
        operations = (obj.edit_payload or {}).get('topology_operation_audit_summary')
        return operations if isinstance(operations, list) else []

    @admin.display(description='Operations')
    def operation_count(self, obj):
        return len(self._operations(obj))

    @admin.display(description='Compacted')
    def compacted_status(self, obj):
        if not (obj.edit_payload or {}).get('topology_chain_compacted'):
            return 'No'
        compaction = (obj.edit_payload or {}).get('topology_chain_compaction') or {}
        original = compaction.get('original_operation_count') or '-'
        kept = compaction.get('kept_operation_count') or len(self._operations(obj))
        dropped = compaction.get('dropped_operation_count') or '-'
        return f'Yes: kept {kept} of {original}, dropped {dropped}'

    @admin.display(description='Payload KB')
    def payload_size(self, obj):
        return topology_edit_payload_size_kb(obj)

    @admin.display(description='Payload compacted')
    def history_payload_compacted_status(self, obj):
        compaction = (obj.edit_payload or {}).get('history_payload_compaction') or {}
        if not (obj.edit_payload or {}).get('history_payload_compacted'):
            return 'No'
        size = compaction.get('original_size_bytes')
        if size:
            return f"Yes: original {round(size / 1024, 1)} KB"
        return 'Yes'

    @admin.display(description='Current baseline fingerprint')
    def current_baseline_fingerprint(self, obj):
        try:
            payload = build_project_sld_payload(obj.project_id, apply_topology=False)
        except Exception as error:
            return f'Unavailable: {error}'
        return payload_fingerprint(payload)

    @admin.display(description='Baseline changed')
    def baseline_changed_status(self, obj):
        current = self.current_baseline_fingerprint(obj)
        if not obj.baseline_fingerprint or str(current).startswith('Unavailable:'):
            return 'Unknown'
        return 'Yes' if obj.baseline_fingerprint != current else 'No'

    @admin.display(description='Validation')
    def validation_status(self, obj):
        return (obj.validation_summary or {}).get('status') or '-'

    @admin.display(description='Chain audit summary')
    def chain_audit_summary(self, obj):
        audit = (obj.edit_payload or {}).get('topology_chain_audit') or {}
        compaction = (obj.edit_payload or {}).get('topology_chain_compaction') or {}
        if not audit and not compaction:
            return 'No chain audit metadata recorded.'
        return _preformatted(_json_pretty({
            'topology_chain_audit': audit,
            'topology_chain_compaction': compaction,
        }))

    @admin.display(description='Operation history')
    def operation_history(self, obj):
        operations = self._operations(obj)
        if not operations and self._operation_audit_summary(obj):
            return _preformatted(_json_pretty({
                'audit_only': True,
                'operations': self._operation_audit_summary(obj),
            }))
        if not operations:
            return 'No replayable operation records are stored for this edit.'

        lines = []
        for index, operation in enumerate(operations, start=1):
            preview = operation.get('preview') if isinstance(operation, dict) else {}
            preview = preview if isinstance(preview, dict) else {}
            lines.append(
                '\n'.join([
                    f"#{index} {operation.get('operation_type') or 'unknown'}",
                    f"  schema_version: {operation.get('schema_version') or '-'}",
                    f"  inputs: {_json_pretty(operation.get('inputs') or {})}",
                    f"  warning: {preview.get('warning') or '-'}",
                    f"  recommended_breaker_rating: {preview.get('recommended_breaker_rating') or '-'}",
                ])
            )
        return _preformatted('\n\n'.join(lines))

    @admin.display(description='Replay diagnostic')
    def replay_diagnostic(self, obj):
        operations = self._operations(obj)
        if (obj.edit_payload or {}).get('history_payload_compacted'):
            return 'Not replayed: this old history row was compacted to audit-only payload storage.'
        if not operations:
            return 'No operation chain is available to replay.'
        if (obj.edit_payload or {}).get('topology_chain_compacted') and self.baseline_changed_status(obj) == 'Yes':
            return (
                'Not replayed: this chain was compacted and the generated baseline changed. '
                'The edit should remain review-required until an engineer reapplies or resets it.'
            )

        try:
            generated_payload = build_project_sld_payload(obj.project_id, apply_topology=False)
            from eht.sld_topology_workflows import replay_topology_operations
            replay = replay_topology_operations(obj.project_id, generated_payload, operations)
        except Exception as error:
            return f'Replay diagnostic failed before replay: {error}'

        if not replay.get('ok'):
            return _preformatted(_json_pretty({
                'ok': False,
                'failed_operation_index': replay.get('failed_operation_index'),
                'failed_operation_type': replay.get('failed_operation_type'),
                'error': replay.get('error') or 'Replay failed.',
            }))

        invariant_summary = validate_sld_topology_invariants(replay['payload'])
        return _preformatted(_json_pretty({
            'ok': True,
            'operation_count': len(operations),
            'topology_invariants': invariant_summary,
        }))

    @admin.display(description='Validation summary')
    def validation_summary_pretty(self, obj):
        return _preformatted(_json_pretty(obj.validation_summary))

    @admin.display(description='Edit payload')
    def edit_payload_pretty(self, obj):
        return _preformatted(_json_pretty(obj.edit_payload))

    @admin.display(description='Generated snapshot')
    def generated_snapshot_pretty(self, obj):
        return _preformatted(_json_pretty(obj.generated_snapshot))

    @admin.action(description='Compact selected old topology history records')
    def compact_selected_history_records(self, request, queryset):
        compacted = 0
        skipped = 0
        saved_bytes = 0
        for edit in queryset:
            result = compact_topology_edit_record(edit, reason='admin_selected_history_compaction')
            if result.get('ok') and result.get('changed'):
                compacted += 1
                saved_bytes += result.get('saved_size_bytes') or 0
            else:
                skipped += 1

        self.message_user(
            request,
            f'Compacted {compacted} topology history row(s), skipped {skipped}; '
            f'freed approximately {round(saved_bytes / 1024, 1)} KB of JSON payload.',
        )

    @admin.action(
        permissions=['delete'],
        description='Emergency delete selected non-active topology history records',
    )
    def emergency_delete_selected_non_active_history_records(self, request, queryset):
        deletable = queryset.filter(status__in=DELETABLE_HISTORY_STATUSES)
        skipped = queryset.exclude(status__in=DELETABLE_HISTORY_STATUSES).count()
        deleted_count = deletable.count()
        deletable.delete()

        self.message_user(
            request,
            f'Emergency-deleted {deleted_count} non-active topology history row(s). '
            f'Skipped {skipped} protected applied/needs-review row(s).',
            level=messages.WARNING if deleted_count else messages.INFO,
        )


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
