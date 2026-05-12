import math

from django.test import SimpleTestCase, TestCase

from eht.calculations.heat_loss import (
    SR_ACCESSORY_ADDER_RULE_SET,
    calculate_accessory_adders,
    calculate_heat_loss,
)
from eht.data_service import store_calculated_results
from eht.models import HeatLoss, HeatTracingInput
from eht.tests import make_asme_table, make_line, make_project_record, make_project_settings, make_thermal_table


class HeatLossEvidenceTests(SimpleTestCase):
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
        self.assertEqual(result.wind_correction, 1.0)
        self.assertEqual(result.accessory_adders['total'], 3.6)
