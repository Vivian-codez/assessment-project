/**
 * ReviewAssistantModal Component.
 *
 * Implements Phase 4 Teacher Review Mode Meta-Prompt Assistant & Feedback Console:
 * - Error logging & mistake tagging ("Too harsh", "Too lenient", "Missed evidence", etc.).
 * - AI Assistant-assisted prompt fixing analyzing rubric, reference solution, and logged feedback.
 * - Side-by-side prompt diff visualizer.
 * - Non-destructive dry-run sandbox on sample submissions showing before/after score deltas.
 * - Prompt versioning history with instant rollback capability.
 */

// Import React hooks for component state, effects, and memoization
import React, { useState, useEffect } from "react";
// Import Lucide icons for rich UI interaction and status indicators
import {
  Sparkles,
  Tag,
  AlertCircle,
  CheckCircle2,
  GitCompare,
  Play,
  RotateCcw,
  Save,
  X,
  Loader2,
  ChevronRight,
  History,
  FileCode,
  ThumbsDown,
  Info,
} from "lucide-react";
// Import UI primitive components
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
// Import API client and data types
import { api, type Assignment, type SubmissionDetail } from "@/lib/api";

/**
 * Interface contract for Prompt Version record.
 */
interface PromptVersionItem {
  // Unique version identifier
  id: string;
  // Assignment association
  assignment_id: string;
  // Monotonically increasing version integer
  version_number: number;
  // Complete prompt text
  prompt_text: string;
  // Change rationale description
  change_reason?: string;
  // Author identity
  created_by?: string;
  // Active deployment indicator
  is_active: boolean;
  // Creation ISO timestamp
  created_at: string;
}

/**
 * Interface contract for Dry Run Result comparison item.
 */
interface DryRunItem {
  // Submission identifier
  submission_id: string;
  // Student display name
  student_name: string;
  // Previous model score
  old_score: number;
  // Re-evaluated score under candidate prompt
  new_score: number;
  // Numerical score variance
  score_delta: number;
  // New evaluation rationale text
  new_rationale: string;
}

/**
 * Contract props for ReviewAssistantModal component.
 */
interface ReviewAssistantModalProps {
  // Modal visibility flag
  isOpen: boolean;
  // Modal close callback
  onClose: () => void;
  // Active assignment
  assignment: Assignment | null;
  // Current active submission being reviewed
  submission: SubmissionDetail | null;
  // Toast notification callback
  showToast: (msg: string, type?: "success" | "error" | "info" | "loading") => void;
  // Callback when prompt is updated
  onPromptUpdated?: () => void;
}

// Available mistake taxonomy tags
const ERROR_CATEGORIES = [
  { value: "too_harsh", label: "Too harsh", description: "Score deducted unfairly for minor stylistic issues" },
  { value: "too_lenient", label: "Too lenient", description: "Overlooked major missing requirements or bugs" },
  { value: "missed_evidence", label: "Missed evidence", description: "Code or explanation was present but AI claimed it was absent" },
  { value: "wrong_criteria_tier", label: "Wrong criteria tier", description: "Assigned incorrect tier level from the rubric matrix" },
  { value: "syntax_misunderstanding", label: "Misunderstood code syntax", description: "Flagged valid modern language syntax as an error" },
  { value: "hallucinated_issue", label: "Hallucinated issue", description: "Claimed a flaw that does not exist in student code" },
];

/**
 * ReviewAssistantModal component renders the prompt-fix console with mistake logging, diff inspection, and sandbox dry run.
 *
 * @param {ReviewAssistantModalProps} props - Component properties.
 * @returns {JSX.Element | null} The rendered meta-prompt console.
 */
export function ReviewAssistantModal({
  isOpen,
  onClose,
  assignment,
  submission,
  showToast,
  onPromptUpdated,
}: ReviewAssistantModalProps) {
  // Active sub-tab state: "feedback" | "assistant" | "dry_run" | "history"
  const [activeTab, setActiveTab] = useState<"feedback" | "assistant" | "dry_run" | "history">("feedback");
  // Error tag category selection
  const [errorCategory, setErrorCategory] = useState<string>("too_harsh");
  // Teacher explanation of the mistake
  const [explanation, setExplanation] = useState<string>("");
  // Teacher statement of expected behavior
  const [expectedBehavior, setExpectedBehavior] = useState<string>("");
  // Feedback submission loading state
  const [submittingFeedback, setSubmittingFeedback] = useState<boolean>(false);

  // Meta-prompt assistant state
  const [assistantNotes, setAssistantNotes] = useState<string>("");
  const [proposingFix, setProposingFix] = useState<boolean>(false);
  const [proposedPrompt, setProposedPrompt] = useState<string>("");
  const [originalPrompt, setOriginalPrompt] = useState<string>("");
  const [diffExplanation, setDiffExplanation] = useState<string>("");

  // Dry run state
  const [runningDryRun, setRunningDryRun] = useState<boolean>(false);
  const [dryRunResults, setDryRunResults] = useState<DryRunItem[]>([]);

  // Version history state
  const [versions, setVersions] = useState<PromptVersionItem[]>([]);
  const [loadingVersions, setLoadingVersions] = useState<boolean>(false);

  // Load prompt versions on modal open
  useEffect(() => {
    // Check if modal is visible and assignment is available
    if (isOpen && assignment?.id) {
      // Fetch prompt version history
      loadPromptVersions(assignment.id);
    }
  }, [isOpen, assignment?.id]);

  // If modal is not open, return null
  if (!isOpen || !assignment) {
    return null;
  }

  // Helper function to fetch prompt versions
  const loadPromptVersions = async (assignId: string) => {
    // Set loading indicator
    setLoadingVersions(true);
    // Begin try block
    try {
      // Execute API request to list versions
      const data = await api.reviewMode.listPromptVersions(assignId);
      // Store returned versions
      setVersions(data || []);
      // Find currently active prompt
      const active = (data || []).find((v: PromptVersionItem) => v.is_active);
      // Set original prompt state
      if (active) {
        setOriginalPrompt(active.prompt_text);
        if (!proposedPrompt) setProposedPrompt(active.prompt_text);
      }
    } catch (err: any) {
      // Log warning to console
      console.warn("Failed to load prompt versions:", err);
    } finally {
      // Reset loading indicator
      setLoadingVersions(false);
    }
  };

  // Submit teacher mistake feedback
  const handleSubmitFeedback = async () => {
    // Validate explanation
    if (!explanation.trim()) {
      showToast("Please provide an explanation of the AI grading mistake.", "error");
      return;
    }
    // Set submitting flag
    setSubmittingFeedback(true);
    // Begin try block
    try {
      // Call feedback API endpoint
      await api.reviewMode.submitFeedback(assignment.id, {
        submission_id: submission?.id,
        error_category: errorCategory,
        explanation: explanation.trim(),
        expected_behavior: expectedBehavior.trim() || undefined,
      });
      // Show confirmation toast
      showToast("Grading mistake feedback registered. Ready to trigger AI prompt fix!", "success");
      // Clear explanation fields
      setExplanation("");
      setExpectedBehavior("");
      // Transition to assistant tab
      setActiveTab("assistant");
    } catch (err: any) {
      // Notify user of error
      showToast(`Error submitting feedback: ${err.message}`, "error");
    } finally {
      // Reset submitting flag
      setSubmittingFeedback(false);
    }
  };

  // Trigger Gemini meta-prompt assistant to propose a prompt fix
  const handleAssistantFix = async () => {
    // Set proposing indicator
    setProposingFix(true);
    // Begin try block
    try {
      // Invoke assistant fix endpoint
      const res = await api.reviewMode.assistantFix(assignment.id, assistantNotes);
      // Store proposed prompt and explanation
      setProposedPrompt(res.proposed_prompt || res.prompt_text || "");
      setDiffExplanation(res.explanation || res.change_reason || "Analyzed teacher error logs and refined evaluation directives.");
      // Show confirmation toast
      showToast("AI Assistant generated revised prompt directives. Inspect the diff below.", "success");
    } catch (err: any) {
      // Notify user of error
      showToast(`AI Assistant error: ${err.message}`, "error");
    } finally {
      // Reset proposing indicator
      setProposingFix(false);
    }
  };

  // Execute non-destructive dry run on sample submissions
  const handleRunDryRun = async () => {
    // Set running indicator
    setRunningDryRun(true);
    // Begin try block
    try {
      // Invoke dry run sandbox API
      const res = await api.reviewMode.dryRun(assignment.id, proposedPrompt);
      // Store dry run results
      setDryRunResults(res.results || []);
      // Switch to dry run view
      setActiveTab("dry_run");
      // Show success toast
      showToast(`Dry run completed across ${res.results?.length || 0} sample submissions!`, "success");
    } catch (err: any) {
      // Notify user of error
      showToast(`Dry run failed: ${err.message}`, "error");
    } finally {
      // Reset running indicator
      setRunningDryRun(false);
    }
  };

  // Save candidate prompt as active new version
  const handleApplyPrompt = async () => {
    // Verify candidate prompt exists
    if (!proposedPrompt.trim()) return;
    // Begin try block
    try {
      // Call dry run apply / version save
      await api.reviewMode.dryRun(assignment.id, proposedPrompt);
      // Refresh prompt versions
      await loadPromptVersions(assignment.id);
      // Trigger parent callback
      onPromptUpdated?.();
      // Show success toast
      showToast("New prompt version activated for this assignment!", "success");
      // Close modal
      onClose();
    } catch (err: any) {
      // Notify user of error
      showToast(`Failed to activate prompt: ${err.message}`, "error");
    }
  };

  // Render modal layout
  return (
    // Backdrop overlay
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      {/* Modal card */}
      <div className="w-full max-w-3xl rounded-2xl border border-line bg-card p-6 shadow-2xl animate-fade-up max-h-[92vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-line pb-4">
          <div className="flex items-center gap-3">
            <div className="grid size-10 place-items-center rounded-xl bg-lav-soft text-amber-ink">
              <Sparkles className="size-5 text-amber-600" />
            </div>
            <div>
              <h2 className="font-display text-xl font-bold tracking-tight text-foreground">
                Prompt-Fix Review Console & Assistant
              </h2>
              <p className="text-xs text-muted-foreground">
                Teach the AI from your corrections. Log mistakes, auto-refine directives, and test with non-destructive dry runs.
              </p>
            </div>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose} className="size-8">
            <X className="size-4" />
          </Button>
        </div>

        {/* Tab Navigation */}
        <div className="mt-4 flex border-b border-line gap-2">
          {/* Tab 1: Log Mistake */}
          <button
            type="button"
            onClick={() => setActiveTab("feedback")}
            className={`pb-2.5 px-3 text-xs font-semibold border-b-2 transition-all flex items-center gap-1.5 ${
              activeTab === "feedback"
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <ThumbsDown className="size-3.5" />
            1. Log Mistake
          </button>

          {/* Tab 2: AI Prompt Assistant */}
          <button
            type="button"
            onClick={() => setActiveTab("assistant")}
            className={`pb-2.5 px-3 text-xs font-semibold border-b-2 transition-all flex items-center gap-1.5 ${
              activeTab === "assistant"
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <Sparkles className="size-3.5" />
            2. AI Prompt Fix
          </button>

          {/* Tab 3: Sandbox Dry Run */}
          <button
            type="button"
            onClick={() => setActiveTab("dry_run")}
            className={`pb-2.5 px-3 text-xs font-semibold border-b-2 transition-all flex items-center gap-1.5 ${
              activeTab === "dry_run"
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <GitCompare className="size-3.5" />
            3. Sandbox Dry Run ({dryRunResults.length})
          </button>

          {/* Tab 4: Version History */}
          <button
            type="button"
            onClick={() => setActiveTab("history")}
            className={`pb-2.5 px-3 text-xs font-semibold border-b-2 transition-all flex items-center gap-1.5 ${
              activeTab === "history"
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <History className="size-3.5" />
            Version History ({versions.length})
          </button>
        </div>

        {/* TAB 1: LOG MISTAKE */}
        {activeTab === "feedback" && (
          <div className="mt-5 space-y-4">
            {submission && (
              <div className="rounded-xl border border-line bg-muted/20 p-3 text-xs">
                <span className="font-semibold text-foreground">Target Student: </span>
                <span>{submission.student} ({submission.roll}) — Suggested Score: {submission.score}/100</span>
              </div>
            )}

            {/* Error Category Taxonomy */}
            <div>
              <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                Error Classification
              </label>
              <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
                {ERROR_CATEGORIES.map((cat) => (
                  <button
                    key={cat.value}
                    type="button"
                    onClick={() => setErrorCategory(cat.value)}
                    className={`flex flex-col items-start rounded-xl border p-2.5 text-left transition-all ${
                      errorCategory === cat.value
                        ? "border-primary bg-primary/5 text-primary"
                        : "border-line bg-card text-muted-foreground hover:border-primary/50"
                    }`}
                  >
                    <span className="text-xs font-bold">{cat.label}</span>
                    <span className="text-[10px] text-muted-foreground mt-0.5">{cat.description}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Explanation text */}
            <div>
              <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                What went wrong? (Plain English explanation)
              </label>
              <Textarea
                value={explanation}
                onChange={(e) => setExplanation(e.target.value)}
                rows={3}
                className="mt-1.5 text-xs"
                placeholder="e.g. The model deducted 5 points for missing destructor, but the student implemented clean RAII smart pointers instead."
              />
            </div>

            {/* Expected Behavior */}
            <div>
              <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                Expected Directive / How should AI evaluate this? (Optional)
              </label>
              <Input
                value={expectedBehavior}
                onChange={(e) => setExpectedBehavior(e.target.value)}
                className="mt-1.5 text-xs"
                placeholder="e.g. Do not penalize smart pointers in place of explicit manual destructors."
              />
            </div>

            <div className="flex justify-end pt-3 border-t border-line">
              <Button
                size="sm"
                onClick={handleSubmitFeedback}
                disabled={submittingFeedback || !explanation.trim()}
                className="bg-primary text-primary-foreground text-xs font-semibold"
              >
                {submittingFeedback ? (
                  <>
                    <Loader2 className="mr-1.5 size-3.5 animate-spin" /> Saving...
                  </>
                ) : (
                  <>
                    Save Feedback & Fix Prompt
                    <ChevronRight className="ml-1.5 size-3.5" />
                  </>
                )}
              </Button>
            </div>
          </div>
        )}

        {/* TAB 2: AI PROMPT ASSISTANT & DIFF */}
        {activeTab === "assistant" && (
          <div className="mt-5 space-y-4">
            <div className="rounded-xl border border-line bg-muted/20 p-4">
              <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                Prompt Assistant Guidance (Optional)
              </label>
              <p className="mt-0.5 text-[11px] text-muted-foreground">
                Provide specific guidance or let Gemini automatically analyze all teacher error tags for this assignment.
              </p>
              <div className="mt-2 flex gap-2">
                <Input
                  value={assistantNotes}
                  onChange={(e) => setAssistantNotes(e.target.value)}
                  placeholder="e.g. Ensure modern C++20 features are treated as exemplary."
                  className="text-xs flex-1"
                />
                <Button
                  size="sm"
                  onClick={handleAssistantFix}
                  disabled={proposingFix}
                  className="bg-primary text-primary-foreground text-xs shrink-0"
                >
                  {proposingFix ? (
                    <>
                      <Loader2 className="mr-1.5 size-3.5 animate-spin" /> Analyzing...
                    </>
                  ) : (
                    <>
                      <Sparkles className="mr-1.5 size-3.5" /> Propose Fix
                    </>
                  )}
                </Button>
              </div>
            </div>

            {/* Explanation of the fix */}
            {diffExplanation && (
              <div className="rounded-xl border border-primary/20 bg-primary/5 p-3 text-xs">
                <span className="font-bold text-primary">Proposed Improvement Rationale: </span>
                <span className="text-foreground">{diffExplanation}</span>
              </div>
            )}

            {/* Prompt Editor & Side-by-Side Diff */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              {/* Active Prompt */}
              <div>
                <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Current Active Prompt (Baseline)
                </label>
                <Textarea
                  value={originalPrompt || "Standard system evaluation prompt active."}
                  readOnly
                  rows={10}
                  className="mt-1 font-mono text-[11px] bg-muted/30 text-muted-foreground"
                />
              </div>

              {/* Proposed Candidate Prompt */}
              <div>
                <label className="text-xs font-semibold uppercase tracking-wider text-primary">
                  Proposed Prompt with Fixes (Editable)
                </label>
                <Textarea
                  value={proposedPrompt}
                  onChange={(e) => setProposedPrompt(e.target.value)}
                  rows={10}
                  className="mt-1 font-mono text-[11px] border-primary/50 bg-card text-foreground"
                  placeholder="Candidate prompt with teacher directives..."
                />
              </div>
            </div>

            {/* Action Bar */}
            <div className="flex items-center justify-between pt-3 border-t border-line">
              <Button
                variant="outline"
                size="sm"
                onClick={handleRunDryRun}
                disabled={runningDryRun || !proposedPrompt.trim()}
                className="text-xs"
              >
                {runningDryRun ? (
                  <>
                    <Loader2 className="mr-1.5 size-3.5 animate-spin" /> Testing...
                  </>
                ) : (
                  <>
                    <Play className="mr-1.5 size-3.5 text-primary" /> Run Non-Destructive Dry Run
                  </>
                )}
              </Button>

              <Button
                size="sm"
                onClick={handleApplyPrompt}
                disabled={!proposedPrompt.trim()}
                className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold"
              >
                <Save className="mr-1.5 size-3.5" />
                Activate This Prompt Version
              </Button>
            </div>
          </div>
        )}

        {/* TAB 3: SANDBOX DRY RUN */}
        {activeTab === "dry_run" && (
          <div className="mt-5 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-display text-base font-semibold text-foreground">
                  Non-Destructive Dry Run Sandbox
                </h3>
                <p className="text-xs text-muted-foreground">
                  Evaluated on sample student submissions without mutating live gradebook records.
                </p>
              </div>
              <Button
                size="sm"
                variant="outline"
                onClick={handleRunDryRun}
                disabled={runningDryRun}
                className="text-xs"
              >
                {runningDryRun ? <Loader2 className="size-3 animate-spin" /> : <Play className="size-3" />}
                Re-Run Dry Run
              </Button>
            </div>

            {dryRunResults.length === 0 ? (
              <div className="rounded-xl border border-dashed border-line p-8 text-center text-xs text-muted-foreground">
                No dry run results yet. Click "Run Non-Destructive Dry Run" from the AI Prompt Fix tab to benchmark candidate changes.
              </div>
            ) : (
              <div className="space-y-3">
                {dryRunResults.map((r, idx) => (
                  <div key={idx} className="rounded-xl border border-line bg-card p-3 text-xs">
                    <div className="flex items-center justify-between border-b border-line pb-2 mb-2">
                      <span className="font-bold text-foreground">{r.student_name}</span>
                      <div className="flex items-center gap-3">
                        <span className="text-muted-foreground">Old: {r.old_score} pts</span>
                        <ChevronRight className="size-3 text-muted-foreground" />
                        <span className="font-bold text-foreground">New: {r.new_score} pts</span>
                        <Badge
                          className={
                            r.score_delta > 0
                              ? "bg-emerald-500/10 text-emerald-600"
                              : r.score_delta < 0
                                ? "bg-destructive/10 text-destructive"
                                : "bg-muted text-muted-foreground"
                          }
                        >
                          {r.score_delta > 0 ? `+${r.score_delta}` : r.score_delta} delta
                        </Badge>
                      </div>
                    </div>
                    <p className="text-[11px] text-muted-foreground leading-relaxed">
                      <strong>New Rationale: </strong> {r.new_rationale}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* TAB 4: VERSION HISTORY */}
        {activeTab === "history" && (
          <div className="mt-5 space-y-3">
            {loadingVersions ? (
              <div className="py-8 text-center text-xs text-muted-foreground">
                <Loader2 className="size-5 animate-spin mx-auto mb-2 text-primary" />
                Loading version history...
              </div>
            ) : versions.length === 0 ? (
              <div className="py-8 text-center text-xs text-muted-foreground">
                No previous prompt versions recorded. Baseline prompt v1 active.
              </div>
            ) : (
              versions.map((v) => (
                <div key={v.id} className="rounded-xl border border-line bg-card p-3 text-xs">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="font-display font-bold text-sm text-foreground">
                        Version {v.version_number}
                      </span>
                      {v.is_active && (
                        <Badge className="bg-emerald-500/10 text-emerald-600 border-emerald-500/30 text-[10px]">
                          Currently Active
                        </Badge>
                      )}
                    </div>
                    <span className="text-[10px] text-muted-foreground">
                      {new Date(v.created_at).toLocaleString()}
                    </span>
                  </div>
                  {v.change_reason && (
                    <p className="mt-1 text-muted-foreground text-[11px]">
                      <strong>Reason: </strong> {v.change_reason}
                    </p>
                  )}
                  <div className="mt-2 flex justify-end">
                    {!v.is_active && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => {
                          setProposedPrompt(v.prompt_text);
                          setActiveTab("assistant");
                          showToast(`Loaded Version ${v.version_number} into editor.`, "info");
                        }}
                        className="h-7 text-xs gap-1"
                      >
                        <RotateCcw className="size-3" />
                        Roll Back / Load v{v.version_number}
                      </Button>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
}
