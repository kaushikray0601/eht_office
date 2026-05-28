import pandas as pd
from django.test import TestCase

from eht.cal import orchestrate_calculations
from eht.heat_loss_methods import DEFAULT_HEAT_LOSS_METHOD
from eht.models import MICableFamily, MICableHeater, MIColdLeadOption


def make_process_lines(**overrides):
    values = {
        'uid': 1,
        'line_id': 'LINE-001',
        'proj_id': 'p1',
        'service_type': 'EP',
        'line_size': 2.0,
        'line_length': 100.0,
        'ins_mat_type': 'MW',
        'insul_thick': 50.0,
        'maint_temp': 120.0,
        'oper_temp': 100.0,
        'design_temp': 160.0,
        'valve_qty': 0,
        'flange_qty': 0,
        'support_qty': 0,
        'phase': '1PH',
        'status': 'confirmed',
    }
    values.update(overrides)
    return pd.DataFrame([values])


def make_project_settings(**overrides):
    values = {
        'proj_id': 'p1',
        'min_amb_t': 20.0,
        'wind_speed': 32.0,
        'voltage': 230.0,
        'voltage_var_factor': 0.0,
        'margin_on_tracer_lengths': 10.0,
        'spiral_wrap_allowed': True,
        'spiral_factor': 2.0,
        'max_cb_size': 32.0,
        'restrict_cb_current': 80.0,
        'termination_margin': 250.0,
        'ckt_ln': 30.0,
        'loop_ln': 12.0,
        'isolator_location': 'bothSides',
        'rtd_thrm': 'TI',
        'caution_label_interval': 10.0,
        'allowablevdrop': 5.0,
        'vendor': 'THR',
        'area_class': 'Zone 1, IIC',
        'gas_group': '',
        'temp_class': 'T3',
        'heat_loss_sf': 1.0,
        'heat_loss_method': DEFAULT_HEAT_LOSS_METHOD,
    }
    values.update(overrides)
    return values


def make_vendor_data(**overrides):
    values = {
        'V_UID': 'SR-001',
        'Voltage_Float': 230.0,
        'A_Coeff': 0.0,
        'B_Coeff': 0.0,
        'C_Coeff': 20.0,
        'Power_at_Startup_T': 10.0,
        'Ohm_per_km': 1.0,
        'Res_corrFactor_Mica': 1.0,
        'Tracer_Family': 'Self Regulating',
        'Zone': 'Zone 1',
        'Gas_Group': 'IIC',
        'T_Rating': 'T1,T2,T3',
        'Maint_T': 150.0,
        'Max_Op_T': 150.0,
        'Max_Exp_T_On': 232.0,
    }
    values.update(overrides)
    return pd.DataFrame([values])


def make_asme_table():
    return pd.DataFrame([{'Nominal_Pipe_Size': 2.0, 'Outside_Diameter_mm': 60.3}])


def make_thermal_table():
    return pd.DataFrame([{'Ins_Mat_Type': 'MW', 'K_factor_A': 0.0, 'K_factor_B': 0.0, 'K_factor_C': 0.05}])


def make_validated_mi_catalogue():
    family = MICableFamily.objects.create(
        vendor='THR',
        family_name='MIQ',
        alloy_type='Alloy 825',
        max_voltage=600.0,
        max_sheath_temp_c=180.0,
        max_maintain_temp_c=500.0,
        max_exposure_temp_c=600.0,
        max_watt_density_w_m=80.0,
        min_circuit_length_m=1.0,
        max_circuit_length_m=250.0,
        temp_class_rating='T3',
        gas_group='IIC',
        zone_approval='Zone 1',
        source_document='Test-only vendor document',
        is_validated=True,
    )
    heater = MICableHeater.objects.create(
        family=family,
        part_number='MIQ-R001',
        conductors=1,
        resistance_ohms_m=0.1,
        max_current_a=60.0,
        cold_lead_resistance_ohms_m=0.02,
        cold_lead_max_ampacity_a=60.0,
        sheath_material='Alloy 825',
        conductor_material='Nickel Chromium',
    )
    MIColdLeadOption.objects.create(
        heater=heater,
        option_code='CL-2M',
        length_m=2.0,
    )


class MIOrchestrationBoundaryTests(TestCase):
    def test_sr_selected_by_default_without_mi_catalogue_noise(self):
        result = orchestrate_calculations(
            process_lines=make_process_lines(),
            vendor_data=make_vendor_data(),
            project_settings=make_project_settings(),
            asme_b36_table=make_asme_table(),
            thermal_cond_data=make_thermal_table(),
        )

        self.assertEqual(len(result['selected_tracers']), 1)
        self.assertEqual(result['selected_mi_heaters'], [])
        self.assertEqual(len(result['power_distribution']), 1)

    def test_sr_selected_line_keeps_mi_candidate_ready_for_later_override(self):
        make_validated_mi_catalogue()

        result = orchestrate_calculations(
            process_lines=make_process_lines(),
            vendor_data=make_vendor_data(),
            project_settings=make_project_settings(),
            asme_b36_table=make_asme_table(),
            thermal_cond_data=make_thermal_table(),
        )

        self.assertEqual(len(result['selected_tracers']), 1)
        self.assertEqual(len(result['selected_mi_heaters']), 1)
        self.assertEqual(result['selected_mi_heaters'][0]['heater_part_number'], 'MIQ-R001')
        self.assertEqual(result['selected_mi_heaters'][0]['selection_status'], 'available_alternative')
        self.assertEqual(len(result['power_distribution']), 1)

    def test_high_temperature_line_falls_back_to_mi_when_sr_limit_is_exceeded(self):
        make_validated_mi_catalogue()

        result = orchestrate_calculations(
            process_lines=make_process_lines(design_temp=260.0),
            vendor_data=make_vendor_data(),
            project_settings=make_project_settings(),
            asme_b36_table=make_asme_table(),
            thermal_cond_data=make_thermal_table(),
        )

        self.assertEqual(result['selected_tracers'], [])
        self.assertEqual(len(result['selected_mi_heaters']), 1)
        self.assertEqual(result['selected_mi_heaters'][0]['selection_status'], 'selected')
        self.assertEqual(
            result['selected_mi_heaters'][0]['selection_basis']['selection_mode'],
            'automatic_temperature_fallback',
        )
        self.assertEqual(len(result['power_distribution']), 1)
        self.assertEqual(len(result['tracer_power_param']), 1)
        self.assertEqual(result['tracer_power_param'][0]['selected_tracer'], 'MIQ-R001')
        self.assertEqual(result['boq_per_line'][1]['MI_HEATER_SET'], 1)
        self.assertGreater(result['consolidated_boq']['MI_HEATED_LENGTH'], 0)

    def test_high_temperature_line_records_mi_rejection_when_fallback_catalogue_is_empty(self):
        result = orchestrate_calculations(
            process_lines=make_process_lines(design_temp=260.0),
            vendor_data=make_vendor_data(),
            project_settings=make_project_settings(),
            asme_b36_table=make_asme_table(),
            thermal_cond_data=make_thermal_table(),
        )

        self.assertEqual(result['selected_tracers'], [])
        self.assertEqual(len(result['selected_mi_heaters']), 1)
        rejection = result['selected_mi_heaters'][0]
        self.assertEqual(rejection['mi_selection_status'], 'rejected')
        self.assertEqual(rejection['selection_basis']['selection_mode'], 'automatic_temperature_fallback')
        self.assertEqual(rejection['mi_selection_rejection_reasons'][0]['code'], 'NO_VALIDATED_MI_CATALOGUE_DATA')
        self.assertEqual(result['power_distribution'], [])

    def test_non_temperature_sr_rejection_does_not_trigger_mi_fallback(self):
        result = orchestrate_calculations(
            process_lines=make_process_lines(),
            vendor_data=make_vendor_data(C_Coeff=1.0),
            project_settings=make_project_settings(
                spiral_factor=1.0,
                spiral_wrap_allowed=False,
                sr_max_parallel_runs=1,
            ),
            asme_b36_table=make_asme_table(),
            thermal_cond_data=make_thermal_table(),
        )

        self.assertEqual(result['selected_tracers'], [])
        self.assertEqual(result['selected_mi_heaters'], [])
        self.assertEqual(result['power_distribution'], [])
