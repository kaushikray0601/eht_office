import logging

import pandas as pd

from eht.calculations.boq import compute_bill_of_quantities
from eht.calculations.heat_loss import calculate_heat_loss
from eht.calculations.power_distribution import compute_power_distribution, compute_power_params
from eht.calculations.tracer_selection import get_tracer_options


logger = logging.getLogger(__name__)


def _ensure_process_lines_df(process_lines):
    if isinstance(process_lines, pd.DataFrame):
        return process_lines
    return pd.DataFrame(process_lines)


def orchestrate_calculations(process_lines, vendor_data, project_settings, asme_b36_table, thermal_cond_data):
    """Run the active heat-tracing pipeline and return the aggregated payload."""
    aggregated_results = {
        "heat_loss": [],
        "selected_tracers": [],
        "alternative_tracers": [],
        "power_distribution": [],
        "boq_per_line": {},
        "consolidated_boq": {},
        "tracer_power_param": [],
    }
    process_lines_df = _ensure_process_lines_df(process_lines)
    if process_lines_df.empty:
        return aggregated_results

    for _, line in process_lines_df.iterrows():
        try:
            heat_loss = calculate_heat_loss(line, project_settings, asme_b36_table, thermal_cond_data)
            if not heat_loss:
                continue
            aggregated_results["heat_loss"].append(heat_loss)

            selected_tracer, alternative_tracers = get_tracer_options(
                heat_loss,
                line,
                project_settings,
                vendor_data,
            )
            if not selected_tracer:
                continue

            selected_tracer = {**selected_tracer, "uid": line["uid"]}
            aggregated_results["selected_tracers"].append(selected_tracer)
            if isinstance(alternative_tracers, list):
                aggregated_results["alternative_tracers"].extend(
                    {**tracer, "uid": line["uid"]}
                    for tracer in alternative_tracers
                )

            power_params = compute_power_params(line, project_settings, asme_b36_table, selected_tracer)
            power_distribution = compute_power_distribution(power_params, project_settings)
            aggregated_results["power_distribution"].append(power_distribution)

            boq = compute_bill_of_quantities(
                power_distribution=power_distribution,
                project_settings=project_settings,
                tracer_qty=power_params["total_tracer_length"],
                line_length=line["line_length"],
                pipe_size_mm=power_params["pipe_size_mm"],
                is_process_temp_controlled=line["service_type"] == "EP",
            )
            line_uid = line["uid"]
            aggregated_results["boq_per_line"][line_uid] = boq
            aggregated_results["tracer_power_param"].append(power_params)

            for item, count in boq.items():
                aggregated_results["consolidated_boq"].setdefault(item, 0)
                aggregated_results["consolidated_boq"][item] += count

        except Exception:
            logger.exception("Error processing line UID %s", line.get("uid"))

    return aggregated_results
