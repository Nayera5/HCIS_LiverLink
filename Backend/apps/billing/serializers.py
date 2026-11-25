from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from rest_framework import serializers

from apps.registry.models import Patient
from apps.radiology.models import ImagingOrder
from apps.scheduling.models import Appointment

from .models import Invoice, InvoiceItem, Payment, Service


def _django_errors(exc):
    return exc.message_dict if hasattr(exc, 'message_dict') else {'non_field_errors': exc.messages}


# --------------------------------------------------------------------------- services

class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = [
            'id', 'code', 'name', 'category', 'coding_system', 'standard_code',
            'price', 'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError('Price cannot be negative.')
        return value

    def validate_code(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('This field may not be blank.')
        qs = Service.objects.filter(code__iexact=value)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('A service with this code already exists.')
        return value


# --------------------------------------------------------------------------- invoices (read)

class InvoiceItemSerializer(serializers.ModelSerializer):
    service_code = serializers.CharField(source='service.code', read_only=True)
    service_name = serializers.CharField(source='service.name', read_only=True)

    class Meta:
        model = InvoiceItem
        fields = ['id', 'service', 'service_code', 'service_name', 'appointment', 'surgery', 'imaging_order',
                  'quantity', 'unit_price', 'line_total']
        read_only_fields = fields


class PaymentSerializer(serializers.ModelSerializer):
    received_by_name = serializers.SerializerMethodField()
    has_receipt = serializers.SerializerMethodField()

    def get_has_receipt(self, payment):
        return payment.status in Payment.RECEIPT_STATUSES

    class Meta:
        model = Payment
        fields = ['id', 'receipt_no', 'amount', 'method', 'status', 'paid_at',
                  'received_by', 'received_by_name', 'gateway_txn_id', 'has_receipt']
        read_only_fields = fields

    def get_received_by_name(self, payment):
        staff = payment.received_by
        return staff.user.get_full_name() or staff.user.username if staff else None


class InvoiceListSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    patient_mrn = serializers.CharField(source='patient.mrn', read_only=True)
    paid_amount = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = ['id', 'invoice_no', 'patient', 'patient_name', 'patient_mrn', 'issue_date',
                  'due_date', 'total_amount', 'paid_amount', 'status']
        read_only_fields = fields

    def get_paid_amount(self, invoice):
        return invoice.paid_amount()


class InvoiceDetailSerializer(InvoiceListSerializer):
    issued_by_name = serializers.SerializerMethodField()
    items = InvoiceItemSerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)

    class Meta(InvoiceListSerializer.Meta):
        fields = InvoiceListSerializer.Meta.fields + ['issued_by_name', 'items', 'payments', 'created_at']
        read_only_fields = fields

    def get_issued_by_name(self, invoice):
        staff = invoice.issued_by
        return staff.user.get_full_name() or staff.user.username if staff else None


# --------------------------------------------------------------------------- invoices (write)

class InvoiceItemInputSerializer(serializers.Serializer):
    service = serializers.PrimaryKeyRelatedField(queryset=Service.objects.filter(is_active=True))
    quantity = serializers.IntegerField(min_value=1, default=1)
    appointment = serializers.PrimaryKeyRelatedField(
        queryset=Appointment.objects.all(), required=False, allow_null=True)
    imaging_order = serializers.PrimaryKeyRelatedField(
        queryset=ImagingOrder.objects.all(), required=False, allow_null=True)


class InvoiceCreateSerializer(serializers.Serializer):
    """Staff picks a patient and one or more services; prices are snapshotted at this moment."""

    patient = serializers.PrimaryKeyRelatedField(queryset=Patient.objects.all())
    due_date = serializers.DateField()
    items = InvoiceItemInputSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError('An invoice must have at least one item.')
        return value

    def validate(self, attrs):
        patient = attrs['patient']
        for item in attrs['items']:
            appointment = item.get('appointment')
            if appointment is not None and appointment.patient_id != patient.pk:
                raise serializers.ValidationError(
                    {'items': ['An appointment on the invoice must belong to the billed patient.']})
            imaging_order = item.get('imaging_order')
            if imaging_order is not None and imaging_order.patient_id != patient.pk:
                raise serializers.ValidationError(
                    {'items': ['An imaging order on the invoice must belong to the billed patient.']})
            if imaging_order is not None and imaging_order.status != 'acquired':
                raise serializers.ValidationError(
                    {'items': ['An imaging order can be billed only after the scan is acquired.']})
            if imaging_order is not None and item['service'].category != Service.Category.IMAGING:
                raise serializers.ValidationError(
                    {'items': ['An imaging order must be billed with an imaging service.']})
            if (imaging_order is not None and imaging_order.billing_service_id is not None
                    and item['service'].pk != imaging_order.billing_service_id):
                raise serializers.ValidationError(
                    {'items': ['An imaging order must use its selected billing service.']})
        return attrs

    def validate_due_date(self, value):
        issue_date = self.context.get('issue_date')
        if issue_date and value < issue_date:
            raise serializers.ValidationError('The due date cannot be before the issue date.')
        return value

    def create(self, validated):
        items_data = validated.pop('items')
        invoice = Invoice(patient=validated['patient'], due_date=validated['due_date'],
                          issued_by=self.context.get('issued_by'))
        try:
            with transaction.atomic():
                imaging_order_ids = sorted({
                    item_data['imaging_order'].pk
                    for item_data in items_data if item_data.get('imaging_order') is not None
                })
                if imaging_order_ids:
                    list(ImagingOrder.objects.select_for_update().filter(
                        pk__in=imaging_order_ids,
                    ).order_by('pk'))
                    if InvoiceItem.objects.filter(
                        imaging_order_id__in=imaging_order_ids, is_current_imaging_charge=True,
                    ).exclude(invoice__status=Invoice.Status.CANCELLED).exists():
                        raise serializers.ValidationError({
                            'items': ['An active invoice already contains this imaging order.'],
                        })
                invoice.full_clean(exclude=['invoice_no', 'total_amount'])
                invoice.save()
                total = Decimal('0')
                for item_data in items_data:
                    service = item_data['service']
                    item = InvoiceItem(
                        invoice=invoice, service=service, quantity=item_data['quantity'],
                        unit_price=service.price, appointment=item_data.get('appointment'),
                        imaging_order=item_data.get('imaging_order'),
                    )
                    item.full_clean(exclude=['line_total'])
                    item.save()
                    total += item.line_total
                invoice.total_amount = total
                invoice.save(update_fields=['total_amount', 'updated_at'])
        except DjangoValidationError as exc:
            raise serializers.ValidationError(_django_errors(exc))
        except IntegrityError:
            raise serializers.ValidationError(
                {'non_field_errors': ['This invoice could not be saved because of a conflicting change. '
                                      'Please try again.']})
        return invoice


class PaymentCreateSerializer(serializers.Serializer):
    """Desk payment (cash or card) recorded by billing staff against an invoice."""

    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0.01'))
    # Desk only: online payments are started by the patient through Paymob.
    method = serializers.ChoiceField(choices=[c for c in Payment.Method.choices if c[0] in Payment.DESK_METHODS])

    @staticmethod
    def check_open(invoice):
        if invoice.status in (Invoice.Status.PAID, Invoice.Status.CANCELLED):
            raise serializers.ValidationError(
                {'non_field_errors': [f'An invoice that is {invoice.get_status_display().lower()} '
                                      'cannot take further payments.']})

    def validate(self, attrs):
        self.check_open(self.context['invoice'])
        return attrs

    def create(self, validated):
        """
        Locks the invoice row (SELECT ... FOR UPDATE) for the whole check-and-save, so two desk
        payments recorded at the same time cannot both pass the "not more than the total" check.
        The second one waits, then sees the first payment and the updated status.
        """
        try:
            with transaction.atomic():
                invoice = Invoice.objects.select_for_update().get(pk=self.context['invoice'].pk)
                self.check_open(invoice)
                payment = Payment(invoice=invoice, received_by=self.context.get('received_by'), **validated)
                payment.full_clean(exclude=['receipt_no'])
                payment.save()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(_django_errors(exc))
        return payment
