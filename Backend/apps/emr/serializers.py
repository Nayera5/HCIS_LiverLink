from rest_framework import serializers

from .models import Diagnosis, Document, Encounter, EncounterAddendum, MedicalHistory, VitalSigns
from .permissions import staff_profile


def _reject_if_signed(encounter):
    if encounter and encounter.status == Encounter.Status.SIGNED:
        raise serializers.ValidationError(
            {"encounter": "This encounter is signed. Add an addendum instead."}
        )


class VitalSignsSerializer(serializers.ModelSerializer):
    class Meta:
        model = VitalSigns
        fields = [
            "vitals_id", "encounter", "bp_systolic", "bp_diastolic", "pulse",
            "temperature", "weight_kg", "height_cm", "bmi", "recorded_at",
        ]
        read_only_fields = ["vitals_id", "bmi"]

    def validate(self, attrs):
        encounter = attrs.get("encounter") or getattr(self.instance, "encounter", None)
        _reject_if_signed(encounter)
        sys_ = attrs.get("bp_systolic", getattr(self.instance, "bp_systolic", None))
        dia = attrs.get("bp_diastolic", getattr(self.instance, "bp_diastolic", None))
        if sys_ is not None and dia is not None and sys_ <= dia:
            raise serializers.ValidationError({"bp_systolic": "Systolic must be higher than diastolic."})
        return attrs


class DiagnosisSerializer(serializers.ModelSerializer):
    class Meta:
        model = Diagnosis
        fields = [
            "diagnosis_id", "encounter", "patient", "icd10_code", "description",
            "is_primary", "status", "diagnosed_at",
        ]
        read_only_fields = ["diagnosis_id", "patient"]

    def validate_icd10_code(self, value):
        return value.strip().upper()

    def validate(self, attrs):
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
        return attrs

    def create(self, validated_data):
        validated_data["patient"] = validated_data["encounter"].patient
        return super().create(validated_data)


class EncounterAddendumSerializer(serializers.ModelSerializer):
    author_name = serializers.StringRelatedField(source="author", read_only=True)

    class Meta:
        model = EncounterAddendum
        fields = ["addendum_id", "encounter", "author", "author_name", "text", "created_at"]
        read_only_fields = ["addendum_id", "encounter", "author", "created_at"]


class EncounterSerializer(serializers.ModelSerializer):
    diagnoses = DiagnosisSerializer(many=True, read_only=True)
    vital_signs = VitalSignsSerializer(many=True, read_only=True)
    addenda = EncounterAddendumSerializer(many=True, read_only=True)

    class Meta:
        model = Encounter
        fields = [
            "encounter_id", "patient", "appointment", "staff", "encounter_date",
            "chief_complaint", "clinical_notes", "status",
            "diagnoses", "vital_signs", "addenda",
        ]
        read_only_fields = ["encounter_id", "status"]
        extra_kwargs = {"staff": {"required": False}}

    def validate(self, attrs):
        if self.instance:
            _reject_if_signed(self.instance)
        # Default the treating doctor to the logged-in staff member.
        if not attrs.get("staff") and not self.instance:
            staff = staff_profile(self.context["request"].user)
            if staff is None:
                raise serializers.ValidationError({"staff": "Treating doctor is required."})
            attrs["staff"] = staff
        appointment = attrs.get("appointment")
        patient = attrs.get("patient") or getattr(self.instance, "patient", None)
        if appointment and patient and getattr(appointment, "patient_id", patient.pk) != patient.pk:
            raise serializers.ValidationError({"appointment": "Appointment belongs to a different patient."})
        return attrs


class EncounterListSerializer(serializers.ModelSerializer):
    """Lightweight rows for list views."""

    class Meta:
        model = Encounter
        fields = ["encounter_id", "patient", "appointment", "staff", "encounter_date", "chief_complaint", "status"]


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
        extra_kwargs = {"file_path": {"write_only": True}}

    def get_file_url(self, obj):
        request = self.context.get("request")
        if not obj.file_path:
            return None
        return request.build_absolute_uri(obj.file_path.url) if request else obj.file_path.url
