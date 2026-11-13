from django.contrib import admin
from .models import FeeCategory, FeeStructure, FeeInvoice, InvoiceItem, PaymentTransaction


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0


class PaymentTransactionInline(admin.TabularInline):
    model = PaymentTransaction
    extra = 0
    readonly_fields = ['transaction_reference', 'payment_date', 'amount_paid', 'payment_method', 'payer_name', 'status']

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(FeeCategory)
class FeeCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']


@admin.register(FeeStructure)
class FeeStructureAdmin(admin.ModelAdmin):
    list_display = ['class_level', 'category', 'academic_year', 'amount', 'due_date']
    list_filter = ['academic_year', 'class_level', 'category']


@admin.register(FeeInvoice)
class FeeInvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'student', 'academic_year', 'total_amount', 'paid_amount', 'outstanding_balance', 'status', 'due_date']
    list_filter = ['status', 'academic_year']
    search_fields = ['invoice_number', 'student__first_name', 'student__last_name', 'student__admission_number']
    inlines = [InvoiceItemInline, PaymentTransactionInline]


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ['transaction_reference', 'invoice', 'amount_paid', 'payment_method', 'payer_name', 'payment_date', 'status']
    list_filter = ['status', 'payment_method', 'payment_date']
    search_fields = ['transaction_reference', 'payer_name', 'invoice__invoice_number']
    readonly_fields = [f.name for f in PaymentTransaction._meta.fields]

    def has_add_permission(self, request):
        return False
