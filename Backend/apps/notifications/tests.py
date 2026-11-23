"""Notifications (module 14): events raised by other modules and the periodic reminder task."""
import datetime
from decimal import Decimal

from django.utils import timezone

from apps.labs import services as lab_services
from apps.labs.models import LabTest
from apps.registry.test_api import PatientAPITestBase, make_patient
from apps.scheduling.models import Appointment
from apps.transplant.models import ChecklistItem, FollowUpPlan, FollowUpVisit, TransplantCase

from .models import Notification
from .tasks import check_due_reminders

T = Notification.Type


class NotificationTestBase(PatientAPITestBase):
    def notes(self, user, notif_type=None):
        qs = Notification.objects.filter(user=user)
        return qs.filter(type=notif_type) if notif_type else qs

    def make_case(self, **kw):
        return TransplantCase.objects.create(
            recipient=self.own, referred_by=self.hep.staff_profile, referral_date=timezone.localdate(), **kw)


class ResultNotificationTests(NotificationTestBase):
    def setUp(self):
        super().setUp()
        self.alt = LabTest.objects.create(code='1742-6', name='ALT', normal_min=7, normal_max=56, critical_max=1000)
        self.order = lab_services.create_order(self.own, self.hep.staff_profile, [self.alt])

    def test_doctor_told_when_all_results_are_in(self):
        lab_services.record_result(self.order.results.get(), Decimal('1500'))
        note = self.notes(self.hep, T.RESULT_READY).get()
        self.assertEqual(note.title, 'Critical lab results')
        self.assertIn('1 result is critical', note.message)
        self.assertEqual((note.related_type, note.related_id), ('labs.laborder', self.order.pk))
        self.assertFalse(self.notes(self.pat_user).exists())  # not released yet

    def test_patient_told_when_results_are_released(self):
        lab_services.record_result(self.order.results.get(), Decimal('30'))
        self.order.refresh_from_db()
        lab_services.release_order(self.order)
        self.assertEqual(self.notes(self.pat_user, T.RESULT_READY).count(), 1)
        lab_services.release_order(self.order)  # nothing new to release: no second notification
        self.assertEqual(self.notes(self.pat_user, T.RESULT_READY).count(), 1)


class CaseUpdateTests(NotificationTestBase):
    def test_stage_change_notifies_recipient_referrer_and_coordinator(self):
        case = self.make_case(coordinator=self.coord.staff_profile)
        case.transition_to('under_evaluation')
        for user in (self.pat_user, self.hep, self.coord):
            with self.subTest(user=user.username):
                self.assertEqual(self.notes(user, T.CASE_UPDATE).count(), 1)
        self.assertIn('Under evaluation', self.notes(self.hep, T.CASE_UPDATE).get().message)

    def test_unassigned_case_notifies_all_coordinators(self):
        self.make_case().transition_to('under_evaluation')
        self.assertEqual(self.notes(self.coord, T.CASE_UPDATE).count(), 1)

    def test_rejected_transition_sends_nothing(self):
        from django.core.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            self.make_case().transition_to('approved')
        self.assertFalse(Notification.objects.exists())


class ReminderTaskTests(NotificationTestBase):
    def appointment(self, hours_ahead, status=Appointment.Status.BOOKED, patient=None):
        start = timezone.now() + datetime.timedelta(hours=hours_ahead)
        return Appointment.objects.create(
            patient=patient or self.own, staff=self.hep.staff_profile, booked_by=self.coord,
            appointment_type='consultation', start_time=start, end_time=start + datetime.timedelta(minutes=30),
            status=status)

    def test_appointment_reminders_once_within_24_hours(self):
        soon = self.appointment(3)
        self.appointment(30)                                   # too far ahead
        self.appointment(5, status=Appointment.Status.CANCELLED)
        self.appointment(4, patient=self.other)                # no portal account
        check_due_reminders()
        check_due_reminders()
        notes = self.notes(self.pat_user, T.APPOINTMENT_REMINDER)
        self.assertEqual(notes.count(), 1)
        self.assertEqual(notes.get().related_id, soon.pk)

    def test_follow_up_reminders(self):
        case = self.make_case()
        plan = FollowUpPlan.objects.create(case=case, patient=self.own, patient_role='recipient',
                                           start_date=timezone.localdate())
        today = timezone.localdate()
        due = FollowUpVisit.objects.create(plan=plan, due_date=today + datetime.timedelta(days=2))
        FollowUpVisit.objects.create(plan=plan, due_date=today + datetime.timedelta(days=10))
        FollowUpVisit.objects.create(plan=plan, due_date=today, status='completed')
        check_due_reminders()
        check_due_reminders()
        notes = self.notes(self.pat_user, T.FOLLOW_UP_REMINDER)
        self.assertEqual([n.related_id for n in notes], [due.pk])

    def test_pending_task_alert_once_a_day(self):
        case = self.make_case(coordinator=self.coord.staff_profile)
        for name, required, status in (('CT volumetry', True, 'pending'), ('Consent form', True, 'pending'),
                                       ('Dental check', False, 'pending'), ('Blood group', True, 'done')):
            ChecklistItem.objects.create(case=case, patient=self.own, item_name=name, item_type='document',
                                         is_required=required, status=status)
        check_due_reminders()
        check_due_reminders()
        note = self.notes(self.coord, T.PENDING_TASK).get()
        self.assertIn('2 pending required items', note.message)
        self.assertIn('CT volumetry', note.message)
        self.assertNotIn('Dental check', note.message)
        # Next day: alerted again.
        Notification.objects.filter(pk=note.pk).update(sent_at=timezone.now() - datetime.timedelta(days=1))
        check_due_reminders()
        self.assertEqual(self.notes(self.coord, T.PENDING_TASK).count(), 2)

    def test_no_alert_when_nothing_is_pending(self):
        case = self.make_case(coordinator=self.coord.staff_profile)
        ChecklistItem.objects.create(case=case, patient=self.own, item_name='Consent', item_type='document',
                                     status='waived')
        check_due_reminders()
        self.assertFalse(self.notes(self.coord, T.PENDING_TASK).exists())


class InboxTests(NotificationTestBase):
    def test_inbox_shows_related_record(self):
        other_user = make_patient(first_name='X', last_name='Y', national_id='29001011234599')
        self.assertIsNone(other_user.user)
        case = self.make_case()
        case.transition_to('under_evaluation')
        self.as_(self.pat_user)
        r = self.client.get('/api/notifications/me/')
        self.assertEqual(r.data['unread_count'], 1)
        self.assertEqual(r.data['notifications'][0]['related_type'], 'transplant.transplantcase')
