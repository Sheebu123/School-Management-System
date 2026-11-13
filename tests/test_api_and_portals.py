import pytest
from datetime import date
from decimal import Decimal
from django.urls import reverse
from rest_framework.test import APIClient
from apps.attendance.models import AttendanceStatus
from apps.examinations.models import Exam, ExamSubjectSchedule
from apps.finance.models import FeeInvoice, InvoiceStatus, PaymentMethod


@pytest.mark.django_db
class TestApiAndPortals:
    def test_openapi_schema_endpoint(self, db_setup):
        client = APIClient()
        response = client.get(reverse('api-schema'))
        assert response.status_code == 200
        assert 'openapi' in response.data or 'paths' in response.data

    def test_api_class_sections_scoped_by_teacher(self, db_setup):
        client = APIClient()
        teacher_1 = db_setup['teacher_1']
        section_10a = db_setup['section_10a']
        section_10b = db_setup['section_10b']

        client.force_authenticate(user=teacher_1.user)
        response = client.get(reverse('class-section-list'))
        assert response.status_code == 200
        section_ids = [s['id'] for s in response.data]
        # Teacher 1 should see Section 10-A, but NOT Section 10-B
        assert str(section_10a.id) in section_ids
        assert str(section_10b.id) not in section_ids

    def test_api_student_profiles_scoped_by_guardian(self, db_setup):
        client = APIClient()
        guardian_1 = db_setup['guardian_1']
        student_1 = db_setup['student_1']
        student_2 = db_setup['student_2']

        client.force_authenticate(user=guardian_1.user)
        response = client.get(reverse('student-list'))
        assert response.status_code == 200
        student_ids = [s['id'] for s in response.data]
        # Guardian 1 sees only own ward student 1
        assert str(student_1.id) in student_ids
        assert str(student_2.id) not in student_ids

    def test_api_attendance_record_submission(self, db_setup):
        client = APIClient()
        teacher_1 = db_setup['teacher_1']
        section_10a = db_setup['section_10a']
        student_1 = db_setup['student_1']

        client.force_authenticate(user=teacher_1.user)
        payload = {
            'class_section_id': str(section_10a.id),
            'date': '2026-11-20',
            'session_type': 'FULL_DAY',
            'records': [
                {'student_id': str(student_1.id), 'status': AttendanceStatus.PRESENT, 'remarks': 'On time'}
            ]
        }
        url = reverse('attendance-session-record')
        response = client.post(url, payload, format='json')
        assert response.status_code == 201
        assert response.data['records'][0]['status'] == AttendanceStatus.PRESENT

    def test_api_simulated_fee_payment_reconciliation(self, db_setup):
        client = APIClient()
        guardian_1 = db_setup['guardian_1']
        student_1 = db_setup['student_1']
        acad_year = db_setup['acad_year']

        invoice = FeeInvoice.objects.create(
            invoice_number='INV-API-TEST',
            student=student_1,
            academic_year=acad_year,
            total_amount=Decimal('500.00'),
            paid_amount=Decimal('0.00'),
            due_date=date(2026, 12, 1),
            status=InvoiceStatus.UNPAID
        )

        client.force_authenticate(user=guardian_1.user)
        url = reverse('api-process-payment')
        payload = {
            'invoice_id': str(invoice.id),
            'amount_paid': '200.00',
            'payment_method': PaymentMethod.SIMULATED_CARD,
            'payer_name': 'Alice Smith'
        }
        response = client.post(url, payload, format='json')
        assert response.status_code == 201

        invoice.refresh_from_db()
        assert invoice.paid_amount == Decimal('200.00')
        assert invoice.outstanding_balance == Decimal('300.00')
        assert invoice.status == InvoiceStatus.PARTIALLY_PAID

    def test_portal_login_redirect_flows(self, db_setup):
        from django.test import Client
        c = Client()

        # Admin login -> /admin-portal/
        c.login(username='admin_test', password='AdminPassword123!')
        resp = c.get(reverse('dashboard_redirect'))
        assert resp.status_code == 302
        assert resp.url == reverse('admin-dashboard')

        # Teacher login -> /teacher-portal/
        c.login(username='teacher_john', password='TeacherPassword123!')
        resp = c.get(reverse('dashboard_redirect'))
        assert resp.status_code == 302
        assert resp.url == reverse('teacher-dashboard')

        # Guardian login -> /guardian-portal/
        c.login(username='guardian_alice', password='GuardianPassword123!')
        resp = c.get(reverse('dashboard_redirect'))
        assert resp.status_code == 302
        assert resp.url == reverse('guardian-dashboard')
