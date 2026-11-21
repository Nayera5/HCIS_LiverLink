"""
Turn the adopted `auth_user` table into the LiverLink User.

Additive only: adds the `role` column and four constraints. No column, table or existing
constraint is removed or altered. The three foreign keys that point at auth_user
(auth_user_groups, auth_user_user_permissions, django_admin_log) are not touched.

Existing rows:
- Empty table: nothing to convert.
- Every existing row is a Django superuser (is_superuser AND is_staff): each keeps all of its
  data (username, password, email, names, flags, dates) and receives role='admin'.
- Any other existing row: the migration stops before changing anything, so no account is
  ever given a guessed role.
The whole migration runs in one transaction, so any failure leaves the table unchanged.
"""

from django.db import migrations, models
from django.db.models import Q
from django.db.models.functions import Lower

import apps.accounts.models


def refuse_unless_only_superusers(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    users = User.objects.using(schema_editor.connection.alias)
    others = users.exclude(is_superuser=True, is_staff=True).count()
    if others:
        raise RuntimeError(
            f'accounts.0002: auth_user has {others} existing account(s) that are not Django '
            'superusers (is_superuser and is_staff). Stop and agree on their roles before migrating.'
        )


def assign_admin_role_to_existing_superusers(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    users = User.objects.using(schema_editor.connection.alias)
    users.filter(is_superuser=True, is_staff=True).update(role='admin')
    # Defensive re-check: after the guard, nothing else may exist.
    if users.exclude(role='admin').exists():
        raise RuntimeError('accounts.0002: unexpected non-admin row after role assignment.')


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(refuse_unless_only_superusers, migrations.RunPython.noop),
        # The one-off default only fills rows that already exist; the guard above guarantees
        # those are superusers, for whom 'admin' is the correct role. It is dropped right after.
        migrations.AddField(
            model_name='user',
            name='role',
            field=models.CharField(
                choices=[('admin', 'Admin'), ('clinical_staff', 'Clinical staff'), ('patient', 'Patient')],
                default='admin',
                max_length=20,
            ),
            preserve_default=False,
        ),
        migrations.RunPython(assign_admin_role_to_existing_superusers, migrations.RunPython.noop),
        migrations.AlterModelManagers(
            name='user',
            managers=[('objects', apps.accounts.models.UserManager())],
        ),
        migrations.AddConstraint(
            model_name='user',
            constraint=models.CheckConstraint(
                condition=Q(role__in=['admin', 'clinical_staff', 'patient']),
                name='accounts_user_role_valid',
            ),
        ),
        migrations.AddConstraint(
            model_name='user',
            constraint=models.UniqueConstraint(
                Lower('username'),
                name='accounts_user_username_ci_unique',
                violation_error_message='A user with that username already exists.',
            ),
        ),
        migrations.AddConstraint(
            model_name='user',
            constraint=models.UniqueConstraint(
                Lower('email'),
                condition=~Q(email=''),
                name='accounts_user_email_ci_unique',
                violation_error_message='A user with that email address already exists.',
            ),
        ),
        migrations.AddConstraint(
            model_name='user',
            constraint=models.CheckConstraint(
                condition=~Q(role='patient') | Q(is_staff=False, is_superuser=False),
                name='accounts_user_patient_no_admin_access',
                violation_error_message='Patient accounts cannot have Django admin access.',
            ),
        ),
    ]
