"""
Service catalog limited to what the system can bill: appointments, imaging orders, transplant
evaluation and surgery. The services of migration 0004 that no module can trigger are removed.
"""
from decimal import Decimal

from django.db import migrations

# (code, name, category, coding_system, standard_code, price EGP)
SERVICES = [
    # Consultation: one per bookable appointment type
    ('CONS-001', 'Hepatology Consultation', 'consultation', 'cpt', '99204', 1000),
    ('CONS-002', 'Post-Transplant Follow-up', 'consultation', 'cpt', '99214', 800),
    ('CONS-003', 'Transplant Surgery Consultation', 'consultation', 'cpt', '99204', 1200),
    ('EVA-001', 'Recipient Evaluation Visit', 'consultation', 'cpt', '99204', 1500),
    ('EVA-002', 'Donor Evaluation Visit', 'consultation', 'cpt', '99204', 1000),
    ('EXM-001', 'Clinical Examination', 'consultation', 'cpt', '99213', 600),
    # Imaging: one per ImagingOrder protocol (report and AI analysis included)
    ('IMG-003', 'Multiphase Liver CT', 'imaging', 'cpt', '74170', 3000),
    ('IMG-006', 'Donor Volumetry CT', 'imaging', 'cpt', '74175', 4000),
    ('IMG-007', 'Follow-up CT', 'imaging', 'cpt', '74160', 2500),
    # Evaluation packages (bundles: no single standard code)
    ('PKG-001', 'Recipient Evaluation Package', 'evaluation_package', '', '', 15000),
    ('PKG-002', 'Living Donor Evaluation Package', 'evaluation_package', '', '', 12000),
    # Surgery: the recipient's operation, and the donor's operation by graft type
    ('SUR-001', 'Liver Transplant Surgery', 'surgery', 'cpt', '47135', 500000),
    ('SUR-005', 'Donor Hepatectomy - Right Lobe', 'surgery', 'cpt', '47142', 150000),
    ('SUR-006', 'Donor Hepatectomy - Left Lobe', 'surgery', 'cpt', '47141', 140000),
    ('SUR-007', 'Donor Hepatectomy - Left Lateral Segment', 'surgery', 'cpt', '47140', 120000),
]

RETIRED_CODES = [
    'CONS-004', 'CONS-005',
    'IMG-001', 'IMG-002', 'IMG-004', 'IMG-005',
    'PKG-003', 'PKG-004', 'PKG-005',
    'SUR-002', 'SUR-003', 'SUR-004',
    *[f'{prefix}-{number:03d}' for prefix in ('PROC', 'INP', 'PREV') for number in range(1, 6)],
]


def seed_services(apps, schema_editor):
    Service = apps.get_model('billing', 'Service')
    for code, name, category, coding_system, standard_code, price in SERVICES:
        service = Service.objects.filter(code=code).first()
        if service is not None and service.name == name:
            continue  # already there: keep the admin's price and other changes
        # New, or a code that migration 0004 used for another service.
        Service.objects.update_or_create(code=code, defaults={
            'name': name, 'category': category, 'coding_system': coding_system,
            'standard_code': standard_code, 'price': Decimal(price), 'is_active': True,
        })


def retire_services(apps, schema_editor):
    # Services already billed on an invoice are PROTECTed; deactivate those instead of deleting.
    retired = apps.get_model('billing', 'Service').objects.filter(code__in=RETIRED_CODES)
    retired.filter(invoice_items__isnull=False).update(is_active=False)
    retired.filter(invoice_items__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0010_remove_lab_and_ai_service_categories'),
    ]

    operations = [
        migrations.RunPython(seed_services, migrations.RunPython.noop),
        migrations.RunPython(retire_services, migrations.RunPython.noop),
    ]
