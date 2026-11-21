"""Stage 5 API tests: donor applications (donor portal, staff screening, permissions, audit)."""
from unittest import mock

from apps.accounts.models import AuditLog, User

from .donor_serializers import MRN_NOT_FOUND
from .donor_views import SubmissionThrottle
from .models import DonorApplication, Patient
from .test_api import PW, PatientAPITestBase, make_patient

MINE = '/api/donor-applications/mine/'
STAFF = '/api/donor-applications/'


class DonorAPITestBase(PatientAPITestBase):
    def setUp(self):
        super().setUp()
        # self.own (pat_user) is a liver patient; self.other is a liver patient without an account.
        self.donor_user = User.objects.create_user('donor', 'donor@lh.test', PW, role='patient')
        self.donor = make_patient(first_name='Dina', last_name='Donor', category='donor', user=self.donor_user,
                                  phone='0122')
        self.donor2_user = User.objects.create_user('donor2', 'd2@lh.test', PW, role='patient')
        self.donor2 = make_patient(first_name='Dalia', last_name='Second', category='donor',
                                   user=self.donor2_user, phone='0133')
        self.recipient = make_patient(first_name='Rami', last_name='Recipient', category='recipient',
                                      blood_group='O+', phone='0144')
        self.walk_in_donor = make_patient(first_name='Walid', last_name='Walkin', category='donor', phone='0155')
        self.no_record_user = User.objects.create_user('norecord', 'nr@lh.test', PW, role='patient')

    def submit(self, user=None, **over):
        self.as_(user or self.donor_user)
        data = {'recipient_mrn': self.recipient.mrn, 'relationship': 'daughter'}
        data.update(over)
        return self.client.post(MINE, data, format='json')

    def make_app(self, donor=None, recipient=None, **extra):
        return DonorApplication.objects.create(donor=donor or self.donor, recipient=recipient or self.recipient,
                                               relationship='daughter', **extra)

    def screen(self, app, new_status, user=None, **extra):
        self.as_(user or self.coord)
        return self.client.post(f'{STAFF}{app.pk}/status/', {'status': new_status, **extra}, format='json')

    def entries(self):
        return list(AuditLog.objects.order_by('id').values_list('user__username', 'action', 'entity_type',
                                                                 'entity_id', 'patient_id'))


class DonorPortalTests(DonorAPITestBase):
    def test_donor_submits_with_recipient_mrn_only(self):
        r = self.submit(recipient_mrn=f'  {self.recipient.mrn.lower()} ')  # case/whitespace tolerant
        self.assertEqual(r.status_code, 201, r.data)
        app = DonorApplication.objects.get()
        self.assertEqual((app.donor, app.recipient, app.relationship, app.status),
                         (self.donor, self.recipient, 'daughter', 'submitted'))
        self.assertEqual(set(r.data), {'id', 'recipient_mrn', 'relationship', 'status', 'status_label',
                                       'can_withdraw', 'submitted_at', 'updated_at'})
        self.assertEqual(r.data['recipient_mrn'], self.recipient.mrn)
        self.assertNotIn('Rami', str(r.data))  # recipient's name is never shown to the donor

    def test_date_of_birth_is_not_required(self):
        self.assertEqual(self.submit().status_code, 201)

    def test_unknown_and_ineligible_mrns_get_the_same_error(self):
        for mrn in ('LL-999999', self.donor2.mrn, 'garbage'):  # unknown / another donor / malformed
            with self.subTest(mrn=mrn):
                r = self.submit(recipient_mrn=mrn)
                self.assertEqual((r.status_code, r.data['recipient_mrn']), (400, [MRN_NOT_FOUND]))
        self.assertEqual(DonorApplication.objects.count(), 0)

    def test_liver_patient_can_be_named_as_recipient(self):
        self.assertEqual(self.submit(recipient_mrn=self.other.mrn).status_code, 201)

    def test_cannot_name_self(self):
        r = self.submit(recipient_mrn=self.donor.mrn)
        self.assertEqual(r.status_code, 400)
        self.assertIn('different people', str(r.data['recipient_mrn']))

    def test_required_fields(self):
        r = self.submit(recipient_mrn='', relationship='  ')
        self.assertEqual(r.status_code, 400)
        self.assertEqual(set(r.data), {'recipient_mrn', 'relationship'})

    def test_one_open_application_per_recipient(self):
        self.assertEqual(self.submit().status_code, 201)
        r = self.submit()
        self.assertEqual(r.status_code, 400)
        self.assertIn('already an open application', str(r.data['recipient_mrn']))
        app = DonorApplication.objects.get()
        self.client.post(f'{MINE}{app.pk}/withdraw/')
        self.assertEqual(self.submit().status_code, 201)  # allowed again after withdrawing

    def test_database_race_on_duplicate_is_a_400(self):
        from django.db import IntegrityError
        with mock.patch.object(DonorApplication.objects, 'create', side_effect=IntegrityError):
            r = self.submit()
        self.assertEqual(r.status_code, 400)
        self.assertEqual(AuditLog.objects.count(), 0)

    def test_only_donor_category_records_can_apply(self):
        self.as_(self.pat_user)  # liver patient
        r = self.client.get(MINE)
        self.assertEqual((r.status_code, r.data['can_apply'], r.data['results']), (200, False, []))
        self.assertIn('living donors', r.data['reason'])
        self.assertEqual(self.submit(user=self.pat_user).status_code, 403)
        self.as_(self.no_record_user)
        r = self.client.get(MINE)
        self.assertEqual((r.data['can_apply'], r.data['results']), (False, []))
        self.assertEqual(self.submit(user=self.no_record_user).status_code, 404)
        self.assertEqual(DonorApplication.objects.count(), 0)

    def test_donor_sees_only_own_applications_without_notes(self):
        mine = self.make_app(status='rejected', screened_by=self.coord.staff_profile,
                             screened_at='2026-01-01T00:00Z', screening_notes='Secret clinical note')
        self.make_app(donor=self.donor2)
        self.as_(self.donor_user)
        r = self.client.get(MINE)
        self.assertEqual((r.data['can_apply'], [a['id'] for a in r.data['results']]), (True, [mine.pk]))
        self.assertNotIn('Secret', str(r.data))
        self.assertNotIn('coord', str(r.data).lower())

    def test_donor_withdraws_own_open_application(self):
        app = self.make_app()
        self.as_(self.donor_user)
        r = self.client.post(f'{MINE}{app.pk}/withdraw/')
        self.assertEqual((r.status_code, r.data['status'], r.data['can_withdraw']), (200, 'withdrawn', False))
        self.assertEqual(self.client.post(f'{MINE}{app.pk}/withdraw/').status_code, 400)  # already withdrawn

    def test_accepted_can_be_withdrawn_rejected_cannot(self):
        staff = self.coord.staff_profile
        accepted = self.make_app(status='accepted', screened_by=staff, screened_at='2026-01-01T00:00Z')
        rejected = self.make_app(recipient=self.other, status='rejected', screened_by=staff,
                                 screened_at='2026-01-01T00:00Z')
        self.as_(self.donor_user)
        self.assertEqual(self.client.post(f'{MINE}{accepted.pk}/withdraw/').status_code, 200)
        self.assertEqual(self.client.post(f'{MINE}{rejected.pk}/withdraw/').status_code, 400)

    def test_withdrawal_after_acceptance_keeps_record_and_audit(self):
        app_id = self.submit().data['id']
        app = DonorApplication.objects.get(pk=app_id)
        self.screen(app, 'accepted')
        self.as_(self.donor_user)
        listed = self.client.get(MINE).data['results'][0]
        self.assertEqual((listed['status'], listed['can_withdraw']), ('accepted', True))
        r = self.client.post(f'{MINE}{app_id}/withdraw/')
        self.assertEqual((r.status_code, r.data['status'], r.data['can_withdraw']), (200, 'withdrawn', False))
        app.refresh_from_db()  # the row is kept, with the screening history
        self.assertEqual((app.status, app.screened_by, app.relationship), ('withdrawn', self.coord.staff_profile,
                                                                         'daughter'))
        self.assertEqual([e[1] for e in self.entries()], ['create', 'status_change', 'withdraw'])
        self.assertEqual(self.client.get(MINE).data['results'][0]['status'], 'withdrawn')  # still listed

    def test_rejected_and_withdrawn_are_terminal(self):
        staff = self.coord.staff_profile
        rejected = self.make_app(status='rejected', screened_by=staff, screened_at='2026-01-01T00:00Z')
        withdrawn = self.make_app(recipient=self.other, status='withdrawn')
        for app in (rejected, withdrawn):
            with self.subTest(status=app.status):
                self.as_(self.donor_user)
                self.assertEqual(self.client.post(f'{MINE}{app.pk}/withdraw/').status_code, 400)
                self.as_(self.coord)
                self.assertEqual(self.client.post(f'{STAFF}{app.pk}/withdraw/').status_code, 400)
                for new_status in ('screening', 'accepted', 'rejected'):
                    self.assertEqual(self.screen(app, new_status, screening_notes='x').status_code, 400)
                app.refresh_from_db()
                self.assertIn(app.status, ('rejected', 'withdrawn'))
        self.assertEqual(AuditLog.objects.count(), 0)

    def test_cannot_withdraw_someone_elses_application(self):
        theirs = self.make_app(donor=self.donor2)
        for user in (self.donor_user, self.pat_user, self.no_record_user):
            with self.subTest(user=user.username):
                self.as_(user)
                self.assertEqual(self.client.post(f'{MINE}{theirs.pk}/withdraw/').status_code, 404)
        theirs.refresh_from_db()
        self.assertEqual(theirs.status, 'submitted')

    def test_donors_cannot_reach_staff_endpoints_or_other_records(self):
        app = self.make_app()
        self.as_(self.donor_user)
        for method, url in (('get', STAFF), ('post', STAFF), ('get', f'{STAFF}{app.pk}/'),
                            ('post', f'{STAFF}{app.pk}/status/'), ('post', f'{STAFF}{app.pk}/withdraw/'),
                            ('get', '/api/patients/'), ('get', f'/api/patients/{self.recipient.pk}/')):
            with self.subTest(url=url, method=method):
                self.assertEqual(getattr(self.client, method)(url, {}, format='json').status_code, 403)

    def test_staff_cannot_use_the_donor_portal(self):
        for user in (self.coord, self.admin, self.root):
            with self.subTest(user=user.username):
                self.as_(user)
                self.assertEqual(self.client.get(MINE).status_code, 403)
                self.assertEqual(self.client.post(MINE, {}, format='json').status_code, 403)

    def test_anonymous_rejected(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(MINE).status_code, 401)
        self.assertEqual(self.client.get(STAFF).status_code, 401)

    def test_submissions_are_throttled_reads_are_not(self):
        with mock.patch.object(SubmissionThrottle, 'THROTTLE_RATES', {'donor_application': '2/hour'}):
            self.submit(recipient_mrn='LL-999998')
            self.submit(recipient_mrn='LL-999997')
            self.assertEqual(self.submit().status_code, 429)
            for _ in range(3):
                self.assertEqual(self.client.get(MINE).status_code, 200)


class StaffApplicationTests(DonorAPITestBase):
    def test_view_permission_matrix(self):
        app = self.make_app()
        for user, code in ((self.root, 200), (self.admin, 200), (self.coord, 200), (self.hep, 200),
                           (self.rad, 200), (self.surg, 200), (self.billing, 403), (self.nojob, 403),
                           (self.pat_user, 403)):
            with self.subTest(user=user.username):
                self.as_(user)
                self.assertEqual(self.client.get(STAFF).status_code, code)
                self.assertEqual(self.client.get(f'{STAFF}{app.pk}/').status_code, code)

    def test_only_coordinator_screens_submits_and_withdraws(self):
        app = self.make_app()
        payload = {'donor_mrn': self.walk_in_donor.mrn, 'recipient_mrn': self.recipient.mrn, 'relationship': 'son'}
        for user in (self.root, self.admin, self.hep, self.rad, self.surg, self.billing, self.nojob):
            with self.subTest(user=user.username):
                self.as_(user)
                self.assertEqual(self.client.post(STAFF, payload, format='json').status_code, 403)
                self.assertEqual(self.screen(app, 'screening', user=user).status_code, 403)
                self.assertEqual(self.client.post(f'{STAFF}{app.pk}/withdraw/').status_code, 403)
        app.refresh_from_db()
        self.assertEqual(app.status, 'submitted')
        self.assertEqual(DonorApplication.objects.count(), 1)

    def test_staff_view_shows_both_people_and_screening(self):
        app = self.make_app()
        self.as_(self.hep)
        r = self.client.get(f'{STAFF}{app.pk}/')
        self.assertEqual(r.data['donor'], {'id': self.donor.pk, 'mrn': self.donor.mrn, 'name': 'Dina Donor',
                                           'category': 'donor', 'blood_group': None})
        self.assertEqual(r.data['recipient']['name'], 'Rami Recipient')
        self.assertEqual(r.data['recipient']['blood_group'], 'O+')
        self.assertEqual((r.data['status'], r.data['is_open'], r.data['next_statuses'], r.data['screened_by']),
                         ('submitted', True, ['screening', 'accepted', 'rejected'], None))
        self.assertEqual(self.client.get(f'{STAFF}99999/').status_code, 404)

    def test_coordinator_submits_on_behalf_of_a_donor(self):
        self.as_(self.coord)
        r = self.client.post(STAFF, {'donor_mrn': self.walk_in_donor.mrn.lower(), 'recipient_mrn': self.recipient.mrn,
                                     'relationship': 'brother'}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual((r.data['donor']['id'], r.data['recipient']['id'], r.data['status']),
                         (self.walk_in_donor.pk, self.recipient.pk, 'submitted'))

    def test_on_behalf_donor_must_be_a_registered_donor(self):
        self.as_(self.coord)
        for mrn, message in (('LL-999999', 'No patient'), (self.other.mrn, 'not registered as a living donor')):
            with self.subTest(mrn=mrn):
                r = self.client.post(STAFF, {'donor_mrn': mrn, 'recipient_mrn': self.recipient.mrn,
                                             'relationship': 'x'}, format='json')
                self.assertEqual(r.status_code, 400)
                self.assertIn(message, str(r.data['donor_mrn']))
        r = self.client.post(STAFF, {'donor_mrn': self.donor.mrn, 'recipient_mrn': self.donor2.mrn,
                                     'relationship': 'x'}, format='json')
        self.assertEqual(r.data['recipient_mrn'], [MRN_NOT_FOUND])

    def test_screening_workflow(self):
        app = self.make_app()
        r = self.screen(app, 'screening')
        self.assertEqual((r.status_code, r.data['status'], r.data['next_statuses']),
                         (200, 'screening', ['accepted', 'rejected']))
        self.assertEqual(r.data['screened_by']['name'], 'Coord Staff')
        self.assertIsNotNone(r.data['screened_at'])
        r = self.screen(app, 'accepted', screening_notes='  ABO compatible, BMI 24.  ')
        self.assertEqual((r.status_code, r.data['status'], r.data['screening_notes'], r.data['next_statuses']),
                         (200, 'accepted', 'ABO compatible, BMI 24.', []))
        r = self.screen(app, 'rejected', screening_notes='changed mind')  # accepted is final for screening
        self.assertEqual(r.status_code, 400)
        app.refresh_from_db()
        self.assertEqual(app.status, 'accepted')

    def test_invalid_transitions_and_statuses(self):
        app = self.make_app()
        self.screen(app, 'screening')
        self.assertEqual(self.screen(app, 'screening').status_code, 400)       # same status
        for bad in ('withdrawn', 'submitted', 'nonsense'):
            with self.subTest(status=bad):
                self.assertEqual(self.screen(app, bad).status_code, 400)    # not a screening decision
        withdrawn = self.make_app(recipient=self.other, status='withdrawn')
        self.assertEqual(self.screen(withdrawn, 'accepted').status_code, 400)
        self.assertEqual(self.screen(self.make_app(donor=self.donor2), 'accepted', user=self.coord).status_code, 200)
        self.as_(self.coord)
        self.assertEqual(self.client.post(f'{STAFF}99999/status/', {'status': 'screening'}).status_code, 404)

    def test_rejection_requires_a_reason(self):
        app = self.make_app()
        r = self.screen(app, 'rejected')
        self.assertEqual(r.status_code, 400)
        self.assertIn('reason', str(r.data['screening_notes']))
        r = self.screen(app, 'rejected', screening_notes='ABO incompatible')
        self.assertEqual((r.status_code, r.data['status']), (200, 'rejected'))

    def test_coordinator_records_withdrawal_including_after_acceptance(self):
        accepted = self.make_app(recipient=self.other)
        self.screen(accepted, 'accepted')
        self.as_(self.coord)
        r = self.client.post(f'{STAFF}{accepted.pk}/withdraw/')
        self.assertEqual((r.status_code, r.data['status']), (200, 'withdrawn'))
        app = self.make_app()
        self.as_(self.coord)
        r = self.client.post(f'{STAFF}{app.pk}/withdraw/')
        self.assertEqual((r.status_code, r.data['status'], r.data['next_statuses']), (200, 'withdrawn', []))
        self.assertEqual(self.client.post(f'{STAFF}{app.pk}/withdraw/').status_code, 400)

    def test_list_filters_and_order(self):
        a1 = self.make_app()
        a2 = self.make_app(donor=self.donor2, status='screening')
        a3 = self.make_app(donor=self.walk_in_donor, recipient=self.other, status='withdrawn')
        self.as_(self.hep)

        def ids(**params):
            r = self.client.get(STAFF, params)
            self.assertEqual(r.status_code, 200)
            return [row['id'] for row in r.data['results']]

        self.assertEqual(ids(), [a3.pk, a2.pk, a1.pk])                          # newest first
        self.assertEqual(ids(status='screening'), [a2.pk])
        self.assertEqual(ids(status='open'), [a2.pk, a1.pk])
        self.assertEqual(ids(status='bogus'), [a3.pk, a2.pk, a1.pk])            # unknown status ignored
        self.assertEqual(ids(search='walid'), [a3.pk])                         # donor name
        self.assertEqual(ids(search=self.other.mrn), [a3.pk])                  # recipient MRN
        self.assertEqual(ids(search='rami'), [a2.pk, a1.pk])                   # recipient name
        self.assertEqual(ids(donor=self.donor.pk), [a1.pk])
        self.assertEqual(ids(recipient=self.recipient.pk), [a2.pk, a1.pk])
        r = self.client.get(STAFF, {'page_size': 2})
        self.assertEqual((r.data['count'], len(r.data['results'])), (3, 2))


class DonorAuditTests(DonorAPITestBase):
    def test_create_withdraw_and_status_changes_are_logged(self):
        r = self.submit()
        own_id = r.data['id']
        self.client.post(f'{MINE}{own_id}/withdraw/')
        self.as_(self.coord)
        staff_id = self.client.post(STAFF, {'donor_mrn': self.walk_in_donor.mrn, 'recipient_mrn': self.recipient.mrn,
                                            'relationship': 'son'}, format='json').data['id']
        staff_app = DonorApplication.objects.get(pk=staff_id)
        self.screen(staff_app, 'screening')
        self.screen(staff_app, 'rejected', screening_notes='Confidential reason')
        other = self.make_app(donor=self.donor2)
        self.as_(self.coord)
        self.client.post(f'{STAFF}{other.pk}/withdraw/')
        E = 'registry.donorapplication'
        self.assertEqual(self.entries(), [
            ('donor', 'create', E, own_id, self.donor.pk),
            ('donor', 'withdraw', E, own_id, self.donor.pk),
            ('coord', 'create', E, staff_id, self.walk_in_donor.pk),
            ('coord', 'status_change', E, staff_id, self.walk_in_donor.pk),
            ('coord', 'status_change', E, staff_id, self.walk_in_donor.pk),
            ('coord', 'withdraw', E, other.pk, self.donor2.pk),
        ])
        stored = ' '.join(str(v) for e in AuditLog.objects.values() for v in e.values())
        self.assertNotIn('Confidential', stored)
        self.assertNotIn('daughter', stored)

    def test_reads_and_failed_requests_are_not_logged(self):
        app = self.make_app()
        self.as_(self.donor_user)
        self.client.get(MINE)
        self.submit(recipient_mrn='LL-999999')                         # invalid MRN
        self.submit(user=self.pat_user)                                # not a donor
        self.as_(self.pat_user)
        self.client.post(f'{MINE}{app.pk}/withdraw/')                  # not theirs
        self.as_(self.hep)
        self.client.get(STAFF, {'search': 'Dina'})
        self.client.get(f'{STAFF}{app.pk}/')
        self.client.post(f'{STAFF}{app.pk}/status/', {'status': 'accepted'}, format='json')  # no permission
        self.screen(app, 'withdrawn')                                  # invalid transition
        self.screen(app, 'rejected')                                   # missing reason
        self.assertEqual(AuditLog.objects.count(), 0)

    def test_new_actions_count_as_writes(self):
        for action in ('status_change', 'withdraw'):
            self.assertNotIn(action, AuditLog.READ_ACTIONS)


class DonorApplicationModelRulesTests(DonorAPITestBase):
    def test_screening_transitions_table_covers_every_status(self):
        self.assertEqual(set(DonorApplication.SCREENING_TRANSITIONS), set(DonorApplication.Status.values))

    def test_recipient_categories_exclude_donors(self):
        self.assertNotIn(Patient.Category.DONOR, DonorApplication.RECIPIENT_CATEGORIES)
