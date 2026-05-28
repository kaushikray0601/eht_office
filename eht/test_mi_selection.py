from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from eht.calculations.mi_selection import get_mi_heater_options
from eht.models import HeatTracingInput, MIAlloyTempFactor, MICableFamily, MICableHeater, MIColdLeadOption


def make_heat_loss(**overrides):
    values = {
        'uid': 1,
        'heat_loss': 20.0,
        'design_heat_loss': 20.0,
        'tracer_adder': 0.0,
    }
    values.update(overrides)
    return values


def make_line(**overrides):
    values = {
        'uid': 1,
        'line_id': 'LINE-MI-001',
        'proj_id': 'p1',
        'service_type': 'EP',
        'line_size': 2.0,
        'line_length': 100.0,
        'ins_mat_type': 'Mineral Wool',
        'insul_thick': 50.0,
        'maint_temp': 120.0,
        'oper_temp': 100.0,
        'design_temp': 160.0,
        'phase': '1PH',
        'status': 'confirmed',
    }
    values.update(overrides)
    return HeatTracingInput.objects.create(**values)


def make_project_settings(**overrides):
    values = {
        'proj_id': 'p1',
        'vendor': 'THR',
        'voltage': 230.0,
        'voltage_var_factor': 0.0,
        'allowablevdrop': 5.0,
        'area_class': 'Zone 1, IIC',
        'gas_group': '',
        'temp_class': 'T3',
    }
    values.update(overrides)
    return values


def make_family(**overrides):
    values = {
        'vendor': 'THR',
        'family_name': 'MIQ',
        'alloy_type': 'Alloy 825',
        'max_voltage': 600.0,
        'max_sheath_temp_c': 180.0,
        'max_maintain_temp_c': 500.0,
        'max_exposure_temp_c': 600.0,
        'max_watt_density_w_m': 80.0,
        'min_circuit_length_m': 1.0,
        'max_circuit_length_m': 250.0,
        'temp_class_rating': 'T3',
        'gas_group': 'IIC',
        'zone_approval': 'Zone 1',
        'source_document': 'Test-only vendor example',
        'is_validated': True,
    }
    values.update(overrides)
    return MICableFamily.objects.create(**values)


def make_heater(family=None, **overrides):
    values = {
        'family': family or make_family(),
        'part_number': 'MIQ-R001',
        'conductors': 1,
        'resistance_ohms_m': 0.1,
        'max_current_a': 60.0,
        'cold_lead_resistance_ohms_m': 0.0,
        'cold_lead_max_ampacity_a': 60.0,
        'sheath_material': 'Alloy 825',
        'conductor_material': 'Nickel Chromium',
    }
    values.update(overrides)
    return MICableHeater.objects.create(**values)


def make_cold_lead(heater=None, **overrides):
    values = {
        'heater': heater or make_heater(),
        'option_code': 'CL-2M',
        'length_m': 2.0,
    }
    values.update(overrides)
    return MIColdLeadOption.objects.create(**values)


class MISelectionDiagnosticsTests(TestCase):
    def test_empty_catalogue_returns_validated_catalogue_diagnostic(self):
        heat_loss = make_heat_loss()
        line = make_line()

        selected, alternatives = get_mi_heater_options(heat_loss, line, make_project_settings())

        self.assertEqual(selected, {})
        self.assertEqual(alternatives, [])
        self.assertEqual(heat_loss['mi_selection_status'], 'rejected')
        self.assertEqual(
            heat_loss['mi_selection_rejection_reasons'][0]['code'],
            'NO_VALIDATED_MI_CATALOGUE_DATA',
        )

    def test_unvalidated_family_is_never_selectable(self):
        family = make_family(is_validated=False)
        heater = make_heater(family=family)
        make_cold_lead(heater=heater)
        heat_loss = make_heat_loss()
        line = make_line()

        selected, _ = get_mi_heater_options(heat_loss, line, make_project_settings())

        self.assertEqual(selected, {})
        self.assertEqual(
            heat_loss['mi_selection_rejection_reasons'][0]['code'],
            'NO_VALIDATED_MI_CATALOGUE_DATA',
        )

    def test_unsupported_phase_is_rejected_before_catalogue_lookup(self):
        heat_loss = make_heat_loss()
        line = make_line(phase='3PH')

        selected, _ = get_mi_heater_options(heat_loss, line, make_project_settings())

        self.assertEqual(selected, {})
        self.assertEqual(heat_loss['mi_selection_rejection_reasons'][0]['code'], 'UNSUPPORTED_PHASE')

    def test_family_exposure_limit_rejects_candidate(self):
        family = make_family(max_exposure_temp_c=150.0)
        heater = make_heater(family=family)
        make_cold_lead(heater=heater)
        heat_loss = make_heat_loss()
        line = make_line(design_temp=160.0)

        selected, _ = get_mi_heater_options(heat_loss, line, make_project_settings())

        self.assertEqual(selected, {})
        rejection = heat_loss['mi_selection_rejection_reasons'][0]
        self.assertEqual(rejection['code'], 'NO_MI_CANDIDATE_MATCH')
        self.assertEqual(
            rejection['details']['family_rejections'][0]['reasons'],
            ['EXPOSURE_TEMP_EXCEEDS_FAMILY_LIMIT'],
        )


class MISelectionCandidateTests(TestCase):
    def test_selects_feasible_single_phase_heater_and_records_cold_lead_drop(self):
        family = make_family()
        heater = make_heater(
            family=family,
            resistance_ohms_m=0.1,
            cold_lead_resistance_ohms_m=0.02,
        )
        cold_lead = make_cold_lead(heater=heater, length_m=2.0)
        heat_loss = make_heat_loss(design_heat_loss=20.0, tracer_adder=5.0)
        line = make_line(line_length=100.0)

        selected, alternatives = get_mi_heater_options(heat_loss, line, make_project_settings())

        self.assertEqual(alternatives, [])
        self.assertEqual(heat_loss['mi_selection_status'], 'selected')
        self.assertEqual(selected['heater_part_number'], heater.part_number)
        self.assertEqual(selected['cold_lead_option_id'], cold_lead.id)
        self.assertAlmostEqual(selected['heated_length_m'], 105.0)
        self.assertAlmostEqual(selected['heater_resistance_ohms'], 10.5)
        self.assertAlmostEqual(selected['cold_lead_resistance_total_ohms'], 0.04)
        self.assertGreater(selected['power_density_w_m'], 20.0)
        self.assertGreater(selected['cold_lead_voltage_drop_percent'], 0.0)
        self.assertEqual(selected['t_class_verdict'], 'review')
        self.assertEqual(
            selected['selection_basis']['t_class_review_reason'],
            'DESIGN_SPECIFIC_SURFACE_TEMPERATURE_REVIEW_REQUIRED',
        )
        resistance_basis = selected['selection_basis']['resistance_temperature_basis']
        self.assertEqual(resistance_basis['factor_rows'], 0)
        self.assertEqual(resistance_basis['maintain_multiplier'], 1.0)

    def test_uses_conductor_temperature_factor_for_maintain_and_startup_resistance(self):
        family = make_family(alloy_type='Alloy 825')
        heater = make_heater(
            family=family,
            resistance_ohms_m=0.1,
            cold_lead_resistance_ohms_m=0.0,
            conductor_material='Nickel Chromium',
        )
        make_cold_lead(heater=heater, length_m=2.0)
        MIAlloyTempFactor.objects.create(
            alloy_type='Alloy 825',
            temperature_c=20.0,
            resistance_multiplier=9.0,
        )
        MIAlloyTempFactor.objects.create(
            alloy_type='Nickel Chromium',
            temperature_c=20.0,
            resistance_multiplier=1.0,
        )
        MIAlloyTempFactor.objects.create(
            alloy_type='Nickel Chromium',
            temperature_c=120.0,
            resistance_multiplier=1.1,
        )
        heat_loss = make_heat_loss(design_heat_loss=20.0)
        line = make_line(line_length=100.0, maint_temp=120.0)

        selected, _alternatives = get_mi_heater_options(
            heat_loss,
            line,
            make_project_settings(startup_t=20.0),
        )

        self.assertEqual(selected['heater_part_number'], heater.part_number)
        self.assertAlmostEqual(selected['heater_base_resistance_ohms'], 10.0)
        self.assertAlmostEqual(selected['heater_resistance_ohms'], 11.0)
        self.assertAlmostEqual(selected['heater_startup_resistance_ohms'], 10.0)
        self.assertAlmostEqual(selected['current_nominal_a'], 230.0 / 11.0)
        self.assertAlmostEqual(selected['current_cold_start_a'], 23.0)
        resistance_basis = selected['selection_basis']['resistance_temperature_basis']
        self.assertEqual(resistance_basis['factor_rows'], 2)
        self.assertEqual(resistance_basis['sheath_alloy_type'], 'Alloy 825')
        self.assertEqual(resistance_basis['conductor_material'], 'Nickel Chromium')
        self.assertEqual(resistance_basis['factor_lookup_key'], 'Nickel Chromium')
        self.assertEqual(resistance_basis['maintain_method'], 'nearest_high_endpoint')
        self.assertEqual(resistance_basis['startup_method'], 'nearest_low_endpoint')

    def test_heater_tcr_takes_priority_over_conductor_factor_table(self):
        family = make_family(alloy_type='Alloy 825')
        heater = make_heater(
            family=family,
            resistance_ohms_m=0.1,
            cold_lead_resistance_ohms_m=0.0,
            conductor_material='Nickel Chromium',
            tcr_per_degree_c=0.001,
        )
        make_cold_lead(heater=heater, length_m=2.0)
        MIAlloyTempFactor.objects.create(
            alloy_type='Nickel Chromium',
            temperature_c=120.0,
            resistance_multiplier=9.0,
        )
        heat_loss = make_heat_loss(design_heat_loss=20.0)
        line = make_line(line_length=100.0, maint_temp=120.0)

        selected, _alternatives = get_mi_heater_options(
            heat_loss,
            line,
            make_project_settings(startup_t=20.0),
        )

        self.assertEqual(selected['heater_part_number'], heater.part_number)
        self.assertAlmostEqual(selected['heater_base_resistance_ohms'], 10.0)
        self.assertAlmostEqual(selected['heater_resistance_ohms'], 11.0)
        self.assertAlmostEqual(selected['heater_startup_resistance_ohms'], 10.0)
        resistance_basis = selected['selection_basis']['resistance_temperature_basis']
        self.assertEqual(resistance_basis['tcr_per_degree_c'], 0.001)
        self.assertEqual(resistance_basis['factor_rows'], 1)
        self.assertEqual(resistance_basis['maintain_method'], 'linear_tcr_per_degree_c')
        self.assertEqual(resistance_basis['startup_method'], 'linear_tcr_per_degree_c')

    def test_zero_degree_startup_temperature_is_used_for_cold_start_current(self):
        family = make_family()
        heater = make_heater(
            family=family,
            resistance_ohms_m=0.1,
            cold_lead_resistance_ohms_m=0.0,
            tcr_per_degree_c=0.001,
        )
        make_cold_lead(heater=heater, length_m=2.0)
        heat_loss = make_heat_loss(design_heat_loss=20.0)
        line = make_line(line_length=100.0, maint_temp=120.0)

        selected, _alternatives = get_mi_heater_options(
            heat_loss,
            line,
            make_project_settings(startup_t=0.0),
        )

        self.assertEqual(selected['heater_part_number'], heater.part_number)
        self.assertAlmostEqual(selected['heater_resistance_ohms'], 11.0)
        self.assertAlmostEqual(selected['heater_startup_resistance_ohms'], 9.8)
        self.assertAlmostEqual(selected['current_cold_start_a'], 230.0 / 9.8)
        resistance_basis = selected['selection_basis']['resistance_temperature_basis']
        self.assertEqual(resistance_basis['startup_temp_c'], 0.0)
        self.assertEqual(
            resistance_basis['cold_start_temperature_basis']['selected_source'],
            'startup_t',
        )

    def test_mi_cold_start_uses_minimum_ambient_when_colder_than_startup_temperature(self):
        family = make_family()
        heater = make_heater(
            family=family,
            resistance_ohms_m=0.1,
            cold_lead_resistance_ohms_m=0.0,
            tcr_per_degree_c=0.001,
        )
        make_cold_lead(heater=heater, length_m=2.0)
        heat_loss = make_heat_loss(design_heat_loss=20.0)
        line = make_line(line_length=100.0, maint_temp=120.0)

        selected, _alternatives = get_mi_heater_options(
            heat_loss,
            line,
            make_project_settings(startup_t=15.0, min_amb_t=-20.0),
        )

        self.assertEqual(selected['heater_part_number'], heater.part_number)
        self.assertAlmostEqual(selected['heater_startup_resistance_ohms'], 9.6)
        self.assertAlmostEqual(selected['current_cold_start_a'], 230.0 / 9.6)
        resistance_basis = selected['selection_basis']['resistance_temperature_basis']
        cold_start_basis = resistance_basis['cold_start_temperature_basis']
        self.assertEqual(resistance_basis['startup_temp_c'], -20.0)
        self.assertEqual(cold_start_basis['selected_source'], 'min_amb_t')
        self.assertEqual(
            cold_start_basis['candidate_temperatures_c'],
            {'startup_t': 15.0, 'min_amb_t': -20.0},
        )

    def test_cold_lead_ampacity_failure_rejects_candidate(self):
        family = make_family()
        heater = make_heater(
            family=family,
            resistance_ohms_m=0.1,
            cold_lead_max_ampacity_a=1.0,
        )
        make_cold_lead(heater=heater)
        heat_loss = make_heat_loss(design_heat_loss=20.0)
        line = make_line(line_length=100.0)

        selected, _ = get_mi_heater_options(heat_loss, line, make_project_settings())

        self.assertEqual(selected, {})
        rejection = heat_loss['mi_selection_rejection_reasons'][0]
        self.assertEqual(rejection['code'], 'NO_MI_CANDIDATE_MATCH')
        self.assertIn(
            'EXCEEDS_COLD_LEAD_AMPACITY',
            rejection['details']['candidate_rejections'][0]['rejection_reasons'],
        )

    def test_high_published_sheath_rating_requires_review_without_rejecting_candidate(self):
        family = make_family(max_sheath_temp_c=600.0, temp_class_rating='T3')
        heater = make_heater(family=family, resistance_ohms_m=0.1)
        make_cold_lead(heater=heater)
        heat_loss = make_heat_loss(design_heat_loss=20.0)
        line = make_line(line_length=100.0)

        selected, _ = get_mi_heater_options(heat_loss, line, make_project_settings(temp_class='T3'))

        self.assertEqual(heat_loss['mi_selection_status'], 'selected')
        self.assertEqual(selected['heater_part_number'], heater.part_number)
        self.assertEqual(selected['max_sheath_temp_published_c'], 600.0)
        self.assertEqual(selected['project_t_class_limit_c'], 200.0)
        self.assertEqual(selected['t_class_verdict'], 'review')
        self.assertEqual(selected['rejection_reasons'], [])
        self.assertEqual(
            selected['selection_basis']['t_class_review_reason'],
            'DESIGN_SPECIFIC_SURFACE_TEMPERATURE_REVIEW_REQUIRED',
        )

    def test_selects_multiple_identical_heater_sets_when_single_set_underheats(self):
        family = make_family(max_watt_density_w_m=20.0)
        heater = make_heater(
            family=family,
            resistance_ohms_m=0.5,
            max_current_a=10.0,
            cold_lead_max_ampacity_a=10.0,
        )
        make_cold_lead(heater=heater, length_m=2.0)
        heat_loss = make_heat_loss(design_heat_loss=25.0)
        line = make_line(line_length=100.0)

        selected, alternatives = get_mi_heater_options(
            heat_loss,
            line,
            make_project_settings(max_cb_size=10.0, restrict_cb_current=80.0),
        )

        self.assertEqual(alternatives, [])
        self.assertEqual(heat_loss['mi_selection_status'], 'selected')
        self.assertEqual(selected['heater_part_number'], heater.part_number)
        self.assertEqual(selected['heater_set_count'], 3)
        self.assertEqual(selected['selection_basis']['heater_set_count'], 3)
        self.assertTrue(selected['selection_basis']['mvp_multi_set_selection'])
        self.assertLess(selected['selection_basis']['per_set_low_voltage_power_density_w_m'], 25.0)
        self.assertGreaterEqual(selected['low_voltage_power_density_w_m'], 25.0)
        self.assertLessEqual(selected['current_cold_start_a'], 8.0)
        self.assertAlmostEqual(
            selected['total_current_cold_start_a'],
            selected['current_cold_start_a'] * 3,
        )

    def test_returns_alternatives_sorted_by_closest_low_voltage_heat_delivery(self):
        family = make_family(max_watt_density_w_m=200.0)
        high_output = make_heater(
            family=family,
            part_number='MIQ-HIGH',
            resistance_ohms_m=0.05,
        )
        closer_output = make_heater(
            family=family,
            part_number='MIQ-CLOSE',
            resistance_ohms_m=0.1,
        )
        make_cold_lead(heater=high_output)
        make_cold_lead(heater=closer_output)
        heat_loss = make_heat_loss(design_heat_loss=20.0)
        line = make_line(line_length=100.0)

        selected, alternatives = get_mi_heater_options(heat_loss, line, make_project_settings())

        self.assertEqual(selected['heater_part_number'], 'MIQ-CLOSE')
        self.assertEqual([item['heater_part_number'] for item in alternatives], ['MIQ-HIGH'])


class MIRealCatalogueSmokeTests(TestCase):
    def test_validated_catalogue_loaded_by_command_can_select_tcr_corrected_mi_heater(self):
        call_command('populate_mi_catalogue', stdout=StringIO())
        family = MICableFamily.objects.get(vendor='THR', family_name='MIQ')
        family.is_validated = True
        family.save()
        heat_loss = make_heat_loss(design_heat_loss=10.0)
        line = make_line(line_length=10.0, maint_temp=120.0, design_temp=260.0)

        selected, alternatives = get_mi_heater_options(
            heat_loss,
            line,
            make_project_settings(
                startup_t=0.0,
                min_amb_t=-20.0,
                max_cb_size=40.0,
                restrict_cb_current=100.0,
                temp_class='',
            ),
        )

        self.assertEqual(heat_loss['mi_selection_status'], 'selected')
        self.assertEqual(selected['vendor'], 'THR')
        self.assertEqual(selected['family_name'], 'MIQ')
        self.assertEqual(selected['heater_part_number'], 'MIQ-11EOH-2S')
        self.assertEqual(selected['cold_lead_option_code'], 'CL-4FT')
        self.assertGreater(len(alternatives), 0)
        resistance_basis = selected['selection_basis']['resistance_temperature_basis']
        self.assertEqual(resistance_basis['conductor_material'], 'Nickel-Chromium')
        self.assertAlmostEqual(resistance_basis['tcr_per_degree_c'], 0.000088)
        self.assertEqual(resistance_basis['maintain_method'], 'linear_tcr_per_degree_c')
        self.assertEqual(resistance_basis['startup_method'], 'linear_tcr_per_degree_c')
        self.assertEqual(resistance_basis['startup_temp_c'], -20.0)
        self.assertEqual(
            resistance_basis['cold_start_temperature_basis']['selected_source'],
            'min_amb_t',
        )
        self.assertGreater(selected['heater_resistance_ohms'], selected['heater_base_resistance_ohms'])
        self.assertLess(selected['heater_startup_resistance_ohms'], selected['heater_base_resistance_ohms'])

    def test_real_catalogue_selects_multi_set_mi_for_high_temperature_sample_line(self):
        call_command('populate_mi_catalogue', stdout=StringIO())
        family = MICableFamily.objects.get(vendor='THR', family_name='MIQ')
        family.is_validated = True
        family.save()
        heat_loss = make_heat_loss(
            uid=9433,
            design_heat_loss=102.95195280403176,
            tracer_adder=18.02621241242483,
        )
        line = make_line(
            uid=9433,
            line_id='1__1-PS-A',
            line_size=30.0,
            line_length=70.95,
            maint_temp=45.0,
            oper_temp=45.0,
            design_temp=350.0,
        )

        selected, _alternatives = get_mi_heater_options(
            heat_loss,
            line,
            make_project_settings(
                voltage=240.0,
                voltage_var_factor=5.0,
                startup_t=5.0,
                min_amb_t=5.0,
                max_cb_size=25.0,
                restrict_cb_current=80.0,
                allowablevdrop=6.0,
                temp_class='T3',
            ),
        )

        self.assertEqual(heat_loss['mi_selection_status'], 'selected')
        self.assertEqual(selected['vendor'], 'THR')
        self.assertEqual(selected['heater_part_number'], 'MIQ-31E4H-2S')
        self.assertEqual(selected['heater_set_count'], 3)
        self.assertGreaterEqual(selected['low_voltage_power_density_w_m'], heat_loss['design_heat_loss'])
        self.assertLessEqual(selected['current_cold_start_a'], 20.0)
        self.assertAlmostEqual(selected['heated_length_m'], 88.97621241242483)
