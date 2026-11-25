"""HL7 interoperability (spec 4.43-4.44): external systems and the log of every HL7 message."""
from django.db import models
from django.db.models import Q


class ExternalSystem(models.Model):
    """An outside system that exchanges HL7 messages with LiverLink (4.43)."""

    class SystemType(models.TextChoices):
        EXTERNAL_LAB = 'external_lab', 'External lab'
        CLINIC = 'clinic', 'Clinic'
        HOSPITAL_HIS = 'hospital_his', 'Hospital HIS'

    name = models.CharField(max_length=100, unique=True,
                            help_text='Must match the sending application (MSH-3) of its messages.')
    system_type = models.CharField(max_length=20, choices=SystemType.choices)
    host = models.CharField(max_length=255)
    port = models.PositiveIntegerField(help_text='Network port used for HL7 (MLLP).')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class HL7Message(models.Model):
    """One HL7 message sent or received, with its acknowledgement (4.44)."""

    class Direction(models.TextChoices):
        INBOUND = 'inbound', 'Inbound'
        OUTBOUND = 'outbound', 'Outbound'

    class Status(models.TextChoices):
        QUEUED = 'queued', 'Queued'          # addition to the spec: outbound, not answered yet
        RECEIVED = 'received', 'Received'
        PROCESSED = 'processed', 'Processed'
        SENT = 'sent', 'Sent'
        ERROR = 'error', 'Error'

    class AckCode(models.TextChoices):
        AA = 'AA', 'Accepted'
        AE = 'AE', 'Error'
        AR = 'AR', 'Rejected'

    # Nullable (addition to the spec) so messages from unknown senders are logged too.
    system = models.ForeignKey(ExternalSystem, null=True, blank=True, on_delete=models.PROTECT,
                               related_name='messages')
    patient = models.ForeignKey('registry.Patient', null=True, blank=True, on_delete=models.PROTECT,
                                related_name='hl7_messages')
    direction = models.CharField(max_length=10, choices=Direction.choices)
    message_type = models.CharField(max_length=20)
    control_id = models.CharField(max_length=50, blank=True, db_index=True, help_text='MSH-10')
    raw_message = models.TextField()
    ack_code = models.CharField(max_length=2, choices=AckCode.choices, blank=True)
    ack_message = models.TextField(blank=True, help_text='Full text of the ACK (addition to the spec).')
    status = models.CharField(max_length=10, choices=Status.choices)
    error_text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']
        constraints = [
            models.CheckConstraint(condition=Q(direction__in=['inbound', 'outbound']), name='hl7_direction_valid'),
            models.CheckConstraint(
                condition=Q(status__in=['queued', 'received', 'processed', 'sent', 'error']),
                name='hl7_status_valid'),
            models.CheckConstraint(condition=Q(ack_code__in=['', 'AA', 'AE', 'AR']), name='hl7_ack_code_valid'),
        ]

    def __str__(self):
        return f'{self.message_type} {self.control_id} ({self.direction})'
