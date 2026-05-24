from django.test import TestCase

from eht.data_service import clear_project_workspace_data, store_calculated_results
from eht.heat_loss_methods import DEFAULT_HEAT_LOSS_METHOD
from eht.models import (
    HeatTracingInput,
    ManagedProject,
    MICableFamily,
    MICableHeater,
    MIColdLeadOption,
    BOQ,
    PowerDistribution,
    ProcessLineCalculation,
    ProjectData,
    SelectedMIHeater,
)


def make_project(project_id='p1'):
    ManagedProject.objects.get_or_create(
        proj_id=project_id,
        defaults={'description': f'Project {project_id}', 'is_active': True},
    )
    return ProjectData.objects.create(
        proj_id=project_id,
        min_amb_t=20.0,
        max_amb_t=45.0,
        startup_t=15.0,
        area_class='Zone 1, IIC',
        temp_class='T3',
        voltage=230.0,
        max_cb_size=10,
        restrict_cb_current=80.0,
        vendor='THR',
        spiral_wrap_allowed=True,
        spiral_factor=2.0,
        margin_on_tracer_lengths=10.0,
        voltage_var_factor=0.0,
        res_tol=10.0,
        termination_margin=250.0,
        heat_loss_sf=1.2,
        heat_loss_method=DEFAULT_HEAT_LOSS_METHOD,
        rtd_thrm='TI',
        wind_speed=32.0,
        req_local_isolator='required',
        caution_label_interval=10.0,
        isolator_location='bothSides',
        ckt_ln=30.0,
        loop_ln=12.0,
        allowablevdrop=5.0,
    )


def make_input_line(project_id='p1', **overrides):
    values = {
        'proj_id': project_id,
        'line_id': 'LINE-MI-001',
        'service_type': 'EP',
        'line_size': 2.0,
        'line_length': 100.0,
        'ins_mat_type': 'Mineral Wool',
        'insul_thick': 50.0,
        'maint_temp': 120.0,
        'oper_temp': 100.0,
        'design_temp': 160.0,
        'status': 'confirmed',
    }
    values.update(overrides)
    return HeatTracingInput.objects.create(**values)


def make_validated_mi_option():
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
    cold_lead = MIColdLeadOption.objects.create(
        heater=heater,
        option_code='CL-2M',
        length_m=2.0,
    )
    return heater, cold_lead


class MISelectionPersistenceTests(TestCase):
    def test_store_calculated_results_persists_selected_mi_snapshot(self):
        make_project()
        line = make_input_line()
        heater, cold_lead = make_validated_mi_option()

        store_calculated_results('p1', {
            'selected_mi_heaters': [{
                'uid': line.uid,
                'heater_id': heater.id,
                'cold_lead_option_id': cold_lead.id,
                'cold_lead_option_code': 'CL-2M',
                'heated_length_m': 105.0,
                'cold_lead_length_m': 2.0,
                'heater_resistance_ohms': 10.5,
                'cold_lead_resistance_total_ohms': 0.04,
                'power_nominal_w': 5284.8,
                'power_density_w_m': 50.33,
                'current_nominal_a': 21.82,
                'current_cold_start_a': 21.82,
                'max_sheath_temp_published_c': 180.0,
                'project_t_class_limit_c': 200.0,
                't_class_verdict': 'pass',
                'selection_basis': {'rule_set': 'MI_SINGLE_PHASE_SELECTION_MVP_V1'},
            }],
        })

        result = SelectedMIHeater.objects.get(line=line)
        self.assertEqual(result.heater, heater)
        self.assertEqual(result.cold_lead_option, cold_lead)
        self.assertEqual(result.selection_status, 'selected')
        self.assertAlmostEqual(result.heated_length_m, 105.0)
        self.assertAlmostEqual(result.cold_lead_resistance_total_ohms, 0.04)
        self.assertEqual(result.selection_basis['rule_set'], 'MI_SINGLE_PHASE_SELECTION_MVP_V1')

    def test_store_calculated_results_persists_mi_downstream_outputs(self):
        make_project()
        line = make_input_line()
        heater, cold_lead = make_validated_mi_option()

        store_calculated_results('p1', {
            'heat_loss': [{
                'uid': line.uid,
                'heat_loss': 32.0,
                'design_heat_loss': 32.0,
                'tracer_adder': 0.0,
            }],
            'selected_mi_heaters': [{
                'uid': line.uid,
                'heater_id': heater.id,
                'cold_lead_option_id': cold_lead.id,
                'selection_status': 'selected',
                'cold_lead_option_code': 'CL-2M',
                'heated_length_m': 100.0,
                'cold_lead_length_m': 2.0,
                'power_nominal_w': 5000.0,
                'power_density_w_m': 50.0,
                'current_nominal_a': 21.7,
                'current_cold_start_a': 22.0,
                'selection_basis': {'rule_set': 'MI_SINGLE_PHASE_SELECTION_MVP_V1'},
            }],
            'power_distribution': [{
                'uid': line.uid,
                'total_circuits': 1,
                'branches': [{
                    'type': '1phJB',
                    'circuit_count': 1,
                    'connected_to': 'Tracer',
                    'cable_length_db_to_jb': 30.0,
                    'cable_length_jb_to_jb': None,
                    'tagged_components': {'MCB': 'MCB_001', 'Downstream': [{'Tracer': 'Tracer_001'}]},
                }],
            }],
            'boq_per_line': {
                line.uid: {'MCB': 1, 'MI_HEATER_SET': 1, 'MI_HEATED_LENGTH': 100.0},
            },
            'consolidated_boq': {'MCB': 1, 'MI_HEATER_SET': 1, 'MI_HEATED_LENGTH': 100.0},
            'tracer_power_param': [{
                'uid': line.uid,
                'calculation_basis': 'MI_SINGLE_HEATER_MVP',
                'selected_tracer': heater.part_number,
                'no_of_circuits': 1,
                'breaker_size': 32,
                'max_current': 22.0,
                'operating_current': 21.7,
                'operating_load': 5000.0,
                'total_tracer_length': 100.0,
                'pipe_size_mm': 60.3,
            }],
        })

        calculation = ProcessLineCalculation.objects.get(line=line)
        self.assertEqual(calculation.selected_tracer, heater.part_number)
        self.assertEqual(calculation.remarks, 'MI_SINGLE_HEATER_MVP')
        self.assertEqual(PowerDistribution.objects.get(line=line).total_circuits, 1)
        self.assertEqual(
            BOQ.objects.get(project_id='p1', scope='line', line=line, item_code='MI_HEATER_SET').unit,
            'EA',
        )

    def test_store_calculated_results_can_persist_rejected_mi_record(self):
        make_project()
        line = make_input_line()

        store_calculated_results('p1', {
            'selected_mi_heaters': [{
                'uid': line.uid,
                'mi_selection_status': 'rejected',
                'mi_selection_rejection_reasons': [{
                    'rule_set': 'MI_SELECTION_REJECTION_REASON_V1',
                    'code': 'NO_VALIDATED_MI_CATALOGUE_DATA',
                    'message': 'No validated MI catalogue rows are available for the selected vendor.',
                }],
            }],
        })

        result = SelectedMIHeater.objects.get(line=line)
        self.assertIsNone(result.heater)
        self.assertIsNone(result.cold_lead_option)
        self.assertEqual(result.selection_status, 'rejected')
        self.assertEqual(result.selection_rejection_reasons[0]['code'], 'NO_VALIDATED_MI_CATALOGUE_DATA')

    def test_store_calculated_results_clears_stale_mi_selection_rows(self):
        make_project()
        line = make_input_line()
        heater, cold_lead = make_validated_mi_option()
        SelectedMIHeater.objects.create(
            line=line,
            heater=heater,
            cold_lead_option=cold_lead,
            selection_status='selected',
            cold_lead_option_code='CL-2M',
        )

        store_calculated_results('p1', {})

        self.assertFalse(SelectedMIHeater.objects.filter(line=line).exists())

    def test_clear_project_workspace_data_counts_and_removes_mi_selection_rows(self):
        make_project()
        line = make_input_line()
        heater, cold_lead = make_validated_mi_option()
        SelectedMIHeater.objects.create(
            line=line,
            heater=heater,
            cold_lead_option=cold_lead,
            selection_status='selected',
            cold_lead_option_code='CL-2M',
        )

        summary = clear_project_workspace_data('p1')

        self.assertGreaterEqual(summary['derived_rows'], 1)
        self.assertFalse(SelectedMIHeater.objects.exists())
