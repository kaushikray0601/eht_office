import math

import pandas as pd


def _as_float(value):
    if value is None:
        return 0.0
    return float(value)


def _normalize_power_distribution(power_distribution):
    """Accept the active dict payload while remaining tolerant of older ad hoc shapes."""
    if isinstance(power_distribution, pd.DataFrame):
        if power_distribution.empty:
            return {"total_circuits": 0, "branches": []}
        if len(power_distribution.index) != 1:
            raise ValueError("BOQ expects one power-distribution payload per process line.")
        return _normalize_power_distribution(power_distribution.iloc[0].to_dict())

    if isinstance(power_distribution, list):
        return {
            "total_circuits": sum(int(branch.get("circuit_count", 0) or 0) for branch in power_distribution),
            "branches": power_distribution,
        }

    if not isinstance(power_distribution, dict):
        raise TypeError("Unsupported power distribution payload for BOQ calculation.")

    branches = power_distribution.get("branches", [])
    if isinstance(branches, dict):
        branches = [branches]
    if not isinstance(branches, list):
        raise TypeError("Power distribution branches must be a list or dict.")

    total_circuits = power_distribution.get("total_circuits")
    if total_circuits in (None, ""):
        total_circuits = sum(int(branch.get("circuit_count", 0) or 0) for branch in branches)

    return {
        "total_circuits": int(total_circuits or 0),
        "branches": branches,
    }


def compute_bill_of_quantities(power_distribution, project_settings, tracer_qty, line_length, pipe_size_mm, is_process_temp_controlled):
    """
    Compute BOQ items for a single process line from the active power-distribution payload.
    """
    normalized_distribution = _normalize_power_distribution(power_distribution)
    total_circuits = normalized_distribution["total_circuits"]

    boq = {
        'MCB': 0,
        'JB3PH': 0,
        'JB1PH': 0,
        'CCMCB-3PHJB': 0,
        'CC3PHJB-1PHJB': 0,
        'TRACER': tracer_qty,
        'ENDTRM': 0,
        'ISOLATOR_1PH': 0,
        'ISOLATOR_3PH': 0,
        'RTD': 0,
        'THERMOSTAT': 0,
        'Caution_Label': 0,
        'Aluminium_Adhesive_Tape': 0,
        'Pipe_Strap': 0,
    }

    for branch in normalized_distribution["branches"]:
        branch_type = branch.get('type')
        circuit_count = int(branch.get('circuit_count', 0) or 0)

        if branch_type == '3phJB':
            boq['MCB'] += 1
            boq['JB3PH'] += 1
            boq['CCMCB-3PHJB'] += _as_float(branch.get('cable_length_db_to_jb'))
            if branch.get('connected_to') in ['3x 1phJB', '2x 1phJB']:
                boq['JB1PH'] += circuit_count
                boq['CC3PHJB-1PHJB'] += circuit_count * _as_float(branch.get('cable_length_jb_to_jb'))
        elif branch_type == '1phJB':
            boq['MCB'] += 1
            boq['JB1PH'] += circuit_count
            boq['CC3PHJB-1PHJB'] += circuit_count * _as_float(
                branch.get('cable_length_db_to_jb', project_settings['ckt_ln'])
            )
        else:
            raise ValueError(f"Unsupported branch type for BOQ calculation: {branch_type!r}")

    isolator_setting = project_settings['isolator_location']
    if isolator_setting == 'bothSides':
        boq['ISOLATOR_3PH'] = boq['JB3PH']
        boq['ISOLATOR_1PH'] = total_circuits
    elif isolator_setting == 'outgoingOnly':
        boq['ISOLATOR_1PH'] = total_circuits
    elif isolator_setting == 'incomingOnly':
        boq['ISOLATOR_3PH'] = boq['JB3PH']

    if is_process_temp_controlled:
        if project_settings['rtd_thrm'] in ['RI', 'TI']:
            boq['RTD'] = total_circuits if 'RI' in project_settings['rtd_thrm'] else 0
            boq['THERMOSTAT'] = total_circuits if 'TI' in project_settings['rtd_thrm'] else 0
            boq['Pipe_Strap'] = boq['RTD'] + boq['THERMOSTAT']
        elif project_settings['rtd_thrm'] in ['RO', 'TO']:
            boq['RTD'] = boq['MCB'] if 'RO' in project_settings['rtd_thrm'] else 0
            boq['THERMOSTAT'] = boq['MCB'] if 'TO' in project_settings['rtd_thrm'] else 0
            boq['Pipe_Strap'] = boq['JB1PH'] + boq['RTD'] + boq['THERMOSTAT']

    boq['ENDTRM'] = total_circuits
    boq['Caution_Label'] = math.ceil(max(_as_float(line_length) / _as_float(project_settings['caution_label_interval']), 1))
    boq['Aluminium_Adhesive_Tape'] = math.ceil(
        max(_as_float(pipe_size_mm) * math.pi * 4 * _as_float(line_length) / 1000, 1)
    )

    return boq
