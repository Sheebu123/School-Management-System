from django.views.generic import TemplateView
from apps.core.permissions import GuardianRequiredMixin
from apps.attendance.services import get_student_attendance_summary
from apps.finance.models import FeeInvoice
from apps.examinations.models import Exam
from apps.examinations.services import generate_student_report_card


class GuardianDashboardView(GuardianRequiredMixin, TemplateView):
    template_name = 'guardian_portal/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        guardian = getattr(user, 'guardian_profile', None)

        wards_data = []
        if guardian:
            wards = guardian.students.filter(is_active=True).prefetch_related('enrollments__class_section')
            latest_published_exam = Exam.objects.filter(is_published=True).order_by('-start_date').first()

            for ward in wards:
                att_summary = get_student_attendance_summary(ward)
                invoices = FeeInvoice.objects.filter(student=ward)
                outstanding = sum(inv.outstanding_balance for inv in invoices)

                latest_gpa = 'N/A'
                if latest_published_exam:
                    rep = generate_student_report_card(ward, latest_published_exam)
                    if rep['has_marks']:
                        latest_gpa = f"{rep['overall_grade']} (GPA: {rep['gpa']})"

                current_enrollment = ward.enrollments.filter(is_active=True).first()
                class_name = current_enrollment.class_section.display_name if current_enrollment else 'Not Enrolled'

                wards_data.append({
                    'ward': ward,
                    'class_name': class_name,
                    'attendance_percentage': att_summary['attendance_percentage'],
                    'total_sessions': att_summary['total_sessions'],
                    'outstanding_fee': outstanding,
                    'latest_gpa': latest_gpa,
                })

        ctx['wards_data'] = wards_data
        return ctx
