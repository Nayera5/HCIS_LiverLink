from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0008_alter_auditlog_changes_alter_auditlog_reason'),
    ]

    operations = [
        migrations.AddField(
            model_name='auditlog',
            name='outcome',
            field=models.CharField(
                blank=True,
                choices=[('success', 'Success'), ('failure', 'Failure')],
                max_length=10,
                null=True,
            ),
        ),
        migrations.AddConstraint(
            model_name='auditlog',
            constraint=models.CheckConstraint(
                condition=Q(outcome__isnull=True) | Q(outcome__in=['success', 'failure']),
                name='accounts_auditlog_outcome_valid',
            ),
        ),
    ]
