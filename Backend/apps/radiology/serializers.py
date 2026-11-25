import datetime

from django.utils import timezone
from rest_framework import serializers

from apps.billing.models import Service
from apps.emr.models import Encounter
from apps.registry.models import Patient

from .models import ImagingOrder, ImagingSlot

MAX_SLOTS = 100  # per request
SERVICE_FIELDS = ["billing_service", "billing_service_code", "billing_service_name"]
BOOKING_FIELDS = ["appointment", "appointment_start", "appointment_end", "appointment_status", "booking_state"]


def imaging_service_field():
    """Active imaging services of the Billing catalog: exactly what the form's dropdown offers."""
    return serializers.PrimaryKeyRelatedField(
        queryset=Service.objects.filter(category=Service.Category.IMAGING, is_active=True),
        error_messages={"does_not_exist": "This imaging type is not available. Choose another one.",
                        "required": "Choose the imaging type.", "null": "Choose the imaging type."},
    )


class ServiceFields(serializers.Serializer):
    billing_service_code = serializers.CharField(source="billing_service.code", read_only=True)
    billing_service_name = serializers.CharField(source="billing_service.name", read_only=True)


class BookingFields(ServiceFields):
    """Labels and scan appointment. booking_state: none | pending (awaiting confirmation) | confirmed | done."""

    status_label = serializers.CharField(source="get_status_display", read_only=True)
    appointment = serializers.IntegerField(source="booking.pk", read_only=True, default=None)
    appointment_start = serializers.DateTimeField(source="booking.start_time", read_only=True, default=None)
    appointment_end = serializers.DateTimeField(source="booking.end_time", read_only=True, default=None)
    appointment_status = serializers.CharField(source="booking.status", read_only=True, default=None)
    booking_state = serializers.SerializerMethodField()

    def get_booking_state(self, order):
        if order.booking is None:
            return "none"
        return {"ordered": "pending", "scheduled": "confirmed"}.get(order.status, "done")


class ImagingOrderSerializer(BookingFields, serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.full_name", read_only=True)
    patient_mrn = serializers.CharField(source="patient.mrn", read_only=True)
    patient_has_portal = serializers.SerializerMethodField()
    ordered_by_name = serializers.SerializerMethodField()
    encounter_date = serializers.DateTimeField(source="encounter.encounter_date", read_only=True, default=None)
    can_cancel = serializers.SerializerMethodField()
    billing_state = serializers.SerializerMethodField()

    class Meta:
        model = ImagingOrder
        fields = [
            "imaging_order_id", "patient", "patient_name", "patient_mrn", "patient_has_portal",
            "encounter", "encounter_date", *BOOKING_FIELDS, "ordered_by", "ordered_by_name",
            *SERVICE_FIELDS, "clinical_indication", "status", "status_label", "order_date", "can_cancel",
            "billing_state",
        ]
        read_only_fields = fields

    def get_patient_has_portal(self, order):
        return order.patient.user_id is not None

    def get_ordered_by_name(self, order):
        user = order.ordered_by.user
        return user.get_full_name() or user.username

    def get_can_cancel(self, order):
        return order.status in ImagingOrder.ACTIVE_STATUSES and self.context["may_cancel"](order)

    def get_billing_state(self, order):
        if order.status != ImagingOrder.Status.ACQUIRED:
            return "not_ready"
        if getattr(order, "has_active_billing_invoice", False):
            return "invoiced"
        if not order.billing_service.is_active:
            return "needs_service"
        return "needs_review"


class MyImagingOrderSerializer(BookingFields, serializers.ModelSerializer):
    """What a patient sees of their own order (no clinical indication)."""

    class Meta:
        model = ImagingOrder
        fields = ["imaging_order_id", *BOOKING_FIELDS, *SERVICE_FIELDS, "status", "status_label", "order_date"]
        read_only_fields = fields


class ImagingOrderCreateSerializer(serializers.ModelSerializer):
    """`ordered_by`, `status` and `order_date` are set by the server."""

    patient = serializers.PrimaryKeyRelatedField(queryset=Patient.objects.all())
    encounter = serializers.PrimaryKeyRelatedField(
        queryset=Encounter.objects.all(), required=False, allow_null=True,
    )
    clinical_indication = serializers.CharField(max_length=2000)
    billing_service = imaging_service_field()

    class Meta:
        model = ImagingOrder
        fields = ["patient", "encounter", "billing_service", "clinical_indication"]

    def validate(self, attrs):
        encounter = attrs.get("encounter")
        if encounter and encounter.patient_id != attrs["patient"].pk:
            raise serializers.ValidationError({"encounter": "This encounter belongs to another patient."})
        return attrs


class ImagingOrderStatusSerializer(serializers.Serializer):
    """{status, reason?}. 'scheduled' confirms the booked slot; `reason` is required to cancel (audit log)."""

    status = serializers.ChoiceField(choices=ImagingOrder.Status.choices)
    reason = serializers.CharField(required=False, allow_blank=True, max_length=500)

    def validate(self, attrs):
        if attrs["status"] == ImagingOrder.Status.CANCELLED and not attrs.get("reason"):
            raise serializers.ValidationError({"reason": "Write why the order is cancelled."})
        return attrs


class SlotChoiceSerializer(serializers.Serializer):
    slot = serializers.IntegerField(min_value=1, max_value=2**31 - 1)


class ReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500)


class AvailableSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImagingSlot
        fields = ["slot_id", "start_time", "end_time", "resource_name"]


class ImagingSlotSerializer(ServiceFields, serializers.ModelSerializer):
    """Radiologist's view. Only `is_published` can be changed."""

    booking = serializers.SerializerMethodField()

    class Meta:
        model = ImagingSlot
        fields = ["slot_id", *SERVICE_FIELDS, "resource_name", "start_time", "end_time",
                  "is_published", "booking"]
        read_only_fields = ["slot_id", "billing_service", "resource_name", "start_time", "end_time"]

    def get_booking(self, slot):
        if not slot.live_bookings:
            return None
        appointment = slot.live_bookings[0]
        return {"imaging_order": appointment.imaging_order_id, "patient_name": appointment.patient.full_name,
                "order_status": appointment.imaging_order.status, "status": appointment.status}


class SlotBatchSerializer(serializers.Serializer):
    """{billing_service, date, start_time, end_time, slot_minutes, is_published}: hours of one day, split into equal slots."""

    billing_service = imaging_service_field()
    date = serializers.DateField()
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()
    slot_minutes = serializers.IntegerField(min_value=5, max_value=240)
    is_published = serializers.BooleanField(default=True)
    resource_name = serializers.CharField(required=False, allow_blank=True, max_length=80, default="")

    def validate(self, attrs):
        tz = timezone.get_current_timezone()
        start, end = (timezone.make_aware(datetime.datetime.combine(attrs["date"], attrs[name]), tz)
                      for name in ("start_time", "end_time"))
        if end <= start:
            raise serializers.ValidationError({"end_time": "End time must be after start time."})
        if start <= timezone.now():
            raise serializers.ValidationError({"date": "Scan slots must be in the future."})
        step = datetime.timedelta(minutes=attrs["slot_minutes"])
        times = []
        while start + step <= end:
            times.append((start, start + step))
            start += step
        if not times:
            raise serializers.ValidationError({"slot_minutes": "A slot cannot be longer than the working hours."})
        if len(times) > MAX_SLOTS:
            raise serializers.ValidationError({"slot_minutes": f"At most {MAX_SLOTS} slots at once."})
        attrs["times"] = times
        return attrs
