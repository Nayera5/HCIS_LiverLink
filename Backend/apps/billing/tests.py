from django.test import SimpleTestCase
from rest_framework.test import APITestCase

from apps.accounts.models import Staff
from apps.accounts.tests import make_staff

from .models import Service


class ServiceCodingFieldsTests(SimpleTestCase):
    def test_supported_coding_system_choices(self):
        self.assertEqual(
            list(Service.CodingSystem.values),
            ['snomed_ct', 'cpt', 'hcpcs', 'icd10_pcs', 'loinc'],
        )

    def test_new_service_category_choices(self):
        self.assertIn('medical_procedures', Service.Category.values)
        self.assertIn('inpatient_services', Service.Category.values)
        self.assertIn('preventive_care', Service.Category.values)
        self.assertNotIn('lab', Service.Category.values)
        self.assertNotIn('ai_analysis', Service.Category.values)


class ServiceListPaginationTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        Service.objects.all().delete()  # drop the catalog seeded by migration 0004
        cls.admin = make_staff('biller', Staff.JobTitle.BILLING_ADMIN)
        # 12 active + 3 inactive; names collide in pairs so ordering needs the id tie-breaker.
        cls.services = [
            Service.objects.create(code=f'SVC-{i:02d}', name=f'Service {i // 2:02d}', category='imaging',
                                   price=100, is_active=i < 12)
            for i in range(15)
        ]

    def setUp(self):
        self.client.force_authenticate(self.admin)

    def get(self, **params):
        return self.client.get('/api/services/', params)

    def codes(self, response):
        return [row['code'] for row in response.data['results']]

    def test_default_page_size_is_10(self):
        r = self.get()
        self.assertEqual(r.status_code, 200)
        self.assertEqual((r.data['count'], len(r.data['results'])), (15, 10))
        self.assertIsNotNone(r.data['next'])
        self.assertIsNone(r.data['previous'])

    def test_pages_are_stable_and_disjoint(self):
        first, second = self.get(page=1), self.get(page=2)
        self.assertEqual(self.codes(first) + self.codes(second), [s.code for s in self.services])
        self.assertIsNone(second.data['next'])

    def test_page_size_param_and_cap(self):
        self.assertEqual(len(self.get(page_size=4).data['results']), 4)
        self.assertEqual(len(self.get(page_size=10_000).data['results']), 15)  # capped at 100

    def test_filters_apply_before_paging(self):
        r = self.get(status='active', page_size=5, page=3)
        self.assertEqual(r.data['count'], 12)
        self.assertEqual(self.codes(r), ['SVC-10', 'SVC-11'])

    def test_out_of_range_page_is_404(self):
        self.assertEqual(self.get(page=99).status_code, 404)

    def test_billing_admin_can_manage_imaging_services_for_dynamic_picker(self):
        response = self.client.post('/api/services/', {
            'code': 'IMG-DYNAMIC', 'name': 'New Dynamic Imaging Service', 'category': 'imaging',
            'coding_system': 'cpt', 'standard_code': '70000', 'price': '1250.00',
        }, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        service_id = response.data['id']

        active = self.get(category='imaging', active_only='true', page_size=100)
        self.assertIn('IMG-DYNAMIC', self.codes(active))

        response = self.client.patch(f'/api/services/{service_id}/', {'is_active': False}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        inactive = self.get(category='imaging', active_only='true', page_size=100)
        self.assertNotIn('IMG-DYNAMIC', self.codes(inactive))

        response = self.client.patch(f'/api/services/{service_id}/', {'is_active': True}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        active = self.get(category='imaging', active_only='true', page_size=100)
        self.assertIn('IMG-DYNAMIC', self.codes(active))


class ServiceReadOnlyAccessTests(APITestCase):
    """The read-only Services page: clinical staff and patients may list services, never change them."""

    @classmethod
    def setUpTestData(cls):
        from apps.accounts.models import User
        from apps.accounts.tests import make_user

        cls.service = Service.objects.create(code='RO-01', name='Read-only check', category='imaging', price=100)
        cls.readers = [make_staff(f'ro_{title}', title) for title in (
            Staff.JobTitle.HEPATOLOGIST, Staff.JobTitle.RADIOLOGIST,
            Staff.JobTitle.TRANSPLANT_SURGEON, Staff.JobTitle.TRANSPLANT_COORDINATOR)]
        cls.readers.append(make_user('ro_patient', User.Role.PATIENT))
        cls.nojob = make_user('ro_nojob', User.Role.CLINICAL_STAFF)

    def test_readers_can_list_but_not_change(self):
        for user in self.readers:
            with self.subTest(user=user.username):
                self.client.force_authenticate(user)
                r = self.client.get('/api/services/', {'category': 'imaging'})
                self.assertEqual(r.status_code, 200)
                self.assertIn('RO-01', [row['code'] for row in r.data['results']])
                payload = {'code': 'X-1', 'name': 'X', 'category': 'imaging', 'price': 1}
                self.assertEqual(self.client.post('/api/services/', payload, format='json').status_code, 403)
                url = f'/api/services/{self.service.pk}/'
                self.assertEqual(self.client.patch(url, {'price': 5}, format='json').status_code, 403)

    def test_account_without_job_title_cannot_list(self):
        self.client.force_authenticate(self.nojob)
        self.assertEqual(self.client.get('/api/services/').status_code, 403)
