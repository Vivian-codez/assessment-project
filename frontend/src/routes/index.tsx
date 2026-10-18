import { createFileRoute } from "@tanstack/react-router";
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
} from "lucide-react";
import { useState, useEffect } from "react";
import type { LucideIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import {
  api,
  getAuthToken,
  clearAuthToken,
  getCachedUser,
  type Course as APICourse,
  type Assignment as APIAssignment,
  type SubmissionItem,
  type SubmissionDetail,
  type UserProfile,
  type Rubric,
  type SimilarityMatch,
} from "@/lib/api";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Verism AI — Teacher Review & Auto-Grading Console" },
      {
        name: "description",
        content:
          "Authoritative, teacher-first workspace for automated rubric grading, reference assignment benchmarking, and 3-way plagiarism audits.",
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
    <span className={cn("inline-flex items-center rounded-md px-2.5 py-1 text-[11px] font-medium", `tone-${tone}`)}>
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
        {eyebrow && <p className="mb-2 text-[11px] uppercase tracking-[0.2em] text-faint">{eyebrow}</p>}
        <h1 className="font-display text-3xl leading-tight tracking-tight text-ink sm:text-4xl">{title}</h1>
        {description && <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted-ink">{description}</p>}
      </div>
      {action}
    </div>
  );
}

function VerismApp() {
  const [view, setView] = useState<ViewKey>("dashboard");
  const [mobileNav, setMobileNav] = useState(false);
  const [notifications, setNotifications] = useState(false);
  const [search, setSearch] = useState("");
  const [toast, setToast] = useState("");

  // Authentication State
  const [currentUser, setCurrentUser] = useState<UserProfile | null>(getCachedUser());
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [authTab, setAuthTab] = useState<"login" | "signup">("login");
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState("");

  // Live Backend Data States
  const [courses, setCourses] = useState<APICourse[]>([]);
  const [selectedCourseId, setSelectedCourseId] = useState<string>("");
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

  // Evaluation & Batch Job Polling
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingProgress, setProcessingProgress] = useState(0);

  const showToast = (message: string) => {
    setToast(message);
    window.setTimeout(() => setToast(""), 3500);
  };

  // Initial Data Fetch
  useEffect(() => {
    loadUser();
    loadCourses();
  }, []);

  const loadUser = async () => {
    try {
      const user = await api.auth.getMe();
      setCurrentUser(user);
    } catch {
      // not logged in yet or default fallback
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

  const loadAssignments = async (courseId: string) => {
    try {
      const list = await api.assignments.listByCourse(courseId);
      setAssignments(list);
      if (list.length > 0 && list[0]) {
        const firstAssign = list[0];
        setSelectedAssignmentId(firstAssign.id);
        loadSubmissions(firstAssign.id);
        loadSimilarity(firstAssign.id);
      } else {
        setSelectedAssignmentId("");
        setSubmissions([]);
        setSimilarityMatches([]);
      }
    } catch (e: any) {
      console.error(e);
    }
  };

  const loadSubmissions = async (assignmentId: string) => {
    try {
      const subs = await api.submissions.listByAssignment(assignmentId);
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
    loadAssignments(courseId);
  };

  const handleSelectAssignment = (assignId: string) => {
    setSelectedAssignmentId(assignId);
    loadSubmissions(assignId);
    loadSimilarity(assignId);
  };

  const navigate = (next: ViewKey) => {
    setView(next);
    setMobileNav(false);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const [editAssignmentOpen, setEditAssignmentOpen] = useState(false);

  const currentCourse: APICourse | null = courses.find((c) => c.id === selectedCourseId) || (courses.length > 0 && courses[0] ? courses[0] : null);

  const currentAssignment: APIAssignment | null = assignments.find((a) => a.id === selectedAssignmentId) || (assignments.length > 0 && assignments[0] ? assignments[0] : null);

  const pendingCount = submissions.filter((s) => s.status !== "approved").length;

  const handleDeleteCourse = async (courseId: string) => {
    if (!window.confirm("Are you sure you want to delete this course and all its data?")) return;
    try {
      await api.courses.delete(courseId);
      const remaining = courses.filter((c) => c.id !== courseId);
      setCourses(remaining);
      if (selectedCourseId === courseId) {
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
      showToast("Course deleted successfully.");
    } catch (e: any) {
      showToast(`Error deleting course: ${e.message}`);
    }
  };

  const handleDeleteAssignment = async (assignId: string) => {
    if (!window.confirm("Are you sure you want to delete this assignment?")) return;
    try {
      await api.assignments.delete(assignId);
      const remaining = assignments.filter((a) => a.id !== assignId);
      setAssignments(remaining);
      if (selectedAssignmentId === assignId) {
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
      showToast("Assignment deleted.");
    } catch (e: any) {
      showToast(`Error deleting assignment: ${e.message}`);
    }
  };

  const handleDeleteSubmission = async (subId: string) => {
    try {
      await api.submissions.delete(subId);
      setSubmissions(submissions.filter((s) => s.id !== subId));
      if (selectedSubmissionId === subId) {
        const remaining = submissions.filter((s) => s.id !== subId);
        setSelectedSubmissionId(remaining.length > 0 && remaining[0] ? remaining[0].id : "");
      }
      showToast("Submission removed.");
    } catch (e: any) {
      showToast(`Error deleting submission: ${e.message}`);
    }
  };

  const handleClearAllSubmissions = async () => {
    if (!selectedAssignmentId) return;
    if (!window.confirm("Are you sure you want to clear all submissions for this assignment to enter your own real data?")) return;
    try {
      await api.submissions.clearAll(selectedAssignmentId);
      setSubmissions([]);
      setSelectedSubmissionId("");
      setSimilarityMatches([]);
      showToast("All submissions cleared. Ready for your student data!");
    } catch (e: any) {
      showToast(`Error clearing submissions: ${e.message}`);
    }
  };

  const handleClearMockData = async () => {
    if (!window.confirm("Purge sample mock courses and records? This ensures a clean custom database.")) return;
    try {
      const res = await api.auth.clearMockData();
      showToast(res.message);
      await loadCourses();
    } catch (e: any) {
      showToast(`Error: ${e.message}`);
    }
  };

  // Trigger Live AI Auto-Grading & 3-Way Plagiarism Check
  const startAIAutoGrading = async () => {
    if (!selectedAssignmentId || isProcessing) return;
    setIsProcessing(true);
    setProcessingProgress(5);
    showToast("Dispatched batch evaluation to AI engine with Search Grounding & Peer comparison...");

    try {
      const job = await api.evaluations.triggerBatch(selectedAssignmentId, {
        similarity_threshold: 90.0,
      });

      // Poll job progress
      const pollTimer = window.setInterval(async () => {
        try {
          const status = await api.evaluations.pollJobStatus(job.job_id);
          setProcessingProgress(Math.max(10, Math.round(status.progress_pct)));

          if (status.status === "completed") {
            window.clearInterval(pollTimer);
            setIsProcessing(false);
            setProcessingProgress(100);
            await loadSubmissions(selectedAssignmentId);
            await loadSimilarity(selectedAssignmentId);
            showToast(`Auto-grading complete: ${status.processed_items} submissions ready for review!`);
          } else if (status.status === "failed") {
            window.clearInterval(pollTimer);
            setIsProcessing(false);
            showToast(`Evaluation failed: ${status.error_message || "Unknown error"}`);
          }
        } catch {
          // continue polling
        }
      }, 1200);
    } catch (e: any) {
      setIsProcessing(false);
      showToast(`Error starting evaluation: ${e.message}`);
    }
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
        />
        <div className="flex min-w-0 flex-1 flex-col lg:ml-64">
          <TopBar
            course={currentCourse}
            currentUser={currentUser}
            onOpenAuth={() => setAuthModalOpen(true)}
            onLogout={() => {
              clearAuthToken();
              setCurrentUser(null);
              showToast("Signed out successfully.");
            }}
            search={search}
            setSearch={setSearch}
            notifications={notifications}
            setNotifications={setNotifications}
            onMenu={() => setMobileNav(true)}
          />
          <main className="mx-auto w-full max-w-[1500px] flex-1 px-4 py-6 sm:px-6 sm:py-8">
            {view === "dashboard" && (
              <Dashboard
                course={currentCourse}
                courses={courses}
                assignment={currentAssignment}
                submissions={submissions}
                pendingCount={pendingCount}
                onNavigate={navigate}
                onReview={(subId) => {
                  setSelectedSubmissionId(subId);
                  navigate("review");
                }}
                onOpenAddCourse={() => setAddCourseOpen(true)}
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
                assignments={assignments}
                selectedAssignmentId={selectedAssignmentId}
                onSelectAssignment={handleSelectAssignment}
                onOpenAddAssignment={() => setAddAssignmentOpen(true)}
                onOpenEditAssignment={() => setEditAssignmentOpen(true)}
                onDeleteAssignment={handleDeleteAssignment}
                onOpenManualSubmission={() => setManualSubmissionOpen(true)}
                onDeleteSubmission={handleDeleteSubmission}
                onClearAllSubmissions={handleClearAllSubmissions}
                submissions={submissions}
                isProcessing={isProcessing}
                progress={processingProgress}
                onStartGrading={startAIAutoGrading}
                onReloadSubmissions={() => loadSubmissions(selectedAssignmentId)}
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
                onStartGrading={startAIAutoGrading}
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
                onNavigate={navigate}
                showToast={showToast}
              />
            )}
            {view === "gradebook" && (
              <GradebookView
                course={currentCourse}
                assignment={currentAssignment}
                submissions={submissions}
                showToast={showToast}
              />
            )}
            {view === "reports" && <ReportsView course={currentCourse} submissions={submissions} showToast={showToast} />}
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
        <div className="fixed bottom-5 left-1/2 z-50 flex -translate-x-1/2 items-center gap-2 rounded-lg bg-ink px-4 py-3 text-sm text-card shadow-xl animate-fade-up">
          <CheckCircle2 className="size-4 text-sage" />
          {toast}
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

      {/* Add Assignment Modal (With Reference Assignment / Exemplar Ground Truth) */}
      {addAssignmentOpen && (
        <AddAssignmentModal
          courseId={selectedCourseId}
          onClose={() => setAddAssignmentOpen(false)}
          onCreated={(newAssign) => {
            setAssignments([newAssign, ...assignments]);
            setSelectedAssignmentId(newAssign.id);
            setAddAssignmentOpen(false);
            showToast(`Assignment created with reference exemplar.`);
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
      { key: "courses", label: "My Courses", icon: BookOpen },
      { key: "assignments", label: "Assignments & Submissions", icon: FolderOpen },
      { key: "assessments", label: "Rubric Engine", icon: ClipboardCheck },
      { key: "similarity", label: "Similarity & Plagiarism", icon: ShieldAlert },
      { key: "grading", label: "AI Auto-Grading", icon: Sparkles },
      { key: "review", label: "Review Queue", icon: CheckCircle2 },
      { key: "gradebook", label: "Live Gradebook", icon: BarChart3 },
      { key: "reports", label: "Integrity Reports", icon: Activity },
    ],
  },
  { label: "Account", items: [{ key: "settings", label: "Settings", icon: Settings }] },
];

function Sidebar({
  active,
  onNavigate,
  mobileOpen,
  onClose,
  pendingCount,
}: {
  active: ViewKey;
  onNavigate: (view: ViewKey) => void;
  mobileOpen: boolean;
  onClose: () => void;
  pendingCount: number;
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
          "fixed inset-y-0 left-0 z-40 flex w-64 shrink-0 flex-col border-r border-line bg-card px-5 py-6 transition-transform duration-300 lg:translate-x-0",
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex items-center gap-2.5 px-1">
          <div className="grid size-8 place-items-center rounded-[7px] bg-ink text-card">
            <span className="font-display text-base leading-none">V</span>
          </div>
          <div className="leading-tight">
            <p className="text-[13px] font-semibold tracking-tight">Verism AI</p>
            <p className="mt-0.5 text-[10px] uppercase tracking-[0.18em] text-faint">Academic Integrity & Review</p>
          </div>
          <Button size="icon" variant="ghost" className="ml-auto text-muted-ink lg:hidden" onClick={onClose}>
            <X />
          </Button>
        </div>
        <nav className="mt-8 space-y-0.5 text-[13px]">
          {navSections.map((section) => (
            <div key={section.label} className="mb-5">
              <div className="mb-2 px-3 text-[10px] uppercase tracking-[0.16em] text-faint">{section.label}</div>
              {section.items.map((item) => {
                const Icon = item.icon;
                const isActive = active === item.key;
                return (
                  <Button
                    key={item.key}
                    variant="ghost"
                    onClick={() => onNavigate(item.key)}
                    className={cn(
                      "flex h-9 w-full justify-start gap-3 rounded-lg px-3 font-normal text-muted-ink hover:bg-paper hover:text-ink",
                      isActive && "bg-lav-soft font-medium text-ink hover:bg-lav-soft"
                    )}
                  >
                    <Icon className={cn("size-4", isActive ? "text-amber-ink" : "text-faint")} />
                    <span>{item.label}</span>
                    {item.key === "review" && pendingCount > 0 && (
                      <span className="ml-auto rounded-full bg-lav px-1.5 py-0.5 text-[10px] text-card">
                        {pendingCount}
                      </span>
                    )}
                  </Button>
                );
              })}
            </div>
          ))}
        </nav>
        <div className="mt-auto rounded-[10px] border border-line bg-paper px-3 py-3">
          <p className="text-[11px] leading-snug text-muted-ink">
            AI suggests. <span className="font-medium text-ink">You stamp.</span>
          </p>
          <p className="mt-1 text-[10px] leading-relaxed text-faint">
            Strict FERPA/GDPR encryption. Every grade requires teacher approval.
          </p>
        </div>
      </aside>
    </>
  );
}

function TopBar({
  course,
  currentUser,
  onOpenAuth,
  onLogout,
  search,
  setSearch,
  notifications,
  setNotifications,
  onMenu,
}: {
  course: APICourse | null;
  currentUser: UserProfile | null;
  onOpenAuth: () => void;
  onLogout: () => void;
  search: string;
  setSearch: (value: string) => void;
  notifications: boolean;
  setNotifications: (value: boolean) => void;
  onMenu: () => void;
}) {
  return (
    <header className="sticky top-0 z-20 flex items-center gap-3 border-b border-line bg-paper/90 px-4 py-3 backdrop-blur sm:px-6">
      <Button size="icon" variant="ghost" className="text-muted-ink lg:hidden" onClick={onMenu}>
        <Menu />
      </Button>
      {course ? (
        <div className="hidden items-center gap-2 text-[13px] md:flex">
          <span className="rounded-md border border-line bg-card px-2.5 py-1.5 font-medium">
            {course.code} · {course.name}
          </span>
          <span className="rounded-md border border-line bg-card px-2.5 py-1.5 text-muted-ink">
            Section {course.section || "A"}
          </span>
        </div>
      ) : (
        <div className="hidden items-center gap-2 text-[13px] md:flex">
          <span className="rounded-md border border-line bg-card px-2.5 py-1.5 font-medium text-muted-ink">
            Teacher Console
          </span>
        </div>
      )}
      <div className="relative flex w-full max-w-sm items-center gap-2 rounded-lg border border-line bg-card px-3 py-1.5 text-muted-ink">
        <Search className="size-4 text-faint" />
        <Input
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search students, submissions…"
          className="h-7 border-0 bg-transparent p-0 text-sm shadow-none focus-visible:ring-0"
        />
      </div>
      <div className="ml-auto flex items-center gap-2 sm:gap-3">
        {currentUser ? (
          <div className="flex items-center gap-2">
            <div className="grid size-8 place-items-center rounded-full bg-lav-soft text-[11px] font-medium text-ink">
              {currentUser.name
                .split(" ")
                .map((n) => n[0])
                .join("")
                .substring(0, 2)
                .toUpperCase()}
            </div>
            <div className="hidden text-left leading-tight sm:block">
              <p className="text-[12px] font-medium">{currentUser.name}</p>
              <p className="text-[10px] text-faint">{currentUser.role}</p>
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
          <Button size="sm" onClick={onOpenAuth} className="rounded-lg bg-ink text-card hover:bg-ink/90">
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

function Dashboard({
  course,
  courses,
  assignment,
  submissions,
  pendingCount,
  onNavigate,
  onReview,
  onOpenAddCourse,
}: {
  course: APICourse | null;
  courses: APICourse[];
  assignment: APIAssignment | null;
  submissions: SubmissionItem[];
  pendingCount: number;
  onNavigate: (view: ViewKey) => void;
  onReview: (id: string) => void;
  onOpenAddCourse: () => void;
}) {
  if (!course || courses.length === 0) {
    return (
      <div className="mx-auto max-w-4xl py-12 text-center animate-fade-up">
        <div className="mx-auto grid size-16 place-items-center rounded-2xl bg-lav-soft text-ink mb-6 shadow-sm">
          <BookOpen className="size-8 text-amber-ink" />
        </div>
        <p className="text-xs uppercase tracking-[0.2em] text-faint mb-2">Teacher Workspace · Real Data Input</p>
        <h1 className="font-display text-4xl text-ink">Welcome to Verism AI</h1>
        <p className="mx-auto mt-3 max-w-xl text-sm leading-relaxed text-muted-ink">
          Your personal academic integrity and automated grading console. All mock data has been removed so you can configure your own real courses, grading rubrics, and reference benchmark exemplars.
        </p>
        <div className="mt-8 flex justify-center gap-3">
          <Button onClick={onOpenAddCourse} size="lg" className="bg-ink text-card hover:bg-ink/90 rounded-xl px-6">
            <Plus className="mr-2 size-4" />
            Add Your First Course
          </Button>
        </div>
        <div className="mt-12 grid gap-4 text-left sm:grid-cols-3">
          <div className="rounded-[14px] border border-line bg-card p-5">
            <div className="grid size-9 place-items-center rounded-lg bg-lav-soft text-ink mb-3 font-semibold">1</div>
            <h3 className="font-display text-lg">Rubric Auto-Grading</h3>
            <p className="mt-1 text-xs text-muted-ink">Define criteria with custom weights and marks. Gemini assesses submissions with clear rationales.</p>
          </div>
          <div className="rounded-[14px] border border-line bg-card p-5">
            <div className="grid size-9 place-items-center rounded-lg bg-sage-soft text-sage mb-3 font-semibold">2</div>
            <h3 className="font-display text-lg">Reference Solution</h3>
            <p className="mt-1 text-xs text-muted-ink">Provide an exemplar or benchmark code to evaluate technical accuracy and depth.</p>
          </div>
          <div className="rounded-[14px] border border-line bg-card p-5">
            <div className="grid size-9 place-items-center rounded-lg bg-amber-soft text-amber-ink mb-3 font-semibold">3</div>
            <h3 className="font-display text-lg">3-Way Plagiarism Check</h3>
            <p className="mt-1 text-xs text-muted-ink">Continuous peer-to-peer cross-similarity, AI content probability, and public web search citations.</p>
          </div>
        </div>
      </div>
    );
  }

  const highSimCount = submissions.filter((s) => s.similarity >= 85).length;
  const highAiCount = submissions.filter((s) => s.aiContent >= 60).length;
  const highWebCount = submissions.filter((s) => (s.webPlagiarism || 0) >= 20).length;
  const approvedCount = submissions.filter((s) => s.status === "approved").length;

  const avgScore =
    submissions.length > 0
      ? Math.round(submissions.reduce((acc, s) => acc + (s.score || 0), 0) / submissions.length)
      : 0;

  const metrics = [
    { label: "Active Courses", value: `${courses.length}`, note: "Registered in Supabase", tone: "lav" },
    { label: "Submissions", value: `${submissions.length}`, note: assignment ? assignment.title : "No assignment", tone: "blue" },
    { label: "Pending Reviews", value: `${pendingCount}`, note: "Teacher approval required", tone: "amber" },
    { label: "Approved Grades", value: `${approvedCount}`, note: "Final stamped marks", tone: "sage" },
    { label: "Peer Plagiarism Flags", value: `${highSimCount}`, note: "Similarity >= 85%", tone: "clay" },
    { label: "AI Content Indicators", value: `${highAiCount}`, note: "Synthetic probability >= 60%", tone: "amber" },
    { label: "Web Plagiarism Flags", value: `${highWebCount}`, note: "Public web match >= 20%", tone: "clay" },
  ];

  return (
    <>
      <SectionTitle
        eyebrow="Teacher Console · Live Overview"
        title={`Workspace · ${course.name}`}
        description="Automated grading benchmarks each submission against your reference solution and audits peer, AI, and public web plagiarism."
        action={
          <div className="flex gap-2">
            <Button onClick={() => onNavigate("assignments")} className="rounded-lg bg-ink text-card hover:bg-ink/90">
              <UploadCloud className="mr-1.5 size-4" />
              Manage Submissions
            </Button>
          </div>
        }
      />

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4 xl:grid-cols-7">
        {metrics.map((metric) => (
          <div key={metric.label} className="rounded-[12px] border border-line bg-card p-4">
            <div className={cn("mb-3 size-2 rounded-full", `dot-${metric.tone}`)} />
            <p className="text-xs font-medium text-muted-ink">{metric.label}</p>
            <p className="mt-1 font-display text-3xl text-ink">{metric.value}</p>
            <p className="mt-1 text-[11px] text-faint">{metric.note}</p>
          </div>
        ))}
      </div>

      <div className="mt-6 grid gap-5 xl:grid-cols-12">
        <div className="rounded-[14px] border border-line bg-card p-5 xl:col-span-7">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="font-display text-xl">Integrity Audit Breakdown</h2>
              <p className="mt-1 text-xs text-muted-ink">
                3-Way academic integrity overview for {assignment ? assignment.title : course.name}.
              </p>
            </div>
            <Button variant="ghost" size="sm" className="text-amber-ink" onClick={() => onNavigate("similarity")}>
              Inspect flags <ArrowRight className="ml-1 size-3.5" />
            </Button>
          </div>

          <div className="mt-5 space-y-4">
            <div className="flex items-center gap-3 rounded-lg border border-line bg-paper p-3.5">
              <div className="grid size-9 shrink-0 place-items-center rounded-lg bg-clay-soft text-clay">
                <ShieldAlert className="size-5" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium">Peer-to-Peer Cross Plagiarism</p>
                  <span className="font-semibold text-clay">{highSimCount} flagged</span>
                </div>
                <p className="text-xs text-muted-ink">
                  Vector dense similarity cross-referenced across all submissions.
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3 rounded-lg border border-line bg-paper p-3.5">
              <div className="grid size-9 shrink-0 place-items-center rounded-lg bg-amber-soft text-amber-ink">
                <Sparkles className="size-5" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium">AI-Generated Content Detection</p>
                  <span className="font-semibold text-amber-ink">{highAiCount} indicated</span>
                </div>
                <p className="text-xs text-muted-ink">
                  Perplexity, burstiness, and synthetic transition signatures audited via Gemini.
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3 rounded-lg border border-line bg-paper p-3.5">
              <div className="grid size-9 shrink-0 place-items-center rounded-lg bg-blue-soft text-blue">
                <Globe className="size-5" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium">Public Web Plagiarism (Search Grounding)</p>
                  <span className="font-semibold text-blue">{highWebCount} matched</span>
                </div>
                <p className="text-xs text-muted-ink">
                  Live web citations, GitHub repos, and academic databases cross-checked.
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="rounded-[14px] border border-line bg-card p-5 xl:col-span-5">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-display text-xl">Class Average Score</h2>
              <p className="mt-1 text-xs text-muted-ink">{course.name} · Section {course.section || "A"}</p>
            </div>
            <span className="font-display text-3xl text-ink">{avgScore}/100</span>
          </div>

          <div className="mt-6 border-t border-line pt-4">
            <p className="text-xs font-medium text-muted-ink">Review Progress</p>
            <div className="mt-2 flex items-center justify-between text-xs">
              <span>{approvedCount} approved</span>
              <span className="text-faint">{submissions.length} total</span>
            </div>
            <ProgressLine
              value={submissions.length > 0 ? (approvedCount / submissions.length) * 100 : 0}
              tone="sage"
            />
            <p className="mt-3 text-[11px] leading-relaxed text-faint">
              Every score suggested by AI is a draft recommendation. Teachers retain complete approval authority.
            </p>
          </div>
        </div>
      </div>

      <div className="mt-5 rounded-[14px] border border-line bg-card p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="font-display text-xl">Pending Student Reviews</h2>
            <p className="mt-1 text-xs text-muted-ink">Submissions waiting for teacher review and grading stamp.</p>
          </div>
          <Button variant="outline" size="sm" onClick={() => onNavigate("review")}>
            Open Review Workspace <ArrowRight className="ml-1 size-3.5" />
          </Button>
        </div>

        {submissions.length === 0 ? (
          <div className="mt-6 rounded-lg border border-dashed border-line p-8 text-center">
            <FolderOpen className="mx-auto size-8 text-faint" />
            <p className="mt-2 font-display text-lg text-ink">No submissions in this assignment yet</p>
            <p className="mt-1 text-xs text-muted-ink">
              Upload PDF/DOCX files or input student text to start automated grading.
            </p>
            <Button
              size="sm"
              onClick={() => onNavigate("assignments")}
              className="mt-4 bg-ink text-card hover:bg-ink/90"
            >
              Go to Assignments & Upload
            </Button>
          </div>
        ) : (
          <div className="mt-4 grid gap-3 md:grid-cols-3">
            {submissions.slice(0, 6).map((item) => (
              <div key={item.id} className="rounded-[10px] border border-line bg-paper p-4">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-medium">{item.student}</span>
                  <Pill tone={item.status === "approved" ? "sage" : item.status === "flagged" ? "clay" : "lav"}>
                    {item.status === "approved" ? "Approved" : item.status === "flagged" ? "Flagged" : "Pending"}
                  </Pill>
                </div>
                <div className="mt-2 space-y-1 text-xs text-muted-ink">
                  <p>Roll: {item.roll}</p>
                  <p>AI Suggested: <span className="font-semibold text-ink">{item.score}/100</span></p>
                  <div className="flex items-center gap-2 pt-1 text-[11px]">
                    <span className={item.similarity >= 85 ? "text-clay font-medium" : "text-faint"}>
                      Peer: {item.similarity}%
                    </span>
                    <span>·</span>
                    <span className={item.aiContent >= 60 ? "text-amber-ink font-medium" : "text-faint"}>
                      AI: {item.aiContent}%
                    </span>
                    <span>·</span>
                    <span className={(item.webPlagiarism || 0) >= 20 ? "text-blue font-medium" : "text-faint"}>
                      Web: {item.webPlagiarism || 0}%
                    </span>
                  </div>
                </div>
                <Button
                  size="sm"
                  className="mt-3 w-full bg-ink text-card hover:bg-ink/90"
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
    `${c.name} ${c.code} ${c.section || ""}`.toLowerCase().includes(search.toLowerCase())
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
            Create your first custom course to start managing real assignments and student submissions.
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
                  isSelected ? "border-lav ring-2 ring-lav-soft" : "border-line"
                )}
              >
                <div className="flex items-start justify-between">
                  <div className={cn("grid size-10 place-items-center rounded-lg", `soft-${item.tone || "lav"}`)}>
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

function AssignmentsView({
  course,
  assignments,
  selectedAssignmentId,
  onSelectAssignment,
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
  assignments: APIAssignment[];
  selectedAssignmentId: string;
  onSelectAssignment: (id: string) => void;
  onOpenAddAssignment: () => void;
  onOpenEditAssignment: () => void;
  onDeleteAssignment: (id: string) => void;
  onOpenManualSubmission: () => void;
  onDeleteSubmission: (id: string) => void;
  onClearAllSubmissions: () => void;
  submissions: SubmissionItem[];
  isProcessing: boolean;
  progress: number;
  onStartGrading: () => void;
  onReloadSubmissions: () => void;
  onNavigate: (view: ViewKey) => void;
  showToast: (msg: string) => void;
}) {
  const [uploading, setUploading] = useState(false);
  const activeAssign = assignments.find((a) => a.id === selectedAssignmentId);

  if (!course) {
    return (
      <div className="rounded-[14px] border border-dashed border-line p-12 text-center animate-fade-up">
        <FolderOpen className="mx-auto size-10 text-faint mb-3" />
        <h3 className="font-display text-xl text-ink">No Active Course Selected</h3>
        <p className="mt-1 text-xs text-muted-ink">
          Please select or create a course before configuring assignments and student submissions.
        </p>
        <Button onClick={() => onNavigate("courses")} className="mt-4 bg-ink text-card hover:bg-ink/90">
          Go to Courses
        </Button>
      </div>
    );
  }

  const handleFileUpload = async (files: FileList | null) => {
    if (!files || files.length === 0 || !selectedAssignmentId) return;
    setUploading(true);
    showToast(`Uploading ${files.length} file(s)...`);
    try {
      await api.submissions.batchUpload(selectedAssignmentId, Array.from(files));
      showToast("Files uploaded and decrypted securely.");
      onReloadSubmissions();
    } catch (e: any) {
      showToast(`Upload error: ${e.message}`);
    } finally {
      setUploading(false);
    }
  };

  return (
    <>
      <SectionTitle
        eyebrow={`Assignments · ${course.code} · Section ${course.section || "A"}`}
        title="Student Submissions & Benchmark Exemplars"
        description="Provide a Reference Assignment (ground truth) and grading rubric. The AI engine compares each submission against the benchmark solution."
        action={
          <div className="flex flex-wrap gap-2">
            <Button onClick={onOpenAddAssignment} className="rounded-lg bg-ink text-card hover:bg-ink/90">
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

      <div className="grid gap-5 xl:grid-cols-12">
        <section className="rounded-[14px] border border-line bg-card p-5 xl:col-span-7">
          {/* Active Assignment Selection */}
          <div className="mb-4">
            <label className="text-[11px] font-medium uppercase tracking-[0.14em] text-faint">
              Active Assignment
            </label>
            <div className="mt-1 flex flex-wrap gap-2">
              {assignments.length === 0 ? (
                <span className="text-xs italic text-faint">No assignments in this course yet.</span>
              ) : (
                assignments.map((a) => (
                  <Button
                    key={a.id}
                    size="sm"
                    variant={a.id === selectedAssignmentId ? "default" : "outline"}
                    onClick={() => onSelectAssignment(a.id)}
                  >
                    {a.title}
                  </Button>
                ))
              )}
            </div>
          </div>

          {activeAssign && (
            <div className="mb-5 rounded-lg border border-line bg-paper p-3.5">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-sm font-semibold text-ink">{activeAssign.title}</span>
                  <Badge variant="outline" className="ml-2">Max Marks: {activeAssign.max_score}</Badge>
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

              {/* Reference Assignment Display */}
              <div className="mt-3 border-t border-line pt-2">
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
                    No reference exemplar added yet. Click "Edit Exemplar" to paste benchmark code or solution.
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Drag & Drop File Upload */}
          <label className="flex min-h-52 cursor-pointer flex-col items-center justify-center rounded-[12px] border border-dashed border-line bg-paper p-6 text-center transition-colors hover:border-lav">
            <input
              type="file"
              multiple
              className="hidden"
              accept=".pdf,.doc,.docx,.txt,.zip"
              onChange={(e) => handleFileUpload(e.target.files)}
            />
            <div className="grid size-12 place-items-center rounded-full bg-lav-soft text-amber-ink">
              <UploadCloud className="size-6" />
            </div>
            <p className="mt-3 font-display text-lg">Upload student submissions</p>
            <p className="mt-1 max-w-sm text-xs text-muted-ink">
              Drop PDFs, DOCX, TXT, or ZIP archive. Files are encrypted with FERPA-grade AES-256 upon upload.
            </p>
            <Button type="button" variant="outline" size="sm" className="mt-4" disabled={uploading}>
              {uploading ? "Uploading..." : "Browse files"}
            </Button>
          </label>

          <div className="mt-5 flex items-center justify-between border-t border-line pt-4">
            <div>
              <p className="text-sm font-medium">Ready for Auto-Grading & 3-Way Plagiarism Audit</p>
              <p className="mt-0.5 text-xs text-muted-ink">
                Executes peer cross-matching, synthetic AI probability, and public web search citations.
              </p>
            </div>
            <Button
              onClick={onStartGrading}
              disabled={isProcessing || submissions.length === 0}
              className="bg-ink text-card hover:bg-ink/90"
            >
              {isProcessing ? "Grading in Progress..." : "Start AI Grading"}
              <Sparkles className="ml-1.5 size-4" />
            </Button>
          </div>

          {isProcessing && (
            <div className="mt-4 rounded-lg bg-lav-soft p-3.5">
              <div className="flex items-center justify-between text-xs">
                <span className="font-medium text-ink">Analyzing batch & checking web citations</span>
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
              <p className="mt-1 text-xs text-muted-ink">{submissions.length} submissions in this assignment</p>
            </div>
            <div className="flex items-center gap-1.5">
              <Button
                size="sm"
                variant="ghost"
                className="h-8 text-xs text-muted-ink hover:text-clay hover:bg-clay-soft"
                onClick={onClearAllSubmissions}
                disabled={submissions.length === 0}
                title="Clear all submissions for this assignment"
              >
                <Trash2 className="mr-1 size-3.5" />
                Clear All
              </Button>
              <Button size="icon" variant="ghost" onClick={onReloadSubmissions} title="Refresh">
                <RefreshCw className="size-4" />
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
                <div key={sub.id} className="flex items-center gap-3 rounded-lg border border-line bg-paper p-3">
                  <div className="grid size-8 shrink-0 place-items-center rounded-lg bg-lav-soft text-amber-ink">
                    <FileText className="size-4" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between">
                      <p className="truncate text-xs font-semibold text-ink">{sub.student}</p>
                      <span className="text-[11px] font-bold text-ink">{sub.score}/100</span>
                    </div>
                    <div className="mt-1 flex items-center gap-2 text-[10px]">
                      <span className={sub.similarity >= 85 ? "text-clay font-medium" : "text-faint"}>
                        Peer: {sub.similarity}%
                      </span>
                      <span>·</span>
                      <span className={sub.aiContent >= 60 ? "text-amber-ink font-medium" : "text-faint"}>
                        AI: {sub.aiContent}%
                      </span>
                      <span>·</span>
                      <span className={(sub.webPlagiarism || 0) >= 20 ? "text-blue font-medium" : "text-faint"}>
                        Web: {sub.webPlagiarism || 0}%
                      </span>
                    </div>
                  </div>
                  <Button
                    size="icon"
                    variant="ghost"
                    className="size-7 shrink-0 text-muted-ink hover:text-clay hover:bg-clay-soft"
                    onClick={() => onDeleteSubmission(sub.id)}
                    title="Delete Submission"
                  >
                    <Trash2 className="size-3.5" />
                  </Button>
                </div>
              ))
            )}
          </div>
        </section>
      </div>
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
    { name: "Understanding", description: "Conceptual clarity, problem modeling and depth", weight: 30, max_score: 30 },
    { name: "Accuracy", description: "Correctness of algorithmic solution against benchmark", weight: 30, max_score: 30 },
    { name: "Methodology", description: "Process, computational complexity and reasoning", weight: 20, max_score: 20 },
    { name: "Presentation", description: "Code structure, modularity and documentation", weight: 20, max_score: 20 },
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
        <p className="mt-1 text-xs text-muted-ink">Please select or create a course to configure grading rubrics.</p>
        <Button onClick={() => onNavigate("courses")} className="mt-4 bg-ink text-card hover:bg-ink/90">
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
      { name: "New Criterion", description: "Criterion evaluation standards", weight: 10, max_score: 10 },
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
            <div key={idx} className="grid grid-cols-12 items-center gap-3 border-t border-line px-4 py-3 text-sm">
              <div className="col-span-3">
                <Input
                  value={row.name}
                  onChange={(e) => {
                    setCriteria(criteria.map((c, i) => i === idx ? { ...c, name: e.target.value } : c));
                  }}
                  className="h-8 text-xs font-medium"
                />
              </div>
              <div className="col-span-5">
                <Input
                  value={row.description}
                  onChange={(e) => {
                    setCriteria(criteria.map((c, i) => i === idx ? { ...c, description: e.target.value } : c));
                  }}
                  className="h-8 text-xs text-muted-ink"
                />
              </div>
              <div className="col-span-2">
                <Input
                  type="number"
                  value={row.weight}
                  onChange={(e) => {
                    setCriteria(criteria.map((c, i) => i === idx ? { ...c, weight: Number(e.target.value) } : c));
                  }}
                  className="h-8 text-xs text-center"
                />
              </div>
              <div className="col-span-2">
                <Input
                  type="number"
                  value={row.max_score}
                  onChange={(e) => {
                    setCriteria(criteria.map((c, i) => i === idx ? { ...c, max_score: Number(e.target.value) } : c));
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
        eyebrow="Academic Integrity · 3-Way Plagiarism Check"
        title="Plagiarism & Similarity Audits"
        description="Comprehensive verification across 3 dimensions: (1) Peer-to-Peer Cross Copying, (2) AI Content Likelihood, and (3) Public Web Search Grounding."
      />

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <div className="rounded-[12px] border border-line bg-card p-4">
          <p className="text-xs text-muted-ink">Total Submissions</p>
          <p className="mt-1 font-display text-3xl">{submissions.length}</p>
        </div>
        <div className="rounded-[12px] border border-line bg-card p-4">
          <p className="text-xs text-muted-ink">Peer Plagiarism Flags</p>
          <p className="mt-1 font-display text-3xl text-clay">{highSim.length}</p>
        </div>
        <div className="rounded-[12px] border border-line bg-card p-4">
          <p className="text-xs text-muted-ink">AI Content Flags</p>
          <p className="mt-1 font-display text-3xl text-amber-ink">{highAi.length}</p>
        </div>
        <div className="rounded-[12px] border border-line bg-card p-4">
          <p className="text-xs text-muted-ink">Public Web Flags</p>
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
                <th className="px-3 py-3">Public Web Match</th>
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
                      {sub.aiContent >= 60 ? `${sub.aiContent}% Indicated` : `${sub.aiContent}% Low`}
                    </Pill>
                  </td>
                  <td className="px-3 py-4">
                    <Pill tone={(sub.webPlagiarism || 0) >= 20 ? "clay" : "sage"}>
                      {sub.webPlagiarism || 0}% match
                    </Pill>
                  </td>
                  <td className="px-3 py-4">
                    <Pill tone={sub.status === "approved" ? "sage" : sub.status === "flagged" ? "clay" : "lav"}>
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
  onStartGrading,
  onReview,
  onNavigate,
  showToast,
}: {
  submissions: SubmissionItem[];
  assignment: APIAssignment | null;
  isProcessing: boolean;
  onStartGrading: () => void;
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
          <Button onClick={onStartGrading} disabled={isProcessing} className="bg-ink text-card hover:bg-ink/90">
            <Sparkles className="mr-1.5 size-4" />
            {isProcessing ? "Running Auto-Grading..." : "Rerun Batch Auto-Grading"}
          </Button>
        }
      />

      <div className="rounded-[14px] border border-line bg-card p-5">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead>
              <tr className="border-b border-line text-[10px] uppercase tracking-[0.14em] text-faint">
                <th className="px-3 py-3">Student & Roll</th>
                <th className="px-3 py-3">AI Suggested Score</th>
                <th className="px-3 py-3">Peer Similarity</th>
                <th className="px-3 py-3">AI Likelihood</th>
                <th className="px-3 py-3">Web Plagiarism</th>
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
                    {sub.score}
                    <span className="text-sm text-muted-ink">/100</span>
                  </td>
                  <td className="px-3 py-4">
                    <span className={sub.similarity >= 85 ? "font-semibold text-clay" : "text-muted-ink"}>
                      {sub.similarity}%
                    </span>
                  </td>
                  <td className="px-3 py-4">
                    <Pill tone={sub.aiContent >= 60 ? "amber" : "sage"}>{sub.aiContent}%</Pill>
                  </td>
                  <td className="px-3 py-4">
                    <Pill tone={(sub.webPlagiarism || 0) >= 20 ? "clay" : "sage"}>
                      {sub.webPlagiarism || 0}%
                    </Pill>
                  </td>
                  <td className="px-3 py-4">
                    <Pill tone={sub.status === "approved" ? "sage" : sub.status === "flagged" ? "clay" : "lav"}>
                      {sub.status === "approved" ? "Approved" : sub.status === "flagged" ? "Flagged" : "Pending"}
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
  onNavigate,
  showToast,
}: {
  assignment: APIAssignment | null;
  submissions: SubmissionItem[];
  selectedSubmissionId: string;
  onSelectSubmission: (id: string) => void;
  onGraded: () => void;
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
        description="Inspect the student's submission side-by-side with your Reference Assignment. Verify peer similarity, AI content, and public web search citations."
        action={
          <div className="flex items-center gap-2">
            <Pill tone="sage">
              {submissions.filter((s) => s.status === "approved").length} approved
            </Pill>
            <Pill tone="amber">
              {submissions.filter((s) => s.status !== "approved").length} pending
            </Pill>
          </div>
        }
      />

      {/* Student Selector Carousel */}
      <div className="mb-4 flex items-center gap-2 overflow-x-auto rounded-lg border border-line bg-card p-2">
        <span className="shrink-0 px-2 text-[10px] uppercase tracking-[0.14em] text-faint">Students:</span>
        {submissions.map((sub) => (
          <Button
            key={sub.id}
            size="sm"
            variant={sub.id === selectedSubmissionId ? "default" : "ghost"}
            className="shrink-0 text-xs"
            onClick={() => onSelectSubmission(sub.id)}
          >
            {sub.student} ({sub.score}/100)
          </Button>
        ))}
      </div>

      {currentSub ? (
        <div className="grid gap-5 xl:grid-cols-12">
          {/* Column 1: Student Text & Reference Exemplar */}
          <section className="flex flex-col rounded-[14px] border border-line bg-card p-5 xl:col-span-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] uppercase tracking-[0.16em] text-faint">Student Submission</p>
                <h2 className="mt-1 font-display text-2xl">{currentSub.student}</h2>
                <p className="text-xs text-faint">Roll: {currentSub.roll}</p>
              </div>
              <Pill tone={currentSub.similarity >= 85 ? "clay" : "sage"}>
                {currentSub.similarity}% Peer Match
              </Pill>
            </div>

            {/* 3-Way Integrity Pill Indicators */}
            <div className="mt-4 grid grid-cols-3 gap-2 border-y border-line py-3 text-center">
              <div>
                <span className="text-[10px] uppercase text-faint">Peer Sim</span>
                <p className={cn("text-sm font-bold", currentSub.similarity >= 85 ? "text-clay" : "text-ink")}>
                  {currentSub.similarity}%
                </p>
              </div>
              <div>
                <span className="text-[10px] uppercase text-faint">AI Prob</span>
                <p className={cn("text-sm font-bold", currentSub.aiContent >= 60 ? "text-amber-ink" : "text-ink")}>
                  {currentSub.aiContent}%
                </p>
              </div>
              <div>
                <span className="text-[10px] uppercase text-faint">Web Match</span>
                <p className={cn("text-sm font-bold", (currentSub.webPlagiarism || 0) >= 20 ? "text-blue" : "text-ink")}>
                  {currentSub.webPlagiarism || 0}%
                </p>
              </div>
            </div>

            {/* Submission Content Text */}
            <div className="mt-4 max-h-[300px] overflow-y-auto rounded-lg border border-line bg-paper p-3 text-xs leading-relaxed text-muted-ink">
              <span className="mb-1 block font-semibold uppercase text-faint">Student Submitted Text:</span>
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
                  {crit.rationale && <p className="mt-1.5 text-[11px] text-muted-ink">{crit.rationale}</p>}
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
              "AI suggests. You stamp." — No AI score is officially recorded without your direct confirmation.
            </div>

            <div className="mt-auto flex flex-col gap-2 pt-6">
              <Button
                onClick={handleApproveGrade}
                className="bg-ink text-card hover:bg-ink/90"
              >
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
  if (!course) {
    return (
      <div className="rounded-[14px] border border-dashed border-line p-12 text-center animate-fade-up">
        <BarChart3 className="mx-auto size-10 text-faint mb-3" />
        <h3 className="font-display text-xl text-ink">No Active Course Selected</h3>
        <p className="mt-1 text-xs text-muted-ink">Select or create a course to inspect its gradebook.</p>
      </div>
    );
  }

  const exportCSV = () => {
    const headers = ["Student Name", "Roll Number", "Status", "Score", "Peer Similarity %", "AI Content %", "Web Match %"];
    const rows = submissions.map((s) => [
      s.student,
      s.roll,
      s.status,
      s.score,
      s.similarity,
      s.aiContent,
      s.webPlagiarism || 0,
    ]);
    const csvContent =
      "data:text/csv;charset=utf-8," +
      [headers.join(","), ...rows.map((e) => e.join(","))].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `${course?.code || "course"}_${assignment?.title || "assignment"}_gradebook.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    showToast("Gradebook exported to CSV successfully.");
  };

  return (
    <>
      <SectionTitle
        eyebrow={`Gradebook · ${course.code} · Section ${course.section || "A"}`}
        title="Course Gradebook"
        description="Comprehensive spreadsheet view of student marks, review approval status, and integrity indicators."
        action={
          <Button variant="outline" onClick={exportCSV} disabled={submissions.length === 0}>
            Export to CSV
          </Button>
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
                <th className="px-3 py-3">Web Plagiarism</th>
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
                  <tr key={s.id} className="border-b border-line last:border-0">
                    <td className="px-3 py-3.5 font-medium">{s.student}</td>
                    <td className="px-3 py-3.5 text-xs text-faint">{s.roll}</td>
                    <td className="px-3 py-3.5 font-display text-lg">
                      {s.score}
                      <span className="text-xs text-muted-ink">/100</span>
                    </td>
                    <td className="px-3 py-3.5">
                      <span className={s.similarity >= 85 ? "font-semibold text-clay" : "text-muted-ink"}>
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
                      <Pill tone={s.status === "approved" ? "sage" : s.status === "flagged" ? "clay" : "lav"}>
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
        description="FERPA/GDPR compliance logging and longitudinal similarity trend monitoring."
      />

      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-[14px] border border-line bg-card p-5">
          <h2 className="font-display text-xl">FERPA/GDPR Data Minimization</h2>
          <p className="mt-2 text-xs leading-relaxed text-muted-ink">
            All student identifiers (Names, Roll Numbers, Emails) undergo AES-256 Fernet field-level encryption at rest.
            When submissions are passed to Google Gemini for evaluation, student identities are pseudonymized into deterministic
            tokens (e.g. STUDENT_A3F89B), ensuring zero student PII ever leaves your security perimeter.
          </p>
          <div className="mt-4 rounded bg-sage-soft p-3 text-xs text-sage font-medium">
            Active: Cryptographic Data Minimization & Encryption Enforced
          </div>
        </div>

        <div className="rounded-[14px] border border-line bg-card p-5">
          <h2 className="font-display text-xl">Audit Trail & Teacher Accountability</h2>
          <p className="mt-2 text-xs leading-relaxed text-muted-ink">
            Every grade approval, threshold adjustment, and feedback modification produces an immutable audit record in PostgreSQL
            and Supabase with timestamp, actor ID, and IP address.
          </p>
          <div className="mt-4 rounded bg-lav-soft p-3 text-xs text-ink font-medium">
            Active: Supabase Audit Logs & PostgreSQL Mirroring
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
  return (
    <>
      <SectionTitle
        eyebrow="Preferences & Profile"
        title="Account & Integrity Settings"
        description="Configure similarity thresholds, AI content indicator sensitivity, and teacher review preferences."
      />

      <div className="rounded-[14px] border border-line bg-card p-5 max-w-2xl">
        <h2 className="font-display text-xl">Instructor Profile</h2>
        <div className="mt-4 space-y-3 text-sm">
          <div>
            <label className="text-[11px] uppercase tracking-[0.14em] text-faint">Name</label>
            <p className="font-medium text-ink">{currentUser?.name || "Dr. Priya Rao"}</p>
          </div>
          <div>
            <label className="text-[11px] uppercase tracking-[0.14em] text-faint">Email</label>
            <p className="text-muted-ink">{currentUser?.email || "priya.rao@university.edu"}</p>
          </div>
          <div>
            <label className="text-[11px] uppercase tracking-[0.14em] text-faint">Role</label>
            <p className="text-muted-ink">{currentUser?.role || "Instructor · Computer Science"}</p>
          </div>
        </div>
      </div>

      <div className="mt-5 rounded-[14px] border border-line bg-card p-5 max-w-2xl">
        <h2 className="font-display text-xl text-clay">Database Maintenance & Custom Data</h2>
        <p className="mt-1 text-xs text-muted-ink">
          Purge all seeded demo courses and submissions so you can populate Verism strictly with your own real-world classes, students, and assignment exemplars.
        </p>
        <div className="mt-4">
          <Button variant="outline" className="text-clay hover:bg-clay-soft" onClick={onClearMockData}>
            <Trash2 className="mr-1.5 size-4" /> Purge Demo Seed Data
          </Button>
        </div>
      </div>
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
            <div className="grid size-7 place-items-center rounded bg-ink text-card text-xs font-bold">V</div>
            <h2 className="font-display text-xl">{tab === "login" ? "Sign In to Verism" : "Create Teacher Account"}</h2>
          </div>
          <Button size="icon" variant="ghost" onClick={onClose}><X className="size-4" /></Button>
        </div>

        <div className="mt-4 flex border-b border-line">
          <button
            onClick={() => { setTab("login"); setError(""); }}
            className={cn("flex-1 py-2 text-xs font-semibold text-center border-b-2", tab === "login" ? "border-ink text-ink" : "border-transparent text-muted-ink")}
          >
            Sign In
          </button>
          <button
            onClick={() => { setTab("signup"); setError(""); }}
            className={cn("flex-1 py-2 text-xs font-semibold text-center border-b-2", tab === "signup" ? "border-ink text-ink" : "border-transparent text-muted-ink")}
          >
            Sign Up (New User)
          </button>
        </div>

        {error && (
          <div className="mt-3 rounded bg-clay-soft p-2.5 text-xs text-clay font-medium">{error}</div>
        )}

        <form onSubmit={handleSubmit} className="mt-4 space-y-3">
          {tab === "signup" && (
            <>
              <div>
                <label className="text-[11px] uppercase tracking-[0.12em] text-faint">Full Name</label>
                <Input
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Dr. Alan Turing"
                  className="mt-1"
                />
              </div>
              <div>
                <label className="text-[11px] uppercase tracking-[0.12em] text-faint">Role / Department</label>
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
            <label className="text-[11px] uppercase tracking-[0.12em] text-faint">Email Address</label>
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

          <Button type="submit" disabled={loading} className="mt-4 w-full bg-ink text-card hover:bg-ink/90">
            {loading ? "Processing..." : tab === "login" ? "Sign In" : "Register Account"}
          </Button>
        </form>

        <p className="mt-4 text-center text-[11px] text-faint">
          Synced across PostgreSQL & Supabase Authentication tables.
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
          <Button size="icon" variant="ghost" onClick={onClose}><X className="size-4" /></Button>
        </div>

        <form onSubmit={handleSubmit} className="mt-4 space-y-3">
          <div>
            <label className="text-[11px] uppercase tracking-[0.12em] text-faint">Course Name</label>
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
              <label className="text-[11px] uppercase tracking-[0.12em] text-faint">Course Code</label>
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
            <label className="text-[11px] uppercase tracking-[0.12em] text-faint">Expected Students</label>
            <Input
              type="number"
              value={students}
              onChange={(e) => setStudents(Number(e.target.value))}
              className="mt-1"
            />
          </div>

          <Button type="submit" disabled={submitting} className="mt-4 w-full bg-ink text-card hover:bg-ink/90">
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
          <Button size="icon" variant="ghost" onClick={onClose}><X className="size-4" /></Button>
        </div>

        <form onSubmit={handleSubmit} className="mt-4 space-y-3">
          <div>
            <label className="text-[11px] uppercase tracking-[0.12em] text-faint">Assignment Title</label>
            <Input
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Assignment 4 · Dijkstra & A* Graph Search"
              className="mt-1"
            />
          </div>
          <div>
            <label className="text-[11px] uppercase tracking-[0.12em] text-faint">Instructions / Prompt</label>
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Detailed instructions given to students..."
              className="mt-1 text-xs"
              rows={2}
            />
          </div>
          <div>
            <label className="text-[11px] uppercase tracking-[0.12em] text-faint">Maximum Score</label>
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
              Paste the exemplar solution or reference code. The AI grading engine will benchmark student accuracy and technical depth against this text.
            </p>
            <Textarea
              value={referenceText}
              onChange={(e) => setReferenceText(e.target.value)}
              placeholder="Paste exemplar code, optimal algorithmic solution, or benchmark essay..."
              className="mt-1.5 font-mono text-xs"
              rows={5}
            />
          </div>

          <Button type="submit" disabled={submitting} className="mt-4 w-full bg-ink text-card hover:bg-ink/90">
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
          <Button size="icon" variant="ghost" onClick={onClose}><X className="size-4" /></Button>
        </div>

        <form onSubmit={handleSubmit} className="mt-4 space-y-3">
          <div>
            <label className="text-[11px] uppercase tracking-[0.12em] text-faint">Student Full Name</label>
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
              <label className="text-[11px] uppercase tracking-[0.12em] text-faint">Roll / Student ID</label>
              <Input
                required
                value={studentRoll}
                onChange={(e) => setStudentRoll(e.target.value)}
                placeholder="e.g. 2024-082"
                className="mt-1"
              />
            </div>
            <div>
              <label className="text-[11px] uppercase tracking-[0.12em] text-faint">Student Email</label>
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

          <Button type="submit" disabled={submitting} className="mt-4 w-full bg-ink text-card hover:bg-ink/90">
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
          <Button size="icon" variant="ghost" onClick={onClose}><X className="size-4" /></Button>
        </div>

        <form onSubmit={handleSubmit} className="mt-4 space-y-3">
          <div>
            <label className="text-[11px] uppercase tracking-[0.12em] text-faint">Assignment Title</label>
            <Input
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="mt-1"
            />
          </div>
          <div>
            <label className="text-[11px] uppercase tracking-[0.12em] text-faint">Instructions / Prompt</label>
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="mt-1 text-xs"
              rows={2}
            />
          </div>
          <div>
            <label className="text-[11px] uppercase tracking-[0.12em] text-faint">Maximum Score</label>
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
              Paste the exemplar solution or reference code. The AI grading engine will benchmark student accuracy and technical depth against this text.
            </p>
            <Textarea
              value={referenceText}
              onChange={(e) => setReferenceText(e.target.value)}
              placeholder="Paste exemplar code, optimal algorithmic solution, or benchmark essay..."
              className="mt-1.5 font-mono text-xs"
              rows={6}
            />
          </div>

          <Button type="submit" disabled={submitting} className="mt-4 w-full bg-ink text-card hover:bg-ink/90">
            {submitting ? "Updating..." : "Save Changes & Benchmark"}
          </Button>
        </form>
      </div>
    </div>
  );
}