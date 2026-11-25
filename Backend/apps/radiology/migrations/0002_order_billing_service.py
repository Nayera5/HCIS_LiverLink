"""
The Billing catalog becomes the only list of examinations: `modality` and `body_area` are dropped, and orders
and slots must point to an imaging service. Refuses to run if rows exist that would lose information.
"""
import django.db.models.deletion
from django.db import migrations, models


def refuse_if_data_would_be_lost(apps, schema_editor):
    for name in ('ImagingOrder', 'ImagingSlot'):
        if apps.get_model('radiology', name).objects.using(schema_editor.connection.alias).exists():
            raise RuntimeError(f'{name} rows exist: map them to a billing service before this migration.')


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0009_invoiceitem_imaging_order'),
        ('radiology', '0001_imaging_orders'),
    ]

    operations = [
        migrations.RunPython(refuse_if_data_would_be_lost, migrations.RunPython.noop),
        migrations.RemoveConstraint(model_name='imagingorder', name='radiology_order_modality_valid'),
        migrations.RemoveConstraint(model_name='imagingorder', name='radiology_order_body_area_valid'),
        migrations.RemoveConstraint(model_name='imagingslot', name='radiology_slot_modality_valid'),
        migrations.RemoveConstraint(model_name='imagingslot', name='radiology_slot_resource_start_uniq'),
        migrations.AlterModelOptions(name='imagingslot', options={'ordering': ['start_time', 'resource_name']}),
        migrations.RemoveField(model_name='imagingorder', name='modality'),
        migrations.RemoveField(model_name='imagingorder', name='body_area'),
        migrations.RemoveField(model_name='imagingslot', name='modality'),
        migrations.AlterField(
            model_name='imagingorder',
            name='billing_service',
            field=models.ForeignKey(help_text='Examination ordered: an imaging service of the Billing catalog.', on_delete=django.db.models.deletion.PROTECT, related_name='imaging_orders', to='billing.service'),
        ),
        migrations.AddField(
            model_name='imagingslot',
            name='billing_service',
            field=models.ForeignKey(help_text='Imaging service of the Billing catalog that can be booked in this slot.', on_delete=django.db.models.deletion.PROTECT, related_name='imaging_slots', to='billing.service'),
        ),
        migrations.AddConstraint(
            model_name='imagingslot',
            constraint=models.UniqueConstraint(fields=('billing_service', 'resource_name', 'start_time'), name='radiology_slot_service_start_uniq'),
        ),
    ]
