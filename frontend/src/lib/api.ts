/**
 * Verism AI API Client.
 * Connects the TanStack Start frontend to the FastAPI + PostgreSQL + Supabase backend.
 */

function resolveApiBaseUrl(): string {
  // Declare envUrl variable
  const envUrl = (import.meta.env as any)["VITE_API_BASE_URL"];
  // Evaluate condition: if (envUrl && typeof envUrl === "string" && envUrl.trim().length > 0)
  if (envUrl && typeof envUrl === "string" && envUrl.trim().length > 0) {
    // Declare trimmed variable
    const trimmed = envUrl.trim().replace(/\/+$/, "");
    // Evaluate condition: if (trimmed.endsWith("/api/v1"))
    if (trimmed.endsWith("/api/v1")) {
      // Return value: trimmed
      return trimmed;
    }
    // Evaluate condition: if (trimmed.endsWith("/api"))
    if (trimmed.endsWith("/api")) {
      // Return value: `${trimmed}/v1`
      return `${trimmed}/v1`;
    }
    // Return value: `${trimmed}/api/v1`
    return `${trimmed}/api/v1`;
  }
  // Return value: "http://localhost:8000/api/v1"
  return "http://localhost:8000/api/v1";
}

// Declare API_BASE_URL variable
const API_BASE_URL = resolveApiBaseUrl();

// Define UserProfile interface data contract
export interface UserProfile {
  // Specify id property (string)
  id: string;
  // Specify name? property (string)
  name?: string;
  // Specify full_name? property (string)
  full_name?: string;
  // Specify email property (string)
  email: string;
  // Specify role property (string)
  role: string;
  // Specify preferences? property (Record<string, any>)
  preferences?: Record<string, any>;
}

// Define AuthResponse interface data contract
export interface AuthResponse {
  // Specify access_token property (string)
  access_token: string;
  // Specify token_type property (string)
  token_type: string;
  // Specify user property (UserProfile)
  user: UserProfile;
}

// Define Course interface data contract
export interface Course {
  // Specify id property (string)
  id: string;
  // Specify name property (string)
  name: string;
  // Specify code property (string)
  code: string;
  // Specify section property (string)
  section: string;
  // Specify tone property (string)
  tone: string;
  // Specify students_count property (number)
  students_count: number;
  // Specify assignments_count? property (number)
  assignments_count?: number;
  // Specify reviews_count? property (number)
  reviews_count?: number;
  // Specify flags_count? property (number)
  flags_count?: number;
}

// Define Assignment interface data contract
export interface Assignment {
  // Specify id property (string)
  id: string;
  // Specify course_id property (string)
  course_id: string;
  // Specify title property (string)
  title: string;
  // Specify description? property (string)
  description?: string | undefined;
  // Specify due_date? property (string)
  due_date?: string | undefined;
  // Specify max_score property (number)
  max_score: number;
  // Specify rubric_id? property (string)
  rubric_id?: string | undefined;
  // Specify reference_assignment_text? property (string)
  reference_assignment_text?: string | undefined;
  // Specify created_at property (string)
  created_at: string;
}

// Define Classroom interface data contract
export interface Classroom {
  // Specify id property (string)
  id: string;
  // Specify name property (string)
  name: string;
  // Specify code property (string)
  code: string;
  // Specify instructor_id? property (string)
  instructor_id?: string;
  // Specify students_count property (number)
  students_count: number;
  // Specify created_at? property (string)
  created_at?: string;
}

// Define Student interface data contract
export interface Student {
  // Specify id property (string)
  id: string;
  // Specify classroom_id property (string)
  classroom_id: string;
  // Specify roll_number property (string)
  roll_number: string;
  // Specify full_name property (string)
  full_name: string;
  // Specify email? property (string)
  email?: string;
  // Specify created_at? property (string)
  created_at?: string;
}

// Define StudentUploadCSVResponse interface data contract
export interface StudentUploadCSVResponse {
  // Specify total_inserted property (number)
  total_inserted: number;
  // Specify total_skipped property (number)
  total_skipped: number;
  // Specify skipped property (Array<{ row: any; roll_number: string; full_name: string; reason: string }>)
  skipped: Array<{ row: any; roll_number: string; full_name: string; reason: string }>;
  // Specify inserted property (any[])
  inserted: any[];
}

// Define RubricLevel interface data contract
export interface RubricLevel {
  // Specify level_name property (string)
  level_name: string;
  // Specify points property (number)
  points: number;
  // Specify description property (string)
  description: string;
}

// Define RubricCriterion interface data contract
export interface RubricCriterion {
  // Specify id? property (string)
  id?: string;
  // Specify criterion_name? property (string)
  criterion_name?: string;
  // Specify name property (string)
  name: string;
  // Specify description property (string)
  description: string;
  // Specify weight property (number)
  weight: number;
  // Specify max property (number)
  max: number;
  // Specify max_points? property (number)
  max_points?: number;
  // Specify max_score? property (number)
  max_score?: number;
  // Specify score? property (number)
  score?: number;
  // Specify order_index? property (number)
  order_index?: number;
  // Specify levels? property (RubricLevel[])
  levels?: RubricLevel[];
}

// Define Rubric interface data contract
export interface Rubric {
  // Specify id property (string)
  id: string;
  // Specify title? property (string)
  title?: string;
  // Specify name property (string)
  name: string;
  // Specify classroom_id? property (string)
  classroom_id?: string;
  // Specify course_id property (string)
  course_id: string;
  // Specify total_marks? property (number)
  total_marks?: number;
  // Specify total_max_score property (number)
  total_max_score: number;
  // Specify created_at? property (string)
  created_at?: string;
  // Specify criteria property (RubricCriterion[])
  criteria: RubricCriterion[];
}

// Define WebSource interface data contract
export interface WebSource {
  // Specify url property (string)
  url: string;
  // Specify title property (string)
  title: string;
  // Specify snippet property (string)
  snippet: string;
  // Specify match_pct? property (number)
  match_pct?: number;
}

// Define SubmissionItem interface data contract
export interface SubmissionItem {
  // Specify id property (string)
  id: string;
  // Specify assignment_id property (string)
  assignment_id: string;
  // Specify student property (string)
  student: string;
  // Specify roll property (string)
  roll: string;
  // Specify student_id? property (string)
  student_id?: string;
  // Specify file_name property (string)
  file_name: string;
  // Specify status property ("pending" | "flagged" | "approved" | "queued" | "evaluating" | "completed" | "unmatched" | string)
  status:
    | "pending"
    | "flagged"
    | "approved"
    | "queued"
    | "evaluating"
    | "completed"
    | "unmatched"
    | string;
  // Specify score property (number)
  score: number;
  // Specify max_score? property (number)
  max_score?: number;
  // Specify similarity property (number)
  similarity: number;
  // Specify aiContent property (number)
  aiContent: number;
  // Specify webPlagiarism? property (number)
  webPlagiarism?: number;
  // Specify file_url? property (string)
  file_url?: string;
  // Specify criteria_scores? property (Array<)
  criteria_scores?: Array<{
    // Specify criterion_name property (string)
    criterion_name: string;
    // Specify score property (number)
    score: number;
    // Specify max? property (number)
    max?: number;
    // Specify rationale? property (string)
    rationale?: string;
    // Execute statement: }>
  }>;
  // Specify feedback? property (string)
  feedback?: string;
  // Specify plagiarism_report? property ()
  plagiarism_report?: {
    // Specify peer_to_peer_score? property (number)
    peer_to_peer_score?: number;
    // Specify public_source_score? property (number)
    public_source_score?: number;
    // Specify ai_probability? property (number)
    ai_probability?: number;
    // Specify flagged_matches? property (Array<)
    flagged_matches?: Array<{
      // Specify matched_submission_id? property (string)
      matched_submission_id?: string;
      // Specify matched_student_name? property (string)
      matched_student_name?: string;
      // Specify matched_student_roll? property (string)
      matched_student_roll?: string;
      // Specify similarity_score? property (number)
      similarity_score?: number;
      // Execute statement: }>
    }>;
  };
  // Specify created_at property (string)
  created_at: string;
}

// Define ClassroomBatchUploadItem interface data contract
export interface ClassroomBatchUploadItem {
  // Specify id property (string)
  id: string;
  // Specify file_name property (string)
  file_name: string;
  // Specify student_id? property (string)
  student_id?: string;
  // Specify roll_number? property (string)
  roll_number?: string;
  // Specify student_name? property (string)
  student_name?: string;
  // Specify status property ("queued" | "unmatched" | "completed" | string)
  status: "queued" | "unmatched" | "completed" | string;
  // Specify file_url? property (string)
  file_url?: string;
}

// Define ClassroomBatchUploadResponse interface data contract
export interface ClassroomBatchUploadResponse {
  // Specify batch_job_id property (string)
  batch_job_id: string;
  // Specify total property (number)
  total: number;
  // Specify queued_submissions property (ClassroomBatchUploadItem[])
  queued_submissions: ClassroomBatchUploadItem[];
  // Specify unmatched_submissions property (ClassroomBatchUploadItem[])
  unmatched_submissions: ClassroomBatchUploadItem[];
  // Specify status property (string)
  status: string;
}

// Define JobStatusResponse interface data contract
export interface JobStatusResponse {
  // Specify job_id property (string)
  job_id: string;
  // Specify status property ("PENDING" | "PROCESSING" | "SUCCESS" | "FAILURE")
  status: "PENDING" | "PROCESSING" | "SUCCESS" | "FAILURE";
  // Specify current property (number)
  current: number;
  // Specify total property (number)
  total: number;
  // Specify percent property (number)
  percent: number;
  // Specify details? property (Record<string, any>)
  details?: Record<string, any>;
}

// Define SubmissionDetail extends SubmissionItem interface data contract
export interface SubmissionDetail extends SubmissionItem {
  // Specify extracted_text? property (string)
  extracted_text?: string;
  // Specify matching_phrase? property (string)
  matching_phrase?: string;
  // Specify criteria_scores property (Array<)
  criteria_scores: Array<{
    // Specify criterion_name property (string)
    criterion_name: string;
    // Specify score property (number)
    score: number;
    // Specify max? property (number)
    max?: number;
    // Specify rationale? property (string)
    rationale?: string;
    // Execute statement: }>
  }>;
  // Specify ai_feedback? property (string)
  ai_feedback?: string;
  // Specify teacher_feedback? property (string)
  teacher_feedback?: string;
  // Specify webSources? property (WebSource[])
  webSources?: WebSource[];
  // Specify plagiarisedWords? property (string[])
  plagiarisedWords?: string[];
}

// Define BatchJobResponse interface data contract
export interface BatchJobResponse {
  // Specify job_id property (string)
  job_id: string;
  // Specify status property ("queued" | "processing" | "completed" | "failed")
  status: "queued" | "processing" | "completed" | "failed";
  // Specify progress_pct property (number)
  progress_pct: number;
  // Specify total_items property (number)
  total_items: number;
  // Specify processed_items property (number)
  processed_items: number;
  // Specify similarity_flags property (number)
  similarity_flags: number;
  // Specify ready_for_review property (number)
  ready_for_review: number;
  // Specify error_message? property (string)
  error_message?: string;
}

// Define SimilarityMatch interface data contract
export interface SimilarityMatch {
  // Specify id property (string)
  id: string;
  // Specify assignment_id property (string)
  assignment_id: string;
  // Specify submission_a_id property (string)
  submission_a_id: string;
  // Specify submission_b_id property (string)
  submission_b_id: string;
  // Specify student_a_name property (string)
  student_a_name: string;
  // Specify student_b_name property (string)
  student_b_name: string;
  // Specify similarity_score property (number)
  similarity_score: number;
  // Specify matching_phrases property (string[])
  matching_phrases: string[];
  // Specify status property (string)
  status: string;
  // Specify teacher_note? property (string)
  teacher_note?: string;
}

// Token helper
export function getAuthToken(): string | null {
  // Evaluate condition: if (typeof window !== "undefined")
  if (typeof window !== "undefined") {
    // Return value: localStorage.getItem("verism_token")
    return localStorage.getItem("verism_token");
  }
  // Return value: null
  return null;
}

// Define function setAuthToken
export function setAuthToken(token: string): void {
  // Evaluate condition: if (typeof window !== "undefined")
  if (typeof window !== "undefined") {
    // Invoke method: localStorage.setItem("verism_token", token)
    localStorage.setItem("verism_token", token);
  }
}

// Define function clearAuthToken
export function clearAuthToken(): void {
  // Evaluate condition: if (typeof window !== "undefined")
  if (typeof window !== "undefined") {
    // Invoke method: localStorage.removeItem("verism_token")
    localStorage.removeItem("verism_token");
    // Invoke method: localStorage.removeItem("verism_user")
    localStorage.removeItem("verism_user");
  }
}

// Define function getCachedUser
export function getCachedUser(): UserProfile | null {
  // Evaluate condition: if (typeof window !== "undefined")
  if (typeof window !== "undefined") {
    // Declare raw variable
    const raw = localStorage.getItem("verism_user");
    // Evaluate condition: if (raw)
    if (raw) {
      // Begin try block to handle operations safely
      try {
        // Return value: JSON.parse(raw)
        return JSON.parse(raw);
        // Catch and handle error: } catch
      } catch {
        // Return value: null
        return null;
      }
    }
  }
  // Return value: null
  return null;
}

// Define function setCachedUser
export function setCachedUser(user: UserProfile): void {
  // Evaluate condition: if (typeof window !== "undefined")
  if (typeof window !== "undefined") {
    // Invoke method: localStorage.setItem("verism_user", JSON.stringify(user))
    localStorage.setItem("verism_user", JSON.stringify(user));
  }
}

// Define function request<T>
async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  // Declare url variable
  const url = `${API_BASE_URL}${endpoint}`;
  // Declare token variable
  const token = getAuthToken();

  // Declare headers variable
  const headers: Record<string, string> = {
    // Invoke method: ...(options.headers as Record<string, string>)
    ...(options.headers as Record<string, string>),
  };

  // Evaluate condition: if (!(options.body instanceof FormData))
  if (!(options.body instanceof FormData)) {
    // Execute statement: headers["Content-Type"] = "application/json"
    headers["Content-Type"] = "application/json";
  }

  // Evaluate condition: if (token)
  if (token) {
    // Execute statement: headers["Authorization"] = `Bearer ${token}`
    headers["Authorization"] = `Bearer ${token}`;
  }

  // Declare response variable
  const response = await fetch(url, {
    // Execute statement: ...options
    ...options,
    // Execute statement: headers
    headers,
  });

  // Evaluate condition: if (!response.ok)
  if (!response.ok) {
    // Declare errorMsg variable
    let errorMsg = `HTTP Error ${response.status}${response.statusText ? `: ${response.statusText}` : ""}`;
    // Begin try block to handle operations safely
    try {
      // Declare errorJson variable
      const errorJson = await response.json();
      // Evaluate condition: if (errorJson.detail)
      if (errorJson.detail) {
        // Specify errorMsg = typeof errorJson.detail === "string" ? errorJson.detail property (JSON.stringify(errorJson.detail))
        errorMsg =
          typeof errorJson.detail === "string"
            ? errorJson.detail
            : JSON.stringify(errorJson.detail);
      }
      // Catch and handle error: } catch
    } catch {
      // Evaluate condition: if (response.status === 404)
      if (response.status === 404) {
        // Execute statement: errorMsg = `Endpoint not found (404) at ${url}. Verify backend URL configuration.`
        errorMsg = `Endpoint not found (404) at ${url}. Verify backend URL configuration.`;
      }
    }
    // Invoke method: throw new Error(errorMsg)
    throw new Error(errorMsg);
  }

  // Return value: response.json() as Promise<T>
  return response.json() as Promise<T>;
}

// ==========================================
// Authentication Endpoints
// ==========================================
export const api = {
  // Specify auth property ()
  auth: {
    // Specify signUp property (async (data: { name?: string; full_name?: string; email: string; password: string; role?: string }): Promise<AuthResponse> =>)
    signUp: async (data: {
      name?: string;
      full_name?: string;
      email: string;
      password: string;
      role?: string;
    }): Promise<AuthResponse> => {
      // Declare displayName variable
      const displayName = (data.full_name || data.name || "").trim();
      // Declare payload variable
      const payload = {
        // Specify full_name property (displayName)
        full_name: displayName,
        // Specify name property (displayName)
        name: displayName,
        // Specify email property (data.email.trim().toLowerCase())
        email: data.email.trim().toLowerCase(),
        // Specify password property (data.password)
        password: data.password,
        // Specify role property (data.role || "Instructor · Computer Science")
        role: data.role || "Instructor · Computer Science",
      };
      // Declare res variable
      const res = await request<AuthResponse>("/auth/signup", {
        // Specify method property ("POST")
        method: "POST",
        // Specify body property (JSON.stringify(payload))
        body: JSON.stringify(payload),
      });
      // Invoke method: setAuthToken(res.access_token)
      setAuthToken(res.access_token);
      // Invoke method: setCachedUser(res.user)
      setCachedUser(res.user);
      // Return value: res
      return res;
    },
    // Specify login property (async (data: { email: string; password: string }): Promise<AuthResponse> =>)
    login: async (data: { email: string; password: string }): Promise<AuthResponse> => {
      // Declare res variable
      const res = await request<AuthResponse>("/auth/login", {
        // Specify method property ("POST")
        method: "POST",
        // Specify body property (JSON.stringify()
        body: JSON.stringify({
          // Specify email property (data.email.trim().toLowerCase())
          email: data.email.trim().toLowerCase(),
          // Specify password property (data.password)
          password: data.password,
          // Invoke method: })
        }),
      });
      // Invoke method: setAuthToken(res.access_token)
      setAuthToken(res.access_token);
      // Invoke method: setCachedUser(res.user)
      setCachedUser(res.user);
      // Return value: res
      return res;
    },
    // Specify logout property (async (): Promise<{ message: string }> =>)
    logout: async (): Promise<{ message: string }> => {
      // Begin try block to handle operations safely
      try {
        // Return value: await request<{ message: string }>("/auth/logout",
        return await request<{ message: string }>("/auth/logout", {
          // Specify method property ("POST")
          method: "POST",
        });
        // Execute statement: } finally
      } finally {
        // Invoke method: clearAuthToken()
        clearAuthToken();
      }
    },
    // Specify getMe property (async (): Promise<UserProfile> =>)
    getMe: async (): Promise<UserProfile> => {
      // Declare user variable
      const user = await request<UserProfile>("/auth/me");
      // Invoke method: setCachedUser(user)
      setCachedUser(user);
      // Return value: user
      return user;
    },
    // Specify updatePreferences property (async (prefs: Record<string, any>): Promise<UserProfile> =>)
    updatePreferences: async (prefs: Record<string, any>): Promise<UserProfile> => {
      // Return value: request<UserProfile>("/auth/preferences",
      return request<UserProfile>("/auth/preferences", {
        // Specify method property ("PUT")
        method: "PUT",
        // Specify body property (JSON.stringify(prefs))
        body: JSON.stringify(prefs),
      });
    },
    // Specify clearMockData property (async (): Promise<{ message: string }> =>)
    clearMockData: async (): Promise<{ message: string }> => {
      // Return value: request<{ message: string }>("/auth/clear-mock-data",
      return request<{ message: string }>("/auth/clear-mock-data", {
        // Specify method property ("POST")
        method: "POST",
      });
    },
  },

  // ==========================================
  // Courses
  // ==========================================
  courses: {
    // Specify list property (async (search?: string): Promise<Course[]> =>)
    list: async (search?: string): Promise<Course[]> => {
      // Declare query variable
      const query = search ? `?search=${encodeURIComponent(search)}` : "";
      // Return value: request<Course[]>(`/courses${query}`)
      return request<Course[]>(`/courses${query}`);
    },
    // Specify get property (async (id: string): Promise<Course> =>)
    get: async (id: string): Promise<Course> => {
      // Return value: request<Course>(`/courses/${id}`)
      return request<Course>(`/courses/${id}`);
    },
    // Specify create property (async (data: { name: string; code: string; section?: string; tone?: string; students_count?: number }): Promise<Course> =>)
    create: async (data: {
      name: string;
      code: string;
      section?: string;
      tone?: string;
      students_count?: number;
    }): Promise<Course> => {
      // Return value: request<Course>("/courses",
      return request<Course>("/courses", {
        // Specify method property ("POST")
        method: "POST",
        // Specify body property (JSON.stringify(data))
        body: JSON.stringify(data),
      });
    },
    // Specify delete property (async (id: string): Promise<void> =>)
    delete: async (id: string): Promise<void> => {
      // Return value: request<void>(`/courses/${id}`,
      return request<void>(`/courses/${id}`, {
        // Specify method property ("DELETE")
        method: "DELETE",
      });
    },
  },

  // ==========================================
  // Assignments & Reference Exemplars
  // ==========================================
  assignments: {
    // Specify listByCourse property (async (courseId: string): Promise<Assignment[]> =>)
    listByCourse: async (courseId: string): Promise<Assignment[]> => {
      // Return value: request<Assignment[]>(`/courses/${courseId}/assignments`)
      return request<Assignment[]>(`/courses/${courseId}/assignments`);
    },
    // Specify get property (async (id: string): Promise<Assignment> =>)
    get: async (id: string): Promise<Assignment> => {
      // Return value: request<Assignment>(`/assignments/${id}`)
      return request<Assignment>(`/assignments/${id}`);
    },
    // Specify create property (async ()
    create: async (
      // Specify courseId property (string)
      courseId: string,
      // Specify data property ()
      data: {
        // Specify title property (string)
        title: string;
        // Specify description? property (string)
        description?: string;
        // Specify max_score? property (number)
        max_score?: number;
        // Specify rubric_id? property (string)
        rubric_id?: string;
        // Specify reference_assignment_text? property (string)
        reference_assignment_text?: string;
        // Specify due_date? property (string)
        due_date?: string;
      },
      // Specify ) property (Promise<Assignment> =>)
    ): Promise<Assignment> => {
      // Begin try block to handle operations safely
      try {
        // Return value: await request<Assignment>("/assignments",
        return await request<Assignment>("/assignments", {
          // Specify method property ("POST")
          method: "POST",
          // Specify body property (JSON.stringify()
          body: JSON.stringify({
            // Specify course_id property (courseId)
            course_id: courseId,
            // Execute statement: ...data
            ...data,
            // Invoke method: })
          }),
        });
        // Catch and handle error: } catch
      } catch {
        // Return value: await request<Assignment>(`/courses/${courseId}/assignments`,
        return await request<Assignment>(`/courses/${courseId}/assignments`, {
          // Specify method property ("POST")
          method: "POST",
          // Specify body property (JSON.stringify(data))
          body: JSON.stringify(data),
        });
      }
    },
    // Specify update property (async ()
    update: async (
      // Specify id property (string)
      id: string,
      // Specify data property ()
      data: {
        // Specify title? property (string)
        title?: string;
        // Specify description? property (string)
        description?: string;
        // Specify max_score? property (number)
        max_score?: number;
        // Specify rubric_id? property (string)
        rubric_id?: string;
        // Specify reference_assignment_text? property (string)
        reference_assignment_text?: string;
      },
      // Specify ) property (Promise<Assignment> =>)
    ): Promise<Assignment> => {
      // Return value: request<Assignment>(`/assignments/${id}`,
      return request<Assignment>(`/assignments/${id}`, {
        // Specify method property ("PUT")
        method: "PUT",
        // Specify body property (JSON.stringify(data))
        body: JSON.stringify(data),
      });
    },
    // Specify delete property (async (id: string): Promise<void> =>)
    delete: async (id: string): Promise<void> => {
      // Return value: request<void>(`/assignments/${id}`,
      return request<void>(`/assignments/${id}`, {
        // Specify method property ("DELETE")
        method: "DELETE",
      });
    },
  },

  // ==========================================
  // Classrooms & Roll Call Roster
  // ==========================================
  classrooms: {
    // Specify list property (async (): Promise<Classroom[]> =>)
    list: async (): Promise<Classroom[]> => {
      // Return value: request<Classroom[]>("/classrooms")
      return request<Classroom[]>("/classrooms");
    },
    // Specify get property (async (id: string): Promise<Classroom> =>)
    get: async (id: string): Promise<Classroom> => {
      // Return value: request<Classroom>(`/classrooms/${id}`)
      return request<Classroom>(`/classrooms/${id}`);
    },
    // Specify create property (async (data: { name: string; code: string }): Promise<Classroom> =>)
    create: async (data: { name: string; code: string }): Promise<Classroom> => {
      // Return value: request<Classroom>("/classrooms",
      return request<Classroom>("/classrooms", {
        // Specify method property ("POST")
        method: "POST",
        // Specify body property (JSON.stringify(data))
        body: JSON.stringify(data),
      });
    },
    // Specify delete property (async (id: string): Promise<void> =>)
    delete: async (id: string): Promise<void> => {
      // Return value: request<void>(`/classrooms/${id}`,
      return request<void>(`/classrooms/${id}`, {
        // Specify method property ("DELETE")
        method: "DELETE",
      });
    },
    deleteStudent: async (classroomId: string, studentId: string): Promise<void> => {
      return request<void>(`/classrooms/${classroomId}/students/${studentId}`, {
        method: "DELETE",
      });
    },
    // Specify getStudents property (async (classroomId: string): Promise<Student[]> =>)
    getStudents: async (classroomId: string): Promise<Student[]> => {
      // Return value: request<Student[]>(`/classrooms/${classroomId}/students`)
      return request<Student[]>(`/classrooms/${classroomId}/students`);
    },
    // Specify enrollManual property (async ()
    enrollManual: async (
      // Specify classroomId property (string)
      classroomId: string,
      // Specify students property (Array<{ roll_number: string; full_name: string; email?: string | undefined }>)
      students: Array<{ roll_number: string; full_name: string; email?: string | undefined }>,
      // Specify ) property (Promise<any> =>)
    ): Promise<any> => {
      // Return value: request<any>(`/classrooms/${classroomId}/students/manual`,
      return request<any>(`/classrooms/${classroomId}/students/manual`, {
        // Specify method property ("POST")
        method: "POST",
        // Specify body property (JSON.stringify(students))
        body: JSON.stringify(students),
      });
    },
    // Specify uploadCSV property (async (classroomId: string, file: File): Promise<StudentUploadCSVResponse> =>)
    uploadCSV: async (classroomId: string, file: File): Promise<StudentUploadCSVResponse> => {
      // Declare formData variable
      const formData = new FormData();
      // Invoke method: formData.append("file", file)
      formData.append("file", file);
      // Return value: request<StudentUploadCSVResponse>(`/classrooms/${classroomId}/students/upload-csv`,
      return request<StudentUploadCSVResponse>(`/classrooms/${classroomId}/students/upload-csv`, {
        // Specify method property ("POST")
        method: "POST",
        // Specify body property (formData)
        body: formData,
      });
    },
  },

  // ==========================================
  // Matrix Rubrics
  // ==========================================
  rubrics: {
    // Specify list property (async (classroomId?: string): Promise<Rubric[]> =>)
    list: async (classroomId?: string): Promise<Rubric[]> => {
      // Declare q variable
      const q = classroomId ? `?classroom_id=${encodeURIComponent(classroomId)}` : "";
      // Return value: request<Rubric[]>(`/rubrics${q}`)
      return request<Rubric[]>(`/rubrics${q}`);
    },
    // Specify listByCourse property (async (courseId: string): Promise<Rubric[]> =>)
    listByCourse: async (courseId: string): Promise<Rubric[]> => {
      // Return value: request<Rubric[]>(`/rubrics?classroom_id=${encodeURIComponent(courseId)}`)
      return request<Rubric[]>(`/rubrics?classroom_id=${encodeURIComponent(courseId)}`);
    },
    // Specify get property (async (id: string): Promise<Rubric> =>)
    get: async (id: string): Promise<Rubric> => {
      // Return value: request<Rubric>(`/rubrics/${id}`)
      return request<Rubric>(`/rubrics/${id}`);
    },
    // Specify create property (async (data:)
    create: async (data: {
      // Specify title? property (string)
      title?: string;
      // Specify name? property (string)
      name?: string;
      // Specify classroom_id? property (string)
      classroom_id?: string;
      // Specify course_id? property (string)
      course_id?: string;
      // Specify total_marks? property (number)
      total_marks?: number;
      // Specify total_max_score? property (number)
      total_max_score?: number;
      // Specify criteria property (Array<)
      criteria: Array<{
        // Specify criterion_name? property (string)
        criterion_name?: string;
        // Specify name? property (string)
        name?: string;
        // Specify description? property (string)
        description?: string;
        // Specify weight? property (number)
        weight?: number;
        // Specify max_points? property (number)
        max_points?: number;
        // Specify max_score? property (number)
        max_score?: number;
        // Specify levels? property (RubricLevel[])
        levels?: RubricLevel[];
        // Execute statement: }>
      }>;
      // Specify }) property (Promise<Rubric> =>)
    }): Promise<Rubric> => {
      // Return value: request<Rubric>("/rubrics",
      return request<Rubric>("/rubrics", {
        // Specify method property ("POST")
        method: "POST",
        // Specify body property (JSON.stringify()
        body: JSON.stringify({
          // Specify title property (data.title || data.name)
          title: data.title || data.name,
          // Specify classroom_id property (data.classroom_id || data.course_id)
          classroom_id: data.classroom_id || data.course_id,
          // Specify total_marks property (data.total_marks || data.total_max_score)
          total_marks: data.total_marks || data.total_max_score,
          // Specify criteria property (data.criteria.map((c, i) => ()
          criteria: data.criteria.map((c, i) => ({
            // Specify criterion_name property (c.criterion_name || c.name || `Criterion ${i + 1}`)
            criterion_name: c.criterion_name || c.name || `Criterion ${i + 1}`,
            // Specify max_points property (c.max_points || c.max_score || 4.0)
            max_points: c.max_points || c.max_score || 4.0,
            // Specify order_index property (i)
            order_index: i,
            // Specify levels property (c.levels || [])
            levels: c.levels || [],
            // Invoke method: }))
          })),
          // Invoke method: })
        }),
      });
    },
    // Specify delete property (async (id: string): Promise<void> =>)
    delete: async (id: string): Promise<void> => {
      // Return value: request<void>(`/rubrics/${id}`,
      return request<void>(`/rubrics/${id}`, {
        // Specify method property ("DELETE")
        method: "DELETE",
      });
    },
    // Specify upload property for rubric documents (PDF, DOCX, XLSX, TXT, CSV, images)
    upload: async (
      file: File,
      options?: { classroom_id?: string; course_id?: string; title?: string },
    ): Promise<Rubric> => {
      const formData = new FormData();
      formData.append("file", file);
      if (options?.classroom_id) formData.append("classroom_id", options.classroom_id);
      if (options?.course_id) formData.append("course_id", options.course_id);
      if (options?.title) formData.append("title", options.title);
      return request<Rubric>("/rubrics/upload", {
        method: "POST",
        body: formData,
      });
    },
  },

  // ==========================================
  // Submissions (Upload & Manual Input)
  // ==========================================
  submissions: {
    // Specify listByAssignment property (async (assignmentId: string): Promise<SubmissionItem[]> =>)
    listByAssignment: async (assignmentId: string): Promise<SubmissionItem[]> => {
      // Return value: request<SubmissionItem[]>(`/assignments/${assignmentId}/submissions`)
      return request<SubmissionItem[]>(`/assignments/${assignmentId}/submissions`);
    },
    // Specify createManual property (async ()
    createManual: async (
      // Specify assignmentId property (string)
      assignmentId: string,
      // Specify data property ()
      data: {
        // Specify student_name property (string)
        student_name: string;
        // Specify student_roll property (string)
        student_roll: string;
        // Specify student_email? property (string)
        student_email?: string;
        // Specify extracted_text property (string)
        extracted_text: string;
      },
      // Specify ) property (Promise<SubmissionItem> =>)
    ): Promise<SubmissionItem> => {
      // Return value: request<SubmissionItem>(`/assignments/${assignmentId}/submissions`,
      return request<SubmissionItem>(`/assignments/${assignmentId}/submissions`, {
        // Specify method property ("POST")
        method: "POST",
        // Specify body property (JSON.stringify()
        body: JSON.stringify({
          // Specify assignment_id property (assignmentId)
          assignment_id: assignmentId,
          // Execute statement: ...data
          ...data,
          // Invoke method: })
        }),
      });
    },
    // Specify batchUpload property (async (assignmentId: string, files: File[]): Promise<any> =>)
    batchUpload: async (assignmentId: string, files: File[]): Promise<any> => {
      // Declare formData variable
      const formData = new FormData();
      // Invoke method: files.forEach((f) => formData.append("files", f))
      files.forEach((f) => formData.append("files", f));
      // Return value: request<any>(`/assignments/${assignmentId}/submissions/batch-upload`,
      return request<any>(`/assignments/${assignmentId}/submissions/batch-upload`, {
        // Specify method property ("POST")
        method: "POST",
        // Specify body property (formData)
        body: formData,
      });
    },
    // Specify batchUploadClassroom property (async ()
    batchUploadClassroom: async (
      // Specify classroomId property (string)
      classroomId: string,
      // Specify assignmentId property (string)
      assignmentId: string,
      // Specify files property (File[] | File)
      files: File[] | File,
      // Specify rubricId? property (string)
      rubricId?: string,
      // Specify ) property (Promise<ClassroomBatchUploadResponse> =>)
    ): Promise<ClassroomBatchUploadResponse> => {
      // Declare formData variable
      const formData = new FormData();
      // Evaluate condition: if (Array.isArray(files))
      if (Array.isArray(files)) {
        const firstFile = files[0];
        if (files.length === 1 && firstFile && firstFile.name.toLowerCase().endsWith(".zip")) {
          // Invoke method: formData.append("file", firstFile)
          formData.append("file", firstFile);
          // Execute statement: } else
        } else {
          // Invoke method: files.forEach((f) => formData.append("files", f))
          files.forEach((f) => formData.append("files", f));
        }
        // Execute statement: } else
      } else {
        // Evaluate condition: if (files.name.toLowerCase().endsWith(".zip"))
        if (files.name.toLowerCase().endsWith(".zip")) {
          // Invoke method: formData.append("file", files)
          formData.append("file", files);
          // Execute statement: } else
        } else {
          // Invoke method: formData.append("files", files)
          formData.append("files", files);
        }
      }
      // Evaluate condition: if (rubricId)
      if (rubricId) {
        // Invoke method: formData.append("rubric_id", rubricId)
        formData.append("rubric_id", rubricId);
      }
      // Return value: request<ClassroomBatchUploadResponse>(
      return request<ClassroomBatchUploadResponse>(
        // Execute statement: `/classrooms/${classroomId}/assignments/${assignmentId}/batch-upload`
        `/classrooms/${classroomId}/assignments/${assignmentId}/batch-upload`,
        {
          // Specify method property ("POST")
          method: "POST",
          // Specify body property (formData)
          body: formData,
        },
      );
    },
    // Specify assignStudent property (async ()
    assignStudent: async (
      // Specify submissionId property (string)
      submissionId: string,
      // Specify studentId property (string)
      studentId: string,
      // Specify ) property (Promise<SubmissionItem> =>)
    ): Promise<SubmissionItem> => {
      // Return value: request<SubmissionItem>(`/submissions/${submissionId}/assign-student`,
      return request<SubmissionItem>(`/submissions/${submissionId}/assign-student`, {
        // Specify method property ("PATCH")
        method: "PATCH",
        // Specify body property (JSON.stringify({ student_id: studentId }))
        body: JSON.stringify({ student_id: studentId }),
      });
    },
    // Specify delete property (async (id: string): Promise<void> =>)
    delete: async (id: string): Promise<void> => {
      // Return value: request<void>(`/submissions/${id}`,
      return request<void>(`/submissions/${id}`, {
        // Specify method property ("DELETE")
        method: "DELETE",
      });
    },
    // Specify clearAll property (async (assignmentId: string): Promise<{ cleared: number }> =>)
    clearAll: async (assignmentId: string): Promise<{ cleared: number }> => {
      // Return value: request<{ cleared: number }>(`/assignments/${assignmentId}/submissions`,
      return request<{ cleared: number }>(`/assignments/${assignmentId}/submissions`, {
        // Specify method property ("DELETE")
        method: "DELETE",
      });
    },
  },

  // ==========================================
  // Live Job Status Polling
  // ==========================================
  jobs: {
    // Specify getStatus property (async (batchJobId: string): Promise<JobStatusResponse> =>)
    getStatus: async (batchJobId: string): Promise<JobStatusResponse> => {
      // Return value: request<JobStatusResponse>(`/jobs/${batchJobId}/status`)
      return request<JobStatusResponse>(`/jobs/${batchJobId}/status`);
    },
  },

  // ==========================================
  // Batch AI Evaluation with 3-Way Plagiarism
  // ==========================================
  evaluations: {
    // Specify triggerBatch property (async ()
    triggerBatch: async (
      // Specify assignmentId property (string)
      assignmentId: string,
      // Specify data property ()
      data: {
        rubric_id?: string | undefined;
        similarity_threshold?: number | undefined;
        submission_ids?: string[] | undefined;
        title?: string | undefined;
        reference_assignment_text?: string | undefined;
      } = {},
      // Specify ) property (Promise<BatchJobResponse> =>)
    ): Promise<BatchJobResponse> => {
      // Begin try block to handle operations safely
      try {
        // Return value: await request<BatchJobResponse>(`/assignments/${assignmentId}/evaluate`,
        return await request<BatchJobResponse>(`/assignments/${assignmentId}/evaluate`, {
          // Specify method property ("POST")
          method: "POST",
          // Specify body property (JSON.stringify()
          body: JSON.stringify({
            // Specify assignment_id property (assignmentId)
            assignment_id: assignmentId,
            // Execute statement: ...data
            ...data,
            // Invoke method: })
          }),
        });
        // Catch and handle error: } catch
      } catch {
        // Return value: await request<BatchJobResponse>(`/assignments/${assignmentId}/evaluate-batch`,
        return await request<BatchJobResponse>(`/assignments/${assignmentId}/evaluate-batch`, {
          // Specify method property ("POST")
          method: "POST",
          // Specify body property (JSON.stringify()
          body: JSON.stringify({
            // Specify assignment_id property (assignmentId)
            assignment_id: assignmentId,
            // Execute statement: ...data
            ...data,
            // Invoke method: })
          }),
        });
      }
    },
    // Specify evaluateSingle property (async (submissionId: string): Promise<SubmissionDetail> =>)
    evaluateSingle: async (submissionId: string): Promise<SubmissionDetail> => {
      // Return value: request<SubmissionDetail>(`/submissions/${submissionId}/evaluate`,
      return request<SubmissionDetail>(`/submissions/${submissionId}/evaluate`, {
        // Specify method property ("POST")
        method: "POST",
      });
    },
    // Specify pollJobStatus property (async (jobId: string): Promise<BatchJobResponse> =>)
    pollJobStatus: async (jobId: string): Promise<BatchJobResponse> => {
      // Return value: request<BatchJobResponse>(`/jobs/${jobId}`)
      return request<BatchJobResponse>(`/jobs/${jobId}`);
    },
    // Specify getActiveJob property (async (assignmentId: string): Promise<BatchJobResponse | null> =>)
    getActiveJob: async (assignmentId: string): Promise<BatchJobResponse | null> => {
      // Begin try block to handle operations safely
      try {
        // Return value: await request<BatchJobResponse | null>(`/assignments/${assignmentId}/active-job`)
        return await request<BatchJobResponse | null>(`/assignments/${assignmentId}/active-job`);
        // Catch and handle error: } catch
      } catch {
        // Return value: null
        return null;
      }
    },
  },

  // ==========================================
  // Review Queue & Teacher Grade Stamping
  // ==========================================
  review: {
    // Specify getQueue property (async (assignmentId: string, statusFilter?: string): Promise<SubmissionItem[]> =>)
    getQueue: async (assignmentId: string, statusFilter?: string): Promise<SubmissionItem[]> => {
      // Declare query variable
      const query = statusFilter ? `?status_filter=${statusFilter}` : "";
      // Return value: request<SubmissionItem[]>(`/assignments/${assignmentId}/reviews${query}`)
      return request<SubmissionItem[]>(`/assignments/${assignmentId}/reviews${query}`);
    },
    // Specify getDetail property (async (submissionId: string): Promise<SubmissionDetail> =>)
    getDetail: async (submissionId: string): Promise<SubmissionDetail> => {
      // Return value: request<SubmissionDetail>(`/submissions/${submissionId}/review-detail`)
      return request<SubmissionDetail>(`/submissions/${submissionId}/review-detail`);
    },
    // Specify stampGrade property (async ()
    stampGrade: async (
      // Specify submissionId property (string)
      submissionId: string,
      // Specify data property ()
      data: {
        // Specify status? property (string)
        status?: string;
        // Specify final_score property (number)
        final_score: number;
        // Specify criteria_scores? property (any[])
        criteria_scores?: any[];
        // Specify teacher_feedback? property (string)
        teacher_feedback?: string;
        // Specify action? property (string)
        action?: string;
      },
      // Specify ) property (Promise<any> =>)
    ): Promise<any> => {
      // Return value: request<any>(`/submissions/${submissionId}/stamp-grade`,
      return request<any>(`/submissions/${submissionId}/stamp-grade`, {
        // Specify method property ("PUT")
        method: "PUT",
        // Specify body property (JSON.stringify()
        body: JSON.stringify({
          // Specify status property (data.status || "approved")
          status: data.status || "approved",
          // Specify final_score property (data.final_score)
          final_score: data.final_score,
          // Specify criteria_scores property (data.criteria_scores)
          criteria_scores: data.criteria_scores,
          // Specify teacher_feedback property (data.teacher_feedback)
          teacher_feedback: data.teacher_feedback,
          // Specify action property (data.action || "APPROVE")
          action: data.action || "APPROVE",
          // Invoke method: })
        }),
      });
    },
    // Specify flagAction property (async ()
    flagAction: async (
      // Specify submissionId property (string)
      submissionId: string,
      // Specify data property ({ action: string; note?: string })
      data: { action: string; note?: string },
      // Specify ) property (Promise<any> =>)
    ): Promise<any> => {
      // Return value: request<any>(`/submissions/${submissionId}/flag-action`,
      return request<any>(`/submissions/${submissionId}/flag-action`, {
        // Specify method property ("POST")
        method: "POST",
        // Specify body property (JSON.stringify(data))
        body: JSON.stringify(data),
      });
    },
  },

  // ==========================================
  // Similarity
  // ==========================================
  similarity: {
    // Specify listMatches property (async (assignmentId: string): Promise<SimilarityMatch[]> =>)
    listMatches: async (assignmentId: string): Promise<SimilarityMatch[]> => {
      // Declare res variable
      const res = await request<any>(`/assignments/${assignmentId}/similarity`);
      // Evaluate condition: if (Array.isArray(res))
      if (Array.isArray(res)) {
        // Return value: res
        return res;
      }
      // Evaluate condition: if (res && Array.isArray(res.pairs))
      if (res && Array.isArray(res.pairs)) {
        // Return value: res.pairs.map((p: any) => (
        return res.pairs.map((p: any) => ({
          // Specify id property (p.pair_id || p.id)
          id: p.pair_id || p.id,
          // Specify assignment_id property (assignmentId)
          assignment_id: assignmentId,
          // Specify submission_a_id property (p.student_a?.id || "")
          submission_a_id: p.student_a?.id || "",
          // Specify submission_b_id property (p.student_b?.id || "")
          submission_b_id: p.student_b?.id || "",
          // Specify student_a_name property (p.a || p.student_a?.name || "Student A")
          student_a_name: p.a || p.student_a?.name || "Student A",
          // Specify student_b_name property (p.b || p.student_b?.name || "Student B")
          student_b_name: p.b || p.student_b?.name || "Student B",
          // Specify similarity_score property (p.similarity || 0)
          similarity_score: p.similarity || 0,
          // Specify matching_phrases property (p.matching_phrases || [])
          matching_phrases: p.matching_phrases || [],
          // Specify status property (p.status || "")
          status: p.status || "",
          // Specify teacher_note property (p.teacher_note)
          teacher_note: p.teacher_note,
          // Invoke method: }))
        }));
      }
      // Return value: []
      return [];
    },
  },

  // ==========================================
  // Gradebook
  // ==========================================
  gradebook: {
    // Specify getCourseGradebook property (async (courseId: string): Promise<any> =>)
    getCourseGradebook: async (courseId: string): Promise<any> => {
      // Return value: request<any>(`/courses/${courseId}/gradebook`)
      return request<any>(`/courses/${courseId}/gradebook`);
    },
  },
};
