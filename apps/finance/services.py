import uuid
from decimal import Decimal
from django.db import transaction
from django.db.models import Sum, Count, Q
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .models import FeeInvoice, InvoiceItem, PaymentTransaction, FeeStructure, InvoiceStatus, PaymentMethod
from apps.academics.models import StudentEnrollment
from apps.core.services import log_audit_event


def process_fee_payment(invoice_id, amount_paid, payment_method, payer_name, notes="", actor=None, request=None):
    """
    Transaction-safe fee payment processing engine (Acceptance Criteria 5).
    Uses select_for_update() row locking to prevent race conditions.
    Guarantees strict reconciliation: Outstanding = Total - Paid.
    """
    amt = Decimal(str(amount_paid))
    if amt <= Decimal('0.00'):
        raise ValidationError(_("Payment amount must be strictly greater than zero."))

    with transaction.atomic():
        try:
            invoice = FeeInvoice.objects.select_for_update().get(id=invoice_id)
        except FeeInvoice.DoesNotExist:
            raise ValidationError(_("Invoice not found."))

        current_balance = invoice.total_amount - invoice.paid_amount
        if amt > current_balance:
            raise ValidationError(
                _("Payment amount ($%(amt)s) exceeds the remaining outstanding balance of $%(bal)s.") % {
                    'amt': amt, 'bal': current_balance
                }
            )

        # Generate unique transaction reference
        txn_ref = f"TXN-{uuid.uuid4().hex[:12].upper()}"

        payment = PaymentTransaction.objects.create(
            transaction_reference=txn_ref,
            invoice=invoice,
            amount_paid=amt,
            payment_method=payment_method,
            payer_name=payer_name,
            notes=notes,
            status=PaymentTransaction.TransactionStatus.SUCCESS
        )

        # Update ledger amounts
        invoice.paid_amount += amt
        if invoice.paid_amount >= invoice.total_amount:
            invoice.status = InvoiceStatus.PAID
        else:
            invoice.status = InvoiceStatus.PARTIALLY_PAID

        invoice.save(update_fields=['paid_amount', 'status', 'updated_at'])

        log_audit_event(
            actor=actor or (request.user if request and request.user.is_authenticated else None),
            action='PROCESS_FEE_PAYMENT',
            entity_type='FeeInvoice',
            entity_id=invoice.id,
            description=f"Received payment of ${amt} via {payment_method}. Txn: {txn_ref}. New status: {invoice.status}",
            changes={'paid_amount': str(invoice.paid_amount), 'status': invoice.status, 'amount_paid': str(amt)},
            request=request
        )

    return payment


def generate_invoices_for_class_section(class_section, due_date, actor=None, request=None):
    """
    Generates invoices for all enrolled students in a class section based on configured FeeStructures.
    """
    academic_year = class_section.academic_year
    class_level = class_section.class_level

    fee_structures = FeeStructure.objects.filter(
        academic_year=academic_year,
        class_level=class_level
    )

    if not fee_structures.exists():
        raise ValidationError(
            _("No fee structure defined for %(level)s in academic year %(year)s.") % {
                'level': class_level.name, 'year': academic_year.name
            }
        )

    total_fee_amount = sum(fs.amount for fs in fee_structures)
    enrollments = StudentEnrollment.objects.filter(class_section=class_section, is_active=True).select_related('student')

    created_invoices = []

    with transaction.atomic():
        for enrollment in enrollments:
            student = enrollment.student
            # Skip if invoice already exists for this student and academic year
            if FeeInvoice.objects.filter(student=student, academic_year=academic_year).exists():
                continue

            inv_number = f"INV-{academic_year.name.replace('-', '')}-{student.admission_number}"
            invoice = FeeInvoice.objects.create(
                invoice_number=inv_number,
                student=student,
                academic_year=academic_year,
                total_amount=total_fee_amount,
                paid_amount=Decimal('0.00'),
                due_date=due_date,
                status=InvoiceStatus.UNPAID
            )

            for fs in fee_structures:
                InvoiceItem.objects.create(
                    invoice=invoice,
                    fee_category=fs.category,
                    description=f"{fs.category.name} - {class_level.name}",
                    amount=fs.amount
                )

            created_invoices.append(invoice)

        if created_invoices:
            log_audit_event(
                actor=actor,
                action='GENERATE_CLASS_INVOICES',
                entity_type='ClassSection',
                entity_id=class_section.id,
                description=f"Generated {len(created_invoices)} invoices for {class_section.display_name}. Total billing: ${total_fee_amount * len(created_invoices)}",
                request=request
            )

    return created_invoices


def get_financial_reconciliation_summary(academic_year=None):
    """
    Computes global reconciliation metrics: Total Invoiced, Total Collected, Total Outstanding.
    """
    qs = FeeInvoice.objects.all()
    if academic_year:
        qs = qs.filter(academic_year=academic_year)

    agg = qs.aggregate(
        total_invoiced=Sum('total_amount'),
        total_collected=Sum('paid_amount'),
        invoice_count=Count('id'),
        paid_count=Count('id', filter=Q(status=InvoiceStatus.PAID)),
        partially_paid_count=Count('id', filter=Q(status=InvoiceStatus.PARTIALLY_PAID)),
        unpaid_count=Count('id', filter=Q(status=InvoiceStatus.UNPAID))
    )

    total_inv = agg['total_invoiced'] or Decimal('0.00')
    total_col = agg['total_collected'] or Decimal('0.00')
    total_outstanding = max(Decimal('0.00'), total_inv - total_col)
    recovery_rate = round((total_col / total_inv) * 100, 2) if total_inv > 0 else Decimal('0.00')

    return {
        'total_invoiced': total_inv,
        'total_collected': total_col,
        'total_outstanding': total_outstanding,
        'recovery_rate': recovery_rate,
        'invoice_count': agg['invoice_count'],
        'paid_count': agg['paid_count'],
        'partially_paid_count': agg['partially_paid_count'],
        'unpaid_count': agg['unpaid_count']
    }
