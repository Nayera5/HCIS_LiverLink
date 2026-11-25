"""
Donor applications API (Stage 5). Permissions follow the approved matrix (apps/accounts/rbac.py):

    self.donor_applications              donor portal: submit / view / withdraw OWN applications
    donor_applications.view              staff list + detail     super_admin, coordinator, hepatologist,
                                                                 radiologist, transplant_surgeon
    donor_applications.screen            status decisions        transplant_coordinator
    donor_applications.submit_on_behalf  submit / withdraw for   transplant_coordinator
                                         a donor

Donors are Patients with category `donor` (no separate account type). Only a donor-category
patient record can apply; the recipient is named by MRN only (see donor_serializers.py).

Audit (accounts.AuditLog, entity `registry.donorapplication`, patient = the donor): create,
withdraw and status_change. Reads (lists and details) are not logged, per the audit policy.
"""
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.accounts.audit import audit
from apps.accounts.models import AuditLog
from apps.accounts.permissions import HasCapability
from apps.accounts.rbac import get_staff_profile

from .donor_serializers import (
    MRN_NOT_FOUND, OwnApplicationCreateSerializer, OwnApplicationSerializer, ScreeningSerializer,
    find_recipient,
    StaffApplicationCreateSerializer, StaffApplicationSerializer,
)
from .models import DonorApplication, Patient

ENTITY = 'registry.donorapplication'
A = AuditLog.Action
DUPLICATE_OPEN = {'recipient_mrn': ['There is already an open application for this recipient.']}


class SubmissionThrottle(ScopedRateThrottle):
    """Limits application submissions (and so MRN guessing); reads are not throttled."""

    scope_attr = 'throttle_scope'

    def allow_request(self, request, view):
        if request.method != 'POST':
            return True
        return super().allow_request(request, view)


def _django_errors(exc):
    return exc.message_dict if hasattr(exc, 'message_dict') else {'detail': exc.messages}


def _create(serializer, request):
    """Recheck recipient eligibility while saving, then audit the application."""
    try:
        with transaction.atomic():
            data = serializer.validated_data
            recipient = find_recipient(data['recipient'].mrn, for_update=True)
            if recipient is None or recipient.pk != data['recipient'].pk:
                raise ValidationError({'recipient_mrn': [MRN_NOT_FOUND]})
            application = DonorApplication.objects.create(**data)
    except IntegrityError:
        raise ValidationError(DUPLICATE_OPEN)
    audit(request, A.CREATE, ENTITY, entity_id=application.pk, patient=application.donor)
    return application


def _withdraw(request, application):
    try:
        application.withdraw()
    except DjangoValidationError as exc:
        raise ValidationError(_django_errors(exc))
    audit(request, A.WITHDRAW, ENTITY, entity_id=application.pk, patient=application.donor)


# --------------------------------------------------------------------------- donor portal

class OwnDonorMixin:
    permission_classes = [IsAuthenticated, HasCapability('self.donor_applications')]

    def own_record(self, request):
        return Patient.objects.filter(user=request.user).first()


class MyApplicationsView(OwnDonorMixin, APIView):
    """
    GET  /api/donor-applications/mine/   {can_apply, reason, results: [own applications]}
    POST /api/donor-applications/mine/   {recipient_mrn, relationship}  (donor-category records only)
    """

    throttle_classes = [SubmissionThrottle]
    throttle_scope = 'donor_application'

    @staticmethod
    def eligibility(record):
        if record is None:
            return 'No hospital record is linked to your account. Please contact the hospital.'
        if record.category != Patient.Category.DONOR:
            return ('Only people registered as living donors can apply. Please contact the transplant '
                    'coordinator if you would like to become a donor.')
        return ''

    def get(self, request):
        record = self.own_record(request)
        reason = self.eligibility(record)
        applications = (DonorApplication.objects.filter(donor=record).select_related('recipient')
                        .order_by('-submitted_at', '-id') if record else [])
        return Response({'can_apply': not reason, 'reason': reason,
                         'results': OwnApplicationSerializer(applications, many=True).data})

    def post(self, request):
        record = self.own_record(request)
        reason = self.eligibility(record)
        if reason:
            code = status.HTTP_404_NOT_FOUND if record is None else status.HTTP_403_FORBIDDEN
            return Response({'detail': reason}, status=code)
        serializer = OwnApplicationCreateSerializer(data=request.data, context={'donor': record})
        serializer.is_valid(raise_exception=True)
        application = _create(serializer, request)
        return Response(OwnApplicationSerializer(application).data, status=status.HTTP_201_CREATED)


class MyApplicationWithdrawView(OwnDonorMixin, APIView):
    """POST /api/donor-applications/mine/<id>/withdraw/  (own applications only; others are 404)."""

    @transaction.atomic
    def post(self, request, pk):
        record = self.own_record(request)
        if record is None:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        application = generics.get_object_or_404(
            DonorApplication.objects.select_for_update().select_related('recipient'), pk=pk, donor=record)
        _withdraw(request, application)
        return Response(OwnApplicationSerializer(application).data)


# --------------------------------------------------------------------------- staff

class ApplicationPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


STAFF_QUERYSET = DonorApplication.objects.select_related('donor', 'recipient', 'screened_by__user')


class ApplicationListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/donor-applications/?status=&search=&donor=&recipient=   (donor_applications.view)
         search matches donor or recipient MRN / name. Newest first. Not audited (list view).
    POST /api/donor-applications/ {donor_mrn, recipient_mrn, relationship}  (submit_on_behalf)
    """

    serializer_class = StaffApplicationSerializer
    pagination_class = ApplicationPagination

    def get_permissions(self):
        cap = 'donor_applications.submit_on_behalf' if self.request.method == 'POST' else 'donor_applications.view'
        return [IsAuthenticated(), HasCapability(cap)()]

    def get_queryset(self):
        qs = STAFF_QUERYSET
        params = self.request.query_params
        if (value := params.get('status')) in DonorApplication.Status.values:
            qs = qs.filter(status=value)
        elif value == 'open':
            qs = qs.filter(status__in=DonorApplication.OPEN_STATUSES)
        for key in ('donor', 'recipient'):
            if (value := params.get(key, '')).isdigit():
                qs = qs.filter(**{f'{key}_id': int(value)})
        if search := params.get('search', '').strip():
            for term in search.split():
                qs = qs.filter(Q(donor__mrn__icontains=term) | Q(recipient__mrn__icontains=term)
                               | Q(donor__first_name__icontains=term) | Q(donor__last_name__icontains=term)
                               | Q(recipient__first_name__icontains=term) | Q(recipient__last_name__icontains=term))
        return qs.order_by('-submitted_at', '-id')

    def create(self, request, *args, **kwargs):
        serializer = StaffApplicationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application = _create(serializer, request)
        return Response(StaffApplicationSerializer(application).data, status=status.HTTP_201_CREATED)


class ApplicationDetailView(generics.RetrieveAPIView):
    """GET /api/donor-applications/<id>/ (donor_applications.view). Not audited (policy: writes only)."""

    permission_classes = [IsAuthenticated, HasCapability('donor_applications.view')]
    serializer_class = StaffApplicationSerializer
    queryset = STAFF_QUERYSET


class ApplicationStatusView(APIView):
    """POST /api/donor-applications/<id>/status/ {status, screening_notes?} (donor_applications.screen)."""

    permission_classes = [IsAuthenticated, HasCapability('donor_applications.screen')]

    @transaction.atomic
    def post(self, request, pk):
        application = generics.get_object_or_404(DonorApplication.objects.select_for_update(), pk=pk)
        serializer = ScreeningSerializer(data=request.data, context={'application': application})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            application.apply_screening(data['status'], get_staff_profile(request.user),
                                        data.get('screening_notes'))
        except DjangoValidationError as exc:
            raise ValidationError(_django_errors(exc))
        audit(request, A.STATUS_CHANGE, ENTITY, entity_id=application.pk, patient=application.donor)
        return Response(StaffApplicationSerializer(STAFF_QUERYSET.get(pk=application.pk)).data)


class ApplicationWithdrawView(APIView):
    """POST /api/donor-applications/<id>/withdraw/ : coordinator records a withdrawal for the donor."""

    permission_classes = [IsAuthenticated, HasCapability('donor_applications.submit_on_behalf')]

    @transaction.atomic
    def post(self, request, pk):
        application = generics.get_object_or_404(DonorApplication.objects.select_for_update(), pk=pk)
        _withdraw(request, application)
        return Response(StaffApplicationSerializer(STAFF_QUERYSET.get(pk=application.pk)).data)
