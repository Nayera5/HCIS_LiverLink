"""
Seed the liver-transplant service catalog.

standard_code holds the primary code only; add-on codes (e.g. 90471 vaccine administration,
99292 extra critical-care time, 76937 ultrasound guidance) are billed separately.
Items with no single applicable code (bundled packages, room/bed-day charges, care inside the
47135 global surgical period) are left uncoded on purpose.
"""
from decimal import Decimal

from django.db import migrations

# (code, name, category, coding_system, standard_code, price EGP)
SERVICES = [
    # Consultation
    ('CONS-001', 'Hepatology Consultation', 'consultation', 'cpt', '99204', 1000),
    ('CONS-002', 'Liver Transplant Specialist Consultation', 'consultation', 'cpt', '99204', 1500),
    ('CONS-003', 'Post-Transplant Follow-up', 'consultation', 'cpt', '99214', 800),
    ('CONS-004', 'Transplant Surgery Consultation', 'consultation', 'cpt', '99204', 1200),
    ('CONS-005', 'Donor Evaluation Consultation', 'consultation', 'cpt', '99204', 1000),
    # Imaging
    ('IMG-001', 'Abdominal Ultrasound', 'imaging', 'cpt', '76700', 1000),
    ('IMG-002', 'Liver Doppler Ultrasound', 'imaging', 'cpt', '93975', 1500),
    ('IMG-003', 'Abdominal CT Scan with Contrast', 'imaging', 'cpt', '74160', 3000),
    ('IMG-004', 'Liver MRI with Contrast', 'imaging', 'cpt', '74183', 5000),
    ('IMG-005', 'MRCP', 'imaging', 'cpt', '74181', 5500),
    # Evaluation packages (bundles: no single standard code)
    ('PKG-001', 'Pre-Transplant Evaluation Package', 'evaluation_package', '', '', 15000),
    ('PKG-002', 'Living Liver Donor Evaluation', 'evaluation_package', '', '', 12000),
    ('PKG-003', 'Post-Transplant Follow-up Package', 'evaluation_package', '', '', 8000),
    ('PKG-004', 'Comprehensive Liver Assessment', 'evaluation_package', '', '', 10000),
    ('PKG-005', 'Transplant Readiness Assessment', 'evaluation_package', '', '', 7000),
    # Surgery
    ('SUR-001', 'Liver Transplant Surgery', 'surgery', 'cpt', '47135', 500000),
    ('SUR-002', 'Liver Transplant Revision', 'surgery', 'cpt', '47399', 150000),
    ('SUR-003', 'Liver Transplant Re-exploration', 'surgery', 'cpt', '49002', 120000),
    ('SUR-004', 'Surgical Treatment of Biliary Complications', 'surgery', 'cpt', '47780', 100000),
    # Medical procedures
    ('PROC-001', 'Liver Biopsy', 'medical_procedures', 'cpt', '47000', 5000),
    ('PROC-002', 'Upper GI Endoscopy', 'medical_procedures', 'cpt', '43235', 4000),
    ('PROC-003', 'Abdominal Paracentesis', 'medical_procedures', 'cpt', '49083', 3000),
    ('PROC-004', 'Ascitic Fluid Drainage', 'medical_procedures', 'cpt', '49406', 2500),
    ('PROC-005', 'Central Venous Catheter Insertion', 'medical_procedures', 'cpt', '36556', 3000),
    # Inpatient services (facility bed-day charges: not CPT-coded)
    ('INP-001', 'General Ward Admission (Per Day)', 'inpatient_services', '', '', 3000),
    ('INP-002', 'ICU Admission (Per Day)', 'inpatient_services', '', '', 10000),
    ('INP-003', 'Post-Transplant ICU Monitoring', 'inpatient_services', '', '', 12000),
    ('INP-004', 'Private Room Accommodation (Per Day)', 'inpatient_services', '', '', 5000),
    ('INP-005', 'Post-Operative Patient Monitoring', 'inpatient_services', '', '', 4000),
    # Preventive care
    ('PREV-001', 'Hepatitis B Vaccination', 'preventive_care', 'cpt', '90740', 800),
    ('PREV-002', 'Influenza Vaccination', 'preventive_care', 'cpt', '90656', 600),
    ('PREV-003', 'Post-Transplant Infection Prevention Consultation', 'preventive_care', 'cpt', '99401', 1000),
    ('PREV-004', 'Nutritional Counseling', 'preventive_care', 'cpt', '97802', 700),
    ('PREV-005', 'Liver Disease Prevention Counseling', 'preventive_care', 'cpt', '99401', 700),
]


def seed_services(apps, schema_editor):
    Service = apps.get_model('billing', 'Service')
    for code, name, category, coding_system, standard_code, price in SERVICES:
        Service.objects.update_or_create(
            code=code,
            defaults={
                'name': name,
                'category': category,
                'coding_system': coding_system,
                'standard_code': standard_code,
                'price': Decimal(price),
                'is_active': True,
            },
        )


def unseed_services(apps, schema_editor):
    # Services already billed on an invoice are PROTECTed; deactivate those instead of deleting.
    Service = apps.get_model('billing', 'Service')
    seeded = Service.objects.filter(code__in=[s[0] for s in SERVICES])
    seeded.filter(invoice_items__isnull=False).update(is_active=False)
    seeded.filter(invoice_items__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0003_remove_service_billing_service_category_valid_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_services, unseed_services),
    ]
