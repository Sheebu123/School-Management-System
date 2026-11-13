from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import TemplateView
from django.contrib import messages
from django.core.exceptions import ValidationError, PermissionDenied
from apps.core.permissions import TeacherRequiredMixin, GuardianRequiredMixin, GuardianStudentAccessMixin
from apps.academics.models import ClassSection, StudentEnrollment
from apps.core.models import StudentProfile
from .models import AttendanceSession, AttendanceRecord, AttendanceStatus, SessionType
from .services import record_attendance_session, verify_teacher_class_access, get_student_attendance_summary


class TeacherAttendanceSheetView(TeacherRequiredMixin, View):
    """
    Teacher classroom daily attendance register.
    Enforces Acceptance Criteria 1 & 2:
    - Teacher must be assigned to section.
    - Prevents duplicates or safely updates.
    """
    template_name = 'teacher_portal/attendance_sheet.html'

    def get_section(self, section_id):
        section = get_object_or_404(ClassSection, id=section_id)
        user = self.request.user
        if not (user.is_superuser or user.is_admin):
            teacher = getattr(user, 'teacher_profile', None)
            if not verify_teacher_class_access(teacher, section):
                raise PermissionDenied("You are not assigned to record attendance for this class section.")
        return section

    def get(self, request, section_id):
        section = self.get_section(section_id)
        selected_date_str = request.GET.get('date')
        if selected_date_str:
            try:
                selected_date = date.fromisoformat(selected_date_str)
            except ValueError:
                selected_date = date.today()
        else:
            selected_date = date.today()

        session_type = request.GET.get('session_type', SessionType.FULL_DAY)

        # Check if already recorded
        existing_session = AttendanceSession.objects.filter(
            class_section=section,
            date=selected_date,
            session_type=session_type
        ).first()

        existing_status_map = {}
        if existing_session:
            for rec in existing_session.records.all():
                existing_status_map[rec.student_id] = {
                    'status': rec.status,
                    'remarks': rec.remarks
                }

        enrollments = section.enrollments.filter(is_active=True).select_related('student').order_by('roll_number')

        roster = []
        for enr in enrollments:
            prev = existing_status_map.get(enr.student.id, {})
            roster.append({
                'enrollment': enr,
                'student': enr.student,
                'current_status': prev.get('status', AttendanceStatus.PRESENT),
                'remarks': prev.get('remarks', '')
            })

        return render(request, self.template_name, {
            'section': section,
            'selected_date': selected_date,
            'session_type': session_type,
            'existing_session': existing_session,
            'roster': roster,
            'status_choices': AttendanceStatus.choices,
        })

    def post(self, request, section_id):
        section = self.get_section(section_id)
        selected_date_str = request.POST.get('date')
        try:
            selected_date = date.fromisoformat(selected_date_str)
        except (ValueError, TypeError):
            selected_date = date.today()

        session_type = request.POST.get('session_type', SessionType.FULL_DAY)
        notes = request.POST.get('notes', '')
        update_existing = request.POST.get('update_existing') == 'true'

        teacher = getattr(request.user, 'teacher_profile', None)
        enrollments = section.enrollments.filter(is_active=True).select_related('student')

        records_data = []
        for enr in enrollments:
            st_id = str(enr.student.id)
            st_status = request.POST.get(f'status_{st_id}', AttendanceStatus.PRESENT)
            st_remarks = request.POST.get(f'remarks_{st_id}', '')
            records_data.append({
                'student': enr.student,
                'status': st_status,
                'remarks': st_remarks
            })

        try:
            record_attendance_session(
                class_section=section,
                date=selected_date,
                recorded_by=teacher,
                records_data=records_data,
                session_type=session_type,
                notes=notes,
                update_existing=update_existing,
                request=request
            )
            messages.success(request, f"Attendance for {section.display_name} on {selected_date} recorded successfully!")
            return redirect(f"{request.path}?date={selected_date.isoformat()}")
        except ValidationError as e:
            messages.error(request, str(e.message if hasattr(e, 'message') else e))
            return redirect(f"{request.path}?date={selected_date.isoformat()}")
        except PermissionDenied as e:
            messages.error(request, str(e))
            return redirect('teacher-dashboard')


class SectionAttendanceHistoryView(TeacherRequiredMixin, View):
    template_name = 'teacher_portal/attendance_history.html'

    def get(self, request, section_id):
        section = get_object_or_404(ClassSection, id=section_id)
        sessions = AttendanceSession.objects.filter(class_section=section).select_related('recorded_by__user').order_by('-date')
        return render(request, self.template_name, {
            'section': section,
            'sessions': sessions
        })


class GuardianWardAttendanceView(GuardianStudentAccessMixin, View):
    """
    Acceptance Criteria 4: Guardian view of ward attendance history and percentage.
    """
    template_name = 'guardian_portal/ward_attendance.html'

    def get(self, request, student_id):
        self.check_ward_access(student_id)
        student = get_object_or_404(StudentProfile, id=student_id)
        summary = get_student_attendance_summary(student)
        records = AttendanceRecord.objects.filter(student=student).select_related('session__class_section').order_by('-session__date')[:30]

        return render(request, self.template_name, {
            'student': student,
            'summary': summary,
            'records': records
        })
