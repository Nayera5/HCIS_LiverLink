"""
Patient registration & management API (Stage 4). Permissions follow the approved matrix and are
enforced here, server-side (apps/accounts/rbac.py):

    patients.view             list / profile        super_admin, billing_admin (read), coordinator,
                                                    hepatologist, radiologist, transplant_surgeon
    patients.register         staff registration    super_admin, coordinator
    patients.edit             demographic edits     super_admin, coordinator
    patients.change_category  category changes     super_admin, coordinator, hepatologist
    self.patient_record       own record (portal)   patients (incl. donors)

Audited (AuditLog), without storing field values or search terms: every write (create, update,
category_change) and every opening of an individual profile (profile_view). List, search, filter
and dashboard reads are deliberately not logged.
"""
from django.db.models import Count, Q
from rest_framework import generics, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.accounts.audit import audit
from apps.accounts.models import AuditLog
from apps.accounts.permissions import HasCapability
from apps.accounts.rbac import get_staff_profile

from .models import Patient
from .serializers import (
    OwnContactUpdateSerializer, OwnPatientRecordSerializer, PatientCategorySerializer,
    PatientCreateSerializer, PatientDetailSerializer, PatientListSerializer, PatientUpdateSerializer,
    SelfRegistrationSerializer,
)

ENTITY = 'registry.patient'
A = AuditLog.Action


class PatientPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


def search_patients(qs, text):
    """Every word must match one of: first/last name, MRN, national ID or phone."""
    for term in text.split():
        qs = qs.filter(Q(first_name__icontains=term) | Q(last_name__icontains=term)
                       | Q(mrn__icontains=term) | Q(national_id__startswith=term)
                       | Q(phone__icontains=term))
    return qs


class PatientListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/patients/?search=&category=&sex=&ordering=   (patients.view)
    POST /api/patients/                                    staff registration (patients.register)
    """

    pagination_class = PatientPagination
    ORDERINGS = ('last_name', '-last_name', 'created_at', '-created_at', 'mrn', '-mrn', 'date_of_birth')

    def get_permissions(self):
        cap = 'patients.register' if self.request.method == 'POST' else 'patients.view'
        return [IsAuthenticated(), HasCapability(cap)()]

    def get_queryset(self):
        qs = Patient.objects.all()
        params = self.request.query_params
        if search := params.get('search', '').strip():
            qs = search_patients(qs, search)
        if (category := params.get('category')) in Patient.Category.values:
            qs = qs.filter(category=category)
        if (sex := params.get('sex')) in Patient.Sex.values:
            qs = qs.filter(sex=sex)
        ordering = params.get('ordering')
        if ordering in self.ORDERINGS:
            # Tie-break in the same direction, so "newest first" stays newest first within a second.
            return qs.order_by(ordering, '-id' if ordering.startswith('-') else 'id')
        return qs.order_by('last_name', 'first_name', 'id')

    def get_serializer_class(self):
        return PatientCreateSerializer if self.request.method == 'POST' else PatientListSerializer

    def create(self, request, *args, **kwargs):
        serializer = PatientCreateSerializer(
            data=request.data, context={'registered_by': get_staff_profile(request.user)})
        serializer.is_valid(raise_exception=True)
        patient = serializer.save()
        audit(request, A.CREATE, ENTITY, entity_id=patient.pk, patient=patient)
        return Response(PatientDetailSerializer(patient).data, status=status.HTTP_201_CREATED)


class PatientSummaryView(APIView):
    """
    GET /api/patients/summary/ (patients.view): counts by category for dashboards.
    Aggregates only (no names, MRNs or other patient data), so no audit entry is written.
    """

    permission_classes = [IsAuthenticated, HasCapability('patients.view')]

    def get(self, request):
        counts = dict(Patient.objects.values_list('category').annotate(n=Count('id')))
        by_category = {category: counts.get(category, 0) for category in Patient.Category.values}
        return Response({'total': sum(by_category.values()), 'by_category': by_category})


class PatientDetailView(generics.RetrieveUpdateAPIView):
    """GET /api/patients/<id>/ (patients.view) · PATCH demographics (patients.edit). No PUT/DELETE."""

    queryset = Patient.objects.select_related('user', 'registered_by__user')
    serializer_class = PatientDetailSerializer
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_permissions(self):
        cap = 'patients.edit' if self.request.method == 'PATCH' else 'patients.view'
        return [IsAuthenticated(), HasCapability(cap)()]

    def retrieve(self, request, *args, **kwargs):
        patient = self.get_object()
        audit(request, A.PROFILE_VIEW, ENTITY, entity_id=patient.pk, patient=patient)
        return Response(PatientDetailSerializer(patient).data)

    def partial_update(self, request, *args, **kwargs):
        patient = self.get_object()
        serializer = PatientUpdateSerializer(patient, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        audit(request, A.UPDATE, ENTITY, entity_id=patient.pk, patient=patient)
        patient = self.get_queryset().get(pk=patient.pk)
        return Response(PatientDetailSerializer(patient).data)


class PatientCategoryView(APIView):
    """POST /api/patients/<id>/category/ {category} (patients.change_category)."""

    permission_classes = [IsAuthenticated, HasCapability('patients.change_category')]

    def post(self, request, pk):
        patient = generics.get_object_or_404(Patient.objects.select_related('user', 'registered_by__user'), pk=pk)
        serializer = PatientCategorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_category = serializer.validated_data['category']
        if new_category != patient.category:
            patient.category = new_category
            patient.save(update_fields=['category', 'updated_at'])
            audit(request, A.CATEGORY_CHANGE, ENTITY, entity_id=patient.pk, patient=patient)
        return Response(PatientDetailSerializer(patient).data)


class MyPatientRecordView(APIView):
    """
    GET   /api/patients/me/   the signed-in patient's own record
    PATCH /api/patients/me/   own contact details only (phone, address, emergency contact)
    """

    permission_classes = [IsAuthenticated, HasCapability('self.patient_record')]

    def get_record(self, request):
        # Always read the current row (never a cached relation on the user object).
        return Patient.objects.filter(user=request.user).first()

    def not_linked(self):
        return Response({'detail': 'No hospital record is linked to your account. Please contact the hospital.'},
                        status=status.HTTP_404_NOT_FOUND)

    def get(self, request):
        patient = self.get_record(request)
        if patient is None:
            return self.not_linked()
        audit(request, A.PROFILE_VIEW, ENTITY, entity_id=patient.pk, patient=patient)
        return Response(OwnPatientRecordSerializer(patient).data)

    def patch(self, request):
        patient = self.get_record(request)
        if patient is None:
            return self.not_linked()
        serializer = OwnContactUpdateSerializer(patient, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        audit(request, A.UPDATE, ENTITY, entity_id=patient.pk, patient=patient)
        return Response(OwnPatientRecordSerializer(patient).data)


class SelfRegistrationView(APIView):
    """POST /api/patients/register/: public portal sign-up (account + own patient record)."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'registration'

    def post(self, request):
        serializer = SelfRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        patient = serializer.save()
        audit(request, A.CREATE, ENTITY, entity_id=patient.pk, patient=patient, user=patient.user)
        return Response(
            {'detail': 'Your account has been created. You can now sign in with your username and password.',
             'username': patient.user.username, 'mrn': patient.mrn},
            status=status.HTTP_201_CREATED,
        )
