"""
Module 7 – Radiology (basic workflow). Stage 1: imaging orders (spec §4.20).

DICOM, PACS, study linking, the viewer and AI analysis are out of scope for this phase.

Differences from the spec:
- The CT-only `protocol` is replaced by `billing_service`: the examination is one imaging service of the
  Billing catalog (the only list of examinations; its price is never copied here).
- `indication` is called `clinical_indication` and is required.
- Addition: ImagingSlot, the scan times published by the radiologist, with an optional resource label.
- The scan visit is a scheduling.Appointment of type 'imaging' that points to its order and slot.
- Status becomes `acquired` by hand (spec: when the study arrives in Orthanc, which is excluded).
"""
from django.db import models
from django.db.models import F, Q
from django.utils import timezone


IMAGING_ROOM_NAMES = ("CT Room 1", "CT Room 2")


class ImagingOrder(models.Model):
    """A doctor's request for an imaging examination."""

    class Status(models.TextChoices):
        ORDERED = "ordered", "Ordered"
        SCHEDULED = "scheduled", "Scheduled"
        ACQUIRED = "acquired", "Acquired"
        CANCELLED = "cancelled", "Cancelled"

    ACTIVE_STATUSES = (Status.ORDERED, Status.SCHEDULED)

    # Allowed status changes: current status -> statuses it may move to. (Losing or moving its booking
    # also takes a scheduled order back to ordered; see services.py.)
    TRANSITIONS = {
        Status.ORDERED: {Status.SCHEDULED, Status.ACQUIRED, Status.CANCELLED},
        Status.SCHEDULED: {Status.ACQUIRED, Status.CANCELLED},
    }

    imaging_order_id = models.AutoField(primary_key=True)
    patient = models.ForeignKey(
        "registry.Patient", on_delete=models.PROTECT,
        related_name="imaging_orders", db_column="patient_id",
    )
    # An open encounter can be deleted: the order stays, without the link.
    encounter = models.ForeignKey(
        "emr.Encounter", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="imaging_orders", db_column="encounter_id",
        help_text="Visit in which the scan was requested.",
    )
    ordered_by = models.ForeignKey(
        "accounts.Staff", on_delete=models.PROTECT,
        related_name="imaging_orders", db_column="ordered_by",
    )
    billing_service = models.ForeignKey(
        "billing.Service", on_delete=models.PROTECT,
        related_name="imaging_orders",
        help_text="Examination ordered: an imaging service of the Billing catalog.",
    )
    clinical_indication = models.TextField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ORDERED)
    order_date = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "radiology_imaging_order"
        ordering = ["-order_date", "-imaging_order_id"]
        indexes = [
            models.Index(fields=["patient", "-order_date"], name="radiology_order_patient_idx"),
            models.Index(fields=["status", "-order_date"], name="radiology_order_status_idx"),
        ]
        constraints = [
            models.CheckConstraint(condition=Q(status__in=["ordered", "scheduled", "acquired", "cancelled"]),
                                   name="radiology_order_status_valid"),
        ]

    def __str__(self):
        return f"Imaging order #{self.pk} ({self.status})"

    def can_move_to(self, new_status):
        return new_status in self.TRANSITIONS.get(self.status, set())

    @property
    def booking(self):
        """The order's live scan appointment (booked, checked in or completed), or None."""
        if not hasattr(self, "_bookings"):  # filled by views.orders() to avoid one query per row
            from apps.scheduling.models import Appointment
            return self.appointments.filter(status__in=Appointment.SLOT_HOLDING_STATUSES).first()
        return self._bookings[0] if self._bookings else None


class ImagingSlot(models.Model):
    """A time for one imaging service; patients only see published, free, future slots."""

    slot_id = models.AutoField(primary_key=True)
    billing_service = models.ForeignKey(
        "billing.Service", on_delete=models.PROTECT, related_name="imaging_slots",
        help_text="Imaging service of the Billing catalog that can be booked in this slot.",
    )
    resource_name = models.CharField(
        max_length=80, blank=True, default="",
        help_text="Scanner or room label; blank represents the default resource.",
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_published = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        "accounts.Staff", on_delete=models.PROTECT,
        related_name="imaging_slots", db_column="created_by",
    )

    class Meta:
        db_table = "radiology_imaging_slot"
        ordering = ["start_time", "resource_name"]
        constraints = [
            models.CheckConstraint(condition=Q(end_time__gt=F("start_time")), name="radiology_slot_end_after_start"),
            models.UniqueConstraint(fields=["billing_service", "resource_name", "start_time"],
                                    name="radiology_slot_service_start_uniq"),
        ]

    def __str__(self):
        return f"Scan slot {self.start_time:%Y-%m-%d %H:%M}"
