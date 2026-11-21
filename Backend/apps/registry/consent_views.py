"""
Consents API (Stage 6). Permissions follow the approved matrix (apps/accounts/rbac.py):

    consents.view     list a patient's consents   coordinator, hepatologist, radiologist,
                                                  transplant_surgeon (NOT super_admin)
    consents.record   record / withdraw           transplant_coordinator, hepatologist
    self.consents     own consents, read-only     patients and donors

Super Admin does not see consent records; consent actions are monitored in the audit log.
Audit (entity `registry.consent`, patient = the signer): create and withdraw. Reads are not
logged (list views, per the audit policy). Consents are never deleted.

Not required for donor applications: submitting or accepting an application does not need, and
does not create, a consent.
"""
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.audit import audit
from apps.accounts.models import AuditLog
from apps.accounts.permissions import HasCapability
from apps.accounts.rbac import get_staff_profile

from .consent_serializers import (
    ConsentRecordSerializer, ConsentSerializer, OwnConsentSerializer, WitnessSerializer, active_witnesses,
)
from .models import Consent, Patient

ENTITY = 'registry.consent'
A = AuditLog.Action
CONSENT_QUERYSET = Consent.objects.select_related('witnessed_by__user', 'recorded_by__user', 'withdrawn_by__user')


class PatientConsentsView(APIView):
    """
    GET  /api/patients/<id>/consents/   full history, newest first          (consents.view)
    POST /api/patients/<id>/consents/   {consent_type, signed_at, witnessed_by?}  (consents.record)
    """

    def get_permissions(self):
        cap = 'consents.record' if self.request.method == 'POST' else 'consents.view'
        return [IsAuthenticated(), HasCapability(cap)()]

    def get(self, request, pk):
        patient = generics.get_object_or_404(Patient, pk=pk)
        consents = CONSENT_QUERYSET.filter(patient=patient).order_by('-signed_at', '-id')
        return Response(ConsentSerializer(consents, many=True).data)

    def post(self, request, pk):
        patient = generics.get_object_or_404(Patient, pk=pk)
        serializer = ConsentRecordSerializer(data=request.data, context={'patient': patient})
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                consent = Consent.objects.create(patient=patient, recorded_by=get_staff_profile(request.user),
                                                 **serializer.validated_data)
        except IntegrityError:  # concurrent duplicate (one active consent per type)
            raise ValidationError({'consent_type': ['This person already has an active consent of this type.']})
        audit(request, A.CREATE, ENTITY, entity_id=consent.pk, patient=patient)
        return Response(ConsentSerializer(CONSENT_QUERYSET.get(pk=consent.pk)).data, status=status.HTTP_201_CREATED)


class ConsentWithdrawView(APIView):
    """POST /api/consents/<id>/withdraw/ (consents.record). Final; the record is kept."""

    permission_classes = [IsAuthenticated, HasCapability('consents.record')]

    @transaction.atomic
    def post(self, request, pk):
        consent = generics.get_object_or_404(Consent.objects.select_for_update().select_related('patient'), pk=pk)
        try:
            consent.withdraw(get_staff_profile(request.user))
        except DjangoValidationError as exc:
            raise ValidationError(exc.message_dict)
        audit(request, A.WITHDRAW, ENTITY, entity_id=consent.pk, patient=consent.patient)
        return Response(ConsentSerializer(CONSENT_QUERYSET.get(pk=consent.pk)).data)


class ConsentWitnessesView(generics.ListAPIView):
    """GET /api/consents/witnesses/ (consents.record): active clinical/coordination staff (no Billing/Super Admin)."""

    permission_classes = [IsAuthenticated, HasCapability('consents.record')]
    serializer_class = WitnessSerializer
    pagination_class = None

    def get_queryset(self):
        return active_witnesses().order_by('user__first_name', 'user__last_name', 'id')


class MyConsentsView(APIView):
    """GET /api/consents/mine/ (self.consents): own consents, read-only, newest first."""

    permission_classes = [IsAuthenticated, HasCapability('self.consents')]

    def get(self, request):
        record = Patient.objects.filter(user=request.user).first()
        if record is None:
            return Response({'detail': 'No hospital record is linked to your account. Please contact the hospital.'},
                            status=status.HTTP_404_NOT_FOUND)
        consents = Consent.objects.filter(patient=record).select_related('witnessed_by__user') \
            .order_by('-signed_at', '-id')
        return Response(OwnConsentSerializer(consents, many=True).data)
