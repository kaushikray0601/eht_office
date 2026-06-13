from django.db import migrations


LEGACY_FIELD_NAMES = (
    'fault_current_3c_line_to_neutral_a',
    'fault_protection_3c_status',
)


def drop_legacy_3c_fault_columns(apps, schema_editor):
    ColdCableResult = apps.get_model('eht', 'ColdCableResult')
    table_name = ColdCableResult._meta.db_table

    with schema_editor.connection.cursor() as cursor:
        existing_columns = {
            column.name
            for column in schema_editor.connection.introspection.get_table_description(cursor, table_name)
        }

    for field_name in LEGACY_FIELD_NAMES:
        field = ColdCableResult._meta.get_field(field_name)
        if field.column in existing_columns:
            schema_editor.remove_field(ColdCableResult, field)
            existing_columns.remove(field.column)


class Migration(migrations.Migration):

    dependencies = [
        ('eht', '0036_single_phase_cold_cable_fault_loop'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(drop_legacy_3c_fault_columns, migrations.RunPython.noop),
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
