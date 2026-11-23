"""Stage 6 tests: consents (permissions, validation, history, audit, and unchanged workflows)."""
import datetime
from unittest import mock

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import AuditLog, User

from .models import Consent, DonorApplication
from .test_api import PW, PatientAPITestBase, make_patient, make_staff, T

SIGNED = '2026-03-01T09:30:00Z'


class ConsentTestBase(PatientAPITestBase):
    def setUp(self):
        super().setUp()
        self.donor_user = User.objects.create_user('donor', 'donor@lh.test', PW, role='patient')
        self.donor = make_patient(first_name='Dina', last_name='Donor', category='donor', user=self.donor_user,
                                  phone='0122')
        self.recipient = make_patient(first_name='Rami', last_name='Recipient', category='recipient', phone='0144')

    def url(self, patient):
        return f'/api/patients/{patient.pk}/consents/'

    def record(self, patient=None, user=None, **over):
        self.as_(user or self.coord)
        data = {'consent_type': 'donor_surgery', 'signed_at': SIGNED}
        data.update(over)
        return self.client.post(self.url(patient or self.donor), data, format='json')

    def make_consent(self, patient=None, consent_type='donor_surgery', **extra):
        return Consent.objects.create(patient=patient or self.donor, consent_type=consent_type,
                                      signed_at=timezone.now() - datetime.timedelta(days=1),
                                      recorded_by=self.coord.staff_profile, **extra)

    def withdraw(self, consent, user=None):
        self.as_(user or self.coord)
        return self.client.post(f'/api/consents/{consent.pk}/withdraw/')


class ConsentPermissionTests(ConsentTestBase):
    def test_view_matrix_super_admin_excluded(self):
        self.make_consent()
        for user, code in ((self.coord, 200), (self.hep, 200), (self.rad, 200), (self.surg, 200),
                           (self.admin, 403), (self.root, 403), (self.billing, 403), (self.nojob, 403),
                           (self.pat_user, 403), (self.donor_user, 403)):
            with self.subTest(user=user.username):
                self.as_(user)
                self.assertEqual(self.client.get(self.url(self.donor)).status_code, code)

    def test_only_coordinator_and_hepatologist_record_and_withdraw(self):
        consent = self.make_consent(patient=self.recipient, consent_type='transplant_surgery')
        for user in (self.admin, self.root, self.rad, self.surg, self.billing, self.nojob, self.donor_user):
            with self.subTest(user=user.username):
                self.assertEqual(self.record(user=user).status_code, 403)
                self.assertEqual(self.withdraw(consent, user=user).status_code, 403)
                self.as_(user)
                self.assertEqual(self.client.get('/api/consents/witnesses/').status_code, 403)
        self.assertEqual(Consent.objects.count(), 1)
        for user, patient, kind in ((self.coord, self.donor, 'donor_surgery'), (self.hep, self.recipient, None)):
            with self.subTest(user=user.username):
                if kind is None:  # hepatologist withdraws the recipient's consent
                    self.assertEqual(self.withdraw(consent, user=user).status_code, 200)
                else:
                    self.assertEqual(self.record(patient=patient, user=user, consent_type=kind).status_code, 201)
                self.assertEqual(self.client.get('/api/consents/witnesses/').status_code, 200)

    def test_anonymous_rejected(self):
        self.client.force_authenticate(None)
        for url in (self.url(self.donor), '/api/consents/mine/', '/api/consents/witnesses/'):
            self.assertEqual(self.client.get(url).status_code, 401)

    def test_unknown_patient_and_consent(self):
        self.as_(self.coord)
        self.assertEqual(self.client.get('/api/patients/99999/consents/').status_code, 404)
        self.assertEqual(self.client.post('/api/patients/99999/consents/', {}, format='json').status_code, 404)
        self.assertEqual(self.client.post('/api/consents/99999/withdraw/').status_code, 404)


class ConsentRecordingTests(ConsentTestBase):
    def test_record_donor_surgery_consent(self):
        r = self.record(witnessed_by=self.hep.staff_profile.pk)
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual((r.data['consent_type'], r.data['type_label'], r.data['status'], r.data['is_active']),
                         ('donor_surgery', 'Donor surgery', 'signed', True))
        self.assertEqual(r.data['witnessed_by']['id'], self.hep.staff_profile.pk)
        self.assertEqual(r.data['recorded_by']['name'], 'Coord Staff')
        self.assertIsNone(r.data['withdrawn_at'])
        self.assertTrue(r.data['signed_at'].startswith('2026-03-01T09:30'))

    def test_witness_is_optional(self):
        r = self.record(witnessed_by=None)
        self.assertEqual((r.status_code, r.data['witnessed_by']), (201, None))
        r = self.record(patient=self.recipient, consent_type='transplant_surgery')
        self.assertEqual((r.status_code, r.data['witnessed_by']), (201, None))

    def test_only_surgery_types_in_this_stage(self):
        for kind in ('ct_contrast', 'data_use', 'nonsense', ''):
            with self.subTest(kind=kind):
                self.assertEqual(self.record(consent_type=kind).status_code, 400)
        self.assertEqual(Consent.objects.count(), 0)

    def test_type_must_match_category(self):
        r = self.record(patient=self.own, consent_type='donor_surgery')  # liver patient
        self.assertIn('living donor', str(r.data['consent_type']))
        r = self.record(patient=self.donor, consent_type='transplant_surgery')
        self.assertIn('recipient', str(r.data['consent_type']))
        self.assertEqual(Consent.objects.count(), 0)

    def test_signed_at_required_not_future_not_before_birth(self):
        self.assertIn('signed_at', self.record(signed_at=None).data)
        future = (timezone.now() + datetime.timedelta(days=1)).isoformat()
        self.assertIn('future', str(self.record(signed_at=future).data['signed_at']))
        self.assertIn('date of birth', str(self.record(signed_at='1950-01-01T00:00:00Z').data['signed_at']))
        self.assertEqual(Consent.objects.count(), 0)

    def test_witness_must_be_active_clinical_or_coordination_staff(self):
        inactive = make_staff('gone', T.HEPATOLOGIST)
        inactive.is_active = False
        inactive.save()
        for value in (inactive.staff_profile.pk, self.billing.staff_profile.pk, self.admin.staff_profile.pk,
                      99999, 'abc'):
            with self.subTest(value=value):
                r = self.record(witnessed_by=value)
                self.assertEqual(r.status_code, 400)
                self.assertIn('clinical or coordination staff', str(r.data['witnessed_by']))
        for staff in (self.coord, self.hep, self.rad, self.surg):  # every clinical/coordination title
            with self.subTest(witness=staff.username):
                r = self.record(witnessed_by=staff.staff_profile.pk)
                self.assertEqual((r.status_code, r.data['witnessed_by']['id']), (201, staff.staff_profile.pk))
                Consent.objects.get(pk=r.data['id']).withdraw(self.coord.staff_profile)

    def test_one_active_consent_per_type(self):
        self.assertEqual(self.record().status_code, 201)
        r = self.record()
        self.assertEqual(r.status_code, 400)
        self.assertIn('already has an active consent', str(r.data['consent_type']))

    def test_concurrent_duplicate_is_a_400(self):
        with mock.patch.object(Consent.objects, 'create', side_effect=IntegrityError):
            r = self.record()
        self.assertEqual(r.status_code, 400)
        self.assertEqual(AuditLog.objects.count(), 0)

    def test_witness_list_only_active_clinical_and_coordination_staff(self):
        inactive = make_staff('gone', T.RADIOLOGIST)
        inactive.is_active = False
        inactive.save()
        self.as_(self.hep)
        r = self.client.get('/api/consents/witnesses/')
        self.assertEqual(sorted(row['job_title'] for row in r.data),
                         ['hepatologist', 'radiologist', 'transplant_coordinator', 'transplant_surgeon'])
        self.assertNotIn(inactive.staff_profile.pk, [row['id'] for row in r.data])
        self.assertEqual(set(r.data[0]), {'id', 'name', 'job_title'})


class ConsentHistoryTests(ConsentTestBase):
    def test_withdrawal_is_tracked_final_and_kept(self):
        consent = self.make_consent()
        r = self.withdraw(consent, user=self.hep)
        self.assertEqual((r.status_code, r.data['status'], r.data['is_active']), (200, 'withdrawn', False))
        self.assertEqual(r.data['withdrawn_by']['name'], 'Hep Staff')
        self.assertIsNotNone(r.data['withdrawn_at'])
        self.assertEqual(self.withdraw(consent).status_code, 400)  # already withdrawn
        self.assertTrue(Consent.objects.filter(pk=consent.pk, status='withdrawn').exists())

    def test_signing_again_creates_a_new_record(self):
        first = self.make_consent()
        self.withdraw(first)
        r = self.record()
        self.assertEqual(r.status_code, 201)
        self.as_(self.rad)
        history = self.client.get(self.url(self.donor)).data
        # newest signing first: `first` was signed yesterday, the new one on SIGNED (earlier this year)
        self.assertEqual([(c['id'], c['status']) for c in history], [(first.pk, 'withdrawn'), (r.data['id'], 'signed')])
        self.assertTrue(Consent.has_active(self.donor, 'donor_surgery'))

    def test_has_active(self):
        self.assertFalse(Consent.has_active(self.donor, 'donor_surgery'))
        consent = self.make_consent()
        self.assertTrue(Consent.has_active(self.donor, 'donor_surgery'))
        self.assertFalse(Consent.has_active(self.donor, 'transplant_surgery'))
        consent.withdraw(self.coord.staff_profile)
        self.assertFalse(Consent.has_active(self.donor, 'donor_surgery'))

    def test_consents_cannot_be_deleted(self):
        consent = self.make_consent()
        with self.assertRaises(PermissionError):
            consent.delete()
        with self.assertRaises(PermissionError):
            Consent.objects.all().delete()
        from django.db.models import ProtectedError
        with self.assertRaises(ProtectedError):
            self.donor.delete()
        self.assertEqual(Consent.objects.count(), 1)

    def test_database_rules(self):
        staff = self.coord.staff_profile
        now = timezone.now()
        bad = (
            dict(consent_type='ct_contrast'),                                    # deferred type
            dict(status='withdrawn'),                                            # withdrawal not tracked
            dict(withdrawn_at=now, withdrawn_by=staff),                          # signed with withdrawal data
            dict(status='withdrawn', withdrawn_by=staff,
                 withdrawn_at=now - datetime.timedelta(days=30)),                # withdrawn before signed
        )
        for extra in bad:
            with self.subTest(extra=extra), self.assertRaises(IntegrityError), transaction.atomic():
                data = dict(patient=self.donor, consent_type='donor_surgery', recorded_by=staff,
                            signed_at=now - datetime.timedelta(days=1))
                data.update(extra)
                Consent.objects.create(**data)
        self.make_consent()
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.make_consent()  # second active consent of the same type


class MyConsentsTests(ConsentTestBase):
    def test_patient_sees_only_own_consents_read_only(self):
        mine = self.make_consent(witnessed_by=self.hep.staff_profile)
        self.make_consent(patient=self.recipient, consent_type='transplant_surgery')
        self.as_(self.donor_user)
        r = self.client.get('/api/consents/mine/')
        self.assertEqual([c['id'] for c in r.data], [mine.pk])
        self.assertEqual(set(r.data[0]), {'id', 'consent_type', 'type_label', 'status', 'status_label', 'signed_at',
                                          'witnessed_by', 'withdrawn_at'})
        self.assertEqual(r.data[0]['witnessed_by'], 'Hep Staff')
        for method in ('post', 'patch', 'put', 'delete'):
            self.assertEqual(getattr(self.client, method)('/api/consents/mine/', {}, format='json').status_code, 405)

    def test_patients_cannot_withdraw_or_view_others(self):
        consent = self.make_consent()
        self.as_(self.donor_user)
        self.assertEqual(self.client.post(f'/api/consents/{consent.pk}/withdraw/').status_code, 403)
        self.assertEqual(self.client.get(self.url(self.donor)).status_code, 403)
        self.assertEqual(self.client.get(self.url(self.recipient)).status_code, 403)

    def test_empty_list_and_no_record(self):
        self.as_(self.pat_user)
        self.assertEqual(self.client.get('/api/consents/mine/').data, [])
        self.as_(User.objects.create_user('lonely', '', PW, role='patient'))
        self.assertEqual(self.client.get('/api/consents/mine/').status_code, 404)

    def test_staff_cannot_use_portal_endpoint(self):
        for user in (self.coord, self.admin):
            self.as_(user)
            self.assertEqual(self.client.get('/api/consents/mine/').status_code, 403)


class ConsentAuditTests(ConsentTestBase):
    def entries(self):
        return list(AuditLog.objects.order_by('id').values_list('user__username', 'action', 'entity_type',
                                                                 'entity_id', 'patient_id'))

    def test_create_and_withdraw_are_logged(self):
        created = self.record().data['id']
        self.withdraw(Consent.objects.get(pk=created), user=self.hep)
        E = 'registry.consent'
        self.assertEqual(self.entries(), [('coord', 'create', E, created, self.donor.pk),
                                          ('hep', 'withdraw', E, created, self.donor.pk)])

    def test_reads_and_failures_are_not_logged(self):
        consent = self.make_consent()
        self.as_(self.rad)
        self.client.get(self.url(self.donor))
        self.as_(self.donor_user)
        self.client.get('/api/consents/mine/')
        self.as_(self.coord)
        self.client.get('/api/consents/witnesses/')
        self.record()                                   # duplicate active consent
        self.record(consent_type='ct_contrast')          # deferred type
        self.withdraw(consent, user=self.surg)           # no permission
        self.withdraw(consent, user=self.admin)          # super admin: no permission
        self.assertEqual(AuditLog.objects.count(), 0)


class CategoryChangeTests(ConsentTestBase):
    def test_category_change_keeps_existing_consents_unchanged(self):
        consent = self.make_consent(witnessed_by=self.hep.staff_profile)
        before = Consent.objects.filter(pk=consent.pk).values().get()
        self.as_(self.coord)
        r = self.client.post(f'/api/patients/{self.donor.pk}/category/', {'category': 'recipient'}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Consent.objects.filter(pk=consent.pk).values().get(), before)  # untouched, still signed
        self.as_(self.rad)
        self.assertEqual([c['status'] for c in self.client.get(self.url(self.donor)).data], ['signed'])
        # New consents follow the new category; the old one can still be withdrawn as usual.
        self.assertEqual(self.record(consent_type='donor_surgery').status_code, 400)
        self.assertEqual(self.record(consent_type='transplant_surgery').status_code, 201)
        self.assertEqual(self.withdraw(consent).status_code, 200)
        self.assertEqual(Consent.objects.filter(patient=self.donor).count(), 2)


class ExistingWorkflowTests(ConsentTestBase):
    def test_donor_application_needs_no_consent(self):
        self.as_(self.donor_user)
        r = self.client.post('/api/donor-applications/mine/', {'recipient_mrn': self.recipient.mrn,
                                                               'relationship': 'daughter'}, format='json')
        self.assertEqual(r.status_code, 201)
        app = DonorApplication.objects.get()
        self.as_(self.coord)
        r = self.client.post(f'/api/donor-applications/{app.pk}/status/', {'status': 'accepted'}, format='json')
        self.assertEqual((r.status_code, r.data['status']), (200, 'accepted'))
        self.assertEqual(Consent.objects.count(), 0)  # nothing was created or required

    def test_patient_profile_and_super_admin_patient_access_unchanged(self):
        self.as_(self.admin)
        self.assertEqual(self.client.get(f'/api/patients/{self.donor.pk}/').status_code, 200)
        self.assertEqual(self.client.get('/api/audit-logs/').status_code, 200)  # monitors via audit log
        self.assertEqual(self.client.get(self.url(self.donor)).status_code, 403)
