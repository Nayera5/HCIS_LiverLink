"""
Billing & Payments API (spec §13). Permissions follow the same pattern as apps.registry.views:

    billing.manage_services   service catalog CRUD      super_admin, billing_admin
    billing.view              invoices/payments (read)  super_admin, billing_admin
    billing.create_invoice    create/cancel invoices     super_admin, billing_admin
    billing.record_payment    record a desk payment      super_admin, billing_admin
    self.invoices             own invoices (portal)       patients (incl. donors)

No audit log entries are written for billing yet: AuditLog.patient is the only domain link it
supports today, and billing's own records (Invoice/Payment) are themselves the record of who
issued an invoice or received a payment via `issued_by` / `received_by`.
"""
from io import BytesIO

from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import HasCapability
from apps.accounts.rbac import get_staff_profile
from apps.registry.models import Patient

from .models import Invoice, Payment, Service
from .serializers import (
    InvoiceCreateSerializer, InvoiceDetailSerializer, InvoiceListSerializer, PaymentCreateSerializer,
    PaymentSerializer, ServiceSerializer,
)


class BillingPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class ServicePagination(BillingPagination):
    """
    Catalog pages. The invoice form still asks for up to max_page_size active services in one
    request so it can offer them all in its picker.
    """

    page_size = 10


# --------------------------------------------------------------------------- service catalog

class ServiceListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/services/?category=&coding_system=&status=&active_only=&page=&page_size=
         (billing.view, or services.view: the read-only Services page for clinical staff & patients)
    POST /api/services/                                                                (billing.manage_services)

    Paginated: {count, next, previous, results}; 10 per page by default, page_size up to 100.
    """

    serializer_class = ServiceSerializer
    pagination_class = ServicePagination

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), HasCapability('billing.manage_services')()]
        return [IsAuthenticated(), HasCapability('billing.view', 'services.view')()]

    def get_queryset(self):
        qs = Service.objects.all()
        params = self.request.query_params
        if (category := params.get('category')) in Service.Category.values:
            qs = qs.filter(category=category)
        if (coding_system := params.get('coding_system')) in Service.CodingSystem.values:
            qs = qs.filter(coding_system=coding_system)
        if params.get('status') == 'active':
            qs = qs.filter(is_active=True)
        elif params.get('status') == 'inactive':
            qs = qs.filter(is_active=False)
        if params.get('active_only') == 'true':
            qs = qs.filter(is_active=True)
        # A unique tie-breaker keeps page boundaries stable when two services share a name.
        return qs.order_by('name', 'id')


class ServiceDetailView(generics.RetrieveUpdateAPIView):
    """GET (billing.view) · PATCH (billing.manage_services). No DELETE: deactivate instead."""

    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_permissions(self):
        cap = 'billing.manage_services' if self.request.method == 'PATCH' else 'billing.view'
        return [IsAuthenticated(), HasCapability(cap)()]

    def partial_update(self, request, *args, **kwargs):
        service = self.get_object()
        serializer = ServiceSerializer(service, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(ServiceSerializer(service).data)


# --------------------------------------------------------------------------- invoices (staff)

class InvoiceListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/invoices/?patient=&status=   (billing.view)
    POST /api/invoices/                     create an invoice (billing.create_invoice)
    """

    pagination_class = BillingPagination

    def get_permissions(self):
        cap = 'billing.create_invoice' if self.request.method == 'POST' else 'billing.view'
        return [IsAuthenticated(), HasCapability(cap)()]

    def get_queryset(self):
        qs = Invoice.objects.select_related('patient', 'issued_by__user')
        params = self.request.query_params
        if patient_id := params.get('patient'):
            qs = qs.filter(patient_id=patient_id)
        if (invoice_status := params.get('status')) in Invoice.Status.values:
            qs = qs.filter(status=invoice_status)
        if search := params.get('search', '').strip():
            qs = qs.filter(Q(invoice_no__icontains=search) | Q(patient__mrn__icontains=search)
                          | Q(patient__first_name__icontains=search) | Q(patient__last_name__icontains=search))
        return qs

    def get_serializer_class(self):
        return InvoiceCreateSerializer if self.request.method == 'POST' else InvoiceListSerializer

    def create(self, request, *args, **kwargs):
        serializer = InvoiceCreateSerializer(
            data=request.data,
            context={'issued_by': get_staff_profile(request.user), 'issue_date': None},
        )
        serializer.is_valid(raise_exception=True)
        invoice = serializer.save()
        return Response(InvoiceDetailSerializer(invoice).data, status=status.HTTP_201_CREATED)


class InvoiceDetailView(generics.RetrieveAPIView):
    """GET /api/invoices/<id>/ (billing.view)."""

    queryset = Invoice.objects.select_related('patient', 'issued_by__user').prefetch_related(
        'items__service', 'payments__received_by__user')
    serializer_class = InvoiceDetailSerializer
    permission_classes = [IsAuthenticated, HasCapability('billing.view')]


class InvoiceCancelView(APIView):
    """POST /api/invoices/<id>/cancel/ (billing.create_invoice)."""

    permission_classes = [IsAuthenticated, HasCapability('billing.create_invoice')]

    def post(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        try:
            invoice.cancel()
        except Exception as exc:  # ValidationError
            raise _as_drf_error(exc)
        return Response(InvoiceDetailSerializer(invoice).data)


class PaymentCreateView(APIView):
    """POST /api/invoices/<id>/payments/ {amount, method} (billing.record_payment)."""

    permission_classes = [IsAuthenticated, HasCapability('billing.record_payment')]

    def post(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        serializer = PaymentCreateSerializer(
            data=request.data, context={'invoice': invoice, 'received_by': get_staff_profile(request.user)})
        serializer.is_valid(raise_exception=True)
        payment = serializer.save()
        invoice.refresh_from_db()
        return Response(
            {'payment': PaymentSerializer(payment).data, 'invoice': InvoiceDetailSerializer(invoice).data},
            status=status.HTTP_201_CREATED,
        )


class PatientInvoicesView(generics.ListAPIView):
    """GET /api/patients/<id>/invoices/ (billing.view): one patient's balance & history."""

    serializer_class = InvoiceListSerializer
    permission_classes = [IsAuthenticated, HasCapability('billing.view')]

    def get_queryset(self):
        return Invoice.objects.filter(patient_id=self.kwargs['pk']).select_related('patient')

    def list(self, request, *args, **kwargs):
        patient = get_object_or_404(Patient, pk=self.kwargs['pk'])
        invoices = self.get_queryset()
        outstanding = sum((inv.total_amount - inv.paid_amount() for inv in invoices
                          if inv.status in Invoice.OPEN_STATUSES), start=0)
        return Response({
            'patient': {'id': patient.pk, 'mrn': patient.mrn, 'name': patient.full_name},
            'outstanding_balance': outstanding,
            'invoices': InvoiceListSerializer(invoices, many=True).data,
        })


# --------------------------------------------------------------------------- patient portal

class MyInvoicesView(generics.ListAPIView):
    """GET /api/invoices/me/ (self.invoices): the signed-in patient's own invoices & balance."""

    serializer_class = InvoiceListSerializer
    permission_classes = [IsAuthenticated, HasCapability('self.invoices')]

    def get_queryset(self):
        return Invoice.objects.filter(patient__user=self.request.user)

    def list(self, request, *args, **kwargs):
        invoices = self.get_queryset()
        outstanding = sum((inv.total_amount - inv.paid_amount() for inv in invoices
                          if inv.status in Invoice.OPEN_STATUSES), start=0)
        return Response({
            'outstanding_balance': outstanding,
            'invoices': InvoiceListSerializer(invoices, many=True).data,
        })


class MyInvoiceDetailView(generics.RetrieveAPIView):
    """GET /api/invoices/me/<id>/ (self.invoices): only the signed-in patient's own invoice."""

    serializer_class = InvoiceDetailSerializer
    permission_classes = [IsAuthenticated, HasCapability('self.invoices')]

    def get_queryset(self):
        return Invoice.objects.filter(patient__user=self.request.user).prefetch_related(
            'items__service', 'payments')


# --------------------------------------------------------------------------- receipts (PDF)

def _as_drf_error(exc):
    from django.core.exceptions import ValidationError as DjangoValidationError
    from rest_framework.exceptions import ValidationError as DRFValidationError

    if isinstance(exc, DjangoValidationError):
        detail = exc.message_dict if hasattr(exc, 'message_dict') else {'non_field_errors': exc.messages}
        return DRFValidationError(detail)
    return DRFValidationError({'non_field_errors': [str(exc)]})


def _render_receipt_pdf(payment):
    """A simple one-page PDF receipt for a succeeded or refunded payment."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.pdfgen import canvas

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 2 * cm

    def line(text, size=11, gap=0.7 * cm, bold=False):
        nonlocal y
        pdf.setFont('Helvetica-Bold' if bold else 'Helvetica', size)
        pdf.drawString(2 * cm, y, text)
        y -= gap

    invoice = payment.invoice
    patient = invoice.patient
    line('LiverLink — Payment Receipt', size=16, bold=True, gap=1.2 * cm)
    line(f'Receipt No: {payment.receipt_no}')
    line(f'Invoice No: {invoice.invoice_no}')
    line(f'Patient: {patient.full_name} (MRN {patient.mrn})')
    line(f'Amount Paid: {payment.amount} EGP')
    line(f'Method: {payment.get_method_display()}')
    line(f'Status: {payment.get_status_display()}')
    line(f'Paid At: {payment.paid_at.strftime("%Y-%m-%d %H:%M")}')
    if payment.received_by:
        staff = payment.received_by
        line(f'Received By: {staff.user.get_full_name() or staff.user.username}')
    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer


class _ReceiptViewMixin:
    def get_payment(self):
        raise NotImplementedError

    def get(self, request, *args, **kwargs):
        payment = self.get_payment()
        buffer = _render_receipt_pdf(payment)
        return FileResponse(buffer, as_attachment=True, filename=f'{payment.receipt_no}.pdf',
                            content_type='application/pdf')


class ReceiptPDFView(_ReceiptViewMixin, APIView):
    """GET /api/payments/<id>/receipt/ (billing.view): staff download of any receipt."""

    permission_classes = [IsAuthenticated, HasCapability('billing.view')]

    def get_payment(self):
        return get_object_or_404(Payment.objects.select_related(
            'invoice__patient', 'received_by__user'), pk=self.kwargs['pk'])


class MyReceiptPDFView(_ReceiptViewMixin, APIView):
    """GET /api/payments/me/<id>/receipt/ (self.invoices): own receipt only."""

    permission_classes = [IsAuthenticated, HasCapability('self.invoices')]

    def get_payment(self):
        payment = Payment.objects.select_related('invoice__patient', 'received_by__user').filter(
            pk=self.kwargs['pk'], invoice__patient__user=self.request.user).first()
        if payment is None:
            raise Http404
        return payment
