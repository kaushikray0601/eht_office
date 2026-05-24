# Generated for MI autonomous fallback refactor on 2026-05-24.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('eht', '0024_projectdata_heating_cable_type'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='projectdata',
            name='heating_cable_type',
        ),
    ]
