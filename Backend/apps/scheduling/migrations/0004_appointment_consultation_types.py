from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("scheduling", "0003_alter_appointment_appointment_type"),
    ]

    operations = [
        migrations.AlterField(
            model_name="appointment",
            name="appointment_type",
            field=models.CharField(
                choices=[
                    ("consultation", "Consultation"),
                    ("hepatology_consultation", "Hepatology Consultation"),
                    ("transplant_consultation", "Transplant Consultation"),
                    ("examination", "Examination"),
                    ("ct_scan", "CT scan"),
                    ("lab_visit", "Lab visit"),
                    ("donor_evaluation", "Donor evaluation"),
                    ("recipient_evaluation", "Recipient evaluation"),
                    ("follow_up", "Post-transplant follow-up"),
                ],
                max_length=25,
            ),
        ),
    ]
