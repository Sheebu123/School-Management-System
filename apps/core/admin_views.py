from datetime import date
from django.views.generic import TemplateView, ListView
from django.db.models import Count
from .permissions import AdminRequiredMixin
from .models import User, StudentProfile, TeacherProfile, AuditLog
from apps.academics.models import ClassSection, AcademicYear
from apps.attendance.models import AttendanceSession, AttendanceRecord, AttendanceStatus
from apps.finance.services import get_financial_reconciliation_summary


class AdminDashboardView(AdminRequiredMixin, TemplateView):
    template_name = 'admin_portal/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        current_year = AcademicYear.objects.filter(is_current=True).first()

        ctx['total_students'] = StudentProfile.objects.filter(is_active=True).count()
        ctx['total_teachers'] = TeacherProfile.objects.filter(is_active=True).count()
        ctx['total_sections'] = ClassSection.objects.count()
        ctx['current_year'] = current_year

        # Today's attendance stats
        today = date.today()
        today_sessions = AttendanceSession.objects.filter(date=today)
        ctx['today_sessions_count'] = today_sessions.count()

        records_today = AttendanceRecord.objects.filter(session__date=today)
        total_rec_today = records_today.count()
        present_today = records_today.filter(status=AttendanceStatus.PRESENT).count()
        ctx['today_attendance_pct'] = round((present_today / total_rec_today) * 100, 1) if total_rec_today > 0 else 0.0

        # Financial Reconciliation
        ctx['finance_summary'] = get_financial_reconciliation_summary(current_year)

        # Recent Audit Logs
        ctx['recent_audit_logs'] = AuditLog.objects.select_related('actor').order_by('-timestamp')[:10]

        return ctx


class AdminAuditLogsView(AdminRequiredMixin, ListView):
    model = AuditLog
    template_name = 'admin_portal/audit_logs.html'
    context_object_name = 'logs'
    paginate_by = 50

    def get_queryset(self):
        qs = AuditLog.objects.select_related('actor').order_by('-timestamp')
        action_filter = self.request.GET.get('action')
        if action_filter:
            qs = qs.filter(action__icontains=action_filter)
        entity_filter = self.request.GET.get('entity')
        if entity_filter:
            qs = qs.filter(entity_type__icontains=entity_filter)
        return qs
