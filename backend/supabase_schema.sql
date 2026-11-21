-- ==============================================================================
-- Verism AI - Complete Supabase PostgreSQL Schema
-- Tables: Instructors, Courses, Assignments, Rubrics, Rubric Criteria,
--         Submissions (with FERPA encryption), Draft Grades, Audit Logs,
--         Similarity Matches, Batch Jobs.
-- ==============================================================================

-- 1. Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. Instructors Table
CREATE TABLE IF NOT EXISTS public.instructors (
    -- Column or clause definition: id VARCHAR(64) PRIMARY KEY
    id VARCHAR(64) PRIMARY KEY,
    -- Column or clause definition: name VARCHAR(255) NOT NULL
    name VARCHAR(255) NOT NULL,
    -- Column or clause definition: email VARCHAR(255) UNIQUE NOT NULL
    email VARCHAR(255) UNIQUE NOT NULL,
    -- Column or clause definition: role VARCHAR(128) DEFAULT 'Instructor · Computer Science'
    role VARCHAR(128) DEFAULT 'Instructor · Computer Science',
    -- Column or clause definition: hashed_password VARCHAR(255) NOT NULL
    hashed_password VARCHAR(255) NOT NULL,
    -- Column or clause definition: preferences JSONB DEFAULT '{"show_similarity_context": true, "require_
    preferences JSONB DEFAULT '{"show_similarity_context": true, "require_teacher_notes_on_overrides": false, "include_ai_content_indicator": true}'::jsonb,
    -- Column or clause definition: created_at TIMESTAMPTZ DEFAULT NOW()
    created_at TIMESTAMPTZ DEFAULT NOW(),
    -- Column or clause definition: updated_at TIMESTAMPTZ DEFAULT NOW()
    updated_at TIMESTAMPTZ DEFAULT NOW()
-- Column or clause definition: )
);

-- 3. Classrooms (Courses) Table
CREATE TABLE IF NOT EXISTS public.classrooms (
    -- Column or clause definition: id VARCHAR(64) PRIMARY KEY DEFAULT gen_random_uuid()::text
    id VARCHAR(64) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    -- Column or clause definition: instructor_id VARCHAR(64) REFERENCES public.instructors(id) ON DELETE 
    instructor_id VARCHAR(64) REFERENCES public.instructors(id) ON DELETE SET NULL,
    -- Column or clause definition: name VARCHAR(255) NOT NULL
    name VARCHAR(255) NOT NULL,
    -- Column or clause definition: code VARCHAR(64) NOT NULL
    code VARCHAR(64) NOT NULL,
    -- Column or clause definition: created_at TIMESTAMPTZ DEFAULT NOW()
    created_at TIMESTAMPTZ DEFAULT NOW(),
    -- Column or clause definition: updated_at TIMESTAMPTZ DEFAULT NOW()
    updated_at TIMESTAMPTZ DEFAULT NOW()
-- Column or clause definition: )
);
-- Create database index: CREATE INDEX IF NOT EXISTS idx_classrooms_instructor ON public.classrooms(instructor_id)
CREATE INDEX IF NOT EXISTS idx_classrooms_instructor ON public.classrooms(instructor_id);

-- 3b. Students (Roll Call List) Table
CREATE TABLE IF NOT EXISTS public.students (
    -- Column or clause definition: id VARCHAR(64) PRIMARY KEY DEFAULT gen_random_uuid()::text
    id VARCHAR(64) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    -- Column or clause definition: classroom_id VARCHAR(64) NOT NULL REFERENCES public.classrooms(id) ON 
    classroom_id VARCHAR(64) NOT NULL REFERENCES public.classrooms(id) ON DELETE CASCADE,
    -- Column or clause definition: roll_number VARCHAR(64) NOT NULL
    roll_number VARCHAR(64) NOT NULL,
    -- Column or clause definition: full_name VARCHAR(255) NOT NULL
    full_name VARCHAR(255) NOT NULL,
    -- Column or clause definition: email VARCHAR(255)
    email VARCHAR(255),
    -- Column or clause definition: created_at TIMESTAMPTZ DEFAULT NOW()
    created_at TIMESTAMPTZ DEFAULT NOW(),
    -- Define table constraint: CONSTRAINT uq_students_classroom_roll UNIQUE (classroom_id, roll_number)
    CONSTRAINT uq_students_classroom_roll UNIQUE (classroom_id, roll_number)
-- Column or clause definition: )
);
-- Create database index: CREATE INDEX IF NOT EXISTS idx_students_classroom ON public.students(classroom_id)
CREATE INDEX IF NOT EXISTS idx_students_classroom ON public.students(classroom_id);
-- Create database index: CREATE INDEX IF NOT EXISTS idx_students_roll ON public.students(classroom_id, roll_number)
CREATE INDEX IF NOT EXISTS idx_students_roll ON public.students(classroom_id, roll_number);

-- 3c. Legacy Courses Table (for backwards compatibility)
CREATE TABLE IF NOT EXISTS public.courses (
    -- Column or clause definition: id VARCHAR(64) PRIMARY KEY
    id VARCHAR(64) PRIMARY KEY,
    -- Column or clause definition: name VARCHAR(255) NOT NULL
    name VARCHAR(255) NOT NULL,
    -- Column or clause definition: code VARCHAR(64) NOT NULL
    code VARCHAR(64) NOT NULL,
    -- Column or clause definition: section VARCHAR(32) NOT NULL DEFAULT 'A'
    section VARCHAR(32) NOT NULL DEFAULT 'A',
    -- Column or clause definition: tone VARCHAR(32) DEFAULT 'lav', -- lav, blue, sage, amber
    tone VARCHAR(32) DEFAULT 'lav', -- lav, blue, sage, amber
    -- Column or clause definition: students_count INT DEFAULT 0
    students_count INT DEFAULT 0,
    -- Column or clause definition: instructor_id VARCHAR(64) REFERENCES public.instructors(id) ON DELETE 
    instructor_id VARCHAR(64) REFERENCES public.instructors(id) ON DELETE SET NULL,
    -- Column or clause definition: created_at TIMESTAMPTZ DEFAULT NOW()
    created_at TIMESTAMPTZ DEFAULT NOW(),
    -- Column or clause definition: updated_at TIMESTAMPTZ DEFAULT NOW()
    updated_at TIMESTAMPTZ DEFAULT NOW()
-- Column or clause definition: )
);
-- Create database index: CREATE INDEX IF NOT EXISTS idx_courses_code ON public.courses(code)
CREATE INDEX IF NOT EXISTS idx_courses_code ON public.courses(code);
-- Create database index: CREATE INDEX IF NOT EXISTS idx_courses_instructor ON public.courses(instructor_id)
CREATE INDEX IF NOT EXISTS idx_courses_instructor ON public.courses(instructor_id);

-- 4. Rubrics Table (Matrix Rubric format)
CREATE TABLE IF NOT EXISTS public.rubrics (
    -- Column or clause definition: id VARCHAR(64) PRIMARY KEY DEFAULT gen_random_uuid()::text
    id VARCHAR(64) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    -- Column or clause definition: classroom_id VARCHAR(64) REFERENCES public.classrooms(id) ON DELETE CA
    classroom_id VARCHAR(64) REFERENCES public.classrooms(id) ON DELETE CASCADE,
    -- Column or clause definition: course_id VARCHAR(64)
    course_id VARCHAR(64),
    -- Column or clause definition: title TEXT
    title TEXT,
    -- Column or clause definition: name VARCHAR(255)
    name VARCHAR(255),
    -- Column or clause definition: total_marks NUMERIC(6,2) DEFAULT 0.0
    total_marks NUMERIC(6,2) DEFAULT 0.0,
    -- Column or clause definition: total_max_score NUMERIC(6,2) DEFAULT 0.0
    total_max_score NUMERIC(6,2) DEFAULT 0.0,
    -- Column or clause definition: created_at TIMESTAMPTZ DEFAULT NOW()
    created_at TIMESTAMPTZ DEFAULT NOW(),
    -- Column or clause definition: updated_at TIMESTAMPTZ DEFAULT NOW()
    updated_at TIMESTAMPTZ DEFAULT NOW()
-- Column or clause definition: )
);
-- Create database index: CREATE INDEX IF NOT EXISTS idx_rubrics_classroom ON public.rubrics(classroom_id)
CREATE INDEX IF NOT EXISTS idx_rubrics_classroom ON public.rubrics(classroom_id);
-- Create database index: CREATE INDEX IF NOT EXISTS idx_rubrics_course ON public.rubrics(course_id)
CREATE INDEX IF NOT EXISTS idx_rubrics_course ON public.rubrics(course_id);

-- 4b. Rubric Criteria Table (with Tiered Levels JSONB)
CREATE TABLE IF NOT EXISTS public.rubric_criteria (
    -- Column or clause definition: id VARCHAR(64) PRIMARY KEY DEFAULT gen_random_uuid()::text
    id VARCHAR(64) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    -- Column or clause definition: rubric_id VARCHAR(64) NOT NULL REFERENCES public.rubrics(id) ON DELETE
    rubric_id VARCHAR(64) NOT NULL REFERENCES public.rubrics(id) ON DELETE CASCADE,
    -- Column or clause definition: criterion_name TEXT
    criterion_name TEXT,
    -- Column or clause definition: name VARCHAR(255)
    name VARCHAR(255),
    -- Column or clause definition: description TEXT
    description TEXT,
    -- Column or clause definition: weight NUMERIC(5,2) DEFAULT 25.0
    weight NUMERIC(5,2) DEFAULT 25.0,
    -- Column or clause definition: max_points NUMERIC(6,2) DEFAULT 4.0
    max_points NUMERIC(6,2) DEFAULT 4.0,
    -- Column or clause definition: max_score NUMERIC(5,2) DEFAULT 4.0
    max_score NUMERIC(5,2) DEFAULT 4.0,
    -- Column or clause definition: order_index INT DEFAULT 0
    order_index INT DEFAULT 0,
    -- Column or clause definition: levels JSONB DEFAULT '[]'::jsonb
    levels JSONB DEFAULT '[]'::jsonb,
    -- Column or clause definition: created_at TIMESTAMPTZ DEFAULT NOW()
    created_at TIMESTAMPTZ DEFAULT NOW()
-- Column or clause definition: )
);
-- Create database index: CREATE INDEX IF NOT EXISTS idx_rubric_criteria_rubric ON public.rubric_criteria(rubric_id)
CREATE INDEX IF NOT EXISTS idx_rubric_criteria_rubric ON public.rubric_criteria(rubric_id);

-- 5. Assignments Table
CREATE TABLE IF NOT EXISTS public.assignments (
    -- Column or clause definition: id VARCHAR(64) PRIMARY KEY
    id VARCHAR(64) PRIMARY KEY,
    -- Column or clause definition: course_id VARCHAR(64) NOT NULL REFERENCES public.courses(id) ON DELETE
    course_id VARCHAR(64) NOT NULL REFERENCES public.courses(id) ON DELETE CASCADE,
    -- Column or clause definition: title VARCHAR(255) NOT NULL
    title VARCHAR(255) NOT NULL,
    -- Column or clause definition: description TEXT
    description TEXT,
    -- Column or clause definition: due_date TIMESTAMPTZ
    due_date TIMESTAMPTZ,
    -- Column or clause definition: max_score NUMERIC(5,2) DEFAULT 100.0
    max_score NUMERIC(5,2) DEFAULT 100.0,
    -- Column or clause definition: rubric_id VARCHAR(64) REFERENCES public.rubrics(id) ON DELETE SET NULL
    rubric_id VARCHAR(64) REFERENCES public.rubrics(id) ON DELETE SET NULL,
    -- Column or clause definition: created_at TIMESTAMPTZ DEFAULT NOW()
    created_at TIMESTAMPTZ DEFAULT NOW(),
    -- Column or clause definition: updated_at TIMESTAMPTZ DEFAULT NOW()
    updated_at TIMESTAMPTZ DEFAULT NOW()
-- Column or clause definition: )
);
-- Create database index: CREATE INDEX IF NOT EXISTS idx_assignments_course ON public.assignments(course_id)
CREATE INDEX IF NOT EXISTS idx_assignments_course ON public.assignments(course_id);

-- 6. Submissions Table (FERPA/GDPR Compliant at rest)
CREATE TABLE IF NOT EXISTS public.submissions (
    -- Column or clause definition: id VARCHAR(64) PRIMARY KEY
    id VARCHAR(64) PRIMARY KEY,
    -- Column or clause definition: classroom_id VARCHAR(64) REFERENCES public.classrooms(id) ON DELETE CA
    classroom_id VARCHAR(64) REFERENCES public.classrooms(id) ON DELETE CASCADE,
    -- Column or clause definition: assignment_id VARCHAR(64) NOT NULL REFERENCES public.assignments(id) O
    assignment_id VARCHAR(64) NOT NULL REFERENCES public.assignments(id) ON DELETE CASCADE,
    -- Column or clause definition: student_id VARCHAR(64) REFERENCES public.students(id) ON DELETE SET NU
    student_id VARCHAR(64) REFERENCES public.students(id) ON DELETE SET NULL,
    -- Column or clause definition: student_name_encrypted TEXT
    student_name_encrypted TEXT,
    -- Column or clause definition: student_roll_encrypted TEXT
    student_roll_encrypted TEXT,
    -- Column or clause definition: student_email_encrypted TEXT
    student_email_encrypted TEXT,
    -- Column or clause definition: file_name VARCHAR(255) NOT NULL
    file_name VARCHAR(255) NOT NULL,
    -- Column or clause definition: file_path VARCHAR(512)
    file_path VARCHAR(512),
    -- Column or clause definition: file_url TEXT
    file_url TEXT,
    -- Column or clause definition: file_type VARCHAR(64) DEFAULT 'pdf'
    file_type VARCHAR(64) DEFAULT 'pdf',
    -- Column or clause definition: extracted_text TEXT
    extracted_text TEXT,
    -- Column or clause definition: file_content TEXT
    file_content TEXT,
    -- Column or clause definition: content TEXT
    content TEXT,
    -- Column or clause definition: similarity_score NUMERIC(5,2) DEFAULT 0.0
    similarity_score NUMERIC(5,2) DEFAULT 0.0,
    -- Column or clause definition: ai_content_probability NUMERIC(5,2) DEFAULT 0.0
    ai_content_probability NUMERIC(5,2) DEFAULT 0.0,
    -- Column or clause definition: web_plagiarism_score NUMERIC(5,2) DEFAULT 0.0
    web_plagiarism_score NUMERIC(5,2) DEFAULT 0.0,
    -- Column or clause definition: web_sources JSONB DEFAULT '[]'::jsonb
    web_sources JSONB DEFAULT '[]'::jsonb,
    -- Column or clause definition: status VARCHAR(32) DEFAULT 'queued', -- queued, evaluating, completed,
    status VARCHAR(32) DEFAULT 'queued', -- queued, evaluating, completed, unmatched, pending, flagged, graded
    -- Column or clause definition: created_at TIMESTAMPTZ DEFAULT NOW()
    created_at TIMESTAMPTZ DEFAULT NOW(),
    -- Column or clause definition: updated_at TIMESTAMPTZ DEFAULT NOW()
    updated_at TIMESTAMPTZ DEFAULT NOW()
-- Column or clause definition: )
);
-- Create database index: CREATE INDEX IF NOT EXISTS idx_submissions_classroom ON public.submissions(classroom_id)
CREATE INDEX IF NOT EXISTS idx_submissions_classroom ON public.submissions(classroom_id);
-- Create database index: CREATE INDEX IF NOT EXISTS idx_submissions_assignment ON public.submissions(assignment_id)
CREATE INDEX IF NOT EXISTS idx_submissions_assignment ON public.submissions(assignment_id);
-- Create database index: CREATE INDEX IF NOT EXISTS idx_submissions_student ON public.submissions(student_id)
CREATE INDEX IF NOT EXISTS idx_submissions_student ON public.submissions(student_id);
-- Create database index: CREATE INDEX IF NOT EXISTS idx_submissions_status ON public.submissions(status)
CREATE INDEX IF NOT EXISTS idx_submissions_status ON public.submissions(status);

-- 7. Draft Grades Table (AI suggestions wait for Teacher Stamp)
CREATE TABLE IF NOT EXISTS public.draft_grades (
    -- Column or clause definition: id VARCHAR(64) PRIMARY KEY
    id VARCHAR(64) PRIMARY KEY,
    -- Column or clause definition: submission_id VARCHAR(64) UNIQUE NOT NULL REFERENCES public.submission
    submission_id VARCHAR(64) UNIQUE NOT NULL REFERENCES public.submissions(id) ON DELETE CASCADE,
    -- Column or clause definition: suggested_score NUMERIC(5,2) DEFAULT 0.0
    suggested_score NUMERIC(5,2) DEFAULT 0.0,
    -- Column or clause definition: total_score NUMERIC(6,2)
    total_score NUMERIC(6,2),
    -- Column or clause definition: max_score NUMERIC(6,2) DEFAULT 100.0
    max_score NUMERIC(6,2) DEFAULT 100.0,
    -- Column or clause definition: final_score NUMERIC(5,2)
    final_score NUMERIC(5,2),
    -- Column or clause definition: criteria_scores JSONB DEFAULT '[]'::jsonb
    criteria_scores JSONB DEFAULT '[]'::jsonb,
    -- Column or clause definition: criteria_breakdown JSONB DEFAULT '[]'::jsonb
    criteria_breakdown JSONB DEFAULT '[]'::jsonb,
    -- Column or clause definition: plagiarism_report JSONB DEFAULT '{}'::jsonb, -- peer_to_peer_score, pu
    plagiarism_report JSONB DEFAULT '{}'::jsonb, -- peer_to_peer_score, public_source_score, ai_probability, flagged_matches
    -- Column or clause definition: ai_feedback TEXT
    ai_feedback TEXT,
    -- Column or clause definition: teacher_feedback TEXT
    teacher_feedback TEXT,
    -- Column or clause definition: feedback TEXT
    feedback TEXT,
    -- Column or clause definition: status VARCHAR(32) DEFAULT 'draft', -- draft, released, pending, flagg
    status VARCHAR(32) DEFAULT 'draft', -- draft, released, pending, flagged, approved
    -- Column or clause definition: approved_at TIMESTAMPTZ
    approved_at TIMESTAMPTZ,
    -- Column or clause definition: approved_by_id VARCHAR(64) REFERENCES public.instructors(id) ON DELETE
    approved_by_id VARCHAR(64) REFERENCES public.instructors(id) ON DELETE SET NULL,
    -- Column or clause definition: ai_model VARCHAR(64) DEFAULT 'gemini-2.5-flash'
    ai_model VARCHAR(64) DEFAULT 'gemini-2.5-flash',
    -- Column or clause definition: created_at TIMESTAMPTZ DEFAULT NOW()
    created_at TIMESTAMPTZ DEFAULT NOW(),
    -- Column or clause definition: updated_at TIMESTAMPTZ DEFAULT NOW()
    updated_at TIMESTAMPTZ DEFAULT NOW()
-- Column or clause definition: )
);
-- Create database index: CREATE INDEX IF NOT EXISTS idx_draft_grades_submission ON public.draft_grades(submission_id)
CREATE INDEX IF NOT EXISTS idx_draft_grades_submission ON public.draft_grades(submission_id);
-- Create database index: CREATE INDEX IF NOT EXISTS idx_draft_grades_status ON public.draft_grades(status)
CREATE INDEX IF NOT EXISTS idx_draft_grades_status ON public.draft_grades(status);

-- 8. Similarity Matches Table (Peer Plagiarism Analysis)
CREATE TABLE IF NOT EXISTS public.similarity_matches (
    -- Column or clause definition: id VARCHAR(64) PRIMARY KEY
    id VARCHAR(64) PRIMARY KEY,
    -- Column or clause definition: assignment_id VARCHAR(64) NOT NULL REFERENCES public.assignments(id) O
    assignment_id VARCHAR(64) NOT NULL REFERENCES public.assignments(id) ON DELETE CASCADE,
    -- Column or clause definition: submission_a_id VARCHAR(64) NOT NULL REFERENCES public.submissions(id)
    submission_a_id VARCHAR(64) NOT NULL REFERENCES public.submissions(id) ON DELETE CASCADE,
    -- Column or clause definition: submission_b_id VARCHAR(64) NOT NULL REFERENCES public.submissions(id)
    submission_b_id VARCHAR(64) NOT NULL REFERENCES public.submissions(id) ON DELETE CASCADE,
    -- Column or clause definition: similarity_score NUMERIC(5,2) NOT NULL DEFAULT 0.0
    similarity_score NUMERIC(5,2) NOT NULL DEFAULT 0.0,
    -- Column or clause definition: matching_phrases JSONB DEFAULT '[]'::jsonb
    matching_phrases JSONB DEFAULT '[]'::jsonb,
    -- Column or clause definition: status VARCHAR(64) DEFAULT 'High similarity', -- High similarity, With
    status VARCHAR(64) DEFAULT 'High similarity', -- High similarity, Within range, Confirmed concern, Dismissed
    -- Column or clause definition: teacher_note TEXT
    teacher_note TEXT,
    -- Column or clause definition: created_at TIMESTAMPTZ DEFAULT NOW()
    created_at TIMESTAMPTZ DEFAULT NOW()
-- Column or clause definition: )
);
-- Create database index: CREATE INDEX IF NOT EXISTS idx_sim_matches_assignment ON public.similarity_matches(assignment_id)
CREATE INDEX IF NOT EXISTS idx_sim_matches_assignment ON public.similarity_matches(assignment_id);
-- Create database index: CREATE INDEX IF NOT EXISTS idx_sim_matches_pairs ON public.similarity_matches(submission_a_id, submission_b_id)
CREATE INDEX IF NOT EXISTS idx_sim_matches_pairs ON public.similarity_matches(submission_a_id, submission_b_id);

-- 9. Batch Jobs Table (Async Worker Queue Tracking)
CREATE TABLE IF NOT EXISTS public.batch_jobs (
    -- Column or clause definition: id VARCHAR(64) PRIMARY KEY
    id VARCHAR(64) PRIMARY KEY,
    -- Column or clause definition: assignment_id VARCHAR(64) NOT NULL REFERENCES public.assignments(id) O
    assignment_id VARCHAR(64) NOT NULL REFERENCES public.assignments(id) ON DELETE CASCADE,
    -- Column or clause definition: status VARCHAR(32) DEFAULT 'queued', -- queued, processing, completed,
    status VARCHAR(32) DEFAULT 'queued', -- queued, processing, completed, failed
    -- Column or clause definition: progress_pct NUMERIC(5,2) DEFAULT 0.0
    progress_pct NUMERIC(5,2) DEFAULT 0.0,
    -- Column or clause definition: total_items INT DEFAULT 0
    total_items INT DEFAULT 0,
    -- Column or clause definition: processed_items INT DEFAULT 0
    processed_items INT DEFAULT 0,
    -- Column or clause definition: meta_info JSONB DEFAULT '{}'::jsonb
    meta_info JSONB DEFAULT '{}'::jsonb,
    -- Column or clause definition: error_message TEXT
    error_message TEXT,
    -- Column or clause definition: created_at TIMESTAMPTZ DEFAULT NOW()
    created_at TIMESTAMPTZ DEFAULT NOW(),
    -- Column or clause definition: updated_at TIMESTAMPTZ DEFAULT NOW()
    updated_at TIMESTAMPTZ DEFAULT NOW()
-- Column or clause definition: )
);

-- 10. Audit Logs Table (FERPA / GDPR Compliance Trail)
CREATE TABLE IF NOT EXISTS public.audit_logs (
    -- Column or clause definition: id VARCHAR(64) PRIMARY KEY
    id VARCHAR(64) PRIMARY KEY,
    -- Column or clause definition: actor_id VARCHAR(64) REFERENCES public.instructors(id) ON DELETE SET N
    actor_id VARCHAR(64) REFERENCES public.instructors(id) ON DELETE SET NULL,
    -- Column or clause definition: actor_name VARCHAR(255) DEFAULT 'System'
    actor_name VARCHAR(255) DEFAULT 'System',
    -- Column or clause definition: action VARCHAR(64) NOT NULL
    action VARCHAR(64) NOT NULL,
    -- Column or clause definition: entity_type VARCHAR(64) NOT NULL
    entity_type VARCHAR(64) NOT NULL,
    -- Column or clause definition: entity_id VARCHAR(64) NOT NULL
    entity_id VARCHAR(64) NOT NULL,
    -- Column or clause definition: details JSONB DEFAULT '{}'::jsonb
    details JSONB DEFAULT '{}'::jsonb,
    -- Column or clause definition: ip_address VARCHAR(64)
    ip_address VARCHAR(64),
    -- Column or clause definition: created_at TIMESTAMPTZ DEFAULT NOW()
    created_at TIMESTAMPTZ DEFAULT NOW()
-- Column or clause definition: )
);
-- Create database index: CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON public.audit_logs(action)
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON public.audit_logs(action);
-- Create database index: CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON public.audit_logs(created_at)
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON public.audit_logs(created_at);

-- 11. Row-Level Security (RLS) Configuration
ALTER TABLE public.instructors ENABLE ROW LEVEL SECURITY;
-- Alter table definition: ALTER TABLE public.classrooms ENABLE ROW LEVEL SECURITY
ALTER TABLE public.classrooms ENABLE ROW LEVEL SECURITY;
-- Alter table definition: ALTER TABLE public.students ENABLE ROW LEVEL SECURITY
ALTER TABLE public.students ENABLE ROW LEVEL SECURITY;
-- Alter table definition: ALTER TABLE public.courses ENABLE ROW LEVEL SECURITY
ALTER TABLE public.courses ENABLE ROW LEVEL SECURITY;
-- Alter table definition: ALTER TABLE public.assignments ENABLE ROW LEVEL SECURITY
ALTER TABLE public.assignments ENABLE ROW LEVEL SECURITY;
-- Alter table definition: ALTER TABLE public.rubrics ENABLE ROW LEVEL SECURITY
ALTER TABLE public.rubrics ENABLE ROW LEVEL SECURITY;
-- Alter table definition: ALTER TABLE public.rubric_criteria ENABLE ROW LEVEL SECURITY
ALTER TABLE public.rubric_criteria ENABLE ROW LEVEL SECURITY;
-- Alter table definition: ALTER TABLE public.submissions ENABLE ROW LEVEL SECURITY
ALTER TABLE public.submissions ENABLE ROW LEVEL SECURITY;
-- Alter table definition: ALTER TABLE public.draft_grades ENABLE ROW LEVEL SECURITY
ALTER TABLE public.draft_grades ENABLE ROW LEVEL SECURITY;
-- Alter table definition: ALTER TABLE public.similarity_matches ENABLE ROW LEVEL SECURITY
ALTER TABLE public.similarity_matches ENABLE ROW LEVEL SECURITY;
-- Alter table definition: ALTER TABLE public.batch_jobs ENABLE ROW LEVEL SECURITY
ALTER TABLE public.batch_jobs ENABLE ROW LEVEL SECURITY;
-- Alter table definition: ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;
-- Alter table definition: ALTER TABLE public.users ENABLE ROW LEVEL SECURITY
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
-- Alter table definition: ALTER TABLE public.user_sessions ENABLE ROW LEVEL SECURITY
ALTER TABLE public.user_sessions ENABLE ROW LEVEL SECURITY;

-- Allow service role / anon full access for this prototype API layer
DO $$
-- Column or clause definition: DECLARE
DECLARE
    -- Column or clause definition: tbl text
    tbl text;
    -- Column or clause definition: tbls text[] := ARRAY['classrooms', 'students', 'courses', 'instructors
    tbls text[] := ARRAY['classrooms', 'students', 'courses', 'instructors', 'submissions', 'rubrics', 'rubric_criteria', 'assignments', 'draft_grades', 'audit_logs', 'similarity_matches', 'batch_jobs', 'users', 'user_sessions'];
-- Column or clause definition: BEGIN
BEGIN
    -- Column or clause definition: FOREACH tbl IN ARRAY tbls
    FOREACH tbl IN ARRAY tbls
    -- Column or clause definition: LOOP
    LOOP
        -- Column or clause definition: IF NOT EXISTS (
        IF NOT EXISTS (
            -- Column or clause definition: SELECT 1 FROM pg_policies WHERE tablename = tbl AND policyname = 'Allo
            SELECT 1 FROM pg_policies WHERE tablename = tbl AND policyname = 'Allow all access'
        -- Column or clause definition: ) THEN
        ) THEN
            -- Column or clause definition: EXECUTE format('CREATE POLICY "Allow all access" ON public.%I FOR ALL 
            EXECUTE format('CREATE POLICY "Allow all access" ON public.%I FOR ALL USING (true) WITH CHECK (true)', tbl);
        -- Column or clause definition: END IF
        END IF;
    -- Column or clause definition: END LOOP
    END LOOP;
-- Column or clause definition: END $$
END $$;

