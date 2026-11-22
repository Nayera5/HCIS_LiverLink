from django.test import SimpleTestCase
from rest_framework.test import APITestCase

from apps.accounts.models import Staff
from apps.accounts.tests import make_staff

from .models import Service


class ServiceCodingFieldsTests(SimpleTestCase):
    def test_supported_coding_system_choices(self):
        self.assertEqual(
            list(Service.CodingSystem.values),
            ['snomed_ct', 'cpt', 'hcpcs', 'icd10_pcs'],
        )

    def test_new_service_category_choices(self):
        self.assertIn('medical_procedures', Service.Category.values)
        self.assertIn('inpatient_services', Service.Category.values)
        self.assertIn('preventive_care', Service.Category.values)


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
