from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('eht', '0013_update_sld_topology_edit_types'),
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
                    ('attach_to_jb', 'Attach Feeder to 3PH JB'),
                    ('move_branch_to_jb', 'Move Branch to 3PH JB'),
                ],
                max_length=30,
            ),
        ),
    ]
