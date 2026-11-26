"""Imaging order, scan slot and booking API tests (module 7, stage 1)."""
import datetime
from unittest import mock

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import AuditLog
from apps.billing.models import InvoiceItem, Service
from apps.emr.models import Encounter
from apps.notifications.models import Notification
from apps.notifications.tasks import send_appointment_reminders
from apps.registry.test_api import PatientAPITestBase
from apps.scheduling.models import Appointment

from . import services
from .models import ImagingOrder, ImagingSlot

URL = "/api/radiology/orders/"
MY = "/api/radiology/my-orders/"
SLOTS = "/api/radiology/slots/"
ROOMS = "/api/radiology/rooms/"
APPT = "/api/scheduling/appointments/"


class RadiologyTestBase(PatientAPITestBase):
    """`own` is the patient with a portal account (pat_user); `other` has none."""

    def setUp(self):
        super().setUp()
        self.encounter = Encounter.objects.create(patient=self.other, staff=self.hep.staff_profile)
        self.slot_count = 0
        self.service, self.other_service = Service.objects.filter(
            category="imaging", is_active=True).order_by("code")[:2]

    def call(self, user, url, data=None, method="post"):
        self.as_(user)
        return getattr(self.client, method)(url, data or {}, format="json")

    def post(self, user=None, **over):
        data = {"patient": self.other.pk, "billing_service": self.service.pk,
                "clinical_indication": "Suspected HCC, rising AFP"}
        data.update(over)
        return self.call(user or self.hep, URL, data)

    def create(self, **over):
        r = self.post(**over)
        self.assertEqual(r.status_code, 201, r.data)
        return r.data["imaging_order_id"]

    def own_order(self, **over):
        return self.create(patient=self.own.pk, **over)

    def slot(self, service=None, start=None, published=True):
        self.slot_count += 1  # a new time each call
        start = start or timezone.now() + datetime.timedelta(days=self.slot_count)
        return ImagingSlot.objects.create(
            billing_service=service or self.service, start_time=start, end_time=start + datetime.timedelta(minutes=30),
            is_published=published, created_by=self.rad.staff_profile)

    def move(self, user, pk, status, **extra):
        return self.call(user, f"{URL}{pk}/status/", {"status": status, **extra})

    def book(self, pk, slot, user=None):
        """By the radiologist (default), or by the patient."""
        base = MY if user == self.pat_user else URL
        return self.call(user or self.rad, f"{base}{pk}/booking/", {"slot": slot.pk})

    def ok(self, response, code=200):
        self.assertEqual(response.status_code, code, response.data)
        return response.data

    def order(self, pk):
        return ImagingOrder.objects.get(pk=pk)

    def appointment(self, pk):
        return Appointment.objects.filter(imaging_order_id=pk).latest("appointment_id")


class ImagingOrderTests(RadiologyTestBase):
    # --- create
    def test_doctors_create(self):
        for user in (self.hep, self.surg):
            data = self.ok(self.post(user, encounter=self.encounter.pk), 201)
            self.assertEqual(data["ordered_by"], user.staff_profile.pk)
            self.assertEqual((data["status"], data["booking_state"]), ("ordered", "none"))
            self.assertEqual(data["encounter"], self.encounter.pk)
            self.assertIsNone(data["appointment"])
        log = AuditLog.objects.filter(entity_type="radiology.imagingorder", action="create")
        self.assertEqual(log.count(), 2)
        self.assertEqual(log.first().patient, self.other)

    def test_others_cannot_create(self):
        for user in (self.root, self.admin, self.coord, self.rad, self.billing, self.nojob, self.pat_user):
            with self.subTest(user=user.username):
                self.assertEqual(self.post(user).status_code, 403)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.post(URL, {}).status_code, 401)

    def test_server_fields_cannot_be_set(self):
        order = self.order(self.create(status="acquired", ordered_by=self.surg.staff_profile.pk))
        self.assertEqual((order.status, order.ordered_by), ("ordered", self.hep.staff_profile))

    def test_invalid_fields(self):
        for field, value in (("patient", 99999), ("billing_service", 99999), ("billing_service", "ct"),
                             ("clinical_indication", "   "), ("clinical_indication", "x" * 2001),
                             ("encounter", 99999)):
            with self.subTest(field=field):
                r = self.post(**{field: value})
                self.assertEqual(r.status_code, 400)
                self.assertIn(field, r.data)

    def test_billing_service_must_be_active_and_imaging(self):
        inactive = Service.objects.create(code="IMG-INACTIVE", name="Inactive imaging", category="imaging",
                                          price=100, is_active=False)
        consultation = Service.objects.create(code="CONS-TEST", name="Consultation", category="consultation",
                                              price=100)
        for service in (inactive, consultation):
            with self.subTest(service=service.code):
                response = self.post(billing_service=service.pk)
                self.assertEqual(response.status_code, 400)
                self.assertIn("billing_service", response.data)

    def test_new_active_imaging_service_is_listed_and_preserved_on_order(self):
        active = Service.objects.create(
            code="IMG-DYNAMIC", name="New Dynamic Imaging Service", category="imaging", price="1250.00",
        )
        inactive = Service.objects.create(
            code="IMG-INACTIVE", name="Inactive Imaging Service", category="imaging",
            price="900.00", is_active=False,
        )
        response = self.call(
            self.hep, "/api/services/?category=imaging&active_only=true&page_size=100", method="get",
        )
        self.assertEqual(response.status_code, 200, response.data)
        services = {row["id"]: row for row in response.data["results"]}
        self.assertIn(active.pk, services)
        self.assertNotIn(inactive.pk, services)
        self.assertEqual(
            (services[active.pk]["code"], services[active.pk]["name"], services[active.pk]["price"]),
            ("IMG-DYNAMIC", "New Dynamic Imaging Service", "1250.00"),
        )

        order = self.ok(self.post(billing_service=active.pk), 201)
        self.assertEqual(order["billing_service_code"], active.code)
        self.assertEqual(self.order(order["imaging_order_id"]).billing_service, active)

    def test_dropdown_source_is_exactly_the_active_imaging_services(self):
        Service.objects.create(code="IMG-X", name="Anything new", category="imaging", price=1)
        Service.objects.create(code="IMG-OFF", name="Off", category="imaging", price=1, is_active=False)
        expected = set(Service.objects.filter(category="imaging", is_active=True).values_list("pk", flat=True))
        for user in (self.hep, self.surg, self.rad):
            rows = self.call(user, "/api/services/?category=imaging&active_only=true&page_size=100", method="get")
            self.assertEqual({row["id"] for row in rows.data["results"]}, expected)
        # The order API accepts exactly that list.
        for service in Service.objects.all():
            self.assertEqual(self.post(billing_service=service.pk).status_code,
                             201 if service.pk in expected else 400, service.code)

    def test_service_is_required_and_old_fields_are_gone(self):
        for extra in ({}, {"billing_service": None}):
            r = self.call(self.hep, URL, {"patient": self.other.pk, "modality": "ct", "body_area": "liver",
                                          "clinical_indication": "x", **extra})
            self.assertEqual(r.status_code, 400)
            self.assertEqual(set(r.data), {"billing_service"})
        data = self.ok(self.post(), 201)
        self.assertEqual((data["billing_service"], data["billing_service_name"]),
                         (self.service.pk, self.service.name))
        self.assertFalse({"modality", "body_area"} & set(data))

    def test_encounter_must_belong_to_the_patient(self):
        foreign = Encounter.objects.create(patient=self.own, staff=self.hep.staff_profile)
        self.assertIn("encounter", self.post(encounter=foreign.pk).data)
        self.assertEqual(ImagingOrder.objects.count(), 0)

    def test_open_encounter_can_still_be_deleted(self):
        pk = self.create(encounter=self.encounter.pk)
        self.assertEqual(self.client.delete(f"/api/emr/encounters/{self.encounter.pk}/").status_code, 204)
        self.assertIsNone(self.order(pk).encounter)

    # --- read
    def test_read_access(self):
        pk = self.create()
        for user in (self.coord, self.hep, self.rad, self.surg):
            with self.subTest(user=user.username):
                self.assertEqual(self.ok(self.call(user, URL, method="get"))["count"], 1)
                self.ok(self.call(user, f"{URL}{pk}/", method="get"))
        # Super admin gets no clinical access automatically.
        for user in (self.root, self.admin, self.billing, self.nojob, self.pat_user):
            with self.subTest(user=user.username):
                self.assertEqual(self.call(user, URL, method="get").status_code, 403)
                self.assertEqual(self.call(user, f"{URL}{pk}/", method="get").status_code, 403)

    def test_filters(self):
        self.create(encounter=self.encounter.pk)
        self.create(billing_service=self.other_service.pk, patient=self.own.pk)
        for query, count in ((f"patient={self.own.pk}", 1), (f"encounter={self.encounter.pk}", 1),
                             (f"billing_service={self.other_service.pk}", 1), ("status=ordered", 2), ("status=acquired", 0)):
            with self.subTest(query=query):
                self.assertEqual(self.client.get(f"{URL}?{query}").data["count"], count)
        self.assertEqual(self.client.get(f"{URL}?patient=abc").status_code, 400)

    def test_booking_filter(self):
        unbooked, patient_booked, radiologist_booked = self.own_order(), self.own_order(), self.own_order()
        self.ok(self.book(patient_booked, self.slot(), self.pat_user))
        self.ok(self.book(radiologist_booked, self.slot()))
        unbooked_rows = self.call(self.coord, f"{URL}?booking=none", method="get").data["results"]
        self.assertEqual([row["imaging_order_id"] for row in unbooked_rows], [unbooked])
        pending_rows = self.call(self.coord, f"{URL}?booking=pending", method="get").data["results"]
        self.assertEqual(pending_rows, [])
        self.assertEqual(self.order(patient_booked).status, ImagingOrder.Status.SCHEDULED)

    def test_list_query_count_does_not_grow(self):
        for _ in range(3):
            self.ok(self.book(self.create(), self.slot()))
        self.as_(self.rad)
        with self.assertNumQueries(3):  # count, orders, bookings
            self.client.get(URL)

    def test_no_edit_or_delete(self):
        pk = self.create()
        for method in ("put", "patch", "delete"):
            self.assertEqual(getattr(self.client, method)(f"{URL}{pk}/").status_code, 405)

    # --- status
    def test_transition_matrix(self):
        allowed = {("ordered", "scheduled"), ("ordered", "acquired"), ("ordered", "cancelled"),
                   ("scheduled", "acquired"), ("scheduled", "cancelled")}
        start = timezone.now() + datetime.timedelta(seconds=90)
        for old in ImagingOrder.Status.values:
            for new in ImagingOrder.Status.values:
                with self.subTest(old=old, new=new):
                    pk = self.create()
                    start += datetime.timedelta(days=0, hours=1)
                    self.ok(self.book(pk, self.slot(start=start)))
                    ImagingOrder.objects.filter(pk=pk).update(status=old)
                    with mock.patch.object(services.timezone, "localdate", return_value=start.date()):
                        r = self.move(self.rad, pk, new, reason="test")
                    self.assertEqual(r.status_code, 200 if (old, new) in allowed else 400, r.data)

    def test_status_permissions(self):
        pk = self.create()
        self.ok(self.book(pk, self.slot()))
        for user in (self.hep, self.surg, self.coord, self.admin, self.root, self.billing, self.pat_user):
            for status in ("scheduled", "acquired"):
                with self.subTest(user=user.username, status=status):
                    self.assertEqual(self.move(user, pk, status).status_code, 403)
        self.assertEqual(self.order(pk).status, "scheduled")

    def test_cancel_permissions(self):
        pk = self.create()  # by hep
        for user in (self.surg, self.coord, self.admin, self.root, self.billing, self.pat_user):
            with self.subTest(user=user.username):
                self.assertEqual(self.move(user, pk, "cancelled", reason="x").status_code, 403)
        self.assertTrue(self.call(self.hep, f"{URL}{pk}/", method="get").data["can_cancel"])
        self.assertFalse(self.call(self.surg, f"{URL}{pk}/", method="get").data["can_cancel"])
        self.ok(self.move(self.hep, pk, "cancelled", reason="Duplicate"))
        self.ok(self.move(self.rad, self.create(), "cancelled", reason="Contraindicated"))

    def test_cancel_needs_reason(self):
        pk = self.create()
        for user in (self.hep, self.rad):
            self.assertIn("reason", self.move(user, pk, "cancelled", reason=" ").data)
        self.ok(self.move(self.rad, pk, "cancelled", reason="Scanner down"))
        log = AuditLog.objects.get(entity_type="radiology.imagingorder", action="status_change")
        self.assertEqual((log.reason, log.user), ("Scanner down", self.rad))

    def test_unknown_order(self):
        self.assertEqual(self.move(self.rad, 99999, "acquired").status_code, 404)

    def test_database_constraints(self):
        for extra in ({}, {"billing_service": self.service, "status": "bad"}):
            with self.subTest(extra=extra), self.assertRaises(IntegrityError), transaction.atomic():
                ImagingOrder.objects.create(patient=self.other, ordered_by=self.hep.staff_profile,
                                            clinical_indication="x", **extra)


class ScanSlotTests(RadiologyTestBase):
    def payload(self, **over):
        day = timezone.localdate() + datetime.timedelta(days=5)
        return {"billing_service": self.service.pk, "resource_name": "CT Room 1", "date": day.isoformat(),
                "start_time": "09:00", "end_time": "11:00", "slot_minutes": 30, **over}

    def test_room_choices_are_available_to_radiologists_only(self):
        self.assertEqual(self.call(self.rad, ROOMS, method="get").data, [
            {"value": "CT Room 1", "label": "CT Room 1"},
            {"value": "CT Room 2", "label": "CT Room 2"},
        ])
        for user in (self.root, self.admin, self.coord, self.hep, self.surg, self.billing, self.nojob, self.pat_user):
            with self.subTest(user=user.username):
                self.assertEqual(self.call(user, ROOMS, method="get").status_code, 403)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(ROOMS).status_code, 401)

    def test_only_radiologist_manages_slots(self):
        slot = self.slot()
        for user in (self.root, self.admin, self.coord, self.hep, self.surg, self.billing, self.nojob, self.pat_user):
            with self.subTest(user=user.username):
                self.assertEqual(self.call(user, SLOTS, method="get").status_code, 403)
                self.assertEqual(self.call(user, SLOTS, self.payload()).status_code, 403)
                for method in ("patch", "delete"):
                    self.assertEqual(self.call(user, f"{SLOTS}{slot.pk}/", method=method).status_code, 403)
        self.assertEqual(ImagingSlot.objects.count(), 1)

    def test_create_splits_hours(self):
        data = self.ok(self.call(self.rad, SLOTS, self.payload()), 201)
        self.assertEqual(len(data), 4)
        self.assertTrue(all(row["is_published"] and row["booking"] is None for row in data))
        self.assertEqual(AuditLog.objects.filter(entity_type="radiology.imagingslot", action="create").count(), 4)
        listing = self.call(self.rad, f"{SLOTS}?billing_service={self.service.pk}&date_from={self.payload()['date']}", method="get")
        self.assertEqual(listing.data["count"], 4)

    def test_same_resource_cannot_overlap(self):
        self.ok(self.call(self.rad, SLOTS, self.payload()), 201)
        overlapping = self.payload(start_time="10:45", end_time="12:00", slot_minutes=15)
        self.assertEqual(self.call(self.rad, SLOTS, overlapping).status_code, 400)
        self.ok(self.call(self.rad, SLOTS, self.payload(
            billing_service=self.other_service.pk, resource_name="CT Room 2")), 201)
        self.ok(self.call(self.rad, SLOTS, self.payload(start_time="11:00", end_time="12:00")), 201)

    def test_distinct_resources_can_run_same_service_at_the_same_time(self):
        day = self.payload()["date"]
        first = self.payload(date=day, resource_name="CT Room 1")
        second = self.payload(date=day, resource_name="CT Room 2")
        self.assertEqual(self.call(self.rad, SLOTS, first).status_code, 201)
        data = self.ok(self.call(self.rad, SLOTS, second), 201)
        self.assertEqual({row["resource_name"] for row in data}, {"CT Room 2"})
        conflict = self.payload(date=day, resource_name="CT Room 1", start_time="10:45", end_time="12:00",
                                slot_minutes=15)
        self.assertEqual(self.call(self.rad, SLOTS, conflict).status_code, 400)
        conflict["billing_service"] = self.other_service.pk  # one room cannot run two services at once
        self.assertEqual(self.call(self.rad, SLOTS, conflict).status_code, 400)

    def test_validation(self):
        past = (timezone.localdate() - datetime.timedelta(days=1)).isoformat()
        missing_room = self.payload()
        missing_room.pop("resource_name")
        for payload in (missing_room, self.payload(resource_name=""), self.payload(resource_name="MRI Room 1")):
            with self.subTest(payload=payload):
                self.assertEqual(self.call(self.rad, SLOTS, payload).status_code, 400)
        for over in ({"billing_service": "ct"},
                     {"billing_service": Service.objects.filter(category="consultation").first().pk}, {"date": past}, {"end_time": "08:00"}, {"slot_minutes": 0},
                     {"slot_minutes": 200}, {"date": "x"}):
            with self.subTest(over=over):
                self.assertEqual(self.call(self.rad, SLOTS, self.payload(**over)).status_code, 400)
        self.assertEqual(self.call(self.rad, f"{SLOTS}?date_from=2026-13-45", method="get").status_code, 400)

    def test_publish_and_withdraw(self):
        pk, slot = self.own_order(), self.slot(published=False)
        url = f"{MY}{pk}/slots/"
        self.assertEqual(self.call(self.pat_user, url, method="get").data, [])
        self.assertEqual(self.book(pk, slot, self.pat_user).status_code, 400)
        self.ok(self.call(self.rad, f"{SLOTS}{slot.pk}/", {"is_published": True}, "patch"))
        self.assertEqual(len(self.call(self.pat_user, url, method="get").data), 1)
        log = AuditLog.objects.get(entity_type="radiology.imagingslot", action="update")
        self.assertEqual(log.changes, {"is_published": {"from": False, "to": True}})

    def test_booked_slot_cannot_be_withdrawn_or_deleted(self):
        pk, slot = self.create(), self.slot()
        self.ok(self.book(pk, slot))
        url = f"{SLOTS}{slot.pk}/"
        self.assertEqual(self.call(self.rad, url, {"is_published": False}, "patch").status_code, 400)
        self.assertEqual(self.call(self.rad, url, method="delete").status_code, 400)
        self.ok(self.call(self.rad, f"{URL}{pk}/booking/cancel/", {"reason": "Scanner down"}))
        self.assertEqual(self.call(self.rad, url, method="delete").status_code, 400)  # kept for history
        self.ok(self.call(self.rad, url, {"is_published": False}, "patch"))
        self.assertEqual(self.call(self.rad, f"{SLOTS}{self.slot().pk}/", method="delete").status_code, 204)


class PatientBookingTests(RadiologyTestBase):
    def test_full_flow(self):
        service = Service.objects.create(
            code="IMG-DYNAMIC", name="New Dynamic Imaging Service", category="imaging", price="1375.50",
        )
        pk, slot = self.own_order(billing_service=service.pk), self.slot(service)
        rows = self.call(self.pat_user, f"{MY}{pk}/slots/", method="get").data
        self.assertEqual([row["slot_id"] for row in rows], [slot.pk])
        data = self.ok(self.book(pk, slot, self.pat_user))
        self.assertEqual((data["status"], data["booking_state"]), ("scheduled", "confirmed"))
        appointment = self.appointment(pk)
        self.assertEqual((appointment.appointment_type, appointment.staff, appointment.imaging_slot,
                          appointment.start_time, appointment.booked_by),
                         ("imaging", None, slot, slot.start_time, self.pat_user))
        with mock.patch.object(services.timezone, "localdate", return_value=slot.start_time.date()):
            data = self.ok(self.move(self.rad, pk, "acquired"))
        self.assertEqual((data["status"], data["appointment_status"], data["billing_state"]),
                         ("acquired", "completed", "invoiced"))
        item = InvoiceItem.objects.get(imaging_order_id=pk)
        self.assertEqual((item.service, item.appointment, str(item.unit_price)),
                         (service, appointment, str(service.price)))
        service.price = "1999.00"
        service.save(update_fields=["price"])
        item.refresh_from_db()
        self.assertEqual(str(item.unit_price), "1375.50")
        order = self.order(pk)
        from apps.billing.services import invoice_for_imaging_order
        self.assertIsNone(invoice_for_imaging_order(order, appointment))
        self.assertEqual(self.move(self.rad, pk, "acquired").status_code, 400)
        self.assertEqual(InvoiceItem.objects.filter(imaging_order_id=pk).count(), 1)
        with self.assertRaises(IntegrityError), transaction.atomic():
            InvoiceItem.objects.create(
                invoice=item.invoice, service=service, imaging_order=order, appointment=appointment,
                unit_price=service.price,
            )
        self.assertEqual(AuditLog.objects.filter(entity_type="scheduling.appointment", action="create").count(), 1)
        changes = [log.changes["status"] for log in AuditLog.objects.filter(
            entity_type="radiology.imagingorder", action="status_change")]
        self.assertCountEqual(changes, [{"from": "ordered", "to": "scheduled"}, {"from": "scheduled", "to": "acquired"}])

    def test_acquired_scan_with_deactivated_service_is_flagged_and_not_invoiced(self):
        pk = self.create(patient=self.own.pk)
        Service.objects.filter(pk=self.service.pk).update(is_active=False)
        with self.assertLogs("apps.billing.services", "WARNING"):
            data = self.ok(self.move(self.rad, pk, "acquired"))
        self.assertEqual(data["billing_state"], "needs_service")
        self.assertFalse(InvoiceItem.objects.filter(imaging_order_id=pk).exists())

    def test_patient_booking_is_confirmed_and_notified_immediately(self):
        pk, slot = self.own_order(), self.slot()
        data = self.ok(self.book(pk, slot, self.pat_user))
        self.assertEqual((data["status"], data["booking_state"]), ("scheduled", "confirmed"))
        self.assertTrue(Notification.objects.filter(user=self.pat_user, title="Scan appointment confirmed").exists())

    def test_patient_sees_only_own_orders(self):
        foreign, mine, slot = self.create(), self.own_order(), self.slot()
        rows = self.ok(self.call(self.pat_user, MY, method="get"))
        self.assertEqual([row["imaging_order_id"] for row in rows], [mine])
        self.assertNotIn("clinical_indication", rows[0])
        self.assertEqual(self.call(self.pat_user, f"{MY}{foreign}/slots/", method="get").status_code, 404)
        self.assertEqual(self.book(foreign, slot, self.pat_user).status_code, 404)
        self.ok(self.book(foreign, slot))
        self.assertEqual(self.call(self.pat_user, f"{MY}{foreign}/booking/cancel/").status_code, 404)
        self.assertEqual(self.appointment(foreign).status, "booked")

    def test_patient_cannot_use_staff_endpoints(self):
        pk, slot = self.own_order(), self.slot()
        for path, data in (("booking/", {"slot": slot.pk}), ("booking/cancel/", {"reason": "x"}),
                           ("booking/no-show/", {}), ("remind/", {}), ("status/", {"status": "scheduled"})):
            self.assertEqual(self.call(self.pat_user, f"{URL}{pk}/{path}", data).status_code, 403, path)
        self.assertEqual(self.call(self.pat_user, f"{URL}{pk}/slots/", method="get").status_code, 403)

    def test_staff_cannot_use_patient_endpoints(self):
        pk, slot = self.own_order(), self.slot()
        for user in (self.root, self.coord, self.hep, self.rad, self.billing):
            self.assertEqual(self.call(user, MY, method="get").status_code, 403)
            self.assertEqual(self.call(user, f"{MY}{pk}/booking/", {"slot": slot.pk}).status_code, 403)

    def test_only_matching_free_future_slots(self):
        pk = self.own_order()
        wrong_type = self.slot(self.other_service)
        past = self.slot(start=timezone.now() - datetime.timedelta(hours=1))
        self.assertEqual(self.call(self.pat_user, f"{MY}{pk}/slots/", method="get").data, [])
        for slot in (wrong_type, past):
            self.assertIn("slot", self.book(pk, slot, self.pat_user).data)
            self.assertIn("slot", self.book(pk, slot).data)
        for bad in ("x", None, 99999):
            self.assertEqual(self.call(self.pat_user, f"{MY}{pk}/booking/", {"slot": bad}).status_code, 400)
        self.assertEqual(Appointment.objects.count(), 0)

    def test_slots_by_date(self):
        pk, slot = self.own_order(), self.slot()
        self.slot()
        url = f"{MY}{pk}/slots/?date={slot.start_time.date()}"
        self.assertEqual([row["slot_id"] for row in self.call(self.pat_user, url, method="get").data], [slot.pk])

    def test_no_double_booking(self):
        slot = self.slot()
        self.ok(self.book(self.create(), slot))
        pk = self.own_order()
        self.assertEqual(self.call(self.pat_user, f"{MY}{pk}/slots/", method="get").data, [])
        self.assertIn("slot", self.book(pk, slot, self.pat_user).data)
        self.assertEqual(Appointment.objects.filter(imaging_slot=slot).count(), 1)

    def test_database_refuses_double_booking(self):
        first, slot = self.create(), self.slot()
        self.ok(self.book(first, slot))
        for order, other_slot in ((self.create(), slot), (first, self.slot())):
            with self.assertRaises(IntegrityError), transaction.atomic():
                Appointment.objects.create(patient=self.other, booked_by=self.rad, appointment_type="imaging",
                                           imaging_order_id=order, imaging_slot=other_slot,
                                           start_time=other_slot.start_time, end_time=other_slot.end_time)

    def test_lost_race_is_a_clean_error(self):
        slot, pk = self.slot(), self.own_order()
        self.ok(self.book(self.create(), slot))
        with mock.patch.object(services, "slot_bookings") as hidden:  # as if not visible yet
            hidden.return_value = Appointment.objects.none()
            r = self.call(self.pat_user, f"{MY}{pk}/booking/", {"slot": slot.pk})
        self.assertEqual((r.status_code, "slot" in r.data), (400, True))

    def test_patient_cannot_be_in_two_places(self):
        start = timezone.now() + datetime.timedelta(days=30)
        Appointment.objects.create(patient=self.own, staff=self.hep.staff_profile, booked_by=self.coord,
                                   appointment_type="consultation", start_time=start,
                                   end_time=start + datetime.timedelta(minutes=30))
        r = self.book(self.own_order(), self.slot(start=start + datetime.timedelta(minutes=10)), self.pat_user)
        self.assertIn("slot", r.data)

    def test_reschedule_by_patient_needs_confirmation_again(self):
        pk, first, second = self.own_order(), self.slot(), self.slot()
        self.ok(self.book(pk, first, self.pat_user))
        data = self.ok(self.book(pk, second, self.pat_user))
        self.assertEqual((data["status"], data["booking_state"]), ("scheduled", "confirmed"))
        appointment = Appointment.objects.get(imaging_order_id=pk)  # moved, not duplicated
        self.assertEqual((appointment.imaging_slot, appointment.start_time), (second, second.start_time))
        log = AuditLog.objects.get(entity_type="scheduling.appointment", action="update")
        self.assertEqual(log.changes["imaging_slot"], {"from": first.pk, "to": second.pk})
        self.ok(self.book(self.create(), first))  # the old slot is free again
        self.assertIn("slot", self.book(pk, second, self.pat_user).data)  # same slot again

    def test_cancel_by_patient(self):
        pk, slot = self.own_order(), self.slot()
        self.assertEqual(self.call(self.pat_user, f"{MY}{pk}/booking/cancel/").status_code, 400)  # nothing booked
        self.ok(self.book(pk, slot, self.pat_user))
        data = self.ok(self.call(self.pat_user, f"{MY}{pk}/booking/cancel/"))
        self.assertEqual((data["status"], data["booking_state"]), ("ordered", "none"))
        self.assertEqual(self.appointment(pk).status, "cancelled")
        self.ok(self.book(pk, slot, self.pat_user))  # can be booked again, history kept
        self.assertEqual(Appointment.objects.filter(imaging_order_id=pk).count(), 2)

    def test_patient_cannot_change_after_check_in_or_start(self):
        pk = self.own_order()
        self.ok(self.book(pk, self.slot(), self.pat_user))
        other = self.slot()
        Appointment.objects.update(status="checked_in")
        for _ in range(2):
            self.assertEqual(self.book(pk, other, self.pat_user).status_code, 400)
            self.assertEqual(self.call(self.pat_user, f"{MY}{pk}/booking/cancel/").status_code, 400)
            past = timezone.now() - datetime.timedelta(minutes=5)
            Appointment.objects.update(status="booked", start_time=past)

    def test_closed_orders_cannot_be_booked(self):
        pk, slot = self.own_order(), self.slot()
        for status in ("acquired", "cancelled"):
            ImagingOrder.objects.filter(pk=pk).update(status=status)
            self.assertEqual(self.call(self.pat_user, f"{MY}{pk}/slots/", method="get").data, [])
            self.assertEqual(self.book(pk, slot, self.pat_user).status_code, 400)
            self.assertEqual(self.book(pk, slot).status_code, 400)


class StaffBookingTests(RadiologyTestBase):
    def test_radiologist_schedules_for_the_patient(self):
        pk, slot = self.create(), self.slot()
        data = self.ok(self.book(pk, slot))
        self.assertEqual((data["status"], data["booking_state"]), ("scheduled", "confirmed"))
        data = self.ok(self.book(pk, self.slot()))  # moved by the radiologist: stays confirmed
        self.assertEqual(data["status"], "scheduled")
        self.assertEqual(Appointment.objects.count(), 1)

    def test_only_radiologist(self):
        pk, slot = self.create(), self.slot()
        for user in (self.root, self.admin, self.coord, self.hep, self.surg, self.billing):
            for path, data in (("booking/", {"slot": slot.pk}), ("booking/cancel/", {"reason": "x"}),
                               ("booking/no-show/", {})):
                with self.subTest(user=user.username, path=path):
                    self.assertEqual(self.call(user, f"{URL}{pk}/{path}", data).status_code, 403)

    def test_confirm_needs_a_booking(self):
        pk = self.create()
        self.assertIn("status", self.move(self.rad, pk, "scheduled").data)
        self.assertEqual(self.order(pk).status, "ordered")

    def test_cancel_booking_needs_reason(self):
        pk = self.own_order()
        self.ok(self.book(pk, self.slot()))
        self.assertIn("reason", self.call(self.rad, f"{URL}{pk}/booking/cancel/").data)
        data = self.ok(self.call(self.rad, f"{URL}{pk}/booking/cancel/", {"reason": "Scanner down"}))
        self.assertEqual((data["status"], data["booking_state"]), ("ordered", "none"))
        log = AuditLog.objects.filter(entity_type="scheduling.appointment", action="status_change").get()
        self.assertEqual(log.reason, "Scanner down")

    def test_cancelling_the_order_frees_the_slot(self):
        pk, slot = self.create(), self.slot()
        self.ok(self.book(pk, slot))
        self.ok(self.move(self.hep, pk, "cancelled", reason="Not needed"))
        self.assertEqual(self.appointment(pk).status, "cancelled")
        self.ok(self.book(self.create(), slot))

    def test_no_show(self):
        pk, slot = self.create(), self.slot()
        self.ok(self.book(pk, slot))
        url = f"{URL}{pk}/booking/no-show/"
        self.assertEqual(self.call(self.rad, url).status_code, 400)  # not yet
        Appointment.objects.update(start_time=timezone.now() - datetime.timedelta(minutes=30))
        data = self.ok(self.call(self.rad, url))
        self.assertEqual((data["status"], data["booking_state"]), ("ordered", "none"))
        self.assertEqual(self.appointment(pk).status, "no_show")

    def test_acquire_before_the_booked_day(self):
        pk = self.create()
        self.ok(self.book(pk, self.slot()))
        self.assertIn("status", self.move(self.rad, pk, "acquired").data)
        self.assertEqual(self.order(pk).status, "scheduled")

    def test_acquire_walk_in(self):
        pk = self.create()
        self.assertEqual(self.ok(self.move(self.rad, pk, "acquired"))["booking_state"], "none")

    # --- coordinator follow-up
    def test_coordinator_reminds(self):
        pk = self.own_order()
        Notification.objects.all().delete()  # the "scan requested" notice of today
        url = f"{URL}{pk}/remind/"
        for user in (self.root, self.hep, self.rad, self.billing):
            self.assertEqual(self.call(user, url).status_code, 403)
        self.ok(self.call(self.coord, url))
        note = Notification.objects.get(channel="in_app")
        self.assertEqual(note.user, self.pat_user)
        self.assertIn("choose an appointment", note.message)
        self.assertEqual(self.call(self.coord, url).status_code, 400)  # once a day
        Notification.objects.all().delete()
        self.ok(self.book(pk, self.slot(), self.pat_user))
        confirmation = Notification.objects.get(user=self.pat_user, title="Scan appointment confirmed")
        self.assertIn("confirmed for", confirmation.message)
        self.assertEqual(self.call(self.coord, url).status_code, 400)  # auto-confirmation already notified them
        self.assertEqual(self.order(pk).status, "scheduled")

    def test_remind_needs_open_order_and_portal_account(self):
        self.assertEqual(self.call(self.coord, f"{URL}{self.create()}/remind/").status_code, 400)
        pk = self.own_order()
        ImagingOrder.objects.filter(pk=pk).update(status="acquired")
        self.assertEqual(self.call(self.coord, f"{URL}{pk}/remind/").status_code, 400)

    def test_patient_notices(self):
        pk = self.own_order()
        self.ok(self.book(pk, self.slot()))
        self.ok(self.call(self.rad, f"{URL}{pk}/booking/cancel/", {"reason": "Scanner down"}))
        self.ok(self.move(self.rad, pk, "cancelled", reason="Private clinical reason"))
        notes = Notification.objects.filter(user=self.pat_user, channel="in_app")
        self.assertCountEqual(notes.values_list("title", flat=True), [
            "Scan requested", "Scan appointment confirmed", "Scan appointment cancelled", "Scan request cancelled"])
        self.assertFalse(notes.filter(message__contains="clinical").exists())


class SchedulingIntegrationTests(RadiologyTestBase):
    """Imaging appointments in the shared appointment module."""

    def setUp(self):
        super().setUp()
        self.pk, self.scan = self.own_order(), self.slot(start=timezone.now() + datetime.timedelta(hours=5))
        self.ok(self.book(self.pk, self.scan))
        self.appt = self.appointment(self.pk)
        self.url = f"{APPT}{self.appt.pk}/"

    def test_listed_without_a_doctor(self):
        for user in (self.coord, self.rad, self.pat_user):
            row = self.ok(self.call(user, APPT, method="get"))[0]
            self.assertEqual((row["appointment_type"], row["staff"], row["staff_name"], row["imaging_order"],
                              row["imaging_service"]), ("imaging", None, None, self.pk, self.service.name))

    def test_doctor_appointment_actions_are_refused(self):
        other = self.slot()
        for user in (self.admin, self.coord, self.pat_user):
            self.assertEqual(self.call(user, f"{self.url}cancel/").status_code, 400)
            self.assertEqual(self.call(user, f"{self.url}reschedule/", {
                "start_time": other.start_time.isoformat()}).status_code, 400)
        for action in ("no-show", "complete"):
            self.assertEqual(self.call(self.coord, f"{self.url}{action}/").status_code, 400)
        self.appt.refresh_from_db()
        self.assertEqual((self.appt.status, self.order(self.pk).status), ("booked", "scheduled"))

    def test_coordinator_checks_in(self):
        self.assertEqual(self.call(self.rad, f"{self.url}check-in/").status_code, 403)
        self.ok(self.call(self.coord, f"{self.url}check-in/"))
        self.assertEqual(self.order(self.pk).status, "scheduled")
        with mock.patch.object(services.timezone, "localdate", return_value=self.scan.start_time.date()):
            self.ok(self.move(self.rad, self.pk, "acquired"))
        self.assertEqual(self.appointment(self.pk).status, "completed")

    def test_scans_cannot_be_booked_as_doctor_visits(self):
        start = timezone.now() + datetime.timedelta(days=3)
        for kind in ("imaging", "ct_scan"):
            r = self.call(self.pat_user, APPT, {"staff": self.rad.staff_profile.pk, "appointment_type": kind,
                                                "start_time": start.isoformat()})
            self.assertEqual(r.status_code, 400)
            self.assertIn("appointment_type", r.data)

    def test_kinds_cannot_be_mixed_in_the_database(self):
        start = timezone.now() + datetime.timedelta(days=9)
        base = dict(patient=self.own, booked_by=self.coord, start_time=start,
                    end_time=start + datetime.timedelta(minutes=30))
        order, slot = self.order(self.own_order()), self.slot()
        for extra in ({"appointment_type": "consultation"},  # no doctor
                      {"appointment_type": "imaging"},       # no order / slot
                      {"appointment_type": "imaging", "imaging_order": order},
                      {"appointment_type": "imaging", "imaging_order": order, "imaging_slot": slot,
                       "staff": self.rad.staff_profile},
                      {"appointment_type": "consultation", "staff": self.hep.staff_profile, "imaging_order": order}):
            with self.subTest(extra=extra), self.assertRaises(IntegrityError), transaction.atomic():
                Appointment.objects.create(**base, **extra)

    def test_automatic_reminder_names_no_doctor(self):
        self.assertEqual(send_appointment_reminders(timezone.now()), 1)
        note = Notification.objects.get(title="Upcoming scan", channel="in_app")
        self.assertIn(self.service.name, note.message)
        self.assertNotIn("Dr.", note.message)
