from django.db import migrations, models


def ensure_extra_columns(apps, schema_editor):
    AuditLog = apps.get_model('accounts', 'AuditLog')
    columns = {
        column.name
        for column in schema_editor.connection.introspection.get_table_description(
            schema_editor.connection.cursor(), AuditLog._meta.db_table
        )
    }

    with schema_editor.connection.cursor() as cursor:
        if 'reason' not in columns:
            cursor.execute(
                'ALTER TABLE "%s" ADD COLUMN "reason" text DEFAULT \'\' NOT NULL'
                % AuditLog._meta.db_table
            )
        if 'changes' not in columns:
            cursor.execute(
                'ALTER TABLE "%s" ADD COLUMN "changes" jsonb'
                % AuditLog._meta.db_table
                if schema_editor.connection.vendor == 'postgresql'
                else 'ALTER TABLE "%s" ADD COLUMN "changes" text'
                % AuditLog._meta.db_table
            )


def remove_extra_columns(apps, schema_editor):
    AuditLog = apps.get_model('accounts', 'AuditLog')
    with schema_editor.connection.cursor() as cursor:
        cursor.execute('ALTER TABLE "%s" DROP COLUMN IF EXISTS "changes"' % AuditLog._meta.db_table)
        cursor.execute('ALTER TABLE "%s" DROP COLUMN IF EXISTS "reason"' % AuditLog._meta.db_table)


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0006_auditlog_donor_actions'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(ensure_extra_columns, remove_extra_columns),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='auditlog',
                    name='reason',
                    field=models.TextField(blank=True, default='', help_text='Optional reason or explanation for the action.'),
                ),
                migrations.AddField(
                    model_name='auditlog',
                    name='changes',
                    field=models.JSONField(blank=True, null=True, help_text='Optional structured details about the action.'),
                ),
            ],
        ),
    ]
