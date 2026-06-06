from django.db import OperationalError, ProgrammingError
from django.db.models import Count

from .models import CABLE_INSTALL_METHOD_CHOICES, ColdCableCatalogue


REQUIRED_COLD_CABLE_CORE_COUNTS = (3, 4)


def cold_cable_method_readiness(cable_standard, conductor_material, insulation_type):
    """Summarise validated cold-cable catalogue coverage by installation method."""
    summary = {
        method: {
            'method': method,
            'label': label,
            'validated_rows': 0,
            'core_counts': {},
            'missing_core_counts': list(REQUIRED_COLD_CABLE_CORE_COUNTS),
            'status': 'unavailable',
        }
        for method, label in CABLE_INSTALL_METHOD_CHOICES
    }
    try:
        rows = list(
            ColdCableCatalogue.objects.filter(
                cable_standard=cable_standard,
                conductor_material=conductor_material,
                insulation_type=insulation_type,
                is_validated=True,
            )
            .values('installation_method', 'core_count')
            .annotate(row_count=Count('id'))
        )
    except (OperationalError, ProgrammingError):
        return summary

    for row in rows:
        method = row['installation_method']
        if method not in summary:
            continue
        core_count = row['core_count']
        row_count = row['row_count']
        summary[method]['validated_rows'] += row_count
        summary[method]['core_counts'][core_count] = row_count

    for item in summary.values():
        item['missing_core_counts'] = [
            core_count
            for core_count in REQUIRED_COLD_CABLE_CORE_COUNTS
            if item['core_counts'].get(core_count, 0) == 0
        ]
        if not item['validated_rows']:
            item['status'] = 'unavailable'
        elif item['missing_core_counts']:
            item['status'] = 'partial'
        else:
            item['status'] = 'ready'
    return summary


def cold_cable_readiness_message(cable_standard, conductor_material, insulation_type):
    summary = cold_cable_method_readiness(cable_standard, conductor_material, insulation_type)
    ready = [item for item in summary.values() if item['status'] == 'ready']
    partial = [item for item in summary.values() if item['status'] == 'partial']
    unavailable = [item for item in summary.values() if item['status'] == 'unavailable']

    basis = f'{cable_standard}/{conductor_material}/{insulation_type}'
    parts = [f'Validated catalogue readiness for {basis}:']
    if ready:
        parts.append(
            'ready methods '
            + ', '.join(f"{item['method']} ({item['validated_rows']} rows)" for item in ready)
            + '.'
        )
    if partial:
        parts.append(
            'partial methods '
            + ', '.join(
                f"{item['method']} missing "
                + '/'.join(f'{core_count}C' for core_count in item['missing_core_counts'])
                for item in partial
            )
            + '.'
        )
    if unavailable:
        parts.append(
            'no validated rows for '
            + ', '.join(item['method'] for item in unavailable)
            + '; those selections remain visible but cold-cable sizing will be unsizeable until catalogue data is added.'
        )
    return ' '.join(parts)
