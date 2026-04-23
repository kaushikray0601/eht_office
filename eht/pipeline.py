import logging
from time import perf_counter

from django.conf import settings
from django.core.exceptions import ValidationError

from .cal import orchestrate_calculations
from .data_service import (
    fetch_asme_b36_table,
    fetch_process_lines,
    fetch_project_data,
    fetch_thermal_conductivity_data,
    fetch_vendor_data,
    store_calculated_results,
)
from .models import SELECT_VENDOR


logger = logging.getLogger(__name__)


def emit_timing(message):
    if not getattr(settings, "EHT_TIMING_LOGS", False):
        return
    print(message, flush=True)
    logger.warning(message)


def summarize_calculation_result(calculation_result):
    return {
        'heat_loss': len(calculation_result.get('heat_loss', [])),
        'selected_tracers': len(calculation_result.get('selected_tracers', [])),
        'alternative_tracers': len(calculation_result.get('alternative_tracers', [])),
        'power_distribution': len(calculation_result.get('power_distribution', [])),
        'boq_lines': len(calculation_result.get('boq_per_line', {})),
        'consolidated_boq_items': len(calculation_result.get('consolidated_boq', {})),
        'tracer_power_param': len(calculation_result.get('tracer_power_param', [])),
    }


def resolve_selected_vendor(vendor_code):
    return next(
        (vendor_name for code, vendor_name in SELECT_VENDOR if code == vendor_code),
        None,
    )


def run_project_calculations(project_id):
    """Run the single supported calculation pipeline for the given project."""
    overall_started = perf_counter()

    fetch_started = perf_counter()
    project_settings = fetch_project_data(project_id)
    selected_vendor = resolve_selected_vendor(project_settings['vendor'])
    if not selected_vendor:
        raise ValidationError("Selected vendor could not be resolved for this project.")

    process_lines = fetch_process_lines(project_id)
    if process_lines.empty:
        raise ValidationError("No confirmed input data found for this project.")
    vendor_data = fetch_vendor_data(selected_vendor, project_settings['voltage'])
    asme_b36_table = fetch_asme_b36_table()
    thermal_cond_data = fetch_thermal_conductivity_data()
    fetch_duration = perf_counter() - fetch_started

    orchestrate_started = perf_counter()
    calculation_result = orchestrate_calculations(
        process_lines=process_lines,
        vendor_data=vendor_data,
        project_settings=project_settings,
        asme_b36_table=asme_b36_table,
        thermal_cond_data=thermal_cond_data,
    )
    orchestrate_duration = perf_counter() - orchestrate_started

    store_started = perf_counter()
    store_calculated_results(project_id, calculation_result)
    store_duration = perf_counter() - store_started

    result_counts = summarize_calculation_result(calculation_result)
    total_duration = perf_counter() - overall_started
    emit_timing(
        "EHT timing | project={project} | rows={rows} | fetch={fetch:.3f}s | orchestrate={orchestrate:.3f}s | store={store:.3f}s | total={total:.3f}s | counts={counts}".format(
            project=project_id,
            rows=len(process_lines.index),
            fetch=fetch_duration,
            orchestrate=orchestrate_duration,
            store=store_duration,
            total=total_duration,
            counts=result_counts,
        )
    )
    return calculation_result, result_counts
