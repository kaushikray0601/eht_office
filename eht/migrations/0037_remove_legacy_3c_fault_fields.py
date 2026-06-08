from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('eht', '0036_single_phase_cold_cable_fault_loop'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        'ALTER TABLE eht_coldcableresult '
                        'DROP COLUMN IF EXISTS fault_current_3c_line_to_neutral_a;'
                    ),
                    reverse_sql=migrations.RunSQL.noop,
                ),
                migrations.RunSQL(
                    sql=(
                        'ALTER TABLE eht_coldcableresult '
                        'DROP COLUMN IF EXISTS fault_protection_3c_status;'
                    ),
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
            state_operations=[
                migrations.RemoveField(
                    model_name='coldcableresult',
                    name='fault_current_3c_line_to_neutral_a',
                ),
                migrations.RemoveField(
                    model_name='coldcableresult',
                    name='fault_protection_3c_status',
                ),
            ],
        ),
    ]
