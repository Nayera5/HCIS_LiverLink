from django.core.validators import FileExtensionValidator
from django.urls import reverse
from rest_framework import serializers

from apps.accounts.models import Staff, User
from apps.accounts.rbac import EMR_DOCTOR_TITLES

from .models import Diagnosis, Document, Encounter, EncounterAddendum, Icd10Code, MedicalHistory, VitalSigns
from .permissions import staff_profile

ALLOWED_DOCUMENT_EXTENSIONS = ["pdf", "jpg", "jpeg", "png"]
MAX_DOCUMENT_SIZE = 20 * 1024 * 1024  # 20 MB


def doctors():
    """Active staff who can be the treating doctor of an encounter (hepatologist, transplant surgeon)."""
    return Staff.objects.filter(
        user__is_active=True, user__role=User.Role.CLINICAL_STAFF, job_title__in=EMR_DOCTOR_TITLES,
    ).select_related("user")


def _staff_name(staff):
    return (staff.user.get_full_name() or staff.user.username) if staff else None


def _reject_if_signed(encounter):
    if encounter and encounter.status == Encounter.Status.SIGNED:
        raise serializers.ValidationError(
            {"encounter": "This encounter is signed. Add an addendum instead."}
        )


def _reject_move(instance, attrs):
    """A diagnosis or reading stays on its encounter (moving it would bypass the signed lock)."""
    if instance and "encounter" in attrs and attrs["encounter"].pk != instance.encounter_id:
        raise serializers.ValidationError({"encounter": "This record cannot be moved to another encounter."})


class Icd10CodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Icd10Code
        fields = ["code", "description"]


class VitalSignsSerializer(serializers.ModelSerializer):
    class Meta:
        model = VitalSigns
        fields = [
            "vitals_id", "encounter", "bp_systolic", "bp_diastolic", "pulse",
            "temperature", "weight_kg", "height_cm", "bmi", "recorded_at",
        ]
        read_only_fields = ["vitals_id", "bmi"]

    def validate(self, attrs):
        _reject_move(self.instance, attrs)
        encounter = attrs.get("encounter") or getattr(self.instance, "encounter", None)
        _reject_if_signed(encounter)
        sys_ = attrs.get("bp_systolic", getattr(self.instance, "bp_systolic", None))
        dia = attrs.get("bp_diastolic", getattr(self.instance, "bp_diastolic", None))
        if sys_ is not None and dia is not None and sys_ <= dia:
            raise serializers.ValidationError({"bp_systolic": "Systolic must be higher than diastolic."})
        return attrs


class DiagnosisSerializer(serializers.ModelSerializer):
    """The code must be in the ICD-10 catalog; the name is always taken from it."""

    class Meta:
        model = Diagnosis
        fields = [
            "diagnosis_id", "encounter", "patient", "icd10_code", "description",
            "is_primary", "status", "diagnosed_at",
        ]
        read_only_fields = ["diagnosis_id", "patient", "description"]

    def validate_icd10_code(self, value):
        code = value.strip().upper()
        if not Icd10Code.objects.filter(pk=code).exists():
            raise serializers.ValidationError("Choose a diagnosis from the ICD-10 catalog.")
        return code

    def validate(self, attrs):
        _reject_move(self.instance, attrs)
        encounter = attrs.get("encounter") or getattr(self.instance, "encounter", None)
        # Status changes (active -> resolved) are allowed later; new/edited coding on a signed visit is not.
        if self.instance is None or set(attrs) - {"status"}:
            _reject_if_signed(encounter)
        if attrs.get("is_primary"):
            others = Diagnosis.objects.filter(encounter=encounter, is_primary=True)
            if self.instance:
                others = others.exclude(pk=self.instance.pk)
            if others.exists():
                raise serializers.ValidationError(
                    {"is_primary": "This encounter already has a primary diagnosis."}
                )
        if "icd10_code" in attrs:
            attrs["description"] = Icd10Code.objects.get(pk=attrs["icd10_code"]).description
        return attrs

    def create(self, validated_data):
        validated_data["patient"] = validated_data["encounter"].patient
        return super().create(validated_data)


class EncounterAddendumSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = EncounterAddendum
        fields = ["addendum_id", "encounter", "author", "author_name", "text", "created_at"]
        read_only_fields = ["addendum_id", "encounter", "author", "created_at"]

    def get_author_name(self, addendum):
        return _staff_name(addendum.author)


class EncounterSerializer(serializers.ModelSerializer):
    staff = serializers.PrimaryKeyRelatedField(
        queryset=doctors(), required=False,
        error_messages={"does_not_exist": "Choose an active hepatologist or transplant surgeon.",
                        "incorrect_type": "Choose an active hepatologist or transplant surgeon."},
    )
    staff_name = serializers.SerializerMethodField()
    can_sign = serializers.SerializerMethodField()
    diagnoses = DiagnosisSerializer(many=True, read_only=True)
    vital_signs = VitalSignsSerializer(many=True, read_only=True)
    addenda = EncounterAddendumSerializer(many=True, read_only=True)

    class Meta:
        model = Encounter
        fields = [
            "encounter_id", "patient", "appointment", "staff", "staff_name", "encounter_date",
            "chief_complaint", "clinical_notes", "status", "can_sign",
            "diagnoses", "vital_signs", "addenda",
        ]
        read_only_fields = ["encounter_id", "status"]

    def get_staff_name(self, encounter):
        return _staff_name(encounter.staff)

    def get_can_sign(self, encounter):
        """True when the signed-in user is the treating doctor of this open encounter."""
        request = self.context.get("request")
        staff = staff_profile(request.user) if request else None
        return encounter.status == Encounter.Status.OPEN and staff is not None and staff.pk == encounter.staff_id

    def validate(self, attrs):
        if self.instance:
            _reject_if_signed(self.instance)
        # Default the treating doctor to the logged-in doctor.
        if not attrs.get("staff") and not self.instance:
            staff = staff_profile(self.context["request"].user)
            if staff is None or not doctors().filter(pk=staff.pk).exists():
                raise serializers.ValidationError({"staff": "Treating doctor is required."})
            attrs["staff"] = staff
        # The appointment (if any) must be a visit of the same patient.
        appointment = attrs.get("appointment")
        patient = attrs.get("patient") or getattr(self.instance, "patient", None)
        if appointment is not None and appointment.patient_id != getattr(patient, "pk", None):
            raise serializers.ValidationError({"appointment": "This appointment belongs to another patient."})
        return attrs


class EncounterListSerializer(serializers.ModelSerializer):
    """Lightweight rows for list views."""

    staff_name = serializers.SerializerMethodField()

    class Meta:
        model = Encounter
        fields = ["encounter_id", "patient", "appointment", "staff", "staff_name", "encounter_date",
                  "chief_complaint", "status"]

    def get_staff_name(self, encounter):
        return _staff_name(encounter.staff)


class MedicalHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalHistory
        fields = ["history_id", "patient", "history_type", "description", "onset_date", "recorded_by"]
        read_only_fields = ["history_id", "recorded_by"]


class DocumentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "document_id", "patient", "uploaded_by", "document_type", "title",
            "file_path", "file_url", "is_released", "uploaded_at",
        ]
        read_only_fields = ["document_id", "uploaded_by", "uploaded_at"]
        extra_kwargs = {"file_path": {"write_only": True,
                                      "validators": [FileExtensionValidator(ALLOWED_DOCUMENT_EXTENSIONS)]}}

    def validate_file_path(self, value):
        if value.size > MAX_DOCUMENT_SIZE:
            raise serializers.ValidationError("The file is too large (maximum 20 MB).")
        return value

    def get_file_url(self, obj):
        """Authenticated download endpoint (files are never served from a public URL)."""
        if not obj.file_path:
            return None
        url = reverse("emr:document-download", args=[obj.pk])
        request = self.context.get("request")
        return request.build_absolute_uri(url) if request else url
