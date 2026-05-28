from django.test import TestCase
from django.urls import reverse


class CalculationManualGuideTests(TestCase):
    def test_calculation_manual_view_renders_visual_guide_and_manual_content(self):
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
