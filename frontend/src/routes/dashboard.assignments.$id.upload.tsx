import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { useState, useEffect, useRef, useCallback } from "react";
import {
  UploadCloud,
  FileArchive,
  FileText,
  FileCode,
  CheckCircle2,
  AlertTriangle,
  ShieldAlert,
  Loader2,
  Sparkles,
  ArrowLeft,
  RefreshCw,
  Search,
  Filter,
  Check,
  ChevronRight,
  ExternalLink,
  UserCheck,
  UserX,
  Layers,
  GraduationCap,
  Award,
  Clock,
  ChevronDown,
  ChevronUp,
  Sliders,
  Send,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import {
  api,
  type Assignment,
  type Classroom,
  type Student,
  type Rubric,
  type SubmissionItem,
  type ClassroomBatchUploadItem,
  type JobStatusResponse,
} from "@/lib/api";

export const Route = createFileRoute("/dashboard/assignments/$id/upload")({
  head: () => ({
    meta: [
      { title: "Batch Assignment Ingestion & Auto-Evaluation — Verism AI" },
      {
        name: "description",
        content:
          "High-throughput ZIP batch ingestion, automated roll-number roster matching, Qdrant peer plagiarism audits, and Gemini rubric grading.",
      },
    ],
  }),
  component: AssignmentBatchUploadRoute,
});

type PipelineStage = "idle" | "uploading" | "processing" | "review";

export function AssignmentBatchUploadRoute() {
  const { id: assignmentId } = Route.useParams();
  const navigate = useNavigate();

  // Assignment & metadata state
  const [assignment, setAssignment] = useState<Assignment | null>(null);
  const [classrooms, setClassrooms] = useState<Classroom[]>([]);
  const [selectedClassroomId, setSelectedClassroomId] = useState<string>("");
  const [students, setStudents] = useState<Student[]>([]);
  const [rubrics, setRubrics] = useState<Rubric[]>([]);
  const [selectedRubricId, setSelectedRubricId] = useState<string>("");
  const [loadingInitial, setLoadingInitial] = useState(true);

  // File drag-and-drop state
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Pipeline execution & polling state
  const [stage, setStage] = useState<PipelineStage>("idle");
  const [batchJobId, setBatchJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<JobStatusResponse | null>(null);
  const [pollError, setPollError] = useState<string | null>(null);
  const pollTimerRef = useRef<any>(null);

  // Submissions and review state
  const [submissions, setSubmissions] = useState<SubmissionItem[]>([]);
  const [unmatchedItems, setUnmatchedItems] = useState<ClassroomBatchUploadItem[]>([]);
  const [searchFilter, setSearchFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | "unmatched" | "flagged" | "completed">("all");
  const [expandedSubId, setExpandedSubId] = useState<string | null>(null);
  const [resolvingStudentId, setResolvingStudentId] = useState<Record<string, string>>({});
  const [overrideScores, setOverrideScores] = useState<Record<string, number>>({});
  const [overrideFeedbacks, setOverrideFeedbacks] = useState<Record<string, string>>({});
  const [stampedSubs, setStampedSubs] = useState<Record<string, boolean>>({});
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 4000);
  };

  // 1. Load Assignment, Classrooms, Students, Rubrics
  useEffect(() => {
    let isMounted = true;
    async function loadData() {
      try {
        setLoadingInitial(true);
        // Load assignment details
        let assignData: Assignment | null = null;
        try {
          assignData = await api.assignments.get(assignmentId);
          if (isMounted) setAssignment(assignData);
        } catch (e) {
          console.warn("Could not load assignment directly:", e);
        }

        // Load classrooms
        const clList = await api.classrooms.list();
        if (isMounted) {
          setClassrooms(clList);
          let targetClassroomId = "";
          if (assignData?.course_id && clList.some((c) => c.id === assignData.course_id)) {
            targetClassroomId = assignData.course_id;
          } else if (clList.length > 0) {
            targetClassroomId = clList[0].id;
          }
          setSelectedClassroomId(targetClassroomId);

          if (targetClassroomId) {
            const [stList, rbList] = await Promise.all([
              api.classrooms.getStudents(targetClassroomId).catch(() => []),
              api.rubrics.list(targetClassroomId).catch(() => []),
            ]);
            if (isMounted) {
              setStudents(stList);
              setRubrics(rbList);
              if (assignData?.rubric_id) {
                setSelectedRubricId(assignData.rubric_id);
              } else if (rbList.length > 0) {
                setSelectedRubricId(rbList[0].id);
              }
            }
          }
        }

        // Check if there are already existing evaluated submissions for this assignment
        const existingSubs = await api.submissions.listByAssignment(assignmentId).catch(() => []);
        if (isMounted && existingSubs.length > 0) {
          setSubmissions(existingSubs);
          // If submissions already exist and we're not currently processing, show review panel
          setStage("review");
        }
      } catch (err: any) {
        console.error("Failed to load initial upload context:", err);
      } finally {
        if (isMounted) setLoadingInitial(false);
      }
    }

    loadData();
    return () => {
      isMounted = false;
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
    };
  }, [assignmentId]);

  // Load students and rubrics when classroom changes
  useEffect(() => {
    if (!selectedClassroomId) return;
    let isMounted = true;
    async function updateClassroomScope() {
      try {
        const [stList, rbList] = await Promise.all([
          api.classrooms.getStudents(selectedClassroomId).catch(() => []),
          api.rubrics.list(selectedClassroomId).catch(() => []),
        ]);
        if (isMounted) {
          setStudents(stList);
          setRubrics(rbList);
          if (rbList.length > 0 && !selectedRubricId) {
            setSelectedRubricId(rbList[0].id);
          }
        }
      } catch (e) {
        console.warn("Classroom scope load error:", e);
      }
    }
    updateClassroomScope();
    return () => {
      isMounted = false;
    };
  }, [selectedClassroomId]);

  // File Drop Handling
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const files = Array.from(e.dataTransfer.files);
      setSelectedFiles(files);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const files = Array.from(e.target.files);
      setSelectedFiles(files);
    }
  };

  // Refresh submission records from backend
  const refreshSubmissions = useCallback(async () => {
    try {
      const updated = await api.submissions.listByAssignment(assignmentId);
      setSubmissions(updated);
    } catch (e) {
      console.warn("Error refreshing submissions:", e);
    }
  }, [assignmentId]);

  // 2. Polling Loop for Background Job (Every 2 seconds)
  useEffect(() => {
    if (stage !== "processing" || !batchJobId) return;

    const poll = async () => {
      try {
        const res = await api.jobs.getStatus(batchJobId);
        setJobStatus(res);
        setPollError(null);

        // If Celery / Worker task finished
        if (res.status === "SUCCESS") {
          if (pollTimerRef.current) clearInterval(pollTimerRef.current);
          setStage("review");
          showToast("Evaluation complete! All criteria and peer audits ready.");
          await refreshSubmissions();
        } else if (res.status === "FAILURE") {
          if (pollTimerRef.current) clearInterval(pollTimerRef.current);
          setPollError(res.details?.error || "Evaluation job encountered an error");
          showToast("Job finished with warnings. Reviewing completed drafts.");
          setStage("review");
          await refreshSubmissions();
        }
      } catch (err: any) {
        console.warn("Status poll error:", err);
      }
    };

    poll(); // Run initial poll immediately
    pollTimerRef.current = setInterval(poll, 2000);

    return () => {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
    };
  }, [stage, batchJobId, refreshSubmissions]);

  // 3. Trigger Batch Ingestion & Enqueue
  const handleUploadAndEvaluate = async () => {
    if (selectedFiles.length === 0) {
      showToast("Please select a ZIP file or student submission documents.");
      return;
    }
    if (!selectedClassroomId) {
      showToast("Please choose a target classroom roster.");
      return;
    }

    try {
      setStage("uploading");
      showToast("Uploading payload and matching student roll numbers...");

      const payload = selectedFiles.length === 1 ? selectedFiles[0] : selectedFiles;
      const resp = await api.submissions.batchUploadClassroom(
        selectedClassroomId,
        assignmentId,
        payload,
        selectedRubricId || undefined
      );

      setBatchJobId(resp.batch_job_id);
      setUnmatchedItems(resp.unmatched_submissions || []);
      setJobStatus({
        job_id: resp.batch_job_id,
        status: "PROCESSING",
        current: 0,
        total: resp.total,
        percent: 0,
      });

      // Switch to processing stage and start polling
      setStage("processing");
      showToast(`Enqueued ${resp.total} submission(s). AI worker is grading in background.`);
    } catch (err: any) {
      console.error("Batch upload failed:", err);
      setStage("idle");
      showToast(err.message || "Failed to upload submissions. Please check format.");
    }
  };

  // 4. Manually Resolve Unmatched Submission
  const handleAssignStudent = async (submissionId: string, studentId: string) => {
    if (!studentId) {
      showToast("Please select a student from the roster.");
      return;
    }
    try {
      await api.submissions.assignStudent(submissionId, studentId);
      showToast("Student matched successfully! Record updated.");
      // Remove from unmatched list
      setUnmatchedItems((prev) => prev.filter((u) => u.id !== submissionId));
      await refreshSubmissions();
    } catch (err: any) {
      console.error("Assign student failed:", err);
      showToast(err.message || "Failed to link submission to student.");
    }
  };

  // 5. Teacher Stamp Grade & Override
  const handleStampGrade = async (sub: SubmissionItem) => {
    const finalScore = overrideScores[sub.id] ?? sub.score;
    const teacherNote = overrideFeedbacks[sub.id] ?? "";
    try {
      await api.review.stampGrade(sub.id, {
        final_score: finalScore,
        teacher_feedback: teacherNote,
        action: "APPROVE",
      });
      setStampedSubs((prev) => ({ ...prev, [sub.id]: true }));
      showToast(`Grade stamped and approved for ${sub.student}!`);
      await refreshSubmissions();
    } catch (err: any) {
      console.error("Grade stamp failed:", err);
      showToast(err.message || "Failed to stamp grade.");
    }
  };

  // Filtering Submissions
  const filteredSubmissions = submissions.filter((s) => {
    const matchesSearch =
      s.student.toLowerCase().includes(searchFilter.toLowerCase()) ||
      s.roll.toLowerCase().includes(searchFilter.toLowerCase()) ||
      s.file_name.toLowerCase().includes(searchFilter.toLowerCase());

    if (!matchesSearch) return false;
    if (statusFilter === "unmatched") return s.status === "unmatched" || !s.student_id;
    if (statusFilter === "flagged") return s.similarity > 0.75 || s.status === "flagged";
    if (statusFilter === "completed") return s.status === "completed" || s.status === "approved";
    return true;
  });

  const unmatchedCount = submissions.filter((s) => s.status === "unmatched" || !s.student_id).length;
  const flaggedCount = submissions.filter((s) => s.similarity > 0.75 || s.status === "flagged").length;
  const completedCount = submissions.filter((s) => s.status === "completed" || s.status === "approved").length;
  const avgScore =
    submissions.length > 0
      ? (submissions.reduce((acc, curr) => acc + (curr.score || 0), 0) / submissions.length).toFixed(1)
      : "0.0";

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed top-5 right-5 z-50 bg-slate-900 border border-teal-500/40 text-teal-200 px-4 py-3 rounded-xl shadow-2xl flex items-center gap-3 animate-fade-in backdrop-blur-md">
          <Sparkles className="size-4 text-teal-400 shrink-0" />
          <span className="text-sm font-medium">{toastMessage}</span>
        </div>
      )}

      {/* Top Header / Navigation Bar */}
      <header className="border-b border-slate-800 bg-slate-900/70 backdrop-blur-md sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              to="/dashboard"
              className="flex items-center gap-2 text-slate-400 hover:text-slate-100 transition-colors text-sm font-medium"
            >
              <ArrowLeft className="size-4" />
              <span>Back to Console</span>
            </Link>
            <div className="h-5 w-px bg-slate-800" />
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold px-2.5 py-1 rounded-md bg-teal-500/10 text-teal-400 border border-teal-500/20">
                BATCH PIPELINE
              </span>
              <h1 className="text-base font-semibold text-slate-100 truncate max-w-md">
                {assignment ? assignment.title : "Assignment Ingestion & Evaluation"}
              </h1>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {stage === "review" && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setStage("idle");
                  setSelectedFiles([]);
                }}
                className="border-slate-700 bg-slate-800/80 hover:bg-slate-700 text-slate-200 text-xs flex items-center gap-2"
              >
                <UploadCloud className="size-3.5" />
                <span>Upload Another Batch</span>
              </Button>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={refreshSubmissions}
              className="text-slate-400 hover:text-slate-100 p-2"
              title="Refresh Records"
            >
              <RefreshCw className="size-4" />
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Pipeline Stepper Indicator */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 bg-slate-900/50 p-2 rounded-2xl border border-slate-800/80">
          <div
            className={`flex items-center gap-3 p-3 rounded-xl transition-all ${
              stage === "idle" || stage === "uploading"
                ? "bg-slate-800 border border-teal-500/30 text-teal-300"
                : "text-slate-400"
            }`}
          >
            <div className="size-7 rounded-lg bg-teal-500/10 flex items-center justify-center text-teal-400 font-bold text-xs shrink-0">
              1
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Step 1</p>
              <p className="text-sm font-medium">Batch Ingestion</p>
            </div>
          </div>

          <div
            className={`flex items-center gap-3 p-3 rounded-xl transition-all ${
              stage === "processing"
                ? "bg-slate-800 border border-teal-500/30 text-teal-300"
                : "text-slate-400"
            }`}
          >
            <div className="size-7 rounded-lg bg-teal-500/10 flex items-center justify-center text-teal-400 font-bold text-xs shrink-0">
              2
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Step 2</p>
              <p className="text-sm font-medium">Roll Matching & Qdrant</p>
            </div>
          </div>

          <div
            className={`flex items-center gap-3 p-3 rounded-xl transition-all ${
              stage === "processing"
                ? "bg-slate-800 border border-indigo-500/30 text-indigo-300"
                : "text-slate-400"
            }`}
          >
            <div className="size-7 rounded-lg bg-indigo-500/10 flex items-center justify-center text-indigo-400 font-bold text-xs shrink-0">
              3
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Step 3</p>
              <p className="text-sm font-medium">Gemini 2.5 Rubric Eval</p>
            </div>
          </div>

          <div
            className={`flex items-center gap-3 p-3 rounded-xl transition-all ${
              stage === "review"
                ? "bg-slate-800 border border-emerald-500/30 text-emerald-300"
                : "text-slate-400"
            }`}
          >
            <div className="size-7 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-400 font-bold text-xs shrink-0">
              4
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Step 4</p>
              <p className="text-sm font-medium">Instructor Stamp</p>
            </div>
          </div>
        </div>

        {/* STAGE 1: INGESTION CONFIG & DROPZONE */}
        {(stage === "idle" || stage === "uploading") && (
          <div className="space-y-6">
            <div className="bg-slate-900/90 rounded-2xl border border-slate-800 p-6 sm:p-8 backdrop-blur-md shadow-xl space-y-6">
              <div>
                <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
                  <UploadCloud className="size-6 text-teal-400" />
                  <span>Batch Assignment Ingestion</span>
                </h2>
                <p className="text-sm text-slate-400 mt-1">
                  Upload a ZIP archive or multi-file payload containing student submissions. The backend will parse roll numbers,
                  resolve enrolled students in database roster, and stream evaluations through Celery and Gemini.
                </p>
              </div>

              {/* Classroom & Rubric Selectors */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                    <GraduationCap className="size-4 text-teal-400" />
                    <span>Target Classroom Roster</span>
                  </label>
                  <select
                    value={selectedClassroomId}
                    onChange={(e) => setSelectedClassroomId(e.target.value)}
                    className="w-full bg-slate-800/90 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-teal-500 transition-colors"
                  >
                    <option value="">Select a classroom...</option>
                    {classrooms.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name} ({c.code}) — {c.students_count || students.length} students
                      </option>
                    ))}
                  </select>
                </div>

                <div className="space-y-2">
                  <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                    <Award className="size-4 text-indigo-400" />
                    <span>Evaluation Matrix Rubric</span>
                  </label>
                  <select
                    value={selectedRubricId}
                    onChange={(e) => setSelectedRubricId(e.target.value)}
                    className="w-full bg-slate-800/90 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-colors"
                  >
                    <option value="">Default Criterion Matrix</option>
                    {rubrics.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.title || r.name} ({r.criteria.length} criteria, {r.total_marks || r.total_max_score} pts)
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Drag and Drop Zone */}
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-2xl p-10 text-center cursor-pointer transition-all ${
                  isDragging
                    ? "border-teal-400 bg-teal-500/10 shadow-lg shadow-teal-500/10 scale-[1.01]"
                    : selectedFiles.length > 0
                    ? "border-teal-500/40 bg-slate-800/40"
                    : "border-slate-700/80 bg-slate-800/20 hover:border-slate-600 hover:bg-slate-800/30"
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  accept=".zip,.pdf,.py,.cpp,.java,.docx,.txt"
                  onChange={handleFileChange}
                  className="hidden"
                />

                {selectedFiles.length === 0 ? (
                  <div className="space-y-3">
                    <div className="size-14 mx-auto rounded-2xl bg-teal-500/10 flex items-center justify-center text-teal-400 border border-teal-500/20">
                      <FileArchive className="size-7" />
                    </div>
                    <div>
                      <p className="text-base font-semibold text-slate-200">
                        Drag and drop your ZIP archive or submission files here
                      </p>
                      <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">
                        Supports <span className="text-teal-300 font-mono">.zip</span>,{" "}
                        <span className="text-teal-300 font-mono">.pdf</span>,{" "}
                        <span className="text-teal-300 font-mono">.py</span>,{" "}
                        <span className="text-teal-300 font-mono">.docx</span>. Filenames like{" "}
                        <code className="text-teal-200 bg-slate-800 px-1.5 py-0.5 rounded text-[11px]">
                          Roll_201_Alice.py
                        </code>{" "}
                        or{" "}
                        <code className="text-teal-200 bg-slate-800 px-1.5 py-0.5 rounded text-[11px]">
                          202_Lab.pdf
                        </code>{" "}
                        are automatically resolved to students.
                      </p>
                    </div>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="border-slate-700 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs"
                    >
                      Browse Files
                    </Button>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div className="size-14 mx-auto rounded-2xl bg-teal-500/20 flex items-center justify-center text-teal-300 border border-teal-500/30">
                      <CheckCircle2 className="size-7" />
                    </div>
                    <div>
                      <p className="text-base font-semibold text-teal-300">
                        {selectedFiles.length === 1 ? selectedFiles[0].name : `${selectedFiles.length} files selected`}
                      </p>
                      <p className="text-xs text-slate-400 mt-1">
                        Total size:{" "}
                        {(
                          selectedFiles.reduce((acc, f) => acc + f.size, 0) /
                          (1024 * 1024)
                        ).toFixed(2)}{" "}
                        MB • Ready for in-memory extraction & secure storage upload.
                      </p>
                    </div>
                    <div className="flex items-center justify-center gap-3">
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedFiles([]);
                        }}
                        className="text-slate-400 hover:text-red-400 text-xs"
                      >
                        Remove Selection
                      </Button>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          fileInputRef.current?.click();
                        }}
                        className="border-slate-700 text-slate-200 text-xs"
                      >
                        Change Files
                      </Button>
                    </div>
                  </div>
                )}
              </div>

              {/* Upload CTA */}
              <div className="flex items-center justify-between pt-2">
                <div className="text-xs text-slate-400 flex items-center gap-2">
                  <ShieldAlert className="size-4 text-teal-400" />
                  <span>FERPA-compliant AES-256 identifier encryption & Secure Storage.</span>
                </div>
                <Button
                  onClick={handleUploadAndEvaluate}
                  disabled={selectedFiles.length === 0 || stage === "uploading"}
                  className="bg-gradient-to-r from-teal-500 to-indigo-600 hover:from-teal-600 hover:to-indigo-700 text-white font-medium px-6 py-2.5 rounded-xl shadow-lg shadow-teal-500/10 transition-all flex items-center gap-2"
                >
                  {stage === "uploading" ? (
                    <>
                      <Loader2 className="size-4 animate-spin" />
                      <span>Ingesting & Unpacking...</span>
                    </>
                  ) : (
                    <>
                      <Sparkles className="size-4" />
                      <span>Upload & Run Evaluation Pipeline</span>
                    </>
                  )}
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* STAGE 2: LIVE ASYNC POLLING STATUS BAR */}
        {stage === "processing" && (
          <div className="bg-slate-900/90 rounded-2xl border border-teal-500/30 p-8 backdrop-blur-md shadow-2xl space-y-6 animate-fade-in">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-xs font-semibold px-2.5 py-1 rounded-md bg-teal-500/10 text-teal-400 border border-teal-500/20">
                  CELERY WORKER ACTIVE
                </span>
                <h2 className="text-2xl font-bold text-slate-100 mt-2 flex items-center gap-3">
                  <Loader2 className="size-6 text-teal-400 animate-spin" />
                  <span>Evaluating Submissions in Background</span>
                </h2>
                <p className="text-sm text-slate-400 mt-1">
                  Worker task <code className="text-teal-300 font-mono text-xs">{batchJobId}</code> is generating
                  embeddings, querying Qdrant peer cosine similarity, and calling Gemini 2.5 Flash with strict rubric criteria.
                </p>
              </div>
              <div className="text-right">
                <p className="text-3xl font-extrabold text-teal-300">
                  {jobStatus ? `${jobStatus.percent}%` : "0%"}
                </p>
                <p className="text-xs text-slate-400 mt-0.5">
                  {jobStatus ? `${jobStatus.current} of ${jobStatus.total} evaluated` : "Initializing worker..."}
                </p>
              </div>
            </div>

            {/* Live Progress Bar */}
            <div className="space-y-2">
              <div className="w-full bg-slate-800 rounded-full h-3 overflow-hidden p-0.5 border border-slate-700">
                <div
                  className="bg-gradient-to-r from-teal-400 via-cyan-400 to-indigo-500 h-full rounded-full transition-all duration-500 ease-out shadow-sm"
                  style={{ width: `${Math.max(jobStatus?.percent || 5, 5)}%` }}
                />
              </div>
              <div className="flex justify-between text-xs text-slate-500">
                <span>FastAPI Ingestion (HTTP 202)</span>
                <span>Qdrant Peer Similarity</span>
                <span>Gemini Matrix Rubric</span>
                <span>Synchronized Draft Grades</span>
              </div>
            </div>

            {/* Pipeline Stage Badges */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-4 border-t border-slate-800">
              <div className="bg-slate-800/60 p-3 rounded-xl border border-slate-700/60 flex items-center gap-3">
                <CheckCircle2 className="size-5 text-teal-400 shrink-0" />
                <div className="text-xs">
                  <p className="font-semibold text-slate-200">Roster Resolution</p>
                  <p className="text-slate-400">Roll numbers mapped to enrolled students</p>
                </div>
              </div>
              <div className="bg-slate-800/60 p-3 rounded-xl border border-slate-700/60 flex items-center gap-3">
                <Layers className="size-5 text-cyan-400 shrink-0" />
                <div className="text-xs">
                  <p className="font-semibold text-slate-200">Vector Embeddings</p>
                  <p className="text-slate-400">Cosine similarity audit vs prior peers</p>
                </div>
              </div>
              <div className="bg-slate-800/60 p-3 rounded-xl border border-slate-700/60 flex items-center gap-3">
                <Sparkles className="size-5 text-indigo-400 shrink-0" />
                <div className="text-xs">
                  <p className="font-semibold text-slate-200">Gemini 2.5 Flash</p>
                  <p className="text-slate-400">Structured EvaluationResult JSON schema</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* STAGE 3: INSTRUCTOR REVIEW & OVERRIDE PANEL */}
        {stage === "review" && (
          <div className="space-y-6 animate-fade-in">
            {/* Overview Metric Banner */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-slate-900/80 border border-slate-800 p-5 rounded-2xl">
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Total Submissions</p>
                <p className="text-2xl font-bold text-slate-100 mt-1">{submissions.length}</p>
                <p className="text-xs text-teal-400 mt-1 flex items-center gap-1">
                  <CheckCircle2 className="size-3.5" />
                  <span>{completedCount} evaluated</span>
                </p>
              </div>

              <div className="bg-slate-900/80 border border-slate-800 p-5 rounded-2xl">
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Average Score</p>
                <p className="text-2xl font-bold text-teal-300 mt-1">{avgScore} / 100</p>
                <p className="text-xs text-slate-400 mt-1">Rubric benchmarked</p>
              </div>

              <div className="bg-slate-900/80 border border-slate-800 p-5 rounded-2xl">
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Peer Plagiarism Flags</p>
                <p className="text-2xl font-bold text-amber-300 mt-1">{flaggedCount}</p>
                <p className="text-xs text-slate-400 mt-1">&gt;75% Qdrant vector match</p>
              </div>

              <div className="bg-slate-900/80 border border-slate-800 p-5 rounded-2xl">
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Unmatched Files</p>
                <p className={`text-2xl font-bold mt-1 ${unmatchedCount > 0 ? "text-red-400" : "text-emerald-400"}`}>
                  {unmatchedCount}
                </p>
                <p className="text-xs text-slate-400 mt-1">
                  {unmatchedCount > 0 ? "Requires manual roll binding" : "All students matched"}
                </p>
              </div>
            </div>

            {/* Unmatched Submissions Warning Banner & Resolver */}
            {unmatchedCount > 0 && (
              <div className="bg-amber-500/10 border border-amber-500/30 rounded-2xl p-6 space-y-4">
                <div className="flex items-center gap-3">
                  <AlertTriangle className="size-6 text-amber-400 shrink-0" />
                  <div>
                    <h3 className="text-base font-bold text-amber-200">
                      {unmatchedCount} Unmatched Submission(s) Require Manual Roster Assignment
                    </h3>
                    <p className="text-xs text-amber-300/80 mt-0.5">
                      The filename roll number did not match any enrolled student in this classroom. Select an enrolled
                      student from the dropdown to assign the submission.
                    </p>
                  </div>
                </div>

                <div className="space-y-3 pt-2">
                  {submissions
                    .filter((s) => s.status === "unmatched" || !s.student_id)
                    .map((sub) => (
                      <div
                        key={sub.id}
                        className="bg-slate-900/90 border border-amber-500/20 rounded-xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4"
                      >
                        <div className="flex items-center gap-3">
                          <div className="size-10 rounded-lg bg-amber-500/10 flex items-center justify-center text-amber-400 shrink-0">
                            <UserX className="size-5" />
                          </div>
                          <div>
                            <p className="text-sm font-semibold text-slate-100">{sub.file_name}</p>
                            <p className="text-xs text-slate-400">
                              Detected Roll: <code className="text-amber-300 font-mono">{sub.roll}</code> • ID:{" "}
                              <span className="font-mono text-[10px] text-slate-500">{sub.id.slice(0, 8)}...</span>
                            </p>
                          </div>
                        </div>

                        <div className="flex items-center gap-2">
                          <select
                            value={resolvingStudentId[sub.id] || ""}
                            onChange={(e) =>
                              setResolvingStudentId((prev) => ({
                                ...prev,
                                [sub.id]: e.target.value,
                              }))
                            }
                            className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-100 focus:outline-none focus:ring-1 focus:ring-amber-400"
                          >
                            <option value="">Select Enrolled Student...</option>
                            {students.map((st) => (
                              <option key={st.id} value={st.id}>
                                {st.roll_number} — {st.full_name}
                              </option>
                            ))}
                          </select>
                          <Button
                            size="sm"
                            onClick={() => handleAssignStudent(sub.id, resolvingStudentId[sub.id])}
                            className="bg-amber-500 hover:bg-amber-600 text-slate-950 font-semibold text-xs px-3 py-1.5 rounded-lg flex items-center gap-1.5"
                          >
                            <UserCheck className="size-3.5" />
                            <span>Assign</span>
                          </Button>
                        </div>
                      </div>
                    ))}
                </div>
              </div>
            )}

            {/* Filter and Search Controls */}
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="relative flex-1 max-w-md">
                <Search className="size-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <Input
                  type="text"
                  placeholder="Search by student, roll number, or file name..."
                  value={searchFilter}
                  onChange={(e) => setSearchFilter(e.target.value)}
                  className="pl-9 bg-slate-800/80 border-slate-700 text-xs rounded-xl"
                />
              </div>

              <div className="flex items-center gap-2">
                <Filter className="size-4 text-slate-400" />
                {(["all", "completed", "flagged", "unmatched"] as const).map((filterKey) => (
                  <Button
                    key={filterKey}
                    variant={statusFilter === filterKey ? "default" : "outline"}
                    size="sm"
                    onClick={() => setStatusFilter(filterKey)}
                    className={`text-xs capitalize rounded-xl ${
                      statusFilter === filterKey
                        ? "bg-teal-500 hover:bg-teal-600 text-slate-950 font-semibold"
                        : "border-slate-700 text-slate-300 hover:bg-slate-800"
                    }`}
                  >
                    {filterKey}
                  </Button>
                ))}
              </div>
            </div>

            {/* Submissions Review List */}
            <div className="space-y-4">
              {filteredSubmissions.length === 0 ? (
                <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-12 text-center">
                  <FileText className="size-10 text-slate-600 mx-auto mb-3" />
                  <p className="text-base font-semibold text-slate-300">No submissions found</p>
                  <p className="text-xs text-slate-500 mt-1">Try adjusting your search query or status filter.</p>
                </div>
              ) : (
                filteredSubmissions.map((sub) => {
                  const isExpanded = expandedSubId === sub.id;
                  const isFlagged = sub.similarity > 0.75;
                  const isUnmatched = sub.status === "unmatched" || !sub.student_id;
                  const isApproved = stampedSubs[sub.id] || sub.status === "approved";

                  return (
                    <div
                      key={sub.id}
                      className={`bg-slate-900/90 rounded-2xl border transition-all ${
                        isFlagged
                          ? "border-amber-500/40 shadow-lg shadow-amber-500/5"
                          : isUnmatched
                          ? "border-red-500/30"
                          : "border-slate-800 hover:border-slate-700"
                      }`}
                    >
                      {/* Main Card Header */}
                      <div className="p-5 flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                        <div className="flex items-start gap-4">
                          <div
                            className={`size-11 rounded-xl flex items-center justify-center font-bold text-sm shrink-0 ${
                              isFlagged
                                ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                                : isUnmatched
                                ? "bg-red-500/10 text-red-400 border border-red-500/20"
                                : "bg-teal-500/10 text-teal-400 border border-teal-500/20"
                            }`}
                          >
                            {sub.roll || "N/A"}
                          </div>

                          <div>
                            <div className="flex items-center gap-2">
                              <h4 className="text-base font-bold text-slate-100">{sub.student}</h4>
                              {isApproved ? (
                                <Badge className="bg-emerald-500/10 text-emerald-300 border-emerald-500/20 text-[10px]">
                                  Approved
                                </Badge>
                              ) : isUnmatched ? (
                                <Badge className="bg-red-500/10 text-red-400 border-red-500/20 text-[10px]">
                                  Unmatched Roll
                                </Badge>
                              ) : (
                                <Badge className="bg-teal-500/10 text-teal-300 border-teal-500/20 text-[10px]">
                                  AI Draft Ready
                                </Badge>
                              )}
                            </div>

                            <div className="flex items-center gap-3 text-xs text-slate-400 mt-1">
                              <span className="font-mono text-slate-300">{sub.file_name}</span>
                              {sub.file_url && (
                                <a
                                  href={sub.file_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-teal-400 hover:text-teal-300 flex items-center gap-1 underline underline-offset-2"
                                >
                                  <span>View Raw Asset</span>
                                  <ExternalLink className="size-3" />
                                </a>
                              )}
                            </div>
                          </div>
                        </div>

                        {/* Badges & Metrics Bar */}
                        <div className="flex flex-wrap items-center gap-3">
                          {/* 3-Way Plagiarism Badges */}
                          <div className="flex items-center gap-2">
                            {isFlagged ? (
                              <span className="px-2.5 py-1 rounded-lg bg-amber-500/10 text-amber-300 border border-amber-500/30 text-xs font-semibold flex items-center gap-1.5">
                                <ShieldAlert className="size-3.5" />
                                <span>{(sub.similarity * 100).toFixed(0)}% Peer Match</span>
                              </span>
                            ) : (
                              <span className="px-2.5 py-1 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-medium flex items-center gap-1">
                                <Check className="size-3" />
                                <span>Clean ({(sub.similarity * 100).toFixed(0)}%)</span>
                              </span>
                            )}

                            {sub.aiContent > 0 && (
                              <span className="px-2 py-1 rounded-lg bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 text-xs">
                                {(sub.aiContent * 100).toFixed(0)}% AI
                              </span>
                            )}
                          </div>

                          {/* Score Pill */}
                          <div className="px-3.5 py-1.5 rounded-xl bg-slate-800 border border-slate-700 text-right">
                            <span className="text-lg font-extrabold text-teal-300">
                              {sub.score.toFixed(0)}
                            </span>
                            <span className="text-xs text-slate-400 font-medium">
                              {" "}
                              / {sub.max_score || 100}
                            </span>
                          </div>

                          {/* Expand/Collapse Review Button */}
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setExpandedSubId(isExpanded ? null : sub.id)}
                            className="text-slate-300 hover:text-white p-2"
                          >
                            {isExpanded ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}
                          </Button>
                        </div>
                      </div>

                      {/* Expanded Review & Override Workspace */}
                      {isExpanded && (
                        <div className="border-t border-slate-800 p-6 bg-slate-950/60 rounded-b-2xl space-y-6">
                          {/* Criteria Breakdown Grid */}
                          <div>
                            <h5 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-3 flex items-center gap-2">
                              <Award className="size-4 text-teal-400" />
                              <span>Criteria Rubric Breakdown</span>
                            </h5>

                            {sub.criteria_scores && sub.criteria_scores.length > 0 ? (
                              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                {sub.criteria_scores.map((crit, idx) => (
                                  <div
                                    key={idx}
                                    className="bg-slate-900 border border-slate-800/80 rounded-xl p-3.5 space-y-1.5"
                                  >
                                    <div className="flex items-center justify-between">
                                      <p className="text-xs font-semibold text-slate-200">
                                        {crit.criterion_name || `Criterion ${idx + 1}`}
                                      </p>
                                      <span className="text-xs font-bold text-teal-300">
                                        {crit.score} / {crit.max || 10}
                                      </span>
                                    </div>
                                    {crit.rationale && (
                                      <p className="text-xs text-slate-400 leading-relaxed">{crit.rationale}</p>
                                    )}
                                  </div>
                                ))}
                              </div>
                            ) : (
                              <p className="text-xs text-slate-500 italic">No structured criteria saved.</p>
                            )}
                          </div>

                          {/* Qualitative Feedback */}
                          {sub.feedback && (
                            <div>
                              <h5 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-2 flex items-center gap-2">
                                <Sparkles className="size-4 text-indigo-400" />
                                <span>Qualitative AI Evaluation Notes</span>
                              </h5>
                              <div className="bg-slate-900 border border-slate-800/80 rounded-xl p-4 text-xs text-slate-300 leading-relaxed whitespace-pre-line">
                                {sub.feedback}
                              </div>
                            </div>
                          )}

                          {/* Teacher Override & Grade Stamping Form */}
                          <div className="pt-4 border-t border-slate-800/80 grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
                            <div className="space-y-1.5">
                              <label className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                                <Sliders className="size-3.5 text-teal-400" />
                                <span>Instructor Final Score</span>
                              </label>
                              <Input
                                type="number"
                                min={0}
                                max={sub.max_score || 100}
                                value={overrideScores[sub.id] ?? sub.score}
                                onChange={(e) =>
                                  setOverrideScores((prev) => ({
                                    ...prev,
                                    [sub.id]: parseFloat(e.target.value) || 0,
                                  }))
                                }
                                className="bg-slate-900 border-slate-700 text-xs rounded-xl"
                              />
                            </div>

                            <div className="space-y-1.5 md:col-span-1">
                              <label className="text-xs font-semibold text-slate-300">Teacher Feedback Note</label>
                              <Input
                                type="text"
                                placeholder="Add custom instructor feedback..."
                                value={overrideFeedbacks[sub.id] || ""}
                                onChange={(e) =>
                                  setOverrideFeedbacks((prev) => ({
                                    ...prev,
                                    [sub.id]: e.target.value,
                                  }))
                                }
                                className="bg-slate-900 border-slate-700 text-xs rounded-xl"
                              />
                            </div>

                            <div className="flex items-center gap-2">
                              <Button
                                onClick={() => handleStampGrade(sub)}
                                className="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs py-2 rounded-xl flex items-center justify-center gap-1.5 shadow-md shadow-emerald-500/10"
                              >
                                <Check className="size-3.5" />
                                <span>Stamp Grade & Approve</span>
                              </Button>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
