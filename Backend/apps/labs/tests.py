"""Laboratory API tests."""
import datetime
from decimal import Decimal

from django.core.cache import cache
from rest_framework.test import APITestCase

from apps.accounts.models import AuditLog, Staff, User
from apps.emr.models import Encounter
from apps.registry.models import Patient

from .models import LabOrder, LabResult, LabTest

PW = 'Str0ng-Pass!2026'
T = Staff.JobTitle


def make_staff(username, job_title):
    user = User.objects.create_user(username, f'{username}@lh.test', PW, role=Staff.role_for_job_title(job_title),
                                    first_name=username.title(), last_name='Staff')
    Staff.objects.create(user=user, job_title=job_title)
    return user


def make_patient(**over):
    data = dict(first_name='Hoda', last_name='Salem', date_of_birth=datetime.date(1965, 1, 1), sex='female',
                phone='01001234567', category='liver_patient')
    data.update(over)
    return Patient.objects.create(**data)


class FlagTests(APITestCase):
    def test_flags(self):
        t = LabTest.objects.create(code='X', name='X', normal_min=10, normal_max=20, critical_max=100)
        self.assertEqual(t.compute_flag(None), '')
        self.assertEqual(t.compute_flag(Decimal('15')), 'normal')
        self.assertEqual(t.compute_flag(Decimal('5')), 'low')
        self.assertEqual(t.compute_flag(Decimal('25')), 'high')
        self.assertEqual(t.compute_flag(Decimal('100')), 'critical')


class LabApiTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.doctor = make_staff('doc', T.HEPATOLOGIST)
        self.coord = make_staff('coord', T.TRANSPLANT_COORDINATOR)
        self.billing = make_staff('bill', T.BILLING_ADMIN)
        self.patient = make_patient()
        self.encounter = Encounter.objects.create(patient=self.patient, staff=self.doctor.staff_profile)
        self.pat_user = User.objects.create_user('pat', 'pat@lh.test', PW, role='patient')
        self.patient.user = self.pat_user
        self.patient.save()
        self.bili = LabTest.objects.create(code='1975-2', name='Bilirubin', unit='mg/dL',
                                           normal_min=Decimal('0.1'), normal_max=Decimal('1.2'))
        self.alt = LabTest.objects.create(code='1742-6', name='ALT', normal_min=7, normal_max=56)

    def order(self, tests=None, priority='routine', encounter=None):
        self.client.force_authenticate(self.doctor)
        r = self.client.post('/api/lab/orders/', {'patient': self.patient.pk,
                                                  'encounter': (encounter or self.encounter).pk,
                                                  'priority': priority,
                                                  'tests': [t.pk for t in (tests or [self.bili, self.alt])]},
                             format='json')
        self.assertEqual(r.status_code, 201, r.data)
        return r.data

    def test_order_creates_pending_results_and_audit(self):
        data = self.order()
        self.assertEqual(data['status'], 'ordered')
        self.assertEqual(data['encounter'], self.encounter.pk)
        self.assertEqual(len(data['results']), 2)
        self.assertTrue(all(x['is_pending'] for x in data['results']))
        self.assertTrue(AuditLog.objects.filter(entity_type='labs.laborder', action='create').exists())

    def test_only_doctors_order(self):
        for user in (self.coord, self.billing, self.pat_user):
            self.client.force_authenticate(user)
            r = self.client.post('/api/lab/orders/', {'patient': self.patient.pk, 'tests': [self.bili.pk]},
                                 format='json')
            self.assertEqual(r.status_code, 403)

    def test_order_list_and_filters(self):
        self.order(priority='urgent')
        self.order(priority='routine')
        for user in (self.doctor, self.coord):
            self.client.force_authenticate(user)
            r = self.client.get('/api/lab/orders/')
            self.assertEqual(r.status_code, 200, r.data)
            self.assertEqual(r.data['count'], 2)
        self.assertEqual(self.client.get('/api/lab/orders/?priority=urgent').data['count'], 1)
        self.assertEqual(self.client.get(f'/api/lab/orders/?patient={self.patient.pk}&status=ordered').data['count'], 2)
        self.assertEqual(self.client.get('/api/lab/orders/?status=resulted').data['count'], 0)
        self.client.force_authenticate(self.billing)
        self.assertEqual(self.client.get('/api/lab/orders/').status_code, 403)

    def test_order_detail_and_catalog(self):
        data = self.order()
        self.client.force_authenticate(self.coord)
        r = self.client.get(f"/api/lab/orders/{data['id']}/")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(len(r.data['results']), 2)
        tests = self.client.get('/api/lab/tests/')
        self.assertEqual(tests.status_code, 200)
        self.assertEqual(len(tests.data), 2)
        self.client.force_authenticate(self.pat_user)
        self.assertEqual(self.client.get('/api/lab/tests/').status_code, 403)

    def test_duplicate_test_rejected(self):
        self.client.force_authenticate(self.doctor)
        r = self.client.post('/api/lab/orders/', {'patient': self.patient.pk, 'tests': [self.bili.pk, self.bili.pk]},
                             format='json')
        self.assertEqual(r.status_code, 400)

    def test_orders_require_the_treating_doctors_open_matching_encounter(self):
        payload = {'patient': self.patient.pk, 'encounter': self.encounter.pk, 'tests': [self.bili.pk]}
        self.client.force_authenticate(self.doctor)
        self.assertEqual(self.client.post('/api/lab/orders/', {'patient': self.patient.pk,
                             'tests': [self.bili.pk]}, format='json').status_code, 400)
        other_encounter = Encounter.objects.create(patient=self.patient, staff=self.coord.staff_profile)
        self.assertEqual(self.client.post('/api/lab/orders/', {**payload, 'encounter': other_encounter.pk},
                             format='json').status_code, 400)
        other_patient = make_patient(first_name='Other', phone='01009999999')
        self.assertEqual(self.client.post('/api/lab/orders/', {'patient': other_patient.pk,
                             'encounter': self.encounter.pk, 'tests': [self.bili.pk]},
                             format='json').status_code, 400)
        self.encounter.status = Encounter.Status.SIGNED
        self.encounter.save(update_fields=['status'])
        self.assertEqual(self.client.post('/api/lab/orders/', payload, format='json').status_code, 400)

    def test_result_entry_flags_and_status_flow(self):
        data = self.order()
        ids = {x['test_code']: x['id'] for x in data['results']}
        self.client.force_authenticate(self.coord)
        r = self.client.post(f"/api/lab/results/{ids['1975-2']}/enter/", {'value': '3.4'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['flag'], 'high')
        self.assertEqual(LabOrder.objects.get(pk=data['id']).status, 'partially_resulted')
        self.client.post(f"/api/lab/results/{ids['1742-6']}/enter/", {'value': '30'}, format='json')
        self.assertEqual(LabOrder.objects.get(pk=data['id']).status, 'resulted')

    def test_billing_cannot_enter_results(self):
        data = self.order()
        self.client.force_authenticate(self.billing)
        r = self.client.post(f"/api/lab/results/{data['results'][0]['id']}/enter/", {'value': '1'}, format='json')
        self.assertEqual(r.status_code, 403)

    def test_pending_list_urgent_first_and_shrinks(self):
        self.order(priority='routine')
        self.order(tests=[self.alt], priority='urgent')
        self.client.force_authenticate(self.doctor)
        r = self.client.get('/api/lab/pending/')
        self.assertEqual(r.data['count'], 3)
        self.assertEqual(r.data['results'][0]['priority'], 'urgent')
        res = LabResult.objects.filter(lab_order__priority='urgent').first()
        self.client.force_authenticate(self.coord)
        self.client.post(f'/api/lab/results/{res.pk}/enter/', {'value': '20'}, format='json')
        self.client.force_authenticate(self.doctor)
        self.assertEqual(self.client.get('/api/lab/pending/').data['count'], 2)

    def test_cancel_rules(self):
        data = self.order()
        self.client.force_authenticate(self.doctor)
        self.assertEqual(self.client.post(f"/api/lab/orders/{data['id']}/cancel/").status_code, 200)
        self.assertEqual(self.client.post(f"/api/lab/orders/{data['id']}/cancel/").status_code, 400)
        self.assertEqual(self.client.get('/api/lab/pending/').data['count'], 0)
        self.client.force_authenticate(self.coord)
        r = self.client.post(f"/api/lab/results/{data['results'][0]['id']}/enter/", {'value': '1'}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_patient_sees_only_released_results(self):
        data = self.order(tests=[self.bili])
        rid = data['results'][0]['id']
        self.client.force_authenticate(self.coord)
        self.client.post(f'/api/lab/results/{rid}/enter/', {'value': '2.0'}, format='json')
        self.client.force_authenticate(self.pat_user)
        self.assertEqual(self.client.get('/api/lab/my/results/').data['count'], 0)
        self.client.force_authenticate(self.doctor)
        self.assertEqual(self.client.post(f"/api/lab/orders/{data['id']}/release/").status_code, 200)
        self.client.force_authenticate(self.pat_user)
        self.assertEqual(self.client.get('/api/lab/my/results/').data['count'], 1)
        self.assertEqual(len(self.client.get('/api/lab/my/trends/?test=1975-2').data['points']), 1)
        # Patients cannot use staff endpoints.
        self.assertEqual(self.client.get(f'/api/lab/patients/{self.patient.pk}/results/').status_code, 403)

    def test_cancelled_partial_order_hidden_and_not_releasable(self):
        data = self.order()
        self.client.force_authenticate(self.coord)
        self.client.post(f"/api/lab/results/{data['results'][0]['id']}/enter/", {'value': '2'}, format='json')
        self.client.force_authenticate(self.doctor)
        LabResult.objects.filter(lab_order_id=data['id'], value__isnull=False).update(is_released=True)
        self.assertEqual(self.client.post(f"/api/lab/orders/{data['id']}/cancel/").status_code, 200)
        self.assertEqual(self.client.post(f"/api/lab/orders/{data['id']}/release/").status_code, 400)
        self.client.force_authenticate(self.pat_user)
        self.assertEqual(self.client.get('/api/lab/my/results/').data['count'], 0)

    def test_negative_value_rejected(self):
        data = self.order()
        self.client.force_authenticate(self.coord)
        r = self.client.post(f"/api/lab/results/{data['results'][0]['id']}/enter/", {'value': '-1'}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_patient_sees_own_orders_without_values(self):
        data = self.order()  # bilirubin + ALT
        ids = {x['test_code']: x['id'] for x in data['results']}
        other = make_patient(first_name='Other', phone='01009999999')
        self.client.force_authenticate(self.doctor)
        self.client.post('/api/lab/orders/', {'patient': other.pk, 'tests': [self.alt.pk]}, format='json')

        self.client.force_authenticate(self.pat_user)
        r = self.client.get('/api/lab/my/orders/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 1)  # not the other patient's order
        self.assertEqual({t['state'] for t in r.data['results'][0]['tests']}, {'pending'})

        self.client.force_authenticate(self.coord)
        self.client.post(f"/api/lab/results/{ids['1975-2']}/enter/", {'value': '3.0'}, format='json')
        self.client.force_authenticate(self.pat_user)
        tests = self.client.get('/api/lab/my/orders/').data['results'][0]['tests']
        states = {t['test_name']: t['state'] for t in tests}
        self.assertEqual(states, {'Bilirubin': 'awaiting_review', 'ALT': 'pending'})
        self.assertNotIn('value', tests[0])
        self.assertNotIn('flag', tests[0])

        self.client.force_authenticate(self.doctor)
        self.client.post(f"/api/lab/orders/{data['id']}/release/")
        self.client.force_authenticate(self.pat_user)
        tests = self.client.get('/api/lab/my/orders/').data['results'][0]['tests']
        self.assertEqual({t['test_name']: t['state'] for t in tests}['Bilirubin'], 'available')

        # Staff cannot use the patient endpoint.
        self.client.force_authenticate(self.doctor)
        self.assertEqual(self.client.get('/api/lab/my/orders/').status_code, 403)

    def test_patient_orders_can_be_filtered_by_encounter(self):
        first = self.order()
        other_encounter = Encounter.objects.create(patient=self.patient, staff=self.doctor.staff_profile)
        second = self.order(encounter=other_encounter)
        self.client.force_authenticate(self.pat_user)

        first_response = self.client.get(f'/api/lab/my/orders/?encounter={self.encounter.pk}')
        self.assertEqual(first_response.status_code, 200)
        self.assertEqual([order['id'] for order in first_response.data['results']], [first['id']])

        second_response = self.client.get(f'/api/lab/my/orders/?encounter={other_encounter.pk}')
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual([order['id'] for order in second_response.data['results']], [second['id']])

    def test_release_requires_results(self):
        data = self.order()
        self.client.force_authenticate(self.doctor)
        self.assertEqual(self.client.post(f"/api/lab/orders/{data['id']}/release/").status_code, 400)

    def test_trends_for_staff(self):
        for value in ('1.0', '2.5'):
            data = self.order(tests=[self.bili])
            self.client.force_authenticate(self.coord)
            self.client.post(f"/api/lab/results/{data['results'][0]['id']}/enter/", {'value': value}, format='json')
        self.client.force_authenticate(self.doctor)
        r = self.client.get(f'/api/lab/patients/{self.patient.pk}/trends/?test=1975-2')
        self.assertEqual([p['value'] for p in r.data['points']], [1.0, 2.5])
        self.assertEqual(r.data['points'][1]['flag'], 'high')
        self.assertEqual(self.client.get(f'/api/lab/patients/{self.patient.pk}/trends/').status_code, 400)
        self.assertEqual(self.client.get(f'/api/lab/patients/{self.patient.pk}/results/').data['count'], 2)

    def test_unauthenticated(self):
        self.assertEqual(self.client.get('/api/lab/orders/').status_code, 401)
