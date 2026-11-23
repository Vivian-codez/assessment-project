/**
 * Verism AI API Client.
 * Connects the TanStack Start frontend to the FastAPI + PostgreSQL + Supabase backend.
 */

// Import validated client environment configuration
import { clientEnv } from "./env";

/**
 * Resolves the base API URL for backend HTTP requests.
 * Evaluates VITE_API_BASE_URL environment variable and validates production configurations.
 *
 * @returns {string} The fully qualified API base URL path.
 */
function resolveApiBaseUrl(): string {
  // Read VITE_API_BASE_URL or VITE_API_URL from environment variables
  const envUrl = (import.meta.env as any)["VITE_API_BASE_URL"] || (import.meta.env as any)["VITE_API_URL"];
  // Check if envUrl is populated and non-empty
  if (envUrl && typeof envUrl === "string" && envUrl.trim().length > 0) {
    // Strip trailing slashes from configured URL
    const trimmed = envUrl.trim().replace(/\/+$/, "");
    // Check if trimmed URL already concludes with /api/v1
    if (trimmed.endsWith("/api/v1")) {
      // Return URL as configured
      return trimmed;
    }
    // Check if trimmed URL concludes with /api
    if (trimmed.endsWith("/api")) {
      // Append v1 version segment
      return `${trimmed}/v1`;
    }
    // Append default /api/v1 prefix
    return `${trimmed}/api/v1`;
  }
  // If running in production mode without configured backend URL, warn explicitly
  if (import.meta.env?.PROD) {
    // Log prominent critical warning
    console.warn(
      "[Verism AI API] CRITICAL: VITE_API_BASE_URL environment variable is not defined in production settings. " +
      "Falling back to http://localhost:8000/api/v1 which will fail in remote browser sessions. " +
      "Configure VITE_API_BASE_URL in your Vercel project environment variables."
    );
  }
  // Fallback to local FastAPI development backend URL
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
  // Specify is_unmatched? property (boolean)
  is_unmatched?: boolean | undefined;
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
  if (typeof window !== "undefined") {
    return localStorage.getItem("verism_token");
  }
  return null;
}

// Refresh token helper
export function getRefreshToken(): string | null {
  if (typeof window !== "undefined") {
    return localStorage.getItem("verism_refresh_token");
  }
  return null;
}

// Define function setAuthToken
export function setAuthToken(token: string): void {
  if (typeof window !== "undefined") {
    localStorage.setItem("verism_token", token);
  }
}

// Define function setRefreshToken
export function setRefreshToken(token: string): void {
  if (typeof window !== "undefined") {
    localStorage.setItem("verism_refresh_token", token);
  }
}

// Define function clearAuthToken
export function clearAuthToken(): void {
  if (typeof window !== "undefined") {
    localStorage.removeItem("verism_token");
    localStorage.removeItem("verism_refresh_token");
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

// Define function request<T> executing authenticated HTTP requests with token rotation
async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  // Construct absolute API endpoint URL
  const url = `${API_BASE_URL}${endpoint}`;
  // Retrieve active JWT access token from browser storage
  let token = getAuthToken();

  // Initialize request headers dictionary
  const headers: Record<string, string> = {
    // Spread any custom headers supplied in options
    ...(options.headers as Record<string, string>),
  };

  // Set Content-Type to JSON when body is not multipart FormData
  if (!(options.body instanceof FormData)) {
    // Assign JSON content type header
    headers["Content-Type"] = "application/json";
  }

  // Attach bearer authorization header when token exists and header not already set
  if (token && !headers["Authorization"]) {
    headers["Authorization"] = `Bearer ${token}`;
    headers["X-Auth-Token"] = token;
  }

  // Configure fetch options with credentials included for secure httpOnly refresh cookie
  const fetchOptions: RequestInit = {
    // Include credentials (cookies) in cross-origin and same-origin requests
    credentials: "include",
    // Spread remaining caller options
    ...options,
    // Provide computed request headers
    headers,
  };

  // Perform HTTP request using browser fetch
  let response = await fetch(url, fetchOptions);

  // Validate endpoint boundary ensuring safe string type
  const safeEndpoint = typeof endpoint === "string" ? endpoint : String(endpoint || "");
  // Normalize leading forward slash
  const cleanEndpoint = safeEndpoint.startsWith("/") ? safeEndpoint : `/${safeEndpoint}`;
  // Determine if target is an unauthenticated credential route
  const isAuthRoute =
    cleanEndpoint.startsWith("/auth/login") ||
    cleanEndpoint.startsWith("/auth/signup") ||
    cleanEndpoint.startsWith("/auth/register") ||
    cleanEndpoint.startsWith("/auth/refresh");

  // Check if response is 401 Unauthorized and not on an authentication endpoint
  if (response.status === 401 && !isAuthRoute) {
    // Attempt automatic refresh token rotation
    try {
      const refToken = getRefreshToken();
      // Call backend refresh endpoint with credentials included and optional body fallback
      const refreshRes = await fetch(`${API_BASE_URL}/auth/refresh`, {
        // Specify HTTP POST method
        method: "POST",
        // Send httpOnly cookies with request
        credentials: "include",
        // Specify JSON content type header
        headers: { "Content-Type": "application/json" },
        body: refToken ? JSON.stringify({ refresh_token: refToken }) : undefined,
      });

      // Check if token refresh succeeded
      if (refreshRes.ok) {
        // Parse refreshed token payload
        const refreshData = await refreshRes.json();
        // Check if new access token was returned
        if (refreshData.access_token) {
          // Persist rotated access token to storage
          setAuthToken(refreshData.access_token);
          if (refreshData.refresh_token) {
            setRefreshToken(refreshData.refresh_token);
          }
          // Update Authorization header for retry
          headers["Authorization"] = `Bearer ${refreshData.access_token}`;
          headers["X-Auth-Token"] = refreshData.access_token;
          // Retry original request with newly issued access token
          response = await fetch(url, { ...fetchOptions, headers });
        }
      }
    } catch (refreshErr) {
      console.warn("Silent token refresh error:", refreshErr);
    }
  }

  // Check if HTTP response status indicates an error
  if (!response.ok) {
    // Initialize default error message with status code and text
    let errorMsg = `HTTP Error ${response.status}${response.statusText ? `: ${response.statusText}` : ""}`;
    // Begin try block to extract backend JSON error details
    try {
      // Parse JSON response body
      const errorJson = await response.json();
      // Check if standard detail field is provided
      if (errorJson.detail) {
        // Format string or serialize object detail
        errorMsg =
          typeof errorJson.detail === "string"
            ? errorJson.detail
            : JSON.stringify(errorJson.detail);
      }
    } catch {
      // Provide actionable message for 404 Not Found errors
      if (response.status === 404) {
        // Format descriptive 404 error string
        errorMsg = `Endpoint not found (404) at ${url}. Verify backend URL configuration.`;
      }
    }
    // Throw descriptive Error exception
    throw new Error(errorMsg);
  }

  // Return parsed JSON payload typed as T
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
      if ((res as any).refresh_token) {
        setRefreshToken((res as any).refresh_token);
      }
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
      if ((res as any).refresh_token) {
        setRefreshToken((res as any).refresh_token);
      }
      // Invoke method: setCachedUser(res.user)
      setCachedUser(res.user);
      // Return value: res
      return res;
    },
    // Alias register for signUp endpoint
    register: async (data: {
      name?: string;
      full_name?: string;
      email: string;
      password: string;
      role?: string;
    }): Promise<AuthResponse> => {
      // Delegate registration to signUp method
      return api.auth.signUp(data);
    },
    // Explicit refresh token invocation
    refreshToken: async (): Promise<{ access_token: string; token_type: string }> => {
      // Request refreshed access token using httpOnly cookie
      const res = await request<{ access_token: string; token_type: string }>("/auth/refresh", {
        // Specify HTTP POST method
        method: "POST",
      });
      // Update stored access token
      setAuthToken(res.access_token);
      // Return refreshed token response
      return res;
    },
    // Forgot password request sending recovery instructions
    forgotPassword: async (email: string): Promise<{ message: string }> => {
      // Dispatch forgot password request with email
      return request<{ message: string }>("/auth/forgot-password", {
        // Specify HTTP POST method
        method: "POST",
        // Send email payload in JSON
        body: JSON.stringify({ email: email.trim().toLowerCase() }),
      });
    },
    // Reset password using verified cryptographic token
    resetPassword: async (token: string, newPassword: string): Promise<{ message: string }> => {
      // Dispatch reset password request with token and new password
      return request<{ message: string }>("/auth/reset-password", {
        // Specify HTTP POST method
        method: "POST",
        // Send token and new password payload
        body: JSON.stringify({ token, new_password: newPassword }),
      });
    },
    // Change password for currently authenticated user
    changePassword: async (currentPassword: string, newPassword: string): Promise<{ message: string }> => {
      // Dispatch password update request with current and new password
      return request<{ message: string }>("/auth/change-password", {
        // Specify HTTP POST method
        method: "POST",
        // Send password update payload
        body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
      });
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
    // Auto-save draft assignment
    saveDraft: async (data: Record<string, any>): Promise<any> => {
      return request<any>("/assignments/draft", {
        method: "POST",
        body: JSON.stringify(data),
      });
    },
    // Upload reference solution file or pasted text
    uploadReferenceSolution: async (
      assignmentId: string,
      file?: File,
      solutionText?: string,
    ): Promise<{
      assignment_id: string;
      filename: string;
      file_size: number;
      reference_solution_text: string;
      extracted_preview: string;
    }> => {
      const formData = new FormData();
      if (file) {
        formData.append("file", file);
      }
      if (solutionText) {
        formData.append("solution_text", solutionText);
      }
      return request<any>(`/assignments/${assignmentId}/reference-solution`, {
        method: "POST",
        body: formData,
      });
    },
    // Upload batch submissions with roll-number matching table
    uploadBatchSubmissions: async (
      assignmentId: string,
      files: File[],
    ): Promise<{
      assignment_id: string;
      total_files: number;
      matched: Array<{ filename: string; file_size: number; student_id: string; student_name: string; student_roll: string; confidence: number }>;
      unmatched: Array<{ filename: string; file_size: number }>;
      duplicates: Array<{ filename: string; file_size: number; student_id: string; student_name: string; student_roll: string }>;
      roster: Array<{ id: string; name: string; roll: string }>;
    }> => {
      const formData = new FormData();
      for (const f of files) {
        formData.append("files", f);
      }
      return request<any>(`/assignments/${assignmentId}/submissions/upload-batch`, {
        method: "POST",
        body: formData,
      });
    },
    // Get live grading progress
    getGradingProgress: async (
      assignmentId: string,
    ): Promise<{
      assignment_id: string;
      status: string;
      total: number;
      processed: number;
      current_stage: string;
      progress_pct: number;
      eta_seconds: number;
      failed_count: number;
      errors: string[];
    }> => {
      return request<any>(`/assignments/${assignmentId}/grading-progress`);
    },
    // Cancel active grading job
    cancelGrading: async (assignmentId: string): Promise<any> => {
      return request<any>(`/assignments/${assignmentId}/cancel-grading`, {
        method: "POST",
      });
    },
    // Regrade single submission
    regradeSubmission: async (assignmentId: string, submissionId: string): Promise<any> => {
      return request<any>(`/assignments/${assignmentId}/regrade-submission/${submissionId}`, {
        method: "POST",
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
    parseRoster: async (
      classroomId: string,
      file: File,
    ): Promise<{
      status: string;
      filename: string;
      total_detected: number;
      students: Array<{ roll_number: string; full_name: string; email?: string | undefined }>;
    }> => {
      const formData = new FormData();
      formData.append("file", file);
      return request<{
        status: string;
        filename: string;
        total_detected: number;
        students: Array<{ roll_number: string; full_name: string; email?: string | undefined }>;
      }>(`/classrooms/${classroomId}/students/parse-roster`, {
        method: "POST",
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
    // Parse any rubric file format (PDF, DOCX, XLSX, TXT, CSV, images) with Gemini into matrix criteria
    parseRubricFile: async (file: File): Promise<{
      title: string;
      total_marks: number;
      criteria: Array<{
        criterion_name: string;
        description: string;
        weight: number;
        max_points: number;
        levels: Array<{ level_name: string; points: number; description: string }>;
      }>;
      extracted_text_preview: string;
    }> => {
      const formData = new FormData();
      formData.append("file", file);
      return request<any>("/rubrics/parse-rubric-file", {
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
  // Batch AI Evaluation with Academic Similarity Check
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
    // Retrieve pairwise similarity heatmap matrix
    getMatrix: async (assignmentId: string): Promise<{
      assignment_id: string;
      threshold: number;
      nodes: Array<{ id: string; name: string; roll: string; ai_prob: number }>;
      links: Array<{ source: string; target: string; source_name: string; target_name: string; similarity: number; status: string; matched_phrases: string[] }>;
      matrix: number[][];
    }> => {
      return request<any>(`/assignments/${assignmentId}/similarity-matrix`);
    },
    // Retrieve structured academic integrity case report
    getCaseReport: async (submissionId: string): Promise<any> => {
      return request<any>(`/submissions/${submissionId}/integrity-case-report`);
    },
    // Update integrity flag lifecycle status and teacher notes
    updateFlag: async (flagId: string, data: { status?: string; teacher_notes?: string }): Promise<any> => {
      return request<any>(`/similarity/flags/${flagId}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      });
    },
    // Trigger on-demand integrity scan across assignment
    runIntegrityCheck: async (assignmentId: string): Promise<any> => {
      return request<any>(`/assignments/${assignmentId}/run-integrity-check`, {
        method: "POST",
      });
    },
  },

  // ==========================================
  // Gradebook & Exports
  // ==========================================
  gradebook: {
    // Specify getCourseGradebook property (async (courseId: string): Promise<any> =>)
    getCourseGradebook: async (courseId: string): Promise<any> => {
      // Return value: request<any>(`/courses/${courseId}/gradebook`)
      return request<any>(`/courses/${courseId}/gradebook`);
    },
    // Generate CSV download link with UTF-8 BOM and formula injection defense
    getExportCsvUrl: (courseId: string, mode = "final", formatType = "default", assignmentId?: string): string => {
      const q = new URLSearchParams({ mode, format: formatType });
      if (assignmentId) q.append("assignment_id", assignmentId);
      return `${API_BASE_URL}/courses/${courseId}/export/csv?${q.toString()}`;
    },
    // Generate Excel XLSX download link with branded styling and number formatting
    getExportXlsxUrl: (courseId: string, mode = "final", assignmentId?: string): string => {
      const q = new URLSearchParams({ mode });
      if (assignmentId) q.append("assignment_id", assignmentId);
      return `${API_BASE_URL}/courses/${courseId}/export/xlsx?${q.toString()}`;
    },
    // Toggle auto-approval setting for high-confidence evaluations
    toggleAutoApprove: async (courseId: string, enabled: boolean): Promise<any> => {
      return request<any>(`/courses/${courseId}/settings/auto-approve?enabled=${enabled}`, {
        method: "POST",
      });
    },
  },

  // ==========================================
  // Analytics & Dashboard Reporting
  // ==========================================
  analytics: {
    // Fetch aggregated real analytics with 60s Redis caching
    get: async (params?: { course_id?: string; assignment_id?: string; date_range?: string }): Promise<any> => {
      const q = new URLSearchParams();
      if (params?.course_id) q.append("course_id", params.course_id);
      if (params?.assignment_id) q.append("assignment_id", params.assignment_id);
      if (params?.date_range) q.append("date_range", params.date_range);
      const queryStr = q.toString() ? `?${q.toString()}` : "";
      return request<any>(`/analytics${queryStr}`);
    },
    // Purge sandbox demo dataset and invalidate Redis cache
    clearDemo: async (): Promise<any> => {
      return request<any>("/analytics/demo-data", {
        method: "DELETE",
      });
    },
  },

  // ==========================================
  // 30-Day Trash Bin & Data Deletion
  // ==========================================
  trash: {
    // List all soft-deleted items across courses, assignments, submissions, students, rubrics
    list: async (): Promise<any> => {
      return request<any>("/trash");
    },
    // Restore soft-deleted item from trash bin
    restore: async (entityType: string, entityId: string): Promise<any> => {
      return request<any>(`/trash/restore/${entityType}/${entityId}`, {
        method: "POST",
      });
    },
    // Permanently purge item immediately, cascading through files and Redis
    permanentDelete: async (entityType: string, entityId: string): Promise<any> => {
      return request<any>(`/trash/permanent/${entityType}/${entityId}`, {
        method: "DELETE",
      });
    },
    // Soft-delete specific entity
    deleteCourse: async (id: string): Promise<any> => request<any>(`/courses/${id}`, { method: "DELETE" }),
    deleteAssignment: async (id: string): Promise<any> => request<any>(`/assignments/${id}`, { method: "DELETE" }),
    deleteSubmission: async (id: string): Promise<any> => request<any>(`/submissions/${id}`, { method: "DELETE" }),
    deleteStudent: async (id: string): Promise<any> => request<any>(`/students/${id}`, { method: "DELETE" }),
    deleteRubric: async (id: string): Promise<any> => request<any>(`/rubrics/${id}`, { method: "DELETE" }),
  },

  // ==========================================
  // Privacy & GDPR/DPDP Compliance
  // ==========================================
  privacy: {
    // URL to stream complete educator data ZIP archive
    getExportAllDataUrl: (): string => `${API_BASE_URL}/user/export-all-data`,
    // Retrieve privacy profile and processing activities
    getProfile: async (): Promise<any> => request<any>("/privacy/me"),
    // Submit formal GDPR Art. 17 / DPDP Sec. 12 erasure request
    submitErasureRequest: async (reason?: string): Promise<any> => {
      const q = reason ? `?reason=${encodeURIComponent(reason)}` : "";
      return request<any>(`/privacy/erasure-request${q}`, { method: "POST" });
    },
  },

  // ==========================================
  // Review Mode, Prompt Fixing & Teacher Start
  // ==========================================
  reviewMode: {
    /**
     * Fetch pre-flight check calculations and blocker validation before starting grading.
     *
     * @param {string} assignmentId - Unique identifier of the assignment.
     * @returns {Promise<any>} Pre-flight calculation summary including counts, duration, and token estimates.
     */
    // Define asynchronous method to fetch preflight grading check data
    getPreflight: async (assignmentId: string): Promise<any> => {
      // Execute GET request to preflight endpoint
      return request<any>(`/review-mode/preflight/${assignmentId}`);
    },

    /**
     * Start teacher-controlled grading execution immediately, on schedule, or as draft.
     *
     * @param {Object} data - Grading start parameters.
     * @returns {Promise<any>} Dispatch response containing run ID and execution status.
     */
    // Define asynchronous method to start teacher-controlled grading
    startGrading: async (data: {
      assignment_id?: string;
      scope?: string;
      filter_mode?: string;
      when?: string;
      scheduled_for?: string;
      timezone?: string;
      concurrency_limit?: number;
      max_cost_limit_usd?: number;
    }): Promise<any> => {
      // Execute POST request to start grading endpoint
      return request<any>("/review-mode/start-grading", {
        // Specify HTTP POST verb
        method: "POST",
        // Serialize request configuration payload
        body: JSON.stringify(data),
      });
    },

    /**
     * Retrieve all prompt versions associated with an assignment.
     *
     * @param {string} assignmentId - Unique identifier of the assignment.
     * @returns {Promise<any>} Array of versioned prompt records.
     */
    // Define asynchronous method to list prompt versions
    listPromptVersions: async (assignmentId: string): Promise<any> => {
      // Execute GET request to fetch prompt versions
      return request<any>(`/review-mode/assignments/${assignmentId}/prompt-versions`);
    },

    /**
     * Submit structured teacher feedback on AI grading mistakes to train meta-prompt fixes.
     *
     * @param {string} assignmentId - Unique identifier of the assignment.
     * @param {Object} data - Feedback categorization and explanation payload.
     * @returns {Promise<any>} Created feedback record.
     */
    // Define asynchronous method to submit teacher evaluation mistake feedback
    submitFeedback: async (
      assignmentId: string,
      data: {
        submission_id?: string;
        error_category: string;
        explanation: string;
        expected_behavior?: string;
      },
    ): Promise<any> => {
      // Execute POST request to submit error feedback
      return request<any>(`/review-mode/assignments/${assignmentId}/feedback`, {
        // Specify HTTP POST verb
        method: "POST",
        // Serialize feedback payload
        body: JSON.stringify(data),
      });
    },

    /**
     * Trigger Gemini meta-prompt assistant to analyze teacher feedback and propose prompt diffs.
     *
     * @param {string} assignmentId - Unique identifier of the assignment.
     * @param {string} [notes] - Optional teacher guidance or instructions.
     * @returns {Promise<any>} Proposed prompt version and unified diff.
     */
    // Define asynchronous method to request AI assistant prompt fix
    assistantFix: async (assignmentId: string, notes?: string): Promise<any> => {
      // Build query string parameter for teacher guidance notes
      const q = notes ? `?teacher_notes=${encodeURIComponent(notes)}` : "";
      // Execute POST request to assistant fix endpoint
      return request<any>(`/review-mode/assignments/${assignmentId}/assistant-fix${q}`, {
        // Specify HTTP POST verb
        method: "POST",
      });
    },

    /**
     * Run a non-destructive dry-run sandbox on sampled submissions using a revised prompt.
     *
     * @param {string} assignmentId - Unique identifier of the assignment.
     * @param {string} [promptText] - Prompt text candidate to benchmark.
     * @returns {Promise<any>} Dry run execution results with before/after score comparisons.
     */
    // Define asynchronous method to run non-destructive dry run
    dryRun: async (assignmentId: string, promptText?: string): Promise<any> => {
      // Execute POST request to trigger sandbox dry run
      return request<any>(`/review-mode/assignments/${assignmentId}/dry-run`, {
        // Specify HTTP POST verb
        method: "POST",
        // Serialize prompt text candidate payload
        body: JSON.stringify({ prompt_text: promptText }),
      });
    },

    /**
     * Override submission score with audit trail recording old score, new score, and rationale.
     *
     * @param {Object} data - Override parameters including submission ID, new score, and reason.
     * @returns {Promise<any>} Updated submission and audit history record.
     */
    // Define asynchronous method to execute teacher grade override
    overrideGrade: async (data: {
      submission_id: string;
      new_score: number;
      reason: string;
      teacher_feedback?: string;
      criteria_scores?: any[];
    }): Promise<any> => {
      // Execute POST request to grade override endpoint
      return request<any>("/review-mode/grade-override", {
        // Specify HTTP POST verb
        method: "POST",
        // Serialize grade override payload
        body: JSON.stringify(data),
      });
    },

    /**
     * Fetch immutable grade override audit history for a submission.
     *
     * @param {string} submissionId - Unique identifier of the submission.
     * @returns {Promise<any>} Audit trail history entries for the submission.
     */
    // Define asynchronous method to fetch submission grade audit history
    getGradeHistory: async (submissionId: string): Promise<any> => {
      // Execute GET request to fetch grade audit history
      return request<any>(`/review-mode/grade-history/${submissionId}`);
    },
  },

  // ==========================================
  // System Health & Diagnostics
  // ==========================================
  health: {
    /**
     * Check comprehensive backend system health (Database, Gemini, Storage).
     *
     * @returns {Promise<any>} Structured health report for all backend services.
     */
    // Asynchronous method to inspect full backend health
    check: async (): Promise<any> => {
      // Execute GET request to health check endpoint
      return request<any>("/health");
    },

    /**
     * Check primary PostgreSQL database connectivity and query latency.
     *
     * @returns {Promise<{ status: string; latency_ms?: number }>} Database health status.
     */
    // Asynchronous method to check database ping
    db: async (): Promise<{ status: string; latency_ms?: number }> => {
      // Execute GET request to database health endpoint
      return request<{ status: string; latency_ms?: number }>("/health/db");
    },
  },
};
