-- ==============================================================================
-- Verism AI  –  Local PostgreSQL Initialization Schema
-- Drop-in replacement for hosted Supabase.
-- Automatically executed upon container initialization via /docker-entrypoint-initdb.d
-- ==============================================================================

-- ==============================================================================
-- SECTION 1: PostgreSQL Cryptographic & UUID Extensions
-- ==============================================================================

-- Enable standard OSSP UUID generator functions (e.g. uuid_generate_v4())
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable cryptographic primitives (e.g. gen_random_uuid(), digest(), crypt())
CREATE EXTENSION IF NOT EXISTS "pgcrypto";


-- ==============================================================================
-- SECTION 2: Instructors Table
-- Stores educator administrative accounts, credentials, and console preferences
-- ==============================================================================

-- Create the instructors table if it does not already exist
CREATE TABLE IF NOT EXISTS public.instructors (
    -- Unique identifier for the instructor (e.g. 'usr_1a2b3c4d' or UUID string)
    id VARCHAR(64) PRIMARY KEY,
    -- Full legal or display name of the instructor
    name VARCHAR(255) NOT NULL,
    -- Unique email address utilized for login authentication and correspondence
    email VARCHAR(255) UNIQUE NOT NULL,
    -- Departmental role or academic designation (e.g. 'Instructor · Computer Science')
    role VARCHAR(128) DEFAULT 'Instructor · Computer Science',
    -- Bcrypt cryptographic hash of the instructor's login password
    hashed_password VARCHAR(255) NOT NULL,
    -- JSONB document storing configurable console preferences (thresholds, UI flags)
    preferences JSONB DEFAULT '{"show_similarity_context": true, "require_teacher_notes_on_overrides": false, "include_ai_content_indicator": true}'::jsonb,
    -- UTC timestamp recording when this instructor account was initially created
    created_at TIMESTAMPTZ DEFAULT NOW(),
    -- UTC timestamp recording when this instructor account was last updated
    updated_at TIMESTAMPTZ DEFAULT NOW()
);


-- ==============================================================================
-- SECTION 3: Users Table
-- Local authentication entity for JWT session issuance (replaces auth.users)
-- ==============================================================================

-- Create the users table if it does not already exist
CREATE TABLE IF NOT EXISTS public.users (
    -- Primary key string identifier matching the corresponding instructor record
    id VARCHAR(64) PRIMARY KEY,
    -- User's full display name
    name VARCHAR(255) NOT NULL,
    -- Unique email address required for user credentials verification
    email VARCHAR(255) UNIQUE NOT NULL,
    -- Functional role assigned to the user within the evaluation console
    role VARCHAR(128) DEFAULT 'Instructor · Computer Science',
    -- Secure bcrypt hash of the user's password for identity verification
    hashed_password VARCHAR(255) NOT NULL,
    -- Generic JSONB dictionary for extensible user settings and client states
    preferences JSONB DEFAULT '{}'::jsonb,
    -- Timestamp when the user account was provisioned in the database
    created_at TIMESTAMPTZ DEFAULT NOW(),
    -- Timestamp when the user record attributes were last modified
    updated_at TIMESTAMPTZ DEFAULT NOW()
);


-- ==============================================================================
-- SECTION 4: User Sessions Table
-- Stores issued JWT tokens and tracks token revocation and expiration
-- ==============================================================================

-- Create the user sessions table if it does not already exist
CREATE TABLE IF NOT EXISTS public.user_sessions (
    -- Alphanumeric primary key identifying this specific authenticated session
    id VARCHAR(64) PRIMARY KEY,
    -- Foreign key linking the session to the authenticated user account (cascades on delete)
    user_id VARCHAR(64) NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    -- Raw or hashed Bearer JWT token issued to the client
    token TEXT NOT NULL,
    -- Absolute expiration timestamp after which this session is invalid
    expires_at TIMESTAMPTZ NOT NULL,
    -- UTC timestamp when this session was granted to the client
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Optimize session lookups by user ID when verifying or terminating user sessions
CREATE INDEX IF NOT EXISTS idx_user_sessions_user ON public.user_sessions(user_id);


-- ==============================================================================
-- SECTION 5: Classrooms Table
-- Represents courses, cohorts, and instructional sections managed by instructors
-- ==============================================================================

-- Create the classrooms table if it does not already exist
CREATE TABLE IF NOT EXISTS public.classrooms (
    -- Unique identifier generated automatically for each classroom (UUID string or custom ID)
    id VARCHAR(64) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    -- Foreign key to the instructor managing this classroom (cleared if instructor removed)
    instructor_id VARCHAR(64) REFERENCES public.instructors(id) ON DELETE SET NULL,
    -- Official title of the classroom or academic course (e.g. 'Data Structures & Algorithms')
    name VARCHAR(255) NOT NULL,
    -- Academic identifier or course code (e.g. 'CS-101', 'BIO-204')
    code VARCHAR(64) NOT NULL,
    -- UTC timestamp marking the creation date of the classroom
    created_at TIMESTAMPTZ DEFAULT NOW(),
    -- UTC timestamp marking the latest modification of the classroom attributes
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index to accelerate retrieval of all classrooms belonging to a specific instructor
CREATE INDEX IF NOT EXISTS idx_classrooms_instructor ON public.classrooms(instructor_id);


-- ==============================================================================
-- SECTION 6: Students Table
-- Enrolled student roster belonging to individual classrooms
-- ==============================================================================

-- Create the students roster table if it does not already exist
CREATE TABLE IF NOT EXISTS public.students (
    -- Unique identifier generated automatically for each student enrollment record
    id VARCHAR(64) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    -- Foreign key referencing the parent classroom (cascades on classroom deletion)
    classroom_id VARCHAR(64) NOT NULL REFERENCES public.classrooms(id) ON DELETE CASCADE,
    -- Institutional roll number, matriculation ID, or student registration code
    roll_number VARCHAR(64) NOT NULL,
    -- Full legal name of the enrolled student
    full_name VARCHAR(255) NOT NULL,
    -- Optional student contact email address for grade receipts and feedback
    email VARCHAR(255),
    -- UTC timestamp when the student was enrolled in the classroom roster
    created_at TIMESTAMPTZ DEFAULT NOW(),
    -- Enforce uniqueness of student roll numbers within any individual classroom
    CONSTRAINT uq_students_classroom_roll UNIQUE (classroom_id, roll_number)
);

-- Index to optimize querying student roster members by classroom
CREATE INDEX IF NOT EXISTS idx_students_classroom ON public.students(classroom_id);

-- Composite index to speed up student identification by classroom and roll number
CREATE INDEX IF NOT EXISTS idx_students_roll ON public.students(classroom_id, roll_number);


-- ==============================================================================
-- SECTION 7: Courses Table
-- Legacy course mapping table maintained for backward compatibility
-- ==============================================================================

-- Create the legacy courses table if it does not already exist
CREATE TABLE IF NOT EXISTS public.courses (
    -- Unique string identifier for the course record
    id VARCHAR(64) PRIMARY KEY,
    -- Course name or curriculum title
    name VARCHAR(255) NOT NULL,
    -- Course catalog shorthand code (e.g. 'CS201')
    code VARCHAR(64) NOT NULL,
    -- Academic section identifier (e.g. 'A', 'B', 'Lab 01')
    section VARCHAR(32) NOT NULL DEFAULT 'A',
    -- UI accent tone utilized for visual card styling in frontend dashboard
    tone VARCHAR(32) DEFAULT 'lav',
    -- Cached count of students enrolled in this course for swift dashboard rendering
    students_count INT DEFAULT 0,
    -- Foreign key referencing the assigned instructor (cleared on instructor deletion)
    instructor_id VARCHAR(64) REFERENCES public.instructors(id) ON DELETE SET NULL,
    -- UTC timestamp when the course record was first inserted
    created_at TIMESTAMPTZ DEFAULT NOW(),
    -- UTC timestamp when course attributes were last updated
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index to accelerate querying courses by their catalog code
CREATE INDEX IF NOT EXISTS idx_courses_code ON public.courses(code);

-- Index to accelerate querying courses by their owning instructor
CREATE INDEX IF NOT EXISTS idx_courses_instructor ON public.courses(instructor_id);


-- ==============================================================================
-- SECTION 8: Rubrics Table
-- Container for grading rubrics and criteria matrices
-- ==============================================================================

-- Create the rubrics table if it does not already exist
CREATE TABLE IF NOT EXISTS public.rubrics (
    -- Unique string identifier generated automatically via random UUID
    id VARCHAR(64) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    -- Foreign key to associated classroom (cascades on classroom removal)
    classroom_id VARCHAR(64) REFERENCES public.classrooms(id) ON DELETE CASCADE,
    -- Optional legacy course string identifier association
    course_id VARCHAR(64),
    -- Descriptive title of the rubric matrix (e.g. 'Algorithm Efficiency Rubric')
    title TEXT,
    -- Secondary or shorthand name for the rubric
    name VARCHAR(255),
    -- Calculated aggregate total marks available across all rubric criteria
    total_marks NUMERIC(6,2) DEFAULT 0.0,
    -- Maximum potential numerical score for this evaluation scale
    total_max_score NUMERIC(6,2) DEFAULT 0.0,
    -- UTC timestamp marking when this rubric was created
    created_at TIMESTAMPTZ DEFAULT NOW(),
    -- UTC timestamp marking when this rubric configuration was modified
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index to optimize rubric lookups scoped to a classroom
CREATE INDEX IF NOT EXISTS idx_rubrics_classroom ON public.rubrics(classroom_id);

-- Index to optimize rubric lookups scoped to a legacy course
CREATE INDEX IF NOT EXISTS idx_rubrics_course ON public.rubrics(course_id);


-- ==============================================================================
-- SECTION 9: Rubric Criteria Table
-- Granular assessment criteria categories composing an evaluation rubric
-- ==============================================================================

-- Create the rubric criteria table if it does not already exist
CREATE TABLE IF NOT EXISTS public.rubric_criteria (
    -- Unique string identifier generated automatically via random UUID
    id VARCHAR(64) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    -- Foreign key referencing the parent rubric (cascades on rubric deletion)
    rubric_id VARCHAR(64) NOT NULL REFERENCES public.rubrics(id) ON DELETE CASCADE,
    -- Category name of the evaluation criterion (e.g. 'Code Correctness')
    criterion_name TEXT,
    -- Display name for the criterion category
    name VARCHAR(255),
    -- Comprehensive qualitative description of the assessment objective
    description TEXT,
    -- Percentage weight allocated to this criterion (default 25.0%)
    weight NUMERIC(5,2) DEFAULT 25.0,
    -- Maximum raw points achievable for this specific criterion
    max_points NUMERIC(6,2) DEFAULT 4.0,
    -- Maximum numerical score scaled for this criterion category
    max_score NUMERIC(5,2) DEFAULT 4.0,
    -- Sequential sort order index for displaying criteria in the UI matrix
    order_index INT DEFAULT 0,
    -- JSONB array storing multi-tiered performance levels (e.g. Exemplary, Proficient, Developing)
    levels JSONB DEFAULT '[]'::jsonb,
    -- UTC timestamp when this criterion row was created
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index to accelerate retrieval of all criteria rows for a given rubric
CREATE INDEX IF NOT EXISTS idx_rubric_criteria_rubric ON public.rubric_criteria(rubric_id);


-- ==============================================================================
-- SECTION 10: Assignments Table
-- Academic assignments containing reference exemplars and evaluation settings
-- ==============================================================================

-- Create the assignments table if it does not already exist
CREATE TABLE IF NOT EXISTS public.assignments (
    -- Unique identifier for the assignment (e.g. 'assign_a1b2c3d4')
    id VARCHAR(64) PRIMARY KEY,
    -- Foreign key linking the assignment to its parent course (cascades on delete)
    course_id VARCHAR(64) NOT NULL REFERENCES public.courses(id) ON DELETE CASCADE,
    -- Title or prompt header of the assignment (e.g. 'Lab 3: Binary Search Tree')
    title VARCHAR(255) NOT NULL,
    -- Detailed instructions and student prompt text for the assignment
    description TEXT,
    -- Due date and submission cut-off timestamp
    due_date TIMESTAMPTZ,
    -- Maximum cumulative point value attainable on this assignment
    max_score NUMERIC(5,2) DEFAULT 100.0,
    -- Foreign key referencing the evaluation rubric used to grade submissions
    rubric_id VARCHAR(64) REFERENCES public.rubrics(id) ON DELETE SET NULL,
    -- Official reference exemplar solution text used by AI for grounding and benchmarking
    reference_assignment_text TEXT,
    -- UTC timestamp recording when the assignment was configured
    created_at TIMESTAMPTZ DEFAULT NOW(),
    -- UTC timestamp recording when assignment attributes were last modified
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index to optimize querying assignments by course ID
CREATE INDEX IF NOT EXISTS idx_assignments_course ON public.assignments(course_id);


-- ==============================================================================
-- SECTION 11: Submissions Table
-- Student work submissions with FERPA/GDPR AES-256 encrypted PII fields
-- ==============================================================================

-- Create the submissions table if it does not already exist
CREATE TABLE IF NOT EXISTS public.submissions (
    -- Unique alphanumeric identifier for the submission
    id VARCHAR(64) PRIMARY KEY,
    -- Foreign key to associated classroom (cascades on classroom deletion)
    classroom_id VARCHAR(64) REFERENCES public.classrooms(id) ON DELETE CASCADE,
    -- Foreign key to associated assignment (cascades on assignment deletion)
    assignment_id VARCHAR(64) NOT NULL REFERENCES public.assignments(id) ON DELETE CASCADE,
    -- Foreign key to enrolled student (retained with NULL if student record removed)
    student_id VARCHAR(64) REFERENCES public.students(id) ON DELETE SET NULL,
    -- Student full name encrypted using AES-256 for FERPA/GDPR compliance
    student_name_encrypted TEXT,
    -- Student roll number encrypted using AES-256 for student privacy protection
    student_roll_encrypted TEXT,
    -- Student email address encrypted using AES-256 to prevent PII exposure
    student_email_encrypted TEXT,
    -- Original filename of the uploaded student submission document
    file_name VARCHAR(255) NOT NULL,
    -- Local filesystem storage path pointing to the archived submission file
    file_path VARCHAR(512),
    -- Relative or absolute URL used by the frontend to download or preview the file
    file_url TEXT,
    -- File MIME or extension category (e.g. 'pdf', 'docx', 'py', 'java')
    file_type VARCHAR(64) DEFAULT 'pdf',
    -- Raw text extracted from the document via PDF parser or text extractor
    extracted_text TEXT,
    -- Normalized text content utilized for semantic embedding vectorization
    file_content TEXT,
    -- Shorthand content alias for document body processing
    content TEXT,
    -- Peer-to-peer plagiarism similarity percentage score (0.0 to 100.0)
    similarity_score NUMERIC(5,2) DEFAULT 0.0,
    -- Probability percentage that the document was generated by AI (0.0 to 100.0)
    ai_content_probability NUMERIC(5,2) DEFAULT 0.0,
    -- External web and public source plagiarism match percentage
    web_plagiarism_score NUMERIC(5,2) DEFAULT 0.0,
    -- JSONB array containing matched external web URLs, snippets, and match percentages
    web_sources JSONB DEFAULT '[]'::jsonb,
    -- Pipeline processing status (e.g. 'queued', 'evaluating', 'completed', 'flagged', 'approved')
    status VARCHAR(32) DEFAULT 'queued',
    -- UTC timestamp when the student submission was uploaded
    created_at TIMESTAMPTZ DEFAULT NOW(),
    -- UTC timestamp when the submission record was last evaluated or modified
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index to optimize querying submissions by classroom
CREATE INDEX IF NOT EXISTS idx_submissions_classroom ON public.submissions(classroom_id);

-- Index to optimize querying submissions by assignment
CREATE INDEX IF NOT EXISTS idx_submissions_assignment ON public.submissions(assignment_id);

-- Index to optimize querying submissions by enrolled student
CREATE INDEX IF NOT EXISTS idx_submissions_student ON public.submissions(student_id);

-- Index to optimize filtering submissions by evaluation pipeline status
CREATE INDEX IF NOT EXISTS idx_submissions_status ON public.submissions(status);


-- ==============================================================================
-- SECTION 12: Draft Grades Table
-- AI-generated grading evaluations pending educator review and approval
-- ==============================================================================

-- Create the draft grades table if it does not already exist
CREATE TABLE IF NOT EXISTS public.draft_grades (
    -- Unique identifier for the draft grade record
    id VARCHAR(64) PRIMARY KEY,
    -- Foreign key to parent submission (unique constraint: 1 grade per submission, cascades on delete)
    submission_id VARCHAR(64) UNIQUE NOT NULL REFERENCES public.submissions(id) ON DELETE CASCADE,
    -- AI model initial recommended score before teacher review
    suggested_score NUMERIC(5,2) DEFAULT 0.0,
    -- Aggregate total calculated points across all criteria
    total_score NUMERIC(6,2),
    -- Maximum possible point threshold for this grading evaluation
    max_score NUMERIC(6,2) DEFAULT 100.0,
    -- Final grade awarded after teacher review and stamp approval
    final_score NUMERIC(5,2),
    -- JSONB array storing scores, weights, and rationales for each rubric criterion
    criteria_scores JSONB DEFAULT '[]'::jsonb,
    -- JSONB array storing detailed criterion breakdowns and level descriptors
    criteria_breakdown JSONB DEFAULT '[]'::jsonb,
    -- JSONB document compiling similarity, AI probability, and plagiarism flags
    plagiarism_report JSONB DEFAULT '{}'::jsonb,
    -- Formative feedback and strengths/weaknesses commentary generated by Gemini
    ai_feedback TEXT,
    -- Customized notes, feedback, and corrections provided by the teacher
    teacher_feedback TEXT,
    -- Consolidated final feedback returned to the student
    feedback TEXT,
    -- Approval status of the grade (e.g. 'draft', 'pending_review', 'approved')
    status VARCHAR(32) DEFAULT 'draft',
    -- UTC timestamp when the teacher formally approved and stamped the grade
    approved_at TIMESTAMPTZ,
    -- Foreign key referencing the instructor who reviewed and approved the grade
    approved_by_id VARCHAR(64) REFERENCES public.instructors(id) ON DELETE SET NULL,
    -- Name and version of the Google GenAI model used (e.g. 'gemini-2.5-flash')
    ai_model VARCHAR(64) DEFAULT 'gemini-2.5-flash',
    -- UTC timestamp when the evaluation draft was initially generated
    created_at TIMESTAMPTZ DEFAULT NOW(),
    -- UTC timestamp when the draft grade was last updated or stamped
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index to optimize querying draft grades by submission ID
CREATE INDEX IF NOT EXISTS idx_draft_grades_submission ON public.draft_grades(submission_id);

-- Index to optimize filtering grades by approval status
CREATE INDEX IF NOT EXISTS idx_draft_grades_status ON public.draft_grades(status);


-- ==============================================================================
-- SECTION 13: Similarity Matches Table
-- Pairwise peer-to-peer collision matches and shared passage records
-- ==============================================================================

-- Create the similarity matches table if it does not already exist
CREATE TABLE IF NOT EXISTS public.similarity_matches (
    -- Unique identifier for the collision match record
    id VARCHAR(64) PRIMARY KEY,
    -- Foreign key to assignment in which the similarity match occurred
    assignment_id VARCHAR(64) NOT NULL REFERENCES public.assignments(id) ON DELETE CASCADE,
    -- Foreign key referencing the first student submission in the comparison pair
    submission_a_id VARCHAR(64) NOT NULL REFERENCES public.submissions(id) ON DELETE CASCADE,
    -- Foreign key referencing the second student submission in the comparison pair
    submission_b_id VARCHAR(64) NOT NULL REFERENCES public.submissions(id) ON DELETE CASCADE,
    -- Numerical similarity percentage (0.0 to 100.0) between both submissions
    similarity_score NUMERIC(5,2) NOT NULL DEFAULT 0.0,
    -- JSONB array containing identical phrases, shared verbatim spans, and code snippets
    matching_phrases JSONB DEFAULT '[]'::jsonb,
    -- Qualitative similarity severity tag (e.g. 'High similarity', 'Review suggested')
    status VARCHAR(64) DEFAULT 'High similarity',
    -- Teacher investigation notes or dismissal rationale for false positives
    teacher_note TEXT,
    -- UTC timestamp when the pairwise match was detected and logged
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index to accelerate querying similarity matches for a specific assignment
CREATE INDEX IF NOT EXISTS idx_sim_matches_assignment ON public.similarity_matches(assignment_id);

-- Composite index to accelerate collision lookups between pairs of submissions
CREATE INDEX IF NOT EXISTS idx_sim_matches_pairs ON public.similarity_matches(submission_a_id, submission_b_id);


-- ==============================================================================
-- SECTION 14: Batch Jobs Table
-- Asynchronous Celery background evaluation batch progress tracking
-- ==============================================================================

-- Create the batch jobs table if it does not already exist
CREATE TABLE IF NOT EXISTS public.batch_jobs (
    -- Unique identifier for the batch execution task (e.g. Celery task UUID)
    id VARCHAR(64) PRIMARY KEY,
    -- Foreign key to the assignment whose submissions are being batch processed
    assignment_id VARCHAR(64) NOT NULL REFERENCES public.assignments(id) ON DELETE CASCADE,
    -- Processing status of the batch job ('queued', 'processing', 'completed', 'failed')
    status VARCHAR(32) DEFAULT 'queued',
    -- Percentage progress indicator (0.0 to 100.0) for live frontend progress bars
    progress_pct NUMERIC(5,2) DEFAULT 0.0,
    -- Total count of submission files included in this batch job
    total_items INT DEFAULT 0,
    -- Count of submission files successfully evaluated so far in this batch
    processed_items INT DEFAULT 0,
    -- JSONB document for diagnostics, timing benchmarks, and worker metadata
    meta_info JSONB DEFAULT '{}'::jsonb,
    -- Detailed error trace message if batch job encountered a fatal exception
    error_message TEXT,
    -- UTC timestamp when the batch job was enqueued
    created_at TIMESTAMPTZ DEFAULT NOW(),
    -- UTC timestamp when the batch job progress or status was last updated
    updated_at TIMESTAMPTZ DEFAULT NOW()
);


-- ==============================================================================
-- SECTION 15: Audit Logs Table
-- Immutable FERPA & GDPR compliance audit trail recording all human actions
-- ==============================================================================

-- Create the audit logs table if it does not already exist
CREATE TABLE IF NOT EXISTS public.audit_logs (
    -- Unique identifier for the immutable audit event entry
    id VARCHAR(64) PRIMARY KEY,
    -- Foreign key to the instructor performing the action (NULL for automated system actions)
    actor_id VARCHAR(64) REFERENCES public.instructors(id) ON DELETE SET NULL,
    -- Human-readable name or identity of the acting user (defaults to 'System')
    actor_name VARCHAR(255) DEFAULT 'System',
    -- Action verb identifier (e.g. 'GRADE_APPROVED', 'FEEDBACK_MODIFIED', 'THRESHOLD_CHANGED')
    action VARCHAR(64) NOT NULL,
    -- Target entity type affected by the action (e.g. 'submission', 'grade', 'classroom')
    entity_type VARCHAR(64) NOT NULL,
    -- Target entity identifier affected by the action
    entity_id VARCHAR(64) NOT NULL,
    -- Comprehensive JSONB audit delta containing before/after attributes and change parameters
    details JSONB DEFAULT '{}'::jsonb,
    -- Originating client IP address for network forensic accountability
    ip_address VARCHAR(64),
    -- UTC timestamp recording the exact moment the auditable event transpired
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index to optimize querying audit logs by specific action type
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON public.audit_logs(action);

-- Index to optimize time-series queries and compliance audit reporting by date range
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON public.audit_logs(created_at);


-- ==============================================================================
-- SECTION 16: Matrix Rubrics & Criteria Tables
-- Dedicated matrix-style multi-tiered rubric evaluation definitions
-- ==============================================================================

-- Create the matrix rubrics table if it does not already exist
CREATE TABLE IF NOT EXISTS public.matrix_rubrics (
    -- Unique identifier generated automatically via random UUID
    id VARCHAR(64) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    -- Title or descriptive headline of the matrix rubric
    title VARCHAR(255) NOT NULL,
    -- Foreign key to associated course (cascades on course deletion)
    course_id VARCHAR(64) REFERENCES public.courses(id) ON DELETE CASCADE,
    -- Foreign key to instructor who authored this matrix rubric
    instructor_id VARCHAR(64) REFERENCES public.instructors(id) ON DELETE SET NULL,
    -- Total cumulative mark calculation for this matrix rubric
    total_marks NUMERIC(6,2) DEFAULT 0.0,
    -- UTC timestamp when this matrix rubric was created
    created_at TIMESTAMPTZ DEFAULT NOW(),
    -- UTC timestamp when this matrix rubric was last modified
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create the matrix rubric criteria table if it does not already exist
CREATE TABLE IF NOT EXISTS public.matrix_rubric_criteria (
    -- Unique identifier generated automatically via random UUID
    id VARCHAR(64) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    -- Foreign key referencing the parent matrix rubric (cascades on deletion)
    rubric_id VARCHAR(64) NOT NULL REFERENCES public.matrix_rubrics(id) ON DELETE CASCADE,
    -- Name of the specific assessment criterion (e.g. 'Technical Accuracy')
    name VARCHAR(255) NOT NULL,
    -- Detailed descriptive explanation of what is evaluated under this criterion
    description TEXT,
    -- Percentage weight assigned to this criterion (default 25.0%)
    weight NUMERIC(5,2) DEFAULT 25.0,
    -- Maximum score possible for this criterion category
    max_score NUMERIC(5,2) DEFAULT 4.0,
    -- JSONB array containing discrete performance tier levels (name, points, description)
    levels JSONB DEFAULT '[]'::jsonb,
    -- Display order index within the rubric criteria table
    order_index INT DEFAULT 0,
    -- UTC timestamp when this criterion row was registered
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index to optimize querying criteria belonging to a given matrix rubric
CREATE INDEX IF NOT EXISTS idx_matrix_criteria_rubric ON public.matrix_rubric_criteria(rubric_id);


-- ==============================================================================
-- SECTION 17: Local File Storage Tracking Table
-- Metadata catalog for local filesystem storage (replaces Supabase Storage buckets)
-- ==============================================================================

-- Create the local file storage tracking table if it does not already exist
CREATE TABLE IF NOT EXISTS public.file_storage (
    -- Unique identifier generated automatically via random UUID
    id VARCHAR(64) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    -- Optional assignment foreign identifier association
    assignment_id VARCHAR(64),
    -- Original filename of the uploaded asset as provided by the client
    original_name VARCHAR(512) NOT NULL,
    -- Absolute or relative filesystem storage path where the binary file resides
    storage_path VARCHAR(1024) NOT NULL,
    -- Standard MIME content type of the file (e.g. 'application/pdf', 'text/x-python')
    content_type VARCHAR(128),
    -- Size of the stored file in bytes for storage quotas and bandwidth verification
    size_bytes BIGINT DEFAULT 0,
    -- UTC timestamp when the file asset was written to disk and cataloged
    created_at TIMESTAMPTZ DEFAULT NOW()
);
