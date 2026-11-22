"""
Billing & Payments (spec §13 and entity dictionary §4.38–§4.41).

- Service: catalog of billable services and their prices.
- Invoice: a bill issued to a patient, with its line items.
- InvoiceItem: one billed service on an invoice (price is snapshotted at billing time).
- Payment: a desk payment (cash or card) against an invoice.

Deviations from the spec (agreed for this first pass, scheduling/labs/imaging not built yet):
- Online payment is dropped: Payment.method is cash/card only, and there is no gateway_txn_id.
- InvoiceItem.appointment_id is a plain nullable integer (no FK yet): the Appointment model
  does not exist yet. It will become a real foreign key once the scheduling app is built.
- Automatic invoice generation from completed appointments/scans/tests is not implemented yet
  for the same reason; invoices are created manually by billing staff for now.
"""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import F, Q, Sum
from django.utils import timezone

INVOICE_NO_PREFIX = 'INV-'
RECEIPT_NO_PREFIX = 'RCT-'
SEQUENCE_MIN_DIGITS = 6


class _NumberSequence(models.Model):
    """
    Single-row counter shared by invoice/receipt numbering, locked (SELECT … FOR UPDATE) inside
    the transaction that issues the number, so concurrent requests never get the same one.
    Mirrors apps.registry.models.MRNSequence.
    """

    id = models.PositiveSmallIntegerField(primary_key=True)
    last_value = models.PositiveBigIntegerField(default=0)

    class Meta:
        abstract = True

    @classmethod
    def next_number(cls, prefix):
        if not transaction.get_connection().in_atomic_block:
            raise RuntimeError(f'{cls.__name__}.next_number() must be called inside transaction.atomic().')
        seq, _ = cls.objects.select_for_update().get_or_create(pk=1)
        seq.last_value = F('last_value') + 1
        seq.save(update_fields=['last_value'])
        seq.refresh_from_db(fields=['last_value'])
        return f'{prefix}{seq.last_value:0{SEQUENCE_MIN_DIGITS}d}'


class InvoiceSequence(_NumberSequence):
    class Meta:
        verbose_name = 'invoice number sequence'
        constraints = [models.CheckConstraint(condition=Q(id=1), name='billing_invoiceseq_single_row')]

    @classmethod
    def next_invoice_no(cls):
        return cls.next_number(INVOICE_NO_PREFIX)


class ReceiptSequence(_NumberSequence):
    class Meta:
        verbose_name = 'receipt number sequence'
        constraints = [models.CheckConstraint(condition=Q(id=1), name='billing_receiptseq_single_row')]

    @classmethod
    def next_receipt_no(cls):
        return cls.next_number(RECEIPT_NO_PREFIX)


class Service(models.Model):
    """The catalog of billable services and their prices (§4.38)."""

    class Category(models.TextChoices):
        CONSULTATION = 'consultation', 'Consultation'
        IMAGING = 'imaging', 'Imaging'
        LAB = 'lab', 'Lab'
        AI_ANALYSIS = 'ai_analysis', 'AI analysis'
        EVALUATION_PACKAGE = 'evaluation_package', 'Evaluation package'
        SURGERY = 'surgery', 'Surgery'

    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=150)
    category = models.CharField(max_length=20, choices=Category.choices)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.CheckConstraint(condition=Q(price__gte=0), name='billing_service_price_non_negative'),
            models.CheckConstraint(
                condition=Q(category__in=[
                    'consultation', 'imaging', 'lab', 'ai_analysis', 'evaluation_package', 'surgery',
                ]),
                name='billing_service_category_valid'),
        ]

    def __str__(self):
        return f'{self.code} · {self.name} ({self.price} EGP)'


class Invoice(models.Model):
    """A bill issued to a patient for services received (§4.39)."""

    class Status(models.TextChoices):
        UNPAID = 'unpaid', 'Unpaid'
        PARTIALLY_PAID = 'partially_paid', 'Partially paid'
        PAID = 'paid', 'Paid'
        CANCELLED = 'cancelled', 'Cancelled'

    OPEN_STATUSES = ('unpaid', 'partially_paid')

    invoice_no = models.CharField(max_length=20, unique=True, editable=False)
    patient = models.ForeignKey('registry.Patient', on_delete=models.PROTECT, related_name='invoices')
    issued_by = models.ForeignKey(
        'accounts.Staff', null=True, blank=True, on_delete=models.SET_NULL, related_name='invoices_issued',
        help_text='Staff member who issued it (empty if generated automatically).',
    )
    issue_date = models.DateField(default=timezone.localdate)
    due_date = models.DateField()
    total_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0'),
        validators=[MinValueValidator(Decimal('0'))], help_text='Sum of its line totals.',
    )
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.UNPAID)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-issue_date', '-id']
        indexes = [
            models.Index(fields=['patient', 'status'], name='billing_invoice_pat_status_idx'),
        ]
        constraints = [
            models.CheckConstraint(condition=Q(total_amount__gte=0), name='billing_invoice_total_non_negative'),
            models.CheckConstraint(
                condition=Q(status__in=['unpaid', 'partially_paid', 'paid', 'cancelled']),
                name='billing_invoice_status_valid'),
            models.CheckConstraint(condition=Q(due_date__gte=F('issue_date')), name='billing_invoice_due_after_issue'),
        ]

    def __str__(self):
        return f'{self.invoice_no} · {self.patient.mrn} ({self.status})'

    def clean(self):
        super().clean()
        if self.due_date and self.issue_date and self.due_date < self.issue_date:
            raise ValidationError({'due_date': 'The due date cannot be before the issue date.'})

    def save(self, *args, **kwargs):
        if self._state.adding and not self.invoice_no:
            with transaction.atomic(using=kwargs.get('using')):
                self.invoice_no = InvoiceSequence.next_invoice_no()
                super().save(*args, **kwargs)
            return
        super().save(*args, **kwargs)

    def recompute_total(self, *, save=True):
        total = self.items.aggregate(total=Sum('line_total'))['total'] or Decimal('0')
        self.total_amount = total
        if save:
            self.save(update_fields=['total_amount', 'updated_at'])
        return total

    def paid_amount(self):
        return self.payments.filter(status=Payment.Status.SUCCEEDED).aggregate(
            paid=Sum('amount'))['paid'] or Decimal('0')

    def recompute_status(self, *, save=True):
        """Status becomes paid when payments cover the total (business rule)."""
        if self.status == self.Status.CANCELLED:
            return self.status
        paid = self.paid_amount()
        if paid <= 0:
            new_status = self.Status.UNPAID
        elif paid < self.total_amount:
            new_status = self.Status.PARTIALLY_PAID
        else:
            new_status = self.Status.PAID
        if new_status != self.status:
            self.status = new_status
            if save:
                self.save(update_fields=['status', 'updated_at'])
        return self.status

    def cancel(self):
        if self.paid_amount() > 0:
            raise ValidationError({'status': 'An invoice with recorded payments cannot be cancelled.'})
        self.status = self.Status.CANCELLED
        self.save(update_fields=['status', 'updated_at'])


class InvoiceItem(models.Model):
    """One line on an invoice: which service, how many, and at what price (§4.40)."""

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name='invoice_items')
    appointment_id = models.PositiveBigIntegerField(
        null=True, blank=True,
        help_text='Visit the charge came from, if any. Not yet a foreign key: the Appointment '
                  'model does not exist until the scheduling app is built.',
    )
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0'))],
        help_text='Price per unit at billing time (copied from the service).',
    )
    line_total = models.DecimalField(max_digits=10, decimal_places=2, editable=False)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(quantity__gte=1), name='billing_invoiceitem_quantity_positive'),
            models.CheckConstraint(condition=Q(unit_price__gte=0), name='billing_invoiceitem_unit_price_non_negative'),
        ]

    def __str__(self):
        return f'{self.service.code} × {self.quantity} on {self.invoice.invoice_no}'

    def save(self, *args, **kwargs):
        if self.unit_price is None:
            self.unit_price = self.service.price
        self.line_total = self.unit_price * self.quantity
        super().save(*args, **kwargs)


class Payment(models.Model):
    """A desk payment (cash or card) against an invoice (§4.41, online payment dropped)."""

    class Method(models.TextChoices):
        CASH = 'cash', 'Cash'
        CARD = 'card', 'Card'

    class Status(models.TextChoices):
        SUCCEEDED = 'succeeded', 'Succeeded'
        REFUNDED = 'refunded', 'Refunded'

    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name='payments')
    received_by = models.ForeignKey(
        'accounts.Staff', null=True, blank=True, on_delete=models.SET_NULL, related_name='payments_received',
        help_text='Billing staff who took the payment.',
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    method = models.CharField(max_length=10, choices=Method.choices)
    receipt_no = models.CharField(max_length=20, unique=True, editable=False)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.SUCCEEDED)
    paid_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-paid_at', '-id']
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name='billing_payment_amount_positive'),
            models.CheckConstraint(condition=Q(method__in=['cash', 'card']), name='billing_payment_method_valid'),
            models.CheckConstraint(
                condition=Q(status__in=['succeeded', 'refunded']), name='billing_payment_status_valid'),
        ]

    def __str__(self):
        return f'{self.receipt_no} · {self.amount} EGP on {self.invoice.invoice_no}'

    def clean(self):
        super().clean()
        if self.invoice_id and self.amount:
            already_paid = self.invoice.payments.filter(status=self.Status.SUCCEEDED) \
                .exclude(pk=self.pk).aggregate(paid=Sum('amount'))['paid'] or Decimal('0')
            if self.status == self.Status.SUCCEEDED and already_paid + self.amount > self.invoice.total_amount:
                raise ValidationError({
                    'amount': 'The sum of successful payments cannot exceed the invoice total.'})

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        if is_new and not self.receipt_no:
            with transaction.atomic(using=kwargs.get('using')):
                self.receipt_no = ReceiptSequence.next_receipt_no()
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)
        self.invoice.recompute_status()
