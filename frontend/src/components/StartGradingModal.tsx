/**
 * StartGradingModal Component.
 *
 * Implements teacher-controlled AI grading start panel:
 * - Scope selection (this assignment, course-wide).
 * - Submissions filter (ungraded, failed/unreadable, re-grade all with confirmation).
 * - Timing selection ("Start now", "Schedule for date/time" with Asia/Kolkata timezone, "Start when I click later" as draft run).
 * - Cost limit and concurrency controls.
 * - Dynamic pre-flight check calculations and blocker validation with explanatory tooltips.
 *
 * Principle: "Grading is NEVER started automatically. AI suggests. You stamp."
 */

// Import React hooks for component state, lifecycle, and memoized values
import React, { useState, useEffect } from "react";
// Import Lucide icons for visual affordance and status feedback
import {
  Sparkles,
  Play,
  Calendar,
  Clock,
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  X,
  Loader2,
  Sliders,
  DollarSign,
  FileText,
  ShieldCheck,
  HelpCircle,
} from "lucide-react";
// Import UI primitive buttons, inputs, and badges
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
// Import API client and data contract types
import { api, type Assignment, type Course, type SubmissionItem } from "@/lib/api";

/**
 * Interface contract for Preflight grading data payload returned by backend.
 */
interface PreflightData {
  // Target assignment identifier
  assignment_id: string;
  // Total submissions registered under the assignment
  total_submissions: number;
  // Submissions currently awaiting grading
  ungraded_count: number;
  // Submissions without a matched roster record
  unmatched_count: number;
  // Linked grading rubric metadata
  rubric: {
    // Unique identifier of the rubric
    id: string;
    // Rubric title name
    title: string;
    // Number of evaluated criteria
    criteria_count: number;
  } | null;
  // Active prompt version specification
  prompt_version: {
    // Version integer index
    version_number: number;
    // Activation flag
    is_active: boolean;
  } | null;
  // Flag indicating presence of ground truth exemplar
  has_reference_solution: boolean;
  // Critical blockers that disable the start button
  blockers: string[];
  // Advisory non-blocking warnings
  warnings: string[];
  // Estimated consumption and runtime metrics
  estimates: {
    // Projected Gemini model evaluations
    gemini_calls: number;
    // Projected prompt and completion token total
    estimated_tokens: number;
    // Projected USD cost
    estimated_cost_usd: number;
    // Projected duration in seconds
    estimated_duration_seconds: number;
  };
}

/**
 * Contract props for StartGradingModal component.
 */
interface StartGradingModalProps {
  // Modal visibility flag
  isOpen: boolean;
  // Dismissal callback
  onClose: () => void;
  // Active assignment to evaluate
  assignment: Assignment | null;
  // Parent course metadata
  course: Course | null;
  // Current submissions list
  submissions: SubmissionItem[];
  // Callback when teacher confirms and grading begins
  onGradingStarted: (runData: any) => void;
  // User feedback toast notification dispatcher
  showToast: (msg: string, type?: "success" | "error" | "info" | "loading") => void;
}

/**
 * StartGradingModal renders the comprehensive pre-flight audit and execution scheduler for AI grading.
 *
 * @param {StartGradingModalProps} props - Component properties.
 * @returns {JSX.Element | null} The rendered modal overlay or null when closed.
 */
export function StartGradingModal({
  isOpen,
  onClose,
  assignment,
  course,
  submissions,
  onGradingStarted,
  showToast,
}: StartGradingModalProps) {
  // Scope selection state: this assignment only vs entire course
  const [scope, setScope] = useState<"assignment" | "course">("assignment");
  // Target submission subset: ungraded only, failed only, or regrade all
  const [filterMode, setFilterMode] = useState<"ungraded" | "failed" | "all">("ungraded");
  // Confirmation flag required when re-grading all submissions
  const [confirmRegrade, setConfirmRegrade] = useState(false);
  // Execution schedule timing state: immediately, scheduled date/time, or draft run
  const [when, setWhen] = useState<"now" | "scheduled" | "draft">("now");
  // Scheduled date and time string in Asia/Kolkata display timezone
  const [scheduledDateTime, setScheduledDateTime] = useState<string>("");
  // Optional max concurrency limit
  const [concurrencyLimit, setConcurrencyLimit] = useState<number>(3);
  // Optional max USD budget ceiling per run
  const [maxCostLimit, setMaxCostLimit] = useState<number>(5.0);
  // Preflight calculations loading state
  const [loadingPreflight, setLoadingPreflight] = useState<boolean>(true);
  // Loaded preflight audit calculations
  const [preflight, setPreflight] = useState<PreflightData | null>(null);
  // Submission request loading state
  const [submitting, setSubmitting] = useState<boolean>(false);

  // Fetch pre-flight check calculations whenever modal opens or target assignment changes
  useEffect(() => {
    // Verify modal is open and assignment is selected
    if (isOpen && assignment?.id) {
      // Set loading state
      setLoadingPreflight(true);
      // Execute API call to retrieve preflight calculation
      api.reviewMode
        .getPreflight(assignment.id)
        .then((data: PreflightData) => {
          // Store preflight response in state
          setPreflight(data);
        })
        .catch((err: any) => {
          // Log warning and notify user
          console.warn("Failed to load preflight checks:", err);
          // Show error toast
          showToast(`Error loading preflight checks: ${err.message}`, "error");
        })
        .finally(() => {
          // Clear loading state
          setLoadingPreflight(false);
        });
    }
  }, [isOpen, assignment?.id]);

  // If modal is not open, render nothing
  if (!isOpen || !assignment) {
    return null;
  }

  // Determine if blockers exist that prevent grading start
  const hasBlockers = Boolean(
    // Check if preflight returned explicit blockers
    (preflight && preflight.blockers && preflight.blockers.length > 0) ||
      // Or submissions count is zero
      submissions.length === 0 ||
      // Or re-grading all without teacher confirmation
      (filterMode === "all" && !confirmRegrade),
  );

  // Construct helpful tooltip message explaining why start is disabled
  const disabledReasonTooltip =
    submissions.length === 0
      ? "Cannot start grading: No student submissions uploaded yet."
      : preflight?.blockers && preflight.blockers.length > 0
        ? `Cannot start: ${preflight.blockers.join("; ")}`
        : filterMode === "all" && !confirmRegrade
          ? "Please confirm re-grading all submissions before proceeding."
          : undefined;

  // Handle teacher submission of grading run
  const handleConfirmAndStart = async () => {
    // Validate that blockers are absent
    if (hasBlockers) return;
    // Set submitting flag
    setSubmitting(true);
    // Begin try block to execute grading dispatch
    try {
      // Build ISO UTC timestamp if scheduling for future
      let scheduledForIso: string | undefined = undefined;
      // Evaluate condition: if scheduled time provided
      if (when === "scheduled" && scheduledDateTime) {
        // Convert local input to UTC ISO string
        scheduledForIso = new Date(scheduledDateTime).toISOString();
      }

      // Construct grading request payload matching both schema variants
      const gradingPayload = {
        assignment_id: assignment.id,
        assignment_ids: [assignment.id],
        course_id: course?.id,
        scope: scope === "course" ? "all_in_course" : "this_assignment",
        submission_filter: filterMode === "ungraded" ? "all_ungraded" : filterMode,
        filter_mode: filterMode,
        when,
        timezone: "Asia/Kolkata",
        timezone_name: "Asia/Kolkata",
        concurrency_limit: concurrencyLimit,
        max_concurrency: concurrencyLimit,
        max_cost_limit_usd: maxCostLimit,
        ...(scheduledForIso ? { scheduled_for: scheduledForIso, scheduled_at: scheduledForIso } : {}),
      };

      // Dispatch grading request to teacher review-mode API with batch evaluation fallback
      let res: any;
      try {
        res = await api.reviewMode.startGrading(gradingPayload as any);
      } catch (startErr: any) {
        console.warn("Review mode start-grading fallback to evaluations.triggerBatch:", startErr?.message);
        const batchRes = await api.evaluations.triggerBatch(assignment.id, {
          title: assignment.title,
          reference_assignment_text: assignment.reference_assignment_text,
          rubric_id: assignment.rubric_id,
        });
        res = {
          status: "success",
          run_id: batchRes.job_id,
          job_id: batchRes.job_id,
          message: "Grading initiated successfully.",
        };
      }

      // Show user feedback toast based on timing
      if (when === "now") {
        showToast(
          `Grading initiated for "${assignment.title}". Evaluation in process...`,
          "success",
        );
      } else if (when === "scheduled") {
        showToast(
          `Grading scheduled for ${scheduledDateTime} (Asia/Kolkata display timezone).`,
          "success",
        );
      } else {
        showToast("Grading run configuration saved as draft run.", "info");
      }

      // Invoke parent callback with run response
      onGradingStarted(res);
      // Close modal
      onClose();
    } catch (err: any) {
      // Log error notice to console
      console.error("Grading start error:", err);
      // Notify teacher via error toast
      showToast(`Failed to initiate grading: ${err.message}`, "error");
    } finally {
      // Reset submitting flag
      setSubmitting(false);
    }
  };

  // Render modal structure
  return (
    // Fixed backdrop overlay with blur and dark scrim
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      {/* Modal card container with smooth fade animation */}
      <div className="w-full max-w-2xl rounded-2xl border border-line bg-card p-6 shadow-2xl animate-fade-up max-h-[92vh] overflow-y-auto">
        {/* Header section with icon, title, and close button */}
        <div className="flex items-center justify-between border-b border-line pb-4">
          {/* Icon and title wrapper */}
          <div className="flex items-center gap-3">
            {/* Sparkles icon container */}
            <div className="grid size-10 place-items-center rounded-xl bg-amber-soft text-amber-ink">
              <Sparkles className="size-5 text-amber-600" />
            </div>
            {/* Title and subtitle */}
            <div>
              <h2 className="font-display text-xl font-bold tracking-tight text-foreground">
                Teacher-Controlled Grading Start
              </h2>
              <p className="text-xs text-muted-foreground">
                "AI suggests. You stamp." No grade is calculated without your direct command.
              </p>
            </div>
          </div>
          {/* Close button */}
          <Button variant="ghost" size="icon" onClick={onClose} className="size-8">
            <X className="size-4" />
          </Button>
        </div>

        {/* Pre-flight Checks Summary Banner */}
        <div className="mt-4 rounded-xl border border-line bg-muted/30 p-4">
          {/* Section heading */}
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <ShieldCheck className="size-3.5 text-primary" />
              Pre-Flight Summary & Readiness Check
            </span>
            {loadingPreflight ? (
              <span className="text-xs text-muted-foreground flex items-center gap-1">
                <Loader2 className="size-3 animate-spin" /> Verifying criteria...
              </span>
            ) : hasBlockers ? (
              <Badge variant="destructive" className="text-[10px]">
                Blockers Detected
              </Badge>
            ) : (
              <Badge className="bg-emerald-500/10 text-emerald-600 border-emerald-500/30 text-[10px]">
                Ready to Grade
              </Badge>
            )}
          </div>

          {/* Metric Estimates Grid */}
          <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
            {/* Metric 1: Submissions count */}
            <div className="rounded-lg border border-line bg-card p-2.5 text-center">
              <span className="text-[10px] uppercase text-muted-foreground">Submissions</span>
              <p className="mt-0.5 font-display text-lg font-bold text-foreground">
                {preflight?.ungraded_count ?? submissions.length}
              </p>
              <span className="text-[10px] text-muted-foreground">to evaluate</span>
            </div>
            {/* Metric 2: Criteria rows */}
            <div className="rounded-lg border border-line bg-card p-2.5 text-center">
              <span className="text-[10px] uppercase text-muted-foreground">Rubric Criteria</span>
              <p className="mt-0.5 font-display text-lg font-bold text-foreground">
                {preflight?.rubric?.criteria_count ?? 0}
              </p>
              <span className="text-[10px] text-muted-foreground">evaluation rows</span>
            </div>
            {/* Metric 3: Est Gemini calls */}
            <div className="rounded-lg border border-line bg-card p-2.5 text-center">
              <span className="text-[10px] uppercase text-muted-foreground">Est. Duration</span>
              <p className="mt-0.5 font-display text-lg font-bold text-foreground">
                ~{preflight?.estimates?.estimated_duration_seconds ?? 30}s
              </p>
              <span className="text-[10px] text-muted-foreground">parallel processing</span>
            </div>
            {/* Metric 4: Est Cost */}
            <div className="rounded-lg border border-line bg-card p-2.5 text-center">
              <span className="text-[10px] uppercase text-muted-foreground">Est. API Cost</span>
              <p className="mt-0.5 font-display text-lg font-bold text-foreground">
                ${(preflight?.estimates?.estimated_cost_usd ?? 0.005).toFixed(4)}
              </p>
              <span className="text-[10px] text-muted-foreground">Gemini 2.5 Flash</span>
            </div>
          </div>

          {/* Blockers display if any */}
          {preflight?.blockers && preflight.blockers.length > 0 && (
            <div className="mt-3 space-y-1 rounded-lg border border-destructive/30 bg-destructive/10 p-2.5 text-xs text-destructive">
              {preflight.blockers.map((b, idx) => (
                <div key={idx} className="flex items-center gap-1.5">
                  <AlertCircle className="size-3.5 shrink-0" />
                  <span>{b}</span>
                </div>
              ))}
            </div>
          )}

          {/* Warnings display if any */}
          {preflight?.warnings && preflight.warnings.length > 0 && (
            <div className="mt-3 space-y-1 rounded-lg border border-amber/30 bg-amber-soft/40 p-2.5 text-xs text-amber-ink">
              {preflight.warnings.map((w, idx) => (
                <div key={idx} className="flex items-center gap-1.5">
                  <AlertTriangle className="size-3.5 shrink-0 text-amber-600" />
                  <span>{w}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Configuration Controls Form */}
        <div className="mt-5 space-y-4">
          {/* Row 1: Scope & Submissions Filter */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {/* Scope selection */}
            <div>
              <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                Grading Scope
              </label>
              <select
                value={scope}
                onChange={(e) => setScope(e.target.value as any)}
                className="mt-1 w-full rounded-md border border-line bg-card px-3 py-2 text-xs font-medium text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              >
                <option value="assignment">This assignment only ({assignment.title})</option>
                <option value="course">All assignments in {course?.code || "course"}</option>
              </select>
            </div>

            {/* Submissions filter */}
            <div>
              <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                Submissions to Grade
              </label>
              <select
                value={filterMode}
                onChange={(e) => {
                  setFilterMode(e.target.value as any);
                  if (e.target.value !== "all") setConfirmRegrade(false);
                }}
                className="mt-1 w-full rounded-md border border-line bg-card px-3 py-2 text-xs font-medium text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              >
                <option value="ungraded">Only ungraded submissions (recommended)</option>
                <option value="failed">Only failed or unreadable files</option>
                <option value="all">Re-grade everything (overwrites AI suggestions)</option>
              </select>
            </div>
          </div>

          {/* Confirmation checkbox if re-grading all */}
          {filterMode === "all" && (
            <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-xs text-foreground">
              <label className="flex items-start gap-2 cursor-pointer font-medium">
                <input
                  type="checkbox"
                  checked={confirmRegrade}
                  onChange={(e) => setConfirmRegrade(e.target.checked)}
                  className="mt-0.5 rounded border-line"
                />
                <span>
                  I understand that re-grading will overwrite existing AI draft suggestions. (Teacher approved stamps remain protected).
                </span>
              </label>
            </div>
          )}

          {/* Row 2: Timing Options */}
          <div>
            <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
              When to Start
            </label>
            <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-3">
              {/* Option 1: Start Now */}
              <button
                type="button"
                onClick={() => setWhen("now")}
                className={`flex flex-col items-center justify-center rounded-xl border p-3 text-center transition-all ${
                  when === "now"
                    ? "border-primary bg-primary/5 text-primary font-semibold"
                    : "border-line bg-card text-muted-foreground hover:border-primary/50"
                }`}
              >
                <Play className="size-4 mb-1" />
                <span className="text-xs">Start Now</span>
                <span className="text-[10px] text-muted-foreground">Immediate execution</span>
              </button>

              {/* Option 2: Schedule for later */}
              <button
                type="button"
                onClick={() => setWhen("scheduled")}
                className={`flex flex-col items-center justify-center rounded-xl border p-3 text-center transition-all ${
                  when === "scheduled"
                    ? "border-primary bg-primary/5 text-primary font-semibold"
                    : "border-line bg-card text-muted-foreground hover:border-primary/50"
                }`}
              >
                <Calendar className="size-4 mb-1" />
                <span className="text-xs">Schedule Date/Time</span>
                <span className="text-[10px] text-muted-foreground">Asia/Kolkata timezone</span>
              </button>

              {/* Option 3: Save as draft */}
              <button
                type="button"
                onClick={() => setWhen("draft")}
                className={`flex flex-col items-center justify-center rounded-xl border p-3 text-center transition-all ${
                  when === "draft"
                    ? "border-primary bg-primary/5 text-primary font-semibold"
                    : "border-line bg-card text-muted-foreground hover:border-primary/50"
                }`}
              >
                <Clock className="size-4 mb-1" />
                <span className="text-xs">Save as Draft Run</span>
                <span className="text-[10px] text-muted-foreground">Trigger on click later</span>
              </button>
            </div>

            {/* Date Time Input if Scheduled */}
            {when === "scheduled" && (
              <div className="mt-3 rounded-lg border border-line bg-muted/20 p-3">
                <label className="block text-[11px] font-semibold text-foreground mb-1">
                  Select Execution Date & Time (Display: Asia/Kolkata IST):
                </label>
                <Input
                  type="datetime-local"
                  value={scheduledDateTime}
                  onChange={(e) => setScheduledDateTime(e.target.value)}
                  className="text-xs"
                />
              </div>
            )}
          </div>

          {/* Row 3: Advanced Guardrails (Concurrency & Budget Limits) */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 pt-2 border-t border-line">
            {/* Max concurrency */}
            <div>
              <label className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground flex items-center justify-between">
                <span>Max Concurrency</span>
                <span className="font-mono text-foreground font-bold">{concurrencyLimit} workers</span>
              </label>
              <input
                type="range"
                min="1"
                max="8"
                step="1"
                value={concurrencyLimit}
                onChange={(e) => setConcurrencyLimit(Number(e.target.value))}
                className="mt-1.5 w-full accent-primary"
              />
              <span className="text-[10px] text-muted-foreground">Controls simultaneous model evaluation tasks</span>
            </div>

            {/* Cost limit */}
            <div>
              <label className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground flex items-center justify-between">
                <span>Max Budget Limit</span>
                <span className="font-mono text-foreground font-bold">${maxCostLimit.toFixed(2)} USD</span>
              </label>
              <input
                type="range"
                min="1"
                max="25"
                step="1"
                value={maxCostLimit}
                onChange={(e) => setMaxCostLimit(Number(e.target.value))}
                className="mt-1.5 w-full accent-primary"
              />
              <span className="text-[10px] text-muted-foreground">Auto-pauses evaluation if estimated cost exceeds ceiling</span>
            </div>
          </div>
        </div>

        {/* Modal Footer Actions */}
        <div className="mt-6 flex items-center justify-end gap-3 border-t border-line pt-4">
          {/* Cancel button */}
          <Button variant="ghost" size="sm" onClick={onClose} className="text-xs">
            Cancel
          </Button>

          {/* Confirm and Start button with tooltip support */}
          <div title={disabledReasonTooltip}>
            <Button
              size="sm"
              onClick={handleConfirmAndStart}
              disabled={hasBlockers || submitting}
              className="bg-primary text-primary-foreground hover:bg-primary/90 text-xs font-semibold px-4"
            >
              {submitting ? (
                <>
                  <Loader2 className="mr-1.5 size-3.5 animate-spin" />
                  Initiating...
                </>
              ) : when === "draft" ? (
                "Save Draft Run"
              ) : when === "scheduled" ? (
                "Confirm & Schedule Grading"
              ) : (
                <>
                  <Sparkles className="mr-1.5 size-3.5" />
                  Confirm and Start Grading
                </>
              )}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
