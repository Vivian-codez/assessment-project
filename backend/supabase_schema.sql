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
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    role VARCHAR(128) DEFAULT 'Instructor · Computer Science',
    hashed_password VARCHAR(255) NOT NULL,
    preferences JSONB DEFAULT '{"show_similarity_context": true, "require_teacher_notes_on_overrides": false, "include_ai_content_indicator": true}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Courses Table
CREATE TABLE IF NOT EXISTS public.courses (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    code VARCHAR(64) NOT NULL,
    section VARCHAR(32) NOT NULL DEFAULT 'A',
    tone VARCHAR(32) DEFAULT 'lav', -- lav, blue, sage, amber
    students_count INT DEFAULT 0,
    instructor_id VARCHAR(64) REFERENCES public.instructors(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_courses_code ON public.courses(code);
CREATE INDEX IF NOT EXISTS idx_courses_instructor ON public.courses(instructor_id);

-- 4. Rubrics Table
CREATE TABLE IF NOT EXISTS public.rubrics (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    course_id VARCHAR(64) NOT NULL REFERENCES public.courses(id) ON DELETE CASCADE,
    total_max_score NUMERIC(5,2) DEFAULT 100.0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_rubrics_course ON public.rubrics(course_id);

-- 4b. Rubric Criteria Table
CREATE TABLE IF NOT EXISTS public.rubric_criteria (
    id VARCHAR(64) PRIMARY KEY,
    rubric_id VARCHAR(64) NOT NULL REFERENCES public.rubrics(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    weight NUMERIC(5,2) NOT NULL DEFAULT 25.0,
    max_score NUMERIC(5,2) NOT NULL DEFAULT 30.0,
    order_index INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_rubric_criteria_rubric ON public.rubric_criteria(rubric_id);

-- 5. Assignments Table
CREATE TABLE IF NOT EXISTS public.assignments (
    id VARCHAR(64) PRIMARY KEY,
    course_id VARCHAR(64) NOT NULL REFERENCES public.courses(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    due_date TIMESTAMPTZ,
    max_score NUMERIC(5,2) DEFAULT 100.0,
    rubric_id VARCHAR(64) REFERENCES public.rubrics(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_assignments_course ON public.assignments(course_id);

-- 6. Submissions Table (FERPA/GDPR Compliant at rest)
CREATE TABLE IF NOT EXISTS public.submissions (
    id VARCHAR(64) PRIMARY KEY,
    assignment_id VARCHAR(64) NOT NULL REFERENCES public.assignments(id) ON DELETE CASCADE,
    student_name_encrypted TEXT NOT NULL,
    student_roll_encrypted TEXT NOT NULL,
    student_email_encrypted TEXT,
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(512),
    file_type VARCHAR(64) DEFAULT 'pdf',
    extracted_text TEXT,
    similarity_score NUMERIC(5,2) DEFAULT 0.0,
    ai_content_probability NUMERIC(5,2) DEFAULT 0.0,
    status VARCHAR(32) DEFAULT 'pending', -- pending, flagged, graded, approved
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_submissions_assignment ON public.submissions(assignment_id);
CREATE INDEX IF NOT EXISTS idx_submissions_status ON public.submissions(status);

-- 7. Draft Grades Table (AI suggestions wait for Teacher Stamp)
CREATE TABLE IF NOT EXISTS public.draft_grades (
    id VARCHAR(64) PRIMARY KEY,
    submission_id VARCHAR(64) UNIQUE NOT NULL REFERENCES public.submissions(id) ON DELETE CASCADE,
    suggested_score NUMERIC(5,2) NOT NULL DEFAULT 0.0,
    final_score NUMERIC(5,2),
    criteria_scores JSONB DEFAULT '[]'::jsonb,
    ai_feedback TEXT,
    teacher_feedback TEXT,
    status VARCHAR(32) DEFAULT 'pending', -- pending, flagged, approved
    approved_at TIMESTAMPTZ,
    approved_by_id VARCHAR(64) REFERENCES public.instructors(id) ON DELETE SET NULL,
    ai_model VARCHAR(64) DEFAULT 'gemini-2.5-flash',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_draft_grades_submission ON public.draft_grades(submission_id);
CREATE INDEX IF NOT EXISTS idx_draft_grades_status ON public.draft_grades(status);

-- 8. Similarity Matches Table (Peer Plagiarism Analysis)
CREATE TABLE IF NOT EXISTS public.similarity_matches (
    id VARCHAR(64) PRIMARY KEY,
    assignment_id VARCHAR(64) NOT NULL REFERENCES public.assignments(id) ON DELETE CASCADE,
    submission_a_id VARCHAR(64) NOT NULL REFERENCES public.submissions(id) ON DELETE CASCADE,
    submission_b_id VARCHAR(64) NOT NULL REFERENCES public.submissions(id) ON DELETE CASCADE,
    similarity_score NUMERIC(5,2) NOT NULL DEFAULT 0.0,
    matching_phrases JSONB DEFAULT '[]'::jsonb,
    status VARCHAR(64) DEFAULT 'High similarity', -- High similarity, Within range, Confirmed concern, Dismissed
    teacher_note TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_sim_matches_assignment ON public.similarity_matches(assignment_id);
CREATE INDEX IF NOT EXISTS idx_sim_matches_pairs ON public.similarity_matches(submission_a_id, submission_b_id);

-- 9. Batch Jobs Table (Async Worker Queue Tracking)
CREATE TABLE IF NOT EXISTS public.batch_jobs (
    id VARCHAR(64) PRIMARY KEY,
    assignment_id VARCHAR(64) NOT NULL REFERENCES public.assignments(id) ON DELETE CASCADE,
    status VARCHAR(32) DEFAULT 'queued', -- queued, processing, completed, failed
    progress_pct NUMERIC(5,2) DEFAULT 0.0,
    total_items INT DEFAULT 0,
    processed_items INT DEFAULT 0,
    meta_info JSONB DEFAULT '{}'::jsonb,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 10. Audit Logs Table (FERPA / GDPR Compliance Trail)
CREATE TABLE IF NOT EXISTS public.audit_logs (
    id VARCHAR(64) PRIMARY KEY,
    actor_id VARCHAR(64) REFERENCES public.instructors(id) ON DELETE SET NULL,
    actor_name VARCHAR(255) DEFAULT 'System',
    action VARCHAR(64) NOT NULL,
    entity_type VARCHAR(64) NOT NULL,
    entity_id VARCHAR(64) NOT NULL,
    details JSONB DEFAULT '{}'::jsonb,
    ip_address VARCHAR(64),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON public.audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON public.audit_logs(created_at);

-- 11. Row-Level Security (RLS) Configuration
ALTER TABLE public.instructors ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.courses ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.rubrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.rubric_criteria ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.submissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.draft_grades ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.similarity_matches ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.batch_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;

-- Allow service role / anon full access for this prototype API layer
DO $$
DECLARE
    tbl text;
    tbls text[] := ARRAY['courses', 'instructors', 'submissions', 'rubrics', 'rubric_criteria', 'assignments', 'draft_grades', 'audit_logs', 'similarity_matches', 'batch_jobs'];
BEGIN
    FOREACH tbl IN ARRAY tbls
    LOOP
        IF NOT EXISTS (
            SELECT 1 FROM pg_policies WHERE tablename = tbl AND policyname = 'Allow all access'
        ) THEN
            EXECUTE format('CREATE POLICY "Allow all access" ON public.%I FOR ALL USING (true) WITH CHECK (true)', tbl);
        END IF;
    END LOOP;
END $$;
