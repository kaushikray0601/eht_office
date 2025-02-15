import pandas as pd
from eht.calculations.heat_loss import calculate_heat_loss
from eht.calculations.tracer_selection import get_tracer_options
from eht.calculations.power_distribution import compute_power_params, compute_power_distribution
from eht.calculations.boq import generate_boq, compute_bill_of_quantities

import logging
logger = logging.getLogger(__name__)


def orchestrate_calculations(project_id, process_lines, vendor_data, project_settings, asme_b36_table, thermal_cond_data):

    # Initialize aggregated result containers
    aggregated_results = {
        "heat_loss": [],
        "selected_tracers": [],
        "alternative_tracers": [],
        "power_distribution": [],
        "boq_per_line": {},  # Store BOQ per line (keyed by line UID)
        "consolidated_boq": {}  # Aggregated BOQ across all lines
    }

    # Loop through rows in the DataFrame
    for _, line in pd.DataFrame(process_lines).iterrows():
        try: 
            # Step-1: Heat Loss Calculation
            heat_loss = calculate_heat_loss(line, project_settings, asme_b36_table, thermal_cond_data)
            if not heat_loss:   continue
            aggregated_results["heat_loss"].append(heat_loss)

            # Step-2: Tracer Selection
            selected_tracer, alternative_tracers = get_tracer_options(heat_loss, line, project_settings, vendor_data)
            if not selected_tracer: continue
            aggregated_results["selected_tracers"].append(selected_tracer)
            if isinstance(alternative_tracers, list): 
                aggregated_results["alternative_tracers"].extend(alternative_tracers)
             
            # Step 3: Power Distribution
            power_params = compute_power_params(line, project_settings, asme_b36_table, selected_tracer) # adding asme_data data to append pipe-dia (mm), when returned to calculate BOQ later
            power_distribution = compute_power_distribution(power_params, project_settings)              # Step 3.1: Compute Power Distribution Strategy
            aggregated_results["power_distribution"].append(power_distribution)
            
            # Step 4: Bill of Quantities (BOQ) Calculation
            power_distribution_df= pd.DataFrame(power_distribution)
            boq = compute_bill_of_quantities(
                power_distribution_data=power_distribution_df, 
                project_settings=project_settings,
                tracer_qty=power_params["total_tracer_length"],
                line_length=line["line_length"],
                pipe_size_mm=power_params["pipe_size_mm"]
            )

            # Store BOQ for this line
            line_uid = line["uid"]
            aggregated_results["boq_per_line"][line_uid] = boq

             # Aggregate BOQ across lines
            for item, count in boq.items():
                aggregated_results["consolidated_boq"].setdefault(item, 0)
                aggregated_results["consolidated_boq"][item] += count

        except Exception as e:
            logging.error(f"Error processing line UID {line['uid']}: {str(e)}")

    return aggregated_results
