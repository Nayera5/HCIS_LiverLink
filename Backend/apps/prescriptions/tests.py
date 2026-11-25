"""Prescriptions & treatment plans API tests (Module 6)."""
import datetime
import io

from django.core.cache import cache
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import AuditLog, Staff, User
from apps.registry.models import Patient
from apps.transplant.models import TransplantCase

from .models import Drug, Prescription, TreatmentPlan

PW = 'Str0ng-Pass!2026'
T = Staff.JobTitle
TODAY = timezone.localdate()
D = datetime.timedelta


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


class Base(APITestCase):
    def setUp(self):
        cache.clear()
        self.doctor = make_staff('doc', T.HEPATOLOGIST)
        self.surgeon = make_staff('surg', T.TRANSPLANT_SURGEON)
        self.coord = make_staff('coord', T.TRANSPLANT_COORDINATOR)
        self.admin = make_staff('root', T.SUPER_ADMIN)
        self.billing = make_staff('bill', T.BILLING_ADMIN)
        self.patient = make_patient()
        self.pat_user = User.objects.create_user('pat', 'pat@lh.test', PW, role='patient')
        self.patient.user = self.pat_user
        self.patient.save()
        self.other = make_patient(first_name='Omar', phone='01009999999')
        self.tdf = Drug.objects.create(name='Tenofovir', default_route='oral', drug_class='Antiviral (HBV)')

    def as_(self, user):
        self.client.force_authenticate(user)

    def prescribe(self, user=None, **over):
        self.as_(user or self.doctor)
        data = dict(patient=self.patient.pk, drug=self.tdf.pk, dose='300 mg', route='oral',
                    frequency='once daily', start_date=str(TODAY))
        data.update(over)
        return self.client.post('/api/rx/prescriptions/', data, format='json')

    def plan(self, user=None, **over):
        self.as_(user or self.doctor)
        data = dict(patient=self.patient.pk, plan_type='surveillance', goals='Detect HCC early',
                    steps='US + AFP every 6 months', start_date=str(TODAY), review_date=str(TODAY + D(180)))
        data.update(over)
        return self.client.post('/api/rx/plans/', data, format='json')


class DrugCatalogTests(Base):
    def test_internal_code_assigned(self):
        self.assertRegex(self.tdf.code, r'^DRG-\d{4}$')
        self.assertEqual(Drug.objects.get(pk=self.tdf.pk).code, f'DRG-{self.tdf.pk:04d}')

    def test_autocomplete_search(self):
        Drug.objects.create(name='Tacrolimus', drug_class='Immunosuppressant')
        Drug.objects.create(name='Old drug', is_active=False)
        self.as_(self.coord)
        r = self.client.get('/api/rx/drugs/?q=taCro')
        self.assertEqual(r.status_code, 200)
        self.assertEqual([d['name'] for d in r.data], ['Tacrolimus'])
        self.assertEqual(len(self.client.get('/api/rx/drugs/').data), 2)  # inactive hidden
        self.as_(self.admin)
        self.assertEqual(len(self.client.get('/api/rx/drugs/?include_inactive=1').data), 3)

    def test_authorized_users_add_drugs(self):
        for i, user in enumerate((self.doctor, self.surgeon, self.admin)):
            self.as_(user)
            r = self.client.post('/api/rx/drugs/', {'name': f'New drug {i}', 'default_route': 'iv'}, format='json')
            self.assertEqual(r.status_code, 201, r.data)
            self.assertTrue(r.data['code'].startswith('DRG-'))
        self.assertEqual(AuditLog.objects.filter(entity_type='prescriptions.drug', action='create').count(), 3)
        for user in (self.coord, self.billing, self.pat_user):
            self.as_(user)
            self.assertEqual(self.client.post('/api/rx/drugs/', {'name': 'X'}, format='json').status_code, 403)

    def test_duplicate_name_rejected_case_insensitive(self):
        self.as_(self.doctor)
        r = self.client.post('/api/rx/drugs/', {'name': '  tenofovir '}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('name', r.data)

    def test_generic_name_duplicates_rejected(self):
        Drug.objects.create(name='Tacrolimus', generic_name='Tacrolimus')
        self.as_(self.doctor)
        # brand entry whose generic is already in the catalog
        r = self.client.post('/api/rx/drugs/', {'name': 'Prograf', 'generic_name': 'tacrolimus'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('generic_name', r.data)
        # new name equal to an existing generic name
        Drug.objects.create(name='Cellcept', generic_name='Mycophenolate')
        r = self.client.post('/api/rx/drugs/', {'name': 'mycophenolate'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('name', r.data)
        # a drug may keep its own generic name when edited
        d = Drug.objects.get(name='Cellcept')
        r = self.client.patch(f'/api/rx/drugs/{d.pk}/', {'generic_name': 'Mycophenolate', 'common_dose': '500 mg'},
                              format='json')
        self.assertEqual(r.status_code, 200, r.data)

    def test_dose_in_name_rejected(self):
        self.as_(self.doctor)
        for name in ('Tacrolimus 1mg', 'Tacrolimus 0.5 mg', 'Heparin 5000 units', 'Lidocaine 2%'):
            r = self.client.post('/api/rx/drugs/', {'name': name}, format='json')
            self.assertEqual(r.status_code, 400, name)
            self.assertIn('name', r.data)
        r = self.client.post('/api/rx/drugs/', {'name': 'Tacro', 'generic_name': 'Tacrolimus 1 mg'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('generic_name', r.data)
        r = self.client.post('/api/rx/drugs/', {'name': 'Vitamin B12', 'common_dose': '1000 mcg'}, format='json')
        self.assertEqual(r.status_code, 201, r.data)

    def test_edit_drug_is_audited_with_changes(self):
        self.as_(self.admin)
        r = self.client.patch(f'/api/rx/drugs/{self.tdf.pk}/', {'is_active': False}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        log = AuditLog.objects.get(entity_type='prescriptions.drug', action='update')
        self.assertEqual(log.changes, {'is_active': {'from': True, 'to': False}})

    def test_seed_command_idempotent(self):
        call_command('seed_drugs', stdout=io.StringIO())
        n = Drug.objects.count()
        call_command('seed_drugs', stdout=io.StringIO())
        self.assertEqual(Drug.objects.count(), n)
        self.assertTrue(Drug.objects.filter(name='Tacrolimus').exists())


class PrescriptionTests(Base):
    def test_doctor_prescribes_and_is_audited(self):
        r = self.prescribe(end_date=str(TODAY + D(30)))
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['drug_name'], 'Tenofovir')
        self.assertEqual(r.data['duration_days'], 30)
        self.assertEqual(r.data['status'], 'active')
        self.assertTrue(r.data['is_current'])
        self.assertEqual(r.data['prescribed_by'], self.doctor.staff_profile.pk)
        self.assertTrue(AuditLog.objects.filter(entity_type='prescriptions.prescription', action='create',
                                                patient=self.patient).exists())

    def test_only_doctors_prescribe(self):
        self.assertEqual(self.prescribe(self.surgeon).status_code, 201)
        for user in (self.coord, self.admin, self.billing, self.pat_user):
            self.assertEqual(self.prescribe(user).status_code, 403, user.username)

    def test_end_date_must_be_after_start(self):
        for end in (TODAY, TODAY - D(1)):
            r = self.prescribe(end_date=str(end))
            self.assertEqual(r.status_code, 400)
            self.assertIn('end_date', r.data)

    def test_invalid_route_and_inactive_drug(self):
        self.assertEqual(self.prescribe(route='rectal').status_code, 400)
        self.tdf.is_active = False
        self.tdf.save()
        r = self.prescribe()
        self.assertEqual(r.status_code, 400)
        self.assertIn('no longer', r.data['detail'])

    def test_stop_requires_reason_and_audits_it(self):
        rx = self.prescribe().data
        url = f"/api/rx/prescriptions/{rx['id']}/stop/"
        self.assertEqual(self.client.post(url, {}, format='json').status_code, 400)
        r = self.client.post(url, {'reason': 'Side effects'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['status'], 'stopped')
        self.assertEqual(r.data['stop_reason'], 'Side effects')
        log = AuditLog.objects.get(entity_type='prescriptions.prescription', action='update')
        self.assertEqual(log.reason, 'Side effects')
        self.assertEqual(log.changes, {'status': {'from': 'active', 'to': 'stopped'}})
        self.assertEqual(log.user, self.doctor)
        # cannot stop or complete twice
        self.assertEqual(self.client.post(url, {'reason': 'again'}, format='json').status_code, 400)
        self.assertEqual(self.client.post(f"/api/rx/prescriptions/{rx['id']}/complete/").status_code, 400)

    def test_non_doctor_cannot_stop(self):
        rx = self.prescribe().data
        self.as_(self.coord)
        r = self.client.post(f"/api/rx/prescriptions/{rx['id']}/stop/", {'reason': 'x'}, format='json')
        self.assertEqual(r.status_code, 403)

    def test_medication_list_current_vs_past(self):
        current = self.prescribe().data
        stopped = self.prescribe().data
        self.client.post(f"/api/rx/prescriptions/{stopped['id']}/stop/", {'reason': 'x'}, format='json')
        # an active prescription whose end date has passed counts as past
        expired = Prescription.objects.create(patient=self.patient, prescribed_by=self.doctor.staff_profile,
                                              drug=self.tdf, dose='1', route='oral', frequency='daily',
                                              start_date=TODAY - D(20), end_date=TODAY - D(1))
        self.prescribe(patient=self.other.pk)
        self.as_(self.coord)
        r = self.client.get(f'/api/rx/patients/{self.patient.pk}/medications/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual([x['id'] for x in r.data['current']], [current['id']])
        self.assertEqual({x['id'] for x in r.data['past']}, {stopped['id'], expired.pk})
        self.assertTrue(AuditLog.objects.filter(action='view', entity_type='prescriptions.prescription').exists())
        self.as_(self.billing)
        self.assertEqual(self.client.get(f'/api/rx/patients/{self.patient.pk}/medications/').status_code, 403)

    def test_list_filters(self):
        self.prescribe()
        self.prescribe(patient=self.other.pk)
        self.as_(self.coord)
        self.assertEqual(self.client.get('/api/rx/prescriptions/').data['count'], 2)
        self.assertEqual(self.client.get(f'/api/rx/prescriptions/?patient={self.other.pk}').data['count'], 1)
        self.assertEqual(self.client.get('/api/rx/prescriptions/?status=stopped').data['count'], 0)

    def test_patient_sees_only_own_medications(self):
        self.prescribe()
        self.prescribe(patient=self.other.pk)
        self.as_(self.pat_user)
        r = self.client.get('/api/rx/my/medications/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['current']), 1)
        self.assertNotIn('patient', r.data['current'][0])
        self.assertEqual(self.client.get('/api/rx/prescriptions/').status_code, 403)
        self.assertEqual(self.client.get(f'/api/rx/patients/{self.patient.pk}/medications/').status_code, 403)


class TreatmentPlanTests(Base):
    def test_doctor_creates_plan(self):
        r = self.plan()
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['status'], 'active')
        self.assertFalse(r.data['review_due'])
        self.assertTrue(AuditLog.objects.filter(entity_type='prescriptions.treatmentplan', action='create').exists())

    def test_transplant_referral_plan_creates_case_and_audit_entry(self):
        response = self.plan(plan_type=TreatmentPlan.PlanType.TRANSPLANT_REFERRAL)
        self.assertEqual(response.status_code, 201, response.data)
        case = TransplantCase.objects.get(recipient=self.patient)
        self.assertEqual(case.status, TransplantCase.Status.REFERRED)
        self.assertEqual(case.referred_by, self.doctor.staff_profile)
        self.assertEqual(case.referral_date, TODAY)
        self.assertEqual(response.data['transplant_case_id'], case.pk)
        self.assertTrue(response.data['transplant_case_created'])
        self.assertTrue(AuditLog.objects.filter(
            entity_type='transplant.transplantcase',
            entity_id=case.pk,
            action=AuditLog.Action.CREATE,
        ).exists())

    def test_transplant_referral_plan_reuses_existing_open_case(self):
        first = self.plan(plan_type=TreatmentPlan.PlanType.TRANSPLANT_REFERRAL)
        second = self.plan(plan_type=TreatmentPlan.PlanType.TRANSPLANT_REFERRAL)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201, second.data)
        self.assertEqual(TransplantCase.objects.filter(recipient=self.patient).count(), 1)
        self.assertEqual(second.data['transplant_case_id'], first.data['transplant_case_id'])
        self.assertFalse(second.data['transplant_case_created'])

    def test_donor_cannot_be_referred_as_transplant_recipient(self):
        self.patient.category = Patient.Category.DONOR
        self.patient.save(update_fields=['category'])
        response = self.plan(plan_type=TreatmentPlan.PlanType.TRANSPLANT_REFERRAL)
        self.assertEqual(response.status_code, 400)
        self.assertIn('Only liver patients or recipients', str(response.data))
        self.assertFalse(TransplantCase.objects.exists())

    def test_only_doctors_manage_plans(self):
        self.assertEqual(self.plan(self.surgeon).status_code, 201)
        self.assertEqual(self.plan(self.surgeon, plan_type='transplant_referral').status_code, 403)
        for user in (self.coord, self.admin, self.billing, self.pat_user):
            self.assertEqual(self.plan(user).status_code, 403)

    def test_changing_plan_to_transplant_referral_creates_case(self):
        plan = self.plan().data
        response = self.client.patch(
            f"/api/rx/plans/{plan['id']}/",
            {'plan_type': TreatmentPlan.PlanType.TRANSPLANT_REFERRAL, 'reason': 'Refer for evaluation'},
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        case = TransplantCase.objects.get(recipient=self.patient)
        self.assertEqual(response.data['transplant_case_id'], case.pk)
        self.assertEqual(case.status, TransplantCase.Status.REFERRED)

    def test_only_hepatologist_can_change_plan_to_transplant_referral(self):
        plan = self.plan().data
        self.as_(self.surgeon)
        response = self.client.patch(
            f"/api/rx/plans/{plan['id']}/",
            {'plan_type': TreatmentPlan.PlanType.TRANSPLANT_REFERRAL, 'reason': 'Refer for evaluation'},
            format='json',
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(TransplantCase.objects.exists())

    def test_review_date_not_before_start(self):
        r = self.plan(review_date=str(TODAY - D(1)))
        self.assertEqual(r.status_code, 400)
        self.assertIn('review_date', r.data)
        self.assertEqual(self.plan(plan_type='chemo').status_code, 400)

    def test_edit_records_user_changes_and_reason(self):
        plan = self.plan().data
        url = f"/api/rx/plans/{plan['id']}/"
        new_review = str(TODAY + D(90))
        # reason is mandatory
        self.assertEqual(self.client.patch(url, {'goals': 'x'}, format='json').status_code, 400)
        r = self.client.patch(url, {'goals': 'Detect HCC early; control HBV', 'review_date': new_review,
                                    'steps': plan['steps'], 'reason': 'New AFP rise'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['review_date'], new_review)
        log = AuditLog.objects.get(entity_type='prescriptions.treatmentplan', action='update')
        self.assertEqual(log.user, self.doctor)
        self.assertEqual(log.entity_id, plan['id'])
        self.assertEqual(log.patient, self.patient)
        self.assertEqual(log.reason, 'New AFP rise')
        self.assertIsNotNone(log.timestamp)
        self.assertEqual(log.changes, {
            'goals': {'from': 'Detect HCC early', 'to': 'Detect HCC early; control HBV'},
            'review_date': {'from': plan['review_date'], 'to': new_review},
        })  # unchanged `steps` is not listed

    def test_edit_without_changes_rejected(self):
        plan = self.plan().data
        r = self.client.patch(f"/api/rx/plans/{plan['id']}/", {'goals': plan['goals'], 'reason': 'x'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertFalse(AuditLog.objects.filter(action='update').exists())

    def test_edit_validates_dates_against_stored_start(self):
        plan = self.plan().data
        r = self.client.patch(f"/api/rx/plans/{plan['id']}/",
                              {'review_date': str(TODAY - D(5)), 'reason': 'x'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertEqual(TreatmentPlan.objects.get(pk=plan['id']).review_date.isoformat(), plan['review_date'])

    def test_non_doctor_cannot_edit(self):
        plan = self.plan().data
        self.as_(self.coord)
        r = self.client.patch(f"/api/rx/plans/{plan['id']}/", {'goals': 'x', 'reason': 'y'}, format='json')
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.client.get(f"/api/rx/plans/{plan['id']}/").status_code, 200)

    def test_complete_and_cancel_need_reason_and_lock_plan(self):
        p1, p2 = self.plan().data, self.plan(plan_type='tace').data
        self.assertEqual(self.client.post(f"/api/rx/plans/{p1['id']}/complete/").status_code, 400)
        r = self.client.post(f"/api/rx/plans/{p1['id']}/complete/", {'reason': 'Goals met'}, format='json')
        self.assertEqual(r.data['status'], 'completed')
        r = self.client.post(f"/api/rx/plans/{p2['id']}/cancel/", {'reason': 'Not eligible'}, format='json')
        self.assertEqual(r.data['status'], 'cancelled')
        log = AuditLog.objects.filter(entity_id=p2['id'], action='update').get()
        self.assertEqual(log.changes, {'status': {'from': 'active', 'to': 'cancelled'}})
        self.assertEqual(log.reason, 'Not eligible')
        # closed plans are read-only
        r = self.client.patch(f"/api/rx/plans/{p1['id']}/", {'goals': 'x', 'reason': 'y'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.client.post(f"/api/rx/plans/{p1['id']}/cancel/", {'reason': 'y'},
                                          format='json').status_code, 400)

    def test_review_due_filter(self):
        due = self.plan(start_date=str(TODAY - D(30)), review_date=str(TODAY - D(1))).data
        self.plan()
        self.as_(self.coord)
        r = self.client.get('/api/rx/plans/?review_due=1')
        self.assertEqual([p['id'] for p in r.data['results']], [due['id']])
        self.assertTrue(r.data['results'][0]['review_due'])
        r = self.client.get(f'/api/rx/plans/?patient={self.patient.pk}')
        self.assertEqual(r.data['count'], 2)
        self.assertTrue(AuditLog.objects.filter(action='view', entity_type='prescriptions.treatmentplan').exists())

    def test_patient_sees_only_own_plans(self):
        self.plan()
        self.plan(patient=self.other.pk)
        self.as_(self.pat_user)
        r = self.client.get('/api/rx/my/plans/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data), 1)
        self.assertEqual(self.client.get('/api/rx/plans/').status_code, 403)
