"""Register the external lab (the LabSimulator project) so orders have somewhere to go."""
from django.db import migrations


def seed(apps, schema_editor):
    ExternalSystem = apps.get_model('hl7', 'ExternalSystem')
    ExternalSystem.objects.get_or_create(name='EXTERNAL_LAB', defaults={
        'system_type': 'external_lab', 'host': '127.0.0.1', 'port': 2576, 'is_active': True})


class Migration(migrations.Migration):

    dependencies = [('hl7', '0001_initial')]

    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
