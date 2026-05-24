from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, transaction
from django.core.exceptions import FieldDoesNotExist
from django.test import TestCase

from eht.models import (
    HeatTracingInput,
    MIAlloyTempFactor,
    MICableFamily,
    MICableHeater,
    MIColdLeadOption,
    SelectedMIHeater,
)


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
    return HeatTracingInput.objects.create(**values)


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
