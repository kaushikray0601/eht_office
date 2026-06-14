import math
import logging

from eht.calculations.tag_management import ProjectTagFactory, build_connection


SR_PER_CIRCUIT_BREAKER_RULE_SET = 'SR_PER_CIRCUIT_BREAKER_SIZING_V1'
SR_TERMINATION_MARGIN_RULE_SET = 'SR_TERMINATION_MARGIN_INSTALLATION_ALLOWANCE_V1'
MI_SINGLE_HEATER_BREAKER_RULE_SET = 'MI_SINGLE_HEATER_BREAKER_SIZING_MVP_V1'
MI_MULTI_HEATER_BREAKER_RULE_SET = 'MI_MULTI_HEATER_SET_BREAKER_SIZING_MVP_V1'
BREAKER_SIZES = [2, 4, 6, 10, 16, 20, 25, 32, 40]
SR_POWER_COEFFICIENT_KEYS = ('A_Coeff', 'B_Coeff', 'C_Coeff')


def _select_breaker_size(required_current, max_cb_size):
    candidates = [size for size in BREAKER_SIZES if size <= max_cb_size]
    if not candidates:
        candidates = BREAKER_SIZES
    return next((size for size in candidates if size >= required_current), max_cb_size)


def _sr_power_coefficients(selected_tracer):
    coefficients = []
    invalid_keys = []
    for key in SR_POWER_COEFFICIENT_KEYS:
        try:
            coefficients.append(float(selected_tracer[key]))
        except (KeyError, TypeError, ValueError):
            invalid_keys.append(key)

    if invalid_keys:
        tracer_uid = selected_tracer.get('V_UID') or selected_tracer.get('selected_tracer') or 'unknown'
        logging.error(
            "SR tracer %s has missing or non-numeric power coefficient(s): %s",
            tracer_uid,
            ', '.join(invalid_keys),
        )
        return None
    return tuple(coefficients)


def compute_power_params(line, project_settings, asme_data, selected_tracer):
    """
    Computes electrical parameters for each heating circuit.
    1. Computes number of circuits based on max breaker size.
    2. Assigns appropriate breaker rating.
    3. Computes operating current, max current, and operating load.
    4. Applies termination margin and other accessory margins.
    Returns:
        - no_of_circuits
        - breaker_size
        - operating_current
        - max_current
        - operating_load
        - total_tracer_length
    """
    try:
        voltage = project_settings['voltage']
        max_cb_size = project_settings['max_cb_size']
        margin_on_max_cb_size = project_settings['restrict_cb_current'] / 100  # Convert percentage to fraction     
        tracer_length = float(selected_tracer['Tracer_With_Margin'])
        coefficients = _sr_power_coefficients(selected_tracer)
        if coefficients is None:
            return None
        tracer_A_const, tracer_B_const, tracer_C_const = coefficients
        min_amb_temp = float(project_settings['min_amb_t'])
        operating_temp = float(line['oper_temp'])
        nominal_voltage_correction = float(
            selected_tracer.get('Voltage_Correction_Factor_Nominal', selected_tracer['Voltage_Correction_Factor'])
        )
        max_current_voltage_correction = float(
            selected_tracer.get('Voltage_Correction_Factor_Max_Current', nominal_voltage_correction)
        )
        max_current_voltage = float(selected_tracer.get('Max_Current_Voltage', voltage))
        sr_parallel_run_count = max(1, int(selected_tracer.get('SR_Parallel_Run_Count') or 1))
        sr_grouped_parallel_runs = sr_parallel_run_count > 1
        per_run_tracer_length = float(
            selected_tracer.get('SR_Per_Run_Tracer_Length')
            or (tracer_length / sr_parallel_run_count)
        )
        per_run_tracer_length_with_margin = per_run_tracer_length * (
            1 + float(project_settings['margin_on_tracer_lengths']) / 100
        )
   
        # Compute line-level currents before circuit splitting.
        if sr_grouped_parallel_runs:
            per_run_maximum_current = (
                (tracer_A_const * min_amb_temp**2 + tracer_B_const * min_amb_temp + tracer_C_const)
                * (per_run_tracer_length_with_margin * max_current_voltage_correction)
            ) / max_current_voltage
            per_run_operating_current = (
                (tracer_A_const * operating_temp**2 + tracer_B_const * operating_temp + tracer_C_const)
                * (per_run_tracer_length_with_margin * nominal_voltage_correction)
            ) / voltage
            line_maximum_current = per_run_maximum_current * sr_parallel_run_count
            line_operating_current = per_run_operating_current * sr_parallel_run_count
        else:
            line_maximum_current = (
                (tracer_A_const * min_amb_temp**2 + tracer_B_const * min_amb_temp + tracer_C_const)
                * (tracer_length * max_current_voltage_correction)
            ) / max_current_voltage

            line_operating_current = (
                (tracer_A_const * operating_temp**2 + tracer_B_const * operating_temp + tracer_C_const)
                * (tracer_length * nominal_voltage_correction)
            ) / voltage

        allowed_current_per_circuit = max_cb_size * margin_on_max_cb_size
        if allowed_current_per_circuit <= 0:
            raise ValueError("Maximum breaker size and loading restriction must allow positive current.")

        # Compute No. of Circuits Required from line current, then size each circuit.
        if sr_grouped_parallel_runs:
            no_of_circuits = sr_parallel_run_count
            per_circuit_max_current = per_run_maximum_current
            per_circuit_operating_current = per_run_operating_current
        else:
            no_of_circuits = max(1, math.ceil(line_maximum_current / allowed_current_per_circuit))
            per_circuit_max_current = line_maximum_current / no_of_circuits
            per_circuit_operating_current = line_operating_current / no_of_circuits

        # Breaker Size Selection
        required_breaker_current = (
            line_maximum_current / margin_on_max_cb_size
            if sr_grouped_parallel_runs
            else per_circuit_max_current / margin_on_max_cb_size
        )
        breaker_size = _select_breaker_size(required_breaker_current, max_cb_size)
        
        # Compute Operating Load
        operating_load = line_operating_current * voltage
        
        # Termination margin is an installation allowance, not energized heat-delivery length.
        heated_tracer_length = tracer_length
        termination_margin_per_circuit_m = float(project_settings['termination_margin']) / 1000
        termination_margin_length = no_of_circuits * termination_margin_per_circuit_m
        total_tracer_length = heated_tracer_length + termination_margin_length
       
        outer_dia_mm = asme_data.loc[asme_data['Nominal_Pipe_Size'] == float(line['line_size']), 'Outside_Diameter_mm']
        pipe_size_mm = outer_dia_mm.iloc[0] if not outer_dia_mm.empty else 25.206 * float(line['line_size']) + 9.4852
        return {
            'uid': line['uid'],
            'line_id': line.get('line_id', str(line['uid'])),
            'project_id': project_settings.get('proj_id'),
            'selected_tracer': selected_tracer.get('V_UID', ''),
            'tracer_family': selected_tracer.get('Tracer_Family', 'SR'),
            'no_of_circuits': no_of_circuits,
            'breaker_size': breaker_size,
            'operating_current': per_circuit_operating_current,
            'max_current': per_circuit_max_current,
            'line_operating_current': line_operating_current,
            'line_max_current': line_maximum_current,
            'per_circuit_operating_current': per_circuit_operating_current,
            'per_circuit_max_current': per_circuit_max_current,
            'operating_load': operating_load,
            'total_tracer_length': total_tracer_length,
            'heated_tracer_length': heated_tracer_length,
            'sr_parallel_run_count': sr_parallel_run_count,
            'sr_parallel_run_basis': selected_tracer.get('SR_Parallel_Run_Basis', ''),
            'sr_constructability_warning': selected_tracer.get('SR_Constructability_Warning', ''),
            'sr_per_run_tracer_length': per_run_tracer_length,
            'sr_per_run_tracer_length_with_margin': per_run_tracer_length_with_margin,
            'sr_independent_parallel_runs': False,
            'termination_margin_length': termination_margin_length,
            'termination_margin_per_circuit_m': termination_margin_per_circuit_m,
            'termination_margin_basis': {
                'rule_set': SR_TERMINATION_MARGIN_RULE_SET,
                'semantics': 'installation_allowance_excluded_from_electrical_load',
                'source_field': 'ProjectData.termination_margin',
            },
            'breaker_sizing': {
                'rule_set': SR_PER_CIRCUIT_BREAKER_RULE_SET,
                'max_cb_size': max_cb_size,
                'restricted_loading_factor': margin_on_max_cb_size,
                'allowed_current_per_circuit': allowed_current_per_circuit,
                'required_breaker_current': required_breaker_current,
                'sr_parallel_run_count': sr_parallel_run_count,
                'sr_independent_parallel_runs': False,
                'sr_grouped_parallel_runs': sr_grouped_parallel_runs,
            },
            'voltage_scenarios': {
                'operating_voltage': voltage,
                'max_current_voltage': max_current_voltage,
                'nominal_voltage_correction': nominal_voltage_correction,
                'max_current_voltage_correction': max_current_voltage_correction,
            },
            'pipe_size_mm':pipe_size_mm if pipe_size_mm else 0
        }
    except Exception as e:
        logging.error(f"Error in power parameter computation for UID {line['uid']}: {str(e)}")
        return None


def _pipe_size_mm(line, asme_data):
    outer_dia_mm = asme_data.loc[asme_data['Nominal_Pipe_Size'] == float(line['line_size']), 'Outside_Diameter_mm']
    return outer_dia_mm.iloc[0] if not outer_dia_mm.empty else 25.206 * float(line['line_size']) + 9.4852


def compute_mi_power_params(line, project_settings, asme_data, selected_mi_heater):
    """Build panel-loading parameters for selected MI heater set(s)."""
    try:
        voltage = float(project_settings['voltage'])
        max_cb_size = float(project_settings['max_cb_size'])
        restricted_loading_factor = float(project_settings['restrict_cb_current']) / 100.0
        if restricted_loading_factor <= 0:
            raise ValueError("Maximum breaker loading restriction must be positive.")

        heater_set_count = max(1, int(selected_mi_heater.get('heater_set_count') or 1))
        per_set_operating_current = float(selected_mi_heater.get('current_nominal_a') or 0.0)
        per_set_maximum_current = float(selected_mi_heater.get('current_cold_start_a') or per_set_operating_current)
        line_operating_current = per_set_operating_current * heater_set_count
        line_maximum_current = per_set_maximum_current * heater_set_count
        required_breaker_current = per_set_maximum_current / restricted_loading_factor
        breaker_size = _select_breaker_size(required_breaker_current, max_cb_size)
        operating_load = float(selected_mi_heater.get('power_nominal_w') or (line_operating_current * voltage))
        heated_length_m = float(selected_mi_heater.get('heated_length_m') or line.get('line_length') or 0.0)
        total_heated_length_m = heated_length_m * heater_set_count

        return {
            'uid': line['uid'],
            'line_id': line.get('line_id', str(line['uid'])),
            'project_id': project_settings.get('proj_id'),
            'calculation_basis': 'MI_MULTI_HEATER_SET_MVP' if heater_set_count > 1 else 'MI_SINGLE_HEATER_MVP',
            'selected_tracer': selected_mi_heater.get('heater_part_number', 'MI heater'),
            'tracer_family': 'MI',
            'heater_set_count': heater_set_count,
            'no_of_circuits': heater_set_count,
            'breaker_size': breaker_size,
            'operating_current': per_set_operating_current,
            'max_current': per_set_maximum_current,
            'line_operating_current': line_operating_current,
            'line_max_current': line_maximum_current,
            'per_circuit_operating_current': per_set_operating_current,
            'per_circuit_max_current': per_set_maximum_current,
            'operating_load': operating_load,
            'total_tracer_length': total_heated_length_m,
            'heated_tracer_length': heated_length_m,
            'total_heated_tracer_length': total_heated_length_m,
            'termination_margin_length': 0.0,
            'termination_margin_per_circuit_m': 0.0,
            'termination_margin_basis': {
                'rule_set': 'MI_FACTORY_TERMINATION_LENGTH_BASIS_MVP_V1',
                'semantics': 'factory_terminated_mi_heater_set_no_sr_field_termination_allowance',
            },
            'breaker_sizing': {
                'rule_set': MI_MULTI_HEATER_BREAKER_RULE_SET if heater_set_count > 1 else MI_SINGLE_HEATER_BREAKER_RULE_SET,
                'max_cb_size': max_cb_size,
                'restricted_loading_factor': restricted_loading_factor,
                'allowed_current_per_circuit': max_cb_size * restricted_loading_factor,
                'required_breaker_current': required_breaker_current,
                'single_heater_set': heater_set_count == 1,
                'heater_set_count': heater_set_count,
            },
            'voltage_scenarios': {
                'operating_voltage': voltage,
                'max_current_voltage': voltage * (1.0 + max(float(project_settings.get('voltage_var_factor') or 0.0), 0.0) / 100.0),
            },
            'pipe_size_mm': _pipe_size_mm(line, asme_data),
        }
    except Exception as e:
        logging.error(f"Error in MI power parameter computation for UID {line['uid']}: {str(e)}")
        return None

def _upstream_connection_chain(components):
    chain = [component for component in components if component]
    return [build_connection(chain[index], chain[index + 1]) for index in range(len(chain) - 1)]


def _mi_heater_set_metadata(power_params, heater_set_index):
    if power_params.get('tracer_family') != 'MI':
        return {}

    heater_set_count = int(power_params.get('heater_set_count') or power_params.get('no_of_circuits') or 1)
    return {
        'heating_cable_type': 'MI',
        'mi_group_id': f"{power_params.get('project_id') or 'project'}:{power_params.get('uid')}:MI:{power_params.get('selected_tracer')}",
        'mi_heater_part_number': power_params.get('selected_tracer'),
        'mi_heater_set_index': heater_set_index,
        'mi_heater_set_count': heater_set_count,
        'mi_independent_protection': True,
        'per_set_operating_current': power_params.get('operating_current'),
        'per_set_max_current': power_params.get('max_current'),
        'line_operating_current': power_params.get('line_operating_current'),
        'line_max_current': power_params.get('line_max_current'),
    }


def _sr_parallel_run_metadata(power_params, run_index):
    sr_parallel_run_count = int(power_params.get('sr_parallel_run_count') or 1)
    if sr_parallel_run_count <= 1:
        return {}

    metadata = {
        'heating_cable_type': 'SR',
        'sr_parallel_group_id': (
            f"{power_params.get('project_id') or 'project'}:"
            f"{power_params.get('uid')}:SR:{power_params.get('selected_tracer', 'tracer')}"
        ),
        'sr_parallel_run_count': sr_parallel_run_count,
        'sr_parallel_run_basis': power_params.get('sr_parallel_run_basis', ''),
        'per_run_tracer_length_m': power_params.get('sr_per_run_tracer_length_with_margin'),
        'per_run_operating_current': power_params.get('operating_current'),
        'per_run_max_current': power_params.get('max_current'),
        'line_operating_current': power_params.get('line_operating_current'),
        'line_max_current': power_params.get('line_max_current'),
    }
    if power_params.get('sr_independent_parallel_runs'):
        metadata.update({
            'sr_parallel_run_index': run_index,
            'sr_independent_protection': True,
            'sr_shared_mcb': False,
        })
    else:
        metadata.update({
            'sr_shared_mcb': True,
            'sr_independent_protection': False,
        })
    return metadata


def compute_power_distribution(power_params, project_settings, tag_factory=None):
    """
    Compute the power distribution for a given process line and include tagging logic.

    Args:
        process_line (dict): Process line data containing line attributes and circuit details.
        project_settings (dict): Project-specific settings.

    Returns:
        dict: Power distribution results with tagging and relationships.
    """
    tag_factory = tag_factory or ProjectTagFactory(power_params.get('project_id') or project_settings.get('proj_id'))

    power_distribution_results = {
        "uid": power_params["uid"],
        "line_id": power_params.get("line_id"),
        "total_circuits": power_params["no_of_circuits"],
        "branches": []
    }

    total_circuits = power_params["no_of_circuits"]
    remaining_circuits = total_circuits
    isolator_setting = project_settings.get('isolator_location', 'none')
    line_uid = power_params["uid"]
    line_id = power_params.get("line_id", str(line_uid))
    branch_index = 0
    mi_independent_sets = power_params.get('tracer_family') == 'MI'
    sr_independent_runs = bool(power_params.get('sr_independent_parallel_runs'))

    # Process circuits in batches of 3
    while remaining_circuits > 0:
        branch_index += 1
        circuits_in_this_batch = 1 if (mi_independent_sets or sr_independent_runs) else min(4, remaining_circuits)
        remaining_circuits -= circuits_in_this_batch

        branch_type = "3phJB" if circuits_in_this_batch > 1 else "1phJB"
        connected_to = (
            "4x 1phJB" if circuits_in_this_batch == 4
            else "3x 1phJB" if circuits_in_this_batch == 3
            else "2x 1phJB" if circuits_in_this_batch == 2
            else "Tracer"
        )
        mi_metadata = _mi_heater_set_metadata(power_params, branch_index)
        sr_metadata = _sr_parallel_run_metadata(power_params, branch_index)
        heater_metadata = {**sr_metadata, **mi_metadata}

        tagged_components = {
            "schema_version": 1,
            "component_details": {},
            "Downstream": [],
            "connections": [],
        }
        if mi_metadata:
            tagged_components["heating_cable_type"] = "MI"
            tagged_components["mi_group_id"] = mi_metadata["mi_group_id"]
            tagged_components["mi_heater_set_index"] = mi_metadata["mi_heater_set_index"]
            tagged_components["mi_heater_set_count"] = mi_metadata["mi_heater_set_count"]
        if sr_metadata:
            tagged_components["heating_cable_type"] = "SR"
            tagged_components["sr_parallel_group_id"] = sr_metadata["sr_parallel_group_id"]
            tagged_components["sr_parallel_run_count"] = sr_metadata["sr_parallel_run_count"]
            tagged_components["sr_parallel_run_basis"] = sr_metadata.get("sr_parallel_run_basis", "")
            tagged_components["sr_shared_mcb"] = sr_metadata.get("sr_shared_mcb", False)
            if "sr_parallel_run_index" in sr_metadata:
                tagged_components["sr_parallel_run_index"] = sr_metadata["sr_parallel_run_index"]

        mcb_component = tag_factory.create_component(
            "MCB",
            line_uid=line_uid,
            line_id=line_id,
            branch_index=branch_index,
            sequence_index=1,
            metadata={
                "breaker_size": power_params["breaker_size"],
                "max_current": power_params.get("max_current"),
                "operating_current": power_params.get("operating_current"),
                "line_max_current": power_params.get("line_max_current"),
                "line_operating_current": power_params.get("line_operating_current"),
                "breaker_sizing": power_params.get("breaker_sizing", {}),
                "branch_type": branch_type,
                **heater_metadata,
            },
        )
        tagged_components["MCB"] = mcb_component["display_tag"]
        tagged_components["component_details"]["MCB"] = mcb_component

        branch = {
            "type": branch_type,
            "circuit_count": circuits_in_this_batch,
            "connected_to": connected_to,
            "cable_length_db_to_jb": project_settings["ckt_ln"],
            "cable_length_jb_to_jb": project_settings["loop_ln"] if circuits_in_this_batch > 1 else None,
            "tagged_components": tagged_components,
        }

        if branch_type == "3phJB":
            cable4c_component = tag_factory.create_component(
                "Cable4C",
                line_uid=line_uid,
                line_id=line_id,
                branch_index=branch_index,
                sequence_index=2,
                metadata={
                    "length_m": project_settings["ckt_ln"],
                    "cable_role": "MCB_TO_JB3PH",
                    **heater_metadata,
                },
            )
            tagged_components["Cable4C"] = cable4c_component["display_tag"]
            tagged_components["component_details"]["Cable4C"] = cable4c_component

            isolator_3ph_component = None
            if isolator_setting in ['bothSides', 'incomingOnly']:
                isolator_3ph_component = tag_factory.create_component(
                    "Isolator3PH",
                    line_uid=line_uid,
                    line_id=line_id,
                    branch_index=branch_index,
                    sequence_index=3,
                    metadata={"location": "incoming", **heater_metadata},
                )
                tagged_components["Isolator3PH"] = isolator_3ph_component["display_tag"]
                tagged_components["component_details"]["Isolator3PH"] = isolator_3ph_component
            else:
                tagged_components["Isolator3PH"] = None

            jb3ph_component = tag_factory.create_component(
                "JB3PH",
                line_uid=line_uid,
                line_id=line_id,
                branch_index=branch_index,
                sequence_index=4,
                metadata={"circuit_count": circuits_in_this_batch, **heater_metadata},
            )
            tagged_components["JB3PH"] = jb3ph_component["display_tag"]
            tagged_components["component_details"]["JB3PH"] = jb3ph_component

            tagged_components["connections"].extend(
                _upstream_connection_chain([
                    mcb_component,
                    cable4c_component,
                    isolator_3ph_component,
                    jb3ph_component,
                ])
            )
            downstream_root = jb3ph_component
            cable_length_to_jb = project_settings["loop_ln"]
        else:
            tagged_components["Cable4C"] = None
            tagged_components["Isolator3PH"] = None
            tagged_components["JB3PH"] = None
            downstream_root = mcb_component
            cable_length_to_jb = project_settings["ckt_ln"]

        for circuit_index in range(1, circuits_in_this_batch + 1):
            downstream_details = {}
            downstream = {
                "circuit_index": circuit_index,
                "component_details": downstream_details,
            }
            downstream_components = []

            if isolator_setting in ['bothSides', 'outgoingOnly']:
                downstream_metadata = (
                    {**heater_metadata, "mi_heater_set_index": branch_index}
                    if heater_metadata
                    else {}
                )
                isolator_1ph_component = tag_factory.create_component(
                    "Isolator1PH",
                    line_uid=line_uid,
                    line_id=line_id,
                    branch_index=branch_index,
                    sequence_index=5,
                    circuit_index=circuit_index,
                    metadata={"location": "outgoing", **downstream_metadata},
                )
                downstream["Isolator1PH"] = isolator_1ph_component["display_tag"]
                downstream_details["Isolator1PH"] = isolator_1ph_component
                downstream_components.append(isolator_1ph_component)

            cable3c_component = tag_factory.create_component(
                "Cable3C",
                line_uid=line_uid,
                line_id=line_id,
                branch_index=branch_index,
                sequence_index=6,
                circuit_index=circuit_index,
                metadata={
                    "length_m": cable_length_to_jb,
                    "cable_role": "JB_TO_1PHJB" if branch_type == "3phJB" else "MCB_TO_1PHJB",
                    **(
                        {**heater_metadata, "mi_heater_set_index": branch_index}
                        if heater_metadata
                        else {}
                    ),
                },
            )
            downstream["Cable3C"] = cable3c_component["display_tag"]
            downstream_details["Cable3C"] = cable3c_component
            downstream_components.append(cable3c_component)

            jb1ph_component = tag_factory.create_component(
                "JB1PH",
                line_uid=line_uid,
                line_id=line_id,
                branch_index=branch_index,
                sequence_index=7,
                circuit_index=circuit_index,
                metadata={
                    "branch_type": branch_type,
                    **(
                        {**heater_metadata, "mi_heater_set_index": branch_index}
                        if heater_metadata
                        else {}
                    ),
                },
            )
            downstream["JB1PH"] = jb1ph_component["display_tag"]
            downstream_details["JB1PH"] = jb1ph_component
            downstream_components.append(jb1ph_component)

            tracer_component = tag_factory.create_component(
                "Tracer",
                line_uid=line_uid,
                line_id=line_id,
                branch_index=branch_index,
                sequence_index=8,
                circuit_index=circuit_index,
                metadata=(
                    {**heater_metadata, "mi_heater_set_index": branch_index}
                    if heater_metadata
                    else None
                ),
            )
            downstream["Tracer"] = tracer_component["display_tag"]
            downstream_details["Tracer"] = tracer_component
            downstream_components.append(tracer_component)

            end_term_component = tag_factory.create_component(
                "EndTermination",
                line_uid=line_uid,
                line_id=line_id,
                branch_index=branch_index,
                sequence_index=9,
                circuit_index=circuit_index,
                metadata=(
                    {**heater_metadata, "mi_heater_set_index": branch_index}
                    if heater_metadata
                    else None
                ),
            )
            downstream["EndTermination"] = end_term_component["display_tag"]
            downstream_details["EndTermination"] = end_term_component
            downstream_components.append(end_term_component)

            tagged_components["Downstream"].append(downstream)

            first_downstream_component = downstream_components[0]
            tagged_components["connections"].append(build_connection(downstream_root, first_downstream_component))
            tagged_components["connections"].extend(
                _upstream_connection_chain(downstream_components)
            )

        # Append branch to results
        power_distribution_results["branches"].append(branch)

    return power_distribution_results
