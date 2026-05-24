# Generated for MI cable data-foundation Pass 1 on 2026-05-24.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('eht', '0021_heatloss_selection_rejection_reasons_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='heattracinginput',
            name='phase',
            field=models.CharField(
                blank=True,
                choices=[('1PH', 'Single Phase')],
                default='1PH',
                max_length=10,
            ),
        ),
        migrations.RenameField(
            model_name='micableheater',
            old_name='base_resistance_ohms_km',
            new_name='resistance_ohms_m',
        ),
        migrations.RenameField(
            model_name='micableheater',
            old_name='max_ampacity',
            new_name='max_current_a',
        ),
        migrations.AddField(
            model_name='micablefamily',
            name='gas_group',
            field=models.CharField(
                blank=True,
                choices=[('', 'Not specified'), ('IIA', 'IIA'), ('IIB', 'IIB'), ('IIC', 'IIC')],
                default='',
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name='micablefamily',
            name='is_validated',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='micablefamily',
            name='max_circuit_length_m',
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name='micablefamily',
            name='max_exposure_temp_c',
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name='micablefamily',
            name='min_circuit_length_m',
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name='micablefamily',
            name='source_document',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
        migrations.AddField(
            model_name='micablefamily',
            name='temp_class_rating',
            field=models.CharField(
                blank=True,
                choices=[
                    ('', 'Not specified'),
                    ('T1', 'T1'),
                    ('T2', 'T2'),
                    ('T3', 'T3'),
                    ('T4', 'T4'),
                    ('T5', 'T5'),
                    ('T6', 'T6'),
                ],
                default='',
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name='micablefamily',
            name='zone_approval',
            field=models.CharField(blank=True, default='', max_length=60),
        ),
        migrations.AddField(
            model_name='micableheater',
            name='cold_lead_max_ampacity_a',
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name='micableheater',
            name='cold_lead_resistance_ohms_m',
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name='micableheater',
            name='conductor_material',
            field=models.CharField(blank=True, default='', max_length=50),
        ),
        migrations.AddField(
            model_name='micableheater',
            name='sheath_material',
            field=models.CharField(blank=True, default='', max_length=50),
        ),
        migrations.AlterModelOptions(
            name='micableheater',
            options={'ordering': ['resistance_ohms_m']},
        ),
        migrations.CreateModel(
            name='MIColdLeadOption',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('option_code', models.CharField(max_length=20)),
                ('length_m', models.FloatField()),
                ('heater', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cold_lead_options', to='eht.micableheater')),
            ],
            options={
                'ordering': ['heater', 'length_m', 'option_code'],
                'constraints': [models.UniqueConstraint(fields=('heater', 'option_code'), name='unique_mi_cold_lead_option_per_heater')],
            },
        ),
        migrations.CreateModel(
            name='SelectedMIHeater',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('heated_length_m', models.FloatField(default=0.0)),
                ('cold_lead_option_code', models.CharField(blank=True, default='', max_length=20)),
                ('cold_lead_length_m', models.FloatField(default=0.0)),
                ('heater_resistance_ohms', models.FloatField(default=0.0)),
                ('cold_lead_resistance_total_ohms', models.FloatField(default=0.0)),
                ('power_nominal_w', models.FloatField(default=0.0)),
                ('power_density_w_m', models.FloatField(default=0.0)),
                ('current_nominal_a', models.FloatField(default=0.0)),
                ('current_cold_start_a', models.FloatField(default=0.0)),
                ('max_sheath_temp_published_c', models.FloatField(blank=True, null=True)),
                ('project_t_class_limit_c', models.FloatField(default=0.0)),
                ('t_class_verdict', models.CharField(choices=[('pass', 'Pass'), ('fail', 'Fail'), ('review', 'Review Required')], default='review', max_length=20)),
                ('selection_basis', models.JSONField(blank=True, default=dict)),
                ('cold_lead_option', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='eht.micoldleadoption')),
                ('heater', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='eht.micableheater')),
                ('line', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='selected_mi_heater_result', to='eht.heattracinginput')),
            ],
            options={
                'ordering': ['line'],
            },
        ),
    ]
