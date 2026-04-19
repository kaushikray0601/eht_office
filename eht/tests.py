import json
import math
from io import BytesIO

import pandas as pd
from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from openpyxl import load_workbook

from eht.cal import orchestrate_calculations
from eht.calculations.boq import compute_bill_of_quantities
from eht.calculations.heat_loss import calculate_heat_loss
from eht.calculations.power_distribution import compute_power_distribution, compute_power_params
from eht.calculations.tracer_selection import get_tracer_options
from eht.data_service import store_calculated_results
from eht.forms import ProjectDataForm
from eht.models import (
    AlternateTracer,
    BOQ,
    DEFAULT_PROJECT_ID,
    ElecEHT_ASMEB36,
    ElecEHT_ThermalConductivity,
    ElecEHT_Vendor,
    HeatLoss,
    HeatTracingInput,
    ManagedProject,
    PowerDistribution,
    PowerDistributionBranch,
    ProcessLineCalculation,
    ProjectData,
    SelectedTracer,
    is_default_project_id,
)


def make_line(**overrides):
    line = {
        'uid': 'L1',
        'maint_temp': 100.0,
        'insul_thick': 50.0,
        'ins_mat_type': 'MW',
        'line_size': 2.0,
        'valve_qty': 2,
        'support_qty': 3,
        'flange_qty': 1,
        'line_length': 10.0,
        'oper_temp': 80.0,
        'design_temp': 120.0,
        'service_type': 'EP',
    }
    line.update(overrides)
    return line


def make_project_settings(**overrides):
    settings = {
        'min_amb_t': 20.0,
        'wind_speed': 32.0,
        'voltage': 230.0,
        'voltage_var_factor': 0.0,
        'margin_on_tracer_lengths': 10.0,
        'spiral_wrap_allowed': True,
        'spiral_factor': 2.0,
        'max_cb_size': 10.0,
        'restrict_cb_current': 80.0,
        'termination_margin': 250.0,
        'ckt_ln': 30.0,
        'loop_ln': 12.0,
        'isolator_location': 'bothSides',
        'rtd_thrm': 'TI',
        'caution_label_interval': 10.0,
        'allowablevdrop': 5.0,
        'vendor': 'CHR',
    }
    settings.update(overrides)
    return settings


def make_asme_table():
    return pd.DataFrame([
        {'Nominal_Pipe_Size': 2.0, 'Outside_Diameter_mm': 60.3},
    ])


def make_thermal_table():
    return pd.DataFrame([
        {'Ins_Mat_Type': 'MW', 'K_factor_A': 0.0, 'K_factor_B': 0.0, 'K_factor_C': 0.05},
    ])


def make_tracer_vendor_data():
    return pd.DataFrame([
        {
            'V_UID': 'T1',
            'Voltage_Float': 230.0,
            'A_Coeff': 0.0,
            'B_Coeff': 0.0,
            'C_Coeff': 100.0,
            'Power_at_Startup_T': 10.0,
            'Ohm_per_km': 1.0,
            'Res_corrFactor_Mica': 1.0,
            'Tracer_Family': 'SR',
        },
        {
            'V_UID': 'T2',
            'Voltage_Float': 230.0,
            'A_Coeff': 0.0,
            'B_Coeff': 0.0,
            'C_Coeff': 80.0,
            'Power_at_Startup_T': 10.0,
            'Ohm_per_km': 1.0,
            'Res_corrFactor_Mica': 1.0,
            'Tracer_Family': 'SR',
        },
        {
            'V_UID': 'T3',
            'Voltage_Float': 230.0,
            'A_Coeff': 0.0,
            'B_Coeff': 0.0,
            'C_Coeff': 60.0,
            'Power_at_Startup_T': 10.0,
            'Ohm_per_km': 1.0,
            'Res_corrFactor_Mica': 1.0,
            'Tracer_Family': 'SR',
        },
    ])


def make_project_record(**overrides):
    data = {
        'proj_id': 'p1',
        'min_amb_t': 20.0,
        'max_amb_t': 45.0,
        'startup_t': 15.0,
        'area_class': 'SAFE',
        'temp_class': 'T3',
        'voltage': 230.0,
        'max_cb_size': 10,
        'restrict_cb_current': 80.0,
        'vendor': 'CHR',
        'spiral_wrap_allowed': True,
        'spiral_factor': 2.0,
        'margin_on_tracer_lengths': 10.0,
        'voltage_var_factor': 0.0,
        'res_tol': 10.0,
        'termination_margin': 250.0,
        'heat_loss_sf': 1.0,
        'rtd_thrm': 'TI',
        'wind_speed': 32.0,
        'req_local_isolator': 'required',
        'caution_label_interval': 10.0,
        'isolator_location': 'bothSides',
        'ckt_ln': 30.0,
        'loop_ln': 12.0,
        'allowablevdrop': 5.0,
    }
    data.update(overrides)
    ManagedProject.objects.get_or_create(
        proj_id=data['proj_id'],
        defaults={'description': f"Project {data['proj_id']}", 'is_active': True},
    )
    return ProjectData.objects.create(**data)


def make_project_form_payload(**overrides):
    payload = {
        'proj_id': 'PLANT_A_001',
        'vendor': 'CHR',
        'startup_t': '15.00',
        'min_amb_t': '20.00',
        'max_amb_t': '45.00',
        'area_class': 'SAFE',
        'temp_class': 'T3',
        'voltage': '230.00',
        'max_cb_size': '10',
        'restrict_cb_current': '80.00',
        'allowablevdrop': '5.00',
        'spiral_factor': '2.00',
        'spiral_wrap_allowed': 'True',
        'margin_on_tracer_lengths': '10.00',
        'voltage_var_factor': '0.00',
        'res_tol': '10.00',
        'termination_margin': '250.00',
        'heat_loss_sf': '1.00',
        'rtd_thrm': 'TI',
        'wind_speed': '32.00',
        'caution_label_interval': '10.00',
        'isolator_location': 'bothSides',
        'ckt_ln': '30.00',
        'loop_ln': '12.00',
    }
    payload.update(overrides)
    return payload


def make_managed_project(proj_id='PLANT_A_001', description='Plant A 001', users=None, is_active=True):
    project, _created = ManagedProject.objects.get_or_create(
        proj_id=proj_id,
        defaults={
            'description': description,
            'is_active': is_active,
        },
    )
    project.description = description
    project.is_active = is_active
    project.save(update_fields=['description', 'is_active'])
    if users:
        project.assigned_users.set(users)
    return project


def make_default_project_record(**overrides):
    managed_project, _ = ManagedProject.objects.get_or_create(
        proj_id=DEFAULT_PROJECT_ID,
        defaults={'description': 'Default project', 'is_active': True},
    )
    data = {
        'proj_id': DEFAULT_PROJECT_ID,
        'min_amb_t': 10.0,
        'max_amb_t': 40.0,
        'startup_t': 5.0,
        'area_class': 'SAFE',
        'temp_class': 'T4',
        'voltage': 110.0,
        'max_cb_size': 16,
        'restrict_cb_current': 75.0,
        'vendor': 'THR',
        'spiral_wrap_allowed': False,
        'spiral_factor': 1.5,
        'margin_on_tracer_lengths': 8.0,
        'voltage_var_factor': 2.0,
        'res_tol': 5.0,
        'termination_margin': 200.0,
        'heat_loss_sf': 1.1,
        'rtd_thrm': 'TO',
        'wind_speed': 25.0,
        'req_local_isolator': 'required',
        'caution_label_interval': 12.0,
        'isolator_location': 'incomingOnly',
        'ckt_ln': 15.0,
        'loop_ln': 6.0,
        'allowablevdrop': 3.0,
    }
    data.update(overrides)
    return ProjectData.objects.create(**data)


def make_calculated_project_snapshot(project_id='p1'):
    make_project_record(proj_id=project_id)
    line = HeatTracingInput.objects.create(
        proj_id=project_id,
        line_id='LINE-001',
        service_type='EP',
        line_size=2.0,
        line_length=10.0,
        ins_mat_type='Mineral Wool',
        insul_thick=50.0,
        maint_temp=120.0,
        oper_temp=100.0,
        design_temp=140.0,
        status='confirmed',
    )

    aggregated_results = {
        'heat_loss': [
            {'uid': line.uid, 'heat_loss': 12.5, 'tracer_adder': 1.2},
        ],
        'selected_tracers': [
            {
                'uid': line.uid,
                'V_UID': 'V-001',
                'A_Coeff': 1.0,
                'B_Coeff': 2.0,
                'C_Coeff': 3.0,
                'Power_at_Startup_T': 11.5,
                'Ohm_per_km': 9.5,
                'Res_corrFactor_Mica': 0.5,
                'Tracer_Family': 'Self Regulating',
                'Voltage_Float': 230.0,
                'Voltage_Correction_Factor': 0.95,
                'Power_Output': 30.0,
                'Spiral_Factor': 1.1,
                'Tracer_Length': 12.0,
                'Tracer_With_Margin': 12.6,
            },
        ],
        'alternative_tracers': [
            {
                'uid': line.uid,
                'V_UID': 'V-ALT-001',
                'A_Coeff': 1.1,
                'B_Coeff': 2.1,
                'C_Coeff': 3.1,
                'Power_at_Startup_T': 12.5,
                'Ohm_per_km': 10.5,
                'Res_corrFactor_Mica': 0.6,
                'Tracer_Family': 'Self Regulating',
                'Voltage_Float': 230.0,
                'Voltage_Correction_Factor': 0.97,
                'Power_Output': 31.0,
                'Spiral_Factor': 1.2,
                'Tracer_Length': 13.0,
                'Tracer_With_Margin': 13.7,
            },
        ],
        'power_distribution': [
            {
                'uid': line.uid,
                'total_circuits': 2,
                'branches': [
                    {
                        'type': '3phJB',
                        'circuit_count': 2,
                        'connected_to': '2x 1phJB',
                        'cable_length_db_to_jb': 25.0,
                        'cable_length_jb_to_jb': 10.0,
                        'tagged_components': {
                            'MCB': 'MCB_001',
                            'JB3PH': 'JB3PH_001',
                            'Downstream': [
                                {'Tracer': 'Tracer_001'},
                                {'Tracer': 'Tracer_002'},
                            ],
                        },
                    }
                ],
            },
        ],
        'boq_per_line': {
            line.uid: {
                'TRACER': 12.6,
                'MCB': 1,
                'JB3PH': 1,
            },
        },
        'consolidated_boq': {
            'TRACER': 12.6,
            'MCB': 1,
            'JB3PH': 1,
        },
        'tracer_power_param': [
            {
                'uid': line.uid,
                'breaker_size': 10,
                'no_of_circuits': 2,
                'max_current': 2.5,
                'operating_current': 2.0,
                'operating_load': 460.0,
                'total_tracer_length': 12.6,
                'pipe_size_mm': 60.3,
            },
        ],
    }
    store_calculated_results(project_id, aggregated_results)
    return line


def seed_reference_data():
    ElecEHT_ThermalConductivity.objects.create(
        Ins_Mat_Type='Mineral Wool',
        K_factor_A=0.0,
        K_factor_B=0.0,
        K_factor_C=0.05,
    )
    ElecEHT_ASMEB36.objects.create(
        Nominal_Pipe_Size=2.0,
        Outside_Diameter_mm=60.3,
    )
    ElecEHT_Vendor.objects.create(
        V_UID='V-001',
        Vendor='Chromalox',
        Tracer_Family='SR',
        Voltage=230.0,
        A_Coeff=0.0,
        B_Coeff=0.0,
        C_Coeff=30.0,
        Power_at_Startup_T=10.0,
        Ohm_per_km=1.0,
        Res_corrFactor_Mica=1.0,
    )
    ElecEHT_Vendor.objects.create(
        V_UID='V-ALT-001',
        Vendor='Chromalox',
        Tracer_Family='SR',
        Voltage=230.0,
        A_Coeff=0.0,
        B_Coeff=0.0,
        C_Coeff=25.0,
        Power_at_Startup_T=10.0,
        Ohm_per_km=1.0,
        Res_corrFactor_Mica=1.0,
    )


class HeatLossCalculationTests(SimpleTestCase):
    def test_calculate_heat_loss_returns_expected_values(self):
        line = make_line()
        project_settings = make_project_settings()
        pipe_size_mm = 60.3

        result = calculate_heat_loss(line, project_settings, make_asme_table(), make_thermal_table())

        expected_heat_loss = (2 * math.pi * 0.05 * 80.0) / math.log((2 * 50.0 + pipe_size_mm) / pipe_size_mm)
        expected_tracer_adder = (
            2 * (3.5 + 0.5 * pipe_size_mm / 25.4) / 3.048
            + 3 * (2 + 0.08 * pipe_size_mm / 25.4) / 3.048
            + 0.3
        )

        self.assertEqual(result['uid'], 'L1')
        self.assertAlmostEqual(result['heat_loss'], expected_heat_loss, places=6)
        self.assertAlmostEqual(result['tracer_adder'], expected_tracer_adder, places=6)

    def test_calculate_heat_loss_returns_none_for_unknown_insulation(self):
        line = make_line(ins_mat_type='UNKNOWN')

        result = calculate_heat_loss(line, make_project_settings(), make_asme_table(), make_thermal_table())

        self.assertIsNone(result)


class TracerSelectionTests(SimpleTestCase):
    def test_get_tracer_options_returns_best_and_sorted_alternatives(self):
        best_tracer, alternatives = get_tracer_options(
            {'uid': 'L1', 'heat_loss': 90.0, 'tracer_adder': 2.0},
            make_line(),
            make_project_settings(),
            make_tracer_vendor_data(),
        )

        self.assertEqual(best_tracer['V_UID'], 'T1')
        self.assertAlmostEqual(best_tracer['Tracer_With_Margin'], 11.88, places=2)
        self.assertEqual([item['V_UID'] for item in alternatives], ['T2', 'T3'])

    def test_get_tracer_options_rejects_spiral_wrap_candidates_when_not_allowed(self):
        best_tracer, alternatives = get_tracer_options(
            {'uid': 'L1', 'heat_loss': 90.0, 'tracer_adder': 2.0},
            make_line(),
            make_project_settings(spiral_wrap_allowed=False),
            make_tracer_vendor_data().iloc[1:].copy(),
        )

        self.assertEqual(best_tracer, {})
        self.assertEqual(alternatives, [])


class PowerDistributionCalculationTests(SimpleTestCase):
    def test_compute_power_params_and_distribution_for_two_circuits(self):
        selected_tracer = {
            'Tracer_With_Margin': 20.0,
            'A_Coeff': 0.0,
            'B_Coeff': 0.0,
            'C_Coeff': 100.0,
            'Voltage_Correction_Factor': 1.0,
        }

        power_params = compute_power_params(
            make_line(),
            make_project_settings(),
            make_asme_table(),
            selected_tracer,
        )
        distribution = compute_power_distribution(power_params, make_project_settings())
        branch = distribution['branches'][0]

        self.assertEqual(power_params['no_of_circuits'], 2)
        self.assertEqual(power_params['breaker_size'], 10)
        self.assertAlmostEqual(power_params['total_tracer_length'], 20.5, places=6)
        self.assertAlmostEqual(power_params['pipe_size_mm'], 60.3, places=6)

        self.assertEqual(distribution['total_circuits'], 2)
        self.assertEqual(branch['type'], '3phJB')
        self.assertEqual(branch['connected_to'], '2x 1phJB')
        self.assertEqual(branch['tagged_components']['Isolator3PH'], 'ISOL_3PH_001')
        self.assertEqual(branch['tagged_components']['Isolator1PH'], 'ISOL_1PH_001')
        self.assertEqual(len(branch['tagged_components']['Downstream']), 2)


class BoqCalculationTests(SimpleTestCase):
    def test_compute_bill_of_quantities_counts_key_components(self):
        power_distribution = {
            'uid': 'L1',
            'total_circuits': 2,
            'branches': [
                {
                    'type': '3phJB',
                    'connected_to': '2x 1phJB',
                    'circuit_count': 2,
                    'cable_length_db_to_jb': 30.0,
                    'cable_length_jb_to_jb': 12.0,
                },
            ],
        }

        boq = compute_bill_of_quantities(
            power_distribution=power_distribution,
            project_settings=make_project_settings(),
            tracer_qty=20.5,
            line_length=10.0,
            pipe_size_mm=60.3,
            is_process_temp_controlled=True,
        )

        self.assertEqual(boq['MCB'], 1)
        self.assertEqual(boq['JB3PH'], 1)
        self.assertEqual(boq['JB1PH'], 2)
        self.assertEqual(boq['CCMCB-3PHJB'], 30.0)
        self.assertEqual(boq['CC3PHJB-1PHJB'], 24.0)
        self.assertEqual(boq['ISOLATOR_3PH'], 1)
        self.assertEqual(boq['ISOLATOR_1PH'], 2)
        self.assertEqual(boq['THERMOSTAT'], 2)
        self.assertEqual(boq['ENDTRM'], 2)

    def test_compute_bill_of_quantities_aggregates_all_branches_in_active_payload(self):
        power_distribution = {
            'uid': 'L2',
            'total_circuits': 4,
            'branches': [
                {
                    'type': '3phJB',
                    'connected_to': '3x 1phJB',
                    'circuit_count': 3,
                    'cable_length_db_to_jb': 30.0,
                    'cable_length_jb_to_jb': 12.0,
                },
                {
                    'type': '1phJB',
                    'connected_to': 'Tracer',
                    'circuit_count': 1,
                    'cable_length_db_to_jb': 30.0,
                    'cable_length_jb_to_jb': None,
                },
            ],
        }

        boq = compute_bill_of_quantities(
            power_distribution=power_distribution,
            project_settings=make_project_settings(),
            tracer_qty=41.0,
            line_length=20.0,
            pipe_size_mm=60.3,
            is_process_temp_controlled=True,
        )

        self.assertEqual(boq['MCB'], 2)
        self.assertEqual(boq['JB3PH'], 1)
        self.assertEqual(boq['JB1PH'], 4)
        self.assertEqual(boq['CCMCB-3PHJB'], 30.0)
        self.assertEqual(boq['CC3PHJB-1PHJB'], 66.0)
        self.assertEqual(boq['ISOLATOR_3PH'], 1)
        self.assertEqual(boq['ISOLATOR_1PH'], 4)
        self.assertEqual(boq['THERMOSTAT'], 4)
        self.assertEqual(boq['ENDTRM'], 4)


class OrchestrationTests(SimpleTestCase):
    def test_orchestrate_calculations_builds_expected_aggregates(self):
        line = make_line(valve_qty=0, support_qty=0, flange_qty=0)
        vendor_data = make_tracer_vendor_data().assign(
            C_Coeff=[30.0, 25.0, 20.0]
        )

        result = orchestrate_calculations(
            process_lines=[line],
            vendor_data=vendor_data,
            project_settings=make_project_settings(),
            asme_b36_table=make_asme_table(),
            thermal_cond_data=make_thermal_table(),
        )

        self.assertEqual(len(result['heat_loss']), 1)
        self.assertEqual(result['selected_tracers'][0]['uid'], 'L1')
        self.assertEqual(len(result['alternative_tracers']), 2)
        self.assertEqual({item['uid'] for item in result['alternative_tracers']}, {'L1'})
        self.assertEqual(len(result['power_distribution']), 1)
        self.assertEqual(len(result['tracer_power_param']), 1)
        self.assertIn('TRACER', result['boq_per_line']['L1'])
        self.assertIn('MCB', result['consolidated_boq'])


class StoreCalculatedResultsTests(TestCase):
    def test_store_calculated_results_handles_current_orchestration_payload(self):
        make_project_record()
        line = HeatTracingInput.objects.create(
            proj_id='p1',
            line_id='LINE-001',
            service_type='EP',
            line_size=2.0,
            line_length=10.0,
            ins_mat_type='Mineral Wool',
            insul_thick=50.0,
            maint_temp=120.0,
            oper_temp=100.0,
            design_temp=140.0,
            status='confirmed',
        )

        aggregated_results = {
            'heat_loss': [
                {'uid': line.uid, 'heat_loss': 12.5, 'tracer_adder': 1.2},
            ],
            'selected_tracers': [
                {
                    'uid': line.uid,
                    'V_UID': 'V-001',
                    'A_Coeff': 1.0,
                    'B_Coeff': 2.0,
                    'C_Coeff': 3.0,
                    'Power_at_Startup_T': 11.5,
                    'Ohm_per_km': 9.5,
                    'Res_corrFactor_Mica': 0.5,
                    'Tracer_Family': 'Self Regulating',
                    'Voltage_Float': 230.0,
                    'Voltage_Correction_Factor': 0.95,
                    'Power_Output': 30.0,
                    'Spiral_Factor': 1.1,
                    'Tracer_Length': 12.0,
                    'Tracer_With_Margin': 12.6,
                },
            ],
            'alternative_tracers': [
                {
                    'uid': line.uid,
                    'V_UID': 'V-ALT-001',
                    'A_Coeff': 1.1,
                    'B_Coeff': 2.1,
                    'C_Coeff': 3.1,
                    'Power_at_Startup_T': 12.5,
                    'Ohm_per_km': 10.5,
                    'Res_corrFactor_Mica': 0.6,
                    'Tracer_Family': 'Self Regulating',
                    'Voltage_Float': 230.0,
                    'Voltage_Correction_Factor': 0.97,
                    'Power_Output': 31.0,
                    'Spiral_Factor': 1.2,
                    'Tracer_Length': 13.0,
                    'Tracer_With_Margin': 13.7,
                },
            ],
            'power_distribution': [
                {
                    'uid': line.uid,
                    'total_circuits': 1,
                    'branches': [
                        {
                            'type': '1phJB',
                            'circuit_count': 1,
                            'connected_to': 'Tracer',
                            'cable_length_db_to_jb': 25.0,
                            'cable_length_jb_to_jb': None,
                            'tagged_components': {
                                'MCB': 'MCB_001',
                                'Downstream': [{'Tracer': 'Tracer_001'}],
                            },
                        }
                    ],
                },
            ],
            'boq_per_line': {
                line.uid: {'TRACER': 12.6, 'MCB': 1},
            },
            'consolidated_boq': {
                'TRACER': 12.6,
                'MCB': 1,
            },
            'tracer_power_param': [
                {
                    'uid': line.uid,
                    'max_current': 2.5,
                    'operating_current': 2.0,
                    'operating_load': 460.0,
                    'total_tracer_length': 12.6,
                    'pipe_size_mm': 60.3,
                },
            ],
        }

        self.assertTrue(store_calculated_results('p1', aggregated_results))

        self.assertEqual(HeatLoss.objects.get(line=line).heat_loss, 12.5)
        self.assertEqual(SelectedTracer.objects.get(line=line).power_output, 30.0)
        alternate_tracer = AlternateTracer.objects.get(line=line, option_rank=1)
        self.assertEqual(alternate_tracer.tracer_with_margin, 13.7)
        self.assertEqual(PowerDistribution.objects.get(line=line).total_circuits, 1)

        branch = PowerDistributionBranch.objects.get(distribution__line=line, branch_index=1)
        self.assertEqual(branch.branch_type, '1phJB')
        self.assertEqual(branch.tagged_components['MCB'], 'MCB_001')

        process_line_calc = ProcessLineCalculation.objects.get(line=line)
        self.assertEqual(process_line_calc.selected_tracer, 'V-001')
        self.assertEqual(process_line_calc.breaker_size, 0)
        self.assertEqual(process_line_calc.total_circuits, 0)
        self.assertEqual(process_line_calc.total_power_consumption, 460.0)
        self.assertEqual(process_line_calc.total_tracer_length, 12.6)
        self.assertEqual(process_line_calc.pipe_size_mm, 60.3)

        self.assertEqual(
            BOQ.objects.filter(project_id='p1', scope='line', line=line).count(),
            2,
        )
        self.assertEqual(
            BOQ.objects.filter(project_id='p1', scope='consolidated', line__isnull=True).count(),
            2,
        )
        self.assertEqual(
            BOQ.objects.get(project_id='p1', scope='line', line=line, item_code='TRACER').unit,
            'm',
        )

    def test_same_tracer_vendor_uid_can_be_stored_for_multiple_lines(self):
        make_project_record()
        line_one = HeatTracingInput.objects.create(
            proj_id='p1',
            line_id='LINE-001',
            service_type='EP',
            line_size=2.0,
            line_length=10.0,
            ins_mat_type='Mineral Wool',
            insul_thick=50.0,
            maint_temp=120.0,
            oper_temp=100.0,
            design_temp=140.0,
            status='confirmed',
        )
        line_two = HeatTracingInput.objects.create(
            proj_id='p1',
            line_id='LINE-002',
            service_type='EP',
            line_size=3.0,
            line_length=12.0,
            ins_mat_type='Mineral Wool',
            insul_thick=50.0,
            maint_temp=120.0,
            oper_temp=100.0,
            design_temp=140.0,
            status='confirmed',
        )

        aggregated_results = {
            'heat_loss': [],
            'selected_tracers': [
                {
                    'uid': line_one.uid,
                    'V_UID': 'V-001',
                    'A_Coeff': 1.0,
                    'B_Coeff': 2.0,
                    'C_Coeff': 3.0,
                    'Power_at_Startup_T': 11.5,
                    'Ohm_per_km': 9.5,
                    'Res_corrFactor_Mica': 0.5,
                    'Tracer_Family': 'Self Regulating',
                    'Voltage_Float': 230.0,
                    'Voltage_Correction_Factor': 0.95,
                    'Power_Output': 30.0,
                    'Spiral_Factor': 1.1,
                    'Tracer_Length': 12.0,
                    'Tracer_With_Margin': 12.6,
                },
                {
                    'uid': line_two.uid,
                    'V_UID': 'V-001',
                    'A_Coeff': 1.0,
                    'B_Coeff': 2.0,
                    'C_Coeff': 3.0,
                    'Power_at_Startup_T': 11.5,
                    'Ohm_per_km': 9.5,
                    'Res_corrFactor_Mica': 0.5,
                    'Tracer_Family': 'Self Regulating',
                    'Voltage_Float': 230.0,
                    'Voltage_Correction_Factor': 0.95,
                    'Power_Output': 30.0,
                    'Spiral_Factor': 1.3,
                    'Tracer_Length': 14.0,
                    'Tracer_With_Margin': 14.7,
                },
            ],
            'alternative_tracers': [],
            'power_distribution': [],
            'boq_per_line': {},
            'consolidated_boq': {},
            'tracer_power_param': [],
        }

        store_calculated_results('p1', aggregated_results)

        self.assertEqual(SelectedTracer.objects.filter(v_uid='V-001').count(), 2)
        self.assertEqual(SelectedTracer.objects.get(line=line_one).tracer_with_margin, 12.6)
        self.assertEqual(SelectedTracer.objects.get(line=line_two).tracer_with_margin, 14.7)


class ProjectDataFormTests(TestCase):
    def test_form_lists_only_assigned_projects_for_logged_in_user(self):
        user = User.objects.create_user(username='planner', password='password123')
        make_managed_project(proj_id='P-001', description='Assigned', users=[user])
        make_managed_project(proj_id='P-002', description='Not Assigned')
        make_managed_project(proj_id='DEFAULT_PROJECT', description='Default project', users=[user])

        form = ProjectDataForm(user=user)
        choices = {value for value, _label in form.fields['proj_id'].choices}

        self.assertIn('', choices)
        self.assertIn('P-001', choices)
        self.assertNotIn('P-002', choices)
        self.assertNotIn('DEFAULT_PROJECT', choices)

    def test_default_project_id_helper_is_case_insensitive(self):
        self.assertTrue(is_default_project_id('DEFAULT_PROJECT'))
        self.assertTrue(is_default_project_id('default_project'))
        self.assertFalse(is_default_project_id('project_default'))

    def test_form_saves_setup_for_registered_project_and_hides_tracer_family(self):
        make_managed_project(proj_id='PLANT_A_001', description='Plant A')
        form = ProjectDataForm(data=make_project_form_payload())

        self.assertTrue(form.is_valid(), form.errors)
        project = form.save()
        self.assertEqual(project.proj_id, 'PLANT_A_001')
        self.assertEqual(project.req_local_isolator, 'required')
        self.assertNotIn('tracer_family', form.fields)
        self.assertNotIn('req_local_isolator', form.fields)
        self.assertEqual(form.fields['proj_id'].help_text, 'Projects are managed in Django admin.')

    def test_form_rejects_unregistered_project_id(self):
        make_managed_project(proj_id='PLANT_B_001', description='Plant B')
        form = ProjectDataForm(data=make_project_form_payload())

        self.assertFalse(form.is_valid())
        self.assertIn('proj_id', form.errors)

    def test_existing_project_form_keeps_current_project_selected(self):
        project = make_project_record(proj_id='p1')
        form = ProjectDataForm(instance=project)

        self.assertFalse(form.fields['proj_id'].disabled)
        self.assertEqual(form.initial['proj_id'], 'p1')

    def test_project_save_syncs_local_isolator_requirement_from_location(self):
        project = make_project_record(proj_id='p-sync', isolator_location='noIsolator', req_local_isolator='required')

        project.refresh_from_db()
        self.assertEqual(project.req_local_isolator, 'not_required')


class ProjectDataViewTests(TestCase):
    def test_create_project_data_view_persists_registered_project_id(self):
        make_managed_project(proj_id='PLANT_A_001', description='Plant A')
        response = self.client.post(reverse('create_project_data'), data=make_project_form_payload())

        self.assertEqual(response.status_code, 200)
        self.assertTrue(ProjectData.objects.filter(proj_id='PLANT_A_001').exists())

    def test_update_project_data_view_renders_blank_form_for_registered_project_without_setup(self):
        make_managed_project(proj_id='PLANT_B_001', description='Plant B')

        response = self.client.get(
            reverse('update_project_data', args=['PLANT_B_001']),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(ProjectData.objects.filter(proj_id='PLANT_B_001').exists())
        self.assertIn('PLANT_B_001', response.json()['form_html'])

    def test_default_project_button_copies_template_values_into_selected_project(self):
        make_managed_project(proj_id='PLANT_A_001', description='Plant A')
        make_default_project_record(proj_id='DEFAULT_PROJECT')

        response = self.client.post(
            reverse('create_project_data'),
            data={'proj_id': 'PLANT_A_001', 'action': 'load_defaults'},
        )

        self.assertEqual(response.status_code, 200)
        project = ProjectData.objects.get(proj_id='PLANT_A_001')
        self.assertEqual(project.vendor, 'THR')
        self.assertEqual(float(project.startup_t), 5.0)
        self.assertEqual(project.isolator_location, 'incomingOnly')
        self.assertEqual(project.req_local_isolator, 'required')

    def test_default_project_button_does_not_auto_create_template_project(self):
        make_managed_project(proj_id='PLANT_C_001', description='Plant C')

        response = self.client.post(
            reverse('create_project_data'),
            data={'proj_id': 'PLANT_C_001', 'action': 'load_defaults'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(ProjectData.objects.filter(proj_id='PLANT_C_001').exists())
        self.assertFalse(ProjectData.objects.filter(proj_id__iexact=DEFAULT_PROJECT_ID).exists())


class ResultAndBoqViewTests(TestCase):
    def test_result_view_prompts_for_project_selection_when_missing(self):
        response = self.client.get(reverse('result_view'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Select a project in the Project Data form')

    def test_result_view_renders_stored_project_results(self):
        line = make_calculated_project_snapshot()

        response = self.client.get(reverse('result_view'), {'project_id': 'p1'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Calculation Results')
        self.assertContains(response, line.line_id)
        self.assertContains(response, 'V-001')
        self.assertContains(response, 'V-ALT-001')
        self.assertContains(response, 'MCB_001')

    def test_boq_view_renders_consolidated_and_line_items(self):
        line = make_calculated_project_snapshot()

        response = self.client.get(reverse('boq_view'), {'project_id': 'p1'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Bill Of Quantities')
        self.assertContains(response, 'TRACER')
        self.assertContains(response, 'MCB')
        self.assertContains(response, line.line_id)
        self.assertContains(response, 'Miniature Circuit Breaker')

    def test_boq_view_filters_selected_line_for_verification(self):
        line = make_calculated_project_snapshot()

        response = self.client.get(
            reverse('boq_view'),
            {'project_id': 'p1', 'line_lookup': line.line_id},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'Selected Line: {line.line_id}')
        self.assertContains(response, 'Show Line BOQ')

    def test_boq_export_returns_summary_and_per_line_sheets(self):
        line = make_calculated_project_snapshot()

        response = self.client.get(reverse('boq_export_view'), {'project_id': 'p1'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        self.assertIn('p1_boq.xlsx', response['Content-Disposition'])

        workbook = load_workbook(BytesIO(response.content))
        self.assertEqual(workbook.sheetnames, ['BOQ Summary', 'BOQ Per Line'])

        summary_rows = list(workbook['BOQ Summary'].iter_rows(values_only=True))
        detail_rows = list(workbook['BOQ Per Line'].iter_rows(values_only=True))

        self.assertIn(('Project ID', 'Item Code', 'Description', 'Quantity', 'Unit'), summary_rows)
        self.assertIn(('Project ID', 'Line ID', 'Service Type', 'Item Code', 'Description', 'Quantity', 'Unit'), detail_rows)
        self.assertTrue(any(row[1] == 'TRACER' for row in summary_rows[1:]))
        self.assertTrue(any(row[1] == line.line_id for row in detail_rows[1:]))


class ConfirmValidDataViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='tester', password='password123')
        self.client.force_login(self.user)
        make_project_record()
        seed_reference_data()

    def create_pending_line(self, **overrides):
        defaults = {
            'proj_id': 'p1',
            'line_id': 'LINE-001',
            'service_type': 'EP',
            'line_size': 2.0,
            'line_length': 10.0,
            'ins_mat_type': 'Mineral Wool',
            'insul_thick': 50.0,
            'maint_temp': 100.0,
            'oper_temp': 80.0,
            'design_temp': 120.0,
            'valve_qty': 0,
            'flange_qty': 0,
            'support_qty': 0,
            'status': 'pending',
        }
        defaults.update(overrides)
        return HeatTracingInput.objects.create(**defaults)

    def test_confirm_valid_data_processes_pending_rows_and_stores_results(self):
        line = self.create_pending_line()

        response = self.client.post(reverse('confirm_valid_data'), {'project_id': 'p1'})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['project_id'], 'p1')
        self.assertEqual(payload['confirmed_rows'], 1)
        self.assertEqual(payload['result_counts']['heat_loss'], 1)
        self.assertEqual(payload['result_counts']['selected_tracers'], 1)
        self.assertEqual(payload['result_counts']['boq_lines'], 1)

        line.refresh_from_db()
        self.assertEqual(line.status, 'confirmed')
        self.assertTrue(HeatLoss.objects.filter(line=line).exists())
        self.assertTrue(SelectedTracer.objects.filter(line=line).exists())
        self.assertTrue(AlternateTracer.objects.filter(line=line, option_rank=1).exists())
        self.assertTrue(PowerDistribution.objects.filter(line=line).exists())
        self.assertTrue(ProcessLineCalculation.objects.filter(line=line).exists())
        self.assertTrue(BOQ.objects.filter(project_id='p1', scope='line', line=line).exists())
        self.assertTrue(BOQ.objects.filter(project_id='p1', scope='consolidated').exists())

    def test_confirm_valid_data_rejects_requests_when_no_rows_are_pending(self):
        line = self.create_pending_line(status='confirmed')

        response = self.client.post(reverse('confirm_valid_data'), {'project_id': 'p1'})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'No valid uploaded data is pending confirmation.')
        self.assertEqual(line.status, 'confirmed')
        self.assertFalse(HeatLoss.objects.filter(line=line).exists())
