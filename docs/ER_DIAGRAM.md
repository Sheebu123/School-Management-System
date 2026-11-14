# Entity-Relationship (ER) Diagram & Database Architecture

This document describes the actual entity-relationship architecture of the **ALGIONS School Management System (SMS)** based on the Django models implemented in `apps/core`, `apps/academics`, `apps/attendance`, `apps/examinations`, and `apps/finance`.

---

## 1. Complete Mermaid ER Diagram

```mermaid
erDiagram
    User ||--o| TeacherProfile : "has profile"
    User ||--o| GuardianProfile : "has profile"
    User ||--o| StudentProfile : "has user account"
    User ||--o{ AuditLog : "triggers"

    GuardianProfile ||--o{ StudentProfile : "responsible for"

    AcademicYear ||--o{ ClassSection : "schedules"
    ClassLevel ||--o{ ClassSection : "classifies"
    TeacherProfile ||--o{ ClassSection : "mentors as class teacher"

    ClassSection ||--o{ StudentEnrollment : "enrolls"
    StudentProfile ||--o{ StudentEnrollment : "enrolled via"

    ClassSection ||--o{ SubjectAssignment : "offers"
    Subject ||--o{ SubjectAssignment : "taught in"
    TeacherProfile ||--o{ SubjectAssignment : "instructs"

    ClassSection ||--o{ AttendanceSession : "conducts"
    TeacherProfile ||--o{ AttendanceSession : "records"
    AttendanceSession ||--o{ AttendanceRecord : "contains"
    StudentProfile ||--o{ AttendanceRecord : "recorded for"

    AcademicYear ||--o{ Exam : "holds"
    GradingSystem ||--o{ Exam : "evaluates with"
    GradingSystem ||--o{ GradeRule : "defines thresholds"

    Exam ||--o{ ExamSubjectSchedule : "schedules"
    SubjectAssignment ||--o{ ExamSubjectSchedule : "scheduled for"
    ExamSubjectSchedule ||--o{ StudentMark : "scores"
    StudentProfile ||--o{ StudentMark : "receives"

    AcademicYear ||--o{ FeeStructure : "bills in"
    ClassLevel ||--o{ FeeStructure : "applies to"
    FeeCategory ||--o{ FeeStructure : "categorizes"

    StudentProfile ||--o{ FeeInvoice : "invoiced to"
    AcademicYear ||--o{ FeeInvoice : "incurred in"
    FeeInvoice ||--o{ InvoiceItem : "itemizes"
    FeeCategory ||--o{ InvoiceItem : "categorizes"
    FeeInvoice ||--o{ PaymentTransaction : "settled by"

    User {
        UUID id PK
        string username
        string email
        string role
        string phone_number
        boolean is_active
        boolean is_staff
        datetime date_joined
    }

    TeacherProfile {
        UUID id PK
        UUID user_id FK
        string employee_id UK
        string qualification
        string specialization
        date joining_date
        boolean is_active
    }

    GuardianProfile {
        UUID id PK
        UUID user_id FK
        string relationship
        string occupation
        string emergency_contact
        text address
    }

    StudentProfile {
        UUID id PK
        UUID user_id FK
        string admission_number UK
        string first_name
        string last_name
        date date_of_birth
        string gender
        UUID guardian_id FK
        text address
        boolean is_active
        datetime created_at
    }

    AuditLog {
        UUID id PK
        UUID actor_id FK
        string action
        string entity_type
        string entity_id
        text description
        json changes
        ip ip_address
        datetime timestamp
    }

    AcademicYear {
        UUID id PK
        string name UK
        date start_date
        date end_date
        boolean is_current
    }

    ClassLevel {
        UUID id PK
        string name UK
        int order
    }

    ClassSection {
        UUID id PK
        UUID class_level_id FK
        string section_name
        UUID academic_year_id FK
        UUID class_teacher_id FK
    }

    Subject {
        UUID id PK
        string code UK
        string name
        boolean is_elective
    }

    SubjectAssignment {
        UUID id PK
        UUID class_section_id FK
        UUID subject_id FK
        UUID teacher_id FK
    }

    StudentEnrollment {
        UUID id PK
        UUID student_id FK
        UUID class_section_id FK
        int roll_number
        date enrollment_date
        boolean is_active
    }

    AttendanceSession {
        UUID id PK
        UUID class_section_id FK
        date date
        string session_type
        UUID recorded_by_id FK
        datetime recorded_at
        text notes
    }

    AttendanceRecord {
        UUID id PK
        UUID session_id FK
        UUID student_id FK
        string status
        string remarks
    }

    GradingSystem {
        UUID id PK
        string name UK
        boolean is_active
        datetime created_at
    }

    GradeRule {
        UUID id PK
        UUID grading_system_id FK
        string grade_letter
        decimal grade_point
        decimal min_percentage
        decimal max_percentage
        string description
    }

    Exam {
        UUID id PK
        string name
        UUID academic_year_id FK
        UUID grading_system_id FK
        date start_date
        date end_date
        boolean is_published
    }

    ExamSubjectSchedule {
        UUID id PK
        UUID exam_id FK
        UUID subject_assignment_id FK
        date exam_date
        decimal max_marks
        decimal passing_marks
    }

    StudentMark {
        UUID id PK
        UUID exam_schedule_id FK
        UUID student_id FK
        decimal marks_obtained
        boolean is_absent
        string remarks
    }

    FeeCategory {
        UUID id PK
        string name UK
        text description
    }

    FeeStructure {
        UUID id PK
        UUID academic_year_id FK
        UUID class_level_id FK
        UUID category_id FK
        decimal amount
        date due_date
    }

    FeeInvoice {
        UUID id PK
        string invoice_number UK
        UUID student_id FK
        UUID academic_year_id FK
        decimal total_amount
        decimal paid_amount
        date due_date
        string status
        datetime created_at
        datetime updated_at
    }

    InvoiceItem {
        UUID id PK
        UUID invoice_id FK
        UUID fee_category_id FK
        string description
        decimal amount
    }

    PaymentTransaction {
        UUID id PK
        string transaction_reference UK
        UUID invoice_id FK
        decimal amount_paid
        string payment_method
        datetime payment_date
        string payer_name
        string status
        text notes
    }
```

---

## 2. Key Database Constraints and Integrity Rules

### 2.1 Multi-Column Unique Constraints
- `ClassSection`: `UniqueConstraint(fields=['class_level', 'section_name', 'academic_year'])` prevents creating multiple identical sections within the same academic year.
- `SubjectAssignment`: `UniqueConstraint(fields=['class_section', 'subject'])` guarantees a subject is assigned to at most one instructional assignment per section.
- `StudentEnrollment`:
  - `UniqueConstraint(fields=['class_section', 'roll_number'])` guarantees no two students in a section share the same roll number.
  - `UniqueConstraint(fields=['student', 'class_section'])` guarantees a student cannot be enrolled multiple times in the same section.
- `AttendanceSession`: `UniqueConstraint(fields=['class_section', 'date', 'session_type'])` guarantees that a section can have at most one attendance register per date and session type (Acceptance Criterion 2).
- `AttendanceRecord`: `UniqueConstraint(fields=['session', 'student'])` guarantees no duplicate attendance marks for a student within a single session.
- `ExamSubjectSchedule`: `UniqueConstraint(fields=['exam', 'subject_assignment'])` ensures a subject is scheduled only once per examination.
- `StudentMark`: `UniqueConstraint(fields=['exam_schedule', 'student'])` ensures a student cannot receive duplicate marks for the same exam subject schedule.
- `FeeStructure`: `UniqueConstraint(fields=['academic_year', 'class_level', 'category'])` ensures unique pricing per fee category and grade level per year.

### 2.2 Database Engine Check Constraints
- `GradeRule`: `CheckConstraint(condition=Q(min_percentage__lte=F('max_percentage')))` prevents inverted percentage boundaries.
- `StudentMark`: `CheckConstraint(condition=Q(marks_obtained__gte=0))` prevents negative marks.
- `PaymentTransaction`: `CheckConstraint(condition=Q(amount_paid__gt=0))` guarantees payments are strictly positive amounts.

### 2.3 Foreign Key Protection Rules
- `on_delete=models.PROTECT`: Used on critical foreign keys (`StudentProfile.guardian`, `FeeInvoice.student`, `PaymentTransaction.invoice`, `StudentMark.student`, `StudentEnrollment.student`, `SubjectAssignment.teacher`) to prevent accidental cascade deletion of financial and academic records.
