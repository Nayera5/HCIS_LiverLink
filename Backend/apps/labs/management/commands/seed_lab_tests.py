"""python manage.py seed_lab_tests : create/update the liver and transplant test catalog (idempotent)."""
from decimal import Decimal as D

from django.core.management.base import BaseCommand

from apps.labs.models import LabTest

# code (LOINC), name, unit, normal_min, normal_max, critical_min, critical_max
CATALOG = [
    ('1742-6', 'ALT (SGPT)', 'U/L', 7, 56, None, 1000),
    ('1920-8', 'AST (SGOT)', 'U/L', 10, 40, None, 1000),
    ('1975-2', 'Total bilirubin', 'mg/dL', D('0.1'), D('1.2'), None, 12),
    ('1751-7', 'Albumin', 'g/dL', D('3.5'), D('5.0'), D('1.5'), None),
    ('6301-6', 'INR', '', D('0.8'), D('1.1'), None, D('5.0')),
    ('2160-0', 'Creatinine', 'mg/dL', D('0.6'), D('1.3'), None, D('7.0')),
    ('2951-2', 'Sodium', 'mmol/L', 135, 145, 120, 160),
    ('1834-1', 'AFP (Alpha-fetoprotein)', 'ng/mL', 0, 10, None, None),
    ('5195-3', 'HBsAg (HBV surface antigen)', 'index', 0, D('0.9'), None, None),
    ('13955-0', 'HCV antibody', 'index', 0, D('0.9'), None, None),
    # ABO blood group is not numeric: it stays on the Patient record (Patient.blood_group).
]


class Command(BaseCommand):
    help = 'Seed the lab test catalog.'

    def handle(self, *args, **opts):
        for code, name, unit, nmin, nmax, cmin, cmax in CATALOG:
            LabTest.objects.update_or_create(code=code, defaults=dict(
                name=name, unit=unit, normal_min=nmin, normal_max=nmax, critical_min=cmin, critical_max=cmax))
        self.stdout.write(self.style.SUCCESS(f'{len(CATALOG)} lab tests ready.'))
