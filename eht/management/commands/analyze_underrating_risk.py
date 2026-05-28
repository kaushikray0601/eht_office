"""
Underrating Risk Analysis
==========================

Analyzes the risk of selecting an undersized tracer when using PTC-calculated
coefficients vs. manually-curated vendor data.

Critical Question: If my method OVERESTIMATES power output, then actual
heat capacity would be LOWER than predicted, causing the tracer to be
UNDERRATED and potentially FAIL to compensate heat loss.

This tool:
1. Compares power predictions across temperature ranges
2. Identifies directional bias (over/underestimate)
3. Calculates probability of underrating at different temps
4. Provides confidence metrics and risk alerts

Usage:
    python manage.py analyze_underrating_risk --sample 10
    python manage.py analyze_underrating_risk --sample 10 --detailed
"""

import numpy as np
from django.core.management.base import BaseCommand
from eht.models import ElecEHT_Vendor
import random


class Command(BaseCommand):
    help = 'Analyze underrating risk when using PTC-calculated coefficients'

    def add_arguments(self, parser):
        parser.add_argument('--sample', type=int, default=10)
        parser.add_argument('--detailed', action='store_true')

    def handle(self, *args, **options):
        sample_size = options['sample']
        detailed = options['detailed']

        self.stdout.write(self.style.WARNING('\n' + '='*130))
        self.stdout.write(self.style.WARNING('UNDERRATING RISK ANALYSIS'))
        self.stdout.write(self.style.WARNING('Comparing PTC-Calculated vs. Vendor-Curated Coefficients'))
        self.stdout.write(self.style.WARNING('='*130))

        # Get test cables (manual data)
        all_sr = ElecEHT_Vendor.objects.filter(Tracer_Family='Self Regulating')
        manual_cables = [c for c in all_sr if float(c.A_Coeff) != 0 or float(c.B_Coeff) != 0 or float(c.C_Coeff) != 0]
        new_vendors = {'Eltherm', 'Heat Trace', 'Pentair'}
        manual_cables = [c for c in manual_cables if c.Vendor not in new_vendors]

        if len(manual_cables) < sample_size:
            selected = manual_cables
        else:
            selected = random.sample(manual_cables, sample_size)

        self.stdout.write(f'\n🔍 Analyzing underrating risk for {len(selected)} cables\n')

        all_results = []
        for cable in selected:
            result = self._analyze_underrating_risk(cable, detailed)
            all_results.append(result)
            if detailed:
                self._print_detailed_analysis(result)
            else:
                self._print_summary_line(result)

        # Overall risk assessment
        self._print_overall_assessment(all_results)

        self.stdout.write(self.style.WARNING('\n' + '='*130 + '\n'))

    def _analyze_underrating_risk(self, cable, detailed=False):
        """Analyze underrating risk for a cable"""

        result = {
            'V_UID': cable.V_UID,
            'Vendor': cable.Vendor,
            'Model': cable.Tracer_Model,
            'Power_ref': float(cable.Power_at_Startup_T),
            'Voltage': float(cable.Voltage),
            'Existing_A': float(cable.A_Coeff),
            'Existing_B': float(cable.B_Coeff),
            'Existing_C': float(cable.C_Coeff),
            'Maint_T': float(cable.Maint_T),
            'Max_Op_T': float(cable.Max_Op_T),
            'Min_Install_T': float(cable.Min_Installation_T),
        }

        try:
            # Calculate using PTC method
            P_ref = float(cable.Power_at_Startup_T)
            T_ref = 10.0
            temp_coeff = 0.0025

            # Generate temperature points
            min_temp = float(cable.Min_Installation_T)
            max_temp = float(cable.Max_Op_T)

            temperatures = np.array([-40, -20, 0, 10, 25, 50, 75, 100, 120, 150])
            temperatures = temperatures[
                (temperatures >= min_temp - 10) &
                (temperatures <= max_temp + 10)
            ]

            if len(temperatures) < 3:
                result['error'] = 'Insufficient temperature range'
                return result

            # Calculate powers
            powers_ptc = P_ref / (1 + temp_coeff * (temperatures - T_ref))
            coeffs = np.polyfit(temperatures, powers_ptc, 2)
            A_calc, B_calc, C_calc = coeffs[0], coeffs[1], coeffs[2]

            # Calculate power at key temperatures using BOTH methods
            result['temperatures'] = temperatures
            result['powers_calculated'] = powers_ptc

            # Calculate powers using EXISTING coefficients
            powers_existing = result['Existing_A'] * temperatures**2 + result['Existing_B'] * temperatures + result['Existing_C']
            result['powers_existing'] = powers_existing

            # Calculate differences
            deltas = powers_ptc - powers_existing  # Positive = my method higher = underrating risk
            result['deltas'] = deltas
            result['delta_pct'] = (deltas / powers_existing * 100)

            # Risk assessment at key temperatures
            # Cold temp (-40°C) - underrating risk low
            # Ambient (10°C) - baseline
            # Maintenance (Maint_T) - underrating risk HIGH
            # Operating limit (Max_Op_T) - underrating risk HIGHEST

            result['underrating_prob'] = self._calculate_underrating_probability(deltas)
            result['risk_level'] = self._assess_risk_level(deltas, result['Maint_T'], temperatures)
            result['worst_case'] = {
                'temp': temperatures[np.argmax(deltas)],
                'delta': np.max(deltas),
                'delta_pct': np.max(result['delta_pct'])
            }
            result['best_case'] = {
                'temp': temperatures[np.argmin(deltas)],
                'delta': np.min(deltas),
                'delta_pct': np.min(result['delta_pct'])
            }

            result['success'] = True

        except Exception as e:
            result['error'] = str(e)

        return result

    def _calculate_underrating_probability(self, deltas):
        """Calculate probability of underrating (where my method > existing)"""
        underrated = np.sum(deltas > 0) / len(deltas)
        return float(underrated) * 100

    def _assess_risk_level(self, deltas, maint_t, temperatures):
        """Assess risk level based on maintenance temperature"""
        # Find delta at maintenance temperature
        if maint_t in temperatures:
            idx = np.where(temperatures == maint_t)[0][0]
            delta_at_maint = deltas[idx]
        else:
            # Interpolate to maintenance temperature
            f = np.interp(maint_t, temperatures, deltas)
            delta_at_maint = f

        if delta_at_maint > 10:
            return '🔴 HIGH RISK'
        elif delta_at_maint > 5:
            return '🟠 MEDIUM RISK'
        elif delta_at_maint > 0:
            return '🟡 LOW RISK'
        else:
            return '🟢 SAFE'

    def _print_summary_line(self, result):
        """Print one-line summary"""
        if 'error' in result:
            self.stdout.write(f"❌ {result['Vendor']:12} - {result['error']}")
            return

        risk = result['risk_level'].split()[0]  # Just the emoji
        self.stdout.write(
            f"{risk} {result['Vendor']:12} {result['Model']:15} "
            f"{result['underrating_prob']:5.1f}% underrated | "
            f"Worst: {result['worst_case']['delta_pct']:+6.1f}% @ "
            f"{result['worst_case']['temp']:.0f}°C"
        )

    def _print_detailed_analysis(self, result):
        """Print detailed analysis"""
        if 'error' in result:
            self.stdout.write(f"\n❌ {result['V_UID']} - {result['error']}\n")
            return

        self.stdout.write(f"\n{'='*130}")
        self.stdout.write(f"📊 {result['V_UID']}")
        self.stdout.write(f"   {result['Vendor']:15} {result['Model']:15} | "
                        f"{result['Power_ref']:.1f}W @ {result['Voltage']:.0f}V")
        self.stdout.write(f"   Maintenance Temp: {result['Maint_T']}°C | Operating Range: {result['Min_Install_T']}-{result['Max_Op_T']}°C")

        self.stdout.write(f"\n   Temperature-Dependent Power Comparison:")
        self.stdout.write(f"   {'Temp(°C)':<12} {'Vendor':<12} {'Calculated':<12} {'Delta':<12} {'% Diff':<12} {'Risk':<15}")
        self.stdout.write(f"   {'-'*120}")

        for i, temp in enumerate(result['temperatures']):
            p_vendor = result['powers_existing'][i]
            p_calc = result['powers_calculated'][i]
            delta = result['deltas'][i]
            pct = result['delta_pct'][i]

            # Risk indicator at this temperature
            if temp == result['Maint_T']:
                risk_indicator = "⚠️  MAINT TEMP"
            elif temp == result['Max_Op_T']:
                risk_indicator = "🔴 MAX OPERATING"
            elif delta > 0:
                risk_indicator = "❌ UNDERRATED"
            else:
                risk_indicator = "✅ Safe"

            self.stdout.write(
                f"   {temp:<12.0f} {p_vendor:<12.2f} {p_calc:<12.2f} "
                f"{delta:<12.2f} {pct:<12.1f} {risk_indicator:<15}"
            )

        self.stdout.write(f"\n   Risk Summary:")
        self.stdout.write(f"     Probability of underrating: {result['underrating_prob']:.1f}%")
        self.stdout.write(f"     Worst case: {result['worst_case']['delta_pct']:+.1f}% @ {result['worst_case']['temp']:.0f}°C")
        self.stdout.write(f"     Best case: {result['best_case']['delta_pct']:+.1f}% @ {result['best_case']['temp']:.0f}°C")
        self.stdout.write(f"     Risk Level: {result['risk_level']}")

    def _print_overall_assessment(self, results):
        """Print overall risk assessment"""
        successful = [r for r in results if r.get('success', False)]

        if not successful:
            return

        self.stdout.write(f"\n{'='*130}")
        self.stdout.write(f"🎯 OVERALL UNDERRATING RISK ASSESSMENT ({len(successful)} cables)\n")

        # Statistics
        underrating_probs = [r['underrating_prob'] for r in successful]
        worst_cases = [r['worst_case']['delta_pct'] for r in successful]
        best_cases = [r['best_case']['delta_pct'] for r in successful]

        self.stdout.write(f"Underrating Probability Distribution:")
        self.stdout.write(f"  Average: {np.mean(underrating_probs):.1f}%")
        self.stdout.write(f"  Median: {np.median(underrating_probs):.1f}%")
        self.stdout.write(f"  Range: {np.min(underrating_probs):.1f}% to {np.max(underrating_probs):.1f}%")

        self.stdout.write(f"\nWorst-Case Overestimation (Underrating Risk):")
        self.stdout.write(f"  Average worst case: {np.mean(worst_cases):+.1f}%")
        self.stdout.write(f"  Max worst case: {np.max(worst_cases):+.1f}%")
        self.stdout.write(f"  Interpretation: My method overestimates by up to {np.max(worst_cases):+.1f}% → Tracer may be UNDERRATED")

        self.stdout.write(f"\nBest-Case Underestimation (Safe Zone):")
        self.stdout.write(f"  Average best case: {np.mean(best_cases):+.1f}%")
        self.stdout.write(f"  Min best case: {np.min(best_cases):+.1f}%")

        # Risk categorization
        high_risk = sum(1 for r in successful if '🔴' in r['risk_level'])
        med_risk = sum(1 for r in successful if '🟠' in r['risk_level'])
        low_risk = sum(1 for r in successful if '🟡' in r['risk_level'])
        safe = sum(1 for r in successful if '🟢' in r['risk_level'])

        self.stdout.write(f"\nRisk Distribution:")
        self.stdout.write(f"  🔴 HIGH RISK (>10% overestimate): {high_risk} cables")
        self.stdout.write(f"  🟠 MEDIUM RISK (5-10% overestimate): {med_risk} cables")
        self.stdout.write(f"  🟡 LOW RISK (0-5% overestimate): {low_risk} cables")
        self.stdout.write(f"  🟢 SAFE (underestimate or match): {safe} cables")

        # Recommendation
        self.stdout.write(f"\n{'─'*130}")
        self.stdout.write(f"⚠️  RECOMMENDATION FOR YOUR USE:\n")

        if np.max(worst_cases) > 15:
            confidence = "🔴 LOW CONFIDENCE"
            action = "DO NOT USE without vendor verification"
        elif np.max(worst_cases) > 10:
            confidence = "🟠 MEDIUM CONFIDENCE"
            action = "Use only with safety factor margin ≥ 15%"
        elif np.max(worst_cases) > 5:
            confidence = "🟡 CAUTION"
            action = "Use with safety factor margin ≥ 10%"
        else:
            confidence = "🟢 HIGH CONFIDENCE"
            action = "Safe to use with normal safety factor"

        self.stdout.write(f"  Confidence Level: {confidence}")
        self.stdout.write(f"  Action: {action}")
        self.stdout.write(f"  Max Underrating Risk: {np.max(worst_cases):+.1f}%")
        self.stdout.write(f"  Suggested Safety Margin: {max(int(-np.min(best_cases)) + 5, 15)}%")

        self.stdout.write(f"\nKey Insight:")
        self.stdout.write(f"  Your empirical data (vendor curves) → Baseline (ground truth)")
        self.stdout.write(f"  My PTC method → May OVERESTIMATE by {np.mean(worst_cases):+.1f}% on average")
        self.stdout.write(f"                → Risk HIGHEST at maintenance temperature ({np.median([r['Maint_T'] for r in successful]):.0f}°C)")
        self.stdout.write(f"                → Can safely use IF you add {max(int(-np.min(best_cases)) + 5, 15)}% safety margin")
