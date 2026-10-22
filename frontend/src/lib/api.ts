/**
 * Verism AI API Client.
 * Connects the TanStack Start frontend to the FastAPI + PostgreSQL + Supabase backend.
 */

function resolveApiBaseUrl(): string {
  const envUrl = (import.meta.env as any)["VITE_API_BASE_URL"];
  if (envUrl && typeof envUrl === "string" && envUrl.trim().length > 0) {
    const trimmed = envUrl.trim().replace(/\/+$/, "");
    if (trimmed.endsWith("/api/v1")) {
      return trimmed;
    }
    if (trimmed.endsWith("/api")) {
      return `${trimmed}/v1`;
    }
    return `${trimmed}/api/v1`;
  }
  return "http://localhost:8000/api/v1";
}

const API_BASE_URL = resolveApiBaseUrl();

export interface UserProfile {
  id: string;
  name: string;
  email: string;
  role: string;
  preferences?: Record<string, any>;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: UserProfile;
}

export interface Course {
  id: string;
  name: string;
  code: string;
  section: string;
  tone: string;
  students_count: number;
  assignments_count?: number;
  reviews_count?: number;
  flags_count?: number;
}

export interface Assignment {
  id: string;
  course_id: string;
  title: string;
  description?: string;
  due_date?: string;
  max_score: number;
  rubric_id?: string;
  reference_assignment_text?: string;
  created_at: string;
}

export interface Classroom {
  id: string;
  name: string;
  code: string;
  instructor_id?: string;
  students_count: number;
  created_at?: string;
}

export interface Student {
  id: string;
  classroom_id: string;
  roll_number: string;
  full_name: string;
  email?: string;
  created_at?: string;
}

export interface StudentUploadCSVResponse {
  total_inserted: number;
  total_skipped: number;
  skipped: Array<{ row: any; roll_number: string; full_name: string; reason: string }>;
  inserted: any[];
}

export interface RubricLevel {
  level_name: string;
  points: number;
  description: string;
}

export interface RubricCriterion {
  id?: string;
  criterion_name?: string;
  name: string;
  description: string;
  weight: number;
  max: number;
  max_points?: number;
  score?: number;
  order_index?: number;
  levels?: RubricLevel[];
}

export interface Rubric {
  id: string;
  title?: string;
  name: string;
  classroom_id?: string;
  course_id: string;
  total_marks?: number;
  total_max_score: number;
  created_at?: string;
  criteria: RubricCriterion[];
}

export interface WebSource {
  url: string;
  title: string;
  snippet: string;
  match_pct?: number;
}

export interface SubmissionItem {
  id: string;
  assignment_id: string;
  student: string;
  roll: string;
  file_name: string;
  status: "pending" | "flagged" | "approved";
  score: number;
  similarity: number;
  aiContent: number;
  webPlagiarism?: number;
  created_at: string;
}

export interface SubmissionDetail extends SubmissionItem {
  extracted_text?: string;
  matching_phrase?: string;
  criteria_scores: Array<{
    criterion_name: string;
    score: number;
    max?: number;
    rationale?: string;
  }>;
  ai_feedback?: string;
  teacher_feedback?: string;
  webSources?: WebSource[];
  plagiarisedWords?: string[];
}

export interface BatchJobResponse {
  job_id: string;
  status: "queued" | "processing" | "completed" | "failed";
  progress_pct: number;
  total_items: number;
  processed_items: number;
  similarity_flags: number;
  ready_for_review: number;
  error_message?: string;
}

export interface SimilarityMatch {
  id: string;
  assignment_id: string;
  submission_a_id: string;
  submission_b_id: string;
  student_a_name: string;
  student_b_name: string;
  similarity_score: number;
  matching_phrases: string[];
  status: string;
  teacher_note?: string;
}

// Token helper
export function getAuthToken(): string | null {
  if (typeof window !== "undefined") {
    return localStorage.getItem("verism_token");
  }
  return null;
}

export function setAuthToken(token: string): void {
  if (typeof window !== "undefined") {
    localStorage.setItem("verism_token", token);
  }
}

export function clearAuthToken(): void {
  if (typeof window !== "undefined") {
    localStorage.removeItem("verism_token");
    localStorage.removeItem("verism_user");
  }
}

export function getCachedUser(): UserProfile | null {
  if (typeof window !== "undefined") {
    const raw = localStorage.getItem("verism_user");
    if (raw) {
      try {
        return JSON.parse(raw);
      } catch {
        return null;
      }
    }
  }
  return null;
}

export function setCachedUser(user: UserProfile): void {
  if (typeof window !== "undefined") {
    localStorage.setItem("verism_user", JSON.stringify(user));
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const token = getAuthToken();

  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };

  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorMsg = `HTTP Error ${response.status}${response.statusText ? `: ${response.statusText}` : ""}`;
    try {
      const errorJson = await response.json();
      if (errorJson.detail) {
        errorMsg = typeof errorJson.detail === "string" ? errorJson.detail : JSON.stringify(errorJson.detail);
      }
    } catch {
      if (response.status === 404) {
        errorMsg = `Endpoint not found (404) at ${url}. Verify backend URL configuration.`;
      }
    }
    throw new Error(errorMsg);
  }

  return response.json() as Promise<T>;
}

// ==========================================
// Authentication Endpoints
// ==========================================
export const api = {
  auth: {
    signUp: async (data: { name: string; email: string; password: string; role?: string }): Promise<AuthResponse> => {
      const res = await request<AuthResponse>("/auth/signup", {
        method: "POST",
        body: JSON.stringify(data),
      });
      setAuthToken(res.access_token);
      setCachedUser(res.user);
      return res;
    },
    login: async (data: { email: string; password: string }): Promise<AuthResponse> => {
      const res = await request<AuthResponse>("/auth/login", {
        method: "POST",
        body: JSON.stringify(data),
      });
      setAuthToken(res.access_token);
      setCachedUser(res.user);
      return res;
    },
    getMe: async (): Promise<UserProfile> => {
      const user = await request<UserProfile>("/auth/me");
      setCachedUser(user);
      return user;
    },
    updatePreferences: async (prefs: Record<string, any>): Promise<UserProfile> => {
      return request<UserProfile>("/auth/preferences", {
        method: "PUT",
        body: JSON.stringify(prefs),
      });
    },
    clearMockData: async (): Promise<{ message: string }> => {
      return request<{ message: string }>("/auth/clear-mock-data", {
        method: "POST",
      });
    },
  },

  // ==========================================
  // Courses
  // ==========================================
  courses: {
    list: async (search?: string): Promise<Course[]> => {
      const query = search ? `?search=${encodeURIComponent(search)}` : "";
      return request<Course[]>(`/courses${query}`);
    },
    get: async (id: string): Promise<Course> => {
      return request<Course>(`/courses/${id}`);
    },
    create: async (data: { name: string; code: string; section?: string; tone?: string; students_count?: number }): Promise<Course> => {
      return request<Course>("/courses", {
        method: "POST",
        body: JSON.stringify(data),
      });
    },
    delete: async (id: string): Promise<void> => {
      return request<void>(`/courses/${id}`, {
        method: "DELETE",
      });
    },
  },

  // ==========================================
  // Assignments & Reference Exemplars
  // ==========================================
  assignments: {
    listByCourse: async (courseId: string): Promise<Assignment[]> => {
      return request<Assignment[]>(`/courses/${courseId}/assignments`);
    },
    get: async (id: string): Promise<Assignment> => {
      return request<Assignment>(`/assignments/${id}`);
    },
    create: async (
      courseId: string,
      data: {
        title: string;
        description?: string;
        max_score?: number;
        rubric_id?: string;
        reference_assignment_text?: string;
        due_date?: string;
      }
    ): Promise<Assignment> => {
      try {
        return await request<Assignment>("/assignments", {
          method: "POST",
          body: JSON.stringify({
            course_id: courseId,
            ...data,
          }),
        });
      } catch {
        return await request<Assignment>(`/courses/${courseId}/assignments`, {
          method: "POST",
          body: JSON.stringify(data),
        });
      }
    },
    update: async (
      id: string,
      data: {
        title: string;
        description?: string;
        max_score?: number;
        rubric_id?: string;
        reference_assignment_text?: string;
      }
    ): Promise<Assignment> => {
      return request<Assignment>(`/assignments/${id}`, {
        method: "PUT",
        body: JSON.stringify(data),
      });
    },
    delete: async (id: string): Promise<void> => {
      return request<void>(`/assignments/${id}`, {
        method: "DELETE",
      });
    },
  },

  // ==========================================
  // Classrooms & Roll Call Roster
  // ==========================================
  classrooms: {
    list: async (): Promise<Classroom[]> => {
      return request<Classroom[]>("/classrooms");
    },
    get: async (id: string): Promise<Classroom> => {
      return request<Classroom>(`/classrooms/${id}`);
    },
    create: async (data: { name: string; code: string }): Promise<Classroom> => {
      return request<Classroom>("/classrooms", {
        method: "POST",
        body: JSON.stringify(data),
      });
    },
    delete: async (id: string): Promise<void> => {
      return request<void>(`/classrooms/${id}`, {
        method: "DELETE",
      });
    },
    getStudents: async (classroomId: string): Promise<Student[]> => {
      return request<Student[]>(`/classrooms/${classroomId}/students`);
    },
    enrollManual: async (
      classroomId: string,
      students: Array<{ roll_number: string; full_name: string; email?: string }>
    ): Promise<any> => {
      return request<any>(`/classrooms/${classroomId}/students/manual`, {
        method: "POST",
        body: JSON.stringify(students),
      });
    },
    uploadCSV: async (classroomId: string, file: File): Promise<StudentUploadCSVResponse> => {
      const formData = new FormData();
      formData.append("file", file);
      return request<StudentUploadCSVResponse>(`/classrooms/${classroomId}/students/upload-csv`, {
        method: "POST",
        body: formData,
      });
    },
  },

  // ==========================================
  // Matrix Rubrics
  // ==========================================
  rubrics: {
    list: async (classroomId?: string): Promise<Rubric[]> => {
      const q = classroomId ? `?classroom_id=${encodeURIComponent(classroomId)}` : "";
      return request<Rubric[]>(`/rubrics${q}`);
    },
    listByCourse: async (courseId: string): Promise<Rubric[]> => {
      return request<Rubric[]>(`/rubrics?classroom_id=${encodeURIComponent(courseId)}`);
    },
    get: async (id: string): Promise<Rubric> => {
      return request<Rubric>(`/rubrics/${id}`);
    },
    create: async (data: {
      title?: string;
      name?: string;
      classroom_id?: string;
      course_id?: string;
      total_marks?: number;
      total_max_score?: number;
      criteria: Array<{
        criterion_name?: string;
        name?: string;
        description?: string;
        weight?: number;
        max_points?: number;
        max_score?: number;
        levels?: RubricLevel[];
      }>;
    }): Promise<Rubric> => {
      return request<Rubric>("/rubrics", {
        method: "POST",
        body: JSON.stringify({
          title: data.title || data.name,
          classroom_id: data.classroom_id || data.course_id,
          total_marks: data.total_marks || data.total_max_score,
          criteria: data.criteria.map((c, i) => ({
            criterion_name: c.criterion_name || c.name || `Criterion ${i + 1}`,
            max_points: c.max_points || c.max_score || 4.0,
            order_index: i,
            levels: c.levels || [],
          })),
        }),
      });
    },
    delete: async (id: string): Promise<void> => {
      return request<void>(`/rubrics/${id}`, {
        method: "DELETE",
      });
    },
  },

  // ==========================================
  // Submissions (Upload & Manual Input)
  // ==========================================
  submissions: {
    listByAssignment: async (assignmentId: string): Promise<SubmissionItem[]> => {
      return request<SubmissionItem[]>(`/assignments/${assignmentId}/submissions`);
    },
    createManual: async (
      assignmentId: string,
      data: {
        student_name: string;
        student_roll: string;
        student_email?: string;
        extracted_text: string;
      }
    ): Promise<SubmissionItem> => {
      return request<SubmissionItem>(`/assignments/${assignmentId}/submissions`, {
        method: "POST",
        body: JSON.stringify({
          assignment_id: assignmentId,
          ...data,
        }),
      });
    },
    batchUpload: async (assignmentId: string, files: File[]): Promise<any> => {
      const formData = new FormData();
      files.forEach((f) => formData.append("files", f));
      return request<any>(`/assignments/${assignmentId}/submissions/batch-upload`, {
        method: "POST",
        body: formData,
      });
    },
    delete: async (id: string): Promise<void> => {
      return request<void>(`/submissions/${id}`, {
        method: "DELETE",
      });
    },
    clearAll: async (assignmentId: string): Promise<{ cleared: number }> => {
      return request<{ cleared: number }>(`/assignments/${assignmentId}/submissions`, {
        method: "DELETE",
      });
    },
  },

  // ==========================================
  // Batch AI Evaluation with 3-Way Plagiarism
  // ==========================================
  evaluations: {
    triggerBatch: async (
      assignmentId: string,
      data: {
        rubric_id?: string;
        similarity_threshold?: number;
        submission_ids?: string[];
        title?: string;
        reference_assignment_text?: string;
      } = {}
    ): Promise<BatchJobResponse> => {
      try {
        return await request<BatchJobResponse>(`/assignments/${assignmentId}/evaluate`, {
          method: "POST",
          body: JSON.stringify({
            assignment_id: assignmentId,
            ...data,
          }),
        });
      } catch {
        return await request<BatchJobResponse>(`/assignments/${assignmentId}/evaluate-batch`, {
          method: "POST",
          body: JSON.stringify({
            assignment_id: assignmentId,
            ...data,
          }),
        });
      }
    },
    evaluateSingle: async (submissionId: string): Promise<SubmissionDetail> => {
      return request<SubmissionDetail>(`/submissions/${submissionId}/evaluate`, {
        method: "POST",
      });
    },
    pollJobStatus: async (jobId: string): Promise<BatchJobResponse> => {
      return request<BatchJobResponse>(`/jobs/${jobId}`);
    },
    getActiveJob: async (assignmentId: string): Promise<BatchJobResponse | null> => {
      try {
        return await request<BatchJobResponse | null>(`/assignments/${assignmentId}/active-job`);
      } catch {
        return null;
      }
    },
  },

  // ==========================================
  // Review Queue & Teacher Grade Stamping
  // ==========================================
  review: {
    getQueue: async (assignmentId: string, statusFilter?: string): Promise<SubmissionItem[]> => {
      const query = statusFilter ? `?status_filter=${statusFilter}` : "";
      return request<SubmissionItem[]>(`/assignments/${assignmentId}/reviews${query}`);
    },
    getDetail: async (submissionId: string): Promise<SubmissionDetail> => {
      return request<SubmissionDetail>(`/submissions/${submissionId}/review-detail`);
    },
    stampGrade: async (
      submissionId: string,
      data: {
        status?: string;
        final_score: number;
        criteria_scores?: any[];
        teacher_feedback?: string;
        action?: string;
      }
    ): Promise<any> => {
      return request<any>(`/submissions/${submissionId}/stamp-grade`, {
        method: "PUT",
        body: JSON.stringify({
          status: data.status || "approved",
          final_score: data.final_score,
          criteria_scores: data.criteria_scores,
          teacher_feedback: data.teacher_feedback,
          action: data.action || "APPROVE",
        }),
      });
    },
    flagAction: async (
      submissionId: string,
      data: { action: string; note?: string }
    ): Promise<any> => {
      return request<any>(`/submissions/${submissionId}/flag-action`, {
        method: "POST",
        body: JSON.stringify(data),
      });
    },
  },

  // ==========================================
  // Similarity
  // ==========================================
  similarity: {
    listMatches: async (assignmentId: string): Promise<SimilarityMatch[]> => {
      const res = await request<any>(`/assignments/${assignmentId}/similarity`);
      if (Array.isArray(res)) {
        return res;
      }
      if (res && Array.isArray(res.pairs)) {
        return res.pairs.map((p: any) => ({
          id: p.pair_id || p.id,
          assignment_id: assignmentId,
          submission_a_id: p.student_a?.id || "",
          submission_b_id: p.student_b?.id || "",
          student_a_name: p.a || p.student_a?.name || "Student A",
          student_b_name: p.b || p.student_b?.name || "Student B",
          similarity_score: p.similarity || 0,
          matching_phrases: p.matching_phrases || [],
          status: p.status || "",
          teacher_note: p.teacher_note,
        }));
      }
      return [];
    },
  },

  // ==========================================
  // Gradebook
  // ==========================================
  gradebook: {
    getCourseGradebook: async (courseId: string): Promise<any> => {
      return request<any>(`/courses/${courseId}/gradebook`);
    },
  },
};
