"""
EMR API (module 4), mounted at /api/emr/. Permissions: see permissions.py (module 1 RBAC).

Audit (module 1 audit log, patient = the record's owner): create, update, delete, sign,
addendum and document release. Reads are not logged (per the audit policy).
"""
import os

from django.db import transaction
from django.db.models import Q
from django.http import FileResponse
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.audit import audit
from apps.accounts.models import AuditLog
from apps.accounts.permissions import HasCapability

from .models import Diagnosis, Document, Encounter, Icd10Code, MedicalHistory, VitalSigns
from .permissions import EMRAccess, can_view_all, patient_profile, staff_profile
from .serializers import (
    DiagnosisSerializer,
    DocumentSerializer,
    EncounterAddendumSerializer,
    EncounterListSerializer,
    EncounterSerializer,
    Icd10CodeSerializer,
    MedicalHistorySerializer,
    VitalSignsSerializer,
)

A = AuditLog.Action


class EMRViewSet(viewsets.ModelViewSet):
    """
    Base viewset for EMR resources.

    - Patients/donors only see their own records (`patient_lookup` is the path from the
      model to registry.Patient) and only what is released (`released_filter`).
    - Supports simple query-string filters listed in `filter_params`.
    - Every write is recorded in the audit log as `audit_entity`.
    """

    permission_classes = [EMRAccess]
    patient_lookup = "patient"
    released_filter = {}
    filter_params = ()
    audit_entity = ""

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not can_view_all(user):  # portal user (EMRAccess already refused everyone else)
            patient = patient_profile(user)
            if patient is None:
                return qs.none()
            qs = qs.filter(**{self.patient_lookup: patient}, **self.released_filter)
        for param in self.filter_params:
            value = self.request.query_params.get(param)
            if value not in (None, ""):
                qs = qs.filter(**{param: value})
        return qs

    # --- audit helpers ---------------------------------------------------
    def patient_of(self, instance):
        return instance.patient

    def log(self, action, instance, entity=None, entity_id=None):
        audit(self.request, action, entity or self.audit_entity,
              entity_id=entity_id or instance.pk, patient=self.patient_of(instance))

    def save_kwargs(self):
        """Extra fields set by the server on create (e.g. who recorded it)."""
        return {}

    def perform_create(self, serializer):
        with transaction.atomic():
            self.log(A.CREATE, serializer.save(**self.save_kwargs()))

    def perform_update(self, serializer):
        with transaction.atomic():
            self.log(A.UPDATE, serializer.save())

    def perform_destroy(self, instance):
        pk, patient = instance.pk, self.patient_of(instance)
        with transaction.atomic():
            instance.delete()
            audit(self.request, A.DELETE, self.audit_entity, entity_id=pk, patient=patient)


class EncounterRecordMixin:
    """Child records of an encounter (diagnoses, vitals) cannot be deleted once it is signed."""

    def perform_destroy(self, instance):
        if instance.encounter.status == Encounter.Status.SIGNED:
            raise ValidationError("Records on a signed encounter cannot be deleted.")
        super().perform_destroy(instance)


class EncounterViewSet(EMRViewSet):
    """
    /api/emr/encounters/
    Patients see only signed encounters. Signed encounters are read-only;
    use POST /encounters/{id}/addenda/ to amend them.
    """

    queryset = Encounter.objects.select_related("patient", "staff__user")
    released_filter = {"status": Encounter.Status.SIGNED}
    filter_params = ("patient", "staff", "status")
    audit_entity = "emr.encounter"

    def get_serializer_class(self):
        return EncounterListSerializer if self.action == "list" else EncounterSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == "retrieve":
            qs = qs.prefetch_related("diagnoses", "vital_signs", "addenda__author__user")
        return qs

    def perform_destroy(self, instance):
        if instance.status == Encounter.Status.SIGNED:
            raise ValidationError("Signed encounters cannot be deleted.")
        if (instance.lab_orders.exists() or instance.prescriptions.exists()
                or instance.treatment_plans.exists()):
            raise ValidationError("An encounter with linked clinical orders or plans cannot be deleted.")
        super().perform_destroy(instance)

    @action(detail=True, methods=["post"])
    def sign(self, request, pk=None):
        encounter = self.get_object()
        if encounter.status == Encounter.Status.SIGNED:
            raise ValidationError("Encounter is already signed.")
        staff = staff_profile(request.user)
        if staff is None or staff.pk != encounter.staff_id:
            raise PermissionDenied("Only the treating doctor can sign this encounter.")
        with transaction.atomic():
            encounter.status = Encounter.Status.SIGNED
            encounter.save(update_fields=["status"])
            self.log(A.STATUS_CHANGE, encounter)
        return Response(EncounterSerializer(encounter, context=self.get_serializer_context()).data)

    @action(detail=True, methods=["get", "post"])
    def addenda(self, request, pk=None):
        encounter = self.get_object()
        if request.method == "GET":
            data = EncounterAddendumSerializer(encounter.addenda.select_related("author__user"), many=True).data
            return Response(data)

        if encounter.status != Encounter.Status.SIGNED:
            raise ValidationError("Edit the encounter directly; addenda are only for signed encounters.")
        staff = staff_profile(request.user)
        if staff is None:
            raise PermissionDenied("Only staff members can add addenda.")
        serializer = EncounterAddendumSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            addendum = serializer.save(encounter=encounter, author=staff)
            self.log(A.CREATE, encounter, entity="emr.encounteraddendum", entity_id=addendum.pk)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class MedicalHistoryViewSet(EMRViewSet):
    """
    /api/emr/medical-history/?patient=<id>&history_type=allergy
    Allergies (history_type=allergy) are what the prescribing screen shows as warnings.
    """

    queryset = MedicalHistory.objects.select_related("recorded_by")
    serializer_class = MedicalHistorySerializer
    filter_params = ("patient", "history_type")
    audit_entity = "emr.medicalhistory"

    def save_kwargs(self):
        return {"recorded_by": staff_profile(self.request.user)}


class Icd10SearchView(generics.ListAPIView):
    """
    GET /api/emr/icd10/?q=   search the ICD-10 catalog (emr.view), at most 50 results.
    Matches the start of a code (K74.6 or K746), or every word in the name / search words.
    """

    permission_classes = [IsAuthenticated, HasCapability("emr.view")]
    serializer_class = Icd10CodeSerializer
    pagination_class = None

    def get_queryset(self):
        q = self.request.query_params.get("q", "").strip()
        code = q.replace(".", "")
        if not code:
            return Icd10Code.objects.none()
        if len(code) > 3:
            code = f"{code[:3]}.{code[3:]}"
        match = Q()
        for word in q.split():
            match &= Q(description__icontains=word) | Q(keywords__icontains=word)
        return Icd10Code.objects.filter(match | Q(code__istartswith=code))[:50]


class DiagnosisViewSet(EncounterRecordMixin, EMRViewSet):
    """/api/emr/diagnoses/?patient=<id>&encounter=<id>&status=active"""

    queryset = Diagnosis.objects.select_related("encounter")
    serializer_class = DiagnosisSerializer
    released_filter = {"encounter__status": Encounter.Status.SIGNED}
    filter_params = ("patient", "encounter", "status", "icd10_code", "is_primary")
    audit_entity = "emr.diagnosis"


class VitalSignsViewSet(EncounterRecordMixin, EMRViewSet):
    """/api/emr/vital-signs/?encounter=<id>&encounter__patient=<id>"""

    queryset = VitalSigns.objects.select_related("encounter")
    serializer_class = VitalSignsSerializer
    patient_lookup = "encounter__patient"
    released_filter = {"encounter__status": Encounter.Status.SIGNED}
    filter_params = ("encounter", "encounter__patient")
    audit_entity = "emr.vitalsigns"

    def patient_of(self, instance):
        return instance.encounter.patient


class DocumentViewSet(EMRViewSet):
    """
    /api/emr/documents/  (multipart upload: file_path, title, document_type, patient)
    /api/emr/documents/{id}/download/  the file itself (same access rules as the record)
    Patients only see documents with is_released=true.
    """

    queryset = Document.objects.select_related("uploaded_by")
    serializer_class = DocumentSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    released_filter = {"is_released": True}
    filter_params = ("patient", "document_type", "is_released")
    audit_entity = "emr.document"

    def save_kwargs(self):
        return {"uploaded_by": self.request.user}

    def perform_destroy(self, instance):
        if hasattr(instance, "consent"):
            raise ValidationError("This document is the signed copy of a consent and cannot be deleted.")
        super().perform_destroy(instance)

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        document = self.get_object()
        try:
            handle = document.file_path.open("rb")
        except (FileNotFoundError, ValueError):
            return Response({"detail": "The file is missing."}, status=status.HTTP_404_NOT_FOUND)
        return FileResponse(handle, as_attachment=True, filename=os.path.basename(document.file_path.name))

    @action(detail=True, methods=["post"])
    def release(self, request, pk=None):
        document = self.get_object()
        document.is_released = request.data.get("is_released", True) in (True, "true", "1", 1)
        with transaction.atomic():
            document.save(update_fields=["is_released"])
            self.log(A.STATUS_CHANGE, document)
        return Response(self.get_serializer(document).data)
