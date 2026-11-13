import pytest
from datetime import date
from decimal import Decimal
from django.core.exceptions import ValidationError
from apps.finance.models import FeeInvoice, InvoiceStatus, PaymentMethod, PaymentTransaction
from apps.finance.services import process_fee_payment, get_financial_reconciliation_summary


@pytest.mark.django_db
class TestFeeReconciliation:
    """
    Acceptance Criteria 5:
    Fee payments, paid totals and outstanding balances reconcile correctly.
    """

    def test_fee_payment_reconciliation_lifecycle(self, db_setup):
        acad_year = db_setup['acad_year']
        student_1 = db_setup['student_1']

        # 1. Create Invoice of $1200.00
        invoice = FeeInvoice.objects.create(
            invoice_number='INV-2026-STU1001',
            student=student_1,
            academic_year=acad_year,
            total_amount=Decimal('1200.00'),
            paid_amount=Decimal('0.00'),
            due_date=date(2026, 12, 1),
            status=InvoiceStatus.UNPAID
        )

        assert invoice.total_amount == Decimal('1200.00')
        assert invoice.paid_amount == Decimal('0.00')
        assert invoice.outstanding_balance == Decimal('1200.00')
        assert invoice.status == InvoiceStatus.UNPAID
        assert not invoice.is_fully_paid

        # 2. First Partial Payment: $500.00
        txn1 = process_fee_payment(
            invoice_id=invoice.id,
            amount_paid=Decimal('500.00'),
            payment_method=PaymentMethod.SIMULATED_CARD,
            payer_name='Alice Smith'
        )
        assert txn1.status == PaymentTransaction.TransactionStatus.SUCCESS

        invoice.refresh_from_db()
        assert invoice.paid_amount == Decimal('500.00')
        assert invoice.outstanding_balance == Decimal('700.00')
        assert invoice.status == InvoiceStatus.PARTIALLY_PAID
        assert not invoice.is_fully_paid

        # 3. Second Payment to Complete Balance: $700.00
        txn2 = process_fee_payment(
            invoice_id=invoice.id,
            amount_paid=Decimal('700.00'),
            payment_method=PaymentMethod.UPI,
            payer_name='Alice Smith'
        )
        assert txn2.status == PaymentTransaction.TransactionStatus.SUCCESS

        invoice.refresh_from_db()
        assert invoice.paid_amount == Decimal('1200.00')
        assert invoice.outstanding_balance == Decimal('0.00')
        assert invoice.status == InvoiceStatus.PAID
        assert invoice.is_fully_paid

        # 4. Strict Ledger Mathematical Verification:
        # Sum of all transaction amounts MUST equal invoice.paid_amount
        total_txns = sum(t.amount_paid for t in invoice.payments.all())
        assert total_txns == invoice.paid_amount
        assert total_txns == Decimal('1200.00')
        assert invoice.payments.count() == 2

    def test_overpayment_is_strictly_rejected(self, db_setup):
        acad_year = db_setup['acad_year']
        student_1 = db_setup['student_1']

        invoice = FeeInvoice.objects.create(
            invoice_number='INV-2026-OVERPAY',
            student=student_1,
            academic_year=acad_year,
            total_amount=Decimal('500.00'),
            paid_amount=Decimal('0.00'),
            due_date=date(2026, 12, 1),
            status=InvoiceStatus.UNPAID
        )

        # Attempting to pay $600 on a $500 invoice must be rejected
        with pytest.raises(ValidationError) as exc:
            process_fee_payment(
                invoice_id=invoice.id,
                amount_paid=Decimal('600.00'),
                payment_method=PaymentMethod.SIMULATED_CARD,
                payer_name='Alice Smith'
            )
        assert "exceeds the remaining outstanding balance" in str(exc.value)

        # Assert no transaction was created and invoice remains unchanged
        invoice.refresh_from_db()
        assert invoice.paid_amount == Decimal('0.00')
        assert invoice.status == InvoiceStatus.UNPAID
        assert invoice.payments.count() == 0

    def test_zero_or_negative_payment_is_rejected(self, db_setup):
        acad_year = db_setup['acad_year']
        student_1 = db_setup['student_1']

        invoice = FeeInvoice.objects.create(
            invoice_number='INV-2026-NEG',
            student=student_1,
            academic_year=acad_year,
            total_amount=Decimal('500.00'),
            paid_amount=Decimal('0.00'),
            due_date=date(2026, 12, 1)
        )

        with pytest.raises(ValidationError):
            process_fee_payment(
                invoice_id=invoice.id,
                amount_paid=Decimal('0.00'),
                payment_method=PaymentMethod.SIMULATED_CARD,
                payer_name='Alice Smith'
            )

        with pytest.raises(ValidationError):
            process_fee_payment(
                invoice_id=invoice.id,
                amount_paid=Decimal('-50.00'),
                payment_method=PaymentMethod.SIMULATED_CARD,
                payer_name='Alice Smith'
            )

    def test_financial_reconciliation_summary_aggregation(self, db_setup):
        acad_year = db_setup['acad_year']
        student_1 = db_setup['student_1']
        student_2 = db_setup['student_2']

        # Invoice 1: $1000, Paid: $1000 (PAID)
        inv1 = FeeInvoice.objects.create(
            invoice_number='INV-R1',
            student=student_1,
            academic_year=acad_year,
            total_amount=Decimal('1000.00'),
            paid_amount=Decimal('1000.00'),
            due_date=date(2026, 12, 1),
            status=InvoiceStatus.PAID
        )

        # Invoice 2: $800, Paid: $400 (PARTIALLY_PAID)
        inv2 = FeeInvoice.objects.create(
            invoice_number='INV-R2',
            student=student_2,
            academic_year=acad_year,
            total_amount=Decimal('800.00'),
            paid_amount=Decimal('400.00'),
            due_date=date(2026, 12, 1),
            status=InvoiceStatus.PARTIALLY_PAID
        )

        summary = get_financial_reconciliation_summary(acad_year)

        # Total invoiced: 1000 + 800 = 1800
        assert summary['total_invoiced'] == Decimal('1800.00')
        # Total collected: 1000 + 400 = 1400
        assert summary['total_collected'] == Decimal('1400.00')
        # Outstanding: 1800 - 1400 = 400
        assert summary['total_outstanding'] == Decimal('400.00')
        # Recovery rate: (1400/1800)*100 = 77.78%
        assert summary['recovery_rate'] == Decimal('77.78')
        assert summary['paid_count'] == 1
        assert summary['partially_paid_count'] == 1
        assert summary['invoice_count'] == 2
