"""
Stage 2 tests: Users & RBAC. Run on local SQLite only, e.g.
    $env:DATABASE_URL="sqlite:///test.sqlite3"; python manage.py test apps.accounts
"""
import re

from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from .models import AuditLog, Staff, User
from .rbac import capabilities_for, effective_job_title

PW = 'Str0ng-Pass!2026'
T = Staff.JobTitle


def make_staff(username, job_title, **extra):
    role = Staff.role_for_job_title(job_title)
    user = User.objects.create_user(username, f'{username}@liverlink.test', PW, role=role,
                                    first_name=username.title(), last_name='Tester', **extra)
    Staff.objects.create(user=user, job_title=job_title)
    return user


def make_user(username, role, **extra):
    return User.objects.create_user(username, extra.pop('email', ''), PW, role=role, **extra)


class RBACUnitTests(TestCase):
    """The approved D1 matrix, checked capability by capability."""

    EXPECTED = {
        T.SUPER_ADMIN: {'users.manage', 'audit.view', 'patients.register', 'patients.view', 'patients.edit',
                        'patients.change_category', 'donor_applications.view', 'consents.view',
                        'labs.view', 'labs.enter_result', 'prescriptions.view', 'treatment_plans.view', 'drugs.manage'},
        T.BILLING_ADMIN: {'patients.view'},
        T.TRANSPLANT_COORDINATOR: {'patients.register', 'patients.view', 'patients.edit',
                                   'patients.change_category', 'donor_applications.submit_on_behalf',
                                   'donor_applications.screen', 'donor_applications.view',
                                   'consents.record', 'consents.view', 'labs.view', 'labs.enter_result',
                                   'prescriptions.view', 'treatment_plans.view'},
        T.HEPATOLOGIST: {'patients.view', 'patients.change_category', 'donor_applications.view',
                         'consents.record', 'consents.view', 'labs.view', 'labs.order', 'labs.enter_result',
                         'labs.release', 'prescriptions.view', 'prescriptions.prescribe', 'treatment_plans.view', 'treatment_plans.manage', 'drugs.manage'},
        T.RADIOLOGIST: {'patients.view', 'donor_applications.view', 'consents.view', 'labs.view',
                        'prescriptions.view', 'treatment_plans.view'},
        T.TRANSPLANT_SURGEON: {'patients.view', 'donor_applications.view', 'consents.view', 'labs.view',
                               'labs.order', 'labs.release', 'prescriptions.view', 'prescriptions.prescribe', 'treatment_plans.view', 'treatment_plans.manage', 'drugs.manage'},
    }

    def test_matrix_per_job_title(self):
        for title, expected in self.EXPECTED.items():
            with self.subTest(title=title):
                user = make_staff(f'u_{title}', title)
                self.assertEqual(effective_job_title(user), title)
                self.assertEqual(capabilities_for(user), expected | {'self.profile'})

    def test_patient_only_self_service(self):
        user = make_user('pat', User.Role.PATIENT)
        self.assertEqual(capabilities_for(user), {'self.profile', 'self.patient_record',
                                                  'self.donor_applications', 'self.consents',
                                                  'self.lab_results', 'self.medications'})
        self.assertIsNone(effective_job_title(user))

    def test_clinical_staff_without_job_title_has_no_clinical_permissions(self):
        user = make_user('nojob', User.Role.CLINICAL_STAFF)
        self.assertIsNone(effective_job_title(user))
        self.assertEqual(capabilities_for(user), {'self.profile'})

    def test_admin_role_without_profile_and_not_superuser_has_nothing(self):
        user = make_user('plainadmin', User.Role.ADMIN)
        self.assertEqual(capabilities_for(user), {'self.profile'})

    def test_superuser_without_profile_counts_as_super_admin(self):
        user = User.objects.create_superuser('root', '', PW)
        self.assertEqual(effective_job_title(user), T.SUPER_ADMIN)
        self.assertIn('users.manage', capabilities_for(user))

    def test_mismatched_profile_fails_closed(self):
        user = make_staff('mismatch', T.HEPATOLOGIST)
        User.objects.filter(pk=user.pk).update(role=User.Role.ADMIN)  # bypass validation on purpose
        user.refresh_from_db()
        self.assertIsNone(effective_job_title(user))
        self.assertEqual(capabilities_for(user), {'self.profile'})

    def test_inactive_user_has_nothing(self):
        user = make_staff('gone', T.SUPER_ADMIN, is_active=False)
        self.assertEqual(capabilities_for(user), frozenset())

    def test_staff_model_validation(self):
        patient = make_user('p2', User.Role.PATIENT)
        with self.assertRaises(Exception):
            Staff(user=patient, job_title=T.HEPATOLOGIST).full_clean()
        noname = make_user('noname', User.Role.CLINICAL_STAFF)
        with self.assertRaises(Exception):
            Staff(user=noname, job_title=T.HEPATOLOGIST).full_clean()
        clin = make_user('clin', User.Role.CLINICAL_STAFF, first_name='A', last_name='B')
        with self.assertRaises(Exception):
            Staff(user=clin, job_title=T.SUPER_ADMIN).full_clean()  # admin title needs admin role


class AuthFlowTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = make_staff('coord', T.TRANSPLANT_COORDINATOR)

    def login(self, username='coord', password=PW):
        return self.client.post('/api/auth/token/', {'username': username, 'password': password}, format='json')

    def auth(self, access):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')

    def test_login_records_last_login(self):
        self.assertIsNone(self.user.last_login)
        self.assertEqual(self.login().status_code, 200)
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.last_login)

    def test_login_and_refresh_rotation(self):
        r = self.login()
        self.assertEqual(r.status_code, 200)
        old_refresh = r.data['refresh']
        r2 = self.client.post('/api/auth/token/refresh/', {'refresh': old_refresh}, format='json')
        self.assertEqual(r2.status_code, 200)
        self.assertIn('refresh', r2.data)  # rotated
        r3 = self.client.post('/api/auth/token/refresh/', {'refresh': old_refresh}, format='json')
        self.assertEqual(r3.status_code, 401)  # old one blacklisted

    def test_logout_blacklists_refresh_token(self):
        tokens = self.login().data
        self.auth(tokens['access'])
        r = self.client.post('/api/auth/logout/', {'refresh': tokens['refresh']}, format='json')
        self.assertEqual(r.status_code, 205)
        r = self.client.post('/api/auth/token/refresh/', {'refresh': tokens['refresh']}, format='json')
        self.assertEqual(r.status_code, 401)

    def test_logout_requires_auth_and_own_token(self):
        tokens = self.login().data
        self.assertEqual(self.client.post('/api/auth/logout/', {'refresh': tokens['refresh']},
                                          format='json').status_code, 401)
        other = make_staff('other', T.RADIOLOGIST)
        self.auth(str(RefreshToken.for_user(other).access_token))
        r = self.client.post('/api/auth/logout/', {'refresh': tokens['refresh']}, format='json')
        self.assertEqual(r.status_code, 403)

    def test_logout_with_garbage_token_is_harmless(self):
        self.auth(self.login().data['access'])
        r = self.client.post('/api/auth/logout/', {'refresh': 'not-a-token'}, format='json')
        self.assertEqual(r.status_code, 205)

    def test_me_returns_role_job_title_and_capabilities(self):
        self.auth(self.login().data['access'])
        r = self.client.get('/api/auth/me/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['role'], 'clinical_staff')
        self.assertEqual(r.data['job_title'], 'transplant_coordinator')
        self.assertIn('donor_applications.screen', r.data['capabilities'])
        self.assertNotIn('users.manage', r.data['capabilities'])
        self.assertNotIn('password', r.data)

    def test_me_requires_auth(self):
        self.assertEqual(self.client.get('/api/auth/me/').status_code, 401)

    def test_me_for_clinical_staff_without_job_title(self):
        make_user('nojob', User.Role.CLINICAL_STAFF)
        self.auth(self.login('nojob').data['access'])
        r = self.client.get('/api/auth/me/')
        self.assertIsNone(r.data['job_title'])
        self.assertEqual(r.data['capabilities'], ['self.profile'])

    def test_me_update_contact_details(self):
        self.auth(self.login().data['access'])
        r = self.client.patch('/api/auth/me/', {'email': 'New.Mail@LiverLink.test', 'phone': '0100'}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['email'], 'New.Mail@liverlink.test')
        self.assertEqual(r.data['staff_profile']['phone'], '0100')

    def test_me_update_rejects_duplicate_email_and_role_changes(self):
        make_staff('rad', T.RADIOLOGIST)
        self.auth(self.login().data['access'])
        r = self.client.patch('/api/auth/me/', {'email': 'RAD@liverlink.test'}, format='json')
        self.assertEqual(r.status_code, 400)
        r = self.client.patch('/api/auth/me/', {'role': 'admin', 'username': 'x'}, format='json')
        self.assertEqual(r.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual((self.user.role, self.user.username), ('clinical_staff', 'coord'))

    def test_me_phone_rejected_for_non_staff(self):
        make_user('pat', User.Role.PATIENT)
        self.auth(self.login('pat').data['access'])
        r = self.client.patch('/api/auth/me/', {'phone': '0100'}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_change_password(self):
        tokens = self.login().data
        self.auth(tokens['access'])
        url = '/api/auth/change-password/'
        self.assertEqual(self.client.post(url, {'current_password': 'wrong', 'new_password': 'An0ther-Pass!'},
                                          format='json').status_code, 400)
        self.assertEqual(self.client.post(url, {'current_password': PW, 'new_password': '123'},
                                          format='json').status_code, 400)
        self.assertEqual(self.client.post(url, {'current_password': PW, 'new_password': PW},
                                          format='json').status_code, 400)
        r = self.client.post(url, {'current_password': PW, 'new_password': 'An0ther-Pass!x'}, format='json')
        self.assertEqual(r.status_code, 200)
        # old refresh token revoked, old password rejected, new one works
        self.assertEqual(self.client.post('/api/auth/token/refresh/', {'refresh': tokens['refresh']},
                                          format='json').status_code, 401)
        self.assertEqual(self.login().status_code, 401)
        self.assertEqual(self.login(password='An0ther-Pass!x').status_code, 200)


@override_settings(FRONTEND_URL='http://localhost:5173')
class PasswordResetTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = make_staff('hep', T.HEPATOLOGIST)

    def request_reset(self, email):
        return self.client.post('/api/auth/password-reset/', {'email': email}, format='json')

    def link_parts(self):
        m = re.search(r'reset-password\?uid=([^&\s]+)&token=(\S+)', mail.outbox[-1].body)
        return m.group(1), m.group(2)

    def test_unknown_email_same_answer_and_no_mail(self):
        r = self.request_reset('nobody@nowhere.test')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(r.data, self.request_reset('HEP@liverlink.test').data)  # same message

    def test_full_reset_flow(self):
        old_refresh = str(RefreshToken.for_user(self.user))
        self.request_reset('HEP@LiverLink.test')  # case-insensitive
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['hep@liverlink.test'])
        self.assertIn('http://localhost:5173/reset-password?uid=', mail.outbox[0].body)
        uid, token = self.link_parts()
        url = '/api/auth/password-reset/confirm/'
        self.assertEqual(self.client.post(url, {'uid': uid, 'token': token, 'new_password': 'short'},
                                          format='json').status_code, 400)
        r = self.client.post(url, {'uid': uid, 'token': token, 'new_password': 'Brand-New-Pass!9'}, format='json')
        self.assertEqual(r.status_code, 200)
        # token is single-use, old sessions revoked, new password works
        self.assertEqual(self.client.post(url, {'uid': uid, 'token': token, 'new_password': 'Other-Pass!99x'},
                                          format='json').status_code, 400)
        self.assertEqual(self.client.post('/api/auth/token/refresh/', {'refresh': old_refresh},
                                          format='json').status_code, 401)
        self.assertEqual(self.client.post('/api/auth/token/', {'username': 'hep', 'password': 'Brand-New-Pass!9'},
                                          format='json').status_code, 200)

    def test_bad_uid_or_token(self):
        url = '/api/auth/password-reset/confirm/'
        for uid, token in (('zzz', 'x'), ('MQ', 'bad-token')):
            r = self.client.post(url, {'uid': uid, 'token': token, 'new_password': 'Brand-New-Pass!9'}, format='json')
            self.assertEqual(r.status_code, 400)

    def test_inactive_user_gets_no_mail(self):
        self.user.is_active = False
        self.user.save()
        self.request_reset('hep@liverlink.test')
        self.assertEqual(len(mail.outbox), 0)

    def test_throttled(self):
        codes = [self.request_reset(f'x{i}@nowhere.test').status_code for i in range(6)]
        self.assertEqual(codes[:5], [200] * 5)
        self.assertEqual(codes[5], 429)


class UserManagementTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.admin = make_staff('boss', T.SUPER_ADMIN)
        self.root = User.objects.create_superuser('root', '', PW)  # like the team admin (no profile)
        self.coord = make_staff('coord', T.TRANSPLANT_COORDINATOR)
        self.billing = make_staff('bill', T.BILLING_ADMIN)
        self.nojob = make_user('test_admin', User.Role.CLINICAL_STAFF)
        self.patient = make_user('pat', User.Role.PATIENT)

    def as_user(self, user):
        self.client.force_authenticate(user)

    def new_staff_payload(self, **over):
        data = {'username': 'Dr.Mona', 'email': 'mona@liverlink.test', 'first_name': 'Mona',
                'last_name': 'Elsayed', 'password': 'Very-Strong-Pass!1', 'job_title': 'hepatologist',
                'department': 'Hepatology', 'license_no': 'EG-123'}
        data.update(over)
        return data

    # ---- access control
    def test_only_super_admin_can_list_users(self):
        for user, code in ((self.admin, 200), (self.root, 200), (self.coord, 403), (self.billing, 403),
                           (self.nojob, 403), (self.patient, 403)):
            with self.subTest(user=user.username):
                self.as_user(user)
                self.assertEqual(self.client.get('/api/users/').status_code, code)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get('/api/users/').status_code, 401)

    def test_non_admins_cannot_create_edit_or_deactivate(self):
        for user in (self.coord, self.billing, self.nojob, self.patient):
            with self.subTest(user=user.username):
                self.as_user(user)
                self.assertEqual(self.client.post('/api/users/', self.new_staff_payload(), format='json').status_code, 403)
                self.assertEqual(self.client.patch(f'/api/users/{self.coord.pk}/', {'department': 'x'},
                                                   format='json').status_code, 403)
                self.assertEqual(self.client.post(f'/api/users/{self.coord.pk}/deactivate/').status_code, 403)

    def test_list_filters_and_search(self):
        self.as_user(self.admin)
        r = self.client.get('/api/users/', {'role': 'patient'})
        self.assertEqual([u['username'] for u in r.data['results']], ['pat'])
        r = self.client.get('/api/users/', {'job_title': 'transplant_coordinator'})
        self.assertEqual([u['username'] for u in r.data['results']], ['coord'])
        r = self.client.get('/api/users/', {'search': 'BILL'})
        self.assertEqual([u['username'] for u in r.data['results']], ['bill'])
        self.assertNotIn('password', r.data['results'][0])
        r = self.client.get('/api/users/', {'has_staff_profile': 'false', 'role': 'clinical_staff'})
        self.assertEqual([u['username'] for u in r.data['results']], ['test_admin'])
        r = self.client.get('/api/users/', {'ordering': '-date_joined', 'page_size': 1})
        self.assertEqual((r.data['count'], r.data['results'][0]['username']), (6, 'pat'))
        r = self.client.get('/api/users/', {'ordering': 'password'})  # unknown ordering ignored
        self.assertEqual(r.status_code, 200)

    # ---- create staff accounts
    def test_create_staff_account(self):
        self.as_user(self.admin)
        r = self.client.post('/api/users/', self.new_staff_payload(), format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual((r.data['role'], r.data['job_title']), ('clinical_staff', 'hepatologist'))
        self.assertNotIn('password', r.data)
        user = User.objects.get(username='Dr.Mona')
        self.assertTrue(user.check_password('Very-Strong-Pass!1'))
        self.assertFalse(user.is_staff)  # no Django-admin access from the app
        self.client.force_authenticate(None)
        self.assertEqual(self.client.post('/api/auth/token/', {'username': 'Dr.Mona', 'password': 'Very-Strong-Pass!1'},
                                          format='json').status_code, 200)

    def test_create_admin_title_gets_admin_role(self):
        self.as_user(self.root)
        r = self.client.post('/api/users/', self.new_staff_payload(username='acc', email='', license_no='',
                                                                  job_title='billing_admin'), format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['role'], 'admin')

    def test_create_validation_errors(self):
        self.as_user(self.admin)
        cases = {
            'case-variant username': {'username': 'COORD'},
            'bad username chars': {'username': 'bad name'},
            'duplicate email': {'email': 'COORD@liverlink.test'},
            'weak password': {'password': '1234'},
            'password like username': {'password': 'Dr.Mona'},
            'missing first name': {'first_name': ''},
            'invalid job title': {'job_title': 'patient'},
        }
        for label, override in cases.items():
            with self.subTest(label):
                r = self.client.post('/api/users/', self.new_staff_payload(**override), format='json')
                self.assertEqual(r.status_code, 400, r.data)
        self.client.post('/api/users/', self.new_staff_payload(), format='json')
        r = self.client.post('/api/users/', self.new_staff_payload(username='another', email='', license_no='EG-123'),
                             format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('license_no', r.data)
        self.assertEqual(User.objects.filter(username__in=['another']).count(), 0)  # nothing half-created

    def test_job_title_required_on_create(self):
        self.as_user(self.admin)
        missing = self.new_staff_payload()
        del missing['job_title']
        for label, payload in (('missing', missing), ('blank', self.new_staff_payload(job_title='')),
                               ('null', self.new_staff_payload(job_title=None))):
            with self.subTest(label):
                r = self.client.post('/api/users/', payload, format='json')
                self.assertEqual(r.status_code, 400, r.data)
                self.assertEqual([str(m) for m in r.data['job_title']], ['Choose a job title.'])
        self.assertFalse(User.objects.filter(username='Dr.Mona').exists())  # nothing created
        self.assertFalse(Staff.objects.filter(user__username='Dr.Mona').exists())

    def test_staff_password_similarity_check_unchanged(self):
        # The relaxation applies only to patient self-registration.
        self.as_user(self.admin)
        r = self.client.post('/api/users/', self.new_staff_payload(password='Dr.Mona2026'), format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('password', r.data)

    def test_role_cannot_be_injected(self):
        self.as_user(self.admin)
        r = self.client.post('/api/users/', self.new_staff_payload(role='admin', is_superuser=True, is_staff=True),
                             format='json')
        self.assertEqual(r.status_code, 201)
        user = User.objects.get(username='Dr.Mona')
        self.assertEqual((user.role, user.is_superuser, user.is_staff), ('clinical_staff', False, False))

    # ---- edit / assign job title
    def test_assign_job_title_to_account_without_profile(self):
        self.as_user(self.admin)
        url = f'/api/users/{self.nojob.pk}/'
        r = self.client.patch(url, {'job_title': 'hepatologist'}, format='json')
        self.assertEqual(r.status_code, 400)  # needs first/last name first
        r = self.client.patch(url, {'job_title': 'hepatologist', 'first_name': 'Test', 'last_name': 'Admin'},
                              format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.nojob.refresh_from_db()
        self.assertEqual(effective_job_title(self.nojob), 'hepatologist')
        self.assertIn('consents.record', capabilities_for(self.nojob))

    def test_staff_details_need_job_title_first(self):
        self.as_user(self.admin)
        r = self.client.patch(f'/api/users/{self.nojob.pk}/', {'department': 'X'}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_change_job_title_moves_role(self):
        self.as_user(self.admin)
        r = self.client.patch(f'/api/users/{self.coord.pk}/', {'job_title': 'billing_admin'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual((r.data['role'], r.data['job_title']), ('admin', 'billing_admin'))

    def test_cannot_edit_patient_accounts_or_own_title(self):
        self.as_user(self.admin)
        self.assertEqual(self.client.patch(f'/api/users/{self.patient.pk}/', {'first_name': 'X'},
                                           format='json').status_code, 400)
        r = self.client.patch(f'/api/users/{self.admin.pk}/', {'job_title': 'hepatologist'}, format='json')
        self.assertEqual(r.status_code, 400)
        r = self.client.patch(f'/api/users/{self.admin.pk}/', {'department': 'IT'}, format='json')
        self.assertEqual(r.status_code, 200)

    def test_superuser_protected_from_non_superuser_admin(self):
        self.as_user(self.admin)
        self.assertEqual(self.client.patch(f'/api/users/{self.root.pk}/', {'first_name': 'X'},
                                           format='json').status_code, 400)
        self.assertEqual(self.client.post(f'/api/users/{self.root.pk}/deactivate/').status_code, 403)
        self.root.refresh_from_db()
        self.assertTrue(self.root.is_active)

    def test_put_not_allowed(self):
        self.as_user(self.admin)
        self.assertEqual(self.client.put(f'/api/users/{self.coord.pk}/', {}, format='json').status_code, 405)

    # ---- activation
    def test_deactivate_and_reactivate(self):
        refresh = RefreshToken.for_user(self.coord)
        access = str(refresh.access_token)
        self.as_user(self.admin)
        r = self.client.post(f'/api/users/{self.coord.pk}/deactivate/')
        self.assertEqual((r.status_code, r.data['is_active']), (200, False))
        self.client.force_authenticate(None)
        # cannot log in, refresh revoked, existing access token rejected
        self.assertEqual(self.client.post('/api/auth/token/', {'username': 'coord', 'password': PW},
                                          format='json').status_code, 401)
        self.assertEqual(self.client.post('/api/auth/token/refresh/', {'refresh': str(refresh)},
                                          format='json').status_code, 401)
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        self.assertEqual(c.get('/api/auth/me/').status_code, 401)
        self.as_user(self.admin)
        r = self.client.post(f'/api/users/{self.coord.pk}/activate/')
        self.assertEqual((r.status_code, r.data['is_active']), (200, True))

    def test_patient_accounts_can_be_deactivated(self):
        self.as_user(self.admin)
        self.assertEqual(self.client.post(f'/api/users/{self.patient.pk}/deactivate/').status_code, 200)

    def test_cannot_deactivate_self(self):
        self.as_user(self.admin)
        self.assertEqual(self.client.post(f'/api/users/{self.admin.pk}/deactivate/').status_code, 400)

    def test_unknown_user_404(self):
        self.as_user(self.admin)
        self.assertEqual(self.client.get('/api/users/999999/').status_code, 404)
        self.assertEqual(self.client.post('/api/users/999999/deactivate/').status_code, 404)


class StaffManagementAuditTests(APITestCase):
    """Staff account create / update / activate / deactivate each write one audit entry."""

    def setUp(self):
        cache.clear()
        self.admin = make_staff('boss', T.SUPER_ADMIN)
        self.coord = make_staff('coord', T.TRANSPLANT_COORDINATOR)
        self.client.force_authenticate(self.admin)

    def entries(self):
        return list(AuditLog.objects.order_by('id').values_list('user__username', 'action', 'entity_type',
                                                                 'entity_id', 'patient_id'))

    def test_create_update_deactivate_activate_are_logged(self):
        r = self.client.post('/api/users/', {
            'username': 'Dr.Mona', 'email': 'mona@liverlink.test', 'first_name': 'Mona', 'last_name': 'E',
            'password': 'Very-Strong-Pass!1', 'job_title': 'hepatologist', 'department': 'Hepatology',
            'license_no': 'EG-123'}, format='json')
        self.assertEqual(r.status_code, 201)
        new_id = r.data['id']
        self.client.patch(f'/api/users/{self.coord.pk}/', {'department': 'Transplant Unit'}, format='json')
        self.client.post(f'/api/users/{self.coord.pk}/deactivate/')
        self.client.post(f'/api/users/{self.coord.pk}/activate/')
        self.assertEqual(self.entries(), [
            ('boss', 'create', 'accounts.user', new_id, None),
            ('boss', 'update', 'accounts.user', self.coord.pk, None),
            ('boss', 'deactivate', 'accounts.user', self.coord.pk, None),
            ('boss', 'activate', 'accounts.user', self.coord.pk, None),
        ])
        stored = ' '.join(str(v) for e in AuditLog.objects.values() for v in e.values())
        self.assertNotIn('Very-Strong-Pass', stored)
        self.assertNotIn('Transplant Unit', stored)  # field values are never stored

    def test_noop_and_failed_requests_are_not_logged(self):
        self.client.post(f'/api/users/{self.coord.pk}/activate/')               # already active
        self.client.patch(f'/api/users/{self.coord.pk}/', {}, format='json')    # nothing changed
        self.client.post(f'/api/users/{self.admin.pk}/deactivate/')              # self: refused
        self.client.post('/api/users/', {'username': 'x'}, format='json')        # invalid
        self.client.get('/api/users/', {'search': 'coord'})                      # list/search
        self.client.get(f'/api/users/{self.coord.pk}/')
        self.client.force_authenticate(self.coord)                                # no users.manage
        self.client.post(f'/api/users/{self.admin.pk}/deactivate/')
        self.assertEqual(AuditLog.objects.count(), 0)


class AuditLogModelTests(TestCase):
    """AuditLog is append-only and references users/patients that cannot be deleted."""

    def setUp(self):
        import datetime as _dt

        from apps.registry.models import Patient

        self.user = make_staff('coord', T.TRANSPLANT_COORDINATOR)
        self.patient = Patient.objects.create(
            first_name='Hoda', last_name='Salem', date_of_birth=_dt.date(1965, 1, 1), sex='female',
            phone='0100', category='liver_patient')

    def entry(self, **over):
        data = dict(user=self.user, action='view', entity_type='registry.patient',
                    entity_id=self.patient.pk, patient=self.patient, ip_address='10.0.0.5')
        data.update(over)
        action, entity_type = data.pop('action'), data.pop('entity_type')
        return AuditLog.record(action, entity_type, **data)

    def test_record_and_relations(self):
        log = self.entry()
        self.assertIsNotNone(log.timestamp)
        self.assertEqual(list(self.user.audit_logs.all()), [log])
        self.assertEqual(list(self.patient.audit_logs.all()), [log])
        login = self.entry(action='login', entity_type='accounts.user', entity_id=self.user.pk, patient=None,
                           ip_address='2001:db8::1')
        self.assertIsNone(login.patient)
        self.assertEqual(list(AuditLog.objects.all()), [login, log])  # newest first

    def test_rows_cannot_be_changed_or_deleted(self):
        log = self.entry()
        log.action = 'update'
        with self.assertRaises(PermissionError):
            log.save()
        with self.assertRaises(PermissionError):
            log.delete()
        with self.assertRaises(PermissionError):
            AuditLog.objects.filter(pk=log.pk).update(action='delete')
        with self.assertRaises(PermissionError):
            AuditLog.objects.all().delete()
        self.assertEqual(AuditLog.objects.get(pk=log.pk).action, 'view')

    def test_new_actions_accepted_by_database(self):
        for action in ('profile_view', 'category_change', 'activate', 'deactivate'):
            self.assertEqual(self.entry(action=action).action, action)

    def test_action_check_in_database(self):
        from django.db import IntegrityError, transaction
        with self.assertRaises(IntegrityError), transaction.atomic():
            AuditLog.objects.create(user=self.user, action='hack', entity_type='x')

    def test_referenced_user_and_patient_are_protected(self):
        from django.db.models import ProtectedError
        self.entry()
        with self.assertRaises(ProtectedError):
            self.patient.delete()
        with self.assertRaises(ProtectedError):
            User.objects.filter(pk=self.user.pk).delete()
        self.assertEqual(AuditLog.objects.count(), 1)

    def test_actor_defaults_to_username_snapshot(self):
        self.assertEqual(self.entry().actor, 'coord')

    def test_anonymous_event_with_actor(self):
        from django.contrib.auth.models import AnonymousUser
        log = AuditLog.record('login', 'accounts.user', user=AnonymousUser(), actor='  unknown.user  ',
                              ip_address='192.0.2.10')
        self.assertIsNone(log.user)
        self.assertEqual(log.actor, 'unknown.user')

    def test_every_entry_identifies_who_acted(self):
        from django.db import IntegrityError, transaction
        with self.assertRaises(IntegrityError), transaction.atomic():
            AuditLog.objects.create(user=None, actor='', action='view', entity_type='x')

    def test_admin_is_read_only(self):
        from django.contrib.admin.sites import site
        model_admin = site._registry[AuditLog]
        self.assertFalse(model_admin.has_add_permission(None))
        self.assertFalse(model_admin.has_change_permission(None))
        self.assertFalse(model_admin.has_delete_permission(None))


class AuditLogViewerAPITests(APITestCase):
    """GET /api/audit-logs/: Super Admin only, read-only, paginated, filterable."""

    URL = '/api/audit-logs/'

    def setUp(self):
        import datetime as _dt
        from django.utils import timezone
        from apps.registry.models import Patient
        cache.clear()
        self.admin = make_staff('boss', T.SUPER_ADMIN)
        self.root = User.objects.create_superuser('root', '', PW)
        self.coord = make_staff('coord', T.TRANSPLANT_COORDINATOR)
        self.patient = Patient.objects.create(
            first_name='Hoda', last_name='Salem', date_of_birth=_dt.date(1965, 1, 1), sex='female',
            phone='0100', category='liver_patient')

        def day(d):
            return timezone.make_aware(_dt.datetime(2026, 3, d, 10, 0))

        def add(action, entity_type, when, user=self.coord, **extra):
            return AuditLog.objects.create(user=user, actor=user.username, action=action,
                                           entity_type=entity_type, timestamp=when, **extra)

        P = 'registry.patient'
        self.e_profile = add('profile_view', P, day(1), entity_id=self.patient.pk, patient=self.patient,
                             ip_address='10.0.0.5')
        self.e_category = add('category_change', P, day(2), entity_id=self.patient.pk, patient=self.patient)
        self.e_staff = add('deactivate', 'accounts.user', day(3), user=self.admin, entity_id=self.coord.pk)
        self.e_create = add('create', P, day(4), entity_id=self.patient.pk, patient=self.patient)

    def get(self, as_user=None, **params):
        self.client.force_authenticate(as_user or self.admin)
        return self.client.get(self.URL, params)

    def ids(self, response):
        self.assertEqual(response.status_code, 200, response.data)
        return [row['id'] for row in response.data['results']]

    # ---- permissions
    def test_only_super_admin_can_view(self):
        self.assertEqual(self.get(self.admin).status_code, 200)
        self.assertEqual(self.get(self.root).status_code, 200)  # superuser without profile = super_admin
        others = [self.coord, make_staff('hep', T.HEPATOLOGIST), make_staff('bill', T.BILLING_ADMIN),
                  make_staff('rad', T.RADIOLOGIST), make_staff('surg', T.TRANSPLANT_SURGEON),
                  make_user('nojob', User.Role.CLINICAL_STAFF), make_user('pat', User.Role.PATIENT)]
        for user in others:
            with self.subTest(user=user.username):
                self.assertEqual(self.get(user).status_code, 403)
        inactive = make_staff('oldboss', T.SUPER_ADMIN, is_active=False)
        self.assertEqual(self.get(inactive).status_code, 403)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(self.URL).status_code, 401)

    def test_read_only(self):
        self.client.force_authenticate(self.admin)
        for method in ('post', 'put', 'patch', 'delete'):
            with self.subTest(method=method):
                self.assertEqual(getattr(self.client, method)(self.URL, {}, format='json').status_code, 405)
            with self.subTest(method=f'{method} detail'):
                self.assertEqual(getattr(self.client, method)(f'{self.URL}{self.e_create.pk}/', {},
                                                              format='json').status_code, 404)
        self.assertEqual(AuditLog.objects.count(), 4)

    def test_viewing_the_log_is_not_logged(self):
        self.get()
        self.get(action='create')
        self.assertEqual(AuditLog.objects.count(), 4)

    # ---- content
    def test_entry_fields_newest_first(self):
        r = self.get()
        self.assertEqual(self.ids(r), [self.e_create.pk, self.e_staff.pk, self.e_category.pk, self.e_profile.pk])
        rows = {row['id']: row for row in r.data['results']}
        profile = rows[self.e_profile.pk]
        self.assertEqual({k: profile[k] for k in ('actor', 'user_id', 'action', 'action_label', 'is_read',
                                                  'entity_type', 'entity_id', 'ip_address')},
                         {'actor': 'coord', 'user_id': self.coord.pk, 'action': 'profile_view',
                          'action_label': 'Profile view', 'is_read': True, 'entity_type': 'registry.patient',
                          'entity_id': self.patient.pk, 'ip_address': '10.0.0.5'})
        self.assertEqual(profile['patient'], {'id': self.patient.pk, 'mrn': self.patient.mrn, 'name': 'Hoda Salem'})
        self.assertTrue(profile['timestamp'].startswith('2026-03-01T10:00'))
        staff = rows[self.e_staff.pk]
        self.assertEqual((staff['patient'], staff['is_read'], staff['actor']), (None, False, 'boss'))

    # ---- pagination
    def test_pagination(self):
        r = self.get(page_size=3)
        self.assertEqual((r.data['count'], len(r.data['results'])), (4, 3))
        self.assertIsNotNone(r.data['next'])
        r2 = self.get(page_size=3, page=2)
        self.assertEqual(self.ids(r2), [self.e_profile.pk])
        self.assertIsNone(r2.data['next'])
        self.assertEqual(self.get(page=99).status_code, 404)
        self.assertEqual(len(self.get(page_size=10_000).data['results']), 4)  # capped at max_page_size

    # ---- filters
    def test_filters(self):
        cases = {
            'action': ({'action': 'category_change'}, [self.e_category]),
            'kind read': ({'kind': 'read'}, [self.e_profile]),
            'kind write': ({'kind': 'write'}, [self.e_create, self.e_staff, self.e_category]),
            'user': ({'user': self.admin.pk}, [self.e_staff]),
            'patient': ({'patient': self.patient.pk}, [self.e_create, self.e_category, self.e_profile]),
            'entity_type': ({'entity_type': 'accounts.user'}, [self.e_staff]),
            'entity_id': ({'entity_type': 'accounts.user', 'entity_id': self.coord.pk}, [self.e_staff]),
            'date_from': ({'date_from': '2026-03-03'}, [self.e_create, self.e_staff]),
            'date_to': ({'date_to': '2026-03-02'}, [self.e_category, self.e_profile]),
            'date range': ({'date_from': '2026-03-02', 'date_to': '2026-03-03'},
                           [self.e_staff, self.e_category]),
            'single day': ({'date_from': '2026-03-04', 'date_to': '2026-03-04'}, [self.e_create]),
            'combined': ({'patient': self.patient.pk, 'kind': 'write', 'date_to': '2026-03-03'},
                         [self.e_category]),
            'no match': ({'user': 999999}, []),
        }
        for name, (params, expected) in cases.items():
            with self.subTest(name):
                self.assertEqual(self.ids(self.get(**params)), [e.pk for e in expected])

    def test_invalid_filters_rejected(self):
        for params in ({'action': 'hack'}, {'kind': 'other'}, {'user': 'abc'}, {'patient': '-1'},
                       {'date_from': '2026-13-01'}, {'date_from': '2026-03-05', 'date_to': '2026-03-01'}):
            with self.subTest(params=params):
                self.assertEqual(self.get(**params).status_code, 400)
