import uuid
from decimal import Decimal
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from apps.core.models import StudentProfile
from apps.academics.models import AcademicYear, ClassLevel


class FeeCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True, help_text=_('e.g., Tuition Fee, Laboratory Fee'))
    description = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = _('Fee Category')
        verbose_name_plural = _('Fee Categories')
        ordering = ['name']

    def __str__(self):
        return self.name


class FeeStructure(models.Model):
    """
    Defines standard fee tariff per class level for an academic year.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.PROTECT, related_name='fee_structures')
    class_level = models.ForeignKey(ClassLevel, on_delete=models.PROTECT, related_name='fee_structures')
    category = models.ForeignKey(FeeCategory, on_delete=models.PROTECT, related_name='structures')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    due_date = models.DateField()

    class Meta:
        verbose_name = _('Fee Structure')
        verbose_name_plural = _('Fee Structures')
        constraints = [
            models.UniqueConstraint(
                fields=['academic_year', 'class_level', 'category'],
                name='unique_fee_structure'
            )
        ]
        ordering = ['class_level', 'category']

    def __str__(self):
        return f"{self.class_level.name} - {self.category.name}: ${self.amount} ({self.academic_year.name})"


class InvoiceStatus(models.TextChoices):
    UNPAID = 'UNPAID', _('Unpaid')
    PARTIALLY_PAID = 'PARTIALLY_PAID', _('Partially Paid')
    PAID = 'PAID', _('Paid')
    OVERDUE = 'OVERDUE', _('Overdue')


class FeeInvoice(models.Model):
    """
    Individual fee invoice issued to a student.
    Enforces ledger reconciliation: outstanding_balance = total_amount - paid_amount.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice_number = models.CharField(max_length=50, unique=True, db_index=True)
    student = models.ForeignKey(StudentProfile, on_delete=models.PROTECT, related_name='invoices')
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.PROTECT, related_name='invoices')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    due_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=InvoiceStatus.choices,
        default=InvoiceStatus.UNPAID
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Fee Invoice')
        verbose_name_plural = _('Fee Invoices')
        ordering = ['-created_at']

    @property
    def outstanding_balance(self):
        balance = self.total_amount - self.paid_amount
        return max(Decimal('0.00'), balance)

    @property
    def is_fully_paid(self):
        return self.paid_amount >= self.total_amount

    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.student.full_name} (${self.paid_amount}/${self.total_amount})"


class InvoiceItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(FeeInvoice, on_delete=models.CASCADE, related_name='items')
    fee_category = models.ForeignKey(FeeCategory, on_delete=models.PROTECT)
    description = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = _('Invoice Item')
        verbose_name_plural = _('Invoice Items')

    def __str__(self):
        return f"{self.description}: ${self.amount}"


class PaymentMethod(models.TextChoices):
    SIMULATED_CARD = 'SIMULATED_CARD', _('Debit/Credit Card (Simulated)')
    NET_BANKING = 'NET_BANKING', _('Net Banking (Simulated)')
    UPI = 'UPI', _('UPI (Simulated)')
    CASH = 'CASH', _('Cash (Desk Receipt)')


class PaymentTransaction(models.Model):
    """
    Immutable ledger entry for each fee receipt / simulated payment.
    """
    class TransactionStatus(models.TextChoices):
        SUCCESS = 'SUCCESS', _('Success')
        FAILED = 'FAILED', _('Failed')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transaction_reference = models.CharField(max_length=64, unique=True, db_index=True)
    invoice = models.ForeignKey(FeeInvoice, on_delete=models.PROTECT, related_name='payments')
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(
        max_length=25,
        choices=PaymentMethod.choices,
        default=PaymentMethod.SIMULATED_CARD
    )
    payment_date = models.DateTimeField(auto_now_add=True, db_index=True)
    payer_name = models.CharField(max_length=150)
    status = models.CharField(
        max_length=15,
        choices=TransactionStatus.choices,
        default=TransactionStatus.SUCCESS
    )
    notes = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = _('Payment Transaction')
        verbose_name_plural = _('Payment Transactions')
        ordering = ['-payment_date']
        constraints = [
            models.CheckConstraint(
                condition=Q(amount_paid__gt=0),
                name='payment_amount_positive'
            )
        ]

    def __str__(self):
        return f"{self.transaction_reference} - ${self.amount_paid} ({self.get_status_display()})"
