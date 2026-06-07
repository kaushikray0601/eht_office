import json
from copy import deepcopy

from django.db import transaction
from django.utils import timezone

from .models import SLDTopologyEdit


FULL_HISTORY_STATUSES = ('superseded', 'reset')
PROTECTED_HISTORY_STATUSES = ('applied', 'needs_review')
DELETABLE_HISTORY_STATUSES = ('draft', 'superseded', 'reset')


def json_size_bytes(value):
    return len(json.dumps(value or {}, default=str, separators=(',', ':')).encode('utf-8'))


def topology_edit_payload_size_bytes(edit):
    return (
        json_size_bytes(edit.generated_snapshot)
        + json_size_bytes(edit.edit_payload)
        + json_size_bytes(edit.validation_summary)
    )


def topology_edit_payload_size_kb(edit):
    return round(topology_edit_payload_size_bytes(edit) / 1024, 1)


def _operation_audit_summary(operations):
    if not isinstance(operations, list):
        return []

    summary = []
    for index, operation in enumerate(operations, start=1):
        if not isinstance(operation, dict):
            summary.append({'index': index, 'operation_type': 'invalid_record'})
            continue
        preview = operation.get('preview') if isinstance(operation.get('preview'), dict) else {}
        summary.append({
            'index': index,
            'schema_version': operation.get('schema_version'),
            'operation_type': operation.get('operation_type') or 'unknown',
            'inputs': deepcopy(operation.get('inputs') or {}),
            'warning': preview.get('warning') or '',
            'recommended_breaker_rating': preview.get('recommended_breaker_rating'),
        })
    return summary


def compact_topology_edit_record(edit, *, reason='retention_policy', dry_run=False):
    if edit.status in PROTECTED_HISTORY_STATUSES:
        return {'ok': False, 'reason': f'protected_status:{edit.status}', 'edit_id': edit.pk}

    edit_payload = deepcopy(edit.edit_payload or {})
    operations = edit_payload.get('topology_operations')
    before_size = topology_edit_payload_size_bytes(edit)
    already_compacted = bool(edit_payload.get('history_payload_compacted'))

    if already_compacted and not edit.generated_snapshot:
        return {
            'ok': True,
            'changed': False,
            'reason': 'already_compacted',
            'edit_id': edit.pk,
            'before_size_bytes': before_size,
            'after_size_bytes': before_size,
            'saved_size_bytes': 0,
        }

    retained_payload = {
        'history_payload_compacted': True,
        'history_payload_compaction': {
            'reason': reason,
            'compacted_at': timezone.now().isoformat(),
            'original_size_bytes': before_size,
            'dropped_keys': [
                key for key in (
                    'sld_payload',
                    'cable_schedule_rows',
                    'combine_preview',
                    'split_preview',
                    'downstream_jb_preview',
                    'attach_to_jb_preview',
                    'move_branch_to_jb_preview',
                ) if key in edit_payload
            ],
            'operation_count': len(operations) if isinstance(operations, list) else 0,
        },
        'topology_operation_audit_summary': _operation_audit_summary(operations),
    }

    for key in (
        'topology_chain_audit',
        'topology_chain_compacted',
        'topology_chain_compaction',
    ):
        if key in edit_payload:
            retained_payload[key] = deepcopy(edit_payload[key])

    if dry_run:
        probe = deepcopy(edit)
        probe.generated_snapshot = {}
        probe.edit_payload = retained_payload
        after_size = topology_edit_payload_size_bytes(probe)
        return {
            'ok': True,
            'changed': True,
            'dry_run': True,
            'edit_id': edit.pk,
            'before_size_bytes': before_size,
            'after_size_bytes': after_size,
            'saved_size_bytes': max(before_size - after_size, 0),
        }

    edit.generated_snapshot = {}
    edit.edit_payload = retained_payload
    edit.save(update_fields=['generated_snapshot', 'edit_payload', 'updated_at'])
    after_size = topology_edit_payload_size_bytes(edit)
    return {
        'ok': True,
        'changed': True,
        'edit_id': edit.pk,
        'before_size_bytes': before_size,
        'after_size_bytes': after_size,
        'saved_size_bytes': max(before_size - after_size, 0),
    }


def compact_sld_topology_history(*, project_id=None, keep_full=20, keep_reset=10, dry_run=False, reason='retention_policy'):
    keep_full = max(int(keep_full), 0)
    keep_reset = max(int(keep_reset), 0)
    qs = SLDTopologyEdit.objects.select_related('project').order_by('project_id', '-created_at', '-id')
    if project_id:
        qs = qs.filter(project_id=project_id)

    candidates = []
    project_ids = qs.order_by('project_id').values_list('project_id', flat=True).distinct()
    for current_project_id in project_ids:
        superseded_full_payload = [
            edit for edit in qs.filter(project_id=current_project_id, status='superseded').order_by('-created_at', '-id')
            if not (edit.edit_payload or {}).get('history_payload_compacted')
        ]
        reset_full_payload = [
            edit for edit in qs.filter(project_id=current_project_id, status='reset').order_by('-created_at', '-id')
            if not (edit.edit_payload or {}).get('history_payload_compacted')
        ]
        superseded = superseded_full_payload[keep_full:]
        reset = reset_full_payload[keep_reset:]
        candidates.extend(superseded)
        candidates.extend(reset)

    summary = {
        'candidate_count': len(candidates),
        'compacted_count': 0,
        'skipped_count': 0,
        'saved_size_bytes': 0,
        'dry_run': dry_run,
        'results': [],
    }

    context = transaction.atomic() if not dry_run else transaction.atomic()
    with context:
        for edit in candidates:
            result = compact_topology_edit_record(edit, reason=reason, dry_run=dry_run)
            summary['results'].append(result)
            if result.get('ok') and result.get('changed'):
                summary['compacted_count'] += 1
                summary['saved_size_bytes'] += result.get('saved_size_bytes') or 0
            else:
                summary['skipped_count'] += 1
        if dry_run:
            transaction.set_rollback(True)

    return summary
