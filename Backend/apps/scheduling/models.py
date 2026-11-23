"""Module 3 – Appointment & Scheduling.

Entities: DoctorSchedule, Appointment (entity dictionary sections 4.8 – 4.9).

Linked modules:
- module 1 (accounts): Staff (the doctor) and User (who booked);
- module 2 (registry): Patient (the patient or donor of the visit);
- module 4 (EMR): Encounter.appointment points here (one encounter per appointment).

Deferred: Appointment.case_id (→ transplant.TransplantCase, spec §4.9) is added with a
migration once the transplant module has a TransplantCase model.

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

    class Status(models.TextChoices):
        BOOKED = "booked", "Booked"
        CHECKED_IN = "checked_in", "Checked in"
        COMPLETED = "completed", "Completed"
        NO_SHOW = "no_show", "No-show"
        CANCELLED = "cancelled", "Cancelled"

    # Appointments in these statuses hold the doctor's slot.
    ACTIVE_STATUSES = (Status.BOOKED, Status.CHECKED_IN)

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
    staff = models.ForeignKey(
        "accounts.Staff", on_delete=models.PROTECT,
        related_name="appointments", db_column="staff_id",
        help_text="Doctor the visit is with.",
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
        ]

    def __str__(self):
        return f"Appointment #{self.pk} – patient {self.patient_id} ({self.start_time:%Y-%m-%d %H:%M})"

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
