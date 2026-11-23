"""python manage.py seed_drugs : create/update common hepatology & transplant drugs (idempotent, by name)."""
from django.core.management.base import BaseCommand

from apps.prescriptions.models import Drug

# name, generic name, class, default route, common dose
CATALOG = [
    # Hepatitis B / C antivirals
    ('Tenofovir disoproxil fumarate', 'tenofovir disoproxil', 'Antiviral (HBV)', 'oral', '300 mg once daily'),
    ('Tenofovir alafenamide', 'tenofovir alafenamide', 'Antiviral (HBV)', 'oral', '25 mg once daily'),
    ('Entecavir', 'entecavir', 'Antiviral (HBV)', 'oral', '0.5 mg once daily'),
    ('Sofosbuvir/Velpatasvir', 'sofosbuvir + velpatasvir', 'Antiviral (HCV)', 'oral', '400/100 mg once daily'),
    ('Sofosbuvir/Daclatasvir', 'sofosbuvir + daclatasvir', 'Antiviral (HCV)', 'oral', '400/60 mg once daily'),
    ('Glecaprevir/Pibrentasvir', 'glecaprevir + pibrentasvir', 'Antiviral (HCV)', 'oral', '300/120 mg once daily'),
    ('Ribavirin', 'ribavirin', 'Antiviral (HCV)', 'oral', 'weight-based, twice daily'),
    # Hepatocellular carcinoma systemic therapy
    ('Sorafenib', 'sorafenib', 'Kinase inhibitor (HCC)', 'oral', '400 mg twice daily'),
    ('Lenvatinib', 'lenvatinib', 'Kinase inhibitor (HCC)', 'oral', '8-12 mg once daily'),
    ('Atezolizumab', 'atezolizumab', 'Immunotherapy (HCC)', 'iv', '1200 mg every 3 weeks'),
    ('Bevacizumab', 'bevacizumab', 'Anti-VEGF (HCC)', 'iv', '15 mg/kg every 3 weeks'),
    # Cirrhosis complications
    ('Propranolol', 'propranolol', 'Non-selective beta blocker', 'oral', '20-40 mg twice daily'),
    ('Carvedilol', 'carvedilol', 'Non-selective beta blocker', 'oral', '6.25 mg once daily'),
    ('Spironolactone', 'spironolactone', 'Diuretic', 'oral', '100 mg once daily'),
    ('Furosemide', 'furosemide', 'Diuretic', 'oral', '40 mg once daily'),
    ('Lactulose', 'lactulose', 'Hepatic encephalopathy', 'oral', '20-30 g two to three times daily'),
    ('Rifaximin', 'rifaximin', 'Hepatic encephalopathy', 'oral', '550 mg twice daily'),
    ('Ursodeoxycholic acid', 'ursodiol', 'Bile acid', 'oral', '13-15 mg/kg/day'),
    ('Terlipressin', 'terlipressin', 'Vasopressin analogue', 'iv', '1 mg every 4-6 hours'),
    ('Albumin 20%', 'human albumin', 'Plasma expander', 'iv', '1 g/kg'),
    ('Vitamin K (phytomenadione)', 'phytomenadione', 'Vitamin', 'iv', '10 mg once daily'),
    ('Ceftriaxone', 'ceftriaxone', 'Antibiotic', 'iv', '1 g once daily'),
    ('Norfloxacin', 'norfloxacin', 'Antibiotic (SBP prophylaxis)', 'oral', '400 mg once daily'),
    # Transplant immunosuppression & prophylaxis
    ('Tacrolimus', 'tacrolimus', 'Immunosuppressant (calcineurin inhibitor)', 'oral', '0.05 mg/kg twice daily'),
    ('Cyclosporine', 'ciclosporin', 'Immunosuppressant (calcineurin inhibitor)', 'oral', 'per trough level'),
    ('Mycophenolate mofetil', 'mycophenolate mofetil', 'Immunosuppressant (antimetabolite)', 'oral',
     '1 g twice daily'),
    ('Everolimus', 'everolimus', 'Immunosuppressant (mTOR inhibitor)', 'oral', '1 mg twice daily'),
    ('Prednisolone', 'prednisolone', 'Corticosteroid', 'oral', '20 mg once daily, tapered'),
    ('Methylprednisolone', 'methylprednisolone', 'Corticosteroid', 'iv', '500 mg once (induction)'),
    ('Basiliximab', 'basiliximab', 'Immunosuppressant (induction)', 'iv', '20 mg on day 0 and day 4'),
    ('Valganciclovir', 'valganciclovir', 'Antiviral (CMV prophylaxis)', 'oral', '900 mg once daily'),
    ('Trimethoprim/Sulfamethoxazole', 'co-trimoxazole', 'Antibiotic (PCP prophylaxis)', 'oral',
     '480 mg once daily'),
    ('Omeprazole', 'omeprazole', 'Proton pump inhibitor', 'oral', '20 mg once daily'),
    ('Enoxaparin', 'enoxaparin', 'Anticoagulant', 'sc', '40 mg once daily'),
]


class Command(BaseCommand):
    help = 'Seed the drug catalog with common hepatology and transplant medications.'

    def handle(self, *args, **opts):
        created = 0
        for name, generic, klass, route, dose in CATALOG:
            drug = Drug.objects.filter(name__iexact=name).first() or Drug(name=name)
            created += drug.pk is None
            drug.generic_name, drug.drug_class, drug.default_route, drug.common_dose = generic, klass, route, dose
            drug.save()
        self.stdout.write(self.style.SUCCESS(f'{len(CATALOG)} drugs ready ({created} new).'))
