# Generated for MI cable persistence Pass 3 on 2026-05-24.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('eht', '0022_mi_catalogue_foundation'),
    ]

    operations = [
        migrations.AddField(
            model_name='selectedmiheater',
            name='selection_rejection_reasons',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='selectedmiheater',
            name='selection_status',
            field=models.CharField(blank=True, default='', max_length=30),
        ),
    ]
