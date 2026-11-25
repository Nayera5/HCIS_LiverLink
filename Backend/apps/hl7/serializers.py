from rest_framework import serializers

from .models import HL7Message


class HL7MessageSerializer(serializers.ModelSerializer):
    system_name = serializers.CharField(source='system.name', default='', read_only=True)
    patient_mrn = serializers.CharField(source='patient.mrn', default='', read_only=True)
    can_resend = serializers.SerializerMethodField()

    class Meta:
        model = HL7Message
        fields = ['id', 'created_at', 'direction', 'message_type', 'control_id', 'system_name', 'patient_mrn',
                  'status', 'ack_code', 'error_text', 'can_resend']

    def get_can_resend(self, obj):
        return obj.direction == HL7Message.Direction.OUTBOUND and obj.status in (
            HL7Message.Status.ERROR, HL7Message.Status.QUEUED)


class HL7MessageDetailSerializer(HL7MessageSerializer):
    class Meta(HL7MessageSerializer.Meta):
        fields = HL7MessageSerializer.Meta.fields + ['raw_message', 'ack_message']
