from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

from apps.core.views import CustomLoginView, DashboardRedirectView, custom_logout_view
from apps.core.admin_views import AdminDashboardView, AdminAuditLogsView
from apps.core.guardian_views import GuardianDashboardView
from apps.academics.views import AdminClassesListView, AdminClassDetailView, TeacherDashboardView
from apps.attendance.views import TeacherAttendanceSheetView, SectionAttendanceHistoryView, GuardianWardAttendanceView
from apps.examinations.views import TeacherMarksEntryView, GuardianStudentReportCardView
from apps.finance.views import AdminFinanceDashboardView, GuardianWardFeesView, ProcessSimulatedPaymentView

urlpatterns = [
    # Built-in Django Admin
    path('admin/', admin.site.urls),

    # Authentication & Dashboard Routing
    path('', DashboardRedirectView.as_view(), name='index'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', custom_logout_view, name='logout'),
    path('dashboard/', DashboardRedirectView.as_view(), name='dashboard_redirect'),

    # Admin Portal Routes
    path('admin-portal/', AdminDashboardView.as_view(), name='admin-dashboard'),
    path('admin-portal/classes/', AdminClassesListView.as_view(), name='admin-classes'),
    path('admin-portal/classes/<uuid:pk>/', AdminClassDetailView.as_view(), name='admin-class-detail'),
    path('admin-portal/finance/', AdminFinanceDashboardView.as_view(), name='admin-finance'),
    path('admin-portal/audit-logs/', AdminAuditLogsView.as_view(), name='admin-audit-logs'),

    # Teacher Portal Routes
    path('teacher-portal/', TeacherDashboardView.as_view(), name='teacher-dashboard'),
    path('teacher-portal/attendance/<uuid:section_id>/', TeacherAttendanceSheetView.as_view(), name='teacher-attendance-sheet'),
    path('teacher-portal/attendance/<uuid:section_id>/history/', SectionAttendanceHistoryView.as_view(), name='teacher-attendance-history'),
    path('teacher-portal/marks/<uuid:schedule_id>/', TeacherMarksEntryView.as_view(), name='teacher-marks-entry'),

    # Guardian Portal Routes
    path('guardian-portal/', GuardianDashboardView.as_view(), name='guardian-dashboard'),
    path('guardian-portal/wards/<uuid:student_id>/attendance/', GuardianWardAttendanceView.as_view(), name='guardian-ward-attendance'),
    path('guardian-portal/wards/<uuid:student_id>/report-card/', GuardianStudentReportCardView.as_view(), name='guardian-ward-report-card'),
    path('guardian-portal/fees/', GuardianWardFeesView.as_view(), name='guardian-fees'),
    path('guardian-portal/fees/pay/', ProcessSimulatedPaymentView.as_view(), name='guardian-process-payment'),

    # Centralized REST API (drf-spectacular OpenAPI 3.0)
    path('api/v1/', include('apps.api.urls')),
    path('api/v1/schema/', SpectacularAPIView.as_view(), name='api-schema'),
    path('api/v1/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='api-schema'), name='swagger-ui'),
    path('api/v1/schema/redoc/', SpectacularRedocView.as_view(url_name='api-schema'), name='redoc'),
]
