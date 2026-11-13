from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ClassSectionViewSet,
    StudentProfileViewSet,
    AttendanceSessionViewSet,
    ExamViewSet,
    MarksSubmissionAPIView,
    StudentReportCardAPIView,
    FeeInvoiceViewSet,
    ProcessPaymentAPIView,
    FinancialReconciliationAPIView,
)

router = DefaultRouter()
router.register(r'classes', ClassSectionViewSet, basename='class-section')
router.register(r'students', StudentProfileViewSet, basename='student')
router.register(r'attendance/sessions', AttendanceSessionViewSet, basename='attendance-session')
router.register(r'exams', ExamViewSet, basename='exam')
router.register(r'finance/invoices', FeeInvoiceViewSet, basename='fee-invoice')

urlpatterns = [
    path('', include(router.urls)),
    path('exams/marks/submit/', MarksSubmissionAPIView.as_view(), name='api-marks-submit'),
    path('students/<uuid:student_id>/report-card/', StudentReportCardAPIView.as_view(), name='api-student-report-card'),
    path('finance/pay/', ProcessPaymentAPIView.as_view(), name='api-process-payment'),
    path('finance/reconciliation/', FinancialReconciliationAPIView.as_view(), name='api-finance-reconciliation'),
]
