from io import StringIO

from django.contrib import admin
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, transaction
from django.core.exceptions import FieldDoesNotExist
from django.test import TestCase

from eht.mi_catalogue_readiness import evaluate_mi_family_readiness
from eht.models import (
    HeatTracingInput,
    MIAlloyTempFactor,
    MICableFamily,
    MICableHeater,
    MIColdLeadOption,
    ProjectData,
    SelectedMIHeater,
)
import eht.admin  # noqa: F401 - ensures admin registrations are loaded for smoke tests.


def make_mi_family(**overrides):
    values = {
        'vendor': 'THR',
        'family_name': 'MIQ',
        'alloy_type': 'Alloy 825',
        'max_voltage': 600.0,
        'max_sheath_temp_c': 600.0,
        'max_maintain_temp_c': 500.0,
        'max_exposure_temp_c': 600.0,
        'max_watt_density_w_m': 250.0,
        'min_circuit_length_m': 1.0,
        'max_circuit_length_m': 200.0,
        'temp_class_rating': 'T4',
        'gas_group': 'IIC',
        'zone_approval': 'IEC Zone 1',
        'source_document': 'Verified vendor document reference',
        'is_validated': False,
    }
    values.update(overrides)
    return MICableFamily.objects.create(**values)


def make_mi_heater(family=None, **overrides):
    values = {
        'family': family or make_mi_family(),
        'part_number': 'MIQ-R001',
        'conductors': 1,
        'resistance_ohms_m': 0.010,
        'max_current_a': 16.0,
        'cold_lead_resistance_ohms_m': 0.002,
        'cold_lead_max_ampacity_a': 20.0,
        'sheath_material': 'Alloy 825',
        'conductor_material': 'Nickel Chromium',
    }
    values.update(overrides)
    return MICableHeater.objects.create(**values)


def make_input_line(**overrides):
    values = {
        'proj_id': 'p1',
        'line_id': 'LINE-MI-001',
        'service_type': 'EP',
        'line_size': 2.0,
        'line_length': 25.0,
        'ins_mat_type': 'Mineral Wool',
        'insul_thick': 50.0,
        'maint_temp': 120.0,
        'oper_temp': 100.0,
        'design_temp': 140.0,
        'status': 'confirmed',
    }
    values.update(overrides)
    ensure_project(values['proj_id'])
    return HeatTracingInput.objects.create(**values)


def ensure_project(project_id):
    ProjectData.objects.get_or_create(
        proj_id=project_id,
        defaults={
            'min_amb_t': 20.0,
            'max_amb_t': 45.0,
            'startup_t': 15.0,
            'area_class': 'SAFE',
            'temp_class': 'T3',
            'voltage': 230.0,
            'max_cb_size': 10,
            'restrict_cb_current': 80.0,
            'vendor': 'THR',
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
        },
    )


class MICatalogueStructureTests(TestCase):
    def test_mi_catalogue_starts_empty_without_demo_seed_data(self):
        self.assertEqual(MICableFamily.objects.count(), 0)
        self.assertEqual(MICableHeater.objects.count(), 0)
        self.assertEqual(MIAlloyTempFactor.objects.count(), 0)

    def test_old_demo_seed_command_is_not_available(self):
        with self.assertRaises(CommandError):
            call_command('populate_mi_cables')

    def test_mi_cable_family_validation_flag_defaults_false(self):
        family = make_mi_family(is_validated=False)

        self.assertFalse(family.is_validated)

    def test_mi_cable_family_unique_vendor_family_pair(self):
        make_mi_family(vendor='THR', family_name='MIQ')

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                make_mi_family(vendor='THR', family_name='MIQ')

    def test_mi_heater_uses_ohms_per_metre_not_legacy_ohms_per_km_field(self):
        heater = make_mi_heater(resistance_ohms_m=0.025)

        self.assertAlmostEqual(heater.resistance_ohms_m, 0.025)
        with self.assertRaises(FieldDoesNotExist):
            MICableHeater._meta.get_field('base_resistance_ohms_km')

    def test_mi_heater_stores_cold_lead_electrical_limits(self):
        heater = make_mi_heater(
            cold_lead_resistance_ohms_m=0.003,
            cold_lead_max_ampacity_a=18.0,
        )

        self.assertAlmostEqual(heater.cold_lead_resistance_ohms_m, 0.003)
        self.assertAlmostEqual(heater.cold_lead_max_ampacity_a, 18.0)

    def test_mi_heater_stores_conductor_tcr_for_resistance_temperature_correction(self):
        heater = make_mi_heater(tcr_per_degree_c=0.00085)

        self.assertAlmostEqual(heater.tcr_per_degree_c, 0.00085)

    def test_cold_lead_option_is_linked_to_heater_not_family(self):
        heater = make_mi_heater()
        option = MIColdLeadOption.objects.create(
            heater=heater,
            option_code='CL-2M',
            length_m=2.0,
        )

        self.assertEqual(option.heater, heater)
        self.assertFalse(any(field.name == 'family' for field in MIColdLeadOption._meta.fields))

    def test_cold_lead_option_is_unique_per_heater_and_code(self):
        heater = make_mi_heater()
        MIColdLeadOption.objects.create(heater=heater, option_code='CL-2M', length_m=2.0)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                MIColdLeadOption.objects.create(heater=heater, option_code='CL-2M', length_m=2.0)

    def test_phase_defaults_to_single_phase_for_existing_import_shape(self):
        line = make_input_line()

        self.assertEqual(line.phase, '1PH')

    def test_existing_alloy_temperature_factor_model_is_reused(self):
        factor = MIAlloyTempFactor.objects.create(
            alloy_type='Alloy 825',
            temperature_c=200.0,
            resistance_multiplier=1.02,
        )

        self.assertIn('Alloy 825 at 200.0', str(factor))
        self.assertIn('1.02x', str(factor))

    def test_populate_mi_catalogue_creates_conductor_material_and_tcr_values(self):
        call_command('populate_mi_catalogue', stdout=StringIO())

        thermon = MICableHeater.objects.get(part_number='MIQ-11EOH-2S')
        nvent_high_tcr = MICableHeater.objects.get(part_number='HAC2N0.036K')
        chromalox_nichrome = MICableHeater.objects.get(part_number='410B')
        chromalox_alloy_825 = MICableHeater.objects.get(part_number='115B')

        self.assertEqual(thermon.conductor_material, 'Nickel-Chromium')
        self.assertAlmostEqual(thermon.tcr_per_degree_c, 0.000088)
        self.assertEqual(nvent_high_tcr.conductor_material, 'Alloy 825 Conductor')
        self.assertAlmostEqual(nvent_high_tcr.tcr_per_degree_c, 0.003900)
        self.assertEqual(chromalox_nichrome.conductor_material, 'Nichrome T')
        self.assertAlmostEqual(chromalox_nichrome.tcr_per_degree_c, 0.000180)
        self.assertEqual(chromalox_alloy_825.conductor_material, 'Alloy 825 Conductor')
        self.assertAlmostEqual(chromalox_alloy_825.tcr_per_degree_c, 0.003930)
        self.assertFalse(MICableFamily.objects.filter(is_validated=True).exists())

    def test_populate_mi_catalogue_update_repairs_existing_blank_tcr_rows_without_unvalidating_family(self):
        family = make_mi_family(
            vendor='THR',
            family_name='MIQ',
            source_document='Old local note',
            is_validated=True,
        )
        heater = make_mi_heater(
            family=family,
            part_number='MIQ-11EOH-2S',
            conductor_material='',
            tcr_per_degree_c=0.0,
            resistance_ohms_m=99.0,
        )

        call_command('populate_mi_catalogue', vendor='THR', update=True, stdout=StringIO())

        family.refresh_from_db()
        heater.refresh_from_db()
        self.assertTrue(family.is_validated)
        self.assertEqual(family.source_document, 'TEP0020-MIQ-Spec.pdf')
        self.assertAlmostEqual(heater.resistance_ohms_m, 36.10)
        self.assertEqual(heater.conductor_material, 'Nickel-Chromium')
        self.assertAlmostEqual(heater.tcr_per_degree_c, 0.000088)
        self.assertTrue(
            MIColdLeadOption.objects.filter(heater=heater, option_code='CL-4FT', length_m=1.219).exists()
        )
        self.assertTrue(
            MIColdLeadOption.objects.filter(heater=heater, option_code='CL-7FT', length_m=2.134).exists()
        )

    def test_mi_family_readiness_blocks_incomplete_catalogue_before_validation(self):
        family = make_mi_family(source_document='')
        make_mi_heater(family=family, conductor_material='', tcr_per_degree_c=0.0)

        report = evaluate_mi_family_readiness(family)

        self.assertFalse(report['ready'])
        self.assertIn('SOURCE_DOCUMENT_MISSING', report['blockers'])
        self.assertTrue(any('CONDUCTOR_MATERIAL_MISSING' in item for item in report['blockers']))
        self.assertTrue(any('TCR_MISSING_OR_NON_POSITIVE' in item for item in report['blockers']))
        self.assertTrue(any('NO_COLD_LEAD_OPTIONS' in item for item in report['blockers']))

    def test_mi_catalogue_readiness_command_marks_only_ready_reviewed_families_validated(self):
        ready_family = make_mi_family(vendor='THR', family_name='MIQ')
        ready_heater = make_mi_heater(
            family=ready_family,
            part_number='MIQ-11EOH-2S',
            conductor_material='Nickel-Chromium',
            tcr_per_degree_c=0.000088,
        )
        MIColdLeadOption.objects.create(heater=ready_heater, option_code='CL-4FT', length_m=1.219)
        blocked_family = make_mi_family(vendor='CHR', family_name='MI-825B', source_document='')

        output = StringIO()
        call_command('mi_catalogue_readiness', mark_validated=True, confirm_reviewed=True, stdout=output)

        ready_family.refresh_from_db()
        blocked_family.refresh_from_db()
        self.assertTrue(ready_family.is_validated)
        self.assertFalse(blocked_family.is_validated)
        self.assertIn('Marked 1 MI family/families as validated.', output.getvalue())

    def test_mi_catalogue_readiness_command_requires_explicit_review_confirmation(self):
        with self.assertRaises(CommandError):
            call_command('mi_catalogue_readiness', mark_validated=True, stdout=StringIO())

    def test_mi_catalogue_models_are_registered_in_admin(self):
        self.assertIn(MICableFamily, admin.site._registry)
        self.assertIn(MICableHeater, admin.site._registry)
        self.assertIn(MIColdLeadOption, admin.site._registry)
        self.assertIn(MIAlloyTempFactor, admin.site._registry)
        self.assertIn(SelectedMIHeater, admin.site._registry)


class SelectedMIHeaterStructureTests(TestCase):
    def test_selected_mi_heater_persists_catalogue_refs_and_snapshot_values(self):
        line = make_input_line()
        heater = make_mi_heater()
        cold_lead = MIColdLeadOption.objects.create(
            heater=heater,
            option_code='CL-2M',
            length_m=2.0,
        )

        result = SelectedMIHeater.objects.create(
            line=line,
            heater=heater,
            cold_lead_option=cold_lead,
            heated_length_m=27.5,
            cold_lead_option_code='CL-2M',
            cold_lead_length_m=2.0,
            heater_resistance_ohms=0.275,
            cold_lead_resistance_total_ohms=0.004,
            power_nominal_w=1900.0,
            power_density_w_m=69.1,
            current_nominal_a=8.3,
            current_cold_start_a=9.1,
            max_sheath_temp_published_c=120.0,
            project_t_class_limit_c=135.0,
            t_class_verdict='pass',
            selection_status='selected',
            selection_rejection_reasons=[],
            selection_basis={'rule_set': 'MI_SELECTION_MVP_V1'},
        )

        self.assertEqual(result.line, line)
        self.assertEqual(result.heater, heater)
        self.assertEqual(result.cold_lead_option, cold_lead)
        self.assertAlmostEqual(result.cold_lead_resistance_total_ohms, 0.004)
        self.assertEqual(result.selection_status, 'selected')
        self.assertEqual(result.selection_rejection_reasons, [])
        self.assertEqual(result.selection_basis['rule_set'], 'MI_SELECTION_MVP_V1')
