"""
Seed one 'lab' service per test of the lab catalog (apps/labs seed_lab_tests), matched to the
test by LOINC code (coding_system='loinc', standard_code=LabTest.code). Used by automatic
invoicing of resulted lab orders (apps.billing.services.invoice_for_lab_order).
"""
from decimal import Decimal

from django.db import migrations

# (service code, name, LOINC code, price EGP)
LAB_SERVICES = [
    ('LAB-001', 'ALT (SGPT)', '1742-6', 150),
    ('LAB-002', 'AST (SGOT)', '1920-8', 150),
    ('LAB-003', 'Total Bilirubin', '1975-2', 120),
    ('LAB-004', 'Albumin', '1751-7', 120),
    ('LAB-005', 'INR', '6301-6', 200),
    ('LAB-006', 'Creatinine', '2160-0', 120),
    ('LAB-007', 'Sodium', '2951-2', 100),
    ('LAB-008', 'AFP (Alpha-fetoprotein)', '1834-1', 400),
    ('LAB-009', 'HBsAg (HBV surface antigen)', '5195-3', 300),
    ('LAB-010', 'HCV Antibody', '13955-0', 300),
]


def seed(apps, schema_editor):
    Service = apps.get_model('billing', 'Service')
    for code, name, loinc, price in LAB_SERVICES:
        Service.objects.update_or_create(code=code, defaults={
            'name': name, 'category': 'lab', 'coding_system': 'loinc', 'standard_code': loinc,
            'price': Decimal(price), 'is_active': True,
        })


def unseed(apps, schema_editor):
    Service = apps.get_model('billing', 'Service')
    seeded = Service.objects.filter(code__in=[s[0] for s in LAB_SERVICES])
    seeded.filter(invoice_items__isnull=False).update(is_active=False)
    seeded.filter(invoice_items__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0006_invoiceitem_lab_order_lab_categories'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
