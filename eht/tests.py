import json
import math

import pandas as pd
from django.test import SimpleTestCase, TestCase

from eht.cal import orchestrate_calculations
from eht.calculations.boq import compute_bill_of_quantities
from eht.calculations.heat_loss import calculate_heat_loss
from eht.calculations.power_distribution import compute_power_distribution, compute_power_params
from eht.calculations.tracer_selection import get_tracer_options
from eht.data_service import store_calculated_results
from eht.models import (
    AlternateTracer,
    BOQ,
    HeatLoss,
    HeatTracingInput,
    PowerDistribution,
    PowerDistributionBranch,
    ProcessLineCalculation,
    ProjectData,
    SelectedTracer,
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
        'tracer_family': 'SR',
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
    return ProjectData.objects.create(**data)


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
        power_distribution_data = pd.DataFrame([
            {
                'uid': 'L1',
                'total_circuits': 2,
                'branches': {
                    'type': '3phJB',
                    'connected_to': '2x 1phJB',
                    'circuit_count': 2,
                    'cable_length_db_to_jb': 30.0,
                    'cable_length_jb_to_jb': 12.0,
                },
            }
        ])

        boq = compute_bill_of_quantities(
            power_distribution_data=power_distribution_data,
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


class OrchestrationTests(SimpleTestCase):
    def test_orchestrate_calculations_builds_expected_aggregates(self):
        line = make_line(valve_qty=0, support_qty=0, flange_qty=0)
        vendor_data = make_tracer_vendor_data().assign(
            C_Coeff=[30.0, 25.0, 20.0]
        )

        result = orchestrate_calculations(
            project_id='p1',
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
