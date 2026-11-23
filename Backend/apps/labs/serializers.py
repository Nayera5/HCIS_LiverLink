from rest_framework import serializers

from apps.registry.models import Patient

from .models import LabOrder, LabResult, LabTest


class LabTestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabTest
        fields = ['id', 'code', 'name', 'unit', 'normal_min', 'normal_max', 'critical_min', 'critical_max']


class LabResultSerializer(serializers.ModelSerializer):
    test_code = serializers.CharField(source='lab_test.code', read_only=True)
    test_name = serializers.CharField(source='lab_test.name', read_only=True)
    unit = serializers.CharField(source='lab_test.unit', read_only=True)
    normal_min = serializers.DecimalField(source='lab_test.normal_min', max_digits=12, decimal_places=4, read_only=True)
    normal_max = serializers.DecimalField(source='lab_test.normal_max', max_digits=12, decimal_places=4, read_only=True)
    is_pending = serializers.SerializerMethodField()

    class Meta:
        model = LabResult
        fields = ['id', 'lab_order', 'lab_test', 'test_code', 'test_name', 'unit', 'normal_min', 'normal_max',
                  'value', 'flag', 'result_time', 'is_released', 'is_pending']

    def get_is_pending(self, obj):
        return obj.value is None


class PendingResultSerializer(LabResultSerializer):
    patient = serializers.IntegerField(source='lab_order.patient_id', read_only=True)
    patient_mrn = serializers.CharField(source='lab_order.patient.mrn', read_only=True)
    patient_name = serializers.SerializerMethodField()
    priority = serializers.CharField(source='lab_order.priority', read_only=True)
    order_date = serializers.DateTimeField(source='lab_order.order_date', read_only=True)

    class Meta(LabResultSerializer.Meta):
        fields = LabResultSerializer.Meta.fields + ['patient', 'patient_mrn', 'patient_name', 'priority', 'order_date']

    def get_patient_name(self, obj):
        p = obj.lab_order.patient
        return f'{p.first_name} {p.last_name}'


class LabOrderSerializer(serializers.ModelSerializer):
    results = LabResultSerializer(many=True, read_only=True)
    patient_mrn = serializers.CharField(source='patient.mrn', read_only=True)
    patient_name = serializers.SerializerMethodField()
    ordered_by_name = serializers.SerializerMethodField()

    class Meta:
        model = LabOrder
        fields = ['id', 'patient', 'patient_mrn', 'patient_name', 'ordered_by', 'ordered_by_name', 'order_date',
                  'priority', 'status', 'results']
        read_only_fields = fields

    def get_patient_name(self, obj):
        return f'{obj.patient.first_name} {obj.patient.last_name}'

    def get_ordered_by_name(self, obj):
        return obj.ordered_by.user.get_full_name() or obj.ordered_by.user.username


class MyLabOrderTestSerializer(serializers.ModelSerializer):
    """
    One test of the patient's own order. Never includes the value or flag: those are visible only on
    the results page, after the doctor releases them.
        pending          waiting for the lab
        awaiting_review  the lab reported, the doctor has not released it yet
        available        released: see "My lab results"
    """
    test_name = serializers.CharField(source='lab_test.name', read_only=True)
    state = serializers.SerializerMethodField()

    class Meta:
        model = LabResult
        fields = ['id', 'test_name', 'state']

    def get_state(self, obj):
        if obj.value is None:
            return 'pending'
        return 'available' if obj.is_released else 'awaiting_review'


class MyLabOrderSerializer(serializers.ModelSerializer):
    tests = MyLabOrderTestSerializer(source='results', many=True, read_only=True)
    ordered_by_name = serializers.SerializerMethodField()

    class Meta:
        model = LabOrder
        fields = ['id', 'order_date', 'priority', 'status', 'ordered_by_name', 'tests']
        read_only_fields = fields

    def get_ordered_by_name(self, obj):
        return obj.ordered_by.user.get_full_name() or obj.ordered_by.user.username


class LabOrderCreateSerializer(serializers.Serializer):
    patient = serializers.PrimaryKeyRelatedField(queryset=Patient.objects.all())
    priority = serializers.ChoiceField(choices=LabOrder.Priority.choices, default=LabOrder.Priority.ROUTINE)
    tests = serializers.PrimaryKeyRelatedField(queryset=LabTest.objects.all(), many=True, allow_empty=False)

    def validate_tests(self, tests):
        if len({t.pk for t in tests}) != len(tests):
            raise serializers.ValidationError('Each test can only be ordered once per order.')
        return tests


class ResultEntrySerializer(serializers.Serializer):
    value = serializers.DecimalField(max_digits=12, decimal_places=4, min_value=0)
    result_time = serializers.DateTimeField(required=False)
