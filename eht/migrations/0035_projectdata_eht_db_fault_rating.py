from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('eht', '0034_rcd_cu_only_cold_cable'),
    ]

    operations = [
        migrations.AddField(
            model_name='projectdata',
            name='eht_db_fault_rating_ka',
            field=models.DecimalField(decimal_places=2, default=15, max_digits=6),
        ),
    ]
