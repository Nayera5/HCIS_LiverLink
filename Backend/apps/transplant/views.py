"""Views for the transplant module (Modules 11 & 12)."""
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.audit import audit  # type: ignore
from apps.accounts.models import AuditLog, Staff  # type: ignore
from apps.accounts.rbac import get_staff_profile  # type: ignore

from .models import (
    CaseDonor, ChecklistItem, CommitteeDecision,
    FollowUpPlan, FollowUpVisit, Surgery, SurgeryTeamMember, TransplantCase,
)
from .permissions import (
    CanCommitteeDecide, CanManageFollowUp, CanManageTransplant,
    CanRecordSurgery, CanReferTransplant, CanViewFollowUp, CanViewTransplant,
)
from .serializers import (
    CaseDonorSerializer, CaseDonorStatusSerializer, ChecklistItemSerializer,
    ChecklistItemStatusSerializer, CommitteeDecisionCreateSerializer,
    CommitteeDecisionSerializer, FollowUpPlanSerializer,
    FollowUpPlanUpdateSerializer, FollowUpVisitCreateSerializer, FollowUpVisitSerializer,
    SurgeryCompleteSerializer, SurgeryCreateSerializer, SurgerySerializer,
    SurgeryTeamMemberSerializer, TransplantCaseCreateSerializer,
    TransplantCaseDetailSerializer, TransplantCaseListSerializer,
    TransplantCaseStatusSerializer,
)

ENTITY = 'transplant.transplantcase'


class TransplantPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class PositiveIdMixin:
    """Validates that all URL pk parameters are positive integers (>= 1)."""

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        for key, val in kwargs.items():
            if key in ('pk', 'plan_pk', 'case_pk', 'id') or key.endswith('_pk'):
                try:
                    if int(val) < 1:
                        raise DRFValidationError({key: 'ID must be positive and start from 1.'})
                except (ValueError, TypeError):
                    raise DRFValidationError({key: 'ID must be an integer.'})


class StaffPickerView(generics.GenericAPIView):
    """Search active staff for transplant forms without exposing account records."""

    permission_classes = [IsAuthenticated, CanViewTransplant]

    def get(self, request):
        job_title = request.query_params.get('job_title', '').strip()
        if job_title and job_title not in Staff.JobTitle.values:
            raise DRFValidationError({
                'job_title': 'Choose a valid staff job title.',
            })

        staff = Staff.objects.select_related('user').filter(
            user__is_active=True,
        )
        if job_title:
            staff = staff.filter(job_title=job_title)
        search = request.query_params.get('search', '').strip()
        if search:
            staff = staff.filter(
                Q(user__first_name__icontains=search)
                | Q(user__last_name__icontains=search)
                | Q(user__username__icontains=search)
            )

        return Response([
            {
                'id': member.pk,
                'name': member.user.get_full_name() or member.user.username,
                'job_title': member.job_title,
                'job_title_display': member.get_job_title_display(),
                'department': member.department,
            }
            for member in staff.order_by('user__last_name', 'user__first_name', 'pk')[:100]
        ])


def _staff(request):
    return get_staff_profile(request.user)


# ───────────────────────────────────────────────────────────────────────────
# TransplantCase
# ───────────────────────────────────────────────────────────────────────────
class TransplantCaseListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/transplant/cases/         list all cases
    POST /api/transplant/cases/         create a new referral
    """

    pagination_class = TransplantPagination

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), CanReferTransplant()]
        return [IsAuthenticated(), CanViewTransplant()]

    def get_queryset(self):
        qs = TransplantCase.objects.select_related(
            'recipient', 'referred_by__user', 'coordinator__user',
        ).prefetch_related('case_donors', 'checklist_items')
        params = self.request.query_params
        if s := params.get('search', '').strip():
            qs = qs.filter(
                Q(recipient__first_name__icontains=s)
                | Q(recipient__last_name__icontains=s)
                | Q(recipient__mrn__icontains=s)
            )
        if st := params.get('status'):
            qs = qs.filter(status=st)
        if coordinator := params.get('coordinator'):
            try:
                coordinator_id = int(coordinator)
                if coordinator_id < 1:
                    raise ValueError
            except (TypeError, ValueError):
                raise DRFValidationError({'coordinator': 'Choose a valid coordinator.'})
            qs = qs.filter(coordinator_id=coordinator_id)
        return qs

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return TransplantCaseCreateSerializer
        return TransplantCaseListSerializer

    def perform_create(self, serializer):
        case = serializer.save(staff=_staff(self.request))
        audit(self.request, AuditLog.Action.CREATE, ENTITY,
              entity_id=case.pk, patient=case.recipient)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data, context={'staff': _staff(request), 'request': request},
        )
        serializer.is_valid(raise_exception=True)
        case = serializer.save()
        return Response(
            TransplantCaseDetailSerializer(case).data,
            status=status.HTTP_201_CREATED,
        )


class TransplantCaseDetailView(PositiveIdMixin, generics.RetrieveAPIView):
    """GET /api/transplant/cases/<id>/"""

    permission_classes = [IsAuthenticated, CanViewTransplant]
    serializer_class = TransplantCaseDetailSerializer
    queryset = TransplantCase.objects.select_related(
        'recipient', 'referred_by__user', 'coordinator__user',
    ).prefetch_related(
        'case_donors__donor', 'checklist_items',
    )


class TransplantCaseStatusView(PositiveIdMixin, generics.GenericAPIView):
    """POST /api/transplant/cases/<id>/status/  {status: "under_evaluation"}"""

    permission_classes = [IsAuthenticated, CanManageTransplant]
    serializer_class = TransplantCaseStatusSerializer
    queryset = TransplantCase.objects.all()

    def post(self, request, pk):
        case = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data['status']
        try:
            case.transition_to(new_status)
        except DjangoValidationError as exc:
            raise DRFValidationError(exc.message_dict if hasattr(exc, 'message_dict') else exc.messages)
        audit(request, AuditLog.Action.STATUS_CHANGE, ENTITY,
              entity_id=case.pk, patient=case.recipient)
        return Response(TransplantCaseDetailSerializer(case).data)


class TransplantCaseUpdateView(PositiveIdMixin, generics.UpdateAPIView):
    """PATCH /api/transplant/cases/<id>/  (update coordinator, etc.)"""

    permission_classes = [IsAuthenticated, CanManageTransplant]
    queryset = TransplantCase.objects.all()
    http_method_names = ['patch', 'head', 'options']

    class _Serializer(TransplantCaseDetailSerializer):
        class Meta(TransplantCaseDetailSerializer.Meta):
            read_only_fields = [
                f for f in TransplantCaseDetailSerializer.Meta.read_only_fields
                if f not in ('coordinator_detail',)
            ]

    def get_serializer_class(self):
        return self._Serializer

    def partial_update(self, request, *args, **kwargs):
        case = self.get_object()
        allowed = {'coordinator'}
        data = {k: v for k, v in request.data.items() if k in allowed}
        previous_coordinator_id = case.coordinator_id
        if 'coordinator' in data:
            raw_id = data['coordinator']
            if raw_id in (None, ''):
                case.coordinator = None
            else:
                try:
                    coordinator_id = int(raw_id)
                except (TypeError, ValueError):
                    raise DRFValidationError({'coordinator': 'Choose a valid coordinator.'})
                coordinator = Staff.objects.filter(
                    pk=coordinator_id,
                    job_title=Staff.JobTitle.TRANSPLANT_COORDINATOR,
                    user__is_active=True,
                ).first()
                if coordinator is None:
                    raise DRFValidationError({
                        'coordinator': 'Choose an active transplant coordinator.',
                    })
                case.coordinator = coordinator
            if case.coordinator_id != previous_coordinator_id:
                case.save(update_fields=['coordinator_id', 'updated_at'])
                audit(
                    request, AuditLog.Action.UPDATE, ENTITY,
                    entity_id=case.pk, patient=case.recipient,
                )
        return Response(TransplantCaseDetailSerializer(case).data)


# ───────────────────────────────────────────────────────────────────────────
# CaseDonor
# ───────────────────────────────────────────────────────────────────────────
class CaseDonorListCreateView(PositiveIdMixin, generics.ListCreateAPIView):
    """
    GET  /api/transplant/cases/<case_pk>/donors/
    POST /api/transplant/cases/<case_pk>/donors/
    """

    permission_classes = [IsAuthenticated, CanManageTransplant]
    serializer_class = CaseDonorSerializer

    def get_queryset(self):
        return CaseDonor.objects.filter(
            case_id=self.kwargs['case_pk'],
        ).select_related('donor')

    def create(self, request, *args, **kwargs):
        data = {**request.data, 'case': self.kwargs['case_pk']}
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        case_donor = serializer.save()
        audit(
            self.request, AuditLog.Action.CREATE, 'transplant.casedonor',
            entity_id=case_donor.pk, patient=case_donor.case.recipient,
        )


class CaseDonorDetailView(PositiveIdMixin, generics.RetrieveAPIView):
    """GET /api/transplant/donors/<id>/"""

    permission_classes = [IsAuthenticated, CanViewTransplant]
    serializer_class = CaseDonorSerializer
    queryset = CaseDonor.objects.select_related('donor')


class CaseDonorStatusView(PositiveIdMixin, generics.GenericAPIView):
    """POST /api/transplant/donors/<id>/status/  {status: "approved"}"""

    permission_classes = [IsAuthenticated, CanManageTransplant]
    serializer_class = CaseDonorStatusSerializer
    queryset = CaseDonor.objects.all()

    def post(self, request, pk):
        cd = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cd.status = serializer.validated_data['status']
        cd.save(update_fields=['status'])
        audit(
            request, AuditLog.Action.STATUS_CHANGE, 'transplant.casedonor',
            entity_id=cd.pk, patient=cd.case.recipient,
        )
        return Response(CaseDonorSerializer(cd).data)


class ABOCheckView(PositiveIdMixin, generics.GenericAPIView):
    """GET /api/transplant/donors/<id>/abo-check/"""

    permission_classes = [IsAuthenticated, CanViewTransplant]
    queryset = CaseDonor.objects.select_related('donor', 'case__recipient')

    def get(self, request, pk):
        cd = self.get_object()
        cd.calculate_abo()
        cd.save(update_fields=['abo_compatible'])
        return Response({
            'donor_blood_group': cd.donor.blood_group,
            'recipient_blood_group': cd.case.recipient.blood_group,
            'abo_compatible': cd.abo_compatible,
        })


# ───────────────────────────────────────────────────────────────────────────
# ChecklistItem
# ───────────────────────────────────────────────────────────────────────────
class ChecklistItemListCreateView(PositiveIdMixin, generics.ListCreateAPIView):
    """
    GET  /api/transplant/cases/<case_pk>/checklist/
    POST /api/transplant/cases/<case_pk>/checklist/
    """

    permission_classes = [IsAuthenticated, CanManageTransplant]
    serializer_class = ChecklistItemSerializer

    def get_queryset(self):
        return ChecklistItem.objects.filter(
            case_id=self.kwargs['case_pk'],
        ).select_related('patient')

    def create(self, request, *args, **kwargs):
        data = {**request.data, 'case': self.kwargs['case_pk']}
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        item = serializer.save()
        audit(
            self.request, AuditLog.Action.CREATE, 'transplant.checklistitem',
            entity_id=item.pk, patient=item.patient,
        )


class ChecklistItemDetailView(PositiveIdMixin, generics.RetrieveUpdateDestroyAPIView):
    """GET/PATCH/DELETE /api/transplant/checklist/<id>/"""

    permission_classes = [IsAuthenticated, CanManageTransplant]
    serializer_class = ChecklistItemSerializer
    queryset = ChecklistItem.objects.all()

    def perform_update(self, serializer):
        item = serializer.save()
        audit(
            self.request, AuditLog.Action.UPDATE, 'transplant.checklistitem',
            entity_id=item.pk, patient=item.patient,
        )

    def perform_destroy(self, instance):
        audit(
            self.request, AuditLog.Action.DELETE, 'transplant.checklistitem',
            entity_id=instance.pk, patient=instance.patient,
        )
        instance.delete()


class ChecklistItemStatusView(PositiveIdMixin, generics.GenericAPIView):
    """POST /api/transplant/checklist/<id>/status/  {status: "done"}"""

    permission_classes = [IsAuthenticated, CanManageTransplant]
    serializer_class = ChecklistItemStatusSerializer
    queryset = ChecklistItem.objects.all()

    def post(self, request, pk):
        item = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data['status']
        if new_status == 'done':
            item.mark_done()
        elif new_status == 'waived':
            item.mark_waived()
        else:
            item.status = 'pending'
            item.completed_at = None
            item.save(update_fields=['status', 'completed_at'])
        audit(
            request, AuditLog.Action.STATUS_CHANGE, 'transplant.checklistitem',
            entity_id=item.pk, patient=item.patient,
        )
        return Response(ChecklistItemSerializer(item).data)


# ───────────────────────────────────────────────────────────────────────────
# CommitteeDecision
# ───────────────────────────────────────────────────────────────────────────
class CommitteeDecisionListCreateView(PositiveIdMixin, generics.ListCreateAPIView):
    """
    GET  /api/transplant/cases/<case_pk>/decisions/
    POST /api/transplant/cases/<case_pk>/decisions/
    """

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), CanCommitteeDecide()]
        return [IsAuthenticated(), CanViewTransplant()]

    def get_queryset(self):
        return CommitteeDecision.objects.filter(
            case_id=self.kwargs['case_pk'],
        ).select_related('recorded_by__user').prefetch_related('members__staff__user')

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CommitteeDecisionCreateSerializer
        return CommitteeDecisionSerializer

    def create(self, request, *args, **kwargs):
        serializer = CommitteeDecisionCreateSerializer(
            data={**request.data, 'case': self.kwargs['case_pk']},
            context={'staff': _staff(request), 'request': request},
        )
        serializer.is_valid(raise_exception=True)
        decision = serializer.save()
        audit(request, AuditLog.Action.CREATE, 'transplant.committeedecision',
              entity_id=decision.pk)
        return Response(
            CommitteeDecisionSerializer(decision).data,
            status=status.HTTP_201_CREATED,
        )


class CommitteeDecisionDetailView(PositiveIdMixin, generics.RetrieveAPIView):
    """GET /api/transplant/decisions/<id>/"""

    permission_classes = [IsAuthenticated, CanViewTransplant]
    serializer_class = CommitteeDecisionSerializer
    queryset = CommitteeDecision.objects.select_related(
        'recorded_by__user',
    ).prefetch_related('members__staff__user')


# ───────────────────────────────────────────────────────────────────────────
# Surgery
# ───────────────────────────────────────────────────────────────────────────
class SurgeryListCreateView(PositiveIdMixin, generics.ListCreateAPIView):
    """
    GET  /api/transplant/cases/<case_pk>/surgeries/
    POST /api/transplant/cases/<case_pk>/surgeries/
    """

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), CanRecordSurgery()]
        return [IsAuthenticated(), CanViewTransplant()]

    def get_queryset(self):
        return Surgery.objects.filter(
            case_id=self.kwargs['case_pk'],
        ).select_related(
            'case_donor__donor', 'lead_surgeon__user',
        ).prefetch_related('team_members__staff__user')

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return SurgeryCreateSerializer
        return SurgerySerializer

    def create(self, request, *args, **kwargs):
        data = {**request.data, 'case': self.kwargs['case_pk']}
        serializer = SurgeryCreateSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        surgery = serializer.save()
        audit(request, AuditLog.Action.CREATE, 'transplant.surgery',
              entity_id=surgery.pk)
        return Response(
            SurgerySerializer(surgery).data,
            status=status.HTTP_201_CREATED,
        )


class SurgeryDetailView(PositiveIdMixin, generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/transplant/surgeries/<id>/"""

    permission_classes = [IsAuthenticated, CanRecordSurgery]
    serializer_class = SurgerySerializer
    queryset = Surgery.objects.select_related(
        'case_donor__donor', 'lead_surgeon__user',
    ).prefetch_related('team_members__staff__user')
    http_method_names = ['get', 'patch', 'head', 'options']

    def partial_update(self, request, *args, **kwargs):
        surgery = self.get_object()
        allowed = {'scheduled_at', 'operating_room', 'graft_type'}
        data = {key: value for key, value in request.data.items() if key in allowed}
        serializer = self.get_serializer(surgery, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        surgery = serializer.save()
        if data:
            audit(
                request, AuditLog.Action.UPDATE, 'transplant.surgery',
                entity_id=surgery.pk, patient=surgery.case.recipient,
            )
        return Response(SurgerySerializer(surgery).data)


class SurgeryCompleteView(PositiveIdMixin, generics.GenericAPIView):
    """POST /api/transplant/surgeries/<id>/complete/"""

    permission_classes = [IsAuthenticated, CanRecordSurgery]
    serializer_class = SurgeryCompleteSerializer
    queryset = Surgery.objects.all()

    def post(self, request, pk):
        surgery = self.get_object()
        if surgery.status == Surgery.Status.COMPLETED:
            return Response(
                {'detail': 'Surgery is already completed.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if surgery.status == Surgery.Status.CANCELLED:
            return Response(
                {'detail': 'Cancelled surgery cannot be completed.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Update surgical details
        for field, value in serializer.validated_data.items():
            setattr(surgery, field, value)
        surgery.complete()  # This triggers follow-up plan creation
        audit(request, AuditLog.Action.STATUS_CHANGE, 'transplant.surgery',
              entity_id=surgery.pk)
        return Response(SurgerySerializer(surgery).data)


class SurgeryTeamMemberView(PositiveIdMixin, generics.ListCreateAPIView):
    """
    GET/POST /api/transplant/surgeries/<surgery_pk>/team/
    """

    permission_classes = [IsAuthenticated, CanRecordSurgery]
    serializer_class = SurgeryTeamMemberSerializer

    def get_queryset(self):
        return SurgeryTeamMember.objects.filter(
            surgery_id=self.kwargs['surgery_pk'],
        ).select_related('staff__user')

    def perform_create(self, serializer):
        member = serializer.save(surgery_id=self.kwargs['surgery_pk'])
        audit(
            self.request, AuditLog.Action.CREATE, 'transplant.surgeryteammember',
            entity_id=member.pk, patient=member.surgery.case.recipient,
        )


class SurgeryTeamMemberDeleteView(PositiveIdMixin, generics.DestroyAPIView):
    """DELETE /api/transplant/team-members/<id>/"""

    permission_classes = [IsAuthenticated, CanRecordSurgery]
    queryset = SurgeryTeamMember.objects.all()

    def perform_destroy(self, instance):
        audit(
            self.request, AuditLog.Action.DELETE, 'transplant.surgeryteammember',
            entity_id=instance.pk, patient=instance.surgery.case.recipient,
        )
        instance.delete()


# ───────────────────────────────────────────────────────────────────────────
# FollowUpPlan
# ───────────────────────────────────────────────────────────────────────────
class FollowUpPlanListView(generics.ListAPIView):
    """
    GET /api/transplant/followup/plans/
    Filters: ?case=<id>&patient_role=recipient|donor&status=active|completed
    """

    permission_classes = [IsAuthenticated, CanViewFollowUp]
    serializer_class = FollowUpPlanSerializer
    pagination_class = TransplantPagination

    def get_queryset(self):
        qs = FollowUpPlan.objects.select_related('patient', 'case').prefetch_related('visits')
        params = self.request.query_params
        if case_id := params.get('case'):
            qs = qs.filter(case_id=case_id)
        if role := params.get('patient_role'):
            qs = qs.filter(patient_role=role)
        if st := params.get('status'):
            qs = qs.filter(status=st)
        return qs


class FollowUpPlanDetailView(PositiveIdMixin, generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/transplant/followup/plans/<id>/"""

    def get_permissions(self):
        if self.request.method in ('GET', 'HEAD', 'OPTIONS'):
            return [IsAuthenticated(), CanViewFollowUp()]
        return [IsAuthenticated(), CanManageFollowUp()]

    serializer_class = FollowUpPlanSerializer
    queryset = FollowUpPlan.objects.select_related('patient', 'case')
    http_method_names = ['get', 'patch', 'head', 'options']

    def partial_update(self, request, *args, **kwargs):
        plan = self.get_object()
        previous_status = plan.status
        previous_end_date = plan.end_date
        serializer = FollowUpPlanUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        changes = serializer.validated_data
        update_fields = []
        if 'status' in changes:
            plan.status = changes['status']
            update_fields.append('status')
            if plan.status == FollowUpPlan.Status.COMPLETED and not plan.end_date:
                plan.end_date = changes.get('end_date') or timezone.localdate()
                update_fields.append('end_date')
        if 'end_date' in changes and 'end_date' not in update_fields:
            plan.end_date = changes['end_date']
            update_fields.append('end_date')
        if update_fields:
            plan.save(update_fields=update_fields)
            if plan.status != previous_status or plan.end_date != previous_end_date:
                action = (AuditLog.Action.STATUS_CHANGE
                          if plan.status != previous_status
                          else AuditLog.Action.UPDATE)
                audit(
                    request, action, 'transplant.followupplan',
                    entity_id=plan.pk, patient=plan.patient,
                )
        return Response(FollowUpPlanSerializer(plan).data)


# ───────────────────────────────────────────────────────────────────────────
# FollowUpVisit
# ───────────────────────────────────────────────────────────────────────────
class FollowUpVisitListCreateView(PositiveIdMixin, generics.ListCreateAPIView):
    """
    GET  /api/transplant/followup/plans/<plan_pk>/visits/
    POST /api/transplant/followup/plans/<plan_pk>/visits/
    """

    pagination_class = TransplantPagination

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), CanManageFollowUp()]
        return [IsAuthenticated(), CanViewFollowUp()]

    def get_queryset(self):
        return FollowUpVisit.objects.filter(plan_id=self.kwargs['plan_pk'])

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return FollowUpVisitCreateSerializer
        return FollowUpVisitSerializer

    def create(self, request, *args, **kwargs):
        data = {**request.data, 'plan': self.kwargs['plan_pk']}
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        visit = serializer.save()
        audit(
            self.request, AuditLog.Action.CREATE, 'transplant.followupvisit',
            entity_id=visit.pk, patient=visit.plan.patient,
        )


class FollowUpVisitDetailView(PositiveIdMixin, generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/transplant/followup/visits/<id>/"""

    permission_classes = [IsAuthenticated, CanManageFollowUp]
    serializer_class = FollowUpVisitSerializer
    queryset = FollowUpVisit.objects.all()
    http_method_names = ['get', 'patch', 'head', 'options']

    def perform_update(self, serializer):
        visit = serializer.save()
        audit(
            self.request, AuditLog.Action.UPDATE, 'transplant.followupvisit',
            entity_id=visit.pk, patient=visit.plan.patient,
        )


class RecoveryStatsView(PositiveIdMixin, generics.GenericAPIView):
    """
    GET /api/transplant/followup/plans/<plan_pk>/recovery/
    Returns all visits for a plan, ordered by due_date, for chart rendering.
    """

    permission_classes = [IsAuthenticated, CanViewFollowUp]

    def get(self, request, plan_pk):
        plan = FollowUpPlan.objects.get(pk=plan_pk)
        visits = plan.visits.all().order_by('due_date')
        return Response({
            'plan_id': plan.pk,
            'patient_role': plan.patient_role,
            'visits': FollowUpVisitSerializer(visits, many=True).data,
        })
