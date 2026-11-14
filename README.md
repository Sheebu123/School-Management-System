# ALGIONS School Management System (SMS)

**Organization:** ALGIONS AI LABS PRIVATE LIMITED  
**Candidate:** Sheebu Tiwari  
**Role:** Full-Stack Web Development (Internship Assessment)  
**Tech Stack:** Python 3.12+, Django 6+, Bootstrap 5, Vanilla JavaScript, Neon PostgreSQL / SQLite, Django REST Framework, drf-spectacular (OpenAPI 3.0), Render.

> **Demonstration Notice:** This project is developed and demonstrated locally for assessment evaluation. While production deployment configurations (`render.yaml`, `build.sh`, and Neon PostgreSQL integration) are fully implemented and ready, the application is demonstrated locally and is not deployed to a live cloud host.

---

## 1. Project Documentation & Architecture Links

- 📊 **Entity-Relationship (ER) Diagram:** [`docs/ER_DIAGRAM.md`](docs/ER_DIAGRAM.md)
- 📝 **Comprehensive Technical Report:** [`docs/TECHNICAL_REPORT.md`](docs/TECHNICAL_REPORT.md)
- 📄 **Static OpenAPI 3.0 Specification:** [`docs/openapi.yaml`](docs/openapi.yaml)
- 📐 **Architecture Blueprint:** [`architecture_blueprint.md`](file:///C:/Users/sheeb/.gemini/antigravity/brain/62a49063-828f-4fa0-ad7c-b5b77163fa98/architecture_blueprint.md)

---

## 2. Executive Summary & Architecture

The **ALGIONS School Management System** is a production-minded, modular multi-role web application designed for comprehensive school administration across **Admin**, **Teacher**, and **Guardian/Student** personas.

### Architectural Highlights
- **Domain Service Layer:** Business rules (grading computations, attendance validation, fee reconciliation, audit logging) are isolated in dedicated `services.py` modules within each domain app, decoupled from view logic.
- **Database Integrity First:** Multi-column unique constraints (`UniqueConstraint`), foreign keys (`PROTECT` on critical financial and academic records), and atomic transactions (`transaction.atomic()` + `select_for_update()`) enforce consistency at the database engine level.
- **Defense-in-Depth Security:** Insecure Direct Object References (IDOR) are eliminated by strictly scoping all querysets by authenticated user profiles (`StudentProfile.objects.filter(guardian=request.user.guardian_profile)`).
- **Dual Interface:** Full server-rendered UI (Django Templates + Bootstrap 5 + Vanilla JS) alongside a fully-featured REST API with interactive OpenAPI 3.0 documentation (`drf-spectacular` Swagger UI).

---

## 3. Six Required Business Modules

1. **Academic Administration (`apps/academics`):** Academic years, grade levels, sections, subjects, faculty subject assignments, and student enrollments.
2. **Attendance Management (`apps/attendance`):** Daily roll call registers, session types (Full Day, Morning, Afternoon), duplicate attendance guard, student and class attendance summaries.
3. **Examination and Results (`apps/examinations`):** Exam scheduling, marks entry, configurable dynamic grading rules (`GradeRule`), automatic GPA calculation, and printable student report cards.
4. **Fee Management (`apps/finance`):** Fee structures, class invoicing, simulated payments, transaction ledger, and automatic balance reconciliation.
5. **Role-Based Access Control (`apps/core`):** Unified authentication routing users to dedicated role workspaces (`AdminRequiredMixin`, `TeacherRequiredMixin`, `GuardianRequiredMixin`).
6. **Reporting and Audit (`apps/core`):** Real-time KPI dashboards, attendance tracking, financial recovery stats, and immutable operation audit trails (`AuditLog`).

---

## 4. Five Critical Acceptance Criteria Verification

| # | Acceptance Criteria | Engineering Implementation | Automated Test |
|---|---|---|---|
| **1** | **Teacher Class Isolation** | Teachers can access only their assigned classes. Queries are filtered strictly through active `SubjectAssignment` and `class_teacher` relations. Unassigned access raises `PermissionDenied` (403). | `tests/test_ac1_teacher_class_access.py` |
| **2** | **Duplicate Attendance Guard** | Database-level `UniqueConstraint(fields=['class_section', 'date', 'session_type'])` on `AttendanceSession` and `UniqueConstraint(fields=['session', 'student'])` on `AttendanceRecord`. Duplicate submissions are rejected with `ValidationError` or safely updated when explicit update mode is chosen. | `tests/test_ac2_duplicate_attendance.py` |
| **3** | **Configurable Grading Rules** | Exact evaluation of dynamic `GradeRule` thresholds (`min_percentage` to `max_percentage`), computing letter grades (`A+`, `A`, `B`, `C`, `D`, `F`), grade points, GPAs, and pass/fail status. | `tests/test_ac3_grading_engine.py` |
| **4** | **Guardian Ward Data Isolation** | Anti-IDOR security: Guardians can access only information belonging to their linked wards (`StudentProfile.objects.filter(guardian=user.guardian_profile)`). Direct URL manipulation targeting other students results in 403/404. | `tests/test_ac4_guardian_data_isolation.py` |
| **5** | **Fee Reconciliation & Concurrency** | Concurrency-safe simulated payments using `select_for_update()` inside `transaction.atomic()`. Validates positive payments, rejects overpayments, and guarantees: $\text{Outstanding Balance} = \text{Total Invoiced} - \text{Total Paid}$. | `tests/test_ac5_fee_reconciliation.py` |

---

## 5. Quick Start & Local Setup

### 5.1 Prerequisites
- Python 3.12+
- Git

### 5.2 Installation & Local Execution
```bash
# 1. Clone the repository
git clone https://github.com/Sheebu123/School-Management-System.git
cd School-Management-System

# 2. Create and activate a virtual environment
python -m venv .venv

# On Windows (Command Prompt / PowerShell):
.venv\Scripts\activate

# On Linux / macOS:
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Apply database migrations
python manage.py migrate

# 5. Seed synthetic demo evaluation data
python manage.py seed_demo_data

# 6. Run the local development server
python manage.py runserver
```

Open your browser at `http://127.0.0.1:8000/`.

---

## 6. Synthetic Evaluation Accounts

The `seed_demo_data` command populates standard synthetic profiles for instant evaluation:

| Role | Username | Password | Notes / Scope |
|---|---|---|---|
| **Administrator** | `admin` | `AdminPass123!` | Full system access, audit logs, finance, academic setups |
| **Teacher (Math)** | `teacher.john` | `TeacherPass123!` | Assigned to **Grade 10-A Math** |
| **Teacher (Physics)** | `teacher.sarah` | `TeacherPass123!` | Assigned to **Grade 10-A & 10-B Physics** |
| **Guardian** | `guardian.alice` | `GuardianPass123!` | Linked to wards: **Bobby Smith** & **Emily Smith** (Grade 10-A) |
| **Guardian** | `guardian.bob` | `GuardianPass123!` | Linked to ward: **Charlie Brown** (Grade 10-B) |

*Tip:* On the login page (`/login/`), you can also click the demo quick-fill buttons to populate credentials automatically.

---

## 7. Running Automated Tests

Execute the comprehensive 25-test suite:
```bash
pytest -v
```

All 25 tests validate the core domain logic, 5 critical acceptance criteria, REST APIs, and portal redirects.

---

## 8. REST API & OpenAPI Documentation

- **Interactive Swagger UI:** `http://127.0.0.1:8000/api/v1/schema/swagger-ui/`
- **ReDoc Documentation:** `http://127.0.0.1:8000/api/v1/schema/redoc/`
- **Raw OpenAPI 3.0 Schema:** `http://127.0.0.1:8000/api/v1/schema/`
- **Static OpenAPI YAML:** [`docs/openapi.yaml`](docs/openapi.yaml)

### Key API Endpoints
- `GET /api/v1/classes/` — Class sections list (scoped by user role)
- `GET /api/v1/students/` — Student profiles (guardians restricted to own wards)
- `POST /api/v1/attendance/sessions/record/` — Submit attendance sheet
- `GET /api/v1/students/<id>/report-card/?exam_id=<uuid>` — Computed report card
- `POST /api/v1/exams/marks/submit/` — Enter subject examination marks
- `GET /api/v1/finance/invoices/` — Invoices (scoped to linked wards for guardians)
- `POST /api/v1/finance/pay/` — Execute simulated fee payment
- `GET /api/v1/finance/reconciliation/` — System fee reconciliation metrics (Admin only)

---

## 9. Production & Cloud Readiness (Render & Neon PostgreSQL)

The project includes production-ready deployment configurations:
- **Render Service Specification:** [`render.yaml`](render.yaml) (Gunicorn WSGI web service)
- **Deployment Build Script:** [`build.sh`](build.sh) (Automated migrations and WhiteNoise `collectstatic`)
- **Neon Serverless PostgreSQL:** Configured via `DATABASE_URL` environment variable in `config/settings.py` with automatic SSL enforcement and connection pooling.
