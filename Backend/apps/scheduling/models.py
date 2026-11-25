"""Module 3 – Appointment & Scheduling.

Entities: DoctorSchedule, Appointment (entity dictionary sections 4.8 – 4.9).

Linked modules:
- module 1 (accounts): Staff (the doctor) and User (who booked);
- module 2 (registry): Patient (the patient or donor of the visit);
- module 4 (EMR): Encounter.appointment points here (one encounter per appointment).

Appointment may optionally link to a transplant.TransplantCase (spec §4.9).

Two kinds of appointment:
- doctor appointment: a doctor (`staff`) and one of the doctor's free slots;
- imaging appointment (type 'imaging'): no doctor; an imaging order and a published scan slot
  (module 7). It is booked, moved and cancelled only through apps/radiology, which keeps the order
  in step; the database constraints below keep the two kinds apart.

Times: schedule times and slot dates use the server time zone (settings.TIME_ZONE).
"""
import datetime

from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.utils import timezone


# ---------------------------------------------------------------------------
# 4.8 DoctorSchedule
# ---------------------------------------------------------------------------
class DoctorSchedule(models.Model):
    class Day(models.TextChoices):
        SAT = "sat", "Saturday"
        SUN = "sun", "Sunday"
        MON = "mon", "Monday"
        TUE = "tue", "Tuesday"
        WED = "wed", "Wednesday"
        THU = "thu", "Thursday"
        FRI = "fri", "Friday"

    # Python's date.weekday(): Monday = 0 ... Sunday = 6
    WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

    schedule_id = models.AutoField(primary_key=True)
    staff = models.ForeignKey(
        "accounts.Staff", on_delete=models.PROTECT,
        related_name="schedules", db_column="staff_id",
    )
    day_of_week = models.CharField(max_length=3, choices=Day.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()
    slot_minutes = models.PositiveSmallIntegerField(help_text="Length of each bookable slot, e.g. 15 or 30.")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["staff", "day_of_week", "start_time"]
        constraints = [
            models.CheckConstraint(condition=Q(end_time__gt=F("start_time")),
                                   name="scheduling_schedule_end_after_start"),
            models.CheckConstraint(condition=Q(slot_minutes__gt=0),
                                   name="scheduling_schedule_slot_positive"),
        ]

    def __str__(self):
        return f"{self.staff} – {self.day_of_week} {self.start_time:%H:%M}-{self.end_time:%H:%M}"

    @classmethod
    def day_code(cls, day):
        """'sat', 'sun', ... for a date."""
        return cls.WEEKDAYS[day.weekday()]

    def slots_on(self, day):
        """All (start, end) slots of this schedule on `day`, as aware datetimes."""
        tz = timezone.get_current_timezone()
        step = datetime.timedelta(minutes=self.slot_minutes)
        start = timezone.make_aware(datetime.datetime.combine(day, self.start_time), tz)
        last = timezone.make_aware(datetime.datetime.combine(day, self.end_time), tz)
        slots = []
        while start + step <= last:
            slots.append((start, start + step))
            start += step
        return slots


# ---------------------------------------------------------------------------
# 4.9 Appointment
# ---------------------------------------------------------------------------
class Appointment(models.Model):
    class Type(models.TextChoices):
        CONSULTATION = "consultation", "Consultation"
        CT_SCAN = "ct_scan", "CT scan"
        LAB_VISIT = "lab_visit", "Lab visit"
        DONOR_EVALUATION = "donor_evaluation", "Donor evaluation"
        RECIPIENT_EVALUATION = "recipient_evaluation", "Recipient evaluation"
        FOLLOW_UP = "follow_up", "Post-transplant follow-up"
        IMAGING = "imaging", "Imaging scan"

    # Not bookable with a doctor: scans need an imaging order and a scan slot. ('ct_scan' is kept
    # for appointments made before imaging orders existed.)
    NOT_DOCTOR_TYPES = (Type.CT_SCAN, Type.IMAGING)

    class Status(models.TextChoices):
        BOOKED = "booked", "Booked"
        CHECKED_IN = "checked_in", "Checked in"
        COMPLETED = "completed", "Completed"
        NO_SHOW = "no_show", "No-show"
        CANCELLED = "cancelled", "Cancelled"

    # Appointments in these statuses hold the doctor's slot.
    ACTIVE_STATUSES = (Status.BOOKED, Status.CHECKED_IN)
    # An imaging appointment in these statuses uses up its scan slot and its order.
    SLOT_HOLDING_STATUSES = (Status.BOOKED, Status.CHECKED_IN, Status.COMPLETED)

    # Allowed status changes: current status -> statuses it may move to.
    TRANSITIONS = {
        Status.BOOKED: {Status.CHECKED_IN, Status.NO_SHOW, Status.CANCELLED},
        Status.CHECKED_IN: {Status.COMPLETED, Status.CANCELLED},
    }

    appointment_id = models.AutoField(primary_key=True)
    patient = models.ForeignKey(
        "registry.Patient", on_delete=models.PROTECT,
        related_name="appointments", db_column="patient_id",
    )
    case = models.ForeignKey(
        "transplant.TransplantCase", on_delete=models.SET_NULL,
        related_name="appointments", db_column="case_id",
        null=True, blank=True,
        help_text="Transplant case this evaluation or follow-up appointment supports.",
    )
    staff = models.ForeignKey(
        "accounts.Staff", on_delete=models.PROTECT,
        related_name="appointments", db_column="staff_id", null=True, blank=True,
        help_text="Doctor the visit is with (empty for imaging appointments only).",
    )
    imaging_order = models.ForeignKey(
        "radiology.ImagingOrder", on_delete=models.PROTECT,
        related_name="appointments", db_column="imaging_order_id", null=True, blank=True,
        help_text="Order the scan is for (imaging appointments only).",
    )
    imaging_slot = models.ForeignKey(
        "radiology.ImagingSlot", on_delete=models.PROTECT,
        related_name="appointments", db_column="imaging_slot_id", null=True, blank=True,
        help_text="Scan slot (imaging appointments only).",
    )
    booked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="booked_appointments", db_column="booked_by",
    )
    appointment_type = models.CharField(max_length=25, choices=Type.choices)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.BOOKED)
    reason = models.TextField(blank=True)

    class Meta:
        ordering = ["start_time"]
        indexes = [
            models.Index(fields=["staff", "start_time"]),
            models.Index(fields=["patient", "start_time"]),
        ]
        constraints = [
            models.CheckConstraint(condition=Q(end_time__gt=F("start_time")),
                                   name="scheduling_appointment_end_after_start"),
            models.CheckConstraint(
                condition=(
                    Q(appointment_type="imaging", staff__isnull=True,
                      imaging_order__isnull=False, imaging_slot__isnull=False)
                    | (~Q(appointment_type="imaging")
                       & Q(staff__isnull=False, imaging_order__isnull=True, imaging_slot__isnull=True))
                ),
                name="scheduling_appointment_doctor_or_scan"),
            # No double booking of a scan slot, and one live booking per imaging order.
            models.UniqueConstraint(fields=["imaging_slot"], name="scheduling_one_booking_per_scan_slot",
                                    condition=Q(status__in=["booked", "checked_in", "completed"])),
            models.UniqueConstraint(fields=["imaging_order"], name="scheduling_one_booking_per_scan_order",
                                    condition=Q(status__in=["booked", "checked_in", "completed"])),
        ]

    def __str__(self):
        return f"Appointment #{self.pk} – patient {self.patient_id} ({self.start_time:%Y-%m-%d %H:%M})"

    @property
    def is_imaging(self):
        return self.appointment_type == self.Type.IMAGING

    def can_move_to(self, new_status):
        return new_status in self.TRANSITIONS.get(self.status, set())


def free_slots(staff, day, exclude_appointment=None):
    """
    Free (start, end) slots of a doctor on `day`: slots from the doctor's active schedules,
    minus slots already taken by booked / checked-in appointments, minus slots in the past.
    `exclude_appointment` is ignored when checking conflicts (used when rescheduling it).
    """
    schedules = DoctorSchedule.objects.filter(staff=staff, is_active=True, day_of_week=DoctorSchedule.day_code(day))
    slots = sorted(slot for schedule in schedules for slot in schedule.slots_on(day))
    if not slots:
        return []

    taken = Appointment.objects.filter(
        staff=staff, status__in=Appointment.ACTIVE_STATUSES,
        start_time__lt=slots[-1][1], end_time__gt=slots[0][0],
    )
    if exclude_appointment is not None:
        taken = taken.exclude(pk=exclude_appointment.pk)
    taken = list(taken.values_list("start_time", "end_time"))

    now = timezone.now()
    return [
        (start, end) for start, end in slots
        if start > now and not any(start < t_end and end > t_start for t_start, t_end in taken)
    ]
