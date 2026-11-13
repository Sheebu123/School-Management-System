# ALGIONS School Management System (SMS)

**Organization:** ALGIONS AI LABS PRIVATE LIMITED  
**Candidate:** Sheebu Tiwari  
**Registration Number:** 12310860  
**Role:** Senior Full-Stack Software Architect & Technical Lead  
**Tech Stack:** Python 3.14+, Django 6+, Bootstrap 5, Vanilla JavaScript, Neon PostgreSQL, Django REST Framework, drf-spectacular (OpenAPI 3.0), Render.

---

## 1. Executive Summary & Architecture

The **ALGIONS School Management System** is a production-minded, modular multi-role web application designed for comprehensive school administration across **Admin**, **Teacher**, and **Guardian/Student** personas.

### Architectural Highlights
- **Domain Service Layer:** Business rules (grading computations, attendance validation, fee reconciliation, audit logging) are isolated in dedicated `services.py` modules within each domain app, decoupled from view logic.
- **Database Integrity First:** Multi-column unique constraints (`UniqueConstraint`), foreign keys (`PROTECT` on critical financial and academic records), and atomic transactions (`transaction.atomic()` + `select_for_update()`) enforce consistency at the database engine level.
- **Defense-in-Depth Security:** Insecure Direct Object References (IDOR) are eliminated by strictly scoping all querysets by authenticated user profiles (`StudentProfile.objects.filter(guardian=request.user.guardian_profile)`).
- **Dual Interface:** Full server-rendered UI (Django Templates + Bootstrap 5 + Vanilla JS) alongside a fully-featured REST API with interactive OpenAPI 3.0 documentation (`drf-spectacular` Swagger UI).

---

## 2. Six Required Business Modules

1. **Academic Administration (`apps/academics`):** Academic years, grade levels, sections, subjects, faculty subject assignments, and student enrollments.
2. **Attendance Management (`apps/attendance`):** Daily roll call registers, session types (Full Day, Morning, Afternoon), duplicate attendance guard, student and class attendance summaries.
3. **Examination and Results (`apps/examinations`):** Exam scheduling, marks entry, configurable dynamic grading rules (`GradeRule`), automatic GPA calculation, and printable student report cards.
4. **Fee Management (`apps/finance`):** Fee structures, class invoicing, simulated payments, transaction ledger, and automatic balance reconciliation.
5. **Role-Based Access Control (`apps/core`):** Unified authentication routing users to dedicated role workspaces (`AdminRequiredMixin`, `TeacherRequiredMixin`, `GuardianRequiredMixin`).
6. **Reporting and Audit (`apps/core`):** Real-time KPI dashboards, attendance tracking, financial recovery stats, and immutable operation audit trails (`AuditLog`).

---

## 3. Five Critical Acceptance Criteria Verification

| # | Acceptance Criteria | Engineering Implementation | Automated Test |
|---|---|---|---|
| **1** | **Teacher Class Isolation** | Teachers can access only their assigned classes. Queries are filtered strictly through active `SubjectAssignment` and `class_teacher` relations. Unassigned access raises `PermissionDenied` (403). | `tests/test_ac1_teacher_class_access.py` |
| **2** | **Duplicate Attendance Guard** | Database-level `UniqueConstraint(fields=['class_section', 'date', 'session_type'])` on `AttendanceSession` and `UniqueConstraint(fields=['session', 'student'])` on `AttendanceRecord`. Duplicate submissions are rejected with `ValidationError` or safely updated when explicit update mode is chosen. | `tests/test_ac2_duplicate_attendance.py` |
| **3** | **Configurable Grading Rules** | Exact evaluation of dynamic `GradeRule` thresholds (`min_percentage` to `max_percentage`), computing letter grades (`A+`, `A`, `B`, `C`, `D`, `F`), grade points, GPAs, and pass/fail status. | `tests/test_ac3_grading_engine.py` |
| **4** | **Guardian Ward Data Isolation** | Anti-IDOR security: Guardians can access only information belonging to their linked wards (`StudentProfile.objects.filter(guardian=user.guardian_profile)`). Direct URL manipulation targeting other students results in 403/404. | `tests/test_ac4_guardian_data_isolation.py` |
| **5** | **Fee Reconciliation & Concurrency** | Concurrency-safe simulated payments using `select_for_update()` inside `transaction.atomic()`. Validates positive payments, rejects overpayments, and guarantees: $\text{Outstanding Balance} = \text{Total Invoiced} - \text{Total Paid}$. | `tests/test_ac5_fee_reconciliation.py` |

---

## 4. Quick Start & Local Setup

### 4.1 Prerequisites
- Python 3.10+ (Tested on Python 3.14.6)
- Git

### 4.2 Installation
```bash
# Clone or navigate to the project directory
cd "c:\Users\sheeb\Desktop\ALGIONS Project SMS"

# Create and activate virtual environment
python -m venv .venv
# On Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Apply database migrations
python manage.py migrate

# Seed synthetic demo data
python manage.py seed_demo_data

# Run development server
python manage.py runserver
```

Open your browser at `http://127.0.0.1:8000/`.

---

## 5. Synthetic Evaluation Accounts

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

## 6. Running Automated Tests

Execute the comprehensive 25-test suite:
```bash
pytest -v
```

All 25 tests validate the core domain logic, 5 critical acceptance criteria, REST APIs, and portal redirects.

---

## 7. REST API & OpenAPI Documentation

- **Interactive Swagger UI:** `http://127.0.0.1:8000/api/v1/schema/swagger-ui/`
- **ReDoc Documentation:** `http://127.0.0.1:8000/api/v1/schema/redoc/`
- **Raw OpenAPI 3.0 Schema:** `http://127.0.0.1:8000/api/v1/schema/`

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

## 8. Deployment to Render & Neon PostgreSQL

### 8.1 Render Configuration (`render.yaml`)
The project includes a ready-to-deploy `render.yaml` and `build.sh` script:
```yaml
services:
  - type: web
    name: algions-sms
    runtime: python
    buildCommand: "./build.sh"
    startCommand: "gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 3"
    envVars:
      - key: SECRET_KEY
        generateValue: true
      - key: DEBUG
        value: "False"
      - key: ALLOWED_HOSTS
        value: ".onrender.com"
      - key: DATABASE_URL
        sync: false
```

### 8.2 Neon PostgreSQL
To connect to Neon serverless PostgreSQL, simply provide your Neon pooled connection string in the `DATABASE_URL` environment variable:
```env
DATABASE_URL=postgresql://<user>:<password>@<neon-pooler-host>/<dbname>?sslmode=require
```
Django will automatically configure connection pooling and SSL mode via `dj-database-url`.
