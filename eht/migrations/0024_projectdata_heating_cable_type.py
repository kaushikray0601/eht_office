# Generated for MI cable guarded orchestration Pass 4 on 2026-05-24.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('eht', '0023_selectedmiheater_diagnostics'),
    ]

    operations = [
        migrations.AddField(
            model_name='projectdata',
            name='heating_cable_type',
            field=models.CharField(
                choices=[('SR', 'Self-regulating'), ('MI', 'Mineral insulated')],
                default='SR',
                max_length=10,
            ),
        ),
    ]
