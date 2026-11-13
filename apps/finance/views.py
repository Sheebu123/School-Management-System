from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.core.exceptions import ValidationError, PermissionDenied
from apps.core.permissions import AdminRequiredMixin, GuardianStudentAccessMixin, GuardianRequiredMixin
from apps.academics.models import ClassSection, AcademicYear
from apps.core.models import StudentProfile
from .models import FeeStructure, FeeInvoice, PaymentTransaction, PaymentMethod
from .services import (
    process_fee_payment,
    generate_invoices_for_class_section,
    get_financial_reconciliation_summary
)


class AdminFinanceDashboardView(AdminRequiredMixin, View):
    template_name = 'admin_portal/finance_dashboard.html'

    def get(self, request):
        current_year = AcademicYear.objects.filter(is_current=True).first()
        summary = get_financial_reconciliation_summary(current_year)
        structures = FeeStructure.objects.select_related('academic_year', 'class_level', 'category')
        recent_invoices = FeeInvoice.objects.select_related('student', 'academic_year').order_by('-created_at')[:25]
        sections = ClassSection.objects.select_related('class_level', 'academic_year')

        return render(request, self.template_name, {
            'summary': summary,
            'structures': structures,
            'recent_invoices': recent_invoices,
            'sections': sections,
            'current_year': current_year,
        })

    def post(self, request):
        # Trigger invoice generation for a class section
        section_id = request.POST.get('class_section_id')
        due_date_str = request.POST.get('due_date')
        section = get_object_or_404(ClassSection, id=section_id)

        try:
            invoices = generate_invoices_for_class_section(
                class_section=section,
                due_date=due_date_str,
                actor=request.user,
                request=request
            )
            messages.success(request, f"Successfully generated {len(invoices)} new fee invoices for {section.display_name}!")
        except ValidationError as e:
            messages.error(request, str(e.message if hasattr(e, 'message') else e))

        return redirect('admin-finance')


class GuardianWardFeesView(GuardianRequiredMixin, View):
    """
    Acceptance Criteria 4 & 5:
    Guardian fee management and simulated checkout.
    """
    template_name = 'guardian_portal/ward_fees.html'

    def get(self, request):
        guardian = getattr(request.user, 'guardian_profile', None)
        if not guardian:
            messages.error(request, "Guardian profile not found.")
            return redirect('login')

        wards = guardian.students.filter(is_active=True)
        invoices = FeeInvoice.objects.filter(student__in=wards).select_related('student', 'academic_year').prefetch_related('payments')

        total_due = sum(inv.outstanding_balance for inv in invoices)

        return render(request, self.template_name, {
            'wards': wards,
            'invoices': invoices,
            'total_due': total_due,
            'payment_methods': PaymentMethod.choices,
        })


class ProcessSimulatedPaymentView(GuardianRequiredMixin, View):
    """
    Acceptance Criteria 5:
    Processes simulated fee payments with strict reconciliation.
    """
    def post(self, request):
        invoice_id = request.POST.get('invoice_id')
        invoice = get_object_or_404(FeeInvoice, id=invoice_id)

        # IDOR check
        guardian = getattr(request.user, 'guardian_profile', None)
        if not (request.user.is_superuser or request.user.is_admin):
            if not guardian or invoice.student.guardian_id != guardian.id:
                raise PermissionDenied("You do not have permission to pay this invoice.")

        amount_str = request.POST.get('amount')
        payment_method = request.POST.get('payment_method', PaymentMethod.SIMULATED_CARD)
        payer_name = request.POST.get('payer_name', request.user.get_full_name())

        try:
            amount = Decimal(amount_str)
            txn = process_fee_payment(
                invoice_id=invoice.id,
                amount_paid=amount,
                payment_method=payment_method,
                payer_name=payer_name,
                actor=request.user,
                request=request
            )
            messages.success(
                request,
                f"Payment of ${amount:.2f} processed successfully! Transaction Reference: {txn.transaction_reference}"
            )
        except (ValidationError, Exception) as e:
            messages.error(request, str(e.message if hasattr(e, 'message') else e))

        return redirect('guardian-fees')
