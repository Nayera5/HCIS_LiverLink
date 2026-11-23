"""
Prescriptions & treatment plans (Module 6, spec 4.18-4.19).

Deviation from the spec (agreed): `Prescription.drug_name` is a foreign key to a seeded `Drug`
catalog (internal drug code, not NDC) so the UI can autocomplete and authorized users can add drugs.
"""
from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Lower
from django.utils import timezone


class Route(models.TextChoices):
    ORAL = 'oral', 'Oral'
    IV = 'iv', 'Intravenous (IV)'
    IM = 'im', 'Intramuscular (IM)'
    SC = 'sc', 'Subcutaneous (SC)'
    TOPICAL = 'topical', 'Topical'


ROUTE_VALUES = ['oral', 'iv', 'im', 'sc', 'topical']


class Drug(models.Model):
    """Catalog of prescribable medications. `code` is an internal ID (DRG-0001), not an NDC."""

    code = models.CharField(max_length=20, unique=True, editable=False)
    name = models.CharField(max_length=150, help_text='Display / brand-neutral name, e.g. "Tenofovir disoproxil".')
    generic_name = models.CharField(max_length=150, blank=True)
    drug_class = models.CharField(max_length=100, blank=True, help_text='e.g. Antiviral (HBV), Immunosuppressant.')
    default_route = models.CharField(max_length=10, choices=Route.choices, blank=True)
    common_dose = models.CharField(max_length=100, blank=True, help_text='Typical dose, shown as a hint.')
    is_active = models.BooleanField(default=True, help_text='Inactive drugs cannot be newly prescribed.')
    created_by = models.ForeignKey('accounts.User', null=True, blank=True, on_delete=models.SET_NULL,
                                   related_name='drugs_added')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(Lower('name'), name='prescriptions_drug_name_ci_unique'),
            models.CheckConstraint(condition=Q(default_route='') | Q(default_route__in=ROUTE_VALUES),
                                   name='prescriptions_drug_route_valid'),
        ]

    def __str__(self):
        return f'{self.name} ({self.code})'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.code:  # internal ID derived from the primary key
            self.code = f'DRG-{self.pk:04d}'
            Drug.objects.filter(pk=self.pk).update(code=self.code)


class Prescription(models.Model):
    """A medication prescribed to a patient or donor (4.18)."""

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        STOPPED = 'stopped', 'Stopped'
        COMPLETED = 'completed', 'Completed'

    patient = models.ForeignKey('registry.Patient', on_delete=models.PROTECT, related_name='prescriptions')
    # encounter FK is added when the EMR Encounter model exists (apps/emr is still a stub).
    prescribed_by = models.ForeignKey('accounts.Staff', on_delete=models.PROTECT, related_name='prescriptions')
    drug = models.ForeignKey(Drug, on_delete=models.PROTECT, related_name='prescriptions')
    dose = models.CharField(max_length=100, help_text='Dose per intake, e.g. 300 mg.')
    route = models.CharField(max_length=10, choices=Route.choices)
    frequency = models.CharField(max_length=100, help_text='e.g. once daily, twice daily.')
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True, help_text='Empty if ongoing.')
    instructions = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    stopped_at = models.DateTimeField(null=True, blank=True)
    stop_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ['-start_date', '-id']
        indexes = [models.Index(fields=['patient', 'status'], name='rx_patient_status_idx')]
        constraints = [
            models.CheckConstraint(condition=Q(route__in=ROUTE_VALUES), name='rx_route_valid'),
            models.CheckConstraint(condition=Q(status__in=['active', 'stopped', 'completed']), name='rx_status_valid'),
            models.CheckConstraint(condition=Q(end_date__isnull=True) | Q(end_date__gt=F('start_date')),
                                   name='rx_end_after_start'),
        ]

    def __str__(self):
        return f'Rx #{self.pk} {self.drug.name} {self.dose} ({self.status})'

    @property
    def is_current(self):
        """Active and not past its end date: belongs on the *active* medication list."""
        if self.status != self.Status.ACTIVE:
            return False
        return self.end_date is None or self.end_date >= timezone.localdate()


class TreatmentPlan(models.Model):
    """Planned treatment for a patient, with goals, steps and a review date (4.19)."""

    class PlanType(models.TextChoices):
        SURVEILLANCE = 'surveillance', 'Surveillance'
        ANTIVIRAL = 'antiviral', 'Antiviral therapy'
        ABLATION = 'ablation', 'Ablation'
        TACE = 'tace', 'Chemoembolization (TACE)'
        RESECTION = 'resection', 'Resection'
        TRANSPLANT_REFERRAL = 'transplant_referral', 'Transplant referral'
        SUPPORTIVE = 'supportive', 'Supportive care'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'

    # Fields a doctor may change on an active plan (every change is audited with a reason).
    EDITABLE_FIELDS = ('plan_type', 'goals', 'steps', 'start_date', 'review_date')

    patient = models.ForeignKey('registry.Patient', on_delete=models.PROTECT, related_name='treatment_plans')
    created_by = models.ForeignKey('accounts.Staff', on_delete=models.PROTECT, related_name='treatment_plans')
    plan_type = models.CharField(max_length=25, choices=PlanType.choices)
    goals = models.TextField()
    steps = models.TextField(blank=True)
    start_date = models.DateField()
    review_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date', '-id']
        indexes = [models.Index(fields=['patient', 'status'], name='plan_patient_status_idx')]
        constraints = [
            models.CheckConstraint(
                condition=Q(plan_type__in=['surveillance', 'antiviral', 'ablation', 'tace', 'resection',
                                           'transplant_referral', 'supportive']),
                name='plan_type_valid'),
            models.CheckConstraint(condition=Q(status__in=['active', 'completed', 'cancelled']),
                                   name='plan_status_valid'),
            models.CheckConstraint(condition=Q(review_date__isnull=True) | Q(review_date__gte=F('start_date')),
                                   name='plan_review_not_before_start'),
        ]

    def __str__(self):
        return f'Plan #{self.pk} {self.plan_type} ({self.status})'

    @property
    def review_due(self):
        """Active plan whose review date is today or already passed."""
        return (self.status == self.Status.ACTIVE and self.review_date is not None
                and self.review_date <= timezone.localdate())
