import math

import pandas as pd
from django.test import SimpleTestCase, TestCase

from eht.calculations.heat_loss import (
    CONDUCTIVITY_BASIS_LEGACY_MAINT_TEMPERATURE,
    CONDUCTIVITY_BASIS_MEAN_TEMPERATURE,
    SR_ACCESSORY_ADDER_RULE_SET,
    calculate_accessory_adders,
    calculate_heat_loss,
    calculate_insulation_conductivity,
)
from eht.data_service import fetch_vendor_data, store_calculated_results
from eht.heat_loss_methods import (
    DEFAULT_HEAT_LOSS_METHOD,
    HEAT_LOSS_METHOD_INTEGRATED_KT,
    HEAT_LOSS_METHOD_LEGACY_MAINT_TEMPERATURE,
)
from eht.models import ElecEHT_Vendor, HeatLoss, HeatTracingInput
from eht.tests import make_asme_table, make_line, make_project_record, make_project_settings, make_thermal_table


def make_temperature_dependent_thermal_table():
    return pd.DataFrame([
        {'Ins_Mat_Type': 'MW', 'K_factor_A': 0.0, 'K_factor_B': 0.001, 'K_factor_C': 0.0},
    ])


class HeatLossEvidenceTests(SimpleTestCase):
    def test_calculate_insulation_conductivity_defaults_to_mean_temperature(self):
        result = calculate_insulation_conductivity(
            100.0,
            20.0,
            make_temperature_dependent_thermal_table(),
        )

        self.assertAlmostEqual(result['conductivity'], 0.06, places=6)
        self.assertEqual(result['basis']['requested_method'], DEFAULT_HEAT_LOSS_METHOD)
        self.assertEqual(result['basis']['effective_method'], DEFAULT_HEAT_LOSS_METHOD)
        self.assertEqual(result['basis']['rule_set'], CONDUCTIVITY_BASIS_MEAN_TEMPERATURE)
        self.assertEqual(result['basis']['temperature_basis'], 'mean_insulation_temperature')
        self.assertAlmostEqual(result['basis']['evaluation_temperature_c'], 60.0, places=6)

    def test_calculate_insulation_conductivity_preserves_legacy_method(self):
        result = calculate_insulation_conductivity(
            100.0,
            20.0,
            make_temperature_dependent_thermal_table(),
            HEAT_LOSS_METHOD_LEGACY_MAINT_TEMPERATURE,
        )

        self.assertAlmostEqual(result['conductivity'], 0.1, places=6)
        self.assertEqual(result['basis']['effective_method'], HEAT_LOSS_METHOD_LEGACY_MAINT_TEMPERATURE)
        self.assertEqual(result['basis']['rule_set'], CONDUCTIVITY_BASIS_LEGACY_MAINT_TEMPERATURE)
        self.assertEqual(result['basis']['temperature_basis'], 'maint_temp')

    def test_calculate_insulation_conductivity_records_placeholder_fallback(self):
        result = calculate_insulation_conductivity(
            100.0,
            20.0,
            make_temperature_dependent_thermal_table(),
            HEAT_LOSS_METHOD_INTEGRATED_KT,
        )

        self.assertAlmostEqual(result['conductivity'], 0.06, places=6)
        self.assertEqual(result['basis']['requested_method'], HEAT_LOSS_METHOD_INTEGRATED_KT)
        self.assertEqual(result['basis']['effective_method'], DEFAULT_HEAT_LOSS_METHOD)
        self.assertTrue(result['basis']['warnings'])

    def test_calculate_accessory_adders_returns_named_rule_evidence(self):
        adders = calculate_accessory_adders(make_line(), 60.3)

        self.assertAlmostEqual(adders['total'], adders['valve'] + adders['support'] + adders['flange'], places=6)
        self.assertEqual(adders['basis']['rule_set'], SR_ACCESSORY_ADDER_RULE_SET)
        self.assertEqual(adders['basis']['pipe_size_basis'], 'pipe_od_in')
        self.assertAlmostEqual(adders['basis']['pipe_size_in'], 60.3 / 25.4, places=6)
        self.assertEqual(adders['basis']['items']['valve']['quantity'], 2.0)
        self.assertAlmostEqual(adders['basis']['items']['valve']['total_m'], adders['valve'], places=6)

    def test_calculate_heat_loss_returns_design_evidence_payload(self):
        result = calculate_heat_loss(
            make_line(),
            make_project_settings(heat_loss_sf=1.25),
            make_asme_table(),
            make_thermal_table(),
        )

        pipe_size_mm = 60.3
        expected_base_heat_loss = (2 * math.pi * 0.05 * 80.0) / math.log((2 * 50.0 + pipe_size_mm) / pipe_size_mm)

        self.assertAlmostEqual(result['pipe_size_mm'], pipe_size_mm, places=6)
        self.assertAlmostEqual(result['conductivity'], 0.05, places=6)
        self.assertEqual(result['conductivity_basis']['effective_method'], DEFAULT_HEAT_LOSS_METHOD)
        self.assertEqual(result['conductivity_basis']['rule_set'], CONDUCTIVITY_BASIS_MEAN_TEMPERATURE)
        self.assertAlmostEqual(result['wind_correction'], 1.0, places=6)
        self.assertAlmostEqual(result['base_heat_loss'], expected_base_heat_loss, places=6)
        self.assertAlmostEqual(result['design_heat_loss'], expected_base_heat_loss * 1.25, places=6)
        self.assertAlmostEqual(result['accessory_adders']['total'], result['tracer_adder'], places=6)
        self.assertEqual(set(result['accessory_adders']), {'valve', 'support', 'flange', 'total', 'basis'})
        self.assertEqual(result['accessory_adders']['basis']['rule_set'], SR_ACCESSORY_ADDER_RULE_SET)


class HeatLossEvidencePersistenceTests(TestCase):
    def test_store_calculated_results_persists_heat_loss_evidence(self):
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

        store_calculated_results('p1', {
            'heat_loss': [
                {
                    'uid': line.uid,
                    'heat_loss': 15.0,
                    'base_heat_loss': 12.0,
                    'design_heat_loss': 15.0,
                    'heat_loss_sf': 1.25,
                    'pipe_size_mm': 60.3,
                    'conductivity': 0.05,
                    'conductivity_basis': {
                        'requested_method': DEFAULT_HEAT_LOSS_METHOD,
                        'effective_method': DEFAULT_HEAT_LOSS_METHOD,
                    },
                    'wind_correction': 1.0,
                    'accessory_adders': {
                        'valve': 1.1,
                        'support': 2.2,
                        'flange': 0.3,
                        'total': 3.6,
                    },
                    'tracer_adder': 3.6,
                },
            ],
            'selected_tracers': [],
            'alternative_tracers': [],
            'power_distribution': [],
            'boq_per_line': {},
            'consolidated_boq': {},
            'tracer_power_param': [],
        })

        result = HeatLoss.objects.get(line=line)
        self.assertEqual(result.heat_loss, 15.0)
        self.assertEqual(result.base_heat_loss, 12.0)
        self.assertEqual(result.design_heat_loss, 15.0)
        self.assertEqual(result.heat_loss_sf, 1.25)
        self.assertEqual(result.pipe_size_mm, 60.3)
        self.assertEqual(result.conductivity, 0.05)
        self.assertEqual(result.conductivity_basis['effective_method'], DEFAULT_HEAT_LOSS_METHOD)
        self.assertEqual(result.wind_correction, 1.0)
        self.assertEqual(result.accessory_adders['total'], 3.6)


class VendorCatalogueRetrievalTests(TestCase):
    def test_fetch_vendor_data_matches_selected_vendor_case_insensitively(self):
        ElecEHT_Vendor.objects.create(
            V_UID='KRZ_SR',
            Vendor='Krus-Zapad',
            Tracer_Family='Self Regulating',
            Voltage=230.0,
        )

        result = fetch_vendor_data('KRUS-Zapad', 240.0)

        self.assertEqual(result['V_UID'].tolist(), ['KRZ_SR'])

    def test_fetch_vendor_data_does_not_apply_voltage_lower_bound_in_database(self):
        ElecEHT_Vendor.objects.create(
            V_UID='SST_230',
            Vendor='SST',
            Tracer_Family='Self Regulating',
            Voltage=230.0,
        )

        result = fetch_vendor_data('SST', 240.0)

        self.assertEqual(result['V_UID'].tolist(), ['SST_230'])
