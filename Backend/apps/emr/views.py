from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from .models import Diagnosis, Document, Encounter, MedicalHistory, VitalSigns
from .permissions import EMRAccess, is_clinical, is_patient, patient_profile, staff_profile
from .serializers import (
    DiagnosisSerializer,
    DocumentSerializer,
    EncounterAddendumSerializer,
    EncounterListSerializer,
    EncounterSerializer,
    MedicalHistorySerializer,
    VitalSignsSerializer,
)


class EMRViewSet(viewsets.ModelViewSet):
    """
    Base viewset for EMR resources.

    - Patients only see their own records (`patient_lookup` is the path from the
      model to the Patient) and only what is released (`released_filter`).
    - Supports simple query-string filters listed in `filter_params`.
    """

    permission_classes = [EMRAccess]
    patient_lookup = "patient"
    released_filter = {}
    filter_params = ()

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if is_patient(user):
            patient = patient_profile(user)
            if patient is None:
                return qs.none()
            qs = qs.filter(**{self.patient_lookup: patient}, **self.released_filter)
        for param in self.filter_params:
            value = self.request.query_params.get(param)
            if value not in (None, ""):
                qs = qs.filter(**{param: value})
        return qs


class EncounterViewSet(EMRViewSet):
    """
    /api/emr/encounters/
    Patients see only signed encounters. Signed encounters are read-only;
    use POST /encounters/{id}/addenda/ to amend them.
    """

    queryset = Encounter.objects.select_related("patient", "staff", "appointment")
    released_filter = {"status": Encounter.Status.SIGNED}
    filter_params = ("patient", "staff", "status", "appointment")

    def get_serializer_class(self):
        return EncounterListSerializer if self.action == "list" else EncounterSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == "retrieve":
            qs = qs.prefetch_related("diagnoses", "vital_signs", "addenda__author")
        return qs

    def perform_destroy(self, instance):
        if instance.status == Encounter.Status.SIGNED:
            raise ValidationError("Signed encounters cannot be deleted.")
        instance.delete()

    @action(detail=True, methods=["post"])
    def sign(self, request, pk=None):
        encounter = self.get_object()
        if encounter.status == Encounter.Status.SIGNED:
            raise ValidationError("Encounter is already signed.")
        staff = staff_profile(request.user)
        if staff is None or staff.pk != encounter.staff_id:
            raise PermissionDenied("Only the treating doctor can sign this encounter.")
        encounter.status = Encounter.Status.SIGNED
        encounter.save(update_fields=["status"])
        return Response(EncounterSerializer(encounter, context=self.get_serializer_context()).data)

    @action(detail=True, methods=["get", "post"])
    def addenda(self, request, pk=None):
        encounter = self.get_object()
        if request.method == "GET":
            data = EncounterAddendumSerializer(encounter.addenda.select_related("author"), many=True).data
            return Response(data)

        if encounter.status != Encounter.Status.SIGNED:
            raise ValidationError("Edit the encounter directly; addenda are only for signed encounters.")
        staff = staff_profile(request.user)
        if staff is None:
            raise PermissionDenied("Only staff members can add addenda.")
        serializer = EncounterAddendumSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(encounter=encounter, author=staff)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class MedicalHistoryViewSet(EMRViewSet):
    """
    /api/emr/medical-history/?patient=<id>&history_type=allergy
    Allergies (history_type=allergy) are what the prescribing screen shows as warnings.
    """

    queryset = MedicalHistory.objects.select_related("recorded_by")
    serializer_class = MedicalHistorySerializer
    filter_params = ("patient", "history_type")

    def perform_create(self, serializer):
        serializer.save(recorded_by=staff_profile(self.request.user))


class DiagnosisViewSet(EMRViewSet):
    """/api/emr/diagnoses/?patient=<id>&encounter=<id>&status=active"""

    queryset = Diagnosis.objects.select_related("encounter")
    serializer_class = DiagnosisSerializer
    released_filter = {"encounter__status": Encounter.Status.SIGNED}
    filter_params = ("patient", "encounter", "status", "icd10_code", "is_primary")

    def perform_destroy(self, instance):
        if instance.encounter.status == Encounter.Status.SIGNED:
            raise ValidationError("Diagnoses on a signed encounter cannot be deleted.")
        instance.delete()


class VitalSignsViewSet(EMRViewSet):
    """/api/emr/vital-signs/?encounter=<id>&encounter__patient=<id>"""

    queryset = VitalSigns.objects.select_related("encounter")
    serializer_class = VitalSignsSerializer
    patient_lookup = "encounter__patient"
    released_filter = {"encounter__status": Encounter.Status.SIGNED}
    filter_params = ("encounter", "encounter__patient")

    def perform_destroy(self, instance):
        if instance.encounter.status == Encounter.Status.SIGNED:
            raise ValidationError("Vital signs on a signed encounter cannot be deleted.")
        instance.delete()


class DocumentViewSet(EMRViewSet):
    """
    /api/emr/documents/  (multipart upload: file_path, title, document_type, patient)
    Patients only see documents with is_released=true.
    """

    queryset = Document.objects.select_related("uploaded_by")
    serializer_class = DocumentSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    released_filter = {"is_released": True}
    filter_params = ("patient", "document_type", "is_released")

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)

    @action(detail=True, methods=["post"])
    def release(self, request, pk=None):
        if not is_clinical(request.user):
            raise PermissionDenied()
        document = self.get_object()
        document.is_released = request.data.get("is_released", True) in (True, "true", "1", 1)
        document.save(update_fields=["is_released"])
        return Response(self.get_serializer(document).data)
