"""Notifications (module 14): events raised by other modules and the periodic reminder task."""
import datetime
from decimal import Decimal

from django.core import mail
from django.test import override_settings
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


class NoCeleryTriggerTests(NotificationTestBase):
    """Celery is off: opening the inbox runs the reminder check, at most once per interval."""

    def setUp(self):
        super().setUp()
        start = timezone.now() + datetime.timedelta(hours=2)
        Appointment.objects.create(patient=self.own, staff=self.hep.staff_profile, booked_by=self.coord,
                                   appointment_type='consultation', start_time=start,
                                   end_time=start + datetime.timedelta(minutes=30))

    def test_opening_notifications_sends_due_reminders(self):
        self.as_(self.pat_user)
        r = self.client.get('/api/notifications/me/')
        self.assertEqual(r.data['unread_count'], 1)
        self.assertEqual(r.data['notifications'][0]['type'], T.APPOINTMENT_REMINDER)

    def test_check_is_throttled(self):
        from unittest import mock

        from .tasks import run_due_reminders_if_due

        with mock.patch('apps.notifications.tasks.check_due_reminders', return_value=0) as check:
            run_due_reminders_if_due()
            run_due_reminders_if_due()
        self.assertEqual(check.call_count, 1)

    def test_management_command(self):
        from io import StringIO

        from django.core.management import call_command

        out = StringIO()
        call_command('send_reminders', stdout=out)
        self.assertIn('1 notification(s) sent.', out.getvalue())


@override_settings(NOTIFICATION_EMAIL_ASYNC=False)
class EmailNotificationTests(NotificationTestBase):
    """Emailed types go out after commit, once, and are recorded as channel='email' rows."""

    def stage_change(self):
        case = self.make_case(coordinator=self.coord.staff_profile)
        with self.captureOnCommitCallbacks(execute=True):
            case.transition_to('under_evaluation')
        return case

    def test_case_update_is_emailed_to_users_with_an_address(self):
        self.stage_change()
        # pat and the staff accounts all have addresses (test fixtures use @lh.test).
        recipients = sorted(address for message in mail.outbox for address in message.to)
        self.assertEqual(recipients, ['coord@lh.test', 'hep@lh.test', 'pat@lh.test'])
        patient_mail = next(m for m in mail.outbox if m.to == ['pat@lh.test'])
        self.assertEqual(patient_mail.subject, 'LiverLink: Your transplant case was updated')
        self.assertIn('"Under evaluation" stage', patient_mail.body)
        self.assertIn('/notifications', patient_mail.body)
        email_rows = Notification.objects.filter(user=self.pat_user, channel='email')
        self.assertEqual(email_rows.count(), 1)

    def test_inbox_shows_only_in_app_rows(self):
        self.stage_change()
        self.as_(self.pat_user)
        r = self.client.get('/api/notifications/me/')
        self.assertEqual(r.data['unread_count'], 1)
        self.assertEqual([n['channel'] for n in r.data['notifications']], ['in_app'])

    def test_in_app_only_types_and_users_without_email(self):
        self.pat_user.email = ''
        self.pat_user.save(update_fields=['email'])
        case = self.make_case(coordinator=self.coord.staff_profile)
        ChecklistItem.objects.create(case=case, patient=self.own, item_name='Consent', item_type='document')
        with self.captureOnCommitCallbacks(execute=True):
            from .tasks import send_pending_task_alerts
            send_pending_task_alerts(timezone.now())   # pending_task: in-app only
            from . import events
            events.case_stage_changed(case, 'referred')
        self.assertNotIn(['pat@lh.test'], [m.to for m in mail.outbox])
        self.assertFalse(any('missing items' in m.subject for m in mail.outbox))
        self.assertTrue(self.notes(self.coord, T.PENDING_TASK).filter(channel='in_app').exists())

    def test_rolled_back_change_sends_nothing(self):
        from django.db import transaction

        case = self.make_case(coordinator=self.coord.staff_profile)
        with self.captureOnCommitCallbacks(execute=True):
            try:
                with transaction.atomic():
                    case.transition_to('under_evaluation')
                    raise RuntimeError('rollback')
            except RuntimeError:
                pass
        self.assertEqual(mail.outbox, [])

    def test_mail_server_error_keeps_in_app_notification(self):
        from unittest import mock

        with mock.patch('apps.notifications.emails.send_mail', side_effect=OSError('SMTP down')), \
                self.assertLogs('apps.notifications.emails', 'ERROR'):
            self.stage_change()
        self.assertEqual(self.notes(self.pat_user, T.CASE_UPDATE).filter(channel='in_app').count(), 1)
        self.assertFalse(Notification.objects.filter(channel='email').exists())

    def test_reminder_is_not_resent_because_of_its_email_row(self):
        start = timezone.now() + datetime.timedelta(hours=2)
        Appointment.objects.create(patient=self.own, staff=self.hep.staff_profile, booked_by=self.coord,
                                   appointment_type='consultation', start_time=start,
                                   end_time=start + datetime.timedelta(minutes=30))
        with self.captureOnCommitCallbacks(execute=True):
            check_due_reminders()
        with self.captureOnCommitCallbacks(execute=True):
            check_due_reminders()
        self.assertEqual(len([m for m in mail.outbox if m.to == ['pat@lh.test']]), 1)
