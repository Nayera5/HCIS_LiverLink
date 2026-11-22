from rest_framework import serializers

from apps.registry.models import Patient

from .models import Drug, Prescription, Route, TreatmentPlan


def _staff_name(staff):
    return staff.user.get_full_name() or staff.user.username


def _patient_name(patient):
    return f'{patient.first_name} {patient.last_name}'


class DrugSerializer(serializers.ModelSerializer):
    class Meta:
        model = Drug
        fields = ['id', 'code', 'name', 'generic_name', 'drug_class', 'default_route', 'common_dose', 'is_active']
        read_only_fields = ['id', 'code']

    def validate_name(self, value):
        value = value.strip()
        qs = Drug.objects.filter(name__iexact=value)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('A drug with this name already exists in the catalog.')
        return value


class PrescriptionSerializer(serializers.ModelSerializer):
    drug_name = serializers.CharField(source='drug.name', read_only=True)
    drug_code = serializers.CharField(source='drug.code', read_only=True)
    route_label = serializers.CharField(source='get_route_display', read_only=True)
    patient_mrn = serializers.CharField(source='patient.mrn', read_only=True)
    patient_name = serializers.SerializerMethodField()
    prescribed_by_name = serializers.SerializerMethodField()
    is_current = serializers.BooleanField(read_only=True)
    duration_days = serializers.SerializerMethodField()

    class Meta:
        model = Prescription
        fields = ['id', 'patient', 'patient_mrn', 'patient_name', 'prescribed_by', 'prescribed_by_name',
                  'drug', 'drug_name', 'drug_code', 'dose', 'route', 'route_label', 'frequency',
                  'start_date', 'end_date', 'duration_days', 'instructions', 'status', 'is_current',
                  'stopped_at', 'stop_reason', 'created_at']
        read_only_fields = fields

    def get_patient_name(self, obj):
        return _patient_name(obj.patient)

    def get_prescribed_by_name(self, obj):
        return _staff_name(obj.prescribed_by)

    def get_duration_days(self, obj):
        return (obj.end_date - obj.start_date).days if obj.end_date else None


class MyPrescriptionSerializer(PrescriptionSerializer):
    """Portal view: no internal patient/staff IDs."""

    class Meta(PrescriptionSerializer.Meta):
        fields = ['id', 'drug_name', 'dose', 'route', 'route_label', 'frequency', 'start_date', 'end_date',
                  'duration_days', 'instructions', 'status', 'is_current', 'stopped_at', 'prescribed_by_name']
        read_only_fields = fields


class PrescriptionCreateSerializer(serializers.Serializer):
    patient = serializers.PrimaryKeyRelatedField(queryset=Patient.objects.all())
    drug = serializers.PrimaryKeyRelatedField(queryset=Drug.objects.all())
    dose = serializers.CharField(max_length=100)
    route = serializers.ChoiceField(choices=Route.choices)
    frequency = serializers.CharField(max_length=100)
    start_date = serializers.DateField()
    end_date = serializers.DateField(required=False, allow_null=True)
    instructions = serializers.CharField(required=False, allow_blank=True, default='')

    def validate(self, attrs):
        end = attrs.get('end_date')
        if end is not None and end <= attrs['start_date']:
            raise serializers.ValidationError({'end_date': 'The end date must be after the start date.'})
        return attrs


class ReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=2000, trim_whitespace=True)


class OptionalReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=2000, required=False, allow_blank=True, default='')


class TreatmentPlanSerializer(serializers.ModelSerializer):
    plan_type_label = serializers.CharField(source='get_plan_type_display', read_only=True)
    patient_mrn = serializers.CharField(source='patient.mrn', read_only=True)
    patient_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    review_due = serializers.BooleanField(read_only=True)

    class Meta:
        model = TreatmentPlan
        fields = ['id', 'patient', 'patient_mrn', 'patient_name', 'created_by', 'created_by_name', 'plan_type',
                  'plan_type_label', 'goals', 'steps', 'start_date', 'review_date', 'review_due', 'status',
                  'created_at', 'updated_at']
        read_only_fields = fields

    def get_patient_name(self, obj):
        return _patient_name(obj.patient)

    def get_created_by_name(self, obj):
        return _staff_name(obj.created_by)


class MyTreatmentPlanSerializer(TreatmentPlanSerializer):
    class Meta(TreatmentPlanSerializer.Meta):
        fields = ['id', 'plan_type', 'plan_type_label', 'goals', 'steps', 'start_date', 'review_date', 'status',
                  'created_by_name', 'updated_at']
        read_only_fields = fields


class TreatmentPlanCreateSerializer(serializers.Serializer):
    patient = serializers.PrimaryKeyRelatedField(queryset=Patient.objects.all())
    plan_type = serializers.ChoiceField(choices=TreatmentPlan.PlanType.choices)
    goals = serializers.CharField()
    steps = serializers.CharField(required=False, allow_blank=True, default='')
    start_date = serializers.DateField()
    review_date = serializers.DateField(required=False, allow_null=True)

    def validate(self, attrs):
        review = attrs.get('review_date')
        if review is not None and review < attrs['start_date']:
            raise serializers.ValidationError({'review_date': 'The review date cannot be before the start date.'})
        return attrs


class TreatmentPlanUpdateSerializer(serializers.Serializer):
    """PATCH: any editable field, plus a mandatory reason that goes to the audit log."""
    plan_type = serializers.ChoiceField(choices=TreatmentPlan.PlanType.choices, required=False)
    goals = serializers.CharField(required=False)
    steps = serializers.CharField(required=False, allow_blank=True)
    start_date = serializers.DateField(required=False)
    review_date = serializers.DateField(required=False, allow_null=True)
    reason = serializers.CharField(max_length=2000)
