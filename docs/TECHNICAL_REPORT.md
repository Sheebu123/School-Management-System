# Technical Report: School Management System (SMS)

**Candidate:** Sheebu Tiwari  
**Role:** Full-Stack Web Development  
**Organization:** ALGIONS AI LABS PRIVATE LIMITED  
**Assessment Target:** Production-Minded School Management System MVP  
**Demonstration Mode:** Local demonstration (not deployed to production)  

---

## 1. Project Overview & Objectives

The **ALGIONS School Management System** is a modular web application architected to support school governance across administrative, instructional, and guardian workflows.

The objective of the system is to solve the daily operational needs of an educational institution while enforcing strict data consistency, role separation, and business integrity. The solution prioritizes a functional, explainable, and secure MVP that directly addresses five critical acceptance criteria:
1. Teacher class and attendance access control.
2. Duplicate attendance prevention at database and application levels.
3. Configurable grading rules and automatic report card calculation.
4. Anti-IDOR protection for guardian ward data isolation.
5. Double-entry fee ledger reconciliation and simulated payment processing.

---

## 2. Technology Stack

- **Backend Runtime & Framework:** Python 3.12+ (tested with Python 3.14.6), Django 6.1.3
- **Database Engine:** SQLite (local development and demonstration) with zero-code toggle to Neon PostgreSQL via `dj-database-url` and `psycopg2-binary`
- **Web UI:** Django Server-Rendered Templates, Bootstrap 5.3.3 (responsive grid, utility classes, and components), Bootstrap Icons 1.11.3, Vanilla JavaScript
- **API Framework:** Django REST Framework (DRF) 3.18.3
- **OpenAPI Documentation:** `drf-spectacular` 0.30.0 (OpenAPI 3.0 specification with interactive Swagger UI and ReDoc)
- **Static Asset Delivery:** WhiteNoise 6.12.0 (`CompressedManifestStaticFilesStorage`)
- **Automated Testing:** `pytest` 9.2.0, `pytest-django` 4.14.0

---

## 3. Architecture & Database Design

### 3.1 Architecture Overview
The system follows a modular Django monolithic architecture structured into domain applications:

```
algions_sms/
├── config/               # Project settings, URL routing, WSGI/ASGI configuration
├── apps/
│   ├── core/             # Custom User model, RBAC profiles, audit logging, base views
│   ├── academics/        # Academic years, class levels, sections, subjects, enrollments
│   ├── attendance/       # Daily attendance sessions, records, roll-call registers
│   ├── examinations/     # Exam schedules, configurable grading rules, marks entry
│   ├── finance/          # Fee structures, student invoices, simulated payment ledger
│   └── api/              # Centralized DRF API routers, serializers, and OpenAPI views
├── templates/            # Server-rendered Bootstrap 5 templates
├── static/               # Custom CSS styles and Vanilla JavaScript helpers
├── tests/                # Automated pytest suite covering all business rules & criteria
└── docs/                 # ER diagram, technical report, and OpenAPI specification
```

### 3.2 Service Layer Pattern
To prevent business logic from leaking into views or overloading model methods, each domain application isolates transactional operations in a dedicated `services.py` module:
- `apps/attendance/services.py`: `record_attendance_session()`, `verify_teacher_class_access()`, `get_student_attendance_summary()`
- `apps/examinations/services.py`: `get_grade_for_percentage()`, `generate_student_report_card()`, `bulk_save_subject_marks()`
- `apps/finance/services.py`: `process_fee_payment()`, `generate_invoices_for_class_section()`, `get_financial_reconciliation_summary()`
- `apps/core/services.py`: `log_audit_event()`, `get_client_ip()`

### 3.3 Database Design & Integrity
Database entities use UUID primary keys for non-sequential IDs, multi-column unique constraints to prevent duplicates, check constraints for numerical bounds, and `models.PROTECT` on foreign keys to prevent accidental cascading deletions of academic and financial records. Full database relationships are documented in [`docs/ER_DIAGRAM.md`](ER_DIAGRAM.md).

---

## 4. Main Modules & User Roles

### 4.1 User Roles & Portals
- **Administrator (`ADMIN`):** Institutional overview dashboard, class and section roster inspection, bulk fee invoice generation, system-wide financial reconciliation metrics, and operational audit trail review.
- **Teacher (`TEACHER`):** Workspace restricted to assigned classes and subjects, daily attendance register with "Mark All" helpers, session history review, and examination marks entry.
- **Guardian (`GUARDIAN`):** Portal displaying only linked student wards, ward attendance percentage logs, term report card with grade and GPA evaluations, outstanding invoice overview, and simulated payment checkout.
- **Student (`STUDENT`):** Associated with student profiles and redirected to the guardian/student portal for viewing attendance and published report cards.

### 4.2 Core Functional Modules
1. **Academic Administration:** Manages academic years, class levels (e.g., Grade 9, Grade 10), sections (e.g., A, B), subjects, instructional assignments linking teachers to sections, and student enrollments.
2. **Attendance Management:** Records session-based attendance (`FULL_DAY`, `MORNING`, `AFTERNOON`) per section, calculates present/absent/late/excused tallies, and prevents duplicate submissions.
3. **Examination & Grading:** Supports exam definition, subject scheduling with max/passing marks, marks recording with absent handling, and dynamic grade rule calculation.
4. **Fee Management:** Supports fee categories, per-class tariff structures, invoice generation, simulated payments with transaction references, and ledger balance reconciliation.
5. **Audit Logging:** An immutable `AuditLog` records actor, action, timestamp, entity type, entity ID, description, changes payload, and client IP address for critical system operations.

---

## 5. Five Critical Acceptance Criteria & Implementation

### Acceptance Criterion 1: Teacher Class & Attendance Access Isolation
- **Rule:** Teachers must access only their assigned classes and record attendance for their authorized students only.
- **Implementation:** 
  - `TeacherClassAccessMixin` and `verify_teacher_class_access()` verify that the requesting teacher is either the class teacher or holds an active `SubjectAssignment` for that section.
  - Queries in `TeacherDashboardView`, `ClassSectionViewSet`, and `StudentProfileViewSet` strictly filter by `SubjectAssignment.objects.filter(teacher=request.user.teacher_profile)`.
  - Attempts by a teacher to access or submit attendance for an unassigned section raise an immediate `PermissionDenied` (HTTP 403).
- **Test File:** `tests/test_ac1_teacher_class_access.py` (3 tests).

### Acceptance Criterion 2: Duplicate Attendance Prevention
- **Rule:** Duplicate attendance for the same student/session/date must be rejected or safely handled.
- **Implementation:**
  - Multi-column `UniqueConstraint(fields=['class_section', 'date', 'session_type'])` on `AttendanceSession`.
  - Multi-column `UniqueConstraint(fields=['session', 'student'])` on `AttendanceRecord`.
  - Service layer `record_attendance_session()` checks for an existing session on the selected date: raises a `ValidationError` on duplicate submissions unless an explicit `update_existing=True` flag is supplied.
  - When in update mode, existing records are updated in place using `bulk_update` without creating duplicate rows or orphan sessions.
- **Test File:** `tests/test_ac2_duplicate_attendance.py` (4 tests).

### Acceptance Criterion 3: Configurable Grading Rules & Automatic Calculations
- **Rule:** Examination results are calculated accurately using configured dynamic grading rules.
- **Implementation:**
  - `GradingSystem` and `GradeRule` models store boundary percentages (`min_percentage` to `max_percentage`), letter grades (`A+` to `F`), and grade points (`10.0` to `0.0`).
  - `get_grade_for_percentage()` rounds percentages to two decimal places (`ROUND_HALF_UP`) and evaluates matching rule intervals.
  - `generate_student_report_card()` calculates total marks obtained, total maximum marks, aggregate percentage, GPA (mean of subject grade points), overall letter grade, and overall pass/fail status.
- **Test File:** `tests/test_ac3_grading_engine.py` (4 tests).

### Acceptance Criterion 4: Guardian Ward Data Isolation (Anti-IDOR)
- **Rule:** Guardians can access only information belonging to their linked student wards.
- **Implementation:**
  - `GuardianStudentAccessMixin.check_ward_access()` validates that the requested `student_id` belongs to `request.user.guardian_profile.students`.
  - ModelViewSet querysets in `StudentProfileViewSet` and `FeeInvoiceViewSet` scope queries strictly to `user.guardian_profile.students`.
  - DRF permission class `IsGuardianOfStudentObject` validates object-level access.
  - Attempting to access another guardian's student via direct URL ID or API endpoint raises `PermissionDenied` (HTTP 403) or `Http404`.
- **Test File:** `tests/test_ac4_guardian_data_isolation.py` (4 tests).

### Acceptance Criterion 5: Fee Reconciliation & Concurrency-Safe Ledger
- **Rule:** Fee payments, paid totals, and outstanding balances reconcile with 100% mathematical precision under concurrency.
- **Implementation:**
  - `process_fee_payment()` executes within `transaction.atomic()` using `select_for_update()` row-level locking on the `FeeInvoice`.
  - Enforces positive payment amount (`amount > 0`) and rejects overpayments exceeding the current balance (`amount > total_amount - paid_amount`).
  - Creates an immutable `PaymentTransaction` with a unique transaction reference (`TXN-...`).
  - Updates `paid_amount` and sets status (`PARTIALLY_PAID` or `PAID`).
  - Mathematical balance property: `outstanding_balance = total_amount - paid_amount`.
- **Test File:** `tests/test_ac5_fee_reconciliation.py` (4 tests).

---

## 6. Actual Automated Test Results

The test suite was executed against the local environment using `pytest -v`. All 25 tests passed with zero failures.

```
============================= test session starts =============================
platform win32 -- Python 3.14.6, pytest-9.2.0, pluggy-1.7.0
django: version: 6.1.3, settings: config.settings
rootdir: C:\Users\sheeb\Desktop\ALGIONS Project SMS
configfile: pytest.ini
plugins: django-4.14.0
collected 25 items

tests/test_ac1_teacher_class_access.py::TestTeacherClassAccess::test_teacher_assigned_can_record_attendance PASSED [  4%]
tests/test_ac1_teacher_class_access.py::TestTeacherClassAccess::test_teacher_unassigned_is_forbidden_from_recording_attendance PASSED [  8%]
tests/test_ac1_teacher_class_access.py::TestTeacherClassAccess::test_teacher_2_can_record_for_10b_but_rejected_for_10a PASSED [ 12%]
tests/test_ac2_duplicate_attendance.py::TestDuplicateAttendancePrevention::test_duplicate_session_submission_raises_validation_error PASSED [ 16%]
tests/test_ac2_duplicate_attendance.py::TestDuplicateAttendancePrevention::test_safe_update_of_existing_attendance_session PASSED [ 20%]
tests/test_ac2_duplicate_attendance.py::TestDuplicateAttendancePrevention::test_database_level_unique_constraint_on_student_session PASSED [ 24%]
tests/test_ac2_duplicate_attendance.py::TestDuplicateAttendancePrevention::test_database_level_unique_constraint_on_session PASSED [ 28%]
tests/test_ac3_grading_engine.py::TestGradingEngine::test_grading_rule_boundary_evaluations PASSED [ 32%]
tests/test_ac3_grading_engine.py::TestGradingEngine::test_report_card_aggregate_and_gpa_calculation PASSED [ 36%]
tests/test_ac3_grading_engine.py::TestGradingEngine::test_report_card_fails_if_any_subject_below_passing_marks PASSED [ 40%]
tests/test_ac3_grading_engine.py::TestGradingEngine::test_marks_validation_exceeding_max_marks_raises_error PASSED [ 44%]
tests/test_ac4_guardian_data_isolation.py::TestGuardianDataIsolation::test_guardian_can_access_own_ward PASSED [ 48%]
tests/test_ac4_guardian_data_isolation.py::TestGuardianDataIsolation::test_guardian_cannot_access_unlinked_student_idor PASSED [ 52%]
tests/test_ac4_guardian_data_isolation.py::TestGuardianDataIsolation::test_guardian_queryset_filtering_contains_only_linked_wards PASSED [ 56%]
tests/test_ac4_guardian_data_isolation.py::TestGuardianDataIsolation::test_drf_guardian_object_permission_enforcement PASSED [ 60%]
tests/test_ac5_fee_reconciliation.py::TestFeeReconciliation::test_fee_payment_reconciliation_lifecycle PASSED [ 64%]
tests/test_ac5_fee_reconciliation.py::TestFeeReconciliation::test_overpayment_is_strictly_rejected PASSED [ 68%]
tests/test_ac5_fee_reconciliation.py::TestFeeReconciliation::test_zero_or_negative_payment_is_rejected PASSED [ 72%]
tests/test_ac5_fee_reconciliation.py::TestFeeReconciliation::test_financial_reconciliation_summary_aggregation PASSED [ 76%]
tests/test_api_and_portals.py::TestApiAndPortals::test_openapi_schema_endpoint PASSED [ 80%]
tests/test_api_and_portals.py::TestApiAndPortals::test_api_class_sections_scoped_by_teacher PASSED [ 84%]
tests/test_api_and_portals.py::TestApiAndPortals::test_api_student_profiles_scoped_by_guardian PASSED [ 88%]
tests/test_api_and_portals.py::TestApiAndPortals::test_api_attendance_record_submission PASSED [ 92%]
tests/test_api_and_portals.py::TestApiAndPortals::test_api_simulated_fee_payment_reconciliation PASSED [ 96%]
tests/test_api_and_portals.py::TestApiAndPortals::test_portal_login_redirect_flows PASSED [100%]

============================= 25 passed in 59.72s =============================
```

Django system check output:
```
System check identified no issues (0 silenced).
```

---

## 7. Security and Data Integrity

1. **Authentication & Authorization:** Django session-based authentication for web views; basic and session authentication for API endpoints. Role verification is enforced on the server for every view and endpoint.
2. **Insecure Direct Object Reference (IDOR) Mitigation:** URL parameters containing entity IDs are never trusted blindly; queries are bounded by the authenticated user's role profile.
3. **Cross-Site Request Forgery (CSRF) Protection:** Enabled across all web forms using Django's `CsrfViewMiddleware` and `{% csrf_token %}`.
4. **Cross-Site Scripting (XSS) Prevention:** Django template auto-escaping enabled by default.
5. **SQL Injection Defense:** All database queries utilize Django ORM parameterized queries.
6. **Data Integrity & Concurrency:** Multi-column unique constraints enforce business uniqueness; `transaction.atomic()` and `select_for_update()` prevent race conditions during fee payments.
7. **Audit Trail:** Operations that create or alter attendance, marks, invoices, or payments are recorded in the `AuditLog` table.
8. **Secrets Management:** Secrets and sensitive configurations are stored in environment variables (`.env`), which is excluded from version control via `.gitignore`.

---

## 8. Known Limitations & Local Demonstration Status

- **Local Demonstration Mode:** The application is developed and demonstrated locally. While deployment configuration files (`render.yaml`, `build.sh`) are included and prepared for cloud targets (Render and Neon PostgreSQL), the live assessment submission is evaluated on a local workstation.
- **Simulated Payment Gateway:** Payment transactions are simulated internally with database ledger reconciliation; real credit card processors (Stripe, Razorpay) are intentionally omitted per the assessment constraints.
- **Email Notifications:** Configured using Django's console email backend (`django.core.mail.backends.console.EmailBackend`) for local verification without third-party SMTP dependencies.
- **Single Active Academic Year:** The system assumes a primary active academic year for current operational workflows.
