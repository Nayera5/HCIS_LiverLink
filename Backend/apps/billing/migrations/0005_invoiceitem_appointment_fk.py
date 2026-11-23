"""
InvoiceItem.appointment_id: plain integer -> real foreign key to scheduling.Appointment.

Done in steps so existing links survive: add a temporary FK, copy every id that matches a real
appointment (ids that don't are dropped, the FK could not hold them), drop the old integer
column, then rename the FK so its column is `appointment_id` again (spec §4.40).
"""
import django.db.models.deletion
from django.db import migrations, models


def copy_valid_links(apps, schema_editor):
    InvoiceItem = apps.get_model('billing', 'InvoiceItem')
    Appointment = apps.get_model('scheduling', 'Appointment')
    linked = InvoiceItem.objects.filter(appointment_id__isnull=False)
    valid = set(Appointment.objects.filter(
        pk__in=linked.values_list('appointment_id', flat=True)).values_list('pk', flat=True))
    for item in linked:
        if item.appointment_id in valid:
            item.appointment_link_id = item.appointment_id
            item.save(update_fields=['appointment_link'])


def copy_back(apps, schema_editor):
    InvoiceItem = apps.get_model('billing', 'InvoiceItem')
    for item in InvoiceItem.objects.filter(appointment_link__isnull=False):
        item.appointment_id = item.appointment_link_id
        item.save(update_fields=['appointment_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0004_seed_services'),
        ('scheduling', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoiceitem',
            name='appointment_link',
            field=models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.PROTECT,
                                    related_name='+', to='scheduling.appointment'),
        ),
        migrations.RunPython(copy_valid_links, copy_back),
        migrations.RemoveField(model_name='invoiceitem', name='appointment_id'),
        migrations.RenameField(model_name='invoiceitem', old_name='appointment_link', new_name='appointment'),
        migrations.AlterField(
            model_name='invoiceitem',
            name='appointment',
            field=models.ForeignKey(blank=True, help_text='Visit the charge came from, if any.', null=True,
                                    on_delete=django.db.models.deletion.PROTECT, related_name='invoice_items',
                                    to='scheduling.appointment'),
        ),
    ]
