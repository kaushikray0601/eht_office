from django.db import migrations, models


def remove_aluminium_cold_cable_rows(apps, schema_editor):
    ProjectData = apps.get_model('eht', 'ProjectData')
    ColdCableCatalogue = apps.get_model('eht', 'ColdCableCatalogue')

    ProjectData.objects.filter(cable_conductor_material='Al').update(cable_conductor_material='Cu')
    ColdCableCatalogue.objects.filter(conductor_material='Al').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('eht', '0033_coldcableresult_cable_3c_segments'),
    ]

    operations = [
        migrations.RenameField(
            model_name='projectdata',
            old_name='gfep_provided',
            new_name='rcd_provided',
        ),
        migrations.RenameField(
            model_name='coldcableresult',
            old_name='gfep_provided',
            new_name='rcd_provided',
        ),
        migrations.AlterField(
            model_name='projectdata',
            name='cable_conductor_material',
            field=models.CharField(choices=[('Cu', 'Copper')], default='Cu', max_length=5),
        ),
        migrations.AlterField(
            model_name='coldcablecatalogue',
            name='conductor_material',
            field=models.CharField(choices=[('Cu', 'Copper')], max_length=5),
        ),
        migrations.RunPython(remove_aluminium_cold_cable_rows, migrations.RunPython.noop),
    ]
