from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class CalculationManualGuideTests(TestCase):
    def test_calculation_manual_view_renders_visual_guide_and_manual_content(self):
        user = User.objects.create_user(username='manual-reviewer', password='password123')
        self.client.force_login(user)

        response = self.client.get(reverse('calculation_manual_view'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'EHT Design Guide &amp; Calculation Manual')
        self.assertContains(response, 'calculation-workspace-preview.svg')
        self.assertContains(response, 'calculation-flow-map.svg')
        self.assertContains(response, 'calculation-detailed-flow.svg')
        self.assertContains(response, 'calculation-review-board.svg')
        self.assertContains(response, 'manual_guide.js')
        self.assertContains(response, 'Search manual')
        self.assertContains(response, 'Print / PDF')
        self.assertContains(response, 'Heat-transfer physics')
        self.assertContains(response, 'IEEE and IEC controls')
        self.assertContains(response, 'Cold Cable Engineering')
        self.assertContains(response, 'Engineering deep dive')
        self.assertContains(response, 'Open the swim-lane calculation flow')
        self.assertContains(response, 'Formula reference and calculation evidence trail')
        self.assertContains(response, 'T<sub>mean</sub>')
        self.assertContains(response, 'T<sup>2</sup>')
        self.assertContains(response, 'SR Selection Diagnostics')
        self.assertContains(response, 'MI Automatic Fallback Basis')
        self.assertContains(response, 'MI Selection Records')
        self.assertContains(response, 'MI Pass 1-18 Engineering Record')
        self.assertContains(response, 'SR Pass 19 Straight-Run Closure Record')
        self.assertContains(response, 'SR Duty Ratio')
        self.assertContains(response, 'Straight Parallel Runs')
        self.assertContains(response, 'Pending Activities and Phase Assignment')
        self.assertContains(response, 'Noteworthy Architectural Decisions')
        self.assertContains(response, 'Priority P1 - Next Calculation Module')
        self.assertContains(response, 'SR straight-run path with bounded MI fallback')
        self.assertContains(response, 'Known Limitations')
        self.assertNotContains(response, 'Formulas should read like engineering notation')

    def test_manual_and_design_guide_use_shared_mcb_sr_parallel_basis(self):
        manual = (Path(settings.BASE_DIR) / 'NOTES' / 'CALCULATION_MODULE_USER_MANUAL.md').read_text(encoding='utf-8')
        design_guide = (Path(settings.BASE_DIR) / 'templates' / 'eht' / 'design_guide.html').read_text(encoding='utf-8')

        self.assertIn('SR parallel runs share one 2-pole MCB per run group', manual)
        self.assertIn('SR parallel straight runs share one 2-pole MCB per run group', design_guide)
        self.assertNotIn('SR parallel runs are represented as independent protected branches', manual)
        self.assertNotIn('each run/set is modelled as an independently protected branch', design_guide)

    def test_qa_p1_worked_examples_cover_required_mvp_cases(self):
        examples = (Path(settings.BASE_DIR) / 'NOTES' / 'verification' / 'QA_P1_WORKED_EXAMPLES.md').read_text(encoding='utf-8')

        self.assertIn('Example 1 - SR Heat Loss And Straight-Run Selection', examples)
        self.assertIn('Example 2 - MI Automatic Fallback Evidence', examples)
        self.assertIn('Example 3 - Direct Single-Phase Cold Cable', examples)
        self.assertIn('Example 4 - Shared FeederCable / BranchCable Optimisation', examples)
        self.assertIn('VD = 2 x I x R(T) x L', examples)
        self.assertIn('Conductor volume proxy', examples)
