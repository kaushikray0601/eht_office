"""
Self-Regulating Cable Coefficient Calculator
============================================

This command calculates A, B, C coefficients for SR cables by:
1. Using vendor-provided reference power at 10°C
2. Modeling temperature-dependent power using PTC physics
3. Fitting a second-order polynomial: k = A·T² + B·T + C
4. Extracting and reporting coefficients with confidence metrics

Theory:
-------
Self-regulating cables have a positive temperature coefficient (PTC)
semiconductor core. Power output decreases with temperature following:

    P(T) = P_ref / (1 + α(T - T_ref))

Where α is the temperature coefficient (typically 0.002-0.003 for SR cables).

We approximate this with a polynomial for database compatibility.

Usage:
    python manage.py calculate_sr_coefficients --vendor "Eltherm"
    python manage.py calculate_sr_coefficients --all
    python manage.py calculate_sr_coefficients --apply-to-db
"""

import numpy as np
from django.core.management.base import BaseCommand
from django.db.models import Q
from eht.models import ElecEHT_Vendor
from decimal import Decimal
import json


class Command(BaseCommand):
    help = 'Calculate A, B, C coefficients for SR cables from vendor power specifications'

    def add_arguments(self, parser):
        parser.add_argument(
            '--vendor',
            type=str,
            help='Calculate for specific vendor only'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Calculate for all SR cables with zero coefficients'
        )
        parser.add_argument(
            '--apply-to-db',
            action='store_true',
            help='Apply calculated coefficients to database'
        )
        parser.add_argument(
            '--temp-coeff',
            type=float,
            default=0.0025,
            help='Temperature coefficient for PTC material (default 0.0025)'
        )

    def handle(self, *args, **options):
        temp_coeff = options['temp_coeff']
        apply_to_db = options['apply_to_db']

        self.stdout.write(self.style.WARNING('\n' + '='*80))
        self.stdout.write(self.style.WARNING('SR CABLE COEFFICIENT CALCULATOR'))
        self.stdout.write(self.style.WARNING('='*80))

        # Get cables to process
        if options['all']:
            # All SR cables with zero coefficients
            cables = ElecEHT_Vendor.objects.filter(
                Tracer_Family='Self Regulating',
                A_Coeff=0,
                B_Coeff=0,
                C_Coeff=0
            )
        elif options['vendor']:
            cables = ElecEHT_Vendor.objects.filter(
                Vendor=options['vendor'],
                Tracer_Family='Self Regulating',
                A_Coeff=0,
                B_Coeff=0,
                C_Coeff=0
            )
        else:
            # Just new vendors
            cables = ElecEHT_Vendor.objects.filter(
                Vendor__in=['Eltherm', 'Heat Trace', 'Pentair'],
                Tracer_Family='Self Regulating',
                A_Coeff=0,
                B_Coeff=0,
                C_Coeff=0
            )

        self.stdout.write(f'\n📊 Processing {cables.count()} SR cables')
        self.stdout.write(f'Temperature coefficient: {temp_coeff}/°C (PTC effect)')

        results = []

        for cable in cables:
            result = self._calculate_coefficients(
                cable, temp_coeff
            )
            results.append(result)
            self._print_result(result)

            if apply_to_db and result['success']:
                cable.A_Coeff = Decimal(str(result['A_Coeff']))
                cable.B_Coeff = Decimal(str(result['B_Coeff']))
                cable.C_Coeff = Decimal(str(result['C_Coeff']))
                cable.save()

        # Summary
        self.stdout.write(self.style.SUCCESS(f'\n\n📈 SUMMARY ({len(results)} cables):'))
        successful = sum(1 for r in results if r['success'])
        self.stdout.write(f'  ✅ Calculated: {successful}')
        self.stdout.write(f'  ⚠️  Warnings: {len(results) - successful}')

        if apply_to_db:
            self.stdout.write(self.style.SUCCESS(
                f'\n✅ Updated database with {successful} calculated coefficients'
            ))
        else:
            self.stdout.write(self.style.WARNING(
                '\n📌 Preview mode - use --apply-to-db to update database'
            ))

        # Export JSON for reference
        self._export_results_json(results)

        self.stdout.write(self.style.WARNING('\n' + '='*80 + '\n'))

    def _calculate_coefficients(self, cable, temp_coeff):
        """Calculate A, B, C for a specific cable"""

        result = {
            'V_UID': cable.V_UID,
            'Vendor': cable.Vendor,
            'Model': cable.Tracer_Model,
            'P_ref': float(cable.Power_at_Startup_T),
            'success': False,
            'error': None,
            'R_squared': 0,
            'A_Coeff': 0,
            'B_Coeff': 0,
            'C_Coeff': 0,
            'notes': []
        }

        try:
            # Reference power output (at 10°C per vendor specs)
            P_ref = float(cable.Power_at_Startup_T)
            T_ref = 10.0  # Reference temperature where power is specified

            # Generate synthetic data points using PTC model
            # P(T) = P_ref / (1 + temp_coeff * (T - T_ref))
            temperatures = np.array([-40, -20, 0, 10, 25, 50, 75, 100, 120, 150])

            # Filter to cable's valid operating range
            min_temp = float(cable.Min_Installation_T)
            max_temp = float(cable.Max_Op_T)

            temperatures = temperatures[
                (temperatures >= min_temp - 10) &
                (temperatures <= max_temp + 10)
            ]

            if len(temperatures) < 3:
                result['error'] = f'Insufficient temperature range ({len(temperatures)} points)'
                return result

            # Calculate power at each temperature using PTC model
            powers = P_ref / (1 + temp_coeff * (temperatures - T_ref))

            # Fit polynomial: P = A*T² + B*T + C
            coeffs = np.polyfit(temperatures, powers, 2)
            A_fit, B_fit, C_fit = coeffs[0], coeffs[1], coeffs[2]

            # Calculate R² to assess fit quality
            p_fit = np.polyval(coeffs, temperatures)
            ss_res = np.sum((powers - p_fit) ** 2)
            ss_tot = np.sum((powers - np.mean(powers)) ** 2)
            R_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

            result['success'] = True
            result['A_Coeff'] = float(A_fit)
            result['B_Coeff'] = float(B_fit)
            result['C_Coeff'] = float(C_fit)
            result['R_squared'] = float(R_squared)
            result['n_points'] = len(temperatures)
            result['T_min'] = float(min(temperatures))
            result['T_max'] = float(max(temperatures))
            result['notes'].append(f'Fitted to {len(temperatures)} temperature points')
            result['notes'].append(f'Using PTC model: P(T) = P_ref / (1 + {temp_coeff}(T - {T_ref}))')

            if R_squared < 0.95:
                result['notes'].append(f'⚠️ Lower fit quality (R² = {R_squared:.4f})')

        except Exception as e:
            result['error'] = str(e)

        return result

    def _print_result(self, result):
        """Print formatted result"""
        if result['success']:
            self.stdout.write(
                f"\n✅ {result['Vendor']:12} {result['Model']:15} "
                f"{result['P_ref']:5.1f}W @ 10°C"
            )
            self.stdout.write(f"   Coefficients: A={result['A_Coeff']:+.6f}, "
                            f"B={result['B_Coeff']:+.6f}, C={result['C_Coeff']:+.3f}")
            self.stdout.write(f"   R² = {result['R_squared']:.4f} ({result['n_points']} points, "
                            f"{result['T_min']:.0f}-{result['T_max']:.0f}°C)")
            for note in result['notes']:
                self.stdout.write(f"   📝 {note}")
        else:
            self.stdout.write(self.style.ERROR(
                f"❌ {result['Vendor']:12} {result['Model']:15} - {result['error']}"
            ))

    def _export_results_json(self, results):
        """Export results to JSON for reference"""
        json_path = '/home/kr/mydev/eht_office/RESEARCH_DATA/calculated_coefficients.json'

        export_data = {
            'generated': __import__('datetime').datetime.now().isoformat(),
            'method': 'PTC polynomial fitting',
            'results': [
                {
                    'v_uid': r['V_UID'],
                    'vendor': r['Vendor'],
                    'model': r['Model'],
                    'power_ref_at_10c': r['P_ref'],
                    'A_Coeff': r['A_Coeff'],
                    'B_Coeff': r['B_Coeff'],
                    'C_Coeff': r['C_Coeff'],
                    'R_squared': r['R_squared'],
                    'temperature_range': f"{r.get('T_min', 'N/A')}-{r.get('T_max', 'N/A')}",
                    'notes': r['notes'],
                    'success': r['success']
                }
                for r in results
            ]
        }

        with open(json_path, 'w') as f:
            json.dump(export_data, f, indent=2)

        self.stdout.write(f'\n📄 Results exported to: {json_path}')
