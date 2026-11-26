"""Serializers for the transplant module (Modules 11 & 12)."""
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from apps.accounts.models import Staff
from apps.registry.models import Patient  # type: ignore
from apps.scheduling.models import Appointment
from apps.scheduling.serializers import AppointmentSerializer

from .models import (
    CaseDonor, ChecklistItem, CommitteeDecision, CommitteeMember,
    FollowUpPlan, FollowUpVisit, Surgery, SurgeryTeamMember, TransplantCase,
    check_abo_compatibility,
)


# ─── Helpers ──────────────────────────────────────────────────────────────
class _StaffBriefSerializer(serializers.Serializer):
    id = serializers.IntegerField(source='pk')
    name = serializers.SerializerMethodField()
    job_title = serializers.CharField()

    def get_name(self, staff):
        return staff.user.get_full_name() or staff.user.username


class _PatientBriefSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = Patient
        fields = ['id', 'mrn', 'first_name', 'last_name', 'full_name',
                  'blood_group', 'category']
        read_only_fields = fields


# ─── TransplantCase ──────────────────────────────────────────────────────
class TransplantCaseListSerializer(serializers.ModelSerializer):
    recipient_name = serializers.SerializerMethodField()
    recipient_mrn = serializers.SerializerMethodField()
    coordinator_name = serializers.SerializerMethodField()
    donor_count = serializers.SerializerMethodField()
    checklist_progress = serializers.SerializerMethodField()

    class Meta:
        model = TransplantCase
        fields = [
            'id', 'recipient_id', 'recipient_name', 'recipient_mrn',
            'status', 'referral_date', 'coordinator_name', 'donor_count',
            'checklist_progress', 'created_at', 'updated_at',
        ]
        read_only_fields = fields

    def get_recipient_name(self, obj):
        return obj.recipient.full_name

    def get_recipient_mrn(self, obj):
        return obj.recipient.mrn

    def get_coordinator_name(self, obj):
        if obj.coordinator:
            return obj.coordinator.user.get_full_name() or obj.coordinator.user.username
        return None

    def get_donor_count(self, obj):
        return obj.case_donors.count()

    def get_checklist_progress(self, obj):
        items = obj.checklist_items.all()
        total = items.count()
        if total == 0:
            return {'total': 0, 'done': 0, 'percent': 0}
        done = items.filter(status__in=['done', 'waived']).count()
        return {'total': total, 'done': done, 'percent': round(done / total * 100)}


class TransplantCaseDetailSerializer(serializers.ModelSerializer):
    recipient = _PatientBriefSerializer(read_only=True)
    referred_by_detail = _StaffBriefSerializer(source='referred_by', read_only=True)
    coordinator_detail = _StaffBriefSerializer(source='coordinator', read_only=True)
    case_donors = serializers.SerializerMethodField()
    checklist_progress = serializers.SerializerMethodField()
    available_transitions = serializers.SerializerMethodField()

    class Meta:
        model = TransplantCase
        fields = [
            'id', 'recipient', 'referred_by_detail', 'coordinator_detail',
            'referral_encounter_id', 'status', 'referral_date', 'closed_at',
            'case_donors', 'checklist_progress', 'available_transitions',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields

    def get_case_donors(self, obj):
        return CaseDonorSerializer(obj.case_donors.select_related('donor'), many=True).data

    def get_checklist_progress(self, obj):
        items = obj.checklist_items.all()
        total = items.count()
        if total == 0:
            return {'total': 0, 'done': 0, 'percent': 0}
        done = items.filter(status__in=['done', 'waived']).count()
        return {'total': total, 'done': done, 'percent': round(done / total * 100)}

    def get_available_transitions(self, obj):
        return sorted(obj.TRANSITIONS.get(obj.status, set()))


class TransplantCaseCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransplantCase
        fields = ['recipient', 'referral_encounter', 'coordinator', 'referral_date']

    def validate_recipient(self, patient):
        if patient.pk < 1:
            raise serializers.ValidationError('ID must be positive and start from 1.')
        if patient.category not in ('liver_patient', 'recipient'):
            raise serializers.ValidationError(
                'Only liver patients or recipients can be referred for transplant.'
            )
        # Check for existing open case
        if TransplantCase.objects.filter(
            recipient=patient,
        ).exclude(status='closed').exists():
            raise serializers.ValidationError(
                'This recipient already has an open transplant case.'
            )
        return patient

    def validate_coordinator(self, staff):
        if staff and (staff.pk < 1 or staff.job_title != 'transplant_coordinator'
                      or not staff.user.is_active):
            raise serializers.ValidationError('Choose an active transplant coordinator.')
        return staff

    def create(self, validated_data):
        validated_data['referred_by'] = self.context['staff']
        validated_data['status'] = TransplantCase.Status.REFERRED
        return super().create(validated_data)


class TransplantCaseStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=TransplantCase.Status.choices)


# ─── CaseDonor ───────────────────────────────────────────────────────────
class CaseDonorSerializer(serializers.ModelSerializer):
    donor_detail = _PatientBriefSerializer(source='donor', read_only=True)
    abo_compatible = serializers.BooleanField(read_only=True)

    class Meta:
        model = CaseDonor
        fields = [
            'id', 'case', 'donor', 'donor_detail', 'application',
            'abo_compatible', 'status', 'added_at',
        ]
        read_only_fields = ['id', 'abo_compatible', 'added_at']

    def validate(self, attrs):
        case = attrs.get('case') or (self.instance and self.instance.case)
        donor = attrs.get('donor') or (self.instance and self.instance.donor)
        if case and case.status not in TransplantCase.DONOR_MATCHING_STATUSES:
            raise serializers.ValidationError({
                'case': 'Donors can only be assigned while the recipient case is under evaluation.',
            })
        if case and case.recipient.category not in ('liver_patient', 'recipient'):
            raise serializers.ValidationError({
                'case': 'The recipient is not currently eligible for donor matching.',
            })
        if donor and donor.pk < 1:
            raise serializers.ValidationError({'donor': 'ID must be positive and start from 1.'})
        if case and donor:
            if donor.pk == case.recipient_id:
                raise serializers.ValidationError({
                    'donor': 'The donor and the recipient must be different people.'
                })
            if donor.category not in ('donor',):
                raise serializers.ValidationError({
                    'donor': 'Only registered donors can be added as candidates.'
                })
        return attrs

    def create(self, validated_data):
        instance = super().create(validated_data)
        instance.calculate_abo()
        instance.save(update_fields=['abo_compatible'])
        return instance


class CaseDonorStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=CaseDonor.Status.choices)


# ─── ChecklistItem ───────────────────────────────────────────────────────
class ChecklistItemSerializer(serializers.ModelSerializer):
    patient_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ChecklistItem
        fields = [
            'id', 'case', 'patient', 'patient_name', 'item_name',
            'item_type', 'is_required', 'status', 'completed_at',
        ]
        read_only_fields = ['id', 'completed_at']

    def get_patient_name(self, obj):
        return obj.patient.full_name

    def validate(self, attrs):
        case = attrs.get('case') or (self.instance and self.instance.case)
        patient = attrs.get('patient') or (self.instance and self.instance.patient)
        if case and patient:
            case_patient_ids = {case.recipient_id}
            case_patient_ids.update(case.case_donors.values_list('donor_id', flat=True))
            if patient.pk not in case_patient_ids:
                raise serializers.ValidationError({
                    'patient': 'Choose the recipient or a donor linked to this case.',
                })
        return attrs


class ChecklistItemStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[
        ('done', 'Done'), ('waived', 'Waived'), ('pending', 'Pending'),
    ])


# ─── CommitteeDecision ───────────────────────────────────────────────────
class CommitteeMemberWriteSerializer(serializers.Serializer):
    staff_id = serializers.PrimaryKeyRelatedField(
        source='staff', queryset=Staff.objects.filter(
            user__is_active=True,
            job_title__in=[
                Staff.JobTitle.HEPATOLOGIST,
                Staff.JobTitle.RADIOLOGIST,
                Staff.JobTitle.TRANSPLANT_SURGEON,
                Staff.JobTitle.TRANSPLANT_COORDINATOR,
            ],
        ),
    )
    vote = serializers.ChoiceField(
        choices=CommitteeMember.Vote.choices, required=False, allow_null=True,
    )


class CommitteeMemberSerializer(serializers.ModelSerializer):
    staff_detail = _StaffBriefSerializer(source='staff', read_only=True)

    class Meta:
        model = CommitteeMember
        fields = ['id', 'staff', 'staff_detail', 'vote']
        read_only_fields = ['id']


class CommitteeDecisionSerializer(serializers.ModelSerializer):
    members = CommitteeMemberSerializer(many=True, read_only=True)
    recorded_by_detail = _StaffBriefSerializer(source='recorded_by', read_only=True)

    class Meta:
        model = CommitteeDecision
        fields = [
            'id', 'case', 'recorded_by_detail', 'meeting_date',
            'decision', 'reasons', 'extra_tests', 'members', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class CommitteeDecisionCreateSerializer(serializers.ModelSerializer):
    members = CommitteeMemberWriteSerializer(many=True, required=False)

    class Meta:
        model = CommitteeDecision
        fields = ['case', 'meeting_date', 'decision', 'reasons', 'extra_tests', 'members']

    def validate_case(self, case):
        if case.status != TransplantCase.Status.COMMITTEE_REVIEW:
            raise serializers.ValidationError(
                'The case must be in committee review to record a decision.'
            )
        return case

    def validate_members(self, members):
        staff_ids = [member['staff'].pk for member in members]
        if len(staff_ids) != len(set(staff_ids)):
            raise serializers.ValidationError('A staff member can only be listed once per decision.')
        return members

    @transaction.atomic
    def create(self, validated_data):
        members_data = validated_data.pop('members', [])
        validated_data['recorded_by'] = self.context['staff']
        decision = CommitteeDecision.objects.create(**validated_data)
        for member_data in members_data:
            CommitteeMember.objects.create(
                decision=decision,
                staff=member_data['staff'],
                vote=member_data.get('vote'),
            )
        # Apply decision to case status
        if decision.decision:
            decision.apply_decision()
        return decision


# ─── Surgery ─────────────────────────────────────────────────────────────
class SurgeryTeamMemberSerializer(serializers.ModelSerializer):
    staff_detail = _StaffBriefSerializer(source='staff', read_only=True)

    class Meta:
        model = SurgeryTeamMember
        fields = ['id', 'surgery', 'staff', 'staff_detail', 'team_role']
        # The surgery is taken from the URL by SurgeryTeamMemberView, not the POST body.
        read_only_fields = ['id', 'surgery']

    def validate_staff(self, staff):
        if staff.pk < 1 or not staff.user.is_active or staff.job_title in Staff.ADMIN_TITLES:
            raise serializers.ValidationError('Choose an active clinical staff member.')
        return staff

    def validate(self, attrs):
        """Reject a duplicate team member before the database constraint is reached."""
        view = self.context.get('view')
        surgery_id = view.kwargs.get('surgery_pk') if view else None
        staff = attrs.get('staff')
        if surgery_id and staff and SurgeryTeamMember.objects.filter(
            surgery_id=surgery_id,
            staff=staff,
        ).exists():
            raise serializers.ValidationError({
                'staff': 'This staff member is already assigned to this surgery.',
            })
        return attrs


class SurgerySerializer(serializers.ModelSerializer):
    team_members = SurgeryTeamMemberSerializer(many=True, read_only=True)
    case_donor_detail = CaseDonorSerializer(source='case_donor', read_only=True)
    lead_surgeon_detail = _StaffBriefSerializer(source='lead_surgeon', read_only=True)

    class Meta:
        model = Surgery
        fields = [
            'id', 'case', 'case_donor', 'case_donor_detail',
            'lead_surgeon', 'lead_surgeon_detail',
            'scheduled_at', 'operating_room', 'status', 'graft_type',
            'graft_weight_g', 'duration_min', 'operative_notes',
            'complications', 'team_members', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class SurgeryCreateSerializer(serializers.ModelSerializer):
    team_members = serializers.ListField(
        child=serializers.DictField(), required=False, write_only=True,
    )

    class Meta:
        model = Surgery
        fields = [
            'case', 'case_donor', 'lead_surgeon', 'scheduled_at',
            'operating_room', 'graft_type', 'team_members',
        ]

    def validate(self, attrs):
        case = attrs['case']
        case_donor = attrs['case_donor']
        lead_surgeon = attrs.get('lead_surgeon')
        if lead_surgeon and (
            lead_surgeon.pk < 1
            or lead_surgeon.job_title != 'transplant_surgeon'
            or not lead_surgeon.user.is_active
        ):
            raise serializers.ValidationError({
                'lead_surgeon': 'Choose an active transplant surgeon.',
            })

        if case.status != TransplantCase.Status.APPROVED:
            raise serializers.ValidationError({
                'case': 'Case must be approved before scheduling surgery.'
            })
        if case_donor.case_id != case.pk:
            raise serializers.ValidationError({
                'case_donor': 'The donor must belong to this transplant case.'
            })
        if case_donor.status != CaseDonor.Status.APPROVED:
            raise serializers.ValidationError({
                'case_donor': 'Only an approved donor can be assigned to surgery.'
            })
        return attrs

    def create(self, validated_data):
        team_data = validated_data.pop('team_members', [])
        surgery = Surgery.objects.create(**validated_data)
        # Update case status to surgery_scheduled
        surgery.case.transition_to(TransplantCase.Status.SURGERY_SCHEDULED)
        # Create team members
        for member in team_data:
            SurgeryTeamMember.objects.create(
                surgery=surgery,
                staff_id=member['staff_id'],
                team_role=member.get('team_role', ''),
            )
        return surgery


class SurgeryCompleteSerializer(serializers.Serializer):
    graft_type = serializers.ChoiceField(choices=Surgery.GraftType.choices, required=False)
    graft_weight_g = serializers.DecimalField(
        max_digits=7, decimal_places=2, required=False, min_value=Decimal('0.01'),
    )
    duration_min = serializers.IntegerField(required=False, min_value=1)
    operative_notes = serializers.CharField(required=False, allow_blank=True)
    complications = serializers.CharField(required=False, allow_blank=True)


# ─── FollowUpPlan ────────────────────────────────────────────────────────
class FollowUpPlanSerializer(serializers.ModelSerializer):
    patient_detail = _PatientBriefSerializer(source='patient', read_only=True)
    visit_count = serializers.SerializerMethodField()
    unresolved_visit_count = serializers.SerializerMethodField()
    end_date = serializers.SerializerMethodField()
    next_due_date = serializers.SerializerMethodField()

    class Meta:
        model = FollowUpPlan
        fields = [
            'id', 'case', 'patient', 'patient_detail', 'patient_role',
            'start_date', 'end_date', 'next_due_date', 'status', 'visit_count',
            'unresolved_visit_count', 'created_at',
        ]
        read_only_fields = [
            'id', 'case', 'patient', 'patient_detail', 'patient_role',
            'start_date', 'visit_count', 'unresolved_visit_count', 'created_at',
        ]

    def get_visit_count(self, obj):
        return obj.visits.count()

    def get_unresolved_visit_count(self, obj):
        terminal_statuses = {
            FollowUpVisit.Status.COMPLETED,
            FollowUpVisit.Status.CANCELLED,
        }
        return sum(visit.status not in terminal_statuses for visit in obj.visits.all())

    def get_next_due_date(self, obj):
        today = timezone.localdate()
        scheduled_visits = [
            visit for visit in obj.visits.all()
            if visit.status == FollowUpVisit.Status.SCHEDULED and visit.due_date >= today
        ]
        next_visit = min(scheduled_visits, key=lambda visit: visit.due_date, default=None)
        return next_visit.due_date if next_visit else None

    def get_end_date(self, obj):
        if obj.end_date:
            return obj.end_date.isoformat() if hasattr(obj.end_date, 'isoformat') else str(obj.end_date)
        if obj.status == FollowUpPlan.Status.COMPLETED:
            latest = obj.visits.order_by('-due_date').first()
            if latest and latest.due_date:
                return latest.due_date.isoformat() if hasattr(latest.due_date, 'isoformat') else str(latest.due_date)
            if obj.start_date:
                return obj.start_date.isoformat() if hasattr(obj.start_date, 'isoformat') else str(obj.start_date)
        return None


class FollowUpPlanUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=FollowUpPlan.Status.choices, required=False)
    end_date = serializers.DateField(required=False, allow_null=True)


# ─── FollowUpVisit ───────────────────────────────────────────────────────
class FollowUpVisitSerializer(serializers.ModelSerializer):
    class Meta:
        model = FollowUpVisit
        fields = [
            'id', 'plan', 'appointment', 'due_date', 'status',
            'immuno_level', 'rejection_episode', 'liver_regrowth_ml',
            'complications', 'notes', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class FollowUpVisitCreateSerializer(serializers.ModelSerializer):
    staff = serializers.PrimaryKeyRelatedField(
        queryset=Staff.objects.filter(
            user__is_active=True,
            job_title=Staff.JobTitle.HEPATOLOGIST,
        ).select_related('user'),
        write_only=True,
        error_messages={'does_not_exist': 'Choose an active hepatologist.'},
    )
    start_time = serializers.DateTimeField(write_only=True)

    class Meta:
        model = FollowUpVisit
        fields = ['plan', 'staff', 'start_time']

    def validate_plan(self, plan):
        if plan.status != FollowUpPlan.Status.ACTIVE:
            raise serializers.ValidationError('Follow-up plan is not active.')
        return plan

    def create(self, validated_data):
        """Create the scheduled appointment and its linked follow-up visit together."""
        request = self.context['request']
        plan = validated_data.pop('plan')
        staff = validated_data.pop('staff')
        start_time = validated_data.pop('start_time')
        appointment_serializer = AppointmentSerializer(
            data={
                'patient': plan.patient_id,
                'staff': staff.pk,
                'appointment_type': Appointment.Type.FOLLOW_UP,
                'start_time': start_time,
                'reason': f'Post-transplant follow-up for case #{plan.case_id}.',
            },
            context={'request': request},
        )
        appointment_serializer.is_valid(raise_exception=True)
        appointment = appointment_serializer.save(
            booked_by=request.user,
            case=plan.case,
        )
        return FollowUpVisit.objects.create(
            plan=plan,
            appointment=appointment,
            due_date=timezone.localdate(appointment.start_time),
        )


class MyFollowUpVisitSerializer(serializers.ModelSerializer):
    """Portal-safe details for a patient's or donor's upcoming follow-up visits."""

    case = serializers.IntegerField(source='plan.case_id', read_only=True)
    patient_role = serializers.CharField(source='plan.patient_role', read_only=True)
    start_time = serializers.DateTimeField(source='appointment.start_time', read_only=True, allow_null=True)
    doctor_name = serializers.SerializerMethodField()
    get_ready = serializers.SerializerMethodField()

    class Meta:
        model = FollowUpVisit
        fields = ['id', 'case', 'patient_role', 'appointment', 'start_time',
                  'due_date', 'status', 'doctor_name', 'get_ready']

    def get_doctor_name(self, visit):
        appointment = visit.appointment
        if not appointment or not appointment.staff_id:
            return None
        return appointment.staff.user.get_full_name() or appointment.staff.user.username

    def get_get_ready(self, visit):
        days_until = (visit.due_date - timezone.localdate()).days
        return 0 <= days_until <= 4


class RecoveryStatsSerializer(serializers.Serializer):
    """Read-only stats for recovery charts."""
    visits = FollowUpVisitSerializer(many=True)
    patient_role = serializers.CharField()
    plan_id = serializers.IntegerField()
