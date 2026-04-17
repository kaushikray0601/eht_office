import logging

logger = logging.getLogger(__name__)

def generate_tags(process_lines, power_distribution_results, project_settings, consolidated_boq):
    """
    Generate tags for components and track relationships between them.

    Args:
        process_lines (DataFrame): Input process lines.
        power_distribution_results (list of dict): Power distribution results for each line.
        project_settings (dict): Project-specific settings.
        consolidated_boq (dict): Consolidated BOQ data.

    Returns:
        dict: A dictionary containing tags and relationships.
    """

    # Initialize containers
    tags = {
        "MCBs": [],
        "JunctionBoxes": {},  # Stores JB tags
        "Cables": [],
        "Tracers": [],
        "EndTermination": [],
        "Isolators": {"3PH": [], "1PH": []},
        "Thermostats": [],
        "RTDs": []
    }
    relationships = []  # Stores relationships (e.g., "MCB -> JB -> Tracer")

    tag_counter = {
        "MCB": 1,
        "JB3PH": 1,
        "JB1PH": 1,
        "Tracer": 1,
        "Cable4C": 1,
        "Cable3C": 1,
        "ENDTRM": 1,
        "ISOL_3PH": 1,
        "ISOL_1PH": 1,
    }

    isolator_setting = project_settings.get('isolator_location', 'none')

    # Loop through each line and generate tags
    for _, line in process_lines.iterrows():
        try:
            line_uid = line["uid"]
            total_circuits = line.get("total_circuits", 0)

            # Skip process lines with no circuits
            if total_circuits == 0:
                logger.warning(f"Skipping process line UID {line_uid} with no circuits.")
                continue

            remaining_circuits = total_circuits

            while remaining_circuits > 0:
                # Start a new MCB and its associated components for this batch
                mcb_tag = f"MCB_{line_uid}_{tag_counter['MCB']:03d}"
                tags["MCBs"].append(mcb_tag)
                tag_counter["MCB"] += 1

                cable4c_tag = f"CCAB4C_{line_uid}_{tag_counter['Cable4C']:03d}"
                tags["Cables"].append(cable4c_tag)
                tag_counter["Cable4C"] += 1
                relationships.append({"from": mcb_tag, "to": cable4c_tag})

                # Generate ISOLATOR_3PH tag if required
                if isolator_setting in ['bothSides', 'incomingOnly']:
                    isolator_3ph_tag = f"ISOL_3PH_{line_uid}_{tag_counter['ISOL_3PH']:03d}"
                    tags["Isolators"]["3PH"].append(isolator_3ph_tag)
                    tag_counter["ISOL_3PH"] += 1
                    relationships.append({"from": cable4c_tag, "to": isolator_3ph_tag})
                else:
                    isolator_3ph_tag = cable4c_tag  # Skip ISOLATOR_3PH if not required

                # Generate JB3PH tag
                jb3ph_tag = f"JB3PH_{line_uid}_{tag_counter['JB3PH']:03d}"
                tags["JunctionBoxes"][jb3ph_tag] = {"connected_to": []}
                tag_counter["JB3PH"] += 1
                relationships.append({"from": isolator_3ph_tag, "to": jb3ph_tag})

                # Determine the number of circuits to process in this batch
                circuits_in_this_batch = min(3, remaining_circuits)
                remaining_circuits -= circuits_in_this_batch

                # Generate tags for circuits in this batch
                for i in range(circuits_in_this_batch):
                    jb1ph_tag = f"JB1PH_{line_uid}_{tag_counter['JB1PH']:03d}"
                    tags["JunctionBoxes"][jb1ph_tag] = {"connected_to": []}
                    tag_counter["JB1PH"] += 1
                    relationships.append({"from": jb3ph_tag, "to": jb1ph_tag})

                    tracer_tag = f"Tracer_{line_uid}_{tag_counter['Tracer']:03d}"
                    end_term_tag = f"ENDTRM_{line_uid}_{tag_counter['ENDTRM']:03d}"
                    tags["Tracers"].append(tracer_tag)
                    tags["EndTermination"].append(end_term_tag)
                    tag_counter["Tracer"] += 1
                    tag_counter["ENDTRM"] += 1

                    tags["JunctionBoxes"][jb1ph_tag]["connected_to"].append(tracer_tag)
                    relationships.append({"from": jb1ph_tag, "to": tracer_tag})
                    relationships.append({"from": tracer_tag, "to": end_term_tag})

                # Handle single circuit bypassing 3PH JB (for remaining circuits)
                if circuits_in_this_batch == 1 and remaining_circuits == 0:
                    cable3c_tag = f"CCAB3C_{line_uid}_{tag_counter['Cable3C']:03d}"
                    tags["Cables"].append(cable3c_tag)
                    tag_counter["Cable3C"] += 1
                    relationships.append({"from": mcb_tag, "to": cable3c_tag})

                    tracer_tag = f"Tracer_{line_uid}_{tag_counter['Tracer']:03d}"
                    end_term_tag = f"ENDTRM_{line_uid}_{tag_counter['ENDTRM']:03d}"
                    tags["Tracers"].append(tracer_tag)
                    tags["EndTermination"].append(end_term_tag)
                    tag_counter["Tracer"] += 1
                    tag_counter["ENDTRM"] += 1

                    relationships.append({"from": cable3c_tag, "to": tracer_tag})
                    relationships.append({"from": tracer_tag, "to": end_term_tag})

                # Generate ISOLATOR_1PH tag if required
                if isolator_setting in ['bothSides', 'outgoingOnly']:
                    isolator_1ph_tag = f"ISOL_1PH_{line_uid}_{tag_counter['ISOL_1PH']:03d}"
                    tags["Isolators"]["1PH"].append(isolator_1ph_tag)
                    tag_counter["ISOL_1PH"] += 1
                    relationships.append({"from": jb3ph_tag, "to": isolator_1ph_tag})

        except Exception as e:
            logger.error(f"Error generating tags for line UID {line['uid']}: {str(e)}")
            continue

    return {
        "tags": tags,
        "relationships": relationships
    }
