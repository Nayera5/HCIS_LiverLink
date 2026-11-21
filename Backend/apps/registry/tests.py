"""
Registry database tests (Patient, MRN generation, DonorApplication).
Run locally on SQLite or a local PostgreSQL, never on Neon.
"""
import datetime
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from apps.accounts.models import Staff, User

from .models import DonorApplication, MRNSequence, Patient

PW = 'Str0ng-Pass!2026'


def make_patient(**overrides):
    data = dict(first_name='Ahmed', last_name='Ibrahim', date_of_birth=datetime.date(1972, 3, 4),
                sex='male', phone='01000000000', category='liver_patient')
    data.update(overrides)
    return Patient.objects.create(**data)


def make_staff(username, job_title=Staff.JobTitle.TRANSPLANT_COORDINATOR):
    user = User.objects.create_user(username, '', PW, role=Staff.role_for_job_title(job_title),
                                    first_name=username.title(), last_name='Staff')
    return Staff.objects.create(user=user, job_title=job_title)


def db_rejects(fn):
    try:
        with transaction.atomic():
            fn()
    except IntegrityError:
        return True
    return False


class MRNTests(TestCase):
    def test_counter_row_is_seeded_by_migration(self):
        self.assertTrue(MRNSequence.objects.filter(pk=1).exists())

    def test_sequential_unique_formatted_mrns(self):
        start = MRNSequence.objects.get(pk=1).last_value
        mrns = [make_patient(first_name=f'P{i}').mrn for i in range(3)]
        self.assertEqual(mrns, [f'LL-{start + i:06d}' for i in (1, 2, 3)])
        self.assertEqual(MRNSequence.objects.get(pk=1).last_value, start + 3)

    def test_mrn_cannot_be_set_or_changed(self):
        with self.assertRaises(ValueError):
            Patient.objects.create(mrn='LL-999999', first_name='X', last_name='Y',
                                   date_of_birth=datetime.date(1990, 1, 1), sex='male', phone='1',
                                   category='donor')
        patient = make_patient()
        original_mrn = patient.mrn
        patient.mrn = 'LL-000001X'
        with self.assertRaises(ValueError):
            patient.save()
        reloaded = Patient.objects.get(pk=patient.pk)
        reloaded.phone = '0123'
        reloaded.save()  # normal updates keep the MRN
        self.assertEqual(Patient.objects.get(pk=patient.pk).mrn, original_mrn)

    def test_mrn_unique_in_database(self):
        patient = make_patient()
        other = make_patient(first_name='Other')
        self.assertTrue(db_rejects(lambda: Patient.objects.filter(pk=other.pk).update(mrn=patient.mrn)))

    def test_failed_insert_does_not_burn_a_number_silently(self):
        """The counter increment and the insert share one transaction."""
        make_patient(national_id='29001011234567')
        before = MRNSequence.objects.get(pk=1).last_value
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_patient(national_id='29001011234567')  # duplicate national ID
        self.assertEqual(MRNSequence.objects.get(pk=1).last_value, before)


class MRNOutsideTransactionTests(TransactionTestCase):
    def test_next_mrn_refuses_without_transaction(self):
        with self.assertRaises(RuntimeError):
            MRNSequence.next_mrn()

    def test_counter_recreated_if_missing(self):
        MRNSequence.objects.all().delete()
        self.assertTrue(make_patient().mrn.startswith('LL-'))
        self.assertEqual(MRNSequence.objects.count(), 1)

    def test_single_row_check(self):
        with self.assertRaises(IntegrityError):
            MRNSequence.objects.create(pk=2, last_value=0)


class PatientTests(TestCase):
    def test_national_id_rules(self):
        make_patient(national_id='29001011234567')
        self.assertTrue(db_rejects(lambda: make_patient(national_id='29001011234567')))  # unique
        self.assertTrue(db_rejects(lambda: make_patient(national_id='123')))            # 14 digits
        self.assertTrue(db_rejects(lambda: make_patient(national_id='2900101123456X')))
        with self.assertRaises(ValidationError):
            Patient(first_name='a', last_name='b', date_of_birth=datetime.date(1990, 1, 1), sex='male',
                    phone='1', category='donor', national_id='12AB').full_clean()

    def test_many_patients_without_national_id(self):
        a = make_patient(national_id='')
        b = make_patient(national_id=None)
        self.assertIsNone(Patient.objects.get(pk=a.pk).national_id)  # '' stored as NULL
        self.assertIsNone(b.national_id)

    def test_choice_checks_in_database(self):
        p = make_patient()
        for field, bad in (('sex', 'x'), ('category', 'other'), ('blood_group', 'C+')):
            with self.subTest(field=field):
                self.assertTrue(db_rejects(lambda: Patient.objects.filter(pk=p.pk).update(**{field: bad})))
        Patient.objects.filter(pk=p.pk).update(blood_group='AB-')
        Patient.objects.filter(pk=p.pk).update(blood_group=None)  # unknown is allowed

    def test_height_and_weight_must_be_positive(self):
        p = make_patient(height_cm=Decimal('172.5'), weight_kg=Decimal('80.25'))
        self.assertTrue(db_rejects(lambda: Patient.objects.filter(pk=p.pk).update(weight_kg=0)))
        self.assertTrue(db_rejects(lambda: Patient.objects.filter(pk=p.pk).update(height_cm=-1)))
        Patient.objects.filter(pk=p.pk).update(weight_kg=None)  # may be unknown

    def test_date_of_birth_not_in_future(self):
        p = Patient(first_name='a', last_name='b', sex='female', phone='1', category='donor',
                    date_of_birth=timezone.localdate() + datetime.timedelta(days=1))
        with self.assertRaises(ValidationError) as ctx:
            p.full_clean()
        self.assertIn('date_of_birth', ctx.exception.message_dict)

    def test_user_link_rules(self):
        account = User.objects.create_user('pat', '', PW, role='patient')
        p = make_patient(user=account)
        self.assertEqual(account.patient_profile, p)
        self.assertTrue(db_rejects(lambda: make_patient(user=account)))  # one record per account
        staff_account = User.objects.create_user('doc', '', PW, role='clinical_staff')
        with self.assertRaises(ValidationError):
            make_patient().__class__(user=staff_account, first_name='a', last_name='b', sex='male', phone='1',
                                     category='donor', date_of_birth=datetime.date(1990, 1, 1)).full_clean()

    def test_patient_without_account(self):
        p = make_patient()
        self.assertIsNone(p.user)

    def test_registered_by_and_set_null(self):
        coord = make_staff('coord')
        p = make_patient(registered_by=coord)
        self.assertEqual(list(coord.registered_patients.all()), [p])
        coord_user = coord.user
        coord.delete()  # staff profile removed: the patient keeps existing, the link is cleared
        p.refresh_from_db()
        self.assertIsNone(p.registered_by)
        self.assertTrue(User.objects.filter(pk=coord_user.pk).exists())

    def test_deleting_linked_account_keeps_record(self):
        account = User.objects.create_user('pat2', '', PW, role='patient')
        p = make_patient(user=account)
        account.delete()
        p.refresh_from_db()
        self.assertIsNone(p.user)

    def test_age_and_str(self):
        p = make_patient(date_of_birth=datetime.date(2000, 6, 15))
        self.assertEqual(p.age_on(datetime.date(2026, 6, 14)), 25)
        self.assertEqual(p.age_on(datetime.date(2026, 6, 15)), 26)
        self.assertIn(p.mrn, str(p))


class DonorApplicationTests(TestCase):
    def setUp(self):
        self.donor = make_patient(first_name='Omar', category='donor')
        self.recipient = make_patient(first_name='Ahmed', category='recipient')
        self.coord = make_staff('coord')

    def apply(self, **overrides):
        data = dict(donor=self.donor, recipient=self.recipient, relationship='brother')
        data.update(overrides)
        return DonorApplication.objects.create(**data)

    def test_defaults_and_relations(self):
        app = self.apply()
        self.assertEqual(app.status, 'submitted')
        self.assertTrue(app.is_open)
        self.assertEqual(list(self.donor.donor_applications.all()), [app])
        self.assertEqual(list(self.recipient.received_donor_applications.all()), [app])

    def test_donor_and_recipient_must_differ(self):
        self.assertTrue(db_rejects(lambda: self.apply(recipient=self.donor)))
        with self.assertRaises(ValidationError):
            DonorApplication(donor=self.donor, recipient=self.donor, relationship='self').full_clean()

    def test_one_open_application_per_pair(self):
        first = self.apply()
        self.assertTrue(db_rejects(lambda: self.apply()))
        DonorApplication.objects.filter(pk=first.pk).update(status='withdrawn')
        second = self.apply()  # re-applying after withdrawal is allowed
        DonorApplication.objects.filter(pk=second.pk).update(
            status='rejected', screened_by=self.coord, screened_at=timezone.now())
        self.apply()  # and after rejection
        other_recipient = make_patient(first_name='Karim', category='recipient')
        self.apply(recipient=other_recipient)  # different recipient is independent

    def test_validate_constraints_message_for_duplicate(self):
        self.apply()
        with self.assertRaises(ValidationError) as ctx:
            DonorApplication(donor=self.donor, recipient=self.recipient, relationship='x').validate_constraints()
        self.assertIn('already has an open application', str(ctx.exception))

    def test_decision_requires_screener_and_time(self):
        app = self.apply()
        for status in ('accepted', 'rejected'):
            with self.subTest(status=status):
                self.assertTrue(db_rejects(lambda: DonorApplication.objects.filter(pk=app.pk).update(status=status)))
                self.assertTrue(db_rejects(lambda: DonorApplication.objects.filter(pk=app.pk).update(
                    status=status, screened_by=self.coord)))
        DonorApplication.objects.filter(pk=app.pk).update(status='screening')  # no screener needed yet
        DonorApplication.objects.filter(pk=app.pk).update(
            status='accepted', screened_by=self.coord, screened_at=timezone.now(), screening_notes='OK')

    def test_status_check(self):
        app = self.apply()
        self.assertTrue(db_rejects(lambda: DonorApplication.objects.filter(pk=app.pk).update(status='approved')))

    def test_patients_and_screener_protected(self):
        app = self.apply()
        DonorApplication.objects.filter(pk=app.pk).update(
            status='accepted', screened_by=self.coord, screened_at=timezone.now())
        with self.assertRaises(ProtectedError):
            self.donor.delete()
        with self.assertRaises(ProtectedError):
            self.recipient.delete()
        with self.assertRaises(ProtectedError):
            self.coord.delete()
