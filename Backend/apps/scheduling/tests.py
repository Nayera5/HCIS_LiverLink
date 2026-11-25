"""Scheduling tests: links to module 1 (RBAC, Staff, audit), module 2 (Patient) and module 4 (Encounter)."""
import datetime

from django.utils import timezone

from apps.accounts.models import AuditLog
from apps.emr.models import Encounter
from apps.registry.test_api import PatientAPITestBase

from .models import Appointment, DoctorSchedule

SCHED = '/api/scheduling/schedules/'
APPT = '/api/scheduling/appointments/'
DAY = timezone.localdate() + datetime.timedelta(days=7)  # a future day, same weekday every run


def at(hour, minute=0, day=DAY):
    tz = timezone.get_current_timezone()
    return timezone.make_aware(datetime.datetime.combine(day, datetime.time(hour, minute)), tz)


class SchedulingTestBase(PatientAPITestBase):
    def setUp(self):
        super().setUp()
        # Hepatologist works 09:00-11:00 in 30-minute slots on DAY's weekday.
        self.schedule = DoctorSchedule.objects.create(
            staff=self.hep.staff_profile, day_of_week=DoctorSchedule.day_code(DAY),
            start_time=datetime.time(9), end_time=datetime.time(11), slot_minutes=30,
        )

    def book(self, user, start=None, **data):
        self.as_(user)
        payload = {'patient': self.own.pk, 'staff': self.hep.staff_profile.pk,
                   'appointment_type': 'consultation', 'start_time': (start or at(9)).isoformat()}
        payload.update(data)
        payload = {key: value for key, value in payload.items() if value is not None}
        return self.client.post(APPT, payload, format='json')

    def appointment(self, start=None, patient=None, status='booked'):
        start = start or at(9)
        return Appointment.objects.create(
            patient=patient or self.own, staff=self.hep.staff_profile, booked_by=self.coord,
            appointment_type='consultation', start_time=start,
            end_time=start + datetime.timedelta(minutes=30), status=status,
        )


class ScheduleTests(SchedulingTestBase):
    def payload(self, **over):
        other_day = DoctorSchedule.day_code(DAY + datetime.timedelta(days=1))  # not the setUp schedule's day
        data = {'day_of_week': other_day, 'start_time': '09:00', 'end_time': '12:00', 'slot_minutes': 15}
        data.update(over)
        return data

    def test_doctor_creates_own_schedule(self):
        for user in (self.hep, self.surg, self.rad):
            with self.subTest(user=user.username):
                self.as_(user)
                r = self.client.post(SCHED, self.payload(), format='json')
                self.assertEqual(r.status_code, 201, r.data)
                self.assertEqual(r.data['staff'], user.staff_profile.pk)

    def test_doctor_cannot_manage_other_doctor(self):
        self.as_(self.surg)
        r = self.client.post(SCHED, self.payload(staff=self.hep.staff_profile.pk), format='json')
        self.assertEqual(r.status_code, 400)
        r = self.client.patch(f'{SCHED}{self.schedule.pk}/', {'slot_minutes': 15}, format='json')
        self.assertEqual(r.status_code, 403)

    def test_super_admin_manages_any_and_must_choose_doctor(self):
        self.as_(self.admin)
        self.assertEqual(self.client.post(SCHED, self.payload(), format='json').status_code, 400)
        r = self.client.post(SCHED, self.payload(staff=self.surg.staff_profile.pk), format='json')
        self.assertEqual(r.status_code, 201, r.data)

    def test_others_cannot_write(self):
        for user in (self.coord, self.billing, self.nojob, self.pat_user):
            with self.subTest(user=user.username):
                self.as_(user)
                self.assertEqual(self.client.post(SCHED, self.payload(), format='json').status_code, 403)

    def test_validation(self):
        self.as_(self.hep)
        r = self.client.post(SCHED, self.payload(start_time='12:00', end_time='09:00'), format='json')
        self.assertIn('end_time', r.data)
        r = self.client.post(SCHED, self.payload(slot_minutes=0), format='json')
        self.assertIn('slot_minutes', r.data)
        overlap = self.payload(day_of_week=self.schedule.day_of_week, start_time='10:30', end_time='12:00')
        self.assertEqual(self.client.post(SCHED, overlap, format='json').status_code, 400)
        # An inactive schedule does not block a new one.
        self.schedule.is_active = False
        self.schedule.save()
        self.assertEqual(self.client.post(SCHED, overlap, format='json').status_code, 201)

    def test_no_delete(self):
        self.as_(self.hep)
        self.assertEqual(self.client.delete(f'{SCHED}{self.schedule.pk}/').status_code, 405)

    def test_free_slots(self):
        self.appointment(start=at(9, 30))
        self.appointment(start=at(10), status='cancelled')  # cancelled frees the slot
        self.as_(self.pat_user)
        r = self.client.get(f'{SCHED}free-slots/', {'staff': self.hep.staff_profile.pk, 'date': DAY.isoformat()})
        self.assertEqual(r.status_code, 200, r.data)
        starts = [s['start_time'] for s in r.data['slots']]
        self.assertEqual(starts, [at(9), at(10), at(10, 30)])

    def test_doctors_list(self):
        self.as_(self.hep)
        r = self.client.get(f'{SCHED}doctors/')
        self.assertEqual(r.status_code, 200)
        ids = {row['staff_id']: row for row in r.data}
        self.assertEqual(set(ids), {self.hep.staff_profile.pk, self.surg.staff_profile.pk, self.rad.staff_profile.pk})
        self.assertTrue(ids[self.hep.staff_profile.pk]['is_me'])
        self.assertFalse(ids[self.surg.staff_profile.pk]['is_me'])
        self.as_(self.pat_user)
        self.assertEqual(self.client.get(f'{SCHED}doctors/').status_code, 200)
        self.as_(self.billing)
        self.assertEqual(self.client.get(f'{SCHED}doctors/').status_code, 403)

    def test_free_slots_validation(self):
        self.as_(self.coord)
        self.assertEqual(self.client.get(f'{SCHED}free-slots/', {'staff': self.hep.staff_profile.pk}).status_code, 400)
        r = self.client.get(f'{SCHED}free-slots/', {'staff': self.coord.staff_profile.pk, 'date': DAY.isoformat()})
        self.assertEqual(r.status_code, 400)


class BookingTests(SchedulingTestBase):
    def test_examination_is_bookable_but_ct_and_lab_are_not(self):
        for appointment_type in ('ct_scan', 'lab_visit'):
            with self.subTest(appointment_type=appointment_type):
                response = self.book(self.coord, appointment_type=appointment_type)
                self.assertEqual(response.status_code, 400, response.data)
                self.assertIn('appointment_type', response.data)

        response = self.book(self.coord, appointment_type='examination')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['appointment_type'], 'examination')

    def test_consultations_are_specialty_specific(self):
        response = self.book(self.coord, appointment_type='hepatology_consultation')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['appointment_type'], 'hepatology_consultation')

        response = self.book(self.coord, start=at(9, 30), appointment_type='transplant_consultation')
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn('staff', response.data)

        DoctorSchedule.objects.create(
            staff=self.surg.staff_profile, day_of_week=DoctorSchedule.day_code(DAY),
            start_time=datetime.time(9), end_time=datetime.time(11), slot_minutes=30,
        )
        response = self.book(self.coord, start=at(9, 30), staff=self.surg.staff_profile.pk,
                             appointment_type='transplant_consultation')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['appointment_type'], 'transplant_consultation')

    def test_booking_matrix(self):
        starts = iter([at(9), at(9, 30), at(10)])
        for user in (self.coord, self.admin, self.pat_user):
            with self.subTest(user=user.username):
                r = self.book(user, start=next(starts))
                self.assertEqual(r.status_code, 201, r.data)
                self.assertEqual(r.data['booked_by'], user.pk)
                self.assertEqual(r.data['status'], 'booked')
        for user in (self.hep, self.rad, self.surg, self.billing, self.nojob):
            with self.subTest(user=user.username):
                self.assertEqual(self.book(user, start=at(10, 30)).status_code, 403)

    def test_end_time_comes_from_slot(self):
        r = self.book(self.coord)
        self.assertEqual(r.data['end_time'], at(9, 30).isoformat().replace('+00:00', 'Z'))

    def test_patient_books_only_for_self(self):
        r = self.book(self.pat_user, patient=self.other.pk)
        self.assertEqual(r.status_code, 400)
        r = self.book(self.pat_user, patient=None)
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['patient'], self.own.pk)

    def test_no_double_booking(self):
        self.assertEqual(self.book(self.coord).status_code, 201)
        r = self.book(self.coord, patient=self.other.pk)
        self.assertEqual(r.status_code, 400)
        self.assertIn('start_time', r.data)

    def test_must_be_a_slot(self):
        for start in (at(9, 10), at(11), at(8), at(9) - datetime.timedelta(days=14)):
            with self.subTest(start=start):
                self.assertEqual(self.book(self.coord, start=start).status_code, 400)

    def test_appointments_cannot_be_deleted_or_edited(self):
        appt = self.appointment()
        self.as_(self.coord)
        self.assertEqual(self.client.delete(f'{APPT}{appt.pk}/').status_code, 405)
        self.assertEqual(self.client.patch(f'{APPT}{appt.pk}/', {'reason': 'x'}, format='json').status_code, 405)

    def test_create_is_audited(self):
        r = self.book(self.coord)
        log = AuditLog.objects.get(entity_type='scheduling.appointment', entity_id=str(r.data['appointment_id']))
        self.assertEqual(log.action, AuditLog.Action.CREATE)
        self.assertEqual(log.patient, self.own)


class CalendarTests(SchedulingTestBase):
    def test_patient_sees_only_own(self):
        mine = self.appointment(start=at(9))
        self.appointment(start=at(9, 30), patient=self.other)
        self.as_(self.pat_user)
        r = self.client.get(APPT)
        self.assertEqual([a['appointment_id'] for a in r.data], [mine.pk])

    def test_read_matrix(self):
        for user, code in ((self.admin, 200), (self.coord, 200), (self.hep, 200), (self.rad, 200),
                           (self.surg, 200), (self.pat_user, 200), (self.billing, 403), (self.nojob, 403)):
            with self.subTest(user=user.username):
                self.as_(user)
                self.assertEqual(self.client.get(APPT).status_code, code)

    def test_day_and_week_filters(self):
        today = self.appointment(start=at(9))
        later = self.appointment(start=at(9, day=DAY + datetime.timedelta(days=3)))
        self.as_(self.coord)
        day = self.client.get(APPT, {'date_from': DAY.isoformat(), 'date_to': DAY.isoformat()})
        self.assertEqual([a['appointment_id'] for a in day.data], [today.pk])
        week_end = (DAY + datetime.timedelta(days=6)).isoformat()
        week = self.client.get(APPT, {'staff': self.hep.staff_profile.pk, 'date_from': DAY.isoformat(),
                                      'date_to': week_end})
        self.assertEqual([a['appointment_id'] for a in week.data], [today.pk, later.pk])
        self.assertEqual(self.client.get(APPT, {'date_from': 'bad'}).status_code, 400)


class StatusTests(SchedulingTestBase):
    def post(self, user, appt, name, data=None):
        self.as_(user)
        return self.client.post(f'{APPT}{appt.pk}/{name}/', data or {}, format='json')

    def test_reschedule(self):
        appt = self.appointment()
        r = self.post(self.pat_user, appt, 'reschedule', {'start_time': at(10).isoformat()})
        self.assertEqual(r.status_code, 200, r.data)
        appt.refresh_from_db()
        self.assertEqual((appt.start_time, appt.end_time), (at(10), at(10, 30)))
        # The patient cannot be changed by rescheduling.
        r = self.post(self.coord, appt, 'reschedule', {'start_time': at(9).isoformat(), 'patient': self.other.pk})
        self.assertEqual(r.status_code, 200, r.data)
        appt.refresh_from_db()
        self.assertEqual(appt.patient, self.own)

    def test_reschedule_rules(self):
        appt = self.appointment()
        self.appointment(start=at(10), patient=self.other)
        self.assertEqual(self.post(self.coord, appt, 'reschedule', {}).status_code, 400)
        self.assertEqual(self.post(self.coord, appt, 'reschedule', {'start_time': at(10).isoformat()}).status_code, 400)
        self.assertEqual(self.post(self.hep, appt, 'reschedule', {'start_time': at(10, 30).isoformat()}).status_code, 403)
        other = self.appointment(start=at(10, 30), patient=self.other)
        self.assertEqual(self.post(self.pat_user, other, 'reschedule', {'start_time': at(9, 30).isoformat()}).status_code, 404)
        appt.status = 'checked_in'
        appt.save()
        self.assertEqual(self.post(self.coord, appt, 'reschedule', {'start_time': at(9, 30).isoformat()}).status_code, 400)

    def test_cancel(self):
        appt = self.appointment()
        self.assertEqual(self.post(self.hep, appt, 'cancel').status_code, 403)
        r = self.post(self.pat_user, appt, 'cancel')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['status'], 'cancelled')
        self.assertEqual(self.post(self.coord, appt, 'cancel').status_code, 400)  # already cancelled
        self.assertTrue(Appointment.objects.filter(pk=appt.pk).exists())  # kept for reports

    def test_check_in_and_no_show_only_coordinator(self):
        appt = self.appointment()
        for user in (self.admin, self.hep, self.pat_user):
            with self.subTest(user=user.username):
                self.assertEqual(self.post(user, appt, 'check-in').status_code, 403)
                self.assertEqual(self.post(user, appt, 'no-show').status_code, 403)
        self.assertEqual(self.post(self.coord, appt, 'check-in').data['status'], 'checked_in')
        self.assertEqual(self.post(self.coord, appt, 'no-show').status_code, 400)  # not from checked_in

    def test_complete(self):
        appt = self.appointment()
        self.assertEqual(self.post(self.hep, appt, 'complete').status_code, 400)  # must be checked in first
        appt.status = 'checked_in'
        appt.save()
        self.assertEqual(self.post(self.surg, appt, 'complete').status_code, 403)  # not their patient
        r = self.post(self.hep, appt, 'complete')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['status'], 'completed')
        log = AuditLog.objects.filter(entity_type='scheduling.appointment', entity_id=str(appt.pk)).first()
        self.assertEqual(log.action, AuditLog.Action.STATUS_CHANGE)


class EncounterLinkTests(SchedulingTestBase):
    def test_encounter_links_to_appointment(self):
        appt = self.appointment()
        self.as_(self.hep)
        r = self.client.post('/api/emr/encounters/', {'patient': self.own.pk, 'appointment': appt.pk}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(Encounter.objects.get(pk=r.data['encounter_id']).appointment, appt)
        self.assertEqual(self.client.get(f'{APPT}{appt.pk}/').data['encounter'], r.data['encounter_id'])
        # At most one encounter per appointment.
        r = self.client.post('/api/emr/encounters/', {'patient': self.own.pk, 'appointment': appt.pk}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_appointment_must_be_same_patient(self):
        appt = self.appointment(patient=self.other)
        self.as_(self.hep)
        r = self.client.post('/api/emr/encounters/', {'patient': self.own.pk, 'appointment': appt.pk}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('appointment', r.data)
