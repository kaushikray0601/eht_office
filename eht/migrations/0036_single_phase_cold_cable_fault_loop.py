from django.db import migrations, models


def delete_stale_cold_cable_results(apps, schema_editor):
    ColdCableResult = apps.get_model('eht', 'ColdCableResult')
    ColdCableResult.objects.all().delete()


def seed_pe_conductor_size(apps, schema_editor):
    ColdCableCatalogue = apps.get_model('eht', 'ColdCableCatalogue')
    for row in ColdCableCatalogue.objects.filter(pe_conductor_size_mm2__isnull=True):
        row.pe_conductor_size_mm2 = row.conductor_size_mm2
        row.save(update_fields=['pe_conductor_size_mm2'])


class Migration(migrations.Migration):

    dependencies = [
        ('eht', '0035_projectdata_eht_db_fault_rating'),
    ]

    operations = [
        migrations.RunPython(delete_stale_cold_cable_results, migrations.RunPython.noop),
        migrations.AddField(
            model_name='coldcablecatalogue',
            name='pe_conductor_size_mm2',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.RunPython(seed_pe_conductor_size, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='coldcableresult',
            name='fault_current_4c_phase_to_phase_a',
        ),
        migrations.RemoveField(
            model_name='coldcableresult',
            name='fault_protection_4c_status',
        ),
        migrations.AddField(
            model_name='coldcableresult',
            name='fault_current_l_pe_a',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='coldcableresult',
            name='fault_loop_basis',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='coldcableresult',
            name='fault_loop_status',
            field=models.CharField(
                choices=[
                    ('pass', 'Pass'),
                    ('fail', 'Fail'),
                    ('review_required', 'Review Required'),
                    ('not_calculated', 'Not Calculated'),
                ],
                default='not_calculated',
                max_length=20,
            ),
        ),
    ]
