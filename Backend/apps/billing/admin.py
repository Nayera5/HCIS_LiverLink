from django.contrib import admin

from .models import Invoice, InvoiceItem, Payment, Service


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ['receipt_no']


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'category', 'price', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['code', 'name']


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_no', 'patient', 'issue_date', 'due_date', 'total_amount', 'status']
    list_filter = ['status']
    search_fields = ['invoice_no', 'patient__mrn', 'patient__first_name', 'patient__last_name']
    readonly_fields = ['invoice_no', 'total_amount']
    inlines = [InvoiceItemInline, PaymentInline]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['receipt_no', 'invoice', 'amount', 'method', 'status', 'paid_at']
    list_filter = ['method', 'status']
    search_fields = ['receipt_no', 'invoice__invoice_no']
    readonly_fields = ['receipt_no']
