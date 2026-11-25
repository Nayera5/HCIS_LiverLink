from django.utils import timezone
from rest_framework import serializers

from apps.accounts.models import Staff, User
from apps.accounts.rbac import SCHEDULABLE_TITLES, get_staff_profile, has_capability
from apps.emr.models import Encounter
from apps.registry.models import Patient

from .models import Appointment, DoctorSchedule, free_slots
from .permissions import is_portal_user

DOCTOR_ERROR = "Choose an active hepatologist, transplant surgeon or radiologist."
APPOINTMENT_DOCTOR_TITLES = {
    Appointment.Type.HEPATOLOGY_CONSULTATION: "hepatologist",
    Appointment.Type.EXAMINATION: "hepatologist",
    Appointment.Type.TRANSPLANT_CONSULTATION: "transplant_surgeon",
    Appointment.Type.DONOR_EVALUATION: "transplant_surgeon",
    Appointment.Type.RECIPIENT_EVALUATION: "transplant_surgeon",
    Appointment.Type.FOLLOW_UP: "transplant_surgeon",
}


def schedulable_doctors():
    """Active staff who have a working schedule and can be booked."""
    return Staff.objects.filter(
        user__is_active=True, user__role=User.Role.CLINICAL_STAFF, job_title__in=SCHEDULABLE_TITLES,
    ).select_related("user")


def _staff_name(staff):
    return (staff.user.get_full_name() or staff.user.username) if staff else None


def _doctor_field():
    return serializers.PrimaryKeyRelatedField(
        queryset=schedulable_doctors(), required=False,
        error_messages={"does_not_exist": DOCTOR_ERROR, "incorrect_type": DOCTOR_ERROR},
    )


class DoctorScheduleSerializer(serializers.ModelSerializer):
    staff = _doctor_field()
    staff_name = serializers.SerializerMethodField()

    class Meta:
        model = DoctorSchedule
        fields = ["schedule_id", "staff", "staff_name", "day_of_week", "start_time", "end_time",
                  "slot_minutes", "is_active"]
        read_only_fields = ["schedule_id"]

    def get_staff_name(self, schedule):
        return _staff_name(schedule.staff)

    def validate_slot_minutes(self, value):
        if value <= 0:
            raise serializers.ValidationError("Slot length must be more than 0 minutes.")
        return value

    def validate(self, attrs):
        user = self.context["request"].user
        own = get_staff_profile(user)
        staff = attrs.get("staff") or getattr(self.instance, "staff", None)

        # Doctors manage only their own schedule; super admin must say which doctor.
        if not has_capability(user, "schedules.manage_all"):
            if staff is not None and staff != own:
                raise serializers.ValidationError({"staff": "You can only manage your own schedule."})
            staff = own
        elif staff is None:
            raise serializers.ValidationError({"staff": "Doctor is required."})
        attrs["staff"] = staff

        start = attrs.get("start_time", getattr(self.instance, "start_time", None))
        end = attrs.get("end_time", getattr(self.instance, "end_time", None))
        if start and end and end <= start:
            raise serializers.ValidationError({"end_time": "End time must be after start time."})

        # Business rule: schedules of the same doctor on the same day must not overlap.
        day = attrs.get("day_of_week", getattr(self.instance, "day_of_week", None))
        is_active = attrs.get("is_active", getattr(self.instance, "is_active", True))
        if is_active:
            clash = DoctorSchedule.objects.filter(
                staff=staff, day_of_week=day, is_active=True, start_time__lt=end, end_time__gt=start,
            )
            if self.instance:
                clash = clash.exclude(pk=self.instance.pk)
            if clash.exists():
                raise serializers.ValidationError("This overlaps another schedule of the same doctor on that day.")
        return attrs


class AppointmentSerializer(serializers.ModelSerializer):
    """
    Booking and rescheduling. The client sends `start_time` (the start of a free slot);
    the server sets `end_time` from the doctor's schedule.
    """

    patient = serializers.PrimaryKeyRelatedField(queryset=Patient.objects.all(), required=False)
    staff = _doctor_field()
    patient_name = serializers.SerializerMethodField()
    patient_mrn = serializers.CharField(source="patient.mrn", read_only=True)
    staff_name = serializers.SerializerMethodField()
    encounter = serializers.SerializerMethodField()
    # Imaging appointments only (read-only: booked through /api/radiology/).
    imaging_service = serializers.CharField(source="imaging_order.billing_service.name", read_only=True, default=None)

    class Meta:
        model = Appointment
        fields = ["appointment_id", "patient", "patient_name", "patient_mrn", "staff", "staff_name",
                  "booked_by", "appointment_type", "start_time", "end_time", "status", "reason", "encounter",
                  "imaging_order", "imaging_service"]
        read_only_fields = ["appointment_id", "booked_by", "end_time", "status", "imaging_order"]

    def get_patient_name(self, appointment):
        return appointment.patient.full_name

    def get_staff_name(self, appointment):
        return _staff_name(appointment.staff)

    def get_encounter(self, appointment):
        """Id of the EMR encounter recorded for this visit, or None."""
        try:
            return appointment.encounter.pk
        except Encounter.DoesNotExist:
            return None

    def validate_appointment_type(self, value):
        if value in Appointment.NOT_DOCTOR_TYPES:
            raise serializers.ValidationError("Scans are booked from an imaging order, not with a doctor.")
        if value in (Appointment.Type.CT_SCAN, Appointment.Type.LAB_VISIT):
            raise serializers.ValidationError("CT scans and lab visits are not bookable appointment types.")
        return value

    def validate(self, attrs):
        user = self.context["request"].user

        # Patients and donors book only for themselves; the patient cannot be changed later.
        if self.instance is None:
            if is_portal_user(user):
                own = Patient.objects.filter(user=user).first()
                if own is None:
                    raise serializers.ValidationError({"patient": "Your account has no patient record."})
                if attrs.get("patient") not in (None, own):
                    raise serializers.ValidationError({"patient": "You can only book for yourself."})
                attrs["patient"] = own
            elif attrs.get("patient") is None:
                raise serializers.ValidationError({"patient": "Patient is required."})
            if attrs.get("staff") is None:
                raise serializers.ValidationError({"staff": "Doctor is required."})
            if not attrs.get("start_time"):
                raise serializers.ValidationError({"start_time": "Start time is required."})
        else:
            attrs.pop("patient", None)

        staff = attrs.get("staff") or getattr(self.instance, "staff", None)
        appointment_type = attrs.get("appointment_type") or getattr(self.instance, "appointment_type", None)
        required_title = APPOINTMENT_DOCTOR_TITLES.get(appointment_type)
        if required_title and staff.job_title != required_title:
            title = "hepatologist" if required_title == "hepatologist" else "transplant surgeon"
            raise serializers.ValidationError({"staff": f"Choose a {title} for this type of visit."})

        # Business rule: the time must be a free slot of the doctor (no double booking).
        staff = staff or self.instance.staff
        start = attrs.get("start_time") or self.instance.start_time
        slots = dict(free_slots(staff, timezone.localtime(start).date(), exclude_appointment=self.instance))
        if start not in slots:
            raise serializers.ValidationError({"start_time": "This time is not a free slot of the doctor."})
        attrs["start_time"], attrs["end_time"] = start, slots[start]
        return attrs

