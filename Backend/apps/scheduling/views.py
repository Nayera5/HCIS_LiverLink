"""
Scheduling API (module 3), mounted at /api/scheduling/. Permissions: see permissions.py.

    schedules/                          doctor working schedules (no delete: set is_active=false)
    schedules/doctors/                  doctors who can be booked
    schedules/free-slots/?staff=&date=  free slots of a doctor on one day (YYYY-MM-DD)
    appointments/                       list (calendar filters) and book
    appointments/{id}/reschedule/       new start_time (and optionally staff)
    appointments/{id}/cancel/ | check-in/ | no-show/ | complete/

Imaging appointments (type 'imaging') appear in the list and can be checked in here; booking, moving,
cancelling, no-show and completing them is done through /api/radiology/, with the imaging order.

Appointments are never deleted: cancelled and no-show visits are kept for reports.
Audit (module 1 audit log): create, reschedule (update) and status changes.
"""
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.accounts.audit import audit
from apps.accounts.models import AuditLog
from apps.accounts.rbac import get_staff_profile, has_capability
from apps.billing.services import invoice_for_appointment
from .models import Appointment, DoctorSchedule, free_slots
from .permissions import AppointmentAccess, ScheduleAccess, can_book_any, can_view_all, is_portal_user
from .serializers import AppointmentSerializer, DoctorScheduleSerializer, schedulable_doctors

A = AuditLog.Action


def _filter(qs, params, names):
    """Apply simple `?field=value` filters from the query string."""
    for name in names:
        value = params.get(name)
        if value not in (None, ""):
            qs = qs.filter(**{name: value})
    return qs


def _date_param(params, name):
    value = params.get(name)
    if value in (None, ""):
        return None
    day = parse_date(value)
    if day is None:
        raise ValidationError({name: "Use the format YYYY-MM-DD."})
    return day


class DoctorScheduleViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin,
                            mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """/api/scheduling/schedules/?staff=<id>&day_of_week=mon&is_active=true"""

    queryset = DoctorSchedule.objects.select_related("staff__user")
    serializer_class = DoctorScheduleSerializer
    permission_classes = [ScheduleAccess]

    def get_queryset(self):
        qs = super().get_queryset()
        if not can_view_all(self.request.user):  # patients see active schedules only
            qs = qs.filter(is_active=True)
        return _filter(qs, self.request.query_params, ("staff", "day_of_week", "is_active"))

    def perform_create(self, serializer):
        with transaction.atomic():
            schedule = serializer.save()
            audit(self.request, A.CREATE, "scheduling.doctorschedule", entity_id=schedule.pk)

    def update(self, request, *args, **kwargs):
        user = request.user
        if not has_capability(user, "schedules.manage_all") and self.get_object().staff != get_staff_profile(user):
            raise PermissionDenied("You can only manage your own schedule.")
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        with transaction.atomic():
            schedule = serializer.save()
            audit(self.request, A.UPDATE, "scheduling.doctorschedule", entity_id=schedule.pk)

    @action(detail=False, methods=["get"])
    def doctors(self, request):
        """Doctors who can be booked (for the booking and schedule pages). `is_me` marks the signed-in doctor."""
        own = get_staff_profile(request.user)
        rows = schedulable_doctors().order_by("user__first_name", "user__last_name")
        return Response([
            {"staff_id": staff.pk, "name": staff.user.get_full_name() or staff.user.username,
             "job_title": staff.job_title, "is_me": own is not None and own.pk == staff.pk}
            for staff in rows
        ])

    @action(detail=False, methods=["get"], url_path="free-slots")
    def available_slots(self, request):
        day = _date_param(request.query_params, "date")
        if day is None:
            raise ValidationError({"date": "Date is required."})
        staff = schedulable_doctors().filter(pk=request.query_params.get("staff") or None).first()
        if staff is None:
            raise ValidationError({"staff": "Choose an active hepatologist, transplant surgeon or radiologist."})
        slots = [{"start_time": start, "end_time": end} for start, end in free_slots(staff, day)]
        return Response({"staff": staff.pk, "date": day, "slots": slots})


class AppointmentViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin,
                         viewsets.GenericViewSet):
    """
    /api/scheduling/appointments/?staff=&patient=&status=&appointment_type=&date_from=&date_to=
    Day view: date_from = date_to = the day. Week view: date_from = first day, date_to = last day.
    Patients and donors only see and manage their own appointments.
    """

    queryset = Appointment.objects.select_related("patient", "staff__user", "encounter", "imaging_order__billing_service")
    serializer_class = AppointmentSerializer
    permission_classes = [AppointmentAccess]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not can_view_all(user):  # portal user
            qs = qs.filter(patient__user=user)
        params = self.request.query_params
        qs = _filter(qs, params, ("staff", "patient", "status", "appointment_type"))
        date_from, date_to = _date_param(params, "date_from"), _date_param(params, "date_to")
        if date_from:
            qs = qs.filter(start_time__date__gte=date_from)
        if date_to:
            qs = qs.filter(start_time__date__lte=date_to)
        return qs

    # --- helpers ---------------------------------------------------------
    def log(self, action, appointment):
        audit(self.request, action, "scheduling.appointment",
              entity_id=appointment.pk, patient=appointment.patient)

    def check_can_manage(self, appointment):
        """Book / reschedule / cancel: coordinator and super admin, or the patient themself."""
        user = self.request.user
        if can_book_any(user) or appointment.patient.user_id == user.pk:
            return
        raise PermissionDenied("You cannot change this appointment.")

    @staticmethod
    def check_not_imaging(appointment):
        if appointment.is_imaging:
            raise ValidationError("This is a scan appointment: manage it from its imaging order.")

    @transaction.atomic
    def change_status(self, new_status):
        appointment = self.get_object()
        if appointment.is_imaging:
            if new_status != Appointment.Status.CHECKED_IN:
                self.check_not_imaging(appointment)
            # Locked, so a check-in cannot overwrite a cancellation made through the imaging order.
            appointment = Appointment.objects.select_for_update().get(pk=appointment.pk)
        if not appointment.can_move_to(new_status):
            raise ValidationError(f"A {appointment.get_status_display().lower()} appointment cannot be "
                                  f"changed to {Appointment.Status(new_status).label.lower()}.")
        with transaction.atomic():
            appointment.status = new_status
            appointment.save(update_fields=["status"])
            if new_status in (Appointment.Status.CANCELLED, Appointment.Status.NO_SHOW):
                # Keep the linked clinical follow-up visit in sync with its real appointment.
                from apps.transplant.models import FollowUpVisit

                FollowUpVisit.objects.filter(appointment=appointment).update(
                    status=(FollowUpVisit.Status.CANCELLED
                            if new_status == Appointment.Status.CANCELLED
                            else FollowUpVisit.Status.MISSED),
                )
            self.log(A.STATUS_CHANGE, appointment)
            if new_status == Appointment.Status.COMPLETED:
                invoice_for_appointment(appointment)  # module 13: automatic invoice
        return Response(self.get_serializer(appointment).data)

    # --- endpoints -------------------------------------------------------
    def create(self, request, *args, **kwargs):
        if not (can_book_any(request.user) or is_portal_user(request.user)):
            raise PermissionDenied("Only the coordinator can book on behalf of a patient.")
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        with transaction.atomic():
            self.log(A.CREATE, serializer.save(booked_by=self.request.user))

    @action(detail=True, methods=["post"])
    def reschedule(self, request, pk=None):
        appointment = self.get_object()
        self.check_can_manage(appointment)
        self.check_not_imaging(appointment)
        if appointment.status != Appointment.Status.BOOKED:
            raise ValidationError("Only booked appointments can be rescheduled.")
        data = {key: request.data[key] for key in ("start_time", "staff") if key in request.data}
        if "start_time" not in data:
            raise ValidationError({"start_time": "New start time is required."})
        serializer = self.get_serializer(appointment, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            appointment = serializer.save()
            # A post-transplant follow-up visit uses the appointment date as its due date.
            # Keep the coordinator plan, portal, and reminder date in step after a reschedule.
            from apps.transplant.models import FollowUpVisit

            linked_visit = FollowUpVisit.objects.filter(appointment=appointment).first()
            if linked_visit is not None:
                linked_visit.due_date = timezone.localdate(appointment.start_time)
                linked_visit.save(update_fields=['due_date'])
                audit(
                    request, A.UPDATE, 'transplant.followupvisit',
                    entity_id=linked_visit.pk, patient=linked_visit.plan.patient,
                )
            self.log(A.UPDATE, appointment)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        self.check_can_manage(self.get_object())
        return self.change_status(Appointment.Status.CANCELLED)

    @action(detail=True, methods=["post"], url_path="check-in")
    def check_in(self, request, pk=None):
        if not has_capability(request.user, "appointments.check_in"):
            raise PermissionDenied("Only the coordinator can check patients in.")
        return self.change_status(Appointment.Status.CHECKED_IN)

    @action(detail=True, methods=["post"], url_path="no-show")
    def no_show(self, request, pk=None):
        if not has_capability(request.user, "appointments.check_in"):
            raise PermissionDenied("Only the coordinator can mark a no-show.")
        return self.change_status(Appointment.Status.NO_SHOW)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        appointment = self.get_object()
        staff = get_staff_profile(request.user)
        is_doctor = staff is not None and staff.pk == appointment.staff_id
        if not (is_doctor or has_capability(request.user, "appointments.check_in")):
            raise PermissionDenied("Only the appointment's doctor or the coordinator can complete it.")
        return self.change_status(Appointment.Status.COMPLETED)
