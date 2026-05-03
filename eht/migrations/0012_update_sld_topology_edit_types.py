from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('eht', '0011_cablescheduleoverride'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sldtopologyedit',
            name='edit_type',
            field=models.CharField(
                choices=[
                    ('combine_feeders', 'Combine Feeders'),
                    ('split_circuits', 'Split Circuits'),
                    ('downstream_jb', 'Downstream 3PH JB'),
                ],
                max_length=30,
            ),
        ),
    ]
