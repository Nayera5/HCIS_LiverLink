"""Laboratory models (spec 4.15-4.17): test catalog, orders and per-test results."""
from decimal import Decimal

from django.db import models
from django.db.models import Q
from django.utils import timezone


class LabTest(models.Model):
    """Catalog of orderable tests with unit and normal range (4.15)."""

    code = models.CharField(max_length=30, unique=True, help_text='Test code (e.g. LOINC).')
    name = models.CharField(max_length=150)
    unit = models.CharField(max_length=30, blank=True)
    normal_min = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    normal_max = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    # Addition to the spec: the "critical" flag needs thresholds beyond the normal range.
    critical_min = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    critical_max = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.code})'

    def compute_flag(self, value):
        """normal / low / high / critical from the ranges. Empty string while pending."""
        if value is None:
            return ''
        value = Decimal(value)
        if self.critical_min is not None and value <= self.critical_min:
            return LabResult.Flag.CRITICAL
        if self.critical_max is not None and value >= self.critical_max:
            return LabResult.Flag.CRITICAL
        if self.normal_min is not None and value < self.normal_min:
            return LabResult.Flag.LOW
        if self.normal_max is not None and value > self.normal_max:
            return LabResult.Flag.HIGH
        return LabResult.Flag.NORMAL


class LabOrder(models.Model):
    """A request by a doctor for one or more tests (4.16)."""

    class Priority(models.TextChoices):
        ROUTINE = 'routine', 'Routine'
        URGENT = 'urgent', 'Urgent'

    class Status(models.TextChoices):
        ORDERED = 'ordered', 'Ordered'
        PARTIALLY_RESULTED = 'partially_resulted', 'Partially resulted'
        RESULTED = 'resulted', 'Resulted'
        CANCELLED = 'cancelled', 'Cancelled'

    patient = models.ForeignKey('registry.Patient', on_delete=models.PROTECT, related_name='lab_orders')
    # encounter FK is added when the EMR Encounter model exists (apps/emr is still a stub).
    ordered_by = models.ForeignKey('accounts.Staff', on_delete=models.PROTECT, related_name='lab_orders')
    order_date = models.DateTimeField(default=timezone.now)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.ROUTINE)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ORDERED)

    class Meta:
        ordering = ['-order_date', '-id']
        indexes = [models.Index(fields=['patient', '-order_date'], name='labs_order_patient_idx')]
        constraints = [
            models.CheckConstraint(condition=Q(priority__in=['routine', 'urgent']), name='labs_order_priority_valid'),
            models.CheckConstraint(
                condition=Q(status__in=['ordered', 'partially_resulted', 'resulted', 'cancelled']),
                name='labs_order_status_valid'),
        ]

    def __str__(self):
        return f'LabOrder #{self.pk} ({self.status})'

    def refresh_status(self):
        """Business rule: resulted when ALL tests have values; partial when some do."""
        if self.status == self.Status.CANCELLED:
            return
        total = self.results.count()
        done = self.results.filter(value__isnull=False).count()
        new = (self.Status.RESULTED if total and done == total
               else self.Status.PARTIALLY_RESULTED if done else self.Status.ORDERED)
        if new != self.status:
            self.status = new
            self.save(update_fields=['status'])


class LabResult(models.Model):
    """One test within an order; empty value = pending (4.17)."""

    class Flag(models.TextChoices):
        NORMAL = 'normal', 'Normal'
        LOW = 'low', 'Low'
        HIGH = 'high', 'High'
        CRITICAL = 'critical', 'Critical'

    lab_order = models.ForeignKey(LabOrder, on_delete=models.CASCADE, related_name='results')
    lab_test = models.ForeignKey(LabTest, on_delete=models.PROTECT, related_name='results')
    # hl7_message FK is added with the HL7 module (apps/hl7 is still a stub).
    value = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    flag = models.CharField(max_length=10, choices=Flag.choices, blank=True)
    result_time = models.DateTimeField(null=True, blank=True)
    is_released = models.BooleanField(default=False, help_text='Patient can see it in the portal.')

    class Meta:
        ordering = ['lab_order_id', 'lab_test__name']
        constraints = [
            models.UniqueConstraint(fields=['lab_order', 'lab_test'], name='labs_result_unique_test_per_order'),
            models.CheckConstraint(
                condition=Q(flag__in=['', 'normal', 'low', 'high', 'critical']), name='labs_result_flag_valid'),
        ]

    def __str__(self):
        return f'{self.lab_test.code}={self.value}'
