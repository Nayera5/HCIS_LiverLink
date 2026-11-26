"""
Radiology API (module 7), mounted at /api/radiology/. Capabilities (apps/accounts/rbac.py):

    imaging.view         list and open imaging orders                     clinical staff (not super admin)
    imaging.order        create orders, cancel the ones they ordered      hepatologist, transplant_surgeon
    imaging.manage       scan slots; schedule, confirm, acquire, cancel   radiologist
    imaging.coordinate   remind the patient about the scan                coordinator
    self.imaging_orders  own orders: choose, move or cancel a slot        patients and donors

    orders/                        list, create
    orders/{id}/                   open
    orders/{id}/status/            scheduled (confirm) | acquired | cancelled
    orders/{id}/slots/             free slots for the order
    orders/{id}/booking/           book / move to a slot (confirmed at once)
    orders/{id}/booking/cancel/    orders/{id}/booking/no-show/
    orders/{id}/remind/
    my-orders/ , my-orders/{id}/slots|booking|booking/cancel/     the same for the patient's own orders
    slots/ , slots/{id}/           scan slots (a booked slot cannot be withdrawn or deleted)

Orders are never edited or deleted: a wrong order is cancelled. Every write is audited (see services.py).
"""
from django.db import transaction
from django.db.models import Exists, OuterRef, Prefetch
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.audit import audit
from apps.accounts.models import AuditLog, Staff
from apps.accounts.permissions import HasCapability
from apps.accounts.rbac import get_staff_profile, has_capability
from apps.billing.models import Invoice, InvoiceItem
from apps.notifications import events
from apps.scheduling.models import Appointment

from . import services
from .models import IMAGING_ROOM_NAMES, ImagingOrder, ImagingSlot
from .serializers import (
    AvailableSlotSerializer, ImagingOrderCreateSerializer, ImagingOrderSerializer, ImagingOrderStatusSerializer,
    ImagingSlotSerializer, MyImagingOrderSerializer, ReasonSerializer, SlotBatchSerializer, SlotChoiceSerializer,
)

A = AuditLog.Action
S = ImagingOrder.Status
V = Appointment.Status
SLOT_ENTITY = "radiology.imagingslot"


def live_bookings(to_attr):
    return Prefetch("appointments", to_attr=to_attr, queryset=services.slot_bookings().select_related(
        "patient", "imaging_order").order_by("appointment_id"))


def orders():
    billed = InvoiceItem.objects.filter(imaging_order=OuterRef("pk")).exclude(invoice__status=Invoice.Status.CANCELLED)
    return (ImagingOrder.objects.select_related("patient", "ordered_by__user", "encounter", "billing_service")
            .annotate(has_active_billing_invoice=Exists(billed))
            .prefetch_related(live_bookings("_bookings")))


def may_cancel(user):
    """Returns order -> bool: the doctor who ordered it, or a radiologist."""
    manages, orders_imaging = has_capability(user, "imaging.manage"), has_capability(user, "imaging.order")
    staff = get_staff_profile(user)
    return lambda order: manages or (orders_imaging and staff is not None and order.ordered_by_id == staff.pk)


def order_data(request, pk):
    return ImagingOrderSerializer(orders().get(pk=pk), context={"may_cancel": may_cancel(request.user)}).data


def date_param(params, name):
    value = params.get(name)
    if not value:
        return None
    try:
        day = parse_date(value)
    except ValueError:
        day = None
    if day is None:
        raise ValidationError({name: "Use the format YYYY-MM-DD."})
    return day


def id_param(params, name):
    value = params.get(name, "")
    if not value:
        return None
    if not (value.isascii() and value.isdigit() and len(value) <= 9):
        raise ValidationError({name: "Enter a valid id."})
    return int(value)


def validated(serializer_class, request):
    serializer = serializer_class(data=request.data)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


def lock_order(qs, pk):
    return get_object_or_404(qs.select_for_update(of=("self",)), pk=pk)


class Pagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


# ---------------------------------------------------------------- orders (staff)
class ImagingOrderListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/radiology/orders/?patient=&encounter=&status=&billing_service=&booking=none|pending   (imaging.view)
         `booking` finds open orders without a slot, or with a slot waiting for confirmation.
    POST /api/radiology/orders/  {patient, billing_service, clinical_indication, encounter?}
    """

    serializer_class = ImagingOrderSerializer
    pagination_class = Pagination

    def get_permissions(self):
        cap = "imaging.order" if self.request.method == "POST" else "imaging.view"
        return [IsAuthenticated(), HasCapability(cap)()]

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "may_cancel": may_cancel(self.request.user)}

    def get_queryset(self):
        qs, params = orders(), self.request.query_params
        for name in ("patient", "encounter", "billing_service"):
            value = id_param(params, name)
            if value is not None:
                qs = qs.filter(**{f"{name}_id": value})
        if params.get("status") in S.values:
            qs = qs.filter(status=params["status"])
        if params.get("booking") in ("none", "pending"):
            booked = Exists(services.slot_bookings(imaging_order=OuterRef("pk")))
            qs = qs.filter(booked if params["booking"] == "pending" else ~booked, status=S.ORDERED)
        return qs

    def create(self, request, *args, **kwargs):
        serializer = ImagingOrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        staff = get_staff_profile(request.user)
        if staff is None:
            raise PermissionDenied("Only doctors can order imaging.")
        with transaction.atomic():
            order = serializer.save(ordered_by=staff)
            audit(request, A.CREATE, services.ORDER, entity_id=order.pk, patient=order.patient)
            events.imaging_order_created(order)
        return Response(order_data(request, order.pk), status=status.HTTP_201_CREATED)


class ImagingOrderDetailView(APIView):
    """GET /api/radiology/orders/<id>/"""

    permission_classes = [IsAuthenticated, HasCapability("imaging.view")]

    def get(self, request, pk):
        get_object_or_404(ImagingOrder, pk=pk)
        return Response(order_data(request, pk))


class ImagingOrderStatusView(APIView):
    """POST /api/radiology/orders/<id>/status/  {status, reason?}"""

    permission_classes = [IsAuthenticated, HasCapability("imaging.order", "imaging.manage")]

    def post(self, request, pk):
        data = validated(ImagingOrderStatusSerializer, request)
        new_status = data["status"]
        with transaction.atomic():
            order = lock_order(ImagingOrder.objects, pk)
            allowed = (may_cancel(request.user)(order) if new_status == S.CANCELLED
                       else has_capability(request.user, "imaging.manage"))
            if not allowed:
                raise PermissionDenied("You cannot make this status change.")
            if not order.can_move_to(new_status):
                raise ValidationError({"status": f"An order that is {order.get_status_display().lower()} cannot be "
                                                 f"changed to {S(new_status).label.lower()}."})
            if new_status == S.SCHEDULED:
                services.confirm(request, order)
            elif new_status == S.ACQUIRED:
                services.acquire(request, order)
            else:
                services.cancel_order(request, order, data["reason"])
        return Response(order_data(request, pk))


class OrderSlotsView(APIView):
    """GET /api/radiology/orders/<id>/slots/?date=  free slots for the ordered service"""

    permission_classes = [IsAuthenticated, HasCapability("imaging.manage")]

    def orders(self):
        return ImagingOrder.objects.all()

    def get(self, request, pk):
        order = get_object_or_404(self.orders(), pk=pk)
        if order.status not in ImagingOrder.ACTIVE_STATUSES:
            return Response([])
        slots = services.available_slots(order)
        day = date_param(request.query_params, "date")
        if day:
            slots = slots.filter(start_time__date=day)
        return Response(AvailableSlotSerializer(slots[:200], many=True).data)


class OrderBookingView(APIView):
    """
    POST orders/<id>/booking/          {slot}     book, or move the booking; confirmed at once
    POST orders/<id>/booking/cancel/   {reason}   free the slot; the order goes back to ordered
    POST orders/<id>/booking/no-show/             same, after a missed appointment
    """

    permission_classes = [IsAuthenticated, HasCapability("imaging.manage")]
    action = "book"

    def post(self, request, pk):
        slot = validated(SlotChoiceSerializer, request)["slot"] if self.action == "book" else None
        reason = validated(ReasonSerializer, request)["reason"] if self.action == "cancel" else ""
        with transaction.atomic():
            order = lock_order(ImagingOrder.objects, pk)
            if self.action == "book":
                services.book(request, order, slot)
            else:
                services.release(request, order, V.CANCELLED if self.action == "cancel" else V.NO_SHOW, reason=reason)
        return Response(order_data(request, pk))


class OrderRemindView(APIView):
    """POST /api/radiology/orders/<id>/remind/  coordinator reminds the patient (at most once a day per order)."""

    permission_classes = [IsAuthenticated, HasCapability("imaging.coordinate")]

    def post(self, request, pk):
        with transaction.atomic():
            order = lock_order(ImagingOrder.objects, pk)
            if order.status not in ImagingOrder.ACTIVE_STATUSES:
                raise ValidationError({"detail": "This order is closed."})
            user = order.patient.user
            if user is None or not user.is_active:
                raise ValidationError({"detail": "The patient has no active portal account: contact them by phone."})
            if not events.imaging_coordinator_reminder(order, services.active_booking(order, lock=False)):
                raise ValidationError({"detail": "The patient was already notified about this order today."})
            audit(request, A.CREATE, "notifications.notification", entity_id=order.pk, patient=order.patient,
                  reason=f"Reminder for imaging order #{order.pk}")
        return Response({"detail": "Reminder sent."})


# ---------------------------------------------------------------- own orders (patient portal)
def own_orders(request):
    return ImagingOrder.objects.filter(patient__user=request.user)


class MyOrdersView(APIView):
    """GET /api/radiology/my-orders/"""

    permission_classes = [IsAuthenticated, HasCapability("self.imaging_orders")]

    def get(self, request):
        return Response(MyImagingOrderSerializer(orders().filter(patient__user=request.user), many=True).data)


class MyOrderSlotsView(OrderSlotsView):
    permission_classes = [IsAuthenticated, HasCapability("self.imaging_orders")]

    def orders(self):
        return own_orders(self.request)


class MyOrderBookingView(APIView):
    """POST my-orders/<id>/booking/ {slot} (choose or move) | my-orders/<id>/booking/cancel/"""

    permission_classes = [IsAuthenticated, HasCapability("self.imaging_orders")]
    action = "book"

    def post(self, request, pk):
        slot = validated(SlotChoiceSerializer, request)["slot"] if self.action == "book" else None
        with transaction.atomic():
            order = lock_order(own_orders(request), pk)
            if self.action == "book":
                services.book(request, order, slot, by_patient=True)
            else:
                services.release(request, order, V.CANCELLED, by_patient=True)
        return Response(MyImagingOrderSerializer(orders().get(pk=pk)).data)


# ---------------------------------------------------------------- scan slots (radiologist)
class ImagingRoomChoicesView(APIView):
    """GET /api/radiology/rooms/  room choices for scan slot creation."""

    permission_classes = [IsAuthenticated, HasCapability("imaging.manage")]

    def get(self, request):
        return Response([{"value": room, "label": room} for room in IMAGING_ROOM_NAMES])


def slots():
    return ImagingSlot.objects.select_related("billing_service").prefetch_related(live_bookings("live_bookings"))


class ImagingSlotListCreateView(generics.ListAPIView):
    """
    GET  /api/radiology/slots/?billing_service=&date_from=&date_to=
    POST /api/radiology/slots/  {billing_service, resource_name?, date, start_time, end_time, slot_minutes, is_published}
    """

    serializer_class = ImagingSlotSerializer
    permission_classes = [IsAuthenticated, HasCapability("imaging.manage")]
    pagination_class = Pagination

    def get_queryset(self):
        qs, params = slots(), self.request.query_params
        service = id_param(params, "billing_service")
        if service is not None:
            qs = qs.filter(billing_service_id=service)
        date_from, date_to = date_param(params, "date_from"), date_param(params, "date_to")
        if date_from:
            qs = qs.filter(start_time__date__gte=date_from)
        if date_to:
            qs = qs.filter(start_time__date__lte=date_to)
        return qs

    def post(self, request):
        data = validated(SlotBatchSerializer, request)
        times, service, resource_name = data["times"], data["billing_service"], data["resource_name"]
        with transaction.atomic():
            # Serialises slot creation, so two radiologists cannot add overlapping slots at once.
            list(Staff.objects.select_for_update(no_key=True)
                 .filter(job_title=Staff.JobTitle.RADIOLOGIST).order_by("pk"))
            overlapping = ImagingSlot.objects.filter(resource_name=resource_name, start_time__lt=times[-1][1],
                                                     end_time__gt=times[0][0])
            if not resource_name:  # no named resource: only the same service is known to share it
                overlapping = overlapping.filter(billing_service=service)
            if overlapping.exists():
                raise ValidationError({"start_time": "These hours overlap existing slots for this resource."})
            staff = get_staff_profile(request.user)
            created = [ImagingSlot.objects.create(
                billing_service=service, resource_name=resource_name, start_time=start, end_time=end,
                created_by=staff, is_published=data["is_published"],
            ) for start, end in times]
            for slot in created:
                audit(request, A.CREATE, SLOT_ENTITY, entity_id=slot.pk)
        rows = slots().filter(pk__in=[slot.pk for slot in created])
        return Response(ImagingSlotSerializer(rows, many=True).data, status=status.HTTP_201_CREATED)


class ImagingSlotDetailView(APIView):
    """PATCH {is_published} publish / withdraw; DELETE a slot that was never booked."""

    permission_classes = [IsAuthenticated, HasCapability("imaging.manage")]

    def lock(self, pk):
        slot = get_object_or_404(ImagingSlot.objects.select_for_update(), pk=pk)
        if services.slot_bookings(imaging_slot=slot).exists():
            raise ValidationError({"detail": "This slot is booked: move or cancel the booking first."})
        return slot

    @transaction.atomic
    def patch(self, request, pk):
        slot = self.lock(pk)
        serializer = ImagingSlotSerializer(slot, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        old, new = slot.is_published, serializer.validated_data.get("is_published", slot.is_published)
        if old != new:
            slot.is_published = new
            slot.save(update_fields=["is_published"])
            audit(request, A.UPDATE, SLOT_ENTITY, entity_id=pk, changes={"is_published": {"from": old, "to": new}})
        return Response(ImagingSlotSerializer(slots().get(pk=pk)).data)

    @transaction.atomic
    def delete(self, request, pk):
        slot = self.lock(pk)
        if slot.appointments.exists():
            raise ValidationError({"detail": "This slot was used by an earlier booking: withdraw it instead."})
        slot.delete()
        audit(request, A.DELETE, SLOT_ENTITY, entity_id=pk)
        return Response(status=status.HTTP_204_NO_CONTENT)
