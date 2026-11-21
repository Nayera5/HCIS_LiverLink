"""
Patient & Donor Registry (spec §2 and entity dictionary §4.5–§4.6).

- Patient: every person who receives care: liver patients, transplant recipients and living
  donors (one table; the current role is `category`). Optionally linked to a login account.
- MRNSequence: single-row counter that issues Medical Record Numbers (LL-000001, …).
- DonorApplication: a registered person's application to donate to a registered recipient.

Consent (§4.7) is intentionally not implemented yet.
"""
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models, transaction
from django.db.models import F, Q
from django.utils import timezone

MRN_PREFIX = 'LL-'
MRN_MIN_DIGITS = 6

national_id_validator = RegexValidator(
    regex=r'^[0-9]{14}\Z',
    message='The national ID must be exactly 14 digits.',
)


class MRNSequence(models.Model):
    """
    Single-row counter for MRN generation. The row is locked (SELECT … FOR UPDATE) inside the
    transaction that creates the patient, so concurrent registrations never get the same number.
    Works on PostgreSQL and SQLite (SQLite serialises writers).
    """

    id = models.PositiveSmallIntegerField(primary_key=True, default=1)
    last_value = models.PositiveBigIntegerField(default=0)

    class Meta:
        verbose_name = 'MRN sequence'
        constraints = [
            models.CheckConstraint(condition=Q(id=1), name='registry_mrnsequence_single_row'),
        ]

    def __str__(self):
        return f'MRN sequence (last issued: {self.last_value})'

    @classmethod
    def next_mrn(cls):
        """Reserve and return the next MRN. Must run inside a transaction."""
        if not transaction.get_connection().in_atomic_block:
            raise RuntimeError('MRNSequence.next_mrn() must be called inside transaction.atomic().')
        seq, _ = cls.objects.select_for_update().get_or_create(pk=1)
        seq.last_value = F('last_value') + 1
        seq.save(update_fields=['last_value'])
        seq.refresh_from_db(fields=['last_value'])
        return f'{MRN_PREFIX}{seq.last_value:0{MRN_MIN_DIGITS}d}'


class Patient(models.Model):
    """Demographic profile of a liver patient, transplant recipient or living donor (§4.5)."""

    class Sex(models.TextChoices):
        MALE = 'male', 'Male'
        FEMALE = 'female', 'Female'

    class BloodGroup(models.TextChoices):
        A_POS = 'A+', 'A+'
        A_NEG = 'A-', 'A-'
        B_POS = 'B+', 'B+'
        B_NEG = 'B-', 'B-'
        AB_POS = 'AB+', 'AB+'
        AB_NEG = 'AB-', 'AB-'
        O_POS = 'O+', 'O+'
        O_NEG = 'O-', 'O-'

    class Category(models.TextChoices):
        LIVER_PATIENT = 'liver_patient', 'Liver patient'
        RECIPIENT = 'recipient', 'Transplant recipient'
        DONOR = 'donor', 'Living donor'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='patient_profile',
        help_text='Login account (empty when registered by staff without an account).',
    )
    mrn = models.CharField('MRN', max_length=20, unique=True, editable=False)
    national_id = models.CharField(
        max_length=14, unique=True, null=True, blank=True, validators=[national_id_validator],
        help_text='Egyptian national ID (14 digits).',
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    sex = models.CharField(max_length=6, choices=Sex.choices)
    phone = models.CharField(max_length=20)
    address = models.TextField(blank=True)
    emergency_contact = models.CharField(
        max_length=200, blank=True, help_text='Name and phone of an emergency contact.')
    blood_group = models.CharField(max_length=3, choices=BloodGroup.choices, null=True, blank=True)
    height_cm = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal('0.01'))])
    weight_kg = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal('0.01'))], help_text='Needed for GRWR.')
    category = models.CharField(max_length=15, choices=Category.choices)
    registered_by = models.ForeignKey(
        'accounts.Staff', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='registered_patients',
        help_text='Staff member who registered the person (empty for self-registration).',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['last_name', 'first_name'], name='registry_patient_name_idx'),
            models.Index(fields=['category'], name='registry_patient_category_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(national_id__isnull=True) | Q(national_id__regex=r'^[0-9]{14}$'),
                name='registry_patient_national_id_14_digits'),
            models.CheckConstraint(condition=Q(sex__in=['male', 'female']), name='registry_patient_sex_valid'),
            models.CheckConstraint(
                condition=Q(blood_group__isnull=True)
                | Q(blood_group__in=['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']),
                name='registry_patient_blood_group_valid'),
            models.CheckConstraint(
                condition=Q(category__in=['liver_patient', 'recipient', 'donor']),
                name='registry_patient_category_valid'),
            models.CheckConstraint(
                condition=Q(height_cm__isnull=True) | Q(height_cm__gt=0), name='registry_patient_height_positive'),
            models.CheckConstraint(
                condition=Q(weight_kg__isnull=True) | Q(weight_kg__gt=0), name='registry_patient_weight_positive'),
        ]

    def __str__(self):
        return f'{self.mrn} · {self.full_name}'

    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)
        instance._loaded_mrn = instance.__dict__.get('mrn')
        return instance

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()

    def age_on(self, day=None):
        day = day or timezone.localdate()
        born = self.date_of_birth
        return day.year - born.year - ((day.month, day.day) < (born.month, born.day))

    def clean(self):
        super().clean()
        errors = {}
        if self.date_of_birth and self.date_of_birth > timezone.localdate():
            errors['date_of_birth'] = 'Date of birth cannot be in the future.'
        if self.user_id is not None and self.user.role != 'patient':
            errors['user'] = 'Only patient accounts can be linked to a patient record.'
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        # Store "no national ID" as NULL so the unique constraint allows many of them.
        self.national_id = (self.national_id or '').strip() or None
        if self._state.adding:
            if self.mrn:
                raise ValueError('The MRN is generated by the system and cannot be set manually.')
            with transaction.atomic(using=kwargs.get('using')):
                self.mrn = MRNSequence.next_mrn()
                super().save(*args, **kwargs)
            self._loaded_mrn = self.mrn
            return
        if self.mrn != getattr(self, '_loaded_mrn', self.mrn):
            raise ValueError('The MRN of an existing patient cannot be changed.')
        super().save(*args, **kwargs)


class DonorApplication(models.Model):
    """A potential donor's application to donate to a named, registered recipient (§4.6)."""

    class Status(models.TextChoices):
        SUBMITTED = 'submitted', 'Submitted'
        SCREENING = 'screening', 'Screening'
        ACCEPTED = 'accepted', 'Accepted'
        REJECTED = 'rejected', 'Rejected'
        WITHDRAWN = 'withdrawn', 'Withdrawn'

    OPEN_STATUSES = ('submitted', 'screening', 'accepted')
    DECIDED_STATUSES = ('accepted', 'rejected')
    # Screening workflow (coordinator). `accepted` means approved to proceed to the next evaluation
    # stage, NOT medical clearance or surgery approval, so an accepted application stays open and
    # can still be withdrawn by (or for) the donor. Only rejected and withdrawn are terminal.
    SCREENING_TRANSITIONS = {
        'submitted': ('screening', 'accepted', 'rejected'),
        'screening': ('accepted', 'rejected'),
        'accepted': (),
        'rejected': (),
        'withdrawn': (),
    }
    # Who may be named as the intended recipient (not another living donor).
    RECIPIENT_CATEGORIES = ('liver_patient', 'recipient')

    donor = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name='donor_applications')
    recipient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name='received_donor_applications')
    relationship = models.CharField(
        max_length=50, help_text="Donor's relationship to the recipient (son, wife, brother…).")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.SUBMITTED)
    screened_by = models.ForeignKey(
        'accounts.Staff', null=True, blank=True, on_delete=models.PROTECT,
        related_name='screened_donor_applications',
        help_text='Coordinator who screened the application.',
    )
    screened_at = models.DateTimeField(null=True, blank=True)
    screening_notes = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['status', 'submitted_at'], name='registry_donorapp_queue_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=~Q(donor=F('recipient')), name='registry_donorapp_donor_not_recipient'),
            models.CheckConstraint(
                condition=Q(status__in=['submitted', 'screening', 'accepted', 'rejected', 'withdrawn']),
                name='registry_donorapp_status_valid'),
            models.CheckConstraint(
                condition=~Q(status__in=['accepted', 'rejected'])
                | Q(screened_by__isnull=False, screened_at__isnull=False),
                name='registry_donorapp_decision_has_screener'),
            models.UniqueConstraint(
                fields=['donor', 'recipient'], condition=Q(status__in=['submitted', 'screening', 'accepted']),
                name='registry_donorapp_one_open_per_pair',
                violation_error_message='This donor already has an open application for this recipient.'),
        ]

    def __str__(self):
        return f'Application #{self.pk}: {self.donor.mrn} → {self.recipient.mrn} ({self.status})'

    @property
    def is_open(self):
        return self.status in self.OPEN_STATUSES

    def next_screening_statuses(self):
        return self.SCREENING_TRANSITIONS.get(self.status, ())

    def apply_screening(self, new_status, staff, notes=None):
        """Move to `new_status` (must be an allowed transition) and record the screener."""
        if new_status not in self.next_screening_statuses():
            raise ValidationError({'status': f'An application that is {self.get_status_display().lower()} '
                                             f'cannot be moved to {new_status}.'})
        self.status = new_status
        self.screened_by = staff
        self.screened_at = timezone.now()
        if notes is not None:
            self.screening_notes = notes
        self.save(update_fields=['status', 'screened_by', 'screened_at', 'screening_notes', 'updated_at'])

    def withdraw(self):
        """Withdraw an open application (by the donor, or by staff on the donor's behalf)."""
        if not self.is_open:
            raise ValidationError({'status': f'An application that is {self.get_status_display().lower()} '
                                             'cannot be withdrawn.'})
        self.status = self.Status.WITHDRAWN
        self.save(update_fields=['status', 'updated_at'])

    def clean(self):
        super().clean()
        if self.donor_id and self.donor_id == self.recipient_id:
            raise ValidationError({'recipient': 'The donor and the recipient must be different people.'})
