from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('eht', '0014_update_sld_topology_edit_types'),
    ]

    operations = [
        migrations.AlterField(
            model_name='projectdata',
            name='max_cb_size',
            field=models.IntegerField(
                choices=[
                    (2, 2),
                    (4, 4),
                    (6, 6),
                    (10, 10),
                    (16, 16),
                    (20, 20),
                    (25, 25),
                    (32, 32),
                    (40, 40),
                ],
                default=10,
            ),
        ),
    ]
