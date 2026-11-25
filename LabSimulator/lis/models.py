"""The lab's own records. They are filled from HL7 messages only."""
from django.db import models


class Order(models.Model):
    class Status(models.TextChoices):  # sample status
        RECEIVED = 'received', 'Received'
        PROCESSING = 'processing', 'Processing'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'  # set by an ORM^O01 cancel message, not by lab staff

    accession_number = models.CharField(max_length=30, unique=True, null=True)
    sender = models.CharField(max_length=100)
    placer_order_id = models.CharField(max_length=50, help_text="The sender's internal order ID.")
    mrn = models.CharField(max_length=50)
    last_name = models.CharField(max_length=100, blank=True)
    first_name = models.CharField(max_length=100, blank=True)
    birth_date = models.CharField(max_length=10, blank=True)
    sex = models.CharField(max_length=5, blank=True)
    priority = models.CharField(max_length=10, default='routine')
    ordered_by = models.CharField(max_length=150, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.RECEIVED)
    received_at = models.DateTimeField(auto_now_add=True)
    results_sent_at = models.DateTimeField(null=True, blank=True)  # set when LiverLink answers AA

    class Meta:
        ordering = ['-received_at', '-id']
        constraints = [
            models.UniqueConstraint(fields=['sender', 'placer_order_id'], name='lis_order_unique_placer_id'),
        ]


class OrderTest(models.Model):
    """One requested test; `value` is empty until lab staff enter it."""
    FLAGS = ['N', 'L', 'H', 'LL', 'HH']  # HL7 table 0078

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='tests')
    code = models.CharField(max_length=30)
    name = models.CharField(max_length=150)
    value = models.CharField(max_length=20, blank=True)
    unit = models.CharField(max_length=30, blank=True)
    reference_range = models.CharField(max_length=50, blank=True)
    flag = models.CharField(max_length=2, blank=True)
    result_time = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['id']


class Message(models.Model):
    """HL7 Message Monitor: every message received or sent, with its ACK."""
    direction = models.CharField(max_length=10)  # inbound / outbound
    message_type = models.CharField(max_length=20, default='unknown')
    control_id = models.CharField(max_length=50, blank=True)
    raw_message = models.TextField()
    ack_code = models.CharField(max_length=2, blank=True)
    ack_message = models.TextField(blank=True)
    status = models.CharField(max_length=10)     # processed / sent / error
    error_text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-id']
