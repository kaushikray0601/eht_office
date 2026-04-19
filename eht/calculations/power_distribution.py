import math
import logging

from eht.calculations.tag_management import ProjectTagFactory, build_connection

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
        tracer_A_const = float(selected_tracer['A_Coeff'])
        tracer_B_const = float(selected_tracer['B_Coeff'])
        tracer_C_const = float(selected_tracer['C_Coeff'])
        min_amb_temp = float(project_settings['min_amb_t'])
        operating_temp = float(line['oper_temp'])
        vendorVoltage_Correction = float(selected_tracer['Voltage_Correction_Factor'])
   
        # Compute Maximum Current
        maximum_current = (
            (tracer_A_const * min_amb_temp**2 + tracer_B_const * min_amb_temp + tracer_C_const)
            * (tracer_length * vendorVoltage_Correction)
        ) / voltage

        # Compute Operating Current
        operating_current = (
            (tracer_A_const * operating_temp**2 + tracer_B_const * operating_temp + tracer_C_const)
            * (tracer_length * vendorVoltage_Correction)
        ) / voltage

        # Compute No. of Circuits Required
        no_of_circuits = math.ceil(maximum_current / (max_cb_size * margin_on_max_cb_size))

        # Breaker Size Selection
        breaker_sizes = [2, 4, 6, 10, 16, 20, 25, 32, 40]
        breaker_size = next((size for size in breaker_sizes if size >= maximum_current), max_cb_size)
        
        # Compute Operating Load
        operating_load = operating_current * voltage
        
        # Apply termination margins to tracer length
        total_tracer_length = tracer_length + no_of_circuits * float(project_settings['termination_margin']) / 1000
       
        outer_dia_mm = asme_data.loc[asme_data['Nominal_Pipe_Size'] == float(line['line_size']), 'Outside_Diameter_mm']
        pipe_size_mm = outer_dia_mm.iloc[0] if not outer_dia_mm.empty else 25.206 * float(line['line_size']) + 9.4852
        return {
            'uid': line['uid'],
            'line_id': line.get('line_id', str(line['uid'])),
            'project_id': project_settings.get('proj_id'),
            'no_of_circuits': no_of_circuits,
            'breaker_size': breaker_size,
            'operating_current': operating_current,
            'max_current': maximum_current,
            'operating_load': operating_load,
            'total_tracer_length': total_tracer_length,
            'pipe_size_mm':pipe_size_mm if pipe_size_mm else 0
        }
    except Exception as e:
        logging.error(f"Error in power parameter computation for UID {line['uid']}: {str(e)}")
        return None

def _upstream_connection_chain(components):
    chain = [component for component in components if component]
    return [build_connection(chain[index], chain[index + 1]) for index in range(len(chain) - 1)]


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

    # Process circuits in batches of 3
    while remaining_circuits > 0:
        branch_index += 1
        circuits_in_this_batch = min(3, remaining_circuits)
        remaining_circuits -= circuits_in_this_batch

        branch_type = "3phJB" if circuits_in_this_batch > 1 else "1phJB"
        connected_to = (
            "3x 1phJB" if circuits_in_this_batch == 3
            else "2x 1phJB" if circuits_in_this_batch == 2
            else "Tracer"
        )

        tagged_components = {
            "schema_version": 1,
            "component_details": {},
            "Downstream": [],
            "connections": [],
        }

        mcb_component = tag_factory.create_component(
            "MCB",
            line_uid=line_uid,
            line_id=line_id,
            branch_index=branch_index,
            sequence_index=1,
            metadata={
                "breaker_size": power_params["breaker_size"],
                "branch_type": branch_type,
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
                    metadata={"location": "incoming"},
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
                metadata={"circuit_count": circuits_in_this_batch},
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
                isolator_1ph_component = tag_factory.create_component(
                    "Isolator1PH",
                    line_uid=line_uid,
                    line_id=line_id,
                    branch_index=branch_index,
                    sequence_index=5,
                    circuit_index=circuit_index,
                    metadata={"location": "outgoing"},
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
                metadata={"branch_type": branch_type},
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
