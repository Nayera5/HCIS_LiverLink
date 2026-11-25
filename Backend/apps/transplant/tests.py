"""
Transplant module tests: Models, business rules, API endpoints, permissions.
Run locally on SQLite:
    python manage.py test apps.transplant -v2
"""
import datetime
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import Staff, User, AuditLog
from apps.billing.models import InvoiceItem
from apps.registry.models import Patient

from .models import (
    CaseDonor, ChecklistItem, CommitteeDecision, CommitteeMember,
    FollowUpPlan, FollowUpVisit, Surgery, SurgeryTeamMember, TransplantCase,
    check_abo_compatibility,
)

PW = 'Str0ng-Pass!2026'
T = Staff.JobTitle


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════
def _make_staff(username, job_title):
    role = Staff.role_for_job_title(job_title)
    user = User.objects.create_user(
        username, f'{username}@liverlink.test', PW,
        role=role, first_name=username.title(), last_name='Tester',
    )
    return Staff.objects.create(user=user, job_title=job_title)


def _make_patient(category='liver_patient', blood_group=None, **kw):
    defaults = dict(
        first_name='Ahmed', last_name='Ibrahim',
        date_of_birth=datetime.date(1972, 3, 4),
        sex='male', phone='01000000000', category=category,
    )
    defaults.update(kw)
    if blood_group:
        defaults['blood_group'] = blood_group
    return Patient.objects.create(**defaults)


def _authed_client(user):
    client = APIClient()
    token = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
    return client


def _create_case(recipient, referred_by, **kw):
    defaults = dict(
        recipient=recipient,
        referred_by=referred_by,
        referral_date=datetime.date.today(),
        status=TransplantCase.Status.REFERRED,
    )
    defaults.update(kw)
    return TransplantCase.objects.create(**defaults)


def _advance_case_to(case, target_status, donor=None, staff=None):
    """Walk a case through the standard status workflow up to target_status."""
    path = {
        'under_evaluation': ['under_evaluation'],
        'committee_review': ['under_evaluation', 'committee_review'],
        'approved': ['under_evaluation', 'committee_review', 'approved'],
        'surgery_scheduled': ['under_evaluation', 'committee_review', 'approved', 'surgery_scheduled'],
        'transplanted': ['under_evaluation', 'committee_review', 'approved', 'surgery_scheduled', 'transplanted'],
    }
    steps = path.get(target_status, [])
    for s in steps:
        if s == 'committee_review':
            # Must clear required checklist items
            ChecklistItem.objects.filter(case=case, is_required=True, status='pending').update(
                status='done', completed_at=timezone.now()
            )
        if s == 'approved':
            # Create a committee decision to move to approved
            decision = CommitteeDecision.objects.create(
                case=case,
                recorded_by=staff or case.referred_by,
                meeting_date=datetime.date.today(),
                decision='approved',
                reasons='Test approval',
            )
            decision.apply_decision()
            continue
        if s == 'surgery_scheduled':
            # Need an approved donor and schedule surgery
            if not donor:
                donor_patient = _make_patient(category='donor', blood_group='O+', first_name='DonorAuto')
                cd = CaseDonor.objects.create(case=case, donor=donor_patient, status='approved')
            else:
                cd = CaseDonor.objects.filter(case=case, donor=donor, status='approved').first()
                if not cd:
                    cd = CaseDonor.objects.create(case=case, donor=donor, status='approved')
            surgeon = staff or _make_staff('surgeon_auto', T.TRANSPLANT_SURGEON)
            Surgery.objects.create(
                case=case, case_donor=cd, lead_surgeon=surgeon,
                scheduled_at=timezone.now(),
            )
            case.refresh_from_db()
            continue
        if s == 'transplanted':
            surgery = case.surgeries.first()
            if surgery:
                surgery.complete()
                case.refresh_from_db()
            continue
        case.transition_to(s)


# ═══════════════════════════════════════════════════════════════════════════
# 1. ABO Compatibility Unit Tests
# ═══════════════════════════════════════════════════════════════════════════
class ABOCompatibilityTests(TestCase):
    """Test check_abo_compatibility() helper function."""

    def test_o_donor_universal(self):
        for recip in ('A+', 'B-', 'AB+', 'O-'):
            self.assertTrue(check_abo_compatibility('O+', recip))

    def test_a_to_a_compatible(self):
        self.assertTrue(check_abo_compatibility('A+', 'A-'))

    def test_a_to_ab_compatible(self):
        self.assertTrue(check_abo_compatibility('A-', 'AB+'))

    def test_a_to_b_incompatible(self):
        self.assertFalse(check_abo_compatibility('A+', 'B+'))

    def test_b_to_a_incompatible(self):
        self.assertFalse(check_abo_compatibility('B+', 'A+'))

    def test_ab_to_ab_only(self):
        self.assertTrue(check_abo_compatibility('AB+', 'AB-'))
        self.assertFalse(check_abo_compatibility('AB+', 'A+'))

    def test_unknown_returns_none(self):
        self.assertIsNone(check_abo_compatibility('', 'A+'))
        self.assertIsNone(check_abo_compatibility('A+', None))

    def test_same_type_always_compatible(self):
        for bg in ('A+', 'B-', 'AB+', 'O-'):
            self.assertTrue(check_abo_compatibility(bg, bg))


# ═══════════════════════════════════════════════════════════════════════════
# 2. TransplantCase Model Tests
# ═══════════════════════════════════════════════════════════════════════════
class TransplantCaseModelTests(TestCase):

    def setUp(self):
        self.hepatologist = _make_staff('hep1', T.HEPATOLOGIST)
        self.recipient = _make_patient(category='recipient', blood_group='A+')

    def test_create_case(self):
        case = _create_case(self.recipient, self.hepatologist)
        self.assertEqual(case.status, 'referred')
        self.assertIsNotNone(case.created_at)

    def test_valid_transitions(self):
        case = _create_case(self.recipient, self.hepatologist)
        self.assertTrue(case.can_transition_to('under_evaluation'))
        self.assertFalse(case.can_transition_to('approved'))

    def test_transition_referred_to_under_evaluation(self):
        case = _create_case(self.recipient, self.hepatologist)
        case.transition_to('under_evaluation')
        self.assertEqual(case.status, 'under_evaluation')

    def test_invalid_transition_raises(self):
        case = _create_case(self.recipient, self.hepatologist)
        with self.assertRaises(ValidationError):
            case.transition_to('approved')

    def test_closed_sets_closed_at(self):
        case = _create_case(self.recipient, self.hepatologist)
        case.status = 'approved'
        case.save()
        case.transition_to('closed')
        self.assertIsNotNone(case.closed_at)

    def test_closed_allows_no_further_transitions(self):
        case = _create_case(self.recipient, self.hepatologist, status='closed')
        case.closed_at = timezone.now()
        case.save()
        self.assertEqual(len(TransplantCase.TRANSITIONS.get('closed', set())), 0)

    def test_committee_review_blocked_by_pending_checklist(self):
        case = _create_case(self.recipient, self.hepatologist)
        case.transition_to('under_evaluation')
        # Add required checklist item
        ChecklistItem.objects.create(
            case=case, patient=self.recipient,
            item_name='Blood test', item_type='lab_test',
            is_required=True, status='pending',
        )
        with self.assertRaises(ValidationError):
            case.transition_to('committee_review')

    def test_committee_review_allowed_when_checklist_done(self):
        case = _create_case(self.recipient, self.hepatologist)
        case.transition_to('under_evaluation')
        item = ChecklistItem.objects.create(
            case=case, patient=self.recipient,
            item_name='Blood test', item_type='lab_test',
            is_required=True, status='pending',
        )
        item.mark_done()
        case.transition_to('committee_review')
        self.assertEqual(case.status, 'committee_review')

    def test_committee_review_allowed_when_checklist_waived(self):
        case = _create_case(self.recipient, self.hepatologist)
        case.transition_to('under_evaluation')
        item = ChecklistItem.objects.create(
            case=case, patient=self.recipient,
            item_name='Consultation', item_type='consultation',
            is_required=True, status='pending',
        )
        item.mark_waived()
        case.transition_to('committee_review')
        self.assertEqual(case.status, 'committee_review')

    def test_non_required_items_dont_block(self):
        case = _create_case(self.recipient, self.hepatologist)
        case.transition_to('under_evaluation')
        ChecklistItem.objects.create(
            case=case, patient=self.recipient,
            item_name='Optional doc', item_type='document',
            is_required=False, status='pending',
        )
        # No required pending items → should pass
        case.transition_to('committee_review')
        self.assertEqual(case.status, 'committee_review')


class TransplantCaseOneOpenConstraintTests(TransactionTestCase):
    """Test that only one open case per recipient is allowed."""

    def test_one_open_case_per_recipient(self):
        hep = _make_staff('hep_uniq', T.HEPATOLOGIST)
        recip = _make_patient(category='recipient')
        _create_case(recip, hep)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                _create_case(recip, hep)

    def test_closed_case_allows_new_open_case(self):
        hep = _make_staff('hep_closed', T.HEPATOLOGIST)
        recip = _make_patient(category='recipient', first_name='Closed')
        c1 = _create_case(recip, hep)
        c1.status = 'closed'
        c1.closed_at = timezone.now()
        c1.save()
        c2 = _create_case(recip, hep)
        self.assertIsNotNone(c2.pk)


# ═══════════════════════════════════════════════════════════════════════════
# 3. CaseDonor Model Tests
# ═══════════════════════════════════════════════════════════════════════════
class CaseDonorModelTests(TestCase):

    def setUp(self):
        self.hep = _make_staff('hep_cd', T.HEPATOLOGIST)
        self.recipient = _make_patient(category='recipient', blood_group='A+')
        self.donor_patient = _make_patient(category='donor', blood_group='O+', first_name='Donor')
        self.case = _create_case(self.recipient, self.hep)

    def test_create_case_donor(self):
        cd = CaseDonor.objects.create(case=self.case, donor=self.donor_patient)
        self.assertEqual(cd.status, 'candidate')

    def test_donor_cannot_be_recipient(self):
        cd = CaseDonor(case=self.case, donor=self.recipient)
        with self.assertRaises(ValidationError):
            cd.clean()

    def test_calculate_abo(self):
        cd = CaseDonor.objects.create(case=self.case, donor=self.donor_patient)
        cd.calculate_abo()
        self.assertTrue(cd.abo_compatible)  # O+ → A+ = compatible

    def test_abo_incompatible(self):
        incompat_donor = _make_patient(category='donor', blood_group='AB+', first_name='InDonor')
        cd = CaseDonor.objects.create(case=self.case, donor=incompat_donor)
        cd.calculate_abo()
        self.assertFalse(cd.abo_compatible)  # AB+ → A+ = incompatible


class CaseDonorOneApprovedTests(TransactionTestCase):
    """Only one donor per case can be approved."""

    def test_one_approved_per_case(self):
        hep = _make_staff('hep_1app', T.HEPATOLOGIST)
        recip = _make_patient(category='recipient', first_name='RecipAppr')
        d1 = _make_patient(category='donor', first_name='D1')
        d2 = _make_patient(category='donor', first_name='D2')
        case = _create_case(recip, hep)
        CaseDonor.objects.create(case=case, donor=d1, status='approved')
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                CaseDonor.objects.create(case=case, donor=d2, status='approved')


# ═══════════════════════════════════════════════════════════════════════════
# 4. ChecklistItem Model Tests
# ═══════════════════════════════════════════════════════════════════════════
class ChecklistItemTests(TestCase):

    def setUp(self):
        self.hep = _make_staff('hep_cl', T.HEPATOLOGIST)
        self.recipient = _make_patient(category='recipient')
        self.case = _create_case(self.recipient, self.hep)

    def test_mark_done(self):
        item = ChecklistItem.objects.create(
            case=self.case, patient=self.recipient,
            item_name='CT scan', item_type='imaging',
        )
        item.mark_done()
        self.assertEqual(item.status, 'done')
        self.assertIsNotNone(item.completed_at)

    def test_mark_waived(self):
        item = ChecklistItem.objects.create(
            case=self.case, patient=self.recipient,
            item_name='Consult', item_type='consultation',
        )
        item.mark_waived()
        self.assertEqual(item.status, 'waived')
        self.assertIsNotNone(item.completed_at)


# ═══════════════════════════════════════════════════════════════════════════
# 5. CommitteeDecision Tests
# ═══════════════════════════════════════════════════════════════════════════
class CommitteeDecisionTests(TestCase):

    def setUp(self):
        self.hep = _make_staff('hep_dec', T.HEPATOLOGIST)
        self.recipient = _make_patient(category='recipient', first_name='DecRecip')
        self.case = _create_case(self.recipient, self.hep)
        self.case.transition_to('under_evaluation')
        self.case.transition_to('committee_review')

    def test_approved_transitions_case(self):
        decision = CommitteeDecision.objects.create(
            case=self.case, recorded_by=self.hep,
            meeting_date=datetime.date.today(),
            decision='approved', reasons='All clear.',
        )
        decision.apply_decision()
        self.case.refresh_from_db()
        self.assertEqual(self.case.status, 'approved')

    def test_rejected_transitions_case(self):
        decision = CommitteeDecision.objects.create(
            case=self.case, recorded_by=self.hep,
            meeting_date=datetime.date.today(),
            decision='rejected', reasons='Not eligible.',
        )
        decision.apply_decision()
        self.case.refresh_from_db()
        self.assertEqual(self.case.status, 'rejected')

    def test_more_tests_returns_to_evaluation(self):
        decision = CommitteeDecision.objects.create(
            case=self.case, recorded_by=self.hep,
            meeting_date=datetime.date.today(),
            decision='more_tests_needed', reasons='Need more labs.',
            extra_tests='CT + blood panel',
        )
        decision.apply_decision()
        self.case.refresh_from_db()
        self.assertEqual(self.case.status, 'under_evaluation')

    def test_null_decision_no_transition(self):
        decision = CommitteeDecision.objects.create(
            case=self.case, recorded_by=self.hep,
            meeting_date=datetime.date.today(),
            decision=None, reasons='Pending vote.',
        )
        decision.apply_decision()
        self.case.refresh_from_db()
        self.assertEqual(self.case.status, 'committee_review')

    def test_committee_member_creation(self):
        decision = CommitteeDecision.objects.create(
            case=self.case, recorded_by=self.hep,
            meeting_date=datetime.date.today(),
            decision='approved', reasons='OK',
        )
        member = CommitteeMember.objects.create(
            decision=decision, staff=self.hep, vote='approve',
        )
        self.assertEqual(member.vote, 'approve')
        self.assertEqual(decision.members.count(), 1)


# ═══════════════════════════════════════════════════════════════════════════
# 6. Surgery Model Tests
# ═══════════════════════════════════════════════════════════════════════════
class SurgeryModelTests(TestCase):

    def setUp(self):
        self.hep = _make_staff('hep_surg', T.HEPATOLOGIST)
        self.surgeon = _make_staff('surg1', T.TRANSPLANT_SURGEON)
        self.recipient = _make_patient(category='recipient', blood_group='A+', first_name='SurgRecip')
        self.donor_patient = _make_patient(category='donor', blood_group='O+', first_name='SurgDonor')
        self.case = _create_case(self.recipient, self.hep)
        self.case.transition_to('under_evaluation')
        self.case.transition_to('committee_review')
        self.cd = CaseDonor.objects.create(
            case=self.case, donor=self.donor_patient, status='approved',
        )

    def _approve_case(self):
        decision = CommitteeDecision.objects.create(
            case=self.case, recorded_by=self.hep,
            meeting_date=datetime.date.today(),
            decision='approved', reasons='OK',
        )
        decision.apply_decision()
        self.case.refresh_from_db()

    def test_surgery_creation(self):
        self._approve_case()
        surgery = Surgery.objects.create(
            case=self.case, case_donor=self.cd,
            lead_surgeon=self.surgeon,
            scheduled_at=timezone.now(),
        )
        self.assertEqual(surgery.status, 'scheduled')

    def test_donor_must_be_approved(self):
        self._approve_case()
        cd_candidate = CaseDonor.objects.create(
            case=self.case,
            donor=_make_patient(category='donor', first_name='CandDonor'),
            status='candidate',
        )
        surgery = Surgery(
            case=self.case, case_donor=cd_candidate,
            lead_surgeon=self.surgeon,
            scheduled_at=timezone.now(),
        )
        with self.assertRaises(ValidationError):
            surgery.clean()

    def test_complete_creates_followup_plans(self):
        self._approve_case()
        surgery = Surgery.objects.create(
            case=self.case, case_donor=self.cd,
            lead_surgeon=self.surgeon,
            scheduled_at=timezone.now(),
        )
        self.case.transition_to('surgery_scheduled')
        surgery.complete()
        self.case.refresh_from_db()
        self.assertEqual(self.case.status, 'transplanted')
        # Should have two follow-up plans
        plans = FollowUpPlan.objects.filter(case=self.case)
        self.assertEqual(plans.count(), 2)
        self.assertTrue(plans.filter(patient_role='recipient').exists())
        self.assertTrue(plans.filter(patient_role='donor').exists())

    def test_complete_idempotent_followup_plans(self):
        """Calling _create_followup_plans twice doesn't create duplicates (get_or_create)."""
        self._approve_case()
        surgery = Surgery.objects.create(
            case=self.case, case_donor=self.cd,
            lead_surgeon=self.surgeon,
            scheduled_at=timezone.now(),
        )
        self.case.transition_to('surgery_scheduled')
        surgery.complete()
        # Manually call again
        surgery._create_followup_plans()
        self.assertEqual(FollowUpPlan.objects.filter(case=self.case).count(), 2)

    def test_surgery_team_member(self):
        self._approve_case()
        surgery = Surgery.objects.create(
            case=self.case, case_donor=self.cd,
            lead_surgeon=self.surgeon,
            scheduled_at=timezone.now(),
        )
        member = SurgeryTeamMember.objects.create(
            surgery=surgery, staff=self.surgeon,
            team_role='Lead surgeon',
        )
        self.assertEqual(surgery.team_members.count(), 1)


# ═══════════════════════════════════════════════════════════════════════════
# 7. FollowUpPlan & FollowUpVisit Tests
# ═══════════════════════════════════════════════════════════════════════════
class FollowUpTests(TestCase):

    def setUp(self):
        self.hep = _make_staff('hep_fu', T.HEPATOLOGIST)
        self.recipient = _make_patient(category='recipient', first_name='FURecip')
        self.case = _create_case(self.recipient, self.hep)

    def test_plan_creation(self):
        plan = FollowUpPlan.objects.create(
            case=self.case, patient=self.recipient,
            patient_role='recipient', start_date=datetime.date.today(),
        )
        self.assertEqual(plan.status, 'active')

    def test_visit_creation(self):
        plan = FollowUpPlan.objects.create(
            case=self.case, patient=self.recipient,
            patient_role='recipient', start_date=datetime.date.today(),
        )
        visit = FollowUpVisit.objects.create(
            plan=plan, due_date=datetime.date.today(),
        )
        self.assertEqual(visit.status, 'scheduled')

    def test_visit_recipient_fields(self):
        plan = FollowUpPlan.objects.create(
            case=self.case, patient=self.recipient,
            patient_role='recipient', start_date=datetime.date.today(),
        )
        visit = FollowUpVisit.objects.create(
            plan=plan, due_date=datetime.date.today(),
            immuno_level=Decimal('12.50'),
            rejection_episode=False,
        )
        self.assertEqual(visit.immuno_level, Decimal('12.50'))
        self.assertFalse(visit.rejection_episode)

    def test_visit_donor_fields(self):
        donor = _make_patient(category='donor', first_name='FUDonor')
        plan = FollowUpPlan.objects.create(
            case=self.case, patient=donor,
            patient_role='donor', start_date=datetime.date.today(),
        )
        visit = FollowUpVisit.objects.create(
            plan=plan, due_date=datetime.date.today(),
            liver_regrowth_ml=Decimal('850.00'),
        )
        self.assertEqual(visit.liver_regrowth_ml, Decimal('850.00'))


class FollowUpPlanOnePerRoleTests(TransactionTestCase):
    """One plan per role per case."""

    def test_duplicate_role_rejected(self):
        hep = _make_staff('hep_fudup', T.HEPATOLOGIST)
        recip = _make_patient(category='recipient', first_name='FUDupRecip')
        case = _create_case(recip, hep)
        FollowUpPlan.objects.create(
            case=case, patient=recip,
            patient_role='recipient', start_date=datetime.date.today(),
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                FollowUpPlan.objects.create(
                    case=case, patient=recip,
                    patient_role='recipient', start_date=datetime.date.today(),
                )


# ═══════════════════════════════════════════════════════════════════════════
# 8. API Endpoint Tests
# ═══════════════════════════════════════════════════════════════════════════
class TransplantAPITests(TestCase):
    """Test API endpoints with authentication and permissions."""

    def setUp(self):
        self.hepatologist = _make_staff('api_hep', T.HEPATOLOGIST)
        self.coordinator = _make_staff('api_coord', T.TRANSPLANT_COORDINATOR)
        self.surgeon = _make_staff('api_surg', T.TRANSPLANT_SURGEON)
        self.recipient = _make_patient(category='recipient', blood_group='A+', first_name='APIRecip')
        self.donor_patient = _make_patient(category='donor', blood_group='O+', first_name='APIDonor')

        self.hep_client = _authed_client(self.hepatologist.user)
        self.coord_client = _authed_client(self.coordinator.user)
        self.surg_client = _authed_client(self.surgeon.user)

    # ── Create Referral ──────────────────────────────────────────────
    def test_create_referral(self):
        resp = self.hep_client.post('/api/transplant/cases/', {
            'recipient': self.recipient.pk,
            'referral_date': '2026-11-01',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['status'], 'referred')
        self.assertTrue(AuditLog.objects.filter(
            entity_type='transplant.transplantcase',
            entity_id=resp.data['id'],
            action=AuditLog.Action.CREATE,
        ).exists())

    def test_coordinator_cannot_refer(self):
        """Only hepatologists can refer."""
        resp = self.coord_client.post('/api/transplant/cases/', {
            'recipient': self.recipient.pk,
            'referral_date': '2026-11-01',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    # ── List Cases ───────────────────────────────────────────────────
    def test_list_cases(self):
        _create_case(self.recipient, self.hepatologist)
        resp = self.coord_client.get('/api/transplant/cases/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_case_detail(self):
        case = _create_case(self.recipient, self.hepatologist)
        resp = self.coord_client.get(f'/api/transplant/cases/{case.pk}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['id'], case.pk)

    # ── Status Transition ────────────────────────────────────────────
    def test_status_transition_via_api(self):
        case = _create_case(self.recipient, self.hepatologist)
        resp = self.coord_client.post(
            f'/api/transplant/cases/{case.pk}/status/',
            {'status': 'under_evaluation'}, format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['status'], 'under_evaluation')

    def test_invalid_status_transition_via_api(self):
        case = _create_case(self.recipient, self.hepatologist)
        resp = self.coord_client.post(
            f'/api/transplant/cases/{case.pk}/status/',
            {'status': 'approved'}, format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # ── Case Donors ──────────────────────────────────────────────────
    def test_add_donor_to_case(self):
        case = _create_case(self.recipient, self.hepatologist)
        case.transition_to(TransplantCase.Status.UNDER_EVALUATION)
        resp = self.coord_client.post(
            f'/api/transplant/cases/{case.pk}/donors/',
            {'donor': self.donor_patient.pk}, format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(AuditLog.objects.filter(
            entity_type='transplant.casedonor',
            entity_id=resp.data['id'],
            action=AuditLog.Action.CREATE,
        ).exists())

    def test_cannot_add_donor_before_case_enters_evaluation(self):
        case = _create_case(self.recipient, self.hepatologist)
        resp = self.coord_client.post(
            f'/api/transplant/cases/{case.pk}/donors/',
            {'donor': self.donor_patient.pk}, format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('under evaluation', str(resp.data))
        self.assertFalse(CaseDonor.objects.filter(case=case).exists())

    def test_cannot_add_donor_if_recipient_category_changed(self):
        case = _create_case(self.recipient, self.hepatologist, status=TransplantCase.Status.UNDER_EVALUATION)
        self.recipient.category = Patient.Category.DONOR
        self.recipient.save(update_fields=['category'])
        resp = self.coord_client.post(
            f'/api/transplant/cases/{case.pk}/donors/',
            {'donor': self.donor_patient.pk}, format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('not currently eligible', str(resp.data))

    def test_case_can_be_closed_before_matching(self):
        for initial_status in (
            TransplantCase.Status.REFERRED,
            TransplantCase.Status.UNDER_EVALUATION,
            TransplantCase.Status.COMMITTEE_REVIEW,
        ):
            with self.subTest(initial_status=initial_status):
                case = _create_case(
                    _make_patient(category='recipient'),
                    self.hepatologist,
                    status=initial_status,
                )
                response = self.coord_client.post(
                    f'/api/transplant/cases/{case.pk}/status/',
                    {'status': TransplantCase.Status.CLOSED},
                    format='json',
                )
                self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
                self.assertEqual(response.data['status'], TransplantCase.Status.CLOSED)
                self.assertTrue(AuditLog.objects.filter(
                    entity_type='transplant.transplantcase',
                    entity_id=case.pk,
                    action=AuditLog.Action.STATUS_CHANGE,
                ).exists())

    def test_abo_check(self):
        case = _create_case(self.recipient, self.hepatologist)
        cd = CaseDonor.objects.create(case=case, donor=self.donor_patient)
        resp = self.coord_client.get(f'/api/transplant/donors/{cd.pk}/abo-check/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('abo_compatible', resp.data)

    def test_donor_status_update(self):
        case = _create_case(self.recipient, self.hepatologist)
        cd = CaseDonor.objects.create(case=case, donor=self.donor_patient)
        resp = self.coord_client.post(
            f'/api/transplant/donors/{cd.pk}/status/',
            {'status': 'under_evaluation'}, format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['status'], 'under_evaluation')

    # ── Checklist ────────────────────────────────────────────────────
    def test_create_checklist_item(self):
        case = _create_case(self.recipient, self.hepatologist)
        resp = self.coord_client.post(
            f'/api/transplant/cases/{case.pk}/checklist/',
            {
                'patient': self.recipient.pk,
                'item_name': 'Liver function test',
                'item_type': 'lab_test',
                'is_required': True,
            },
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_checklist_status_update(self):
        case = _create_case(self.recipient, self.hepatologist)
        item = ChecklistItem.objects.create(
            case=case, patient=self.recipient,
            item_name='Test', item_type='lab_test',
        )
        resp = self.coord_client.post(
            f'/api/transplant/checklist/{item.pk}/status/',
            {'status': 'done'}, format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        item.refresh_from_db()
        self.assertEqual(item.status, 'done')

    # ── Committee Decisions ──────────────────────────────────────────
    def test_create_decision(self):
        case = _create_case(self.recipient, self.hepatologist)
        case.transition_to('under_evaluation')
        case.transition_to('committee_review')
        resp = self.hep_client.post(
            f'/api/transplant/cases/{case.pk}/decisions/',
            {
                'meeting_date': '2026-11-15',
                'decision': 'approved',
                'reasons': 'Patient meets all criteria.',
                'members': [{'staff_id': self.hepatologist.pk, 'vote': 'approve'}],
            },
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        case.refresh_from_db()
        self.assertEqual(case.status, 'approved')

    def test_decision_requires_committee_review_status(self):
        case = _create_case(self.recipient, self.hepatologist)
        resp = self.hep_client.post(
            f'/api/transplant/cases/{case.pk}/decisions/',
            {
                'meeting_date': '2026-11-15',
                'decision': 'approved',
                'reasons': 'Test',
            },
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_coordinator_cannot_create_decision(self):
        """Only hepatologists can record committee decisions."""
        case = _create_case(self.recipient, self.hepatologist)
        case.transition_to('under_evaluation')
        case.transition_to('committee_review')
        resp = self.coord_client.post(
            f'/api/transplant/cases/{case.pk}/decisions/',
            {
                'meeting_date': '2026-11-15',
                'decision': 'approved',
                'reasons': 'Test',
            },
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    # ── Surgery ──────────────────────────────────────────────────────
    def test_create_surgery(self):
        case = _create_case(self.recipient, self.hepatologist)
        case.transition_to('under_evaluation')
        case.transition_to('committee_review')
        decision = CommitteeDecision.objects.create(
            case=case, recorded_by=self.hepatologist,
            meeting_date=datetime.date.today(),
            decision='approved', reasons='OK',
        )
        decision.apply_decision()
        case.refresh_from_db()
        cd = CaseDonor.objects.create(case=case, donor=self.donor_patient, status='approved')
        resp = self.surg_client.post(
            f'/api/transplant/cases/{case.pk}/surgeries/',
            {
                'case_donor': cd.pk,
                'lead_surgeon': self.surgeon.pk,
                'scheduled_at': '2026-12-01T08:00:00Z',
            },
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        case.refresh_from_db()
        self.assertEqual(case.status, 'surgery_scheduled')

    def test_complete_surgery(self):
        case = _create_case(self.recipient, self.hepatologist)
        case.transition_to('under_evaluation')
        case.transition_to('committee_review')
        decision = CommitteeDecision.objects.create(
            case=case, recorded_by=self.hepatologist,
            meeting_date=datetime.date.today(),
            decision='approved', reasons='OK',
        )
        decision.apply_decision()
        case.refresh_from_db()
        cd = CaseDonor.objects.create(case=case, donor=self.donor_patient, status='approved')
        surgery = Surgery.objects.create(
            case=case, case_donor=cd,
            lead_surgeon=self.surgeon,
            scheduled_at=timezone.now(),
        )
        case.transition_to('surgery_scheduled')
        resp = self.surg_client.post(
            f'/api/transplant/surgeries/{surgery.pk}/complete/',
            {
                'graft_type': 'right_lobe',
                'graft_weight_g': '750.00',
                'duration_min': 480,
            },
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        case.refresh_from_db()
        self.assertEqual(case.status, 'transplanted')
        self.assertEqual(FollowUpPlan.objects.filter(case=case).count(), 2)
        item = InvoiceItem.objects.get(surgery=surgery)
        self.assertEqual(item.service.code, 'SUR-001')
        self.assertEqual(item.invoice.patient, case.recipient)
        from apps.billing.services import invoice_for_surgery

        self.assertIsNone(invoice_for_surgery(surgery))
        self.assertEqual(InvoiceItem.objects.filter(surgery=surgery).count(), 1)

    def test_coordinator_cannot_create_surgery(self):
        case = _create_case(self.recipient, self.hepatologist)
        resp = self.coord_client.post(
            f'/api/transplant/cases/{case.pk}/surgeries/',
            {
                'case_donor': 1,
                'lead_surgeon': self.surgeon.pk,
                'scheduled_at': '2026-12-01T08:00:00Z',
            },
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    # ── Follow-up ────────────────────────────────────────────────────
    def test_list_followup_plans(self):
        resp = self.coord_client.get('/api/transplant/followup/plans/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_create_followup_visit(self):
        plan = FollowUpPlan.objects.create(
            case=_create_case(self.recipient, self.hepatologist),
            patient=self.recipient,
            patient_role='recipient',
            start_date=datetime.date.today(),
        )
        resp = self.coord_client.post(
            f'/api/transplant/followup/plans/{plan.pk}/visits/',
            {'due_date': '2026-12-15'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_update_followup_visit(self):
        case = _create_case(self.recipient, self.hepatologist)
        plan = FollowUpPlan.objects.create(
            case=case, patient=self.recipient,
            patient_role='recipient',
            start_date=datetime.date.today(),
        )
        visit = FollowUpVisit.objects.create(plan=plan, due_date=datetime.date.today())
        resp = self.coord_client.patch(
            f'/api/transplant/followup/visits/{visit.pk}/',
            {'immuno_level': '15.5', 'rejection_episode': False, 'status': 'completed'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        visit.refresh_from_db()
        self.assertEqual(visit.immuno_level, Decimal('15.5'))

    def test_recovery_stats(self):
        case = _create_case(self.recipient, self.hepatologist)
        plan = FollowUpPlan.objects.create(
            case=case, patient=self.recipient,
            patient_role='recipient',
            start_date=datetime.date.today(),
        )
        FollowUpVisit.objects.create(
            plan=plan, due_date=datetime.date.today(),
            status='completed', immuno_level=Decimal('12.5'),
        )
        resp = self.coord_client.get(f'/api/transplant/followup/plans/{plan.pk}/recovery/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data['visits']), 1)

    def test_complete_plan(self):
        case = _create_case(self.recipient, self.hepatologist)
        plan = FollowUpPlan.objects.create(
            case=case, patient=self.recipient,
            patient_role='recipient',
            start_date=datetime.date.today(),
        )
        resp = self.coord_client.patch(
            f'/api/transplant/followup/plans/{plan.pk}/',
            {'status': 'completed'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        plan.refresh_from_db()
        self.assertEqual(plan.status, 'completed')
        self.assertIsNotNone(plan.end_date)
        self.assertEqual(resp.data['end_date'], plan.end_date.isoformat())


# ═══════════════════════════════════════════════════════════════════════════
# 9. Permission / Access Control Tests
# ═══════════════════════════════════════════════════════════════════════════
class PermissionTests(TestCase):
    """Ensure unauthenticated and unauthorized users are blocked."""

    def setUp(self):
        self.anon_client = APIClient()
        # Patient user (no staff profile, no transplant capabilities)
        self.patient_user = User.objects.create_user(
            'patient1', 'patient@test.com', PW, role=User.Role.PATIENT,
        )
        self.patient_client = _authed_client(self.patient_user)

    def test_anon_cannot_list_cases(self):
        resp = self.anon_client.get('/api/transplant/cases/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_anon_cannot_list_plans(self):
        resp = self.anon_client.get('/api/transplant/followup/plans/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_patient_cannot_list_cases(self):
        resp = self.patient_client.get('/api/transplant/cases/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_patient_cannot_list_plans(self):
        resp = self.patient_client.get('/api/transplant/followup/plans/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


# ═══════════════════════════════════════════════════════════════════════════
# 10. Full Workflow Integration Test
# ═══════════════════════════════════════════════════════════════════════════
class FullWorkflowTest(TestCase):
    """Walk through the entire transplant lifecycle via models."""

    def test_referral_to_followup(self):
        hep = _make_staff('wf_hep', T.HEPATOLOGIST)
        surgeon = _make_staff('wf_surg', T.TRANSPLANT_SURGEON)
        recip = _make_patient(category='recipient', blood_group='A+', first_name='WFRecip')
        donor = _make_patient(category='donor', blood_group='O+', first_name='WFDonor')

        # 1. Referral
        case = _create_case(recip, hep)
        self.assertEqual(case.status, 'referred')

        # 2. Under evaluation
        case.transition_to('under_evaluation')
        self.assertEqual(case.status, 'under_evaluation')

        # 3. Add donor
        cd = CaseDonor.objects.create(case=case, donor=donor)
        cd.calculate_abo()
        self.assertTrue(cd.abo_compatible)

        # 4. Add checklist
        item = ChecklistItem.objects.create(
            case=case, patient=recip,
            item_name='Lab panel', item_type='lab_test',
            is_required=True,
        )
        item.mark_done()

        # 5. Committee review
        case.transition_to('committee_review')

        # 6. Committee approval
        decision = CommitteeDecision.objects.create(
            case=case, recorded_by=hep,
            meeting_date=datetime.date.today(),
            decision='approved', reasons='All clear.',
        )
        CommitteeMember.objects.create(
            decision=decision, staff=hep, vote='approve',
        )
        decision.apply_decision()
        case.refresh_from_db()
        self.assertEqual(case.status, 'approved')

        # 7. Approve donor
        cd.status = 'approved'
        cd.save()

        # 8. Schedule surgery
        surgery = Surgery.objects.create(
            case=case, case_donor=cd,
            lead_surgeon=surgeon,
            scheduled_at=timezone.now(),
            graft_type='right_lobe',
        )
        case.transition_to('surgery_scheduled')

        # 9. Add team member
        SurgeryTeamMember.objects.create(
            surgery=surgery, staff=surgeon, team_role='Lead surgeon',
        )

        # 10. Complete surgery
        surgery.complete()
        case.refresh_from_db()
        self.assertEqual(case.status, 'transplanted')

        # 11. Follow-up plans created
        plans = FollowUpPlan.objects.filter(case=case)
        self.assertEqual(plans.count(), 2)

        # 12. Move to follow-up
        case.transition_to('follow_up')
        self.assertEqual(case.status, 'follow_up')

        # 13. Add visits
        recip_plan = plans.get(patient_role='recipient')
        visit = FollowUpVisit.objects.create(
            plan=recip_plan,
            due_date=datetime.date.today(),
            immuno_level=Decimal('10.5'),
            rejection_episode=False,
        )
        self.assertEqual(recip_plan.visits.count(), 1)

        donor_plan = plans.get(patient_role='donor')
        FollowUpVisit.objects.create(
            plan=donor_plan,
            due_date=datetime.date.today(),
            liver_regrowth_ml=Decimal('900.00'),
        )
        self.assertEqual(donor_plan.visits.count(), 1)

        # 14. Close
        case.transition_to('closed')
        self.assertEqual(case.status, 'closed')
        self.assertIsNotNone(case.closed_at)
