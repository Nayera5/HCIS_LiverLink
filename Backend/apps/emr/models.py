

"""Module 4 – Electronic Medical Records (EMR).

Entities: Encounter, MedicalHistory, Diagnosis, VitalSigns, Document
(entity dictionary sections 4.10 – 4.14).

Linked modules:
- module 1 (accounts): Staff (treating doctor, author, recorder) and User (uploader);
- module 2 (registry): Patient (owner of every record); Consent.document points here.

Deferred: Encounter.appointment_id (→ scheduling.Appointment, spec §4.10) is added with a
migration once the scheduling module has an Appointment model.
"""
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


# ---------------------------------------------------------------------------
# 4.10 Encounter
# ---------------------------------------------------------------------------
class Encounter(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        SIGNED = "signed", "Signed"

    # Fields frozen once an encounter is signed (changes go through an addendum).
    LOCKED_FIELDS = ("patient_id", "staff_id",
                     "encounter_date", "chief_complaint", "clinical_notes")

    encounter_id = models.AutoField(primary_key=True)
    patient = models.ForeignKey(
        "registry.Patient", on_delete=models.PROTECT,
        related_name="encounters", db_column="patient_id",
    )
    staff = models.ForeignKey(
        "accounts.Staff", on_delete=models.PROTECT,
        related_name="encounters", db_column="staff_id",
        help_text="Doctor who saw the patient.",
    )
    encounter_date = models.DateTimeField(default=timezone.now)
    chief_complaint = models.TextField(blank=True)
    clinical_notes = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)

    class Meta:
        db_table = "emr_encounter"
        ordering = ["-encounter_date"]
        indexes = [models.Index(fields=["patient", "-encounter_date"])]

    def __str__(self):
        return f"Encounter #{self.pk} – patient {self.patient_id} ({self.encounter_date:%Y-%m-%d})"

    def save(self, *args, **kwargs):
        # Business rule: once signed, the record can only change through an addendum.
        if self.pk:
            previous = Encounter.objects.filter(pk=self.pk).values(*self.LOCKED_FIELDS, "status").first()
            if previous and previous["status"] == self.Status.SIGNED:
                changed = [f for f in self.LOCKED_FIELDS if previous[f] != getattr(self, f)]
                if changed or self.status != self.Status.SIGNED:
                    raise ValidationError(
                        "Signed encounters cannot be modified; add an addendum instead."
                    )
        super().save(*args, **kwargs)


class EncounterAddendum(models.Model):
    """Correction or addition to a signed encounter (business rule of 4.10)."""

    addendum_id = models.AutoField(primary_key=True)
    encounter = models.ForeignKey(
        Encounter, on_delete=models.CASCADE,
        related_name="addenda", db_column="encounter_id",
    )
    author = models.ForeignKey(
        "accounts.Staff", on_delete=models.PROTECT,
        related_name="encounter_addenda", db_column="staff_id",
    )
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "emr_encounter_addendum"
        ordering = ["created_at"]

    def __str__(self):
        return f"Addendum #{self.pk} to encounter {self.encounter_id}"


# ---------------------------------------------------------------------------
# 4.11 MedicalHistory
# ---------------------------------------------------------------------------
class MedicalHistory(models.Model):
    class HistoryType(models.TextChoices):
        CONDITION = "condition", "Past condition"
        LIVER_ETIOLOGY = "liver_etiology", "Cause of liver disease"
        SURGERY = "surgery", "Previous surgery"
        ALLERGY = "allergy", "Allergy"
        FAMILY_HISTORY = "family_history", "Family history"

    history_id = models.AutoField(primary_key=True)
    patient = models.ForeignKey(
        "registry.Patient", on_delete=models.CASCADE,
        related_name="medical_history", db_column="patient_id",
    )
    history_type = models.CharField(max_length=20, choices=HistoryType.choices)
    description = models.TextField()
    onset_date = models.DateField(null=True, blank=True)
    recorded_by = models.ForeignKey(
        "accounts.Staff", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="recorded_histories", db_column="recorded_by",
    )

    class Meta:
        db_table = "emr_medical_history"
        verbose_name_plural = "medical histories"
        ordering = ["history_type", "-onset_date"]
        indexes = [models.Index(fields=["patient", "history_type"])]

    def __str__(self):
        return f"{self.get_history_type_display()}: {self.description[:40]}"


# ---------------------------------------------------------------------------
# 4.12 Diagnosis
# ---------------------------------------------------------------------------
class Diagnosis(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        RESOLVED = "resolved", "Resolved"

    diagnosis_id = models.AutoField(primary_key=True)
    encounter = models.ForeignKey(
        Encounter, on_delete=models.CASCADE,
        related_name="diagnoses", db_column="encounter_id",
    )
    patient = models.ForeignKey(
        "registry.Patient", on_delete=models.PROTECT,
        related_name="diagnoses", db_column="patient_id",
    )
    icd10_code = models.CharField(max_length=10, help_text="e.g. K74.6 cirrhosis, C22.0 HCC")
    description = models.CharField(max_length=255)
    is_primary = models.BooleanField(default=False)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    diagnosed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "emr_diagnosis"
        verbose_name_plural = "diagnoses"
        ordering = ["-diagnosed_at"]
        constraints = [
            # Business rule: each encounter has at most one primary diagnosis.
            models.UniqueConstraint(
                fields=["encounter"], condition=Q(is_primary=True),
                name="uq_diagnosis_one_primary_per_encounter",
            ),
            # Basic ICD-10 shape: letter, 2 digits, optional dot + 1-4 alphanumerics.
            models.CheckConstraint(
                condition=Q(icd10_code__regex=r"^[A-Z][0-9][0-9A-Z](\.[0-9A-Z]{1,4})?$"),
                name="ck_diagnosis_icd10_format",
            ),
        ]
        indexes = [models.Index(fields=["patient", "status"]), models.Index(fields=["icd10_code"])]

    def __str__(self):
        return f"{self.icd10_code} – {self.description}"

    def clean(self):
        if self.encounter_id and self.patient_id and self.encounter.patient_id != self.patient_id:
            raise ValidationError("Diagnosis patient must match the encounter's patient.")

    def save(self, *args, **kwargs):
        self.icd10_code = self.icd10_code.strip().upper()
        if self.encounter_id and not self.patient_id:
            self.patient_id = self.encounter.patient_id
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# 4.13 VitalSigns
# ---------------------------------------------------------------------------
class VitalSigns(models.Model):
    vitals_id = models.AutoField(primary_key=True)
    encounter = models.ForeignKey(
        Encounter, on_delete=models.CASCADE,
        related_name="vital_signs", db_column="encounter_id",
    )
    bp_systolic = models.PositiveSmallIntegerField(null=True, blank=True, help_text="mmHg")
    bp_diastolic = models.PositiveSmallIntegerField(null=True, blank=True, help_text="mmHg")
    pulse = models.PositiveSmallIntegerField(null=True, blank=True, help_text="beats per minute")
    temperature = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, help_text="°C")
    weight_kg = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    height_cm = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    bmi = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True, editable=False,
        help_text="Calculated by the system: weight_kg / (height_m)²",
    )
    recorded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "emr_vital_signs"
        verbose_name_plural = "vital signs"
        ordering = ["-recorded_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(bp_systolic__isnull=True) | Q(bp_diastolic__isnull=True)
                | Q(bp_systolic__gt=models.F("bp_diastolic")),
                name="ck_vitals_systolic_gt_diastolic",
            ),
            models.CheckConstraint(
                condition=Q(weight_kg__isnull=True) | Q(weight_kg__gt=0), name="ck_vitals_weight_positive",
            ),
            models.CheckConstraint(
                condition=Q(height_cm__isnull=True) | Q(height_cm__gt=0), name="ck_vitals_height_positive",
            ),
        ]

    def __str__(self):
        return f"Vitals #{self.pk} (encounter {self.encounter_id})"

    def calculate_bmi(self):
        if self.weight_kg and self.height_cm:
            height_m = Decimal(self.height_cm) / Decimal(100)
            return (Decimal(self.weight_kg) / (height_m * height_m)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        return None

    def save(self, *args, **kwargs):
        # Business rule: BMI is always derived, never entered by hand.
        self.bmi = self.calculate_bmi()
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# 4.14 Document
# ---------------------------------------------------------------------------
def document_upload_path(instance, filename):
    owner = f"patient_{instance.patient_id}" if instance.patient_id else "unassigned"
    return f"documents/{owner}/{timezone.now():%Y/%m}/{filename}"


class DocumentQuerySet(models.QuerySet):
    def released(self):
        """Documents a patient/donor may see in the portal."""
        return self.filter(is_released=True)


class Document(models.Model):
    class DocumentType(models.TextChoices):
        EXTERNAL_REPORT = "external_report", "External report"
        CONSENT_FORM = "consent_form", "Consent form"
        RADIOLOGY_REPORT = "radiology_report", "Radiology report"
        LAB_REPORT = "lab_report", "Lab report"
        OTHER = "other", "Other"

    document_id = models.AutoField(primary_key=True)
    patient = models.ForeignKey(
        "registry.Patient", on_delete=models.CASCADE, null=True, blank=True,
        related_name="documents", db_column="patient_id",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="uploaded_documents", db_column="uploaded_by",
    )
    document_type = models.CharField(max_length=20, choices=DocumentType.choices)
    title = models.CharField(max_length=255)
    file_path = models.FileField(upload_to=document_upload_path, max_length=500)
    is_released = models.BooleanField(default=False, help_text="Visible to the patient in the portal.")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    objects = DocumentQuerySet.as_manager()

    class Meta:
        db_table = "emr_document"
        ordering = ["-uploaded_at"]
        indexes = [models.Index(fields=["patient", "is_released"])]

    def __str__(self):
        return self.title
