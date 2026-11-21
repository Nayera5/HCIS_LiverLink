"""Stage 4 API tests: patient registration & management (run locally on SQLite/PostgreSQL)."""
import datetime

from django.core.cache import cache
from rest_framework.test import APITestCase

from apps.accounts.models import AuditLog, Staff, User

from .models import Patient

PW = 'Str0ng-Pass!2026'
T = Staff.JobTitle


def make_staff(username, job_title):
    user = User.objects.create_user(username, f'{username}@lh.test', PW, role=Staff.role_for_job_title(job_title),
                                    first_name=username.title(), last_name='Staff')
    Staff.objects.create(user=user, job_title=job_title)
    return user


def patient_payload(**over):
    data = {'first_name': 'Samira', 'last_name': 'Hassan', 'date_of_birth': '1968-05-02', 'sex': 'female',
            'phone': '01001234567', 'category': 'liver_patient'}
    data.update(over)
    return data


def make_patient(**over):
    data = dict(first_name='Hoda', last_name='Salem', date_of_birth=datetime.date(1965, 1, 1), sex='female',
                phone='0100', category='liver_patient')
    data.update(over)
    return Patient.objects.create(**data)


class PatientAPITestBase(APITestCase):
    def setUp(self):
        cache.clear()
        self.root = User.objects.create_superuser('root', '', PW)            # super_admin (no profile)
        self.admin = make_staff('boss', T.SUPER_ADMIN)
        self.coord = make_staff('coord', T.TRANSPLANT_COORDINATOR)
        self.hep = make_staff('hep', T.HEPATOLOGIST)
        self.rad = make_staff('rad', T.RADIOLOGIST)
        self.surg = make_staff('surg', T.TRANSPLANT_SURGEON)
        self.billing = make_staff('bill', T.BILLING_ADMIN)
        self.nojob = User.objects.create_user('test_admin', '', PW, role='clinical_staff')
        self.pat_user = User.objects.create_user('pat', 'pat@lh.test', PW, role='patient')
        self.own = make_patient(first_name='Pat', last_name='Own', user=self.pat_user, phone='0111')
        self.other = make_patient(first_name='Other', last_name='Person', national_id='29001011234567')

    def as_(self, user):
        self.client.force_authenticate(user)


class PermissionMatrixTests(PatientAPITestBase):
    def test_list_and_detail_access(self):
        allowed = [self.root, self.admin, self.coord, self.hep, self.rad, self.surg, self.billing]
        for user in allowed:
            with self.subTest(user=user.username):
                self.as_(user)
                self.assertEqual(self.client.get('/api/patients/').status_code, 200)
                self.assertEqual(self.client.get(f'/api/patients/{self.other.pk}/').status_code, 200)
        for user in (self.nojob, self.pat_user):
            with self.subTest(user=user.username):
                self.as_(user)
                self.assertEqual(self.client.get('/api/patients/').status_code, 403)
                self.assertEqual(self.client.get(f'/api/patients/{self.other.pk}/').status_code, 403)
                self.assertEqual(self.client.get(f'/api/patients/{self.own.pk}/').status_code, 403)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get('/api/patients/').status_code, 401)

    def test_register_only_coordinator_and_super_admin(self):
        for user, code in ((self.coord, 201), (self.admin, 201), (self.root, 201), (self.hep, 403),
                           (self.rad, 403), (self.surg, 403), (self.billing, 403), (self.nojob, 403),
                           (self.pat_user, 403)):
            with self.subTest(user=user.username):
                self.as_(user)
                r = self.client.post('/api/patients/', patient_payload(first_name=user.username), format='json')
                self.assertEqual(r.status_code, code, r.data)

    def test_edit_only_coordinator_and_super_admin(self):
        for user, code in ((self.coord, 200), (self.admin, 200), (self.hep, 403), (self.rad, 403),
                           (self.billing, 403), (self.nojob, 403), (self.pat_user, 403)):
            with self.subTest(user=user.username):
                self.as_(user)
                r = self.client.patch(f'/api/patients/{self.other.pk}/', {'address': user.username}, format='json')
                self.assertEqual(r.status_code, code)

    def test_change_category_matrix(self):
        for user, code in ((self.coord, 200), (self.hep, 200), (self.admin, 200), (self.rad, 403),
                           (self.surg, 403), (self.billing, 403), (self.nojob, 403), (self.pat_user, 403)):
            with self.subTest(user=user.username):
                self.as_(user)
                r = self.client.post(f'/api/patients/{self.other.pk}/category/', {'category': 'recipient'},
                                     format='json')
                self.assertEqual(r.status_code, code)

    def test_no_put_or_delete(self):
        self.as_(self.admin)
        self.assertEqual(self.client.put(f'/api/patients/{self.other.pk}/', patient_payload(), format='json').status_code, 405)
        self.assertEqual(self.client.delete(f'/api/patients/{self.other.pk}/').status_code, 405)


class StaffRegistrationTests(PatientAPITestBase):
    def test_registers_record_without_account_and_generates_mrn(self):
        self.as_(self.coord)
        r = self.client.post('/api/patients/', patient_payload(national_id='28512120123456', blood_group='O+',
                                                               weight_kg='72.5', height_cm='165'), format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertRegex(r.data['mrn'], r'^LL-\d{6,}$')
        self.assertFalse(r.data['has_account'])
        self.assertIsNone(r.data['account_username'])
        self.assertEqual(r.data['registered_by']['job_title'], 'transplant_coordinator')
        patient = Patient.objects.get(pk=r.data['id'])
        self.assertIsNone(patient.user)
        self.assertEqual(patient.registered_by, self.coord.staff_profile)
        self.assertEqual(User.objects.filter(role='patient').count(), 1)  # no account was created

    def test_superuser_without_profile_has_no_registrar(self):
        self.as_(self.root)
        r = self.client.post('/api/patients/', patient_payload(), format='json')
        self.assertIsNone(r.data['registered_by'])

    def test_mrns_are_unique_and_sequential(self):
        self.as_(self.coord)
        mrns = [self.client.post('/api/patients/', patient_payload(first_name=f'P{i}'), format='json').data['mrn']
                for i in range(3)]
        numbers = [int(m.split('-')[1]) for m in mrns]
        self.assertEqual(numbers, [numbers[0], numbers[0] + 1, numbers[0] + 2])

    def test_protected_fields_rejected(self):
        self.as_(self.coord)
        for field, value in (('mrn', 'LL-123456'), ('user', self.pat_user.pk), ('registered_by', 1)):
            with self.subTest(field=field):
                r = self.client.post('/api/patients/', patient_payload(**{field: value}), format='json')
                self.assertEqual(r.status_code, 400)
                self.assertIn(field, r.data)

    def test_validation_errors(self):
        self.as_(self.coord)
        cases = {
            'national_id': {'national_id': '123'},
            'date_of_birth': {'date_of_birth': '2999-01-01'},
            'sex': {'sex': 'other'},
            'category': {'category': 'friend'},
            'weight_kg': {'weight_kg': '0'},
            'blood_group': {'blood_group': 'C+'},
            'first_name': {'first_name': '   '},
            'phone': {'phone': ''},
        }
        for field, override in cases.items():
            with self.subTest(field=field):
                r = self.client.post('/api/patients/', patient_payload(**override), format='json')
                self.assertEqual(r.status_code, 400)
                self.assertIn(field, r.data)
        r = self.client.post('/api/patients/', {'first_name': 'Only'}, format='json')
        self.assertEqual(r.status_code, 400)
        for missing in ('last_name', 'date_of_birth', 'sex', 'phone', 'category'):
            self.assertIn(missing, r.data)

    def test_duplicate_national_id_and_blank_allowed(self):
        self.as_(self.coord)
        r = self.client.post('/api/patients/', patient_payload(national_id='29001011234567'), format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('already exists', str(r.data['national_id']))
        for _ in range(2):  # many records may have no national ID
            r = self.client.post('/api/patients/', patient_payload(national_id='', blood_group=''), format='json')
            self.assertEqual(r.status_code, 201, r.data)
            self.assertIsNone(Patient.objects.get(pk=r.data['id']).national_id)
            self.assertIsNone(Patient.objects.get(pk=r.data['id']).blood_group)


class ListSearchDetailTests(PatientAPITestBase):
    def test_search_and_filters(self):
        make_patient(first_name='Samira', last_name='Nabil Hassan', category='recipient', phone='01099998888')
        make_patient(first_name='Omar', last_name='Youssef', category='donor', sex='male')
        self.as_(self.hep)
        names = lambda r: sorted(p['first_name'] for p in r.data['results'])
        self.assertEqual(names(self.client.get('/api/patients/', {'search': 'samira hassan'})), ['Samira'])
        self.assertEqual(names(self.client.get('/api/patients/', {'search': self.other.mrn.lower()})), ['Other'])
        self.assertEqual(names(self.client.get('/api/patients/', {'search': '2900101'})), ['Other'])
        self.assertEqual(names(self.client.get('/api/patients/', {'search': '9999888'})), ['Samira'])
        self.assertEqual(names(self.client.get('/api/patients/', {'category': 'donor'})), ['Omar'])
        self.assertEqual(names(self.client.get('/api/patients/', {'sex': 'male'})), ['Omar'])
        r = self.client.get('/api/patients/', {'ordering': '-created_at', 'page_size': 1})
        self.assertEqual((r.data['count'], r.data['results'][0]['first_name']), (4, 'Omar'))
        self.assertEqual(self.client.get('/api/patients/', {'category': 'bogus'}).data['count'], 4)

    def test_list_hides_sensitive_details_detail_shows_them(self):
        self.as_(self.rad)
        row = self.client.get('/api/patients/', {'search': 'Other'}).data['results'][0]
        self.assertNotIn('national_id', row)
        self.assertNotIn('address', row)
        detail = self.client.get(f'/api/patients/{self.other.pk}/').data
        self.assertEqual(detail['national_id'], '29001011234567')
        self.assertIn('age', detail)

    def test_summary_counts_only_and_not_audited(self):
        make_patient(first_name='R', category='recipient')
        for user, code in ((self.hep, 200), (self.billing, 200), (self.pat_user, 403), (self.nojob, 403)):
            with self.subTest(user=user.username):
                self.as_(user)
                self.assertEqual(self.client.get('/api/patients/summary/').status_code, code)
        self.as_(self.coord)
        r = self.client.get('/api/patients/summary/')
        self.assertEqual(r.data, {'total': 3, 'by_category': {'liver_patient': 2, 'recipient': 1, 'donor': 0}})
        self.assertEqual(AuditLog.objects.count(), 0)

    def test_unknown_patient_404(self):
        self.as_(self.coord)
        self.assertEqual(self.client.get('/api/patients/999999/').status_code, 404)
        self.assertEqual(self.client.post('/api/patients/999999/category/', {'category': 'donor'},
                                          format='json').status_code, 404)


class UpdateAndCategoryTests(PatientAPITestBase):
    def test_demographic_update_keeps_mrn_and_category(self):
        self.as_(self.coord)
        mrn, category = self.other.mrn, self.other.category
        r = self.client.patch(f'/api/patients/{self.other.pk}/', {'weight_kg': '81.40', 'blood_group': 'A-',
                                                                 'emergency_contact': 'Sister 0100'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual((r.data['mrn'], r.data['category'], r.data['weight_kg']), (mrn, category, '81.40'))

    def test_update_rejects_protected_fields(self):
        self.as_(self.coord)
        for field, value in (('mrn', 'LL-000999'), ('category', 'donor'), ('user', self.pat_user.pk)):
            with self.subTest(field=field):
                r = self.client.patch(f'/api/patients/{self.other.pk}/', {field: value}, format='json')
                self.assertEqual(r.status_code, 400)
        self.other.refresh_from_db()
        self.assertEqual(self.other.category, 'liver_patient')

    def test_update_duplicate_national_id(self):
        self.as_(self.coord)
        r = self.client.patch(f'/api/patients/{self.own.pk}/', {'national_id': '29001011234567'}, format='json')
        self.assertEqual(r.status_code, 400)
        r = self.client.patch(f'/api/patients/{self.other.pk}/', {'national_id': '29001011234567'}, format='json')
        self.assertEqual(r.status_code, 200)  # its own value is fine

    def test_category_change(self):
        self.as_(self.hep)
        r = self.client.post(f'/api/patients/{self.other.pk}/category/', {'category': 'recipient'}, format='json')
        self.assertEqual((r.status_code, r.data['category']), (200, 'recipient'))
        r = self.client.post(f'/api/patients/{self.other.pk}/category/', {'category': 'nonsense'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.other.refresh_from_db()
        self.assertEqual(self.other.category, 'recipient')


class PatientPortalTests(PatientAPITestBase):
    def test_own_record(self):
        self.as_(self.pat_user)
        r = self.client.get('/api/patients/me/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual((r.data['id'], r.data['mrn']), (self.own.pk, self.own.mrn))
        self.assertNotIn('registered_by', r.data)

    def test_update_own_contact_details_only(self):
        self.as_(self.pat_user)
        r = self.client.patch('/api/patients/me/', {'phone': '0122', 'address': 'Cairo', 'emergency_contact': 'Wife'},
                              format='json')
        self.assertEqual((r.status_code, r.data['phone'], r.data['address']), (200, '0122', 'Cairo'))
        for field, value in (('category', 'recipient'), ('first_name', 'X'), ('date_of_birth', '1990-01-01'),
                             ('mrn', 'LL-1'), ('national_id', '29001011234568'), ('weight_kg', '50')):
            with self.subTest(field=field):
                r = self.client.patch('/api/patients/me/', {field: value}, format='json')
                self.assertEqual(r.status_code, 400)
        self.own.refresh_from_db()
        self.assertEqual((self.own.category, self.own.first_name), ('liver_patient', 'Pat'))
        self.assertEqual(self.client.patch('/api/patients/me/', {'phone': ' '}, format='json').status_code, 400)

    def test_patient_cannot_reach_other_records_or_category(self):
        self.as_(self.pat_user)
        self.assertEqual(self.client.get(f'/api/patients/{self.other.pk}/').status_code, 403)
        self.assertEqual(self.client.patch(f'/api/patients/{self.own.pk}/', {'phone': '1'}, format='json').status_code, 403)
        self.assertEqual(self.client.post(f'/api/patients/{self.own.pk}/category/', {'category': 'recipient'},
                                          format='json').status_code, 403)

    def test_staff_cannot_use_portal_endpoint(self):
        self.as_(self.coord)
        self.assertEqual(self.client.get('/api/patients/me/').status_code, 403)

    def test_patient_account_without_record(self):
        lonely = User.objects.create_user('lonely', '', PW, role='patient')
        self.as_(lonely)
        r = self.client.get('/api/patients/me/')
        self.assertEqual(r.status_code, 404)
        self.assertIn('No hospital record', r.data['detail'])


class SelfRegistrationTests(APITestCase):
    URL = '/api/patients/register/'

    def setUp(self):
        cache.clear()
        Patient.objects.create(first_name='Existing', last_name='Rec', date_of_birth='1970-01-01', sex='male',
                               phone='1', category='liver_patient', national_id='27001011234567')

    def payload(self, **over):
        data = {'username': 'Mona.Ali', 'password': 'Portal-Pass!2026', 'email': 'mona.ali@example.test',
                'first_name': 'Mona', 'last_name': 'Ali', 'date_of_birth': '1990-07-15', 'sex': 'female',
                'phone': '01011112222', 'category': 'donor'}
        data.update(over)
        return data

    def test_creates_account_and_record_atomically(self):
        r = self.client.post(self.URL, self.payload(), format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertRegex(r.data['mrn'], r'^LL-\d{6,}$')
        self.assertNotIn('password', r.data)
        user = User.objects.get(username='Mona.Ali')
        self.assertEqual((user.role, user.is_staff, user.is_superuser), ('patient', False, False))
        self.assertEqual(user.get_full_name(), 'Mona Ali')
        self.assertEqual(user.patient_profile.mrn, r.data['mrn'])
        self.assertIsNone(user.patient_profile.registered_by)
        r = self.client.post('/api/auth/token/', {'username': 'Mona.Ali', 'password': 'Portal-Pass!2026'}, format='json')
        self.assertEqual(r.status_code, 200)

    def test_recipient_category_not_allowed(self):
        r = self.client.post(self.URL, self.payload(category='recipient'), format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('category', r.data)

    def test_existing_national_id_rejected_and_nothing_created(self):
        r = self.client.post(self.URL, self.payload(national_id='27001011234567'), format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('contact the hospital', str(r.data['national_id']))
        self.assertFalse(User.objects.filter(username='Mona.Ali').exists())

    def test_national_id_optional(self):
        self.assertEqual(self.client.post(self.URL, self.payload(), format='json').status_code, 201)
        r = self.client.post(self.URL, self.payload(username='second', email='second@example.test', national_id=''),
                             format='json')
        self.assertEqual(r.status_code, 201)

    def test_account_validation(self):
        User.objects.create_user('taken', 'taken@example.test', 'x', role='patient')
        cases = {
            'username': {'username': 'TAKEN'},
            'email': {'email': 'TAKEN@example.test'},
            'password': {'password': '12345678'},
        }
        for field, override in cases.items():
            with self.subTest(field=field):
                r = self.client.post(self.URL, self.payload(**override), format='json')
                self.assertEqual(r.status_code, 400)
                self.assertIn(field, r.data)
        r = self.client.post(self.URL, self.payload(email=''), format='json')
        self.assertIn('email', r.data)  # email required for self-registration

    def test_password_may_contain_username(self):
        cases = (('Mona.Ali', 'Mona.Ali'), ('KarimSaad', 'KarimSaad2026'), ('hoda_m', 'my-hoda_m-pass'))
        for i, (username, password) in enumerate(cases):
            with self.subTest(password=password):
                r = self.client.post(self.URL, self.payload(username=username, password=password,
                                                            email=f'user{i}@example.test'), format='json')
                self.assertEqual(r.status_code, 201, r.data)
                self.client.force_authenticate(None)
                login = self.client.post('/api/auth/token/', {'username': username, 'password': password},
                                         format='json')
                self.assertEqual(login.status_code, 200)

    def test_password_may_resemble_name_and_email(self):
        r = self.client.post(self.URL, self.payload(password='mona.ali.example'), format='json')
        self.assertEqual(r.status_code, 201, r.data)

    def test_other_password_validators_still_apply(self):
        cases = {
            'too short': 'Ab1!xyz',
            'too common': 'password123',
            'entirely numeric': '4829163057',
        }
        for label, password in cases.items():
            with self.subTest(label):
                r = self.client.post(self.URL, self.payload(password=password), format='json')
                self.assertEqual(r.status_code, 400)
                self.assertIn('password', r.data)
        self.assertFalse(User.objects.filter(username='Mona.Ali').exists())

    def test_phone_required_and_exactly_11_digits(self):
        missing = self.payload()
        del missing['phone']
        bad = {'missing': missing, 'blank': self.payload(phone=''), 'spaces only': self.payload(phone='   '),
               'null': self.payload(phone=None), '10 digits': self.payload(phone='0101111222'),
               '12 digits': self.payload(phone='010111122223'), 'letters': self.payload(phone='0101111222a'),
               'plus sign': self.payload(phone='+2010111122'), 'dashes': self.payload(phone='010-1111-222'),
               'inner space': self.payload(phone='0101 111222'), 'arabic digits': self.payload(phone='٠١٠١١١١٢٢٢٢')}
        for label, payload in bad.items():
            with self.subTest(label):
                cache.clear()  # keep the signup rate limit out of this test
                r = self.client.post(self.URL, payload, format='json')
                self.assertEqual(r.status_code, 400, r.data)
                self.assertIn('11-digit', str(r.data['phone']))
        self.assertFalse(User.objects.filter(username='Mona.Ali').exists())

    def test_phone_stored_as_string_with_leading_zero(self):
        r = self.client.post(self.URL, self.payload(phone=' 01011112222 '), format='json')
        self.assertEqual(r.status_code, 201, r.data)
        phone = Patient.objects.get(user__username='Mona.Ali').phone
        self.assertEqual(phone, '01011112222')
        self.assertIsInstance(phone, str)

    def test_cannot_inject_privileges_or_protected_fields(self):
        for field, value in (('role', 'admin'), ('is_superuser', True), ('is_staff', True), ('mrn', 'LL-000001'),
                             ('registered_by', 1)):
            with self.subTest(field=field):
                r = self.client.post(self.URL, self.payload(**{field: value}), format='json')
                self.assertEqual(r.status_code, 400)
        self.assertFalse(User.objects.filter(username='Mona.Ali').exists())

    def test_rate_limited(self):
        codes = [self.client.post(self.URL, self.payload(username=f'u{i}', email=f'u{i}@example.test'),
                                  format='json').status_code for i in range(11)]
        self.assertEqual(codes[:10], [201] * 10)
        self.assertEqual(codes[10], 429)


class AuditTrailTests(PatientAPITestBase):
    def entries(self):
        return list(AuditLog.objects.order_by('id').values('user__username', 'actor', 'action', 'entity_id',
                                                            'patient_id', 'ip_address'))

    def test_reads_and_writes_are_audited_without_values(self):
        self.as_(self.coord)
        self.client.get('/api/patients/', {'search': 'Secret Name'})
        self.client.get(f'/api/patients/{self.other.pk}/')
        created = self.client.post('/api/patients/', patient_payload(), format='json').data['id']
        self.client.patch(f'/api/patients/{self.other.pk}/', {'address': 'x'}, format='json')
        self.client.post(f'/api/patients/{self.other.pk}/category/', {'category': 'donor'}, format='json')
        log = self.entries()
        self.assertEqual([e['action'] for e in log], ['view', 'view', 'create', 'update', 'update'])
        self.assertEqual([e['patient_id'] for e in log], [None, self.other.pk, created, self.other.pk, self.other.pk])
        self.assertTrue(all(e['user__username'] == 'coord' and e['actor'] == 'coord' for e in log))
        self.assertTrue(all(e['ip_address'] == '127.0.0.1' for e in log))
        stored = ' '.join(str(v) for e in AuditLog.objects.values() for v in e.values())
        self.assertNotIn('Secret', stored)  # search terms are not stored

    def test_denied_and_invalid_requests_are_not_logged_as_success(self):
        self.as_(self.pat_user)
        self.client.get(f'/api/patients/{self.other.pk}/')
        self.as_(self.coord)
        self.client.post('/api/patients/', patient_payload(national_id='1'), format='json')
        self.assertEqual(AuditLog.objects.count(), 0)

    def test_category_unchanged_is_not_logged(self):
        self.as_(self.hep)
        self.client.post(f'/api/patients/{self.other.pk}/category/', {'category': 'liver_patient'}, format='json')
        self.assertEqual(AuditLog.objects.count(), 0)

    def test_portal_and_self_registration_audited(self):
        self.as_(self.pat_user)
        self.client.get('/api/patients/me/')
        self.client.patch('/api/patients/me/', {'phone': '0199'}, format='json')
        self.client.force_authenticate(None)
        self.client.post('/api/patients/register/', {
            'username': 'newbie', 'password': 'Portal-Pass!2026', 'email': 'n@example.test', 'first_name': 'N',
            'last_name': 'B', 'date_of_birth': '1999-01-01', 'sex': 'male', 'phone': '01000000001',
            'category': 'liver_patient',
        }, format='json')
        log = self.entries()
        self.assertEqual([(e['user__username'], e['action']) for e in log],
                         [('pat', 'view'), ('pat', 'update'), ('newbie', 'create')])
        stored = ' '.join(str(v) for e in AuditLog.objects.values() for v in e.values())
        self.assertNotIn('Portal-Pass', stored)
