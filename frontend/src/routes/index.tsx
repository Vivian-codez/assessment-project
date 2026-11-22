import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import {
  Activity,
  ArrowLeft,
  ArrowRight,
  BarChart3,
  Bell,
  BookOpen,
  Check,
  CheckCircle2,
  ChevronDown,
  ClipboardCheck,
  ExternalLink,
  FileArchive,
  FileCode,
  FileText,
  Filter,
  FolderOpen,
  Globe,
  GraduationCap,
  LayoutDashboard,
  LogIn,
  LogOut,
  Menu,
  MoreHorizontal,
  Plus,
  RefreshCw,
  Search,
  Settings,
  ShieldAlert,
  SlidersHorizontal,
  Sparkles,
  Trash2,
  UploadCloud,
  UserPlus,
  Users,
  X,
  Edit3,
  Loader2,
  Download,
  FileSpreadsheet,
  TrendingUp,
  TrendingDown,
  Layers,
  AlertCircle,
  CheckSquare,
  History,
  RotateCcw,
  Lock,
  HelpCircle,
} from "lucide-react";
import { useState, useEffect, useRef } from "react";
import type { LucideIcon } from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip as RechartsTooltip,
  CartesianGrid,
  Cell,
} from "recharts";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Textarea } from "@/components/ui/textarea";
import { cn, pluralize } from "@/lib/utils";
import {
  api,
  getAuthToken,
  setAuthToken,
  clearAuthToken,
  getCachedUser,
  setCachedUser,
  type Course as APICourse,
  type Assignment as APIAssignment,
  type SubmissionItem,
  type SubmissionDetail,
  type UserProfile,
  type Rubric,
  type SimilarityMatch,
  type Classroom,
  type Student,
} from "@/lib/api";
import { RosterView } from "@/components/RosterView";
import { MatrixRubricBuilder } from "@/components/MatrixRubricBuilder";
import { RubricsListView } from "@/components/RubricsListView";
import { AssignmentWizardModal } from "@/components/AssignmentWizardModal";
import { StartGradingModal } from "@/components/StartGradingModal";
import { ReviewAssistantModal } from "@/components/ReviewAssistantModal";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Verism AI — Teacher Review & Auto-Grading Console" },
      {
        name: "description",
        content:
          "Authoritative, teacher-first workspace for automated rubric grading, reference assignment benchmarking, and academic similarity review.",
      },
      { property: "og:title", content: "Verism AI — Teacher Review & Auto-Grading Console" },
      { property: "og:type", content: "website" },
    ],
  }),
  component: VerismApp,
});

type ViewKey =
  | "dashboard"
  | "courses"
  | "roster"
  | "rubrics"
  | "rubric_builder"
  | "assignments"
  | "assessments"
  | "similarity"
  | "grading"
  | "review"
  | "gradebook"
  | "reports"
  | "settings";

function Pill({
  children,
  tone = "neutral",
}: {
  children: React.ReactNode;
  tone?: "neutral" | "lav" | "sage" | "clay" | "amber" | "blue";
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md px-2.5 py-1 text-[11px] font-medium",
        `tone-${tone}`,
      )}
    >
      {children}
    </span>
  );
}

function ProgressLine({
  value,
  tone = "lav",
}: {
  value: number;
  tone?: "lav" | "sage" | "clay" | "amber";
}) {
  return (
    <div className="h-1.5 overflow-hidden rounded-full bg-line">
      <div
        className={cn("progress-draw h-full rounded-full", `bar-${tone}`)}
        style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
      />
    </div>
  );
}

function SectionTitle({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="mb-7 flex flex-wrap items-end justify-between gap-4 animate-fade-up">
      <div>
        {eyebrow && (
          <p className="mb-2 text-[11px] uppercase tracking-[0.2em] text-faint">{eyebrow}</p>
        )}
        <h1 className="font-display text-3xl leading-tight tracking-tight text-ink sm:text-4xl">
          {title}
        </h1>
        {description && (
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted-ink">{description}</p>
        )}
      </div>
      {action}
    </div>
  );
}

export function VerismApp({ initialView = "dashboard" }: { initialView?: ViewKey } = {}) {
  const routerNavigate = useNavigate();
  const [view, setView] = useState<ViewKey>(initialView);
  const [mobileNav, setMobileNav] = useState(false);
  const [notifications, setNotifications] = useState(false);
  const [search, setSearch] = useState("");
  const [toast, setToast] = useState<{
    message: string;
    type?: "success" | "error" | "info" | "loading";
    retryAction?: () => void;
  } | null>(null);

  // Sidebar collapsible state
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  // Teacher-controlled grading start panel modal
  const [startGradingModalOpen, setStartGradingModalOpen] = useState(false);

  // Review mode assistant & prompt-fix modal
  const [reviewAssistantOpen, setReviewAssistantOpen] = useState(false);

  // Authentication State
  const [currentUser, setCurrentUser] = useState<UserProfile | null>(getCachedUser());
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [authTab, setAuthTab] = useState<"login" | "signup">("login");
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState("");

  // Live Backend Data States - Courses & Classrooms
  const [courses, setCourses] = useState<APICourse[]>([]);
  const [selectedCourseId, setSelectedCourseId] = useState<string>("");
  const [classrooms, setClassrooms] = useState<Classroom[]>([]);
  const [selectedClassroomId, setSelectedClassroomId] = useState<string>("");
  const [enrolledStudents, setEnrolledStudents] = useState<Student[]>([]);
  const [matrixRubrics, setMatrixRubrics] = useState<Rubric[]>([]);

  // Assignments & Submissions
  const [assignments, setAssignments] = useState<APIAssignment[]>([]);
  const [selectedAssignmentId, setSelectedAssignmentId] = useState<string>("");
  const [submissions, setSubmissions] = useState<SubmissionItem[]>([]);
  const [selectedSubmissionId, setSelectedSubmissionId] = useState<string>("");
  const [similarityMatches, setSimilarityMatches] = useState<SimilarityMatch[]>([]);
  const [loadingCourses, setLoadingCourses] = useState(true);

  // Dialog States
  const [addCourseOpen, setAddCourseOpen] = useState(false);
  const [addAssignmentOpen, setAddAssignmentOpen] = useState(false);
  const [manualSubmissionOpen, setManualSubmissionOpen] = useState(false);
  const [helpDrawerOpen, setHelpDrawerOpen] = useState(false);
  // Deletion Confirmation Modal State
  const [deletionModal, setDeletionModal] = useState<{
    type: "course" | "assignment" | "submission" | "all_submissions" | "mock_data";
    id: string;
    title: string;
    details?: string;
  } | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // Evaluation & Batch Job Polling
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingProgress, setProcessingProgress] = useState(0);
  const [processingAssignmentId, setProcessingAssignmentId] = useState<string>("");
  const [takingAssignment, setTakingAssignment] = useState(false);

  const showToast = (
    message: string,
    type?: "success" | "error" | "info" | "loading",
    retryAction?: () => void,
  ) => {
    // Automatically infer error type if message contains error or failure keywords and no explicit type was passed
    const inferredType =
      type ||
      (message.toLowerCase().includes("error") || message.toLowerCase().includes("failed")
        ? "error"
        : "success");
    setToast({ message, type: inferredType, retryAction });
    if (inferredType !== "loading") {
      window.setTimeout(() => setToast(null), 4000);
    }
  };

  // Initial Data Fetch & Auth Verification
  useEffect(() => {
    let mounted = true;
    const initAuthAndData = async () => {
      const token = getAuthToken();

      if (!token) {
        routerNavigate({ to: "/login" });
        return;
      }

      const authed = await loadUser();
      if (!authed) {
        clearAuthToken();
        setCurrentUser(null);
        routerNavigate({ to: "/login" });
        return;
      }

      if (mounted) {
        await Promise.all([loadCourses(), loadClassrooms(), loadRubrics()]);
      }
    };

    initAuthAndData();

    return () => {
      mounted = false;
    };
  }, []);

  const loadUser = async (): Promise<boolean> => {
    try {
      const user = await api.auth.getMe();
      setCurrentUser(user);
      return true;
    } catch {
      clearAuthToken();
      return false;
    }
  };

  const loadCourses = async () => {
    setLoadingCourses(true);
    try {
      const list = await api.courses.list();
      setCourses(list || []);
      if (list && list.length > 0 && list[0]) {
        const initialCourse = list[0];
        setSelectedCourseId(initialCourse.id);
        loadAssignments(initialCourse.id);
      }
    } catch (e: any) {
      console.warn("Could not load initial courses:", e?.message);
      if (getAuthToken()) {
        showToast(`Notice: ${e.message}`);
      }
    } finally {
      setLoadingCourses(false);
    }
  };

  const loadClassrooms = async () => {
    try {
      const cls = await api.classrooms.list();
      setClassrooms(cls || []);
      if (cls && cls.length > 0 && cls[0]) {
        const first = cls[0];
        setSelectedClassroomId((prev) => prev || first.id);
        loadStudents(selectedClassroomId || first.id);
        loadRubrics(selectedClassroomId || first.id);
      }
    } catch (e: any) {
      console.warn("Could not load classrooms:", e?.message);
    }
  };

  const loadStudents = async (classroomId: string) => {
    if (!classroomId) return;
    try {
      const studs = await api.classrooms.getStudents(classroomId);
      setEnrolledStudents(studs || []);
    } catch (e: any) {
      console.warn("Could not load students:", e?.message);
    }
  };

  const loadRubrics = async (classroomId?: string) => {
    try {
      const rub = await api.rubrics.list(classroomId);
      setMatrixRubrics(rub || []);
    } catch (e: any) {
      console.warn("Could not load rubrics:", e?.message);
    }
  };

  const checkActiveJob = async (assignId: string) => {
    if (!assignId) return;
    try {
      const job = await api.evaluations.getActiveJob(assignId);
      if (job && (job.status === "queued" || job.status === "processing")) {
        setIsProcessing(true);
        setProcessingAssignmentId(assignId);
        setProcessingProgress(Math.max(10, Math.round(job.progress_pct)));
        pollBatchJob(job.job_id, assignId);
      }
    } catch {
      // ignore
    }
  };

  const loadAssignments = async (courseId: string) => {
    try {
      const list = await api.assignments.listByCourse(courseId);
      setAssignments(list);
      if (list.length > 0 && list[0]) {
        const firstAssign = list[0];
        setSelectedAssignmentId(firstAssign.id);
        loadSubmissions(firstAssign.id);
        loadSimilarity(firstAssign.id);
        checkActiveJob(firstAssign.id);
      } else {
        setSelectedAssignmentId("");
        setSubmissions([]);
        setSimilarityMatches([]);
      }
    } catch (e: any) {
      console.error(e);
    }
  };

  const loadSubmissions = async (assignmentId?: string) => {
    const targetId = assignmentId || selectedAssignmentId;
    if (!targetId) return;
    try {
      const subs = await api.submissions.listByAssignment(targetId);
      setSubmissions(subs);
      if (subs.length > 0 && subs[0] && !selectedSubmissionId) {
        setSelectedSubmissionId(subs[0].id);
      }
    } catch (e: any) {
      console.error(e);
    }
  };

  const loadSimilarity = async (assignmentId: string) => {
    try {
      const matches = await api.similarity.listMatches(assignmentId);
      setSimilarityMatches(matches);
    } catch (e: any) {
      console.error(e);
    }
  };

  const handleSelectCourse = (courseId: string) => {
    setSelectedCourseId(courseId);
    setSelectedClassroomId(courseId);
    loadStudents(courseId);
    loadRubrics(courseId);
    loadAssignments(courseId);
  };

  const handleSelectAssignment = (assignId: string) => {
    setSelectedAssignmentId(assignId);
    loadSubmissions(assignId);
    loadSimilarity(assignId);
    checkActiveJob(assignId);
  };

  const navigate = (next: ViewKey) => {
    setView(next);
    setMobileNav(false);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const [editAssignmentOpen, setEditAssignmentOpen] = useState(false);

  const currentCourse: APICourse | null =
    courses.find((c) => c.id === selectedCourseId) ||
    (courses.length > 0 && courses[0] ? courses[0] : null);

  const currentClassroom: Classroom | null =
    classrooms.find((c) => c.id === selectedClassroomId) ||
    (classrooms.length > 0 ? classrooms[0] : null) ||
    (currentCourse
      ? {
          id: currentCourse.id,
          name: currentCourse.name,
          code: currentCourse.code,
          students_count: currentCourse.students_count || 0,
        }
      : null);

  const currentAssignment: APIAssignment | null =
    assignments.find((a) => a.id === selectedAssignmentId) ||
    (assignments.length > 0 && assignments[0] ? assignments[0] : null);

  const pendingCount = submissions.filter((s) => s.status === "graded").length;

  const handleSelectClassroom = (classroomId: string) => {
    setSelectedClassroomId(classroomId);
    setSelectedCourseId(classroomId);
    loadStudents(classroomId);
    loadRubrics(classroomId);
    loadAssignments(classroomId);
  };

  const handleLogout = async () => {
    try {
      await api.auth.logout();
    } catch {
      // ignore
    }
    clearAuthToken();
    setCurrentUser(null);
    showToast("Signed out successfully.");
    routerNavigate({ to: "/login" });
  };

  const handleDeleteCourse = (courseId: string) => {
    const c = courses.find((item) => item.id === courseId);
    setDeletionModal({
      type: "course",
      id: courseId,
      title: c ? `${c.code} · ${c.name}` : "Course",
      details:
        "All associated assignments, rubrics, and student submissions will be permanently deleted.",
    });
  };

  const handleDeleteAssignment = (assignId: string) => {
    const a = assignments.find((item) => item.id === assignId);
    setDeletionModal({
      type: "assignment",
      id: assignId,
      title: a ? a.title : "Assignment",
      details:
        "All student submissions and evaluation reports for this assessment will be removed.",
    });
  };

  const handleDeleteSubmission = (subId: string) => {
    const s = submissions.find((item) => item.id === subId);
    setDeletionModal({
      type: "submission",
      id: subId,
      title: s ? `${s.student} (${s.file_name})` : "Student Submission",
      details:
        "This student submission and its evaluation reports will be removed from the assignment.",
    });
  };

  const handleClearAllSubmissions = () => {
    if (!selectedAssignmentId) return;
    setDeletionModal({
      type: "all_submissions",
      id: selectedAssignmentId,
      title: "Clear All Submissions",
      details:
        "This will remove all uploaded student documents for this assignment to allow clean re-entry.",
    });
  };

  const handleClearMockData = () => {
    setDeletionModal({
      type: "mock_data",
      id: "mock_data",
      title: "Purge Sample Mock Data",
      details:
        "This will remove seeded sample mock courses and records to ensure a clean, custom database state.",
    });
  };

  const handleExecuteConfirmedDelete = async () => {
    if (!deletionModal) return;
    const { type, id, title } = deletionModal;
    setIsDeleting(true);

    try {
      if (type === "course") {
        await api.courses.delete(id);
        const remaining = courses.filter((c) => c.id !== id);
        setCourses(remaining);
        if (selectedCourseId === id) {
          if (remaining.length > 0 && remaining[0]) {
            setSelectedCourseId(remaining[0].id);
            loadAssignments(remaining[0].id);
          } else {
            setSelectedCourseId("");
            setAssignments([]);
            setSubmissions([]);
            setSimilarityMatches([]);
          }
        }
        showToast(`Course '${title}' deleted successfully.`);
      } else if (type === "assignment") {
        await api.assignments.delete(id);
        const remaining = assignments.filter((a) => a.id !== id);
        setAssignments(remaining);
        if (selectedAssignmentId === id) {
          if (remaining.length > 0 && remaining[0]) {
            setSelectedAssignmentId(remaining[0].id);
            loadSubmissions(remaining[0].id);
            loadSimilarity(remaining[0].id);
          } else {
            setSelectedAssignmentId("");
            setSubmissions([]);
            setSimilarityMatches([]);
          }
        }
        showToast(`Assignment '${title}' deleted.`);
      } else if (type === "submission") {
        await api.submissions.delete(id);
        const remaining = submissions.filter((s) => s.id !== id);
        setSubmissions(remaining);
        if (selectedSubmissionId === id) {
          setSelectedSubmissionId(remaining.length > 0 && remaining[0] ? remaining[0].id : "");
        }
        showToast(`Submission removed.`);
      } else if (type === "all_submissions") {
        await api.submissions.clearAll(id);
        setSubmissions([]);
        setSelectedSubmissionId("");
        setSimilarityMatches([]);
        showToast("All submissions cleared. Ready for your student data!");
      } else if (type === "mock_data") {
        const res = await api.auth.clearMockData();
        showToast(res.message || "Sample mock data purged.");
        await loadCourses();
      }
      setDeletionModal(null);
    } catch (e: any) {
      showToast(`Error deleting ${type}: ${e.message}`);
    } finally {
      setIsDeleting(false);
    }
  };

  const pollBatchJob = (jobId: string, targetId: string) => {
    let currentProg = 10;
    const pollTimer = window.setInterval(async () => {
      try {
        const status = await api.evaluations.pollJobStatus(jobId);
        if (status.progress_pct > currentProg) {
          currentProg = Math.max(currentProg, Math.round(status.progress_pct));
        } else if (currentProg < 92) {
          currentProg = Math.min(92, currentProg + 8);
        }
        setProcessingProgress(currentProg);

        if (status.status === "completed") {
          window.clearInterval(pollTimer);
          setProcessingProgress(100);
          setTimeout(async () => {
            setIsProcessing(false);
            setProcessingAssignmentId("");
            await loadSubmissions(targetId);
            await loadSimilarity(targetId);
            showToast(
              `Auto-grading complete: ${status.processed_items || "All"} submissions ready for review!`,
            );
          }, 600);
        } else if (status.status === "failed") {
          window.clearInterval(pollTimer);
          setIsProcessing(false);
          setProcessingAssignmentId("");
          showToast(`Evaluation failed: ${status.error_message || "Unknown error"}`);
        }
      } catch {
        // continue polling
      }
    }, 1200);
  };

  // Trigger Live AI Auto-Grading & Academic Similarity Review
  const startAIAutoGrading = async (assignId?: string) => {
    let targetId = assignId || selectedAssignmentId;
    if (!targetId && currentCourse) {
      const created = await handleTakeDefaultAssignment();
      if (created) {
        targetId = created.id;
      }
    }
    if (!targetId || isProcessing) return;
    setIsProcessing(true);
    setProcessingAssignmentId(targetId);
    setProcessingProgress(8);
    showToast("AI Auto-Grading & Academic Similarity Review initiated. Evaluation is in process...");

    try {
      const assignObj = assignments.find((a) => a.id === targetId) || currentAssignment;
      const job = await api.evaluations.triggerBatch(targetId, {
        similarity_threshold: 90.0,
        title: assignObj?.title,
        reference_assignment_text: assignObj?.reference_assignment_text,
        rubric_id: assignObj?.rubric_id,
      });

      pollBatchJob(job.job_id, targetId);
    } catch (e: any) {
      setIsProcessing(false);
      setProcessingAssignmentId("");
      showToast(`Error starting evaluation: ${e.message}`, "error");
    }
  };

  const handleTakeDefaultAssignment = async (): Promise<APIAssignment | null> => {
    if (!currentCourse) {
      showToast("Please select or create a course first.");
      return null;
    }
    setTakingAssignment(true);
    try {
      const title = `Assignment 1 · ${currentCourse.name || currentCourse.code} Submissions`;
      const created = await api.assignments.create(currentCourse.id, {
        title,
        description: `Student submissions and benchmark solutions for ${currentCourse.name || currentCourse.code}. Evaluated against university rubric with academic similarity review.`,
        max_score: 100,
        reference_assignment_text:
          "Benchmark Reference Solution: Students must implement accurate algorithmic models, clean functional modularity, robust boundary test coverage, and comprehensive runtime complexity analysis.",
      });
      setAssignments((prev) => {
        const exists = prev.some((a) => a.id === created.id);
        return exists ? prev : [...prev, created];
      });
      setSelectedAssignmentId(created.id);
      await loadSubmissions(created.id);
      await loadSimilarity(created.id);
      showToast(`Initialized and took "${created.title}". Ready for student submissions!`);
      return created;
    } catch (e: any) {
      showToast(`Error taking assignment: ${e.message}`);
      return null;
    } finally {
      setTakingAssignment(false);
    }
  };

  const handleOpenManualSubmission = async () => {
    if (!selectedAssignmentId) {
      const created = await handleTakeDefaultAssignment();
      if (!created) return;
    }
    setManualSubmissionOpen(true);
  };

  return (
    <div className="min-h-screen bg-paper font-sans text-ink antialiased">
      <div className="flex min-h-screen">
        <Sidebar
          active={view}
          onNavigate={navigate}
          mobileOpen={mobileNav}
          onClose={() => setMobileNav(false)}
          pendingCount={pendingCount}
          isProcessing={isProcessing}
          collapsed={sidebarCollapsed}
          onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
        />
        <div
          className={cn(
            "flex min-w-0 flex-1 flex-col transition-all duration-300",
            sidebarCollapsed ? "lg:ml-20" : "lg:ml-64",
          )}
        >
          <TopBar
            course={currentCourse}
            courses={courses}
            onSelectCourse={handleSelectCourse}
            onSelectSection={(sec) => {
              if (currentCourse) {
                setCourses((prev) =>
                  prev.map((c) => (c.id === currentCourse.id ? { ...c, section: sec } : c)),
                );
                showToast(`Switched to Section ${sec} for ${currentCourse.code}`);
              }
            }}
            onOpenAddCourse={() => setAddCourseOpen(true)}
            currentUser={currentUser}
            onOpenAuth={() => setAuthModalOpen(true)}
            onLogout={handleLogout}
            search={search}
            setSearch={setSearch}
            notifications={notifications}
            setNotifications={setNotifications}
            onMenu={() => setMobileNav(true)}
            isProcessing={isProcessing}
            processingProgress={processingProgress}
          />
          <main className="mx-auto w-full max-w-[1500px] flex-1 px-4 py-6 sm:px-6 sm:py-8">
            {view === "dashboard" && (
              <Dashboard
                course={currentCourse}
                courses={courses}
                classrooms={classrooms}
                students={enrolledStudents}
                rubrics={matrixRubrics}
                assignment={currentAssignment}
                assignments={assignments}
                submissions={submissions}
                pendingCount={pendingCount}
                onNavigate={navigate}
                onReview={(subId) => {
                  setSelectedSubmissionId(subId);
                  navigate("review");
                }}
                onOpenAddCourse={() => setAddCourseOpen(true)}
                onSelectCourse={handleSelectCourse}
                showToast={showToast}
                onRefreshData={async () => {
                  await Promise.all([loadCourses(), loadClassrooms()]);
                }}
              />
            )}
            {view === "roster" && (
              <RosterView
                classroom={currentClassroom}
                classrooms={
                  classrooms.length > 0
                    ? classrooms
                    : courses.map((c) => ({
                        id: c.id,
                        name: c.name,
                        code: c.code,
                        students_count: c.students_count || 0,
                      }))
                }
                onSelectClassroom={handleSelectClassroom}
                showToast={showToast}
              />
            )}
            {view === "rubric_builder" && (
              <MatrixRubricBuilder
                classroom={currentClassroom}
                classrooms={
                  classrooms.length > 0
                    ? classrooms
                    : courses.map((c) => ({
                        id: c.id,
                        name: c.name,
                        code: c.code,
                        students_count: c.students_count || 0,
                      }))
                }
                onSelectClassroom={handleSelectClassroom}
                onSaved={() => {
                  loadRubrics(currentClassroom?.id);
                  navigate("rubrics");
                }}
                onCancel={() => navigate("rubrics")}
                showToast={showToast}
              />
            )}
            {view === "rubrics" && (
              <RubricsListView
                classroom={currentClassroom}
                classrooms={
                  classrooms.length > 0
                    ? classrooms
                    : courses.map((c) => ({
                        id: c.id,
                        name: c.name,
                        code: c.code,
                        students_count: c.students_count || 0,
                      }))
                }
                onOpenCreateRubric={() => navigate("rubric_builder")}
                showToast={showToast}
              />
            )}
            {view === "courses" && (
              <CoursesView
                courses={courses}
                selectedCourseId={selectedCourseId}
                onSelectCourse={handleSelectCourse}
                onOpenAddCourse={() => setAddCourseOpen(true)}
                onDeleteCourse={handleDeleteCourse}
                onNavigate={navigate}
                search={search}
              />
            )}
            {view === "assignments" && (
              <AssignmentsView
                course={currentCourse}
                courses={courses}
                onSelectCourse={handleSelectCourse}
                rubrics={matrixRubrics}
                onReloadRubrics={() => loadRubrics(selectedCourseId || currentCourse?.id)}
                assignments={assignments}
                selectedAssignmentId={selectedAssignmentId}
                processingAssignmentId={processingAssignmentId}
                onSelectAssignment={handleSelectAssignment}
                onTakeDefaultAssignment={handleTakeDefaultAssignment}
                takingAssignment={takingAssignment}
                onOpenAddAssignment={() => setAddAssignmentOpen(true)}
                onOpenEditAssignment={() => setEditAssignmentOpen(true)}
                onDeleteAssignment={handleDeleteAssignment}
                onOpenManualSubmission={handleOpenManualSubmission}
                onDeleteSubmission={handleDeleteSubmission}
                onClearAllSubmissions={handleClearAllSubmissions}
                submissions={submissions}
                isProcessing={isProcessing}
                progress={processingProgress}
                onStartGrading={() => setStartGradingModalOpen(true)}
                onReloadSubmissions={loadSubmissions}
                onNavigate={navigate}
                showToast={showToast}
              />
            )}
            {view === "assessments" && (
              <AssessmentsView
                course={currentCourse}
                assignment={currentAssignment}
                onNavigate={navigate}
                showToast={showToast}
              />
            )}
            {view === "similarity" && (
              <SimilarityView
                matches={similarityMatches}
                submissions={submissions}
                onNavigate={navigate}
                showToast={showToast}
              />
            )}
            {view === "grading" && (
              <AIGradingView
                submissions={submissions}
                assignment={currentAssignment}
                isProcessing={isProcessing}
                progress={processingProgress}
                onStartGrading={() => setStartGradingModalOpen(true)}
                onReview={(subId) => {
                  setSelectedSubmissionId(subId);
                  navigate("review");
                }}
                onNavigate={navigate}
                showToast={showToast}
              />
            )}
            {view === "review" && (
              <ReviewWorkspace
                assignment={currentAssignment}
                submissions={submissions}
                selectedSubmissionId={selectedSubmissionId}
                onSelectSubmission={setSelectedSubmissionId}
                onGraded={() => loadSubmissions(selectedAssignmentId)}
                onOpenAssistant={() => setReviewAssistantOpen(true)}
                onNavigate={navigate}
                showToast={showToast}
              />
            )}
            {view === "gradebook" && (
              <GradebookView
                course={currentCourse}
                assignment={currentAssignment}
                submissions={submissions}
                students={enrolledStudents}
                showToast={showToast}
              />
            )}
            {view === "reports" && (
              <ReportsView course={currentCourse} submissions={submissions} showToast={showToast} />
            )}
            {view === "settings" && (
              <SettingsView
                currentUser={currentUser}
                onClearMockData={handleClearMockData}
                showToast={showToast}
              />
            )}
          </main>
        </div>
      </div>

      {/* Global Toast */}
      {toast && (
        <div
          role={toast.type === "error" ? "alert" : "status"}
          className={cn(
            "fixed bottom-5 left-1/2 z-50 flex -translate-x-1/2 items-center gap-2.5 rounded-xl px-4 py-3 text-xs font-medium shadow-2xl animate-fade-up max-w-md",
            toast.type === "error"
              ? "border border-destructive/30 bg-destructive/95 text-destructive-foreground"
              : toast.type === "loading"
                ? "border border-amber/30 bg-card text-foreground"
                : "border border-line bg-ink text-card",
          )}
        >
          {toast.type === "error" ? (
            <AlertCircle className="size-4 shrink-0 text-destructive-foreground" role="alert" />
          ) : toast.type === "loading" ? (
            <Loader2 className="size-4 shrink-0 animate-spin text-amber" />
          ) : (
            <CheckCircle2 className="size-4 shrink-0 text-sage" />
          )}
          <span className="flex-1 leading-snug">{toast.message}</span>
          {toast.type === "error" && toast.retryAction && (
            <button
              type="button"
              onClick={() => {
                const action = toast.retryAction;
                setToast(null);
                action?.();
              }}
              className="ml-2 rounded-md bg-white/20 px-2.5 py-1 text-[11px] font-bold text-white hover:bg-white/30 transition-colors"
            >
              Retry
            </button>
          )}
          <button
            type="button"
            onClick={() => setToast(null)}
            className="ml-1 text-white/60 hover:text-white"
          >
            <X className="size-3.5" />
          </button>
        </div>
      )}

      {/* Auth Modal (Sign-Up / Sign-In) */}
      {authModalOpen && (
        <AuthModal
          tab={authTab}
          setTab={setAuthTab}
          loading={authLoading}
          error={authError}
          onClose={() => {
            setAuthModalOpen(false);
            setAuthError("");
          }}
          onSuccess={(user) => {
            setCurrentUser(user);
            setAuthModalOpen(false);
            setAuthError("");
            showToast(`Welcome, ${user.name}!`);
            loadCourses();
          }}
          setLoading={setAuthLoading}
          setError={setAuthError}
        />
      )}

      {/* Add Course Modal */}
      {addCourseOpen && (
        <AddCourseModal
          onClose={() => setAddCourseOpen(false)}
          onCreated={(newCourse) => {
            setCourses([newCourse, ...courses]);
            setSelectedCourseId(newCourse.id);
            setAddCourseOpen(false);
            showToast(`Created course ${newCourse.code} · ${newCourse.name}`);
          }}
          showToast={showToast}
        />
      )}

      {/* Guided 4-Step Assignment Creation Wizard */}
      {addAssignmentOpen && (
        <AssignmentWizardModal
          courseId={selectedCourseId}
          onClose={() => setAddAssignmentOpen(false)}
          onCreated={(newAssign) => {
            setAssignments([newAssign, ...assignments]);
            setSelectedAssignmentId(newAssign.id);
            setAddAssignmentOpen(false);
            showToast(`Assignment "${newAssign.title}" created with rubric matrix & reference exemplar.`);
            loadSubmissions(newAssign.id);
          }}
          showToast={showToast}
        />
      )}

      {/* Quick Manual Submission Modal */}
      {manualSubmissionOpen && (
        <ManualSubmissionModal
          assignmentId={selectedAssignmentId}
          onClose={() => setManualSubmissionOpen(false)}
          onCreated={(newSub) => {
            setSubmissions([newSub, ...submissions]);
            setSelectedSubmissionId(newSub.id);
            setManualSubmissionOpen(false);
            showToast(`Submission added for ${newSub.student}.`);
          }}
          showToast={showToast}
        />
      )}

      {/* Edit Assignment & Benchmark Modal */}
      {editAssignmentOpen && currentAssignment && (
        <EditAssignmentModal
          assignment={currentAssignment}
          onClose={() => setEditAssignmentOpen(false)}
          onUpdated={(updated) => {
            setAssignments(assignments.map((a) => (a.id === updated.id ? updated : a)));
            setEditAssignmentOpen(false);
            showToast("Assignment & reference exemplar updated.");
          }}
          showToast={showToast}
        />
      )}

      {/* Teacher-Controlled AI Grading Start Modal */}
      {startGradingModalOpen && currentAssignment && (
        <StartGradingModal
          isOpen={startGradingModalOpen}
          onClose={() => setStartGradingModalOpen(false)}
          assignment={currentAssignment}
          course={currentCourse}
          submissions={submissions}
          onGradingStarted={(runData) => {
            setStartGradingModalOpen(false);
            if (runData?.run_id || runData?.job_id) {
              setProcessingAssignmentId(currentAssignment.id);
              setIsProcessing(true);
              setProcessingProgress(5);
              pollGradingJob(runData.run_id || runData.job_id, currentAssignment.id);
            }
          }}
          showToast={showToast}
        />
      )}

      {/* Prompt-Fix Review Assistant Modal */}
      {reviewAssistantOpen && currentAssignment && (
        <ReviewAssistantModal
          isOpen={reviewAssistantOpen}
          onClose={() => setReviewAssistantOpen(false)}
          assignment={currentAssignment}
          submission={submissions.find((s) => s.id === selectedSubmissionId) as any}
          showToast={showToast}
          onPromptUpdated={() => {
            loadSubmissions(currentAssignment.id);
          }}
        />
      )}

      {/* Reusable Deletion Confirmation Modal */}
      {deletionModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 animate-fade-in">
          <div className="w-full max-w-md rounded-2xl border border-line bg-card p-6 shadow-2xl animate-scale-in">
            <div className="flex items-center gap-3">
              <div className="grid size-10 place-items-center rounded-full bg-destructive/10 text-destructive">
                <Trash2 className="size-5" />
              </div>
              <div>
                <h3 className="font-display text-lg font-semibold text-foreground">
                  Confirm Deletion
                </h3>
                <p className="text-xs text-muted-foreground capitalize">
                  {deletionModal.type.replace("_", " ")} Removal
                </p>
              </div>
            </div>

            <div className="mt-4 rounded-lg bg-muted/40 p-3.5 text-xs text-foreground/90 space-y-1">
              <p className="font-semibold text-foreground">{deletionModal.title}</p>
              {deletionModal.details && (
                <p className="text-muted-foreground text-[11px] leading-relaxed">
                  {deletionModal.details}
                </p>
              )}
            </div>

            <p className="mt-3 text-[11px] text-muted-foreground">
              This operation cannot be undone. Are you sure you want to proceed?
            </p>

            <div className="mt-6 flex justify-end gap-2 border-t border-line pt-4">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setDeletionModal(null)}
                disabled={isDeleting}
                className="text-xs"
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={handleExecuteConfirmedDelete}
                disabled={isDeleting}
                className="text-xs"
              >
                {isDeleting ? (
                  <>
                    <Loader2 className="mr-1.5 size-3.5 animate-spin" /> Deleting...
                  </>
                ) : (
                  <>
                    <Trash2 className="mr-1.5 size-3.5" /> Confirm Delete
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Global Accessible Help Floating Trigger */}
      <button
        type="button"
        onClick={() => setHelpDrawerOpen(true)}
        className="fixed bottom-5 right-5 z-40 flex items-center gap-1.5 rounded-full bg-ink px-3.5 py-2 text-xs font-semibold text-card shadow-lg hover:shadow-xl hover:bg-ink/90 transition-all focus:outline-none focus:ring-2 focus:ring-ring cursor-pointer"
        title="Open Help & Keyboard Shortcuts"
      >
        <HelpCircle className="size-4 text-amber-ink" />
        <span>Help & Shortcuts</span>
      </button>

      {/* Global Slide-Over Help Drawer */}
      <HelpDrawer open={helpDrawerOpen} onClose={() => setHelpDrawerOpen(false)} />
    </div>
  );
}

/**
 * Interface definition for HelpDrawer component properties.
 */
interface HelpDrawerProps {
  // Boolean flag controlling whether the drawer slide-over modal is open
  open: boolean;
  // Callback invoked when the user requests closing the drawer (via Esc, backdrop, or close button)
  onClose: () => void;
}

/**
 * Global slide-over help drawer providing educator documentation, keyboard shortcuts,
 * and support contact information. Follows ARIA dialog best practices.
 *
 * @param props - Object containing open state and onClose handler
 * @returns React JSX element rendering accessible drawer or null
 */
function HelpDrawer({ open, onClose }: HelpDrawerProps) {
  // Return null immediately if drawer is not open to avoid unnecessary DOM nodes
  if (!open) return null;

  // Render modal backdrop overlay and slide-over panel
  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Help and Keyboard Shortcuts"
      className="fixed inset-0 z-50 flex justify-end bg-black/40 backdrop-blur-xs transition-opacity animate-fade-in"
      onClick={onClose}
    >
      <div
        className="h-full w-full max-w-md bg-card p-6 shadow-2xl overflow-y-auto border-l border-line animate-slide-left text-ink"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Drawer Header */}
        <div className="flex items-center justify-between border-b border-line pb-4">
          <div className="flex items-center gap-2">
            <div className="grid size-8 place-items-center rounded-lg bg-lav-soft text-amber-ink">
              <HelpCircle className="size-5" />
            </div>
            <div>
              <h2 className="font-display text-lg font-bold">Help & Shortcuts</h2>
              <p className="text-xs text-muted-ink">Teacher Quick-Reference Guide</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-muted-ink hover:bg-paper hover:text-ink transition-colors cursor-pointer"
            title="Close help drawer (Esc)"
            aria-label="Close help drawer"
          >
            <X className="size-5" />
          </button>
        </div>

        {/* Core Educator Philosophy */}
        <div className="mt-5 rounded-xl border border-amber/30 bg-amber-soft/50 p-4 text-xs leading-relaxed">
          <span className="font-semibold text-amber-ink block mb-1">Guiding Principle:</span>
          <p className="text-muted-ink">
            &ldquo;AI suggests. You stamp. Every grade waits for your approval.&rdquo; Grading never executes without your explicit command, and AI drafts are never published to students until you review and stamp them.
          </p>
        </div>

        {/* Keyboard Shortcuts Table */}
        <div className="mt-6">
          <h3 className="font-display text-sm font-semibold mb-3">Keyboard Shortcuts</h3>
          <div className="space-y-2 text-xs">
            <div className="flex items-center justify-between rounded-lg border border-line bg-paper px-3 py-2">
              <span className="text-muted-ink">Toggle Help Drawer</span>
              <kbd className="rounded border border-line bg-card px-2 py-0.5 font-mono text-[11px] font-bold">?</kbd>
            </div>
            <div className="flex items-center justify-between rounded-lg border border-line bg-paper px-3 py-2">
              <span className="text-muted-ink">Close Modal / Drawer</span>
              <kbd className="rounded border border-line bg-card px-2 py-0.5 font-mono text-[11px] font-bold">Esc</kbd>
            </div>
            <div className="flex items-center justify-between rounded-lg border border-line bg-paper px-3 py-2">
              <span className="text-muted-ink">Next Submission (Review Queue)</span>
              <kbd className="rounded border border-line bg-card px-2 py-0.5 font-mono text-[11px] font-bold">J</kbd>
            </div>
            <div className="flex items-center justify-between rounded-lg border border-line bg-paper px-3 py-2">
              <span className="text-muted-ink">Previous Submission (Review Queue)</span>
              <kbd className="rounded border border-line bg-card px-2 py-0.5 font-mono text-[11px] font-bold">K</kbd>
            </div>
            <div className="flex items-center justify-between rounded-lg border border-line bg-paper px-3 py-2">
              <span className="text-muted-ink">Approve Grade (Review Queue)</span>
              <kbd className="rounded border border-line bg-card px-2 py-0.5 font-mono text-[11px] font-bold">A</kbd>
            </div>
          </div>
        </div>

        {/* Workflow Steps Guide */}
        <div className="mt-6">
          <h3 className="font-display text-sm font-semibold mb-3">Educator Workflow</h3>
          <ol className="space-y-2 text-xs text-muted-ink list-decimal list-inside leading-relaxed">
            <li><strong className="text-ink">Create Course:</strong> Add your course code and section title.</li>
            <li><strong className="text-ink">Enroll Students:</strong> Import CSV roster or add student roll numbers.</li>
            <li><strong className="text-ink">Assignment & Rubric:</strong> Define criteria weights or reference solutions.</li>
            <li><strong className="text-ink">Upload Submissions:</strong> Upload files; all submissions enter &ldquo;ready&rdquo; status.</li>
            <li><strong className="text-ink">Trigger Grading:</strong> Open Start Grading panel to trigger batch evaluation.</li>
            <li><strong className="text-ink">Review & Stamp:</strong> Inspect criterion breakdown and approve or override.</li>
          </ol>
        </div>

        {/* Support & Documentation Links */}
        <div className="mt-6 border-t border-line pt-4 text-xs">
          <p className="text-muted-ink">
            Need assistance or found an edge case?
          </p>
          <div className="mt-2 flex gap-3">
            <a
              href="mailto:support@verism.ai"
              className="font-medium text-amber-ink hover:underline"
            >
              support@verism.ai
            </a>
            <span className="text-faint">·</span>
            <span className="text-faint">Version 2.4.0 (Single-Teacher Edition)</span>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Interface definition for GettingStartedChecklist component properties.
 */
interface GettingStartedChecklistProps {
  // Count of configured courses
  coursesCount: number;
  // Count of enrolled students
  studentsCount: number;
  // Count of assignments created
  assignmentsCount: number;
  // Count of rubrics configured
  rubricsCount: number;
  // Count of submissions uploaded
  submissionsCount: number;
  // Count of approved or graded submissions
  gradedCount: number;
  // Navigation callback
  onNavigate: (view: ViewKey) => void;
  // Callback to trigger course creation modal
  onOpenAddCourse: () => void;
}

/**
 * GettingStartedChecklist guides a new educator through the 5 essential steps
 * to grade their first assignment. It tracks real database entities and hides
 * automatically or when dismissed.
 *
 * @param props - Component properties containing entity counts and action handlers
 * @returns React JSX element rendering progress checklist or null
 */
function GettingStartedChecklist({
  coursesCount,
  studentsCount,
  assignmentsCount,
  rubricsCount,
  submissionsCount,
  gradedCount,
  onNavigate,
  onOpenAddCourse,
}: GettingStartedChecklistProps) {
  // Local state to allow teacher to dismiss the onboarding guide
  const [dismissed, setDismissed] = useState(false);

  // Define the 5 discrete onboarding milestones
  const steps = [
    {
      id: "course",
      title: "Create your first course",
      done: coursesCount > 0,
      actionLabel: "Create Course",
      action: onOpenAddCourse,
    },
    {
      id: "students",
      title: "Enroll students in roll call",
      done: studentsCount > 0,
      actionLabel: "Enroll Students",
      action: () => onNavigate("roster"),
    },
    {
      id: "rubric",
      title: "Set up assignment & rubric",
      done: assignmentsCount > 0 && rubricsCount > 0,
      actionLabel: "Setup Rubric",
      action: () => onNavigate("rubrics"),
    },
    {
      id: "submissions",
      title: "Upload student submissions",
      done: submissionsCount > 0,
      actionLabel: "Upload Files",
      action: () => onNavigate("assignments"),
    },
    {
      id: "grade",
      title: "Start grading & stamp first review",
      done: gradedCount > 0,
      actionLabel: "Start Grading",
      action: () => onNavigate("grading"),
    },
  ];

  // Calculate completed step count
  const completedCount = steps.filter((s) => s.done).length;
  // Calculate completion percentage
  const percentComplete = Math.round((completedCount / steps.length) * 100);

  // If dismissed or all 5 steps complete, hide the checklist
  if (dismissed || completedCount === steps.length) {
    return null;
  }

  return (
    <div className="mb-6 rounded-[14px] border border-amber/30 bg-card p-5 shadow-sm animate-fade-up">
      {/* Header and dismiss control */}
      <div className="flex items-center justify-between pb-3 border-b border-line">
        <div className="flex items-center gap-2.5">
          <div className="grid size-7 place-items-center rounded-lg bg-amber-soft text-amber-ink font-bold text-xs">
            {completedCount}/{steps.length}
          </div>
          <div>
            <h2 className="font-display text-base font-semibold text-ink">Getting Started with Verism AI</h2>
            <p className="text-xs text-muted-ink">
              Follow these {steps.length} steps to set up your grading pipeline. ({percentComplete}% complete)
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => setDismissed(true)}
          className="text-xs text-muted-ink hover:text-ink transition-colors px-2 py-1 rounded cursor-pointer"
          title="Dismiss getting started checklist"
        >
          Dismiss
        </button>
      </div>

      {/* Progress Bar */}
      <div className="mt-3.5 h-1.5 w-full rounded-full bg-paper overflow-hidden">
        <div
          className="h-full bg-amber-ink transition-all duration-300"
          style={{ width: `${percentComplete}%` }}
        />
      </div>

      {/* Steps List */}
      <div className="mt-4 grid gap-2.5 sm:grid-cols-2 lg:grid-cols-5">
        {steps.map((step, idx) => (
          <div
            key={step.id}
            className={cn(
              "flex flex-col justify-between rounded-xl border p-3 text-xs transition-colors",
              step.done
                ? "border-sage/40 bg-sage-soft/30 text-muted-ink"
                : "border-line bg-paper text-ink"
            )}
          >
            <div>
              <div className="flex items-center gap-1.5">
                {step.done ? (
                  <CheckCircle2 className="size-4 text-sage shrink-0" />
                ) : (
                  <div className="grid size-4 place-items-center rounded-full border border-line text-[10px] font-bold text-faint">
                    {idx + 1}
                  </div>
                )}
                <span className={cn("font-medium", step.done && "line-through text-faint")}>
                  {step.title}
                </span>
              </div>
            </div>
            {!step.done && (
              <Button
                variant="outline"
                size="sm"
                onClick={step.action}
                className="mt-3 w-full border-line text-xs font-semibold hover:bg-card"
              >
                {step.actionLabel}
              </Button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// =========================================================================
// Sidebar & TopBar
// =========================================================================

const navSections: {
  label: string;
  items: { key: ViewKey; label: string; icon: LucideIcon; count?: number }[];
}[] = [
  {
    label: "Workspace",
    items: [
      { key: "dashboard", label: "Dashboard", icon: LayoutDashboard },
      { key: "courses", label: "Courses", icon: BookOpen },
      { key: "roster", label: "Students", icon: Users },
      { key: "assignments", label: "Assignments", icon: FolderOpen },
      { key: "rubrics", label: "Rubrics", icon: ClipboardCheck },
    ],
  },
  {
    label: "Grading",
    items: [
      { key: "grading", label: "Grading", icon: Sparkles },
      { key: "review", label: "Review Queue", icon: CheckCircle2 },
      { key: "gradebook", label: "Gradebook", icon: BarChart3 },
    ],
  },
  {
    label: "Insights",
    items: [
      { key: "similarity", label: "Integrity", icon: ShieldAlert },
    ],
  },
  {
    label: "Account",
    items: [
      { key: "settings", label: "Settings", icon: Settings },
    ],
  },
];

function Sidebar({
  active,
  onNavigate,
  mobileOpen,
  onClose,
  pendingCount,
  isProcessing = false,
  collapsed = false,
  onToggleCollapse,
}: {
  active: ViewKey;
  onNavigate: (view: ViewKey) => void;
  mobileOpen: boolean;
  onClose: () => void;
  pendingCount: number;
  isProcessing?: boolean;
  collapsed?: boolean;
  onToggleCollapse?: () => void;
}) {
  return (
    <>
      {mobileOpen && (
        <button
          aria-label="Close navigation"
          className="fixed inset-0 z-30 bg-ink/20 lg:hidden"
          onClick={onClose}
        />
      )}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex shrink-0 flex-col border-r border-line bg-card py-6 transition-all duration-300 lg:translate-x-0",
          collapsed ? "w-20 px-2.5" : "w-64 px-5",
          mobileOpen ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="flex items-center gap-2.5 px-1">
          <div className="grid size-8 shrink-0 place-items-center rounded-[7px] bg-ink text-card">
            <span className="font-display text-base leading-none">V</span>
          </div>
          {!collapsed && (
            <div className="leading-tight min-w-0 flex-1 truncate">
              <p className="text-[13px] font-semibold tracking-tight truncate">Verism AI</p>
              <p className="mt-0.5 text-[10px] uppercase tracking-[0.18em] text-faint truncate">
                Teacher Review
              </p>
            </div>
          )}
          <button
            type="button"
            onClick={onToggleCollapse}
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            className={cn(
              "hidden lg:grid size-7 place-items-center rounded-md border border-line text-muted-ink hover:text-ink hover:bg-paper transition-colors",
              collapsed && "mx-auto mt-2",
            )}
          >
            {collapsed ? <ArrowRight className="size-3.5" /> : <ArrowLeft className="size-3.5" />}
          </button>
          <Button
            size="icon"
            variant="ghost"
            className="ml-auto text-muted-ink lg:hidden"
            onClick={onClose}
          >
            <X />
          </Button>
        </div>
        <nav className="mt-6 space-y-0.5 text-[13px] overflow-y-auto pr-1">
          {navSections.map((section) => (
            <div key={section.label} className="mb-4">
              {!collapsed && (
                <div className="mb-1.5 px-3 text-[10px] uppercase tracking-[0.16em] text-faint truncate">
                  {section.label}
                </div>
              )}
              {section.items.map((item) => {
                const Icon = item.icon;
                const isActive = active === item.key;
                return (
                  <Button
                    key={item.key}
                    variant="ghost"
                    onClick={() => onNavigate(item.key)}
                    title={item.label}
                    className={cn(
                      "flex h-9 w-full rounded-lg font-normal text-muted-ink hover:bg-paper hover:text-ink transition-colors",
                      collapsed ? "justify-center px-0" : "justify-start gap-3 px-3",
                      isActive && "bg-lav-soft font-medium text-ink hover:bg-lav-soft",
                    )}
                  >
                    <Icon className={cn("size-4 shrink-0", isActive ? "text-amber-ink" : "text-faint")} />
                    {!collapsed && <span className="truncate">{item.label}</span>}
                    {item.key === "assignments" && isProcessing && (
                      <span className={cn(
                        "inline-flex items-center gap-1 rounded-full bg-amber-soft text-[9px] font-bold text-amber-ink animate-pulse",
                        collapsed ? "absolute -top-1 -right-1 size-2 rounded-full bg-amber" : "ml-auto px-1.5 py-0.5"
                      )}>
                        {!collapsed && <Loader2 className="size-2.5 animate-spin" />}
                        {!collapsed && "Auditing"}
                      </span>
                    )}
                    {item.key === "review" && pendingCount > 0 && (
                      <span className={cn(
                        "rounded-full bg-lav text-[10px] text-card",
                        collapsed ? "absolute -top-1 -right-1 size-4 grid place-items-center text-[9px]" : "ml-auto px-1.5 py-0.5"
                      )}>
                        {pendingCount}
                      </span>
                    )}
                  </Button>
                );
              })}
            </div>
          ))}
        </nav>
        {!collapsed && (
          <div className="mt-auto rounded-[10px] border border-line bg-paper px-3 py-3">
            <p className="text-[11px] leading-snug text-muted-ink">
              AI suggests. <span className="font-medium text-ink">You stamp.</span>
            </p>
            <p className="mt-1 text-[10px] leading-relaxed text-faint">
              Every grade waits for your direct approval.
            </p>
          </div>
        )}
      </aside>
    </>
  );
}

function TopBar({
  course,
  courses,
  onSelectCourse,
  onSelectSection,
  onOpenAddCourse,
  currentUser,
  onOpenAuth,
  onLogout,
  search,
  setSearch,
  notifications,
  setNotifications,
  onMenu,
  isProcessing = false,
  processingProgress = 0,
}: {
  course: APICourse | null;
  courses: APICourse[];
  onSelectCourse: (id: string) => void;
  onSelectSection?: (section: string) => void;
  onOpenAddCourse?: () => void;
  currentUser: UserProfile | null;
  onOpenAuth: () => void;
  onLogout: () => void;
  search: string;
  setSearch: (value: string) => void;
  notifications: boolean;
  setNotifications: (value: boolean) => void;
  onMenu: () => void;
  isProcessing?: boolean;
  processingProgress?: number;
}) {
  return (
    <header className="sticky top-0 z-20 flex items-center gap-3 border-b border-line bg-paper/90 px-4 py-3 backdrop-blur sm:px-6">
      <Button size="icon" variant="ghost" className="text-muted-ink lg:hidden" onClick={onMenu}>
        <Menu />
      </Button>
      {courses.length > 0 ? (
        <div className="flex items-center gap-1.5 sm:gap-2 text-xs sm:text-[13px] shrink-0">
          {/* Combined Course & Section Switcher */}
          <div className="relative max-w-xs">
            <select
              value={course?.id || ""}
              onChange={(e) => {
                if (e.target.value === "__new__") {
                  onOpenAddCourse?.();
                } else {
                  onSelectCourse(e.target.value);
                }
              }}
              className="appearance-none rounded-md border border-line bg-card py-1.5 pl-2.5 sm:pl-3 pr-7 sm:pr-8 text-xs font-semibold text-ink cursor-pointer hover:border-ink/50 focus:outline-none focus:ring-1 focus:ring-ink transition-colors shadow-2xs truncate max-w-[140px] sm:max-w-[240px]"
              title="Switch Active Course & Section"
            >
              {courses.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.code} · {c.name} ({c.section ? `Sec ${c.section}` : "Sec A"})
                </option>
              ))}
              <option value="__new__">+ Add New Course...</option>
            </select>
            <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted-ink" />
          </div>

          {isProcessing && (
            <span className="hidden sm:inline-flex items-center gap-1.5 rounded-full border border-amber/40 bg-amber-soft px-2.5 py-1 text-xs font-semibold text-amber-ink animate-pulse shadow-xs">
              <Loader2 className="size-3 animate-spin" />
              In Process ({processingProgress}%)
            </span>
          )}
        </div>
      ) : (
        <div className="flex items-center gap-2 text-xs sm:text-[13px] shrink-0">
          <Button
            size="sm"
            variant="outline"
            onClick={onOpenAddCourse}
            className="text-xs h-7 gap-1.5 border-line text-muted-ink"
          >
            <Plus className="size-3 text-amber-ink" /> Create Course
          </Button>
        </div>
      )}
      <div className="relative flex w-full max-w-[130px] sm:max-w-xs md:max-w-sm items-center gap-2 rounded-lg border border-line bg-card px-2.5 sm:px-3 py-1 sm:py-1.5 text-muted-ink">
        <Search className="size-4 text-faint" />
        <Input
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search students, submissions… (Press /)"
          className="h-7 border-0 bg-transparent p-0 text-sm shadow-none focus-visible:ring-0"
        />
        <kbd className="hidden sm:inline-block rounded border border-line bg-paper px-1.5 py-0.5 text-[10px] font-semibold text-faint shadow-2xs">
          /
        </kbd>
      </div>
      <div className="ml-auto flex items-center gap-2 sm:gap-3">
        {currentUser ? (
          <div className="flex items-center gap-2">
            <div className="grid size-8 place-items-center rounded-full bg-lav-soft text-[11px] font-semibold text-ink">
              {(currentUser.name || "Teacher")
                .split(" ")
                .map((n) => n[0])
                .join("")
                .substring(0, 2)
                .toUpperCase()}
            </div>
            <div className="hidden text-left leading-tight sm:block">
              <p className="text-[12px] font-semibold text-ink truncate max-w-[120px]">
                {currentUser.name || "Teacher"}
              </p>
              <p className="text-[10px] text-faint">{currentUser.role || "Instructor"}</p>
            </div>
            <Button
              size="icon"
              variant="ghost"
              title="Sign out"
              onClick={onLogout}
              className="text-muted-ink hover:text-clay"
            >
              <LogOut className="size-4" />
            </Button>
          </div>
        ) : (
          <Button
            size="sm"
            onClick={onOpenAuth}
            className="rounded-lg bg-ink text-card hover:bg-ink/90"
          >
            <LogIn className="mr-1.5 size-3.5" />
            Sign In / Sign Up
          </Button>
        )}
      </div>
    </header>
  );
}

// =========================================================================
// Dashboard View
// =========================================================================

// =========================================================================
// Dashboard View - Fully Connected Real-Time Analytics & Sellable Console
// =========================================================================

/**
 * Props definition for the Educator Analytics Dashboard component.
 */
interface DashboardProps {
  /** Active selected course object from database */
  course: APICourse | null;
  /** Full list of enrolled courses */
  courses: APICourse[];
  /** Roster classrooms list */
  classrooms: Classroom[];
  /** Enrolled student roster list */
  students: Student[];
  /** Configured evaluation rubrics list */
  rubrics: Rubric[];
  /** Currently selected assignment object */
  assignment: APIAssignment | null;
  /** All assignments configured for course */
  assignments: APIAssignment[];
  /** Submissions list belonging to active assignment */
  submissions: SubmissionItem[];
  /** Count of submissions awaiting teacher review */
  pendingCount: number;
  /** View router navigation callback */
  onNavigate: (view: ViewKey) => void;
  /** Callback to open review queue for specific submission */
  onReview: (id: string) => void;
  /** Modal opener callback to add new course */
  onOpenAddCourse: () => void;
  /** Switcher callback when selecting different course */
  onSelectCourse: (id: string) => void;
  /** Toast alert emitter function */
  showToast: (msg: string) => void;
  /** Data refresh callback to trigger parent query invalidation */
  onRefreshData?: () => Promise<void> | void;
}

/**
 * Real-Time Educator Analytics Dashboard Component.
 *
 * Provides a sellable, interactive console consuming real SQL aggregations
 * cached via Redis:
 * - 4 Key Performance Indicator (KPI) metric cards with percentage trends
 * - Grade Distribution Histogram (5 buckets) rendered with Recharts
 * - Longitudinal Assignment Performance Trend lines (mean & median)
 * - Criterion Skill Gap Heatmap highlighting struggling topics
 * - 4-stage Submission Pipeline Funnel (Submitted -> Parsed -> Evaluated -> Approved)
 * - Top Performers & Bottom Performers / Struggling Student rosters
 * - Actionable "Needs Attention" alert cards with one-click jump buttons
 * - Quick Action Buttons: Sandbox Demo Data Loader & Purger
 * - Comprehensive Empty States guiding initial setup
 */
function Dashboard({
  course,
  courses,
  classrooms,
  students,
  rubrics,
  assignment,
  assignments,
  submissions,
  pendingCount,
  onNavigate,
  onReview,
  onOpenAddCourse,
  onSelectCourse,
  showToast,
  onRefreshData,
}: DashboardProps) {
  // Local state holding the live aggregated analytics response from /api/v1/analytics
  const [analytics, setAnalytics] = useState<any>(null);
  // Loading boolean spinner indicator during analytics network fetch
  const [loadingAnalytics, setLoadingAnalytics] = useState(false);
  // Selected date-range window filter ('all' | '7d' | '30d' | '90d')
  const [dateRange, setDateRange] = useState<"all" | "7d" | "30d" | "90d">("all");
  // Optional assignment filter identifier within the active course
  const [filterAssignmentId, setFilterAssignmentId] = useState<string>(assignment?.id || "");
  // Loading indicator for demo data load/clear operations
  const [demoActionLoading, setDemoActionLoading] = useState(false);

  // Synchronize local filterAssignmentId when parent assignment changes
  useEffect(() => {
    // Check if parent assignment ID is defined
    if (assignment?.id) {
      // Set local filter assignment ID
      setFilterAssignmentId(assignment.id);
    }
  }, [assignment?.id]);

  // Effect hook to fetch live SQL analytics whenever course, assignment filter, or date range changes
  useEffect(() => {
    // Active flag to prevent state updates on unmounted component
    let active = true;
    // Set loading indicator
    setLoadingAnalytics(true);

    // Call API client analytics getter with active query parameters
    api.analytics
      .get({
        course_id: course?.id,
        assignment_id: filterAssignmentId || undefined,
        date_range: dateRange,
      })
      .then((data) => {
        // Update analytics state if component is still mounted
        if (active && data) {
          setAnalytics(data);
        }
      })
      .catch((err) => {
        // Log error notice to browser console
        console.warn("Analytics fetch notice:", err);
      })
      .finally(() => {
        // Clear loading spinner if component is mounted
        if (active) {
          setLoadingAnalytics(false);
        }
      });

    // Cleanup function setting active flag false
    return () => {
      active = false;
    };
  }, [course?.id, filterAssignmentId, dateRange]);

  // Handler function loading Sandbox Demo Data into the database
  const handleLoadDemoData = async () => {
    // Set loading flag
    setDemoActionLoading(true);
    try {
      // Invoke backend POST /api/v1/analytics/demo-data endpoint
      await api.analytics.loadDemo();
      // Show user notification toast
      showToast("Demo sandbox dataset loaded successfully (10 students, rubrics, 2 assignments).");
      // Trigger parent data refresh to pull newly seeded course and students
      if (onRefreshData) {
        await onRefreshData();
      }
      // Re-fetch analytics immediately
      const freshAnalytics = await api.analytics.get({
        course_id: "CS101-SANDBOX",
        date_range: dateRange,
      });
      // Set fresh analytics state
      setAnalytics(freshAnalytics);
      // Select the demo sandbox course
      onSelectCourse("CS101-SANDBOX");
    } catch (err: any) {
      // Show error toast message
      showToast(`Demo load error: ${err?.message || "Failed to seed demo data"}`);
    } finally {
      // Clear demo action loading flag
      setDemoActionLoading(false);
    }
  };

  // Handler function purging Sandbox Demo Data from the database
  const handleClearDemoData = async () => {
    // Set loading flag
    setDemoActionLoading(true);
    try {
      // Invoke backend DELETE /api/v1/analytics/demo-data endpoint
      await api.analytics.clearDemo();
      // Show confirmation toast
      showToast("Sandbox demo dataset cleared successfully.");
      // Trigger parent refresh
      if (onRefreshData) {
        await onRefreshData();
      }
      // Clear local analytics state
      setAnalytics(null);
    } catch (err: any) {
      // Show error toast message
      showToast(`Demo clear error: ${err?.message || "Failed to purge demo data"}`);
    } finally {
      // Clear loading indicator
      setDemoActionLoading(false);
    }
  };

  // Inspect empty state condition when no courses exist or analytics reports empty
  const isWorkspaceEmpty = (!course && courses.length === 0 && classrooms.length === 0) || (analytics && analytics.is_empty);

  // If workspace is completely empty, render sellable onboarding and demo loader view
  if (isWorkspaceEmpty && !loadingAnalytics) {
    return (
      <div className="mx-auto max-w-4xl py-12 text-center animate-fade-up">
        {/* Onboarding Icon container */}
        <div className="mx-auto grid size-16 place-items-center rounded-2xl bg-lav-soft text-ink mb-6 shadow-sm">
          <GraduationCap className="size-8 text-amber-ink" />
        </div>
        {/* Eyebrow badge */}
        <p className="text-xs uppercase tracking-[0.2em] text-faint mb-2">
          Verism AI · Teacher-First Auto-Grading & Integrity SaaS
        </p>
        {/* Main welcome headline */}
        <h1 className="font-display text-4xl text-ink">Welcome to Your Educator Workspace</h1>
        {/* Philosophy subtitle */}
        <p className="mx-auto mt-3 max-w-xl text-sm leading-relaxed text-muted-ink">
          "AI suggests. You stamp. Every grade waits for your approval." Experience fast, rubric-based
          evaluation, reference benchmarking, and academic similarity review with zero mock data.
        </p>
        {/* Primary CTA Buttons */}
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          {/* Quick Sandbox Demo Data Loader */}
          <Button
            onClick={handleLoadDemoData}
            disabled={demoActionLoading}
            size="lg"
            className="bg-amber-ink text-white hover:bg-amber-ink/90 rounded-xl px-5 shadow-sm"
          >
            {demoActionLoading ? (
              <Loader2 className="mr-2 size-4 animate-spin" />
            ) : (
              <Sparkles className="mr-2 size-4" />
            )}
            Load Sandbox Demo Dataset (1-Click)
          </Button>
          {/* Add Course Button */}
          <Button
            onClick={onOpenAddCourse}
            size="lg"
            className="bg-ink text-card hover:bg-ink/90 rounded-xl px-5"
          >
            <Plus className="mr-2 size-4" />
            Create Your First Course
          </Button>
          {/* Enroll Student Button */}
          <Button
            onClick={() => onNavigate("roster")}
            size="lg"
            variant="outline"
            className="rounded-xl px-5 border-line"
          >
            <Users className="mr-2 size-4 text-amber-ink" />
            Enroll Students
          </Button>
        </div>

        {/* 3 Value Pillars */}
        <div className="mt-12 grid gap-4 text-left sm:grid-cols-3">
          <div className="rounded-[14px] border border-line bg-card p-5">
            <div className="grid size-9 place-items-center rounded-lg bg-lav-soft text-ink mb-3 font-semibold">
              1
            </div>
            <h3 className="font-display text-lg">Multi-Format Ingestion</h3>
            <p className="mt-1 text-xs text-muted-ink">
              Upload PDF, DOCX, Python, C++, Java, or multi-submission ZIP packages with automatic student roll extraction.
            </p>
          </div>
          <div className="rounded-[14px] border border-line bg-card p-5">
            <div className="grid size-9 place-items-center rounded-lg bg-sage-soft text-sage mb-3 font-semibold">
              2
            </div>
            <h3 className="font-display text-lg">Rubric & Benchmarking</h3>
            <p className="mt-1 text-xs text-muted-ink">
              Upload your own rubric or reference solution. Gemini grades against criteria with pure-Python exact arithmetic.
            </p>
          </div>
          <div className="rounded-[14px] border border-line bg-card p-5">
            <div className="grid size-9 place-items-center rounded-lg bg-amber-soft text-amber-ink mb-3 font-semibold">
              3
            </div>
            <h3 className="font-display text-lg">Academic Integrity & Export</h3>
            <p className="mt-1 text-xs text-muted-ink">
              Winnowing AST peer comparison, AI indicator scoring, and RFC-4180 CSV / XLSX gradebook export.
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Active display name and code
  const activeClassName = course?.name || classrooms[0]?.name || "Active Course";
  const activeClassCode = course?.code || classrooms[0]?.code || "CLASS";

  // KPI card items from live analytics or fallback to current counts
  const avgKpi = analytics?.kpi_cards?.average_score || {
    label: "Class Average Score",
    value:
      submissions.length > 0 && submissions.some((s) => s.score !== null && s.score !== undefined)
        ? `${Math.round(
            submissions
              .filter((s) => s.score !== null && s.score !== undefined)
              .reduce((acc, s) => acc + (s.score || 0), 0) /
              Math.max(1, submissions.filter((s) => s.score !== null && s.score !== undefined).length)
          )}%`
        : "—",
    subtitle: submissions.length > 0 ? "Across graded submissions" : "No graded submissions yet",
    trend: submissions.length > 0 ? "+0.0% vs prior" : undefined,
    trend_direction: "neutral",
    tone: "lav",
  };
  const pendingKpi = analytics?.kpi_cards?.pending_reviews || {
    label: "Pending Reviews",
    value: `${pendingCount}`,
    subtitle: "Awaiting teacher approval stamp",
    trend: pendingCount > 0 ? `${pendingCount} actionable` : "All reviewed",
    trend_direction: pendingCount > 0 ? "negative" : "positive",
    tone: "amber",
  };
  const simKpi = analytics?.kpi_cards?.similarity_flags || {
    label: "Similarity Risk Flags",
    value: submissions.length > 0 ? `${submissions.filter((s) => (s.similarity || 0) >= 85).length}` : "—",
    subtitle: submissions.length > 0 ? ">= 85% pairwise collision" : "No submissions evaluated",
    trend: submissions.length > 0 ? "Peer winnowing audit" : undefined,
    trend_direction: "neutral",
    tone: "clay",
  };
  const onTimeKpi = analytics?.kpi_cards?.on_time_rate || {
    label: "On-Time Submission Rate",
    value:
      analytics?.on_time_stats?.on_time_rate !== undefined && analytics?.on_time_stats?.on_time_rate !== null
        ? `${analytics.on_time_stats.on_time_rate}%`
        : submissions.length > 0
          ? "100%"
          : "—",
    subtitle: submissions.length > 0 ? "Submitted prior to deadline" : "No submissions received",
    trend: submissions.length > 0 ? "+0.0% on-time" : undefined,
    trend_direction: "positive",
    tone: "sage",
  };

  return (
    <>
      {/* Dashboard Header with Course Filter, Date Range Window, and Quick Actions */}
      <SectionTitle
        eyebrow="Teacher Console · Real-Time Analytics"
        title={`Dashboard · ${activeClassName}`}
        description="Live SQL-aggregated performance metrics, score distributions, and integrity alerts. AI suggests. You stamp."
        action={
          <div className="flex flex-wrap items-center gap-2.5">
            {/* Course Selector Dropdown */}
            {courses.length > 0 && (
              <div className="flex items-center gap-2 rounded-lg border border-line bg-card px-3 py-1.5 shadow-2xs">
                <BookOpen className="size-4 text-amber-ink" />
                <span className="text-xs font-semibold text-muted-ink">Course:</span>
                <select
                  value={course?.id || ""}
                  onChange={(e) => onSelectCourse(e.target.value)}
                  className="bg-transparent text-xs font-medium text-ink focus:outline-none cursor-pointer"
                >
                  {courses.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.code} · {c.name}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Assignment Filter Dropdown */}
            {assignments.length > 0 && (
              <div className="flex items-center gap-2 rounded-lg border border-line bg-card px-3 py-1.5 shadow-2xs">
                <Filter className="size-3.5 text-muted-ink" />
                <span className="text-xs font-semibold text-muted-ink">Assignment:</span>
                <select
                  value={filterAssignmentId}
                  onChange={(e) => setFilterAssignmentId(e.target.value)}
                  className="bg-transparent text-xs font-medium text-ink focus:outline-none cursor-pointer"
                >
                  <option value="">All Assignments</option>
                  {assignments.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.title}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Date Range Segmented Control */}
            <div className="flex items-center rounded-lg border border-line bg-paper p-0.5 text-xs font-medium">
              {(["all", "7d", "30d", "90d"] as const).map((r) => (
                <button
                  key={r}
                  type="button"
                  onClick={() => setDateRange(r)}
                  className={cn(
                    "rounded-md px-2.5 py-1 text-xs transition-colors",
                    dateRange === r
                      ? "bg-ink text-white font-semibold shadow-2xs"
                      : "text-muted-ink hover:text-ink"
                  )}
                >
                  {r === "all" ? "All Time" : r.toUpperCase()}
                </button>
              ))}
            </div>

            {/* Demo Data Quick Buttons */}
            {course?.id === "CS101-SANDBOX" ? (
              <Button
                variant="outline"
                size="sm"
                onClick={handleClearDemoData}
                disabled={demoActionLoading}
                className="text-xs border-line text-clay hover:bg-clay-soft"
                title="Purge Sandbox demo data"
              >
                {demoActionLoading ? <Loader2 className="size-3 animate-spin" /> : <Trash2 className="size-3" />}
                Clear Demo Data
              </Button>
            ) : (
              <Button
                variant="outline"
                size="sm"
                onClick={handleLoadDemoData}
                disabled={demoActionLoading}
                className="text-xs border-line text-amber-ink hover:bg-amber-soft"
                title="Load 10 demo submissions, rubrics, and similarity matches into sandbox"
              >
                {demoActionLoading ? <Loader2 className="size-3 animate-spin" /> : <Sparkles className="size-3" />}
                Load Demo Data
              </Button>
            )}

            {/* Manage Submissions Navigation */}
            <Button
              onClick={() => onNavigate("assignments")}
              className="rounded-lg bg-ink text-card hover:bg-ink/90 text-xs"
            >
              <UploadCloud className="mr-1.5 size-3.5" />
              Manage Submissions
            </Button>
          </div>
        }
      />

      {/* Teacher Onboarding & Milestone Progress Checklist */}
      <GettingStartedChecklist
        coursesCount={courses.length}
        studentsCount={students.length}
        assignmentsCount={assignments.length}
        rubricsCount={rubrics.length}
        submissionsCount={submissions.length}
        gradedCount={submissions.filter((s) => s.status === "approved" || s.status === "graded").length}
        onNavigate={onNavigate}
        onOpenAddCourse={onOpenAddCourse}
      />

      {/* 4 Primary KPI Cards with Metric Values, Subtitles, and Trends */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[avgKpi, pendingKpi, simKpi, onTimeKpi].map((kpi, idx) => (
          <div
            key={kpi.label || idx}
            className="rounded-[14px] border border-line bg-card p-5 shadow-2xs transition-shadow hover:shadow-xs"
          >
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-ink">
                {kpi.label}
              </span>
              <div className={cn("size-2.5 rounded-full", `dot-${kpi.tone || "lav"}`)} />
            </div>
            <div className="mt-2 flex items-baseline justify-between">
              <p className="font-display text-3xl font-bold text-ink">{kpi.value}</p>
              {kpi.trend && (
                <span
                  className={cn(
                    "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold",
                    kpi.trend_direction === "positive"
                      ? "bg-sage-soft text-sage"
                      : kpi.trend_direction === "negative"
                      ? "bg-clay-soft text-clay"
                      : "bg-lav-soft text-ink"
                  )}
                >
                  {kpi.trend_direction === "positive" ? (
                    <TrendingUp className="size-3" />
                  ) : kpi.trend_direction === "negative" ? (
                    <TrendingDown className="size-3" />
                  ) : null}
                  {kpi.trend}
                </span>
              )}
            </div>
            <p className="mt-1 text-xs text-faint">{kpi.subtitle}</p>
          </div>
        ))}
      </div>

      {/* Charts Section: Grade Histogram & Longitudinal Trends */}
      <div className="mt-6 grid gap-5 xl:grid-cols-12">
        {/* Grade Distribution Histogram */}
        <div className="rounded-[14px] border border-line bg-card p-5 xl:col-span-7">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-display text-lg">Grade Distribution (5-Bucket Histogram)</h2>
              <p className="mt-1 text-xs text-muted-ink">
                Aggregated student marks distributed across letter-grade bands.
              </p>
            </div>
            <span className="text-xs font-medium text-faint">
              {analytics?.grade_distribution
                ? `${analytics.grade_distribution.reduce((acc: number, b: any) => acc + b.count, 0)} Graded`
                : `${submissions.length} Total`}
            </span>
          </div>

          <div className="mt-4 h-[240px] w-full">
            {analytics?.grade_distribution && analytics.grade_distribution.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={analytics.grade_distribution} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.25} />
                  <XAxis dataKey="bucket" tick={{ fontSize: 11 }} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                  <RechartsTooltip
                    formatter={(val: any) => [`${val} students`, "Count"]}
                    contentStyle={{ borderRadius: "8px", fontSize: "12px", border: "1px solid #e2e8f0" }}
                  />
                  <Bar dataKey="count" radius={[5, 5, 0, 0]} name="Students">
                    {analytics.grade_distribution.map((entry: any, index: number) => (
                      <Cell
                        key={`bar-${index}`}
                        fill={
                          entry.bucket.startsWith("90")
                            ? "#10b981"
                            : entry.bucket.startsWith("0")
                            ? "#ef4444"
                            : "#6366f1"
                        }
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="grid h-full place-items-center rounded-lg border border-dashed border-line text-xs text-faint">
                Upload student submissions to generate grade distribution histogram.
              </div>
            )}
          </div>
        </div>

        {/* Longitudinal Assignment Performance Trends */}
        <div className="rounded-[14px] border border-line bg-card p-5 xl:col-span-5">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-display text-lg">Assignment Trends</h2>
              <p className="mt-1 text-xs text-muted-ink">
                Mean and median trajectory across cohorts.
              </p>
            </div>
            <div className="flex items-center gap-3 text-[11px] font-medium text-muted-ink">
              <span className="flex items-center gap-1">
                <span className="size-2 rounded-full bg-indigo-600" /> Average
              </span>
              <span className="flex items-center gap-1">
                <span className="size-2 rounded-full bg-emerald-500" /> Median
              </span>
            </div>
          </div>

          <div className="mt-4 h-[240px] w-full">
            {analytics?.assignment_trends && analytics.assignment_trends.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={analytics.assignment_trends} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" opacity={0.25} />
                  <XAxis dataKey="assignment_title" tick={{ fontSize: 11 }} />
                  <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
                  <RechartsTooltip
                    formatter={(val: any) => [`${val}%`, "Score"]}
                    contentStyle={{ borderRadius: "8px", fontSize: "12px", border: "1px solid #e2e8f0" }}
                  />
                  <Line type="monotone" dataKey="average_score" stroke="#4f46e5" strokeWidth={2.5} dot={{ r: 4 }} name="Average" />
                  <Line type="monotone" dataKey="median_score" stroke="#10b981" strokeWidth={2} strokeDasharray="4 4" dot={{ r: 3 }} name="Median" />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="grid h-full place-items-center rounded-lg border border-dashed border-line text-xs text-faint">
                Multiple assignments required to render longitudinal performance curve.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 2-Column Section: Criterion Skill Gaps Heatmap & Submission Pipeline Funnel */}
      <div className="mt-5 grid gap-5 xl:grid-cols-12">
        {/* Criterion Skill Gaps Heatmap */}
        <div className="rounded-[14px] border border-line bg-card p-5 xl:col-span-7">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-display text-lg">Criterion Skill Gaps</h2>
              <p className="mt-1 text-xs text-muted-ink">
                Average score percentage per rubric criterion. Identifies learning weaknesses.
              </p>
            </div>
            <span className="text-[11px] font-semibold text-clay">
              Red bars = Weak areas (&lt; 70%)
            </span>
          </div>

          <div className="mt-4 h-[220px] w-full">
            {analytics?.criterion_averages && analytics.criterion_averages.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  layout="vertical"
                  data={analytics.criterion_averages}
                  margin={{ top: 5, right: 20, left: 10, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" opacity={0.25} horizontal={false} />
                  <XAxis type="number" domain={[0, 100]} unit="%" tick={{ fontSize: 10 }} />
                  <YAxis type="category" dataKey="criterion_name" width={140} tick={{ fontSize: 10 }} />
                  <RechartsTooltip
                    formatter={(val: any) => [`${val}%`, "Average"]}
                    contentStyle={{ borderRadius: "8px", fontSize: "12px", border: "1px solid #e2e8f0" }}
                  />
                  <Bar dataKey="average_percentage" radius={[0, 4, 4, 0]} name="Score %">
                    {analytics.criterion_averages.map((entry: any, index: number) => (
                      <Cell
                        key={`crit-${index}`}
                        fill={entry.average_percentage < 70 ? "#e06c75" : "#4f46e5"}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="grid h-full place-items-center rounded-lg border border-dashed border-line text-xs text-faint">
                Configure rubric criteria to surface skill gaps and learning bottlenecks.
              </div>
            )}
          </div>
        </div>

        {/* Submission Pipeline Funnel */}
        <div className="rounded-[14px] border border-line bg-card p-5 xl:col-span-5">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-display text-lg">Submission Pipeline Funnel</h2>
              <p className="mt-1 text-xs text-muted-ink">
                Conversion stages from student upload to stamped grade.
              </p>
            </div>
            <span className="text-xs font-semibold text-sage">
              {analytics?.submission_funnel?.[3]?.conversion_percentage || 0}% Approved
            </span>
          </div>

          <div className="mt-5 space-y-3.5">
            {(analytics?.submission_funnel || [
              { stage: "Uploaded Submissions", count: submissions.length, conversion_percentage: 100 },
              { stage: "Text Extracted & OCR", count: submissions.length, conversion_percentage: 100 },
              { stage: "AI Evaluated (Drafts)", count: submissions.filter((s) => s.status !== "unprocessed").length, conversion_percentage: 80 },
              { stage: "Teacher Approved (Final)", count: submissions.filter((s) => s.status === "approved").length, conversion_percentage: 40 },
            ]).map((stage: any, index: number) => (
              <div key={stage.stage} className="space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-medium text-ink flex items-center gap-1.5">
                    <span className="grid size-4 place-items-center rounded-full bg-lav-soft text-[10px] font-semibold text-ink">
                      {index + 1}
                    </span>
                    {stage.stage}
                  </span>
                  <span className="font-semibold text-muted-ink">
                    {stage.count} ({stage.conversion_percentage}%)
                  </span>
                </div>
                <div className="h-2 w-full overflow-hidden rounded-full bg-line/60">
                  <div
                    className={cn(
                      "h-full rounded-full transition-all duration-500",
                      index === 3 ? "bg-sage" : index === 2 ? "bg-lav" : "bg-ink"
                    )}
                    style={{ width: `${Math.min(100, Math.max(0, stage.conversion_percentage))}%` }}
                  />
                </div>
              </div>
            ))}
          </div>

          <div className="mt-5 rounded-lg border border-line bg-paper p-3 text-[11px] leading-relaxed text-faint">
            <p className="flex items-center gap-1.5 font-medium text-ink">
              <CheckCircle2 className="size-3.5 text-sage" /> Teacher Approval Authority
            </p>
            Verism AI never automatically writes final grades without your explicit stamp. AI suggestions remain drafts until approved.
          </div>
        </div>
      </div>

      {/* Actionable Alerts ("Needs Attention") & Roster Performance */}
      <div className="mt-5 grid gap-5 xl:grid-cols-12">
        {/* Needs Attention Actionable Cards */}
        <div className="rounded-[14px] border border-line bg-card p-5 xl:col-span-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertCircle className="size-5 text-amber-ink" />
              <h2 className="font-display text-lg">Action Items · Needs Attention</h2>
            </div>
            <span className="text-xs font-medium text-muted-ink">
              {analytics?.needs_attention?.length || 0} active notices
            </span>
          </div>

          <div className="mt-4 space-y-3">
            {analytics?.needs_attention && analytics.needs_attention.length > 0 ? (
              analytics.needs_attention.map((alert: any) => (
                <div
                  key={alert.id}
                  className={cn(
                    "flex items-center justify-between gap-3 rounded-lg border p-3.5 transition-colors",
                    alert.severity === "danger"
                      ? "border-clay/30 bg-clay-soft/40"
                      : alert.severity === "warning"
                      ? "border-amber/30 bg-amber-soft/40"
                      : "border-line bg-paper"
                  )}
                >
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-semibold text-ink">{alert.title}</p>
                    <p className="mt-0.5 text-[11px] text-muted-ink">{alert.description}</p>
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    className="shrink-0 text-xs border-line bg-card hover:bg-card/90"
                    onClick={() => {
                      if (alert.action_target) {
                        onNavigate(alert.action_target as ViewKey);
                      }
                    }}
                  >
                    {alert.action_label} <ArrowRight className="ml-1 size-3" />
                  </Button>
                </div>
              ))
            ) : (
              <div className="rounded-lg border border-line bg-paper p-6 text-center text-xs text-muted-ink">
                <CheckCircle2 className="mx-auto size-6 text-sage mb-2" />
                All active assignments and submissions are healthy. No immediate alerts.
              </div>
            )}
          </div>
        </div>

        {/* Top & Struggling Performers */}
        <div className="rounded-[14px] border border-line bg-card p-5 xl:col-span-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Users className="size-5 text-indigo-600" />
              <h2 className="font-display text-lg">Cohort Roster Insights</h2>
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="text-xs text-amber-ink"
              onClick={() => onNavigate("gradebook")}
            >
              Open Gradebook <ArrowRight className="ml-1 size-3" />
            </Button>
          </div>

          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            {/* Top Performers */}
            <div className="rounded-lg border border-line bg-paper p-3.5">
              <p className="text-xs font-semibold text-sage flex items-center gap-1.5 mb-2.5">
                <TrendingUp className="size-3.5" /> Top Performers
              </p>
              {analytics?.top_performers && analytics.top_performers.length > 0 ? (
                <div className="space-y-2 text-xs">
                  {analytics.top_performers.slice(0, 4).map((p: any) => (
                    <div key={p.student_roll} className="flex items-center justify-between">
                      <span className="truncate max-w-[120px] font-medium text-ink">
                        {p.student_name}
                      </span>
                      <span className="font-semibold text-sage">{p.average_score}%</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-[11px] text-faint">Awaiting graded submissions</p>
              )}
            </div>

            {/* Bottom Performers / Needs Help */}
            <div className="rounded-lg border border-line bg-paper p-3.5">
              <p className="text-xs font-semibold text-clay flex items-center gap-1.5 mb-2.5">
                <TrendingDown className="size-3.5" /> Needs Assistance
              </p>
              {analytics?.bottom_performers && analytics.bottom_performers.length > 0 ? (
                <div className="space-y-2 text-xs">
                  {analytics.bottom_performers.slice(0, 4).map((p: any) => (
                    <div key={p.student_roll} className="flex items-center justify-between">
                      <span className="truncate max-w-[120px] font-medium text-ink">
                        {p.student_name}
                      </span>
                      <span className="font-semibold text-clay">{p.average_score}%</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-[11px] text-faint">No struggling students identified</p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Pending Student Reviews Quick Queue */}
      <div className="mt-5 rounded-[14px] border border-line bg-card p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="font-display text-lg">Pending Student Reviews</h2>
            <p className="mt-1 text-xs text-muted-ink">
              Submissions waiting for teacher review and grading stamp.
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={() => onNavigate("review")} className="text-xs">
            Open Review Workspace <ArrowRight className="ml-1 size-3.5" />
          </Button>
        </div>

        {submissions.length === 0 ? (
          <div className="mt-6 rounded-lg border border-dashed border-line p-8 text-center">
            <FolderOpen className="mx-auto size-8 text-faint" />
            <p className="mt-2 font-display text-base text-ink">
              No submissions in this assignment yet
            </p>
            <p className="mt-1 text-xs text-muted-ink">
              Upload PDF, DOCX, or code files to begin automated evaluation.
            </p>
            <Button
              size="sm"
              onClick={() => onNavigate("assignments")}
              className="mt-4 bg-ink text-card hover:bg-ink/90 text-xs"
            >
              Go to Assignments & Upload
            </Button>
          </div>
        ) : (
          <div className="mt-4 grid gap-3 sm:grid-cols-2 md:grid-cols-3">
            {submissions.slice(0, 6).map((item) => (
              <div key={item.id} className="rounded-[10px] border border-line bg-paper p-4 shadow-2xs">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs font-semibold text-ink truncate">{item.student}</span>
                  <Pill
                    tone={
                      item.status === "approved"
                        ? "sage"
                        : item.status === "flagged"
                        ? "clay"
                        : "lav"
                    }
                  >
                    {item.status === "approved"
                      ? "Approved"
                      : item.status === "flagged"
                      ? "Flagged"
                      : "Pending"}
                  </Pill>
                </div>
                <div className="mt-2 space-y-1 text-xs text-muted-ink">
                  <p>Roll: <span className="font-medium text-ink">{item.roll}</span></p>
                  <p>
                    AI Suggested: <span className="font-semibold text-ink">{item.score}/100</span>
                  </p>
                  <div className="flex items-center gap-2 pt-1 text-[10px]">
                    <span className={item.similarity >= 85 ? "text-clay font-medium" : "text-faint"}>
                      Peer: {item.similarity}%
                    </span>
                    <span>·</span>
                    <span className={item.aiContent >= 60 ? "text-amber-ink font-medium" : "text-faint"}>
                      AI: {item.aiContent}%
                    </span>
                    <span>·</span>
                    <span className={(item.webPlagiarism || 0) >= 20 ? "text-blue font-medium" : "text-faint"}>
                      Web: {item.webPlagiarism !== null && item.webPlagiarism !== undefined ? `${item.webPlagiarism}%` : "—"}
                    </span>
                  </div>
                </div>
                <Button
                  size="sm"
                  className="mt-3 w-full bg-ink text-card hover:bg-ink/90 text-xs"
                  onClick={() => onReview(item.id)}
                >
                  Review Submission
                </Button>
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  );
}

// =========================================================================
// Courses Management View
// =========================================================================

function CoursesView({
  courses,
  selectedCourseId,
  onSelectCourse,
  onOpenAddCourse,
  onDeleteCourse,
  onNavigate,
  search,
}: {
  courses: APICourse[];
  selectedCourseId: string;
  onSelectCourse: (id: string) => void;
  onOpenAddCourse: () => void;
  onDeleteCourse: (id: string) => void;
  onNavigate: (view: ViewKey) => void;
  search: string;
}) {
  const filtered = courses.filter((c) =>
    `${c.name} ${c.code} ${c.section || ""}`.toLowerCase().includes(search.toLowerCase()),
  );

  return (
    <>
      <SectionTitle
        eyebrow="Workspace · Course Management"
        title="My Courses"
        description="Every assignment, grading rubric, reference benchmark, and submission is organized cleanly by course."
        action={
          <Button onClick={onOpenAddCourse} className="rounded-lg bg-ink text-card hover:bg-ink/90">
            <Plus className="mr-1.5 size-4" />
            Add Course
          </Button>
        }
      />

      {courses.length === 0 ? (
        <div className="rounded-[14px] border border-dashed border-line p-12 text-center animate-fade-up">
          <BookOpen className="mx-auto size-10 text-faint mb-3" />
          <h3 className="font-display text-xl text-ink">No Courses Added Yet</h3>
          <p className="mt-1 text-xs text-muted-ink">
            Create your first custom course to start managing real assignments and student
            submissions.
          </p>
          <Button onClick={onOpenAddCourse} className="mt-4 bg-ink text-card hover:bg-ink/90">
            <Plus className="mr-1.5 size-4" /> Add First Course
          </Button>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {filtered.map((item) => {
            const isSelected = item.id === selectedCourseId;
            return (
              <div
                key={item.id}
                onClick={() => onSelectCourse(item.id)}
                className={cn(
                  "group relative cursor-pointer rounded-[14px] border bg-card p-5 text-left transition-all hover:-translate-y-0.5 hover:shadow-md",
                  isSelected ? "border-lav ring-2 ring-lav-soft" : "border-line",
                )}
              >
                <div className="flex items-start justify-between">
                  <div
                    className={cn(
                      "grid size-10 place-items-center rounded-lg",
                      `soft-${item.tone || "lav"}`,
                    )}
                  >
                    <GraduationCap className={cn("size-5", `icon-${item.tone || "lav"}`)} />
                  </div>
                  <div className="flex items-center gap-1.5">
                    {isSelected && <Badge variant="outline">Active Course</Badge>}
                    <Button
                      variant="ghost"
                      size="icon"
                      className="size-7 text-muted-ink hover:text-clay hover:bg-clay-soft"
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteCourse(item.id);
                      }}
                      title="Delete Course"
                    >
                      <Trash2 className="size-3.5" />
                    </Button>
                  </div>
                </div>
                <div className="mt-4 flex items-end justify-between gap-2">
                  <div>
                    <p className="font-display text-xl">{item.name}</p>
                    <p className="mt-1 text-xs text-muted-ink">
                      {item.code} · Section {item.section || "A"}
                    </p>
                  </div>
                  <span className="text-xs text-faint">{item.students_count || 0} students</span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </>
  );
}

// =========================================================================
// Assignments & Submissions View (with Reference Assignment / Ground Truth)
// =========================================================================

function getProcessingStage(p: number): string {
  if (p < 25) return "Ingesting student documents & verifying field encryption";
  if (p < 50) return "Computing dense semantic embeddings & text indexing";
  if (p < 75) return "Executing peer-to-peer similarity cross-check";
  if (p < 90) return "Evaluating synthetic AI likelihood & rubric directives";
  return "Applying Gemini rubric evaluation & generating score breakdown";
}

function AssignmentsView({
  course,
  courses,
  onSelectCourse,
  rubrics,
  onReloadRubrics,
  assignments,
  selectedAssignmentId,
  processingAssignmentId,
  onSelectAssignment,
  onTakeDefaultAssignment,
  takingAssignment,
  onOpenAddAssignment,
  onOpenEditAssignment,
  onDeleteAssignment,
  onOpenManualSubmission,
  onDeleteSubmission,
  onClearAllSubmissions,
  submissions,
  isProcessing,
  progress,
  onStartGrading,
  onReloadSubmissions,
  onNavigate,
  showToast,
}: {
  course: APICourse | null;
  courses: APICourse[];
  onSelectCourse: (id: string) => void;
  rubrics: Rubric[];
  onReloadRubrics: () => Promise<void> | void;
  assignments: APIAssignment[];
  selectedAssignmentId: string;
  processingAssignmentId?: string;
  onSelectAssignment: (id: string) => void;
  onTakeDefaultAssignment: () => Promise<APIAssignment | null>;
  takingAssignment: boolean;
  onOpenAddAssignment: () => void;
  onOpenEditAssignment: () => void;
  onDeleteAssignment: (id: string) => void;
  onOpenManualSubmission: () => void;
  onDeleteSubmission: (id: string) => void;
  onClearAllSubmissions: () => void;
  submissions: SubmissionItem[];
  isProcessing: boolean;
  progress: number;
  onStartGrading: (assignId?: string) => void;
  onReloadSubmissions: (assignId?: string) => void;
  onNavigate: (view: ViewKey) => void;
  showToast: (msg: string) => void;
}) {
  const [activeTab, setActiveTab] = useState<"submissions" | "rubrics">("submissions");
  const [rubricMode, setRubricMode] = useState<"list" | "upload" | "builder">("list");
  const [uploading, setUploading] = useState(false);
  const [uploadingRubric, setUploadingRubric] = useState(false);
  const [rubricDragOver, setRubricDragOver] = useState(false);
  const [rubricUploadFile, setRubricUploadFile] = useState<File | null>(null);
  const [rubricUploadTitle, setRubricUploadTitle] = useState("");
  const [linkingRubricId, setLinkingRubricId] = useState<string | null>(null);

  const activeAssign = assignments.find((a) => a.id === selectedAssignmentId);
  const isThisAssignmentProcessing =
    isProcessing && (!processingAssignmentId || processingAssignmentId === selectedAssignmentId);
  const linkedRubric = rubrics.find((r) => r.id === activeAssign?.rubric_id);

  if (!course) {
    return (
      <div className="rounded-[14px] border border-dashed border-line p-12 text-center animate-fade-up">
        <FolderOpen className="mx-auto size-10 text-faint mb-3" />
        <h3 className="font-display text-xl text-ink">No Active Course Selected</h3>
        <p className="mt-1 text-xs text-muted-ink">
          Please select or create a course before configuring assignments and student submissions.
        </p>
        <Button
          onClick={() => onNavigate("courses")}
          className="mt-4 bg-ink text-card hover:bg-ink/90"
        >
          Go to Courses
        </Button>
      </div>
    );
  }

  const handleFileUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;

    let targetAssignId = selectedAssignmentId;
    if (!targetAssignId) {
      if (assignments.length > 0 && assignments[0]) {
        targetAssignId = assignments[0].id;
        onSelectAssignment(targetAssignId);
      } else if (course) {
        setUploading(true);
        showToast(`Taking Assignment 1 for ${course.code || course.name}...`);
        const created = await onTakeDefaultAssignment();
        if (created) {
          targetAssignId = created.id;
        } else {
          setUploading(false);
          return;
        }
      }
    }

    if (!targetAssignId) {
      showToast("Please take or create an assignment first.");
      return;
    }

    setUploading(true);
    showToast(`Uploading ${files.length} submission(s) with field-level encryption...`);
    try {
      await api.submissions.batchUpload(targetAssignId, Array.from(files));
      showToast(
        `Uploaded ${files.length} submission(s). Ready for grading! Click "Start Grading" when ready.`,
        "success",
      );
      await onReloadSubmissions(targetAssignId);
    } catch (e: any) {
      showToast(`Upload error: ${e.message}`, "error");
    } finally {
      setUploading(false);
    }
  };

  const handleRubricFileSelect = (file: File) => {
    setRubricUploadFile(file);
    const cleanName = file.name
      .replace(/\.[^/.]+$/, "")
      .replace(/[-_]/g, " ")
      .trim();
    setRubricUploadTitle(cleanName);
  };

  const handleUploadRubricSubmit = async () => {
    if (!rubricUploadFile) {
      showToast("Please select a rubric file to upload.");
      return;
    }
    setUploadingRubric(true);
    showToast(`Uploading and analyzing rubric document '${rubricUploadFile.name}'...`);
    try {
      const res = await api.rubrics.upload(rubricUploadFile, {
        classroom_id: course.id,
        course_id: course.id,
        title: rubricUploadTitle || rubricUploadFile.name,
      });
      showToast(`Rubric '${res.title || res.name}' successfully added to database!`);
      if (
        activeAssign &&
        (!activeAssign.rubric_id ||
          window.confirm("Attach this uploaded rubric to current active assignment?"))
      ) {
        await api.assignments.update(activeAssign.id, { rubric_id: res.id });
        activeAssign.rubric_id = res.id;
        showToast(`Attached to '${activeAssign.title}'.`);
      }
      await onReloadRubrics();
      setRubricMode("list");
      setRubricUploadFile(null);
      setRubricUploadTitle("");
    } catch (err: any) {
      showToast(`Failed to upload rubric: ${err.message}`);
    } finally {
      setUploadingRubric(false);
    }
  };

  const handleAttachRubric = async (rubricId: string) => {
    if (!activeAssign) {
      showToast("Select or create an assignment first to attach this rubric.");
      return;
    }
    setLinkingRubricId(rubricId);
    try {
      await api.assignments.update(activeAssign.id, { rubric_id: rubricId });
      activeAssign.rubric_id = rubricId;
      showToast(`Rubric attached to '${activeAssign.title}' successfully.`);
      await onReloadRubrics();
    } catch (err: any) {
      showToast(`Error attaching rubric: ${err.message}`);
    } finally {
      setLinkingRubricId(null);
    }
  };

  const handleDetachRubric = async () => {
    if (!activeAssign) return;
    try {
      await api.assignments.update(activeAssign.id, { rubric_id: "" });
      activeAssign.rubric_id = undefined;
      showToast(`Rubric detached from '${activeAssign.title}'.`);
      await onReloadRubrics();
    } catch (err: any) {
      showToast(`Error: ${err.message}`);
    }
  };

  const handleDeleteRubric = async (rubricId: string, rubricTitle: string) => {
    if (!window.confirm(`Are you sure you want to delete rubric '${rubricTitle}'?`)) return;
    try {
      await api.rubrics.delete(rubricId);
      if (activeAssign && activeAssign.rubric_id === rubricId) {
        activeAssign.rubric_id = undefined;
      }
      showToast(`Rubric '${rubricTitle}' deleted.`);
      await onReloadRubrics();
    } catch (err: any) {
      showToast(`Error deleting rubric: ${err.message}`);
    }
  };

  return (
    <>
      <SectionTitle
        eyebrow={`Course: ${course.code} · Section ${course.section || "A"}`}
        title="Assignments, Submissions & Evaluation Rubrics"
        description="Manage coursework, benchmark reference solutions, and configure grading criteria via document upload or the matrix designer."
        action={
          <div className="flex flex-wrap items-center gap-2">
            {courses.length > 0 && (
              <div className="flex items-center gap-2 rounded-lg border border-line bg-card px-3 py-1.5 shadow-xs">
                <BookOpen className="size-4 text-amber-ink" />
                <span className="text-xs font-semibold text-muted-ink">Course:</span>
                <select
                  value={course.id}
                  onChange={(e) => onSelectCourse(e.target.value)}
                  className="bg-transparent text-sm font-medium text-ink focus:outline-none cursor-pointer"
                >
                  {courses.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.code} · {c.name}
                    </option>
                  ))}
                </select>
              </div>
            )}
            {activeAssign && (
              <Button
                asChild
                className="rounded-lg bg-teal-600 text-white hover:bg-teal-500 shadow-sm"
              >
                <Link to="/dashboard/assignments/$id/upload" params={{ id: activeAssign.id }}>
                  <FileArchive className="mr-1.5 size-4" />
                  Batch ZIP & Roll Matching
                </Link>
              </Button>
            )}
            <Button
              onClick={onOpenAddAssignment}
              className="rounded-lg bg-ink text-card hover:bg-ink/90"
            >
              <Plus className="mr-1.5 size-4" />
              New Assignment
            </Button>
            <Button onClick={onOpenManualSubmission} variant="outline">
              <FileCode className="mr-1.5 size-4" />
              Manual Text Input
            </Button>
          </div>
        }
      />

      {/* Integrated Section Tabs */}
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3 border-b border-line pb-3">
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setActiveTab("submissions")}
            className={cn(
              "inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition-all",
              activeTab === "submissions"
                ? "bg-ink text-card shadow-sm"
                : "text-muted-ink hover:text-ink hover:bg-card",
            )}
          >
            <FolderOpen className="size-4" />
            <span>Submissions & Evaluations</span>
            <Badge
              variant={activeTab === "submissions" ? "secondary" : "outline"}
              className="ml-1 text-[10px] font-mono"
            >
              {submissions.length}
            </Badge>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("rubrics")}
            className={cn(
              "inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition-all",
              activeTab === "rubrics"
                ? "bg-ink text-card shadow-sm"
                : "text-muted-ink hover:text-ink hover:bg-card",
            )}
          >
            <ClipboardCheck className="size-4" />
            <span>Rubrics & Criteria Matrix</span>
            <Badge
              variant={activeTab === "rubrics" ? "secondary" : "outline"}
              className="ml-1 text-[10px] font-mono"
            >
              {rubrics.length}
            </Badge>
          </button>
        </div>

        {activeTab === "rubrics" && (
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant={rubricMode === "list" ? "default" : "outline"}
              onClick={() => setRubricMode("list")}
              className="text-xs"
            >
              Rubrics Library ({rubrics.length})
            </Button>
            <Button
              size="sm"
              variant={rubricMode === "upload" ? "default" : "outline"}
              onClick={() => setRubricMode("upload")}
              className="text-xs"
            >
              <UploadCloud className="mr-1.5 size-3.5" />
              Upload Rubric Doc
            </Button>
            <Button
              size="sm"
              variant={rubricMode === "builder" ? "default" : "outline"}
              onClick={() => setRubricMode("builder")}
              className="text-xs"
            >
              <Edit3 className="mr-1.5 size-3.5" />
              Inline Matrix Designer
            </Button>
          </div>
        )}
      </div>

      {/* TAB 1: SUBMISSIONS & EVALUATIONS */}
      {activeTab === "submissions" && (
        <div className="grid gap-5 xl:grid-cols-12">
          <section className="rounded-[14px] border border-line bg-card p-5 xl:col-span-7">
            {/* Active Assignment Selection */}
            <div className="mb-4">
              <div className="flex items-center justify-between">
                <label className="text-[11px] font-medium uppercase tracking-[0.14em] text-faint">
                  Active Assignment
                </label>
                {isThisAssignmentProcessing && (
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-soft px-2.5 py-0.5 text-[11px] font-bold text-amber-ink animate-pulse">
                    <span className="relative flex size-2">
                      <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-amber opacity-75"></span>
                      <span className="relative inline-flex size-2 rounded-full bg-amber"></span>
                    </span>
                    In Process ({progress}%)
                  </span>
                )}
              </div>
              <div className="mt-1 flex flex-wrap items-center gap-2">
                {assignments.length === 0 ? (
                  <div className="flex flex-wrap items-center gap-3 py-1">
                    <span className="text-xs italic text-faint">
                      No assignments in this course yet.
                    </span>
                    <Button
                      size="sm"
                      variant="default"
                      className="h-7 text-xs bg-ink text-card hover:bg-ink/90 font-medium shadow-sm transition-all"
                      onClick={() => onOpenAddAssignment()}
                      disabled={uploading}
                    >
                      <Plus className="mr-1 size-3.5" />
                      New Assignment
                    </Button>
                  </div>
                ) : (
                  assignments.map((a) => {
                    const isThisProcessing =
                      isProcessing && a.id === (processingAssignmentId || selectedAssignmentId);
                    const isSelected = a.id === selectedAssignmentId;
                    return (
                      <Button
                        key={a.id}
                        size="sm"
                        variant={isSelected ? "default" : "outline"}
                        onClick={() => onSelectAssignment(a.id)}
                        className={cn(
                          "transition-all",
                          isThisProcessing && "ring-2 ring-amber/60 border-amber/50 font-medium",
                        )}
                      >
                        {isThisProcessing && (
                          <Loader2 className="mr-1.5 size-3.5 animate-spin text-amber-ink" />
                        )}
                        <span>{a.title}</span>
                        {isThisProcessing && (
                          <span className="ml-1.5 rounded bg-amber-soft px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider text-amber-ink">
                            In Process
                          </span>
                        )}
                      </Button>
                    );
                  })
                )}
              </div>
            </div>

            {/* Dynamic In-Process Banner */}
            {isThisAssignmentProcessing && activeAssign && (
              <div className="mb-5 overflow-hidden rounded-[14px] border border-amber/40 bg-gradient-to-r from-amber-soft/80 via-lav-soft/60 to-amber-soft/40 p-4 shadow-sm animate-fade-up">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="relative flex size-3">
                      <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-amber opacity-75"></span>
                      <span className="relative inline-flex size-3 rounded-full bg-amber"></span>
                    </span>
                    <span className="text-xs font-bold uppercase tracking-wider text-amber-ink">
                      Assignment In Process · AI Engine Actively Auditing
                    </span>
                  </div>
                  <span className="rounded-full bg-card/90 px-2.5 py-0.5 font-mono text-xs font-bold text-ink shadow-sm">
                    {progress}% Complete
                  </span>
                </div>

                <div className="mt-2.5 flex items-center gap-2 text-sm font-semibold text-ink">
                  <Sparkles className="size-4 animate-spin text-amber-ink shrink-0" />
                  <span className="truncate">{getProcessingStage(progress)}</span>
                </div>

                <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-card/60">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-amber via-clay to-lav transition-all duration-500 ease-out"
                    style={{ width: `${Math.max(8, progress)}%` }}
                  />
                </div>

                <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4 text-[11px]">
                  <div
                    className={`flex items-center gap-1.5 rounded bg-card/60 p-1.5 ${progress >= 25 ? "text-ink font-semibold" : "text-amber-ink"}`}
                  >
                    {progress >= 25 ? (
                      <CheckCircle2 className="size-3.5 text-sage shrink-0" />
                    ) : (
                      <Loader2 className="size-3.5 animate-spin text-amber-ink shrink-0" />
                    )}
                    <span className="truncate">1. Ingestion & Pseudonymization</span>
                  </div>
                  <div
                    className={`flex items-center gap-1.5 rounded bg-card/60 p-1.5 ${progress >= 50 ? "text-ink font-semibold" : progress >= 25 ? "text-amber-ink" : "text-faint"}`}
                  >
                    {progress >= 50 ? (
                      <CheckCircle2 className="size-3.5 text-sage shrink-0" />
                    ) : progress >= 25 ? (
                      <Loader2 className="size-3.5 animate-spin text-amber-ink shrink-0" />
                    ) : (
                      <div className="size-3.5 rounded-full border border-faint/30 shrink-0" />
                    )}
                    <span className="truncate">2. Vector Embeddings</span>
                  </div>
                  <div
                    className={`flex items-center gap-1.5 rounded bg-card/60 p-1.5 ${progress >= 75 ? "text-ink font-semibold" : progress >= 50 ? "text-amber-ink" : "text-faint"}`}
                  >
                    {progress >= 75 ? (
                      <CheckCircle2 className="size-3.5 text-sage shrink-0" />
                    ) : progress >= 50 ? (
                      <Loader2 className="size-3.5 animate-spin text-amber-ink shrink-0" />
                    ) : (
                      <div className="size-3.5 rounded-full border border-faint/30 shrink-0" />
                    )}
                    <span className="truncate">3. Similarity & Integrity</span>
                  </div>
                  <div
                    className={`flex items-center gap-1.5 rounded bg-card/60 p-1.5 ${progress >= 100 ? "text-ink font-semibold" : progress >= 75 ? "text-amber-ink" : "text-faint"}`}
                  >
                    {progress >= 100 ? (
                      <CheckCircle2 className="size-3.5 text-sage shrink-0" />
                    ) : progress >= 75 ? (
                      <Loader2 className="size-3.5 animate-spin text-amber-ink shrink-0" />
                    ) : (
                      <div className="size-3.5 rounded-full border border-faint/30 shrink-0" />
                    )}
                    <span className="truncate">4. Gemini Auto-Grade</span>
                  </div>
                </div>
              </div>
            )}

            {activeAssign && (
              <div className="mb-5 rounded-lg border border-line bg-paper p-3.5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-ink">{activeAssign.title}</span>
                    <Badge variant="outline">Max Marks: {activeAssign.max_score}</Badge>
                    {isThisAssignmentProcessing ? (
                      <span className="inline-flex items-center gap-1 rounded-full bg-amber-soft px-2 py-0.5 text-[10px] font-bold text-amber-ink animate-pulse">
                        <Loader2 className="size-2.5 animate-spin" /> In Process
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 rounded-full bg-sage-soft px-2 py-0.5 text-[10px] font-semibold text-sage-ink">
                        <CheckCircle2 className="size-2.5 text-sage" /> Active
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-7 text-xs"
                      onClick={onOpenEditAssignment}
                    >
                      <Edit3 className="mr-1 size-3" />
                      Edit Exemplar
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 text-xs text-muted-ink hover:text-clay hover:bg-clay-soft"
                      onClick={() => onDeleteAssignment(activeAssign.id)}
                      title="Delete Assignment"
                    >
                      <Trash2 className="size-3.5" />
                    </Button>
                  </div>
                </div>
                {activeAssign.description && (
                  <p className="mt-1 text-xs text-muted-ink">{activeAssign.description}</p>
                )}

                {/* Rubric Linkage Summary */}
                <div className="mt-3 flex items-center justify-between border-t border-line pt-2 text-xs">
                  <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-faint">
                    Linked Grading Rubric:
                  </span>
                  {linkedRubric ? (
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-sage-ink flex items-center gap-1">
                        <Check className="size-3 text-sage" />
                        {linkedRubric.title || linkedRubric.name} (
                        {linkedRubric.total_marks || linkedRubric.total_max_score || 100} pts)
                      </span>
                      <button
                        type="button"
                        onClick={() => setActiveTab("rubrics")}
                        className="text-[11px] text-amber-ink hover:underline font-medium"
                      >
                        Change
                      </button>
                    </div>
                  ) : (
                    <button
                      type="button"
                      onClick={() => setActiveTab("rubrics")}
                      className="text-[11px] text-amber-ink hover:underline font-medium"
                    >
                      + Attach Rubric
                    </button>
                  )}
                </div>

                {/* Reference Assignment Display */}
                <div className="mt-2 border-t border-line pt-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-faint">
                      Ground Truth Reference Exemplar:
                    </span>
                    <span className="text-[10px] text-sage font-medium">Active benchmark</span>
                  </div>
                  {activeAssign.reference_assignment_text ? (
                    <p className="mt-1 line-clamp-3 rounded bg-card p-2 font-mono text-[11px] text-muted-ink">
                      {activeAssign.reference_assignment_text}
                    </p>
                  ) : (
                    <p className="mt-1 text-xs italic text-faint">
                      No reference exemplar added yet. Click "Edit Exemplar" to paste benchmark code
                      or solution.
                    </p>
                  )}
                </div>
              </div>
            )}

            {/* Drag & Drop File Upload */}
            <label
              className={cn(
                "flex min-h-52 cursor-pointer flex-col items-center justify-center rounded-[12px] border border-dashed border-line bg-paper p-6 text-center transition-colors hover:border-lav",
                isThisAssignmentProcessing && "border-amber/40 bg-amber-soft/20",
              )}
            >
              <input
                type="file"
                multiple
                className="hidden"
                accept=".pdf,.doc,.docx,.txt,.zip"
                onChange={(e) => handleFileUpload(e.target.files)}
              />
              <div
                className={cn(
                  "grid size-12 place-items-center rounded-full text-amber-ink",
                  isThisAssignmentProcessing ? "bg-amber-soft animate-pulse" : "bg-lav-soft",
                )}
              >
                {isThisAssignmentProcessing ? (
                  <Sparkles className="size-6 animate-spin text-amber" />
                ) : (
                  <UploadCloud className="size-6" />
                )}
              </div>
              <p className="mt-3 font-display text-lg">
                {isThisAssignmentProcessing
                  ? "AI Checks In Process · Queue More Submissions"
                  : !activeAssign
                    ? "Take Assignment & Upload Submissions"
                    : "Upload student submissions"}
              </p>
              <p className="mt-1 max-w-sm text-xs text-muted-ink">
                {!activeAssign
                  ? "Drop student files here to automatically register submissions in 'ready' status for Assignment 1."
                  : "Drop PDFs, DOCX, TXT, or ZIP archive. Student identifiers are encrypted upon upload."}
              </p>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="mt-4"
                disabled={uploading}
              >
                {uploading ? (
                  <>
                    <Loader2 className="mr-1.5 size-3.5 animate-spin" />
                    Uploading & Encrypting...
                  </>
                ) : (
                  "Browse files"
                )}
              </Button>
            </label>

            <div className="mt-5 flex items-center justify-between border-t border-line pt-4">
              <div>
                <p className="text-sm font-medium">
                  Ready for Auto-Grading & Similarity Review
                </p>
                <p className="mt-0.5 text-xs text-muted-ink">
                  Executes peer cross-matching, synthetic AI probability, and rubric criteria analysis.
                </p>
              </div>
              <Button
                onClick={() => onStartGrading(selectedAssignmentId)}
                disabled={
                  isThisAssignmentProcessing || submissions.length === 0 || !selectedAssignmentId
                }
                className="bg-ink text-card hover:bg-ink/90 transition-all"
              >
                {isThisAssignmentProcessing ? (
                  <>
                    <Loader2 className="mr-1.5 size-4 animate-spin text-amber" />
                    Grading in Progress ({progress}%)...
                  </>
                ) : (
                  <>
                    Start AI Grading
                    <Sparkles className="ml-1.5 size-4" />
                  </>
                )}
              </Button>
            </div>

            {isThisAssignmentProcessing && (
              <div className="mt-4 rounded-lg bg-lav-soft p-3.5 animate-fade-up">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-medium text-ink">
                    Extracting batch & validating submission formats
                  </span>
                  <span className="font-semibold text-amber-ink">{progress}%</span>
                </div>
                <Progress value={progress} className="mt-2 bg-card" />
                <p className="mt-1.5 text-[11px] text-muted-ink">
                  Benchmarking against reference exemplar · teacher review remains mandatory.
                </p>
              </div>
            )}
          </section>

          {/* Submissions Queue */}
          <section className="rounded-[14px] border border-line bg-card p-5 xl:col-span-5">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="font-display text-xl">Current Submissions</h2>
                <div className="mt-1 flex items-center gap-2">
                  <p className="text-xs text-muted-ink">
                    {submissions.length} submissions in this assignment
                  </p>
                  {isThisAssignmentProcessing && (
                    <span className="inline-flex items-center gap-1 rounded-full bg-amber-soft px-2 py-0.5 text-[10px] font-bold text-amber-ink animate-pulse">
                      <Loader2 className="size-2.5 animate-spin" />
                      AI Checks In Process
                    </span>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-1.5">
                <Button
                  size="sm"
                  variant="ghost"
                  className="h-8 text-xs text-muted-ink hover:text-clay hover:bg-clay-soft"
                  onClick={onClearAllSubmissions}
                  disabled={submissions.length === 0 || isThisAssignmentProcessing}
                  title="Clear all submissions for this assignment"
                >
                  <Trash2 className="mr-1 size-3.5" />
                  Clear All
                </Button>
                <Button
                  size="icon"
                  variant="ghost"
                  onClick={() => onReloadSubmissions(selectedAssignmentId)}
                  title="Refresh"
                >
                  <RefreshCw
                    className={cn(
                      "size-4",
                      isThisAssignmentProcessing && "animate-spin text-amber",
                    )}
                  />
                </Button>
              </div>
            </div>

            <div className="mt-4 max-h-[460px] space-y-2.5 overflow-y-auto pr-1">
              {submissions.length === 0 ? (
                <p className="py-8 text-center text-xs text-faint">
                  No submissions yet. Upload files or use "Manual Text Input" to enter student work.
                </p>
              ) : (
                submissions.map((sub) => (
                  <div
                    key={sub.id}
                    className={cn(
                      "relative overflow-hidden rounded-lg border border-line bg-paper p-3 transition-all",
                      isThisAssignmentProcessing && "border-amber/30 bg-amber-soft/10",
                    )}
                  >
                    {isThisAssignmentProcessing && (
                      <div className="absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r from-amber via-clay to-lav animate-pulse" />
                    )}
                    <div className="flex items-center gap-3">
                      <div
                        className={cn(
                          "grid size-8 shrink-0 place-items-center rounded-lg text-amber-ink",
                          isThisAssignmentProcessing ? "bg-amber-soft" : "bg-lav-soft",
                        )}
                      >
                        {isThisAssignmentProcessing ? (
                          <Loader2 className="size-4 animate-spin text-amber-ink" />
                        ) : (
                          <FileText className="size-4" />
                        )}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center justify-between">
                          <p className="truncate text-xs font-semibold text-ink">{sub.student}</p>
                          {isThisAssignmentProcessing ? (
                            <span className="inline-flex items-center gap-1 rounded bg-amber-soft px-1.5 py-0.5 text-[10px] font-semibold text-amber-ink animate-pulse">
                              <Loader2 className="size-2.5 animate-spin" /> Evaluating...
                            </span>
                          ) : (
                            <span className="text-[11px] font-bold text-ink">{sub.score}/100</span>
                          )}
                        </div>
                        <div className="mt-1 flex items-center gap-2 text-[10px]">
                          {isThisAssignmentProcessing ? (
                            <span className="text-amber-ink font-medium">
                              Rubric evaluation running...
                            </span>
                          ) : (
                            <>
                              <span
                                className={
                                  sub.similarity >= 85 ? "text-clay font-medium" : "text-faint"
                                }
                              >
                                Peer: {sub.similarity}%
                              </span>
                              <span>·</span>
                              <span
                                className={
                                  sub.aiContent >= 60 ? "text-amber-ink font-medium" : "text-faint"
                                }
                              >
                                AI: {sub.aiContent}%
                              </span>
                              <span>·</span>
                              <span
                                className={
                                  (sub.webPlagiarism || 0) >= 20
                                    ? "text-blue font-medium"
                                    : "text-faint"
                                }
                              >
                                Web: {sub.webPlagiarism !== null && sub.webPlagiarism !== undefined ? `${sub.webPlagiarism}%` : "—"}
                              </span>
                            </>
                          )}
                        </div>
                      </div>
                      <Button
                        size="icon"
                        variant="ghost"
                        className="size-7 shrink-0 text-muted-ink hover:text-clay hover:bg-clay-soft"
                        onClick={() => onDeleteSubmission(sub.id)}
                        disabled={isThisAssignmentProcessing}
                        title="Delete Submission"
                      >
                        <Trash2 className="size-3.5" />
                      </Button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </section>
        </div>
      )}

      {/* TAB 2: INTEGRATED RUBRICS & CRITERIA MATRIX */}
      {activeTab === "rubrics" && (
        <div className="space-y-6 animate-fade-up">
          {/* Active Assignment Rubric Status Banner */}
          {activeAssign && (
            <div className="rounded-[14px] border border-line bg-card p-4 shadow-xs">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="grid size-10 place-items-center rounded-xl bg-lav-soft text-amber-ink">
                    <ClipboardCheck className="size-5" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold uppercase tracking-wider text-muted-ink">
                        Active Assignment:
                      </span>
                      <span className="text-sm font-bold text-ink">{activeAssign.title}</span>
                    </div>
                    <p className="mt-0.5 text-xs text-muted-ink">
                      {linkedRubric ? (
                        <>
                          Grading configured with rubric{" "}
                          <span className="font-semibold text-ink">
                            "{linkedRubric.title || linkedRubric.name}"
                          </span>{" "}
                          ({linkedRubric.total_marks || linkedRubric.total_max_score || 100} pts,{" "}
                          {linkedRubric.criteria?.length || 0} criteria rows).
                        </>
                      ) : (
                        "No rubric currently linked to this assignment. Attach one from below or create a new one."
                      )}
                    </p>
                  </div>
                </div>

                {linkedRubric && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={handleDetachRubric}
                    className="text-xs text-clay border-clay/30 hover:bg-clay-soft"
                  >
                    Detach Rubric
                  </Button>
                )}
              </div>
            </div>
          )}

          {/* MODE: UPLOAD RUBRIC DOCUMENT */}
          {rubricMode === "upload" && (
            <div className="rounded-[14px] border border-line bg-card p-6 shadow-xs animate-fade-up">
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <h3 className="font-display text-xl">Upload Rubric Document</h3>
                  <p className="mt-0.5 text-xs text-muted-ink">
                    Upload any grading rubric document (PDF, Word DOCX, Excel XLSX, CSV, Plain Text,
                    or image). Criteria will be automatically extracted and indexed.
                  </p>
                </div>
                <Button size="sm" variant="ghost" onClick={() => setRubricMode("list")}>
                  Cancel
                </Button>
              </div>

              <div
                onDragOver={(e) => {
                  e.preventDefault();
                  setRubricDragOver(true);
                }}
                onDragLeave={() => setRubricDragOver(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setRubricDragOver(false);
                  if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                    handleRubricFileSelect(e.dataTransfer.files[0]);
                  }
                }}
                className={cn(
                  "flex min-h-56 cursor-pointer flex-col items-center justify-center rounded-[12px] border-2 border-dashed p-8 text-center transition-all",
                  rubricDragOver
                    ? "border-amber bg-amber-soft/20 scale-[1.01]"
                    : "border-line bg-paper hover:border-ink/30",
                )}
              >
                <input
                  type="file"
                  id="rubric-file-input"
                  className="hidden"
                  accept=".pdf,.doc,.docx,.xlsx,.xls,.txt,.csv,.png,.jpg,.jpeg"
                  onChange={(e) => {
                    if (e.target.files && e.target.files[0]) {
                      handleRubricFileSelect(e.target.files[0]);
                    }
                  }}
                />
                <div className="grid size-12 place-items-center rounded-full bg-lav-soft text-amber-ink mb-3">
                  <UploadCloud className="size-6" />
                </div>
                {rubricUploadFile ? (
                  <div className="space-y-1">
                    <p className="font-display text-lg text-ink">{rubricUploadFile.name}</p>
                    <p className="text-xs text-muted-ink">
                      {(rubricUploadFile.size / 1024).toFixed(1)} KB · Ready to process
                    </p>
                  </div>
                ) : (
                  <>
                    <p className="font-display text-lg text-ink">
                      Drag & Drop your Rubric file here
                    </p>
                    <p className="mt-1 text-xs text-muted-ink max-w-sm">
                      Supports PDF, DOCX, XLSX, CSV, TXT, and image files. Automatic criteria and
                      score tier extraction.
                    </p>
                  </>
                )}

                <div className="mt-4 flex flex-wrap justify-center gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => document.getElementById("rubric-file-input")?.click()}
                  >
                    {rubricUploadFile ? "Choose Different File" : "Browse Computer"}
                  </Button>
                </div>
              </div>

              {rubricUploadFile && (
                <div className="mt-5 space-y-3 rounded-lg border border-line bg-paper p-4">
                  <label className="text-xs font-semibold text-muted-ink block">
                    Rubric Title / Name:
                  </label>
                  <Input
                    value={rubricUploadTitle}
                    onChange={(e) => setRubricUploadTitle(e.target.value)}
                    placeholder="e.g., Object Oriented Programming Assignment 1 Rubric"
                    className="bg-card"
                  />
                  <div className="flex justify-end gap-2 pt-2">
                    <Button variant="outline" size="sm" onClick={() => setRubricUploadFile(null)}>
                      Clear
                    </Button>
                    <Button
                      size="sm"
                      onClick={handleUploadRubricSubmit}
                      disabled={uploadingRubric}
                      className="bg-ink text-card hover:bg-ink/90"
                    >
                      {uploadingRubric ? (
                        <>
                          <Loader2 className="mr-1.5 size-3.5 animate-spin" />
                          Processing & Saving...
                        </>
                      ) : (
                        <>
                          <Check className="mr-1.5 size-3.5" />
                          Upload & Save Rubric
                        </>
                      )}
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* MODE: INLINE MATRIX RUBRIC BUILDER */}
          {rubricMode === "builder" && (
            <div className="rounded-[14px] border border-line bg-card p-6 shadow-xs animate-fade-up">
              <MatrixRubricBuilder
                classroom={{
                  id: course.id,
                  name: course.name,
                  code: course.code,
                  students_count: course.students_count || 0,
                }}
                classrooms={courses.map((c) => ({
                  id: c.id,
                  name: c.name,
                  code: c.code,
                  students_count: c.students_count || 0,
                }))}
                onSelectClassroom={(id) => onSelectCourse(id)}
                onSaved={async () => {
                  await onReloadRubrics();
                  setRubricMode("list");
                  showToast("Matrix Rubric saved to database and ready for grading!");
                }}
                onCancel={() => setRubricMode("list")}
                showToast={showToast}
              />
            </div>
          )}

          {/* MODE: RUBRICS LIBRARY LIST */}
          {rubricMode === "list" && (
            <div className="space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h3 className="font-display text-xl">Course Rubrics Library</h3>
                  <p className="mt-0.5 text-xs text-muted-ink">
                    Available rubrics for {course.name} ({course.code}). Attach any rubric to the
                    active assignment.
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setRubricMode("upload")}
                    className="text-xs"
                  >
                    <UploadCloud className="mr-1.5 size-3.5" />
                    Upload File
                  </Button>
                  <Button
                    size="sm"
                    onClick={() => setRubricMode("builder")}
                    className="text-xs bg-ink text-card hover:bg-ink/90"
                  >
                    <Plus className="mr-1.5 size-3.5" />
                    New Matrix Rubric
                  </Button>
                </div>
              </div>

              {rubrics.length === 0 ? (
                <div className="rounded-[14px] border border-dashed border-line p-10 text-center bg-card">
                  <ClipboardCheck className="mx-auto size-10 text-faint mb-3" />
                  <h4 className="font-display text-lg text-ink">No Rubrics Created Yet</h4>
                  <p className="mt-1 text-xs text-muted-ink max-w-md mx-auto">
                    Design multi-tier criteria matrices with quantitative score tiers (4, 3, 2, 0
                    pts) or upload an existing rubric document to guide automated evaluation.
                  </p>
                  <div className="mt-5 flex flex-wrap justify-center gap-3">
                    <Button
                      onClick={() => setRubricMode("upload")}
                      variant="outline"
                      className="text-xs"
                    >
                      <UploadCloud className="mr-1.5 size-3.5" />
                      Upload Rubric Document
                    </Button>
                    <Button
                      onClick={() => setRubricMode("builder")}
                      className="text-xs bg-ink text-card hover:bg-ink/90"
                    >
                      <Plus className="mr-1.5 size-3.5" />
                      Open Matrix Rubric Designer
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="grid gap-4 md:grid-cols-2">
                  {rubrics.map((r) => {
                    const isAttached = activeAssign?.rubric_id === r.id;
                    const isLinking = linkingRubricId === r.id;
                    return (
                      <div
                        key={r.id}
                        className={cn(
                          "rounded-[14px] border bg-card p-5 transition-all shadow-xs",
                          isAttached
                            ? "border-sage/60 ring-1 ring-sage/30 bg-sage-soft/10"
                            : "border-line hover:border-ink/20",
                        )}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-2">
                              <h4 className="font-display text-lg font-semibold text-ink truncate">
                                {r.title || r.name}
                              </h4>
                              {isAttached && (
                                <Badge className="bg-sage text-white text-[10px]">
                                  Active Benchmark
                                </Badge>
                              )}
                            </div>
                            <p className="mt-1 text-xs text-muted-ink">
                              {r.criteria?.length || 0} evaluation criteria rows
                            </p>
                          </div>
                          <Badge variant="secondary" className="font-mono text-xs">
                            {r.total_marks || r.total_max_score || 100} pts
                          </Badge>
                        </div>

                        {/* Criteria preview pills */}
                        {r.criteria && r.criteria.length > 0 && (
                          <div className="mt-3 flex flex-wrap gap-1.5">
                            {r.criteria.slice(0, 4).map((c, i) => (
                              <span
                                key={c.id || i}
                                className="inline-flex items-center rounded-md bg-paper px-2 py-1 text-[10px] font-medium text-muted-ink border border-line"
                              >
                                {c.criterion_name || c.name} ({c.max_points || c.max_score || 4}{" "}
                                pts)
                              </span>
                            ))}
                            {r.criteria.length > 4 && (
                              <span className="text-[10px] text-faint self-center">
                                +{r.criteria.length - 4} more
                              </span>
                            )}
                          </div>
                        )}

                        <div className="mt-4 flex items-center justify-between border-t border-line pt-3">
                          {isAttached ? (
                            <span className="text-xs font-semibold text-sage-ink flex items-center gap-1">
                              <CheckCircle2 className="size-3.5 text-sage" /> Attached to{" "}
                              {activeAssign?.title}
                            </span>
                          ) : (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleAttachRubric(r.id)}
                              disabled={isLinking || !activeAssign}
                              className="text-xs"
                            >
                              {isLinking ? (
                                <Loader2 className="mr-1.5 size-3 animate-spin" />
                              ) : (
                                <Check className="mr-1.5 size-3" />
                              )}
                              Attach to Active Assignment
                            </Button>
                          )}

                          <Button
                            size="icon"
                            variant="ghost"
                            onClick={() => handleDeleteRubric(r.id, r.title || r.name)}
                            className="size-7 text-muted-ink hover:text-clay hover:bg-clay-soft"
                            title="Delete Rubric"
                          >
                            <Trash2 className="size-3.5" />
                          </Button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </>
  );
}

// =========================================================================
// Assessments / Rubric Builder View
// =========================================================================

function AssessmentsView({
  course,
  assignment,
  onNavigate,
  showToast,
}: {
  course: APICourse | null;
  assignment: APIAssignment | null;
  onNavigate: (view: ViewKey) => void;
  showToast: (msg: string) => void;
}) {
  const [rubrics, setRubrics] = useState<Rubric[]>([]);
  const [criteria, setCriteria] = useState([
    {
      name: "Understanding",
      description: "Conceptual clarity, problem modeling and depth",
      weight: 30,
      max_score: 30,
    },
    {
      name: "Accuracy",
      description: "Correctness of algorithmic solution against benchmark",
      weight: 30,
      max_score: 30,
    },
    {
      name: "Methodology",
      description: "Process, computational complexity and reasoning",
      weight: 20,
      max_score: 20,
    },
    {
      name: "Presentation",
      description: "Code structure, modularity and documentation",
      weight: 20,
      max_score: 20,
    },
  ]);

  useEffect(() => {
    if (course?.id) {
      api.rubrics.listByCourse(course.id).then(setRubrics).catch(console.error);
    }
  }, [course?.id]);

  if (!course) {
    return (
      <div className="rounded-[14px] border border-dashed border-line p-12 text-center animate-fade-up">
        <ClipboardCheck className="mx-auto size-10 text-faint mb-3" />
        <h3 className="font-display text-xl text-ink">No Active Course Selected</h3>
        <p className="mt-1 text-xs text-muted-ink">
          Please select or create a course to configure grading rubrics.
        </p>
        <Button
          onClick={() => onNavigate("courses")}
          className="mt-4 bg-ink text-card hover:bg-ink/90"
        >
          Go to Courses
        </Button>
      </div>
    );
  }

  const handleSaveRubric = async () => {
    try {
      const res = await api.rubrics.create({
        name: assignment ? `${assignment.title} Rubric` : `${course.code} Rubric`,
        course_id: course.id,
        total_max_score: 100,
        criteria,
      });
      setRubrics([res, ...rubrics]);
      showToast("Rubric saved and synced with backend.");
      onNavigate("grading");
    } catch (e: any) {
      showToast(`Error saving rubric: ${e.message}`);
    }
  };

  const addCriterion = () => {
    setCriteria([
      ...criteria,
      {
        name: "New Criterion",
        description: "Criterion evaluation standards",
        weight: 10,
        max_score: 10,
      },
    ]);
  };

  return (
    <>
      <SectionTitle
        eyebrow="Rubric Engine · Structured Criteria"
        title="Grading Rubric Setup"
        description="Define structured evaluation criteria with explicit weights and maximum marks. Gemini uses these criteria alongside your Reference Assignment."
        action={
          <Button onClick={handleSaveRubric} className="bg-ink text-card hover:bg-ink/90">
            <Sparkles className="mr-1.5 size-4" />
            Save & Start Grading
          </Button>
        }
      />

      <div className="rounded-[14px] border border-line bg-card p-5">
        <div className="overflow-hidden rounded-lg border border-line">
          <div className="grid grid-cols-12 gap-3 bg-paper px-4 py-3 text-[10px] font-semibold uppercase tracking-[0.12em] text-faint">
            <div className="col-span-3">Criterion</div>
            <div className="col-span-5">Description & Guidelines</div>
            <div className="col-span-2">Weight (%)</div>
            <div className="col-span-2">Max Marks</div>
          </div>
          {criteria.map((row, idx) => (
            <div
              key={idx}
              className="grid grid-cols-12 items-center gap-3 border-t border-line px-4 py-3 text-sm"
            >
              <div className="col-span-3">
                <Input
                  value={row.name}
                  onChange={(e) => {
                    setCriteria(
                      criteria.map((c, i) => (i === idx ? { ...c, name: e.target.value } : c)),
                    );
                  }}
                  className="h-8 text-xs font-medium"
                />
              </div>
              <div className="col-span-5">
                <Input
                  value={row.description}
                  onChange={(e) => {
                    setCriteria(
                      criteria.map((c, i) =>
                        i === idx ? { ...c, description: e.target.value } : c,
                      ),
                    );
                  }}
                  className="h-8 text-xs text-muted-ink"
                />
              </div>
              <div className="col-span-2">
                <Input
                  type="number"
                  value={row.weight}
                  onChange={(e) => {
                    setCriteria(
                      criteria.map((c, i) =>
                        i === idx ? { ...c, weight: Number(e.target.value) } : c,
                      ),
                    );
                  }}
                  className="h-8 text-xs text-center"
                />
              </div>
              <div className="col-span-2">
                <Input
                  type="number"
                  value={row.max_score}
                  onChange={(e) => {
                    setCriteria(
                      criteria.map((c, i) =>
                        i === idx ? { ...c, max_score: Number(e.target.value) } : c,
                      ),
                    );
                  }}
                  className="h-8 text-xs text-center"
                />
              </div>
            </div>
          ))}
        </div>

        <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
          <Button variant="outline" size="sm" onClick={addCriterion}>
            <Plus className="mr-1 size-3.5" />
            Add Criterion Row
          </Button>
          <p className="text-xs text-faint">
            Total Weight:{" "}
            <span className="font-semibold text-ink">
              {criteria.reduce((sum, c) => sum + (Number(c.weight) || 0), 0)}%
            </span>
          </p>
        </div>
      </div>
    </>
  );
}

// =========================================================================
// Similarity & Plagiarism View (Peer, AI, and Public Web)
// =========================================================================

function SimilarityView({
  matches,
  submissions,
  onNavigate,
  showToast,
}: {
  matches: SimilarityMatch[];
  submissions: SubmissionItem[];
  onNavigate: (view: ViewKey) => void;
  showToast: (msg: string) => void;
}) {
  const highSim = submissions.filter((s) => s.similarity >= 85);
  const highAi = submissions.filter((s) => s.aiContent >= 60);
  const highWeb = submissions.filter((s) => (s.webPlagiarism || 0) >= 20);

  return (
    <>
      <SectionTitle
        eyebrow="Academic Integrity · Similarity Check"
        title="Integrity & Academic Similarity Audits"
        description="Comprehensive verification across key integrity dimensions: (1) Peer-to-Peer Cross Copying, (2) AI Content Likelihood, and (3) Rubric Alignment."
      />

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <div className="rounded-[12px] border border-line bg-card p-4">
          <p className="text-xs text-muted-ink">Total Submissions</p>
          <p className="mt-1 font-display text-3xl">{submissions.length}</p>
        </div>
        <div className="rounded-[12px] border border-line bg-card p-4">
          <p className="text-xs text-muted-ink">High Similarity Collisions (&gt;=85%)</p>
          <p className="mt-1 font-display text-3xl text-clay">{highSim.length}</p>
        </div>
        <div className="rounded-[12px] border border-line bg-card p-4">
          <p className="text-xs text-muted-ink">AI Content Flags</p>
          <p className="mt-1 font-display text-3xl text-amber-ink">{highAi.length}</p>
        </div>
        <div className="rounded-[12px] border border-line bg-card p-4">
          <p className="text-xs text-muted-ink">Web Citations Flags</p>
          <p className="mt-1 font-display text-3xl text-blue">{highWeb.length}</p>
        </div>
      </div>

      <div className="mt-5 rounded-[14px] border border-line bg-card p-5">
        <h2 className="font-display text-xl">Flagged Submissions & Matched Peers</h2>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead>
              <tr className="border-b border-line text-[10px] uppercase tracking-[0.14em] text-faint">
                <th className="px-3 py-3">Student</th>
                <th className="px-3 py-3">Peer Similarity</th>
                <th className="px-3 py-3">AI Likelihood</th>
                <th className="px-3 py-3">Web Citations</th>
                <th className="px-3 py-3">Status</th>
                <th className="px-3 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody>
              {submissions.map((sub) => (
                <tr key={sub.id} className="border-b border-line last:border-0">
                  <td className="px-3 py-4 font-medium">
                    {sub.student}
                    <span className="block text-[11px] text-faint">Roll: {sub.roll}</span>
                  </td>
                  <td className="px-3 py-4 font-display text-lg">
                    <span className={sub.similarity >= 85 ? "text-clay" : "text-muted-ink"}>
                      {sub.similarity}%
                    </span>
                  </td>
                  <td className="px-3 py-4">
                    <Pill tone={sub.aiContent >= 60 ? "amber" : "sage"}>
                      {sub.aiContent >= 60
                        ? `${sub.aiContent}% Indicated`
                        : `${sub.aiContent}% Low`}
                    </Pill>
                  </td>
                  <td className="px-3 py-4">
                    <Pill tone={(sub.webPlagiarism || 0) >= 20 ? "clay" : "sage"}>
                      {sub.webPlagiarism || 0}% match
                    </Pill>
                  </td>
                  <td className="px-3 py-4">
                    <Pill
                      tone={
                        sub.status === "approved"
                          ? "sage"
                          : sub.status === "flagged"
                            ? "clay"
                            : "lav"
                      }
                    >
                      {sub.status}
                    </Pill>
                  </td>
                  <td className="px-3 py-4 text-right">
                    <Button size="sm" variant="outline" onClick={() => onNavigate("review")}>
                      Inspect in Queue
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}

// =========================================================================
// AI Auto-Grading Overview View
// =========================================================================

function AIGradingView({
  submissions,
  assignment,
  isProcessing,
  progress = 0,
  onStartGrading,
  onReview,
  onNavigate,
  showToast,
}: {
  submissions: SubmissionItem[];
  assignment: APIAssignment | null;
  isProcessing: boolean;
  progress?: number;
  onStartGrading: (assignId?: string) => void;
  onReview: (id: string) => void;
  onNavigate: (view: ViewKey) => void;
  showToast: (msg: string) => void;
}) {
  return (
    <>
      <SectionTitle
        eyebrow="Auto-Grading Engine · Rubric & Ground Truth"
        title="Suggested Grades & Integrity Scores"
        description="AI evaluates submissions against your criteria and reference solution. Every grade is held in Pending Review until approved."
        action={
          <Button
            onClick={() => onStartGrading(assignment?.id)}
            disabled={isProcessing}
            className="bg-ink text-card hover:bg-ink/90"
          >
            {isProcessing ? (
              <>
                <Loader2 className="mr-1.5 size-4 animate-spin text-amber" />
                Grading in Progress ({progress}%)...
              </>
            ) : (
              <>
                <Sparkles className="mr-1.5 size-4" />
                Rerun Batch Auto-Grading
              </>
            )}
          </Button>
        }
      />

      {isProcessing && (
        <div className="mb-5 overflow-hidden rounded-[14px] border border-amber/40 bg-gradient-to-r from-amber-soft/80 via-lav-soft/60 to-amber-soft/40 p-4 shadow-sm animate-fade-up">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="relative flex size-3">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-amber opacity-75"></span>
                <span className="relative inline-flex size-3 rounded-full bg-amber"></span>
              </span>
              <span className="text-xs font-bold uppercase tracking-wider text-amber-ink">
                Rubric Evaluation & Similarity In Process
              </span>
            </div>
            <span className="rounded-full bg-card/90 px-2.5 py-0.5 font-mono text-xs font-bold text-ink shadow-sm">
              {progress}% Complete
            </span>
          </div>

          <div className="mt-2 flex items-center gap-2 text-sm font-semibold text-ink">
            <Sparkles className="size-4 animate-spin text-amber-ink shrink-0" />
            <span className="truncate">{getProcessingStage(progress)}</span>
          </div>

          <div className="mt-2.5 h-2 w-full overflow-hidden rounded-full bg-card/60">
            <div
              className="h-full rounded-full bg-gradient-to-r from-amber via-clay to-lav transition-all duration-500 ease-out"
              style={{ width: `${Math.max(8, progress)}%` }}
            />
          </div>
        </div>
      )}

      <div className="rounded-[14px] border border-line bg-card p-5">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead>
              <tr className="border-b border-line text-[10px] uppercase tracking-[0.14em] text-faint">
                <th className="px-3 py-3">Student & Roll</th>
                <th className="px-3 py-3">AI Suggested Score</th>
                <th className="px-3 py-3">Peer Similarity</th>
                <th className="px-3 py-3">AI Likelihood</th>
                <th className="px-3 py-3">Web Citations</th>
                <th className="px-3 py-3">Status</th>
                <th className="px-3 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody>
              {submissions.map((sub) => (
                <tr key={sub.id} className="border-b border-line last:border-0">
                  <td className="px-3 py-4">
                    <p className="font-medium text-ink">{sub.student}</p>
                    <p className="text-[11px] text-faint">{sub.roll}</p>
                  </td>
                  <td className="px-3 py-4 font-display text-xl">
                    {sub.score !== null && sub.score !== undefined ? (
                      <>
                        {sub.score}
                        <span className="text-sm text-muted-ink">/100</span>
                      </>
                    ) : (
                      <span className="text-sm text-muted-ink font-normal">—</span>
                    )}
                  </td>
                  <td className="px-3 py-4">
                    {sub.status === "ready" || sub.status === "unmatched" || sub.similarity === null || sub.similarity === undefined ? (
                      <span className="text-sm text-muted-ink">—</span>
                    ) : (
                      <span
                        className={
                          sub.similarity >= 85 ? "font-semibold text-clay" : "text-muted-ink"
                        }
                      >
                        {sub.similarity}%
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-4">
                    {sub.status === "ready" || sub.status === "unmatched" || sub.aiContent === null || sub.aiContent === undefined ? (
                      <span className="text-sm text-muted-ink">—</span>
                    ) : (
                      <Pill tone={sub.aiContent >= 60 ? "amber" : "sage"}>{sub.aiContent}%</Pill>
                    )}
                  </td>
                  <td className="px-3 py-4">
                    {sub.status === "ready" || sub.status === "unmatched" || sub.webPlagiarism === null || sub.webPlagiarism === undefined ? (
                      <span className="text-sm text-muted-ink">—</span>
                    ) : (
                      <Pill tone={(sub.webPlagiarism || 0) >= 20 ? "clay" : "sage"}>
                        {sub.webPlagiarism || 0}%
                      </Pill>
                    )}
                  </td>
                  <td className="px-3 py-4">
                    <Pill
                      tone={
                        sub.status === "approved"
                          ? "sage"
                          : sub.status === "flagged"
                            ? "clay"
                            : sub.status === "ready"
                              ? "amber"
                              : "lav"
                      }
                    >
                      {sub.status === "approved"
                        ? "Approved"
                        : sub.status === "flagged"
                          ? "Flagged"
                          : sub.status === "ready"
                            ? "Ready"
                            : "Pending"}
                    </Pill>
                  </td>
                  <td className="px-3 py-4 text-right">
                    <Button size="sm" onClick={() => onReview(sub.id)}>
                      Review & Stamp
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}

// =========================================================================
// Review Workspace (Teacher Approval & Grade Stamping)
// =========================================================================

function ReviewWorkspace({
  assignment,
  submissions,
  selectedSubmissionId,
  onSelectSubmission,
  onGraded,
  onOpenAssistant,
  onNavigate,
  showToast,
}: {
  assignment: APIAssignment | null;
  submissions: SubmissionItem[];
  selectedSubmissionId: string;
  onSelectSubmission: (id: string) => void;
  onGraded: () => void;
  onOpenAssistant?: () => void;
  onNavigate: (view: ViewKey) => void;
  showToast: (msg: string) => void;
}) {
  const [detail, setDetail] = useState<SubmissionDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editedScore, setEditedScore] = useState<number>(0);
  const [teacherFeedback, setTeacherFeedback] = useState("");
  const [criteriaScores, setCriteriaScores] = useState<any[]>([]);

  useEffect(() => {
    if (selectedSubmissionId) {
      loadDetail(selectedSubmissionId);
    }
  }, [selectedSubmissionId]);

  const loadDetail = async (subId: string) => {
    setLoading(true);
    try {
      const data = await api.review.getDetail(subId);
      setDetail(data);
      setEditedScore(data.score || 0);
      setTeacherFeedback(data.teacher_feedback || data.ai_feedback || "");
      setCriteriaScores(data.criteria_scores || []);
    } catch (e: any) {
      showToast(`Error loading detail: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleApproveGrade = async () => {
    if (!detail) return;
    try {
      await api.review.stampGrade(detail.id, {
        status: "approved",
        final_score: editedScore,
        criteria_scores: criteriaScores,
        teacher_feedback: teacherFeedback,
        action: "APPROVE",
      });
      showToast(`Grade stamped and approved: ${editedScore}/100 for ${detail.student}!`);
      onGraded();
      loadDetail(detail.id);
    } catch (e: any) {
      showToast(`Error stamping grade: ${e.message}`);
    }
  };

  const currentSub = detail || submissions.find((s) => s.id === selectedSubmissionId);

  return (
    <>
      <SectionTitle
        eyebrow="Teacher Review Console · Authoritative Decision"
        title="Review & Stamp Grade"
        description="Inspect the student's submission side-by-side with your Reference Assignment. Verify peer similarity, AI probability, and rubric criteria."
        action={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={onOpenAssistant}
              className="gap-1.5 text-xs border-amber/40 text-amber-ink hover:bg-amber-soft/50"
            >
              <Sparkles className="size-3.5 text-amber-600" />
              Fix Prompt with AI Assistant
            </Button>
            <Pill tone="sage">
              {submissions.filter((s) => s.status === "approved").length} approved
            </Pill>
            <Pill tone="amber">
              {submissions.filter((s) => s.status === "graded").length} pending
            </Pill>
          </div>
        }
      />

      {/* Student Selector Carousel */}
      <div className="mb-4 flex items-center gap-2 overflow-x-auto rounded-lg border border-line bg-card p-2">
        <span className="shrink-0 px-2 text-[10px] uppercase tracking-[0.14em] text-faint">
          Students:
        </span>
        {submissions.map((sub) => (
          <Button
            key={sub.id}
            size="sm"
            variant={sub.id === selectedSubmissionId ? "default" : "ghost"}
            className="shrink-0 text-xs"
            onClick={() => onSelectSubmission(sub.id)}
          >
            {sub.student} ({sub.score !== null && sub.score !== undefined ? `${sub.score}/100` : "—"})
          </Button>
        ))}
      </div>

      {currentSub ? (
        <div className="grid gap-5 xl:grid-cols-12">
          {/* Column 1: Student Text & Reference Exemplar */}
          <section className="flex flex-col rounded-[14px] border border-line bg-card p-5 xl:col-span-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] uppercase tracking-[0.16em] text-faint">
                  Student Submission
                </p>
                <h2 className="mt-1 font-display text-2xl">{currentSub.student}</h2>
                <p className="text-xs text-faint">Roll: {currentSub.roll}</p>
              </div>
              <Pill tone={currentSub.similarity && currentSub.similarity >= 85 ? "clay" : "sage"}>
                {currentSub.similarity !== null && currentSub.similarity !== undefined ? `${currentSub.similarity}% Peer Match` : "—"}
              </Pill>
            </div>

            {/* Academic Integrity Indicator Metrics */}
            <div className="mt-4 grid grid-cols-3 gap-2 border-y border-line py-3 text-center">
              <div>
                <span className="text-[10px] uppercase text-faint">Peer Sim</span>
                <p
                  className={cn(
                    "text-sm font-bold",
                    currentSub.similarity && currentSub.similarity >= 85 ? "text-clay" : "text-ink",
                  )}
                >
                  {currentSub.similarity !== null && currentSub.similarity !== undefined ? `${currentSub.similarity}%` : "—"}
                </p>
              </div>
              <div>
                <span className="text-[10px] uppercase text-faint">AI Prob</span>
                <p
                  className={cn(
                    "text-sm font-bold",
                    currentSub.aiContent && currentSub.aiContent >= 60 ? "text-amber-ink" : "text-ink",
                  )}
                >
                  {currentSub.aiContent !== null && currentSub.aiContent !== undefined ? `${currentSub.aiContent}%` : "—"}
                </p>
              </div>
              <div>
                <span className="text-[10px] uppercase text-faint">Web Match</span>
                <p
                  className={cn(
                    "text-sm font-bold",
                    currentSub.webPlagiarism && currentSub.webPlagiarism >= 20 ? "text-blue" : "text-ink",
                  )}
                >
                  {currentSub.webPlagiarism !== null && currentSub.webPlagiarism !== undefined ? `${currentSub.webPlagiarism}%` : "—"}
                </p>
              </div>
            </div>

            {/* Submission Content Text */}
            <div className="mt-4 max-h-[300px] overflow-y-auto rounded-lg border border-line bg-paper p-3 text-xs leading-relaxed text-muted-ink">
              <span className="mb-1 block font-semibold uppercase text-faint">
                Student Submitted Text:
              </span>
              <p className="whitespace-pre-wrap">
                {detail?.extracted_text || "Submission content registered."}
              </p>
            </div>

            {/* Public Web Citations If Found */}
            {detail?.webSources && detail.webSources.length > 0 && (
              <div className="mt-4 rounded-lg border border-blue-soft bg-blue-soft/30 p-3 text-xs">
                <span className="mb-1 block font-semibold uppercase tracking-[0.12em] text-blue">
                  Public Web Citations Detected:
                </span>
                {detail.webSources.map((source, sIdx) => (
                  <div key={sIdx} className="mt-1.5 border-t border-line/50 pt-1.5">
                    <a
                      href={source.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1 font-medium text-blue hover:underline"
                    >
                      {source.title || source.url}
                      <ExternalLink className="size-3" />
                    </a>
                    <p className="mt-0.5 text-[11px] text-muted-ink">{source.snippet}</p>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* Column 2: Rubric Evaluation Breakdown */}
          <section className="rounded-[14px] border border-line bg-card p-5 xl:col-span-4">
            <div className="mb-4 flex items-center justify-between">
              <p className="text-sm font-semibold">Rubric Criteria Scores</p>
              <span className="text-[11px] text-faint">Benchmarked to Reference</span>
            </div>

            <div className="space-y-4">
              {criteriaScores.map((crit, idx) => (
                <div key={idx} className="rounded-lg border border-line bg-paper p-3">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-ink">{crit.criterion_name}</span>
                    {editing ? (
                      <Input
                        type="number"
                        value={crit.score}
                        onChange={(e) => {
                          const val = Number(e.target.value);
                          const next = [...criteriaScores];
                          next[idx].score = val;
                          setCriteriaScores(next);
                          setEditedScore(next.reduce((sum, c) => sum + (c.score || 0), 0));
                        }}
                        className="h-7 w-16 text-center"
                      />
                    ) : (
                      <span className="font-bold text-ink">
                        {crit.score}/{crit.max || 25}
                      </span>
                    )}
                  </div>
                  {crit.rationale && (
                    <p className="mt-1.5 text-[11px] text-muted-ink">{crit.rationale}</p>
                  )}
                </div>
              ))}
            </div>

            <div className="mt-5 border-t border-line pt-4">
              <label className="text-[11px] font-semibold uppercase tracking-[0.14em] text-faint">
                Teacher Feedback & Guidance
              </label>
              <Textarea
                value={teacherFeedback}
                onChange={(e) => setTeacherFeedback(e.target.value)}
                rows={3}
                className="mt-2 text-xs"
                placeholder="Feedback to be shared with the student..."
              />
            </div>
          </section>

          {/* Column 3: Summary & Teacher Stamp */}
          <section className="flex flex-col rounded-[14px] border border-line bg-card p-5 xl:col-span-4">
            <div className="mb-3 flex items-center justify-between">
              <p className="text-sm font-semibold">Final Grade Stamp</p>
              <Pill tone={currentSub.status === "approved" ? "sage" : "lav"}>
                {currentSub.status === "approved" ? "Approved" : "Awaiting Stamp"}
              </Pill>
            </div>

            <div className="flex items-end gap-3 rounded-[11px] border border-line bg-paper px-4 py-4">
              <p className="font-display text-5xl leading-none text-ink">{editedScore}</p>
              <div className="pb-1">
                <p className="text-xs text-muted-ink">Out of 100 marks</p>
                <p className="mt-0.5 text-[11px] text-faint">Teacher has final authority</p>
              </div>
            </div>

            <div className="mt-4 rounded-[10px] border border-lav bg-lav-soft px-3 py-2.5 text-[11px] leading-snug text-muted-ink">
              "AI suggests. You stamp." — No AI score is officially recorded without your direct
              confirmation.
            </div>

            <div className="mt-auto flex flex-col gap-2 pt-6">
              <Button onClick={handleApproveGrade} className="bg-ink text-card hover:bg-ink/90">
                <Check className="mr-1.5 size-4" />
                Approve Grade · Final {editedScore}/100
              </Button>
              <Button variant="outline" onClick={() => setEditing(!editing)}>
                {editing ? "Finish Score Edits" : "Edit Rubric Marks"}
              </Button>
            </div>
          </section>
        </div>
      ) : (
        <div className="rounded-lg border border-dashed border-line p-8 text-center text-xs text-faint">
          Select a student submission above to begin review.
        </div>
      )}
    </>
  );
}

// =========================================================================
// Live Gradebook View
// =========================================================================

function GradebookView({
  course,
  assignment,
  submissions,
  showToast,
}: {
  course: APICourse | null;
  assignment: APIAssignment | null;
  submissions: SubmissionItem[];
  showToast: (msg: string) => void;
}) {
  // Dropdown open state for export options menu
  const [exportMenuOpen, setExportMenuOpen] = useState(false);
  // Auto-approve high-confidence AI grades toggle state
  const [autoApprove, setAutoApprove] = useState(false);

  // If no course is active, render empty course selection notice
  if (!course) {
    return (
      <div className="rounded-[14px] border border-dashed border-line p-12 text-center animate-fade-up">
        <BarChart3 className="mx-auto size-10 text-faint mb-3" />
        <h3 className="font-display text-xl text-ink">No Active Course Selected</h3>
        <p className="mt-1 text-xs text-muted-ink">
          Select or create a course to inspect its gradebook.
        </p>
      </div>
    );
  }

  // Helper function to trigger browser download of RFC-4180 / XLSX gradebook artifact
  const handleTriggerExport = (url: string, label: string) => {
    // Open download link in browser window to initiate file transfer
    window.open(url, "_blank");
    // Close export options dropdown menu
    setExportMenuOpen(false);
    // Show confirmation toast
    showToast(`Generating and exporting ${label}...`);
  };

  // Toggle handler for high-confidence auto-approval setting
  const handleToggleAutoApprove = async () => {
    try {
      const nextVal = !autoApprove;
      await api.gradebook.toggleAutoApprove(course.id, nextVal);
      setAutoApprove(nextVal);
      showToast(`High-confidence auto-approval ${nextVal ? "enabled" : "disabled"} for ${course.code}.`);
    } catch (err: any) {
      showToast(`Setting update notice: ${err?.message || "Failed to update"}`);
    }
  };

  return (
    <>
      <SectionTitle
        eyebrow={`Gradebook · ${course.code} · Section ${course.section || "A"}`}
        title="Course Gradebook & LMS Exports"
        description="Comprehensive spreadsheet view of student marks, review approval status, and integrity indicators. AI suggests. You stamp."
        action={
          <div className="flex flex-wrap items-center gap-3">
            {/* Auto-Approve Toggle */}
            <div className="flex items-center gap-2 rounded-lg border border-line bg-card px-3 py-1.5 shadow-2xs">
              <span className="text-xs text-muted-ink">Auto-approve &gt;= 90% confidence:</span>
              <button
                type="button"
                onClick={handleToggleAutoApprove}
                className={cn(
                  "relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none",
                  autoApprove ? "bg-sage" : "bg-line"
                )}
                title="Automatically stamp AI recommendations with >=90% model confidence"
              >
                <span
                  className={cn(
                    "pointer-events-none inline-block size-4 transform rounded-full bg-white shadow-sm ring-0 transition duration-200 ease-in-out",
                    autoApprove ? "translate-x-4" : "translate-x-0"
                  )}
                />
              </button>
            </div>

            {/* Export Dropdown Menu */}
            <div className="relative">
              <Button
                variant="outline"
                onClick={() => setExportMenuOpen(!exportMenuOpen)}
                className="gap-1.5 text-xs border-line bg-card hover:bg-paper"
              >
                <Download className="size-3.5 text-amber-ink" />
                Export Gradebook <ChevronDown className="size-3 text-muted-ink" />
              </Button>

              {exportMenuOpen && (
                <div className="absolute right-0 top-full z-50 mt-1.5 w-64 rounded-xl border border-line bg-card p-1.5 shadow-lg animate-in fade-in-50 zoom-in-95">
                  <div className="px-2.5 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-faint">
                    Select Export Format
                  </div>
                  {/* Draft CSV Option */}
                  <button
                    type="button"
                    onClick={() =>
                      handleTriggerExport(
                        api.gradebook.getExportCsvUrl(course.id, "draft", "default", assignment?.id),
                        "Draft CSV"
                      )
                    }
                    className="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left text-xs text-ink hover:bg-paper"
                  >
                    <FileSpreadsheet className="size-4 text-lav" />
                    <div>
                      <p className="font-medium">Draft CSV (AI Suggestions)</p>
                      <p className="text-[10px] text-muted-ink">Includes unapproved draft grades</p>
                    </div>
                  </button>
                  {/* Final Approved CSV Option */}
                  <button
                    type="button"
                    onClick={() =>
                      handleTriggerExport(
                        api.gradebook.getExportCsvUrl(course.id, "final", "default", assignment?.id),
                        "Final Approved CSV"
                      )
                    }
                    className="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left text-xs text-ink hover:bg-paper"
                  >
                    <CheckSquare className="size-4 text-sage" />
                    <div>
                      <p className="font-medium">Final CSV (Approved Grades Only)</p>
                      <p className="text-[10px] text-muted-ink">Official teacher-stamped marks</p>
                    </div>
                  </button>
                  {/* Google Classroom CSV Option */}
                  <button
                    type="button"
                    onClick={() =>
                      handleTriggerExport(
                        api.gradebook.getExportCsvUrl(course.id, "final", "google_classroom", assignment?.id),
                        "Google Classroom CSV"
                      )
                    }
                    className="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left text-xs text-ink hover:bg-paper"
                  >
                    <Globe className="size-4 text-blue" />
                    <div>
                      <p className="font-medium">Google Classroom CSV</p>
                      <p className="text-[10px] text-muted-ink">Compatible with GC Gradebook import</p>
                    </div>
                  </button>
                  {/* Moodle CSV Option */}
                  <button
                    type="button"
                    onClick={() =>
                      handleTriggerExport(
                        api.gradebook.getExportCsvUrl(course.id, "final", "moodle", assignment?.id),
                        "Moodle Gradebook CSV"
                      )
                    }
                    className="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left text-xs text-ink hover:bg-paper"
                  >
                    <Layers className="size-4 text-amber-ink" />
                    <div>
                      <p className="font-medium">Moodle Gradebook CSV</p>
                      <p className="text-[10px] text-muted-ink">Standard Moodle columns schema</p>
                    </div>
                  </button>
                  {/* Excel XLSX Option */}
                  <button
                    type="button"
                    onClick={() =>
                      handleTriggerExport(
                        api.gradebook.getExportXlsxUrl(course.id, "final", assignment?.id),
                        "Excel (.xlsx) Workbook"
                      )
                    }
                    className="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left text-xs text-ink hover:bg-paper border-t border-line mt-1 pt-2"
                  >
                    <FileText className="size-4 text-emerald-600" />
                    <div>
                      <p className="font-medium">Excel (.xlsx) Workbook</p>
                      <p className="text-[10px] text-muted-ink">Multi-tab workbook with audit SHA-256</p>
                    </div>
                  </button>
                </div>
              )}
            </div>
          </div>
        }
      />

      <div className="rounded-[14px] border border-line bg-card p-5">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead>
              <tr className="border-b border-line text-[10px] uppercase tracking-[0.14em] text-faint">
                <th className="px-3 py-3">Student</th>
                <th className="px-3 py-3">Roll</th>
                <th className="px-3 py-3">Final Score</th>
                <th className="px-3 py-3">Peer Similarity</th>
                <th className="px-3 py-3">AI Likelihood</th>
                <th className="px-3 py-3">Web Citations</th>
                <th className="px-3 py-3">Status</th>
              </tr>
            </thead>
            <tbody>
              {submissions.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-xs text-faint">
                    No submissions recorded yet for this assignment.
                  </td>
                </tr>
              ) : (
                submissions.map((s) => (
                  <tr key={s.id} className="border-b border-line last:border-0 hover:bg-paper/40 transition-colors">
                    <td className="px-3 py-3.5 font-medium">{s.student}</td>
                    <td className="px-3 py-3.5 text-xs text-faint">{s.roll}</td>
                    <td className="px-3 py-3.5 font-display text-lg">
                      {s.score}
                      <span className="text-xs text-muted-ink">/100</span>
                    </td>
                    <td className="px-3 py-3.5">
                      <span
                        className={
                          s.similarity >= 85 ? "font-semibold text-clay" : "text-muted-ink"
                        }
                      >
                        {s.similarity}%
                      </span>
                    </td>
                    <td className="px-3 py-3.5">
                      <Pill tone={s.aiContent >= 60 ? "amber" : "sage"}>{s.aiContent}%</Pill>
                    </td>
                    <td className="px-3 py-3.5">
                      <Pill tone={(s.webPlagiarism || 0) >= 20 ? "clay" : "sage"}>
                        {s.webPlagiarism || 0}%
                      </Pill>
                    </td>
                    <td className="px-3 py-3.5">
                      <Pill
                        tone={
                          s.status === "approved" ? "sage" : s.status === "flagged" ? "clay" : "lav"
                        }
                      >
                        {s.status}
                      </Pill>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}

// =========================================================================
// Reports & Settings Views
// =========================================================================

function ReportsView({
  course,
  submissions,
  showToast,
}: {
  course: APICourse | null;
  submissions: SubmissionItem[];
  showToast: (msg: string) => void;
}) {
  return (
    <>
      <SectionTitle
        eyebrow="Compliance & Analytics"
        title="Integrity & Audit Reports"
        description="PII pseudonymization logging and longitudinal similarity trend monitoring."
      />

      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-[14px] border border-line bg-card p-5">
          <h2 className="font-display text-xl">PII Pseudonymization & Data Minimization</h2>
          <p className="mt-2 text-xs leading-relaxed text-muted-ink">
            All student identifiers (Names, Roll Numbers, Emails) undergo Fernet field-level
            encryption at rest. When submissions are passed to Google Gemini for evaluation, student
            identities are pseudonymized into deterministic tokens (e.g. STUDENT_A3F89B), ensuring
            zero student PII ever leaves your security perimeter.
          </p>
          <div className="mt-4 rounded bg-sage-soft p-3 text-xs text-sage font-medium">
            Active: Cryptographic Data Minimization & Encryption Enforced
          </div>
        </div>

        <div className="rounded-[14px] border border-line bg-card p-5">
          <h2 className="font-display text-xl">Audit Trail & Teacher Accountability</h2>
          <p className="mt-2 text-xs leading-relaxed text-muted-ink">
            Every grade approval, threshold adjustment, and feedback modification produces an
            immutable audit record in the database with timestamp, actor ID, and IP address.
          </p>
          <div className="mt-4 rounded bg-lav-soft p-3 text-xs text-ink font-medium">
            Active: Database Audit Logs & Storage Mirroring
          </div>
        </div>
      </div>
    </>
  );
}

function SettingsView({
  currentUser,
  onClearMockData,
  showToast,
}: {
  currentUser: UserProfile | null;
  onClearMockData: () => void;
  showToast: (msg: string) => void;
}) {
  // Trash bin modal open state
  const [trashModalOpen, setTrashModalOpen] = useState(false);
  // Soft-deleted items list from GET /api/v1/trash
  const [trashItems, setTrashItems] = useState<any[]>([]);
  // Trash bin loading indicator
  const [loadingTrash, setLoadingTrash] = useState(false);
  // Erasure request modal state
  const [erasureModalOpen, setErasureModalOpen] = useState(false);
  // Erasure request reason input
  const [erasureReason, setErasureReason] = useState("");
  // Submitting erasure request indicator
  const [submittingErasure, setSubmittingErasure] = useState(false);

  // Load trash bin items from API
  const handleOpenTrash = async () => {
    setTrashModalOpen(true);
    setLoadingTrash(true);
    try {
      const res = await api.trash.list();
      setTrashItems(res?.items || []);
    } catch (err: any) {
      showToast(`Trash load notice: ${err?.message || "Failed to load trash"}`);
    } finally {
      setLoadingTrash(false);
    }
  };

  // Restore item from trash bin
  const handleRestoreItem = async (entityType: string, id: string) => {
    try {
      await api.trash.restore(entityType, id);
      showToast(`Restored ${entityType} successfully.`);
      // Refresh trash list
      const res = await api.trash.list();
      setTrashItems(res?.items || []);
    } catch (err: any) {
      showToast(`Restore notice: ${err?.message || "Failed to restore"}`);
    }
  };

  // Permanent cascade purge
  const handlePermanentPurge = async (entityType: string, id: string) => {
    try {
      await api.trash.permanentDelete(entityType, id);
      showToast(`Permanently deleted ${entityType}.`);
      // Refresh trash list
      const res = await api.trash.list();
      setTrashItems(res?.items || []);
    } catch (err: any) {
      showToast(`Purge notice: ${err?.message || "Failed to permanently purge"}`);
    }
  };

  // Submit GDPR/DPDP Erasure Request
  const handleSubmitErasure = async () => {
    if (!erasureReason.trim()) {
      showToast("Please provide a reason for the erasure request.");
      return;
    }
    setSubmittingErasure(true);
    try {
      const res = await api.privacy.submitErasureRequest(erasureReason.trim());
      showToast(`Erasure ticket submitted: ${res?.ticket_id || "Ticket accepted"}. Retained for 30 days.`);
      setErasureModalOpen(false);
      setErasureReason("");
    } catch (err: any) {
      showToast(`Erasure request notice: ${err?.message || "Failed to submit request"}`);
    } finally {
      setSubmittingErasure(false);
    }
  };

  return (
    <>
      <SectionTitle
        eyebrow="Preferences & Compliance"
        title="Account, Privacy & Governance Settings"
        description="PII pseudonymization, DPDP/GDPR data portability, 30-day trash retention, and educator privacy controls."
      />

      <div className="grid gap-5 md:grid-cols-2 max-w-4xl">
        {/* Instructor Profile Card */}
        <div className="rounded-[14px] border border-line bg-card p-5">
          <h2 className="font-display text-xl text-ink">Instructor Profile</h2>
          <div className="mt-4 space-y-3 text-sm">
            <div>
              <label className="text-[11px] uppercase tracking-[0.14em] text-faint">Name</label>
              <p className="font-medium text-ink">{currentUser?.name || "Educator / Instructor"}</p>
            </div>
            <div>
              <label className="text-[11px] uppercase tracking-[0.14em] text-faint">Email</label>
              <p className="text-muted-ink">{currentUser?.email || "Signed in as Instructor"}</p>
            </div>
            <div>
              <label className="text-[11px] uppercase tracking-[0.14em] text-faint">Role</label>
              <p className="text-muted-ink">{currentUser?.role || "Instructor · Computer Science"}</p>
            </div>
          </div>
        </div>

        {/* 30-Day Trash Bin & Retention Manager */}
        <div className="rounded-[14px] border border-line bg-card p-5">
          <div className="flex items-center gap-2">
            <History className="size-5 text-amber-ink" />
            <h2 className="font-display text-xl text-ink">30-Day Trash Bin</h2>
          </div>
          <p className="mt-2 text-xs leading-relaxed text-muted-ink">
            Deleted courses, assignments, and submissions are preserved in the 30-day trash bin
            before permanent purge. You can restore them anytime within the 30-day retention window.
          </p>
          <div className="mt-4">
            <Button
              variant="outline"
              onClick={handleOpenTrash}
              className="gap-1.5 text-xs border-line bg-card hover:bg-paper"
            >
              <Trash2 className="size-3.5 text-amber-ink" /> Open Trash Bin Manager
            </Button>
          </div>
        </div>
      </div>

      <div className="mt-5 grid gap-5 md:grid-cols-2 max-w-4xl">
        {/* GDPR / DPDP Data Portability & Rights */}
        <div className="rounded-[14px] border border-line bg-card p-5">
          <div className="flex items-center gap-2">
            <Lock className="size-5 text-indigo-600" />
            <h2 className="font-display text-xl text-ink">Data Portability & Erasure</h2>
          </div>
          <p className="mt-2 text-xs leading-relaxed text-muted-ink">
            Under GDPR Art. 20 and DPDP Sec. 12, educators own their data. Download a complete
            ZIP archive of all courses, rubrics, submissions, and audit logs, or submit an erasure ticket.
          </p>
          <div className="mt-4 flex flex-wrap gap-2.5">
            <Button
              variant="outline"
              onClick={() => {
                window.open(api.privacy.getExportAllDataUrl(), "_blank");
                showToast("Generating complete ZIP data archive...");
              }}
              className="gap-1.5 text-xs border-line bg-card hover:bg-paper"
            >
              <Download className="size-3.5 text-sage" /> Download All My Data (ZIP)
            </Button>
            <Button
              variant="ghost"
              onClick={() => setErasureModalOpen(true)}
              className="text-xs text-clay hover:bg-clay-soft"
            >
              Erasure Request
            </Button>
          </div>
        </div>

        {/* Legal Policies & Institutional Documentation */}
        <div className="rounded-[14px] border border-line bg-card p-5">
          <h2 className="font-display text-xl text-ink">Institutional Privacy & Governance</h2>
          <p className="mt-2 text-xs leading-relaxed text-muted-ink">
            Verism operates under the &ldquo;AI suggests. You stamp.&rdquo; model with zero student PII leakage,
            cryptographic student pseudonymization, and full DPDP/GDPR educator data rights.
          </p>
          <div className="mt-4 flex flex-wrap gap-2 text-xs">
            <a
              href="/api/v1/legal/privacy"
              target="_blank"
              rel="noreferrer"
              className="rounded-md border border-line bg-paper px-2.5 py-1.5 font-medium text-ink hover:text-amber-ink transition-colors flex items-center gap-1"
            >
              Privacy Policy <ExternalLink className="size-3" />
            </a>
            <a
              href="/api/v1/legal/terms"
              target="_blank"
              rel="noreferrer"
              className="rounded-md border border-line bg-paper px-2.5 py-1.5 font-medium text-ink hover:text-amber-ink transition-colors flex items-center gap-1"
            >
              Terms of Service <ExternalLink className="size-3" />
            </a>
            <a
              href="/api/v1/legal/dpa"
              target="_blank"
              rel="noreferrer"
              className="rounded-md border border-line bg-paper px-2.5 py-1.5 font-medium text-ink hover:text-amber-ink transition-colors flex items-center gap-1"
            >
              Data Processing Agreement <ExternalLink className="size-3" />
            </a>
          </div>
        </div>
      </div>

      {/* Database Maintenance & Custom Data */}
      <div className="mt-5 rounded-[14px] border border-line bg-card p-5 max-w-4xl">
        <h2 className="font-display text-xl text-clay">Database Maintenance & Custom Data</h2>
        <p className="mt-1 text-xs text-muted-ink">
          Purge all seeded demo courses and submissions so you can populate Verism strictly with
          your own real-world classes, students, and assignment exemplars.
        </p>
        <div className="mt-4">
          <Button
            variant="outline"
            className="text-clay hover:bg-clay-soft text-xs"
            onClick={onClearMockData}
          >
            <Trash2 className="mr-1.5 size-4" /> Purge Demo Seed Data
          </Button>
        </div>
      </div>

      {/* 30-Day Trash Bin Modal */}
      {trashModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-xs">
          <div className="w-full max-w-2xl rounded-2xl border border-line bg-card p-6 shadow-xl animate-in fade-in-50 zoom-in-95">
            <div className="flex items-center justify-between border-b border-line pb-4">
              <div className="flex items-center gap-2">
                <Trash2 className="size-5 text-amber-ink" />
                <h3 className="font-display text-xl text-ink">30-Day Trash Bin</h3>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setTrashModalOpen(false)}
                className="size-8 text-faint hover:text-ink"
              >
                <X className="size-4" />
              </Button>
            </div>

            <div className="mt-4 max-h-96 overflow-y-auto">
              {loadingTrash ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="size-6 animate-spin text-amber-ink" />
                </div>
              ) : trashItems.length === 0 ? (
                <div className="py-12 text-center text-xs text-muted-ink">
                  <CheckCircle2 className="mx-auto size-8 text-sage mb-2" />
                  Your trash bin is empty. No deleted entities awaiting purge.
                </div>
              ) : (
                <div className="space-y-2">
                  {trashItems.map((item) => (
                    <div
                      key={`${item.entity_type}-${item.id}`}
                      className="flex items-center justify-between gap-3 rounded-lg border border-line bg-paper p-3 text-xs"
                    >
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-ink">{item.name || item.id}</span>
                          <span className="rounded bg-lav-soft px-1.5 py-0.5 text-[10px] font-semibold text-ink">
                            {item.entity_type}
                          </span>
                        </div>
                        <p className="mt-0.5 text-[11px] text-faint">
                          {item.days_remaining} days remaining before permanent purge
                        </p>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleRestoreItem(item.entity_type, item.id)}
                          className="h-7 text-xs border-line bg-card hover:bg-paper"
                        >
                          <RotateCcw className="mr-1 size-3 text-sage" /> Restore
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handlePermanentPurge(item.entity_type, item.id)}
                          className="h-7 text-xs text-clay hover:bg-clay-soft"
                        >
                          Purge Now
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="mt-5 border-t border-line pt-3 text-right">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setTrashModalOpen(false)}
                className="text-xs"
              >
                Close
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* GDPR / DPDP Erasure Request Modal */}
      {erasureModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-xs">
          <div className="w-full max-w-md rounded-2xl border border-line bg-card p-6 shadow-xl animate-in fade-in-50 zoom-in-95">
            <div className="flex items-center justify-between border-b border-line pb-3">
              <h3 className="font-display text-lg text-ink">Submit Erasure Request</h3>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setErasureModalOpen(false)}
                className="size-8 text-faint hover:text-ink"
              >
                <X className="size-4" />
              </Button>
            </div>
            <p className="mt-3 text-xs leading-relaxed text-muted-ink">
              Under GDPR Art. 17 and DPDP Sec. 12, this ticket initiates cryptographic deletion of all
              associated educator logs and student submission vectors within 30 days.
            </p>
            <div className="mt-4">
              <label className="text-xs font-semibold text-ink">Reason for Erasure</label>
              <Textarea
                value={erasureReason}
                onChange={(e) => setErasureReason(e.target.value)}
                placeholder="e.g. End of academic semester, institutional departure..."
                className="mt-1 text-xs"
                rows={3}
              />
            </div>
            <div className="mt-5 flex justify-end gap-2 border-t border-line pt-3">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setErasureModalOpen(false)}
                className="text-xs"
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={handleSubmitErasure}
                disabled={submittingErasure}
                className="bg-clay text-white hover:bg-clay/90 text-xs"
              >
                {submittingErasure ? <Loader2 className="mr-1.5 size-3.5 animate-spin" /> : null}
                Confirm Erasure Ticket
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

// =========================================================================
// Modals: Authentication, Add Course, Add Assignment, Manual Submission
// =========================================================================

function AuthModal({
  tab,
  setTab,
  loading,
  error,
  onClose,
  onSuccess,
  setLoading,
  setError,
}: {
  tab: "login" | "signup";
  setTab: (tab: "login" | "signup") => void;
  loading: boolean;
  error: string;
  onClose: () => void;
  onSuccess: (user: UserProfile) => void;
  setLoading: (l: boolean) => void;
  setError: (e: string) => void;
}) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("Instructor · Computer Science");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      if (tab === "signup") {
        const res = await api.auth.signUp({ name, email, password, role });
        onSuccess(res.user);
      } else {
        const res = await api.auth.login({ email, password });
        onSuccess(res.user);
      }
    } catch (err: any) {
      setError(err.message || "Authentication failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-ink/30 backdrop-blur-sm p-4">
      <div className="w-full max-w-md rounded-[16px] border border-line bg-card p-6 shadow-2xl animate-fade-up">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="grid size-7 place-items-center rounded bg-ink text-card text-xs font-bold">
              V
            </div>
            <h2 className="font-display text-xl">
              {tab === "login" ? "Sign In to Verism" : "Create Teacher Account"}
            </h2>
          </div>
          <Button size="icon" variant="ghost" onClick={onClose}>
            <X className="size-4" />
          </Button>
        </div>

        <div className="mt-4 flex border-b border-line">
          <button
            onClick={() => {
              setTab("login");
              setError("");
            }}
            className={cn(
              "flex-1 py-2 text-xs font-semibold text-center border-b-2",
              tab === "login" ? "border-ink text-ink" : "border-transparent text-muted-ink",
            )}
          >
            Sign In
          </button>
          <button
            onClick={() => {
              setTab("signup");
              setError("");
            }}
            className={cn(
              "flex-1 py-2 text-xs font-semibold text-center border-b-2",
              tab === "signup" ? "border-ink text-ink" : "border-transparent text-muted-ink",
            )}
          >
            Sign Up (New User)
          </button>
        </div>

        {error && (
          <div className="mt-3 rounded bg-clay-soft p-2.5 text-xs text-clay font-medium">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-4 space-y-3">
          {tab === "signup" && (
            <>
              <div>
                <label className="text-[11px] uppercase tracking-[0.12em] text-faint">
                  Full Name
                </label>
                <Input
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Dr. Alan Turing"
                  className="mt-1"
                />
              </div>
              <div>
                <label className="text-[11px] uppercase tracking-[0.12em] text-faint">
                  Role / Department
                </label>
                <Input
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  placeholder="e.g. Professor · Computer Science"
                  className="mt-1"
                />
              </div>
            </>
          )}

          <div>
            <label className="text-[11px] uppercase tracking-[0.12em] text-faint">
              Email Address
            </label>
            <Input
              required
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="instructor@university.edu"
              className="mt-1"
            />
          </div>

          <div>
            <label className="text-[11px] uppercase tracking-[0.12em] text-faint">Password</label>
            <Input
              required
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="mt-1"
            />
          </div>

          <Button
            type="submit"
            disabled={loading}
            className="mt-4 w-full bg-ink text-card hover:bg-ink/90"
          >
            {loading ? "Processing..." : tab === "login" ? "Sign In" : "Register Account"}
          </Button>
        </form>

        <p className="mt-4 text-center text-[11px] text-faint">
          Synced across Database & Authentication tables.
        </p>
      </div>
    </div>
  );
}

function AddCourseModal({
  onClose,
  onCreated,
  showToast,
}: {
  onClose: () => void;
  onCreated: (course: APICourse) => void;
  showToast: (msg: string) => void;
}) {
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [section, setSection] = useState("A");
  const [tone, setTone] = useState("lav");
  const [students, setStudents] = useState(48);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const created = await api.courses.create({
        name,
        code,
        section,
        tone,
        students_count: students,
      });
      onCreated(created);
    } catch (err: any) {
      showToast(`Error creating course: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-ink/30 backdrop-blur-sm p-4">
      <div className="w-full max-w-md rounded-[16px] border border-line bg-card p-6 shadow-2xl animate-fade-up">
        <div className="flex items-center justify-between">
          <h2 className="font-display text-xl">Add New Course</h2>
          <Button size="icon" variant="ghost" onClick={onClose}>
            <X className="size-4" />
          </Button>
        </div>

        <form onSubmit={handleSubmit} className="mt-4 space-y-3">
          <div>
            <label className="text-[11px] uppercase tracking-[0.12em] text-faint">
              Course Name
            </label>
            <Input
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Distributed Systems"
              className="mt-1"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[11px] uppercase tracking-[0.12em] text-faint">
                Course Code
              </label>
              <Input
                required
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="e.g. CS401"
                className="mt-1"
              />
            </div>
            <div>
              <label className="text-[11px] uppercase tracking-[0.12em] text-faint">Section</label>
              <Input
                value={section}
                onChange={(e) => setSection(e.target.value)}
                placeholder="A"
                className="mt-1"
              />
            </div>
          </div>
          <div>
            <label className="text-[11px] uppercase tracking-[0.12em] text-faint">
              Expected Students
            </label>
            <Input
              type="number"
              value={students}
              onChange={(e) => setStudents(Number(e.target.value))}
              className="mt-1"
            />
          </div>

          <Button
            type="submit"
            disabled={submitting}
            className="mt-4 w-full bg-ink text-card hover:bg-ink/90"
          >
            {submitting ? "Saving..." : "Create Course"}
          </Button>
        </form>
      </div>
    </div>
  );
}

function AddAssignmentModal({
  courseId,
  onClose,
  onCreated,
  showToast,
}: {
  courseId: string;
  onClose: () => void;
  onCreated: (assign: APIAssignment) => void;
  showToast: (msg: string) => void;
}) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [maxScore, setMaxScore] = useState(100);
  const [referenceText, setReferenceText] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const created = await api.assignments.create(courseId, {
        title,
        description,
        max_score: maxScore,
        reference_assignment_text: referenceText,
      });
      onCreated(created);
    } catch (err: any) {
      showToast(`Error creating assignment: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-ink/30 backdrop-blur-sm p-4">
      <div className="w-full max-w-lg rounded-[16px] border border-line bg-card p-6 shadow-2xl animate-fade-up max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between">
          <h2 className="font-display text-xl">Create Assignment & Benchmark</h2>
          <Button size="icon" variant="ghost" onClick={onClose}>
            <X className="size-4" />
          </Button>
        </div>

        <form onSubmit={handleSubmit} className="mt-4 space-y-3">
          <div>
            <label className="text-[11px] uppercase tracking-[0.12em] text-faint">
              Assignment Title
            </label>
            <Input
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Assignment 4 · Dijkstra & A* Graph Search"
              className="mt-1"
            />
          </div>
          <div>
            <label className="text-[11px] uppercase tracking-[0.12em] text-faint">
              Instructions / Prompt
            </label>
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Detailed instructions given to students..."
              className="mt-1 text-xs"
              rows={2}
            />
          </div>
          <div>
            <label className="text-[11px] uppercase tracking-[0.12em] text-faint">
              Maximum Score
            </label>
            <Input
              type="number"
              value={maxScore}
              onChange={(e) => setMaxScore(Number(e.target.value))}
              className="mt-1"
            />
          </div>
          <div>
            <div className="flex items-center justify-between">
              <label className="text-[11px] uppercase tracking-[0.12em] text-faint font-semibold">
                Reference Assignment (Ground Truth Solution)
              </label>
              <span className="text-[10px] text-sage">AI Benchmark</span>
            </div>
            <p className="mt-0.5 text-[11px] text-muted-ink">
              Paste the exemplar solution or reference code. The AI grading engine will benchmark
              student accuracy and technical depth against this text.
            </p>
            <Textarea
              value={referenceText}
              onChange={(e) => setReferenceText(e.target.value)}
              placeholder="Paste exemplar code, optimal algorithmic solution, or benchmark essay..."
              className="mt-1.5 font-mono text-xs"
              rows={5}
            />
          </div>

          <Button
            type="submit"
            disabled={submitting}
            className="mt-4 w-full bg-ink text-card hover:bg-ink/90"
          >
            {submitting ? "Creating..." : "Save Assignment & Exemplar"}
          </Button>
        </form>
      </div>
    </div>
  );
}

function ManualSubmissionModal({
  assignmentId,
  onClose,
  onCreated,
  showToast,
}: {
  assignmentId: string;
  onClose: () => void;
  onCreated: (sub: SubmissionItem) => void;
  showToast: (msg: string) => void;
}) {
  const [studentName, setStudentName] = useState("");
  const [studentRoll, setStudentRoll] = useState("");
  const [studentEmail, setStudentEmail] = useState("");
  const [text, setText] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const created = await api.submissions.createManual(assignmentId, {
        student_name: studentName,
        student_roll: studentRoll,
        student_email: studentEmail,
        extracted_text: text,
      });
      onCreated(created);
    } catch (err: any) {
      showToast(`Error creating submission: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-ink/30 backdrop-blur-sm p-4">
      <div className="w-full max-w-lg rounded-[16px] border border-line bg-card p-6 shadow-2xl animate-fade-up max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between">
          <h2 className="font-display text-xl">Direct Student Submission Input</h2>
          <Button size="icon" variant="ghost" onClick={onClose}>
            <X className="size-4" />
          </Button>
        </div>

        <form onSubmit={handleSubmit} className="mt-4 space-y-3">
          <div>
            <label className="text-[11px] uppercase tracking-[0.12em] text-faint">
              Student Full Name
            </label>
            <Input
              required
              value={studentName}
              onChange={(e) => setStudentName(e.target.value)}
              placeholder="e.g. Aisha Verma"
              className="mt-1"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[11px] uppercase tracking-[0.12em] text-faint">
                Roll / Student ID
              </label>
              <Input
                required
                value={studentRoll}
                onChange={(e) => setStudentRoll(e.target.value)}
                placeholder="e.g. 2024-082"
                className="mt-1"
              />
            </div>
            <div>
              <label className="text-[11px] uppercase tracking-[0.12em] text-faint">
                Student Email
              </label>
              <Input
                type="email"
                value={studentEmail}
                onChange={(e) => setStudentEmail(e.target.value)}
                placeholder="aisha.verma@university.edu"
                className="mt-1"
              />
            </div>
          </div>
          <div>
            <label className="text-[11px] uppercase tracking-[0.12em] text-faint">
              Submission Code or Essay Content
            </label>
            <Textarea
              required
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Paste student answer, algorithmic implementation, or essay text here..."
              className="mt-1.5 font-mono text-xs"
              rows={6}
            />
          </div>

          <Button
            type="submit"
            disabled={submitting}
            className="mt-4 w-full bg-ink text-card hover:bg-ink/90"
          >
            {submitting ? "Saving..." : "Register Submission"}
          </Button>
        </form>
      </div>
    </div>
  );
}

function EditAssignmentModal({
  assignment,
  onClose,
  onUpdated,
  showToast,
}: {
  assignment: APIAssignment;
  onClose: () => void;
  onUpdated: (assign: APIAssignment) => void;
  showToast: (msg: string) => void;
}) {
  const [title, setTitle] = useState(assignment.title);
  const [description, setDescription] = useState(assignment.description || "");
  const [maxScore, setMaxScore] = useState(assignment.max_score || 100);
  const [referenceText, setReferenceText] = useState(assignment.reference_assignment_text || "");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const updated = await api.assignments.update(assignment.id, {
        title,
        description,
        max_score: maxScore,
        reference_assignment_text: referenceText,
      });
      onUpdated(updated);
    } catch (err: any) {
      showToast(`Error updating assignment: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-ink/30 backdrop-blur-sm p-4">
      <div className="w-full max-w-lg rounded-[16px] border border-line bg-card p-6 shadow-2xl animate-fade-up max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between">
          <h2 className="font-display text-xl">Edit Assignment & Benchmark Exemplar</h2>
          <Button size="icon" variant="ghost" onClick={onClose}>
            <X className="size-4" />
          </Button>
        </div>

        <form onSubmit={handleSubmit} className="mt-4 space-y-3">
          <div>
            <label className="text-[11px] uppercase tracking-[0.12em] text-faint">
              Assignment Title
            </label>
            <Input
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="mt-1"
            />
          </div>
          <div>
            <label className="text-[11px] uppercase tracking-[0.12em] text-faint">
              Instructions / Prompt
            </label>
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="mt-1 text-xs"
              rows={2}
            />
          </div>
          <div>
            <label className="text-[11px] uppercase tracking-[0.12em] text-faint">
              Maximum Score
            </label>
            <Input
              type="number"
              value={maxScore}
              onChange={(e) => setMaxScore(Number(e.target.value))}
              className="mt-1"
            />
          </div>
          <div>
            <div className="flex items-center justify-between">
              <label className="text-[11px] uppercase tracking-[0.12em] text-faint font-semibold">
                Reference Assignment (Ground Truth Solution)
              </label>
              <span className="text-[10px] text-sage font-medium">Active benchmark</span>
            </div>
            <p className="mt-0.5 text-[11px] text-muted-ink">
              Paste the exemplar solution or reference code. The AI grading engine will benchmark
              student accuracy and technical depth against this text.
            </p>
            <Textarea
              value={referenceText}
              onChange={(e) => setReferenceText(e.target.value)}
              placeholder="Paste exemplar code, optimal algorithmic solution, or benchmark essay..."
              className="mt-1.5 font-mono text-xs"
              rows={6}
            />
          </div>

          <Button
            type="submit"
            disabled={submitting}
            className="mt-4 w-full bg-ink text-card hover:bg-ink/90"
          >
            {submitting ? "Updating..." : "Save Changes & Benchmark"}
          </Button>
        </form>
      </div>
    </div>
  );
}
