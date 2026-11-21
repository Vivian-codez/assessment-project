/**
 * AssignmentWizardModal Component.
 * Implements Phase 3 Guided 4-Step Assignment Creation Wizard:
 *   Step 1: Details (title, instructions, type, due date, max score, starter code).
 *   Step 2: Reference solution / model answer (universal file ingestion + live extracted text preview).
 *   Step 3: Rubric matrix (AI file parser for any format, templates, manual builder with descending points validation, student preview).
 *   Step 4: Submissions drop (multi-file / ZIP ingestion with roll-number matching table and manual resolution dropdowns).
 * Includes auto-saved drafts and status workflow (Draft -> Open -> Grading -> Reviewed -> Published).
 */

// Import React hooks for component state, effects, and memoization
import React, { useState, useEffect, useRef } from "react";
// Import Lucide icons for rich UI visualization and navigation
import {
  FileText,
  Upload,
  CheckCircle2,
  AlertCircle,
  Copy,
  Plus,
  Trash2,
  ChevronRight,
  ChevronLeft,
  Sparkles,
  Loader2,
  X,
  Eye,
  Sliders,
  FileCheck,
  Users,
  Save,
  Check,
} from "lucide-react";
// Import custom UI primitives
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
// Import API client and data types
import { api, type Assignment, type Rubric } from "@/lib/api";

// Define interface for criterion tier in the matrix builder
export interface WizardTier {
  // Unique string identifier for the tier
  id: string;
  // Label name of the tier (e.g., Exemplary, Proficient)
  level_name: string;
  // Point value associated with achieving this tier
  points: number;
  // Qualitative descriptor for this achievement tier
  description: string;
}

// Define interface for rubric criterion in the wizard
export interface WizardCriterion {
  // Unique string identifier for the criterion
  id: string;
  // Title or skill evaluated by this criterion
  criterion_name: string;
  // Percentage or weight contribution to final score
  weight: number;
  // Detailed explanation of the criterion's evaluation scope
  description: string;
  // Ordered list of performance tiers with descending points
  levels: WizardTier[];
}

// Define props contract for AssignmentWizardModal
interface AssignmentWizardModalProps {
  // Parent course ID for the assignment
  courseId: string;
  // Existing assignment ID if editing a draft
  initialAssignmentId?: string | null;
  // Callback invoked when modal is dismissed
  onClose: () => void;
  // Callback invoked when assignment is successfully created or published
  onCreated: (assignment: Assignment) => void;
  // Toast notification callback
  showToast: (msg: string) => void;
}

// Define default standard criteria blueprint for new rubrics
const DEFAULT_CRITERIA: WizardCriterion[] = [
  {
    id: "crit_1",
    criterion_name: "Functional Correctness & Logic",
    weight: 40,
    description: "Program correctly implements functional requirements without edge case defects.",
    levels: [
      { id: "t_1_1", level_name: "Exemplary", points: 4.0, description: "All functional specs completely and cleanly satisfied without bugs." },
      { id: "t_1_2", level_name: "Proficient", points: 3.0, description: "Core requirements satisfied with minor edge-case oversights." },
      { id: "t_1_3", level_name: "Developing", points: 2.0, description: "Partially functional; substantial deviations from rubric specifications." },
      { id: "t_1_4", level_name: "Unsatisfactory", points: 0.0, description: "Program fails to execute or core functionality is missing." },
    ],
  },
  {
    id: "crit_2",
    criterion_name: "Architecture & Modularity",
    weight: 30,
    description: "Code modularity, clean encapsulation, and naming conventions.",
    levels: [
      { id: "t_2_1", level_name: "Exemplary", points: 4.0, description: "Clean modular design with excellent separation of concerns." },
      { id: "t_2_2", level_name: "Proficient", points: 3.0, description: "Well organized with occasional redundancy or naming lapses." },
      { id: "t_2_3", level_name: "Developing", points: 2.0, description: "Monolithic design with poor modularity or unclear structure." },
      { id: "t_2_4", level_name: "Unsatisfactory", points: 0.0, description: "Unorganized or tangled implementation structure." },
    ],
  },
  {
    id: "crit_3",
    criterion_name: "Testing & Documentation",
    weight: 30,
    description: "Test coverage, computational efficiency, and inline commentary.",
    levels: [
      { id: "t_3_1", level_name: "Exemplary", points: 4.0, description: "Comprehensive test suite, optimal asymptotic efficiency, and clear comments." },
      { id: "t_3_2", level_name: "Proficient", points: 3.0, description: "Adequate documentation and reasonable performance with minor gaps." },
      { id: "t_3_3", level_name: "Developing", points: 2.0, description: "Sparse comments and suboptimal computational complexity." },
      { id: "t_3_4", level_name: "Unsatisfactory", points: 0.0, description: "Missing documentation; test cases crash or fail." },
    ],
  },
];

/**
 * 4-Step Guided Assignment Creation Wizard.
 */
export function AssignmentWizardModal({
  courseId,
  initialAssignmentId,
  onClose,
  onCreated,
  showToast,
}: AssignmentWizardModalProps) {
  // Step state tracker: 1 (Details), 2 (Reference Solution), 3 (Rubric), 4 (Submissions)
  const [currentStep, setCurrentStep] = useState<number>(1);
  // Assignment primary database ID
  const [assignmentId, setAssignmentId] = useState<string>(initialAssignmentId || "");
  // Assignment status workflow: Draft -> Open -> Grading -> Reviewed -> Published
  const [assignmentStatus, setAssignmentStatus] = useState<string>("Draft");
  // Timestamp string of last auto-saved draft
  const [lastSavedTime, setLastSavedTime] = useState<string>("");
  // Auto-saving indicator boolean
  const [isSavingDraft, setIsSavingDraft] = useState<boolean>(false);

  // Step 1: Assignment Details Form State
  const [title, setTitle] = useState<string>("");
  const [description, setDescription] = useState<string>("");
  const [assignmentType, setAssignmentType] = useState<string>("homework");
  const [dueDate, setDueDate] = useState<string>("");
  const [maxScore, setMaxScore] = useState<number>(100);
  const [similarityThreshold, setSimilarityThreshold] = useState<number>(70);
  const [starterCode, setStarterCode] = useState<string>("");

  // Step 2: Reference Solution / Model Answer State
  const [referenceText, setReferenceText] = useState<string>("");
  const [referenceFilename, setReferenceFilename] = useState<string>("");
  const [isUploadingRef, setIsUploadingRef] = useState<boolean>(false);
  const [refTextPreview, setRefTextPreview] = useState<string>("");

  // Step 3: Rubric Builder State
  const [rubricMode, setRubricMode] = useState<"builder" | "parse" | "preview">("builder");
  const [criteria, setCriteria] = useState<WizardCriterion[]>(DEFAULT_CRITERIA);
  const [isParsingRubric, setIsParsingRubric] = useState<boolean>(false);
  const [parsedPreviewText, setParsedPreviewText] = useState<string>("");

  // Step 4: Submissions Drop & Matching Table State
  const [isUploadingSubmissions, setIsUploadingSubmissions] = useState<boolean>(false);
  const [matchedFiles, setMatchedFiles] = useState<any[]>([]);
  const [unmatchedFiles, setUnmatchedFiles] = useState<any[]>([]);
  const [duplicateFiles, setDuplicateFiles] = useState<any[]>([]);
  const [courseRoster, setCourseRoster] = useState<any[]>([]);

  // Ref for file input triggers
  const refFileInputRef = useRef<HTMLInputElement>(null);
  const rubricFileInputRef = useRef<HTMLInputElement>(null);
  const submissionFileInputRef = useRef<HTMLInputElement>(null);

  // Auto-save draft debouncing timer
  useEffect(() => {
    // Only auto-save if title is non-empty
    if (!title.trim()) return;

    // Set debounce timeout to 1.5 seconds
    const timer = setTimeout(async () => {
      try {
        setIsSavingDraft(true);
        // Invoke auto-save draft API endpoint
        const draftRes = await api.assignments.saveDraft({
          id: assignmentId || undefined,
          course_id: courseId,
          title: title.trim(),
          description,
          max_score: maxScore,
          reference_assignment_text: referenceText,
          assignment_type: assignmentType,
          similarity_threshold: similarityThreshold,
          starter_code: starterCode,
        });
        // Update assignment ID if first save
        if (!assignmentId && draftRes.id) {
          setAssignmentId(draftRes.id);
        }
        // Set timestamp
        setLastSavedTime(new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }));
      } catch (err: any) {
        // Silently capture draft auto-save notices
      } finally {
        setIsSavingDraft(false);
      }
    }, 1500);

    return () => clearTimeout(timer);
  }, [title, description, assignmentType, maxScore, similarityThreshold, starterCode, referenceText, assignmentId, courseId]);

  // Handle universal reference solution file upload
  const handleReferenceFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploadingRef(true);
    try {
      // Ensure we have an active draft assignment ID first
      let activeId = assignmentId;
      if (!activeId) {
        const draftRes = await api.assignments.saveDraft({
          course_id: courseId,
          title: title.trim() || "Assignment with Reference Solution",
          max_score: maxScore,
        });
        activeId = draftRes.id;
        setAssignmentId(activeId);
      }

      // Call universal reference solution endpoint
      const res = await api.assignments.uploadReferenceSolution(activeId, file);
      setReferenceText(res.reference_solution_text);
      setRefTextPreview(res.extracted_preview);
      setReferenceFilename(res.filename);
      showToast(`Reference solution extracted: ${res.filename} (${res.file_size} bytes)`);
    } catch (err: any) {
      showToast(`Error extracting reference solution: ${err.message}`);
    } finally {
      setIsUploadingRef(false);
    }
  };

  // Handle uploading and AI parsing of rubric file of any format
  const handleRubricFileParse = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsParsingRubric(true);
    try {
      // Call universal rubric parser endpoint
      const parsed = await api.rubrics.parseRubricFile(file);
      // Map parsed criteria into wizard criteria format
      const formatted: WizardCriterion[] = (parsed.criteria || []).map((c, i) => ({
        id: `parsed_crit_${i + 1}`,
        criterion_name: c.criterion_name || `Criterion ${i + 1}`,
        weight: c.weight || Math.round(100 / (parsed.criteria?.length || 1)),
        description: c.description || "",
        levels: (c.levels || []).map((lvl, l_idx) => ({
          id: `p_tier_${i}_${l_idx}`,
          level_name: lvl.level_name || `Tier ${l_idx + 1}`,
          points: lvl.points,
          description: lvl.description || "",
        })),
      }));

      if (formatted.length > 0) {
        setCriteria(formatted);
        setParsedPreviewText(parsed.extracted_text_preview || "");
        setRubricMode("builder");
        showToast(`AI parsed ${formatted.length} criteria from ${file.name} with descending tiers.`);
      } else {
        showToast("No criteria detected in document. Switched to manual builder.");
      }
    } catch (err: any) {
      showToast(`Error parsing rubric file: ${err.message}`);
    } finally {
      setIsParsingRubric(false);
    }
  };

  // Handle submissions batch drop (multi-file or ZIP)
  const handleSubmissionsBatchUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    setIsUploadingSubmissions(true);
    try {
      // Ensure active assignment ID
      let activeId = assignmentId;
      if (!activeId) {
        const draftRes = await api.assignments.saveDraft({
          course_id: courseId,
          title: title.trim() || "New Assignment",
          max_score: maxScore,
        });
        activeId = draftRes.id;
        setAssignmentId(activeId);
      }

      // Convert FileList to array
      const fileArray = Array.from(files);
      // Call batch submissions ingestion endpoint
      const res = await api.assignments.uploadBatchSubmissions(activeId, fileArray);
      setMatchedFiles(res.matched || []);
      setUnmatchedFiles(res.unmatched || []);
      setDuplicateFiles(res.duplicates || []);
      setCourseRoster(res.roster || []);
      showToast(`Ingested ${res.total_files} files: ${res.matched.length} matched, ${res.unmatched.length} unmatched.`);
    } catch (err: any) {
      showToast(`Error processing submissions: ${err.message}`);
    } finally {
      setIsUploadingSubmissions(false);
    }
  };

  // Validate descending points across tiers for each criterion
  const validateDescendingTiers = (): { valid: boolean; error?: string } => {
    for (const c of criteria) {
      if (!c.criterion_name.trim()) {
        return { valid: false, error: "All criteria must have a title." };
      }
      for (let i = 0; i < c.levels.length - 1; i++) {
        if (c.levels[i].points < c.levels[i + 1].points) {
          return {
            valid: false,
            error: `In criterion "${c.criterion_name}", tier points must descend: "${c.levels[i].level_name}" (${c.levels[i].points} pts) is less than "${c.levels[i + 1].level_name}" (${c.levels[i + 1].points} pts).`,
          };
        }
      }
    }
    return { valid: true };
  };

  // Calculate sum of criteria weights
  const totalWeight = criteria.reduce((sum, c) => sum + (c.weight || 0), 0);

  // Finalize and save assignment
  const handleFinalize = async (publish: boolean) => {
    // Validate title
    if (!title.trim()) {
      showToast("Please enter an assignment title.");
      setCurrentStep(1);
      return;
    }

    // Validate rubric tiers descending
    const validation = validateDescendingTiers();
    if (!validation.valid) {
      showToast(validation.error || "Please fix rubric tier points.");
      setCurrentStep(3);
      return;
    }

    try {
      setIsSavingDraft(true);
      // 1. Save or update Rubric first
      const rubricRes = await api.rubrics.create({
        title: `${title.trim()} Rubric`,
        course_id: courseId,
        total_marks: maxScore,
        criteria: criteria.map((c, idx) => ({
          criterion_name: c.criterion_name,
          description: c.description,
          weight: c.weight,
          order_index: idx,
          levels: c.levels.map((lvl) => ({
            level_name: lvl.level_name,
            points: lvl.points,
            description: lvl.description,
          })),
        })),
      });

      // 2. Persist or publish assignment
      const targetStatus = publish ? "Open" : "Draft";
      let savedAssignment: Assignment;

      if (assignmentId) {
        savedAssignment = await api.assignments.update(assignmentId, {
          title: title.trim(),
          description,
          max_score: maxScore,
          rubric_id: rubricRes.id,
          reference_assignment_text: referenceText,
        });
      } else {
        savedAssignment = await api.assignments.create(courseId, {
          title: title.trim(),
          description,
          max_score: maxScore,
          rubric_id: rubricRes.id,
          reference_assignment_text: referenceText,
        });
      }

      showToast(publish ? `Assignment "${title}" published successfully!` : "Assignment saved as draft.");
      onCreated(savedAssignment);
      onClose();
    } catch (err: any) {
      showToast(`Error saving assignment: ${err.message}`);
    } finally {
      setIsSavingDraft(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-ink/40 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="w-full max-w-4xl rounded-[20px] border border-line bg-card shadow-2xl animate-fade-up my-6 flex flex-col max-h-[92vh]">
        {/* Modal Header with Progress Stepper */}
        <div className="border-b border-line p-6 pb-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex size-10 items-center justify-center rounded-xl bg-ink text-card font-bold text-sm shadow-sm">
                {currentStep}
              </div>
              <div>
                <h2 className="text-lg font-bold text-ink">
                  {currentStep === 1 && "Step 1: Assignment Details"}
                  {currentStep === 2 && "Step 2: Reference Solution / Model Answer"}
                  {currentStep === 3 && "Step 3: Matrix Rubric Designer"}
                  {currentStep === 4 && "Step 4: Submissions Ingestion & Roster Match"}
                </h2>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="text-xs text-faint">
                    Status: <strong className="text-ink font-semibold">{assignmentStatus}</strong>
                  </span>
                  {lastSavedTime && (
                    <span className="text-[11px] text-teal-ink bg-teal-soft/40 px-2 py-0.5 rounded-full flex items-center gap-1 font-mono">
                      <Save className="size-3" /> Auto-saved {lastSavedTime}
                    </span>
                  )}
                  {isSavingDraft && (
                    <span className="text-[11px] text-amber-ink flex items-center gap-1">
                      <Loader2 className="size-3 animate-spin" /> Saving...
                    </span>
                  )}
                </div>
              </div>
            </div>
            <button
              onClick={onClose}
              className="text-faint hover:text-ink transition-colors p-1.5 rounded-lg hover:bg-tint/60"
            >
              <X className="size-5" />
            </button>
          </div>

          {/* 4-Step Stepper Progress Bar */}
          <div className="grid grid-cols-4 gap-2 mt-6">
            {[
              { num: 1, label: "Details" },
              { num: 2, label: "Reference Exemplar" },
              { num: 3, label: "Rubric Matrix" },
              { num: 4, label: "Submissions Drop" },
            ].map((step) => {
              const isPast = currentStep > step.num;
              const isCurrent = currentStep === step.num;
              return (
                <button
                  key={step.num}
                  type="button"
                  onClick={() => setCurrentStep(step.num)}
                  className={`text-left p-2 rounded-xl transition-all border ${
                    isCurrent
                      ? "bg-tint/70 border-line shadow-sm font-semibold text-ink"
                      : isPast
                      ? "border-transparent text-faint hover:bg-tint/30"
                      : "border-transparent text-faint/60 cursor-default"
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span
                      className={`flex size-5 items-center justify-center rounded-full text-[10px] font-bold ${
                        isPast
                          ? "bg-teal-ink text-card"
                          : isCurrent
                          ? "bg-ink text-card"
                          : "bg-tint text-faint"
                      }`}
                    >
                      {isPast ? <Check className="size-3" /> : step.num}
                    </span>
                    <span className="text-xs truncate">{step.label}</span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Modal Body: Dynamic Step Content */}
        <div className="p-6 overflow-y-auto flex-1 space-y-6">
          {/* STEP 1: ASSIGNMENT DETAILS */}
          {currentStep === 1 && (
            <div className="space-y-4">
              <div>
                <label className="text-xs font-bold uppercase tracking-wider text-faint">
                  Assignment Title <span className="text-amber-ink">*</span>
                </label>
                <Input
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Distributed Systems Lab 2: Raft Consensus"
                  className="mt-1.5 h-10 font-medium text-sm"
                  autoFocus
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="text-xs font-bold uppercase tracking-wider text-faint">
                    Assignment Type
                  </label>
                  <select
                    value={assignmentType}
                    onChange={(e) => setAssignmentType(e.target.value)}
                    className="mt-1.5 w-full h-10 rounded-xl border border-line bg-card px-3 text-sm font-medium text-ink focus:outline-none focus:ring-2 focus:ring-ink/20"
                  >
                    <option value="homework">Homework / Problem Set</option>
                    <option value="code">Code / Programming Lab</option>
                    <option value="essay">Written Essay / Report</option>
                    <option value="lab">Scientific Lab Report</option>
                    <option value="exam">Midterm / Final Exam</option>
                  </select>
                </div>

                <div>
                  <label className="text-xs font-bold uppercase tracking-wider text-faint">
                    Max Possible Score
                  </label>
                  <Input
                    type="number"
                    value={maxScore}
                    onChange={(e) => setMaxScore(Number(e.target.value) || 100)}
                    className="mt-1.5 h-10 text-sm font-mono font-medium"
                  />
                </div>

                <div>
                  <label className="text-xs font-bold uppercase tracking-wider text-faint">
                    Similarity Threshold (%)
                  </label>
                  <Input
                    type="number"
                    value={similarityThreshold}
                    onChange={(e) => setSimilarityThreshold(Number(e.target.value) || 70)}
                    className="mt-1.5 h-10 text-sm font-mono font-medium"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-bold uppercase tracking-wider text-faint">
                  Instructions & Problem Specification
                </label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={4}
                  placeholder="Paste problem prompt, functional requirements, and constraints provided to students..."
                  className="mt-1.5 w-full rounded-xl border border-line bg-card p-3 text-sm text-ink placeholder:text-faint/60 focus:outline-none focus:ring-2 focus:ring-ink/20 font-sans"
                />
              </div>

              <div>
                <label className="text-xs font-bold uppercase tracking-wider text-faint flex items-center justify-between">
                  <span>Teacher Starter Code / Boilerplate (Excluded from Plagiarism Detection)</span>
                  <span className="text-[11px] font-normal text-faint lowercase">MOSS-style winnowing exclusion</span>
                </label>
                <textarea
                  value={starterCode}
                  onChange={(e) => setStarterCode(e.target.value)}
                  rows={3}
                  placeholder="Optional skeleton code, method stubs, or starter template provided to all students..."
                  className="mt-1.5 w-full rounded-xl border border-line bg-tint/30 p-3 text-xs font-mono text-ink placeholder:text-faint/60 focus:outline-none focus:ring-2 focus:ring-ink/20"
                />
              </div>
            </div>
          )}

          {/* STEP 2: REFERENCE SOLUTION / MODEL ANSWER */}
          {currentStep === 2 && (
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-tint/40 border border-line flex items-start gap-3">
                <Sparkles className="size-5 text-amber-ink shrink-0 mt-0.5" />
                <div className="text-xs text-ink/80 space-y-1">
                  <p className="font-semibold text-ink">Universal Reference Ingestion</p>
                  <p>
                    Provide your benchmark model answer or exemplar code. The autograding engine compares student
                    submissions against this exemplar to verify algorithmic correctness and detect alternative valid approaches.
                  </p>
                </div>
              </div>

              {/* Upload Zone */}
              <div
                onClick={() => refFileInputRef.current?.click()}
                className="border-2 border-dashed border-line rounded-2xl p-6 text-center hover:border-ink/40 hover:bg-tint/20 transition-all cursor-pointer group"
              >
                <input
                  type="file"
                  ref={refFileInputRef}
                  onChange={handleReferenceFileUpload}
                  className="hidden"
                  accept=".py,.java,.cpp,.c,.js,.ts,.pdf,.docx,.txt,.md,.zip"
                />
                <div className="flex flex-col items-center gap-2">
                  <div className="size-12 rounded-2xl bg-tint flex items-center justify-center text-faint group-hover:text-ink transition-colors">
                    {isUploadingRef ? <Loader2 className="size-6 animate-spin" /> : <Upload className="size-6" />}
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-ink">
                      {isUploadingRef ? "Extracting model answer..." : "Click or drop reference file here"}
                    </p>
                    <p className="text-xs text-faint mt-0.5">
                      Accepts Python, Java, C++, PDF, DOCX, TXT, or ZIP archives
                    </p>
                  </div>
                </div>
              </div>

              {referenceFilename && (
                <div className="flex items-center justify-between p-3 rounded-xl bg-teal-soft/40 border border-teal/40">
                  <div className="flex items-center gap-2 text-xs text-teal-ink font-medium">
                    <CheckCircle2 className="size-4 shrink-0" />
                    <span>Uploaded file: <strong>{referenceFilename}</strong></span>
                  </div>
                  <button
                    onClick={() => {
                      setReferenceFilename("");
                      setReferenceText("");
                      setRefTextPreview("");
                    }}
                    className="text-xs text-faint hover:text-ink p-1"
                  >
                    <X className="size-4" />
                  </button>
                </div>
              )}

              {/* Text Area for Pasted Reference Solution */}
              <div>
                <label className="text-xs font-bold uppercase tracking-wider text-faint flex items-center justify-between">
                  <span>Reference Solution Content (Extracted or Pasted)</span>
                  <span className="text-[11px] font-mono text-faint">{referenceText.length} characters</span>
                </label>
                <textarea
                  value={referenceText}
                  onChange={(e) => setReferenceText(e.target.value)}
                  rows={8}
                  placeholder="Paste or edit the full model solution text or code here..."
                  className="mt-1.5 w-full rounded-xl border border-line bg-card p-3 text-xs font-mono text-ink placeholder:text-faint/60 focus:outline-none focus:ring-2 focus:ring-ink/20"
                />
              </div>
            </div>
          )}

          {/* STEP 3: MATRIX RUBRIC DESIGNER */}
          {currentStep === 3 && (
            <div className="space-y-4">
              {/* Header Controls & Mode Switcher */}
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line pb-3">
                <div className="flex items-center gap-1.5 bg-tint/60 p-1 rounded-xl">
                  <button
                    type="button"
                    onClick={() => setRubricMode("builder")}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                      rubricMode === "builder" ? "bg-card text-ink shadow-sm" : "text-faint hover:text-ink"
                    }`}
                  >
                    <Sliders className="mr-1.5 inline size-3.5" /> Matrix Builder
                  </button>
                  <button
                    type="button"
                    onClick={() => rubricFileInputRef.current?.click()}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                      rubricMode === "parse" ? "bg-card text-ink shadow-sm" : "text-faint hover:text-ink"
                    }`}
                  >
                    <Sparkles className="mr-1.5 inline size-3.5 text-amber-ink" /> AI File Parser
                  </button>
                  <button
                    type="button"
                    onClick={() => setRubricMode("preview")}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                      rubricMode === "preview" ? "bg-card text-ink shadow-sm" : "text-faint hover:text-ink"
                    }`}
                  >
                    <Eye className="mr-1.5 inline size-3.5" /> Student Preview
                  </button>
                </div>

                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-1.5 text-xs">
                    <span className="text-faint">Weights sum:</span>
                    <Badge
                      variant="outline"
                      className={`font-mono text-xs ${
                        totalWeight === 100
                          ? "bg-teal-soft/50 text-teal-ink border-teal/40"
                          : "bg-amber-soft/50 text-amber-ink border-amber/40"
                      }`}
                    >
                      {totalWeight}%
                    </Badge>
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-8 text-xs font-medium"
                    onClick={() => {
                      const newCrit: WizardCriterion = {
                        id: `crit_${Date.now()}`,
                        criterion_name: `Criterion ${criteria.length + 1}`,
                        weight: 20,
                        description: "Evaluates student implementation against specific standard.",
                        levels: [
                          { id: `t_${Date.now()}_1`, level_name: "Exemplary", points: 4.0, description: "Complete mastery." },
                          { id: `t_${Date.now()}_2`, level_name: "Proficient", points: 3.0, description: "Solid comprehension." },
                          { id: `t_${Date.now()}_3`, level_name: "Developing", points: 2.0, description: "Partial understanding." },
                          { id: `t_${Date.now()}_4`, level_name: "Unsatisfactory", points: 0.0, description: "Missing implementation." },
                        ],
                      };
                      setCriteria([...criteria, newCrit]);
                    }}
                  >
                    <Plus className="mr-1 size-3.5" /> Add Criterion
                  </Button>
                </div>
              </div>

              {/* Hidden file input for AI Rubric Parser */}
              <input
                type="file"
                ref={rubricFileInputRef}
                onChange={handleRubricFileParse}
                className="hidden"
                accept=".pdf,.docx,.xlsx,.xls,.txt,.csv,.md,.png,.jpg"
              />

              {isParsingRubric && (
                <div className="p-4 rounded-xl bg-amber-soft/30 border border-amber/40 flex items-center gap-3 animate-pulse">
                  <Loader2 className="size-5 text-amber-ink animate-spin" />
                  <span className="text-xs text-ink font-medium">Gemini is parsing rubric document into structured matrix criteria with descending points...</span>
                </div>
              )}

              {/* BUILDER VIEW */}
              {rubricMode === "builder" && (
                <div className="space-y-4">
                  {criteria.map((crit, cIdx) => (
                    <div
                      key={crit.id}
                      className="rounded-2xl border border-line bg-card p-4 shadow-sm space-y-3"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex-1 grid grid-cols-1 md:grid-cols-4 gap-3">
                          <div className="md:col-span-3">
                            <label className="text-[11px] font-bold uppercase tracking-wider text-faint">
                              Criterion {cIdx + 1} Title
                            </label>
                            <Input
                              value={crit.criterion_name}
                              onChange={(e) => {
                                const next = [...criteria];
                                next[cIdx].criterion_name = e.target.value;
                                setCriteria(next);
                              }}
                              className="mt-1 h-8 text-xs font-semibold"
                            />
                          </div>
                          <div>
                            <label className="text-[11px] font-bold uppercase tracking-wider text-faint">
                              Weight (%)
                            </label>
                            <Input
                              type="number"
                              value={crit.weight}
                              onChange={(e) => {
                                const next = [...criteria];
                                next[cIdx].weight = Number(e.target.value) || 0;
                                setCriteria(next);
                              }}
                              className="mt-1 h-8 text-xs font-mono font-medium"
                            />
                          </div>
                        </div>

                        <div className="flex items-center gap-1">
                          <button
                            type="button"
                            title="Duplicate Criterion"
                            onClick={() => {
                              const duplicated: WizardCriterion = {
                                ...crit,
                                id: `crit_${Date.now()}`,
                                criterion_name: `${crit.criterion_name} (Copy)`,
                                levels: crit.levels.map((l) => ({ ...l, id: `tier_${Date.now()}_${Math.random()}` })),
                              };
                              const next = [...criteria];
                              next.splice(cIdx + 1, 0, duplicated);
                              setCriteria(next);
                            }}
                            className="p-1.5 text-faint hover:text-ink rounded-lg hover:bg-tint"
                          >
                            <Copy className="size-3.5" />
                          </button>
                          {criteria.length > 1 && (
                            <button
                              type="button"
                              title="Delete Criterion"
                              onClick={() => {
                                setCriteria(criteria.filter((_, idx) => idx !== cIdx));
                              }}
                              className="p-1.5 text-faint hover:text-amber-ink rounded-lg hover:bg-amber-soft/40"
                            >
                              <Trash2 className="size-3.5" />
                            </button>
                          )}
                        </div>
                      </div>

                      {/* Criterion description */}
                      <Input
                        value={crit.description}
                        onChange={(e) => {
                          const next = [...criteria];
                          next[cIdx].description = e.target.value;
                          setCriteria(next);
                        }}
                        placeholder="Criterion evaluation guidance..."
                        className="h-8 text-xs text-faint"
                      />

                      {/* Descending Tiers Grid */}
                      <div className="grid grid-cols-1 md:grid-cols-4 gap-2 pt-2 border-t border-line/60">
                        {crit.levels.map((lvl, lIdx) => {
                          const isDescendingInvalid =
                            lIdx > 0 && lvl.points > crit.levels[lIdx - 1].points;
                          return (
                            <div
                              key={lvl.id}
                              className={`p-2.5 rounded-xl border text-xs space-y-1.5 ${
                                isDescendingInvalid
                                  ? "bg-amber-soft/30 border-amber/60"
                                  : "bg-tint/30 border-line"
                              }`}
                            >
                              <div className="flex items-center justify-between">
                                <input
                                  value={lvl.level_name}
                                  onChange={(e) => {
                                    const next = [...criteria];
                                    next[cIdx].levels[lIdx].level_name = e.target.value;
                                    setCriteria(next);
                                  }}
                                  className="w-20 font-bold bg-transparent focus:outline-none text-ink text-xs"
                                />
                                <div className="flex items-center gap-1 font-mono">
                                  <input
                                    type="number"
                                    step="0.5"
                                    value={lvl.points}
                                    onChange={(e) => {
                                      const next = [...criteria];
                                      next[cIdx].levels[lIdx].points = Number(e.target.value) || 0;
                                      setCriteria(next);
                                    }}
                                    className="w-12 text-right bg-card px-1 py-0.5 rounded border border-line text-xs font-bold"
                                  />
                                  <span className="text-[10px] text-faint">pts</span>
                                </div>
                              </div>
                              <textarea
                                value={lvl.description}
                                onChange={(e) => {
                                  const next = [...criteria];
                                  next[cIdx].levels[lIdx].description = e.target.value;
                                  setCriteria(next);
                                }}
                                rows={2}
                                placeholder="Tier expectations..."
                                className="w-full bg-card p-1.5 rounded border border-line/60 text-[11px] text-ink/80 focus:outline-none"
                              />
                              {isDescendingInvalid && (
                                <p className="text-[10px] text-amber-ink flex items-center gap-1">
                                  <AlertCircle className="size-3 shrink-0" /> Must descend (&le; {crit.levels[lIdx - 1].points})
                                </p>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* READ-ONLY STUDENT PREVIEW */}
              {rubricMode === "preview" && (
                <div className="rounded-2xl border border-line bg-card p-5 space-y-6">
                  <div className="flex items-center justify-between pb-3 border-b border-line">
                    <div>
                      <h3 className="text-sm font-bold text-ink">Student View Preview</h3>
                      <p className="text-xs text-faint">This is the read-only grading matrix visible to students.</p>
                    </div>
                    <Badge variant="outline" className="font-mono text-xs">
                      Total: {maxScore} pts
                    </Badge>
                  </div>

                  <div className="space-y-4">
                    {criteria.map((c, i) => (
                      <div key={c.id} className="border border-line rounded-xl p-4 bg-tint/20 space-y-3">
                        <div className="flex items-center justify-between">
                          <h4 className="text-xs font-bold text-ink">
                            {i + 1}. {c.criterion_name}
                          </h4>
                          <span className="text-xs font-mono text-faint font-medium">Weight: {c.weight}%</span>
                        </div>
                        <p className="text-xs text-faint">{c.description}</p>
                        <div className="grid grid-cols-1 md:grid-cols-4 gap-2 pt-2">
                          {c.levels.map((lvl) => (
                            <div key={lvl.id} className="p-2.5 rounded-lg bg-card border border-line text-xs space-y-1">
                              <div className="flex items-center justify-between font-semibold">
                                <span className="text-ink">{lvl.level_name}</span>
                                <span className="text-faint font-mono">{lvl.points} pts</span>
                              </div>
                              <p className="text-[11px] text-faint leading-relaxed">{lvl.description}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* STEP 4: SUBMISSIONS DROP & MATCHING TABLE */}
          {currentStep === 4 && (
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-tint/40 border border-line flex items-start gap-3">
                <FileCheck className="size-5 text-teal-ink shrink-0 mt-0.5" />
                <div className="text-xs text-ink/80 space-y-1">
                  <p className="font-semibold text-ink">Universal Submissions Drop & Roll Call Match</p>
                  <p>
                    Drag-and-drop multiple files of any format or a bulk ZIP archive. Filenames are automatically
                    matched against student roll numbers and enrolled course roster records.
                  </p>
                </div>
              </div>

              {/* Submissions Drop Zone */}
              <div
                onClick={() => submissionFileInputRef.current?.click()}
                className="border-2 border-dashed border-line rounded-2xl p-6 text-center hover:border-ink/40 hover:bg-tint/20 transition-all cursor-pointer group"
              >
                <input
                  type="file"
                  multiple
                  ref={submissionFileInputRef}
                  onChange={handleSubmissionsBatchUpload}
                  className="hidden"
                  accept="*/*"
                />
                <div className="flex flex-col items-center gap-2">
                  <div className="size-12 rounded-2xl bg-tint flex items-center justify-center text-faint group-hover:text-ink transition-colors">
                    {isUploadingSubmissions ? <Loader2 className="size-6 animate-spin" /> : <Upload className="size-6" />}
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-ink">
                      {isUploadingSubmissions ? "Parsing submissions & matching roll numbers..." : "Click or drop student submissions here"}
                    </p>
                    <p className="text-xs text-faint mt-0.5">
                      Accepts multiple files (.pdf, .py, .java, .docx, .txt) or a single .zip archive
                    </p>
                  </div>
                </div>
              </div>

              {/* Roll Number Matching Table */}
              {(matchedFiles.length > 0 || unmatchedFiles.length > 0 || duplicateFiles.length > 0) && (
                <div className="rounded-2xl border border-line bg-card overflow-hidden shadow-sm">
                  <div className="p-3 border-b border-line bg-tint/30 flex items-center justify-between">
                    <span className="text-xs font-bold text-ink flex items-center gap-2">
                      <Users className="size-3.5" /> Roll Call Matching Results
                    </span>
                    <div className="flex items-center gap-2">
                      <Badge className="bg-teal-soft text-teal-ink border-teal/40 text-[10px]">
                        {matchedFiles.length} Matched
                      </Badge>
                      {unmatchedFiles.length > 0 && (
                        <Badge className="bg-amber-soft text-amber-ink border-amber/40 text-[10px]">
                          {unmatchedFiles.length} Unmatched
                        </Badge>
                      )}
                      {duplicateFiles.length > 0 && (
                        <Badge className="bg-purple-soft text-purple-ink border-purple/40 text-[10px]">
                          {duplicateFiles.length} Duplicates
                        </Badge>
                      )}
                    </div>
                  </div>

                  <div className="overflow-x-auto max-h-60">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-tint/20 border-b border-line text-faint font-semibold uppercase text-[10px]">
                        <tr>
                          <th className="p-2.5 pl-4">Filename</th>
                          <th className="p-2.5">File Size</th>
                          <th className="p-2.5">Detected Student</th>
                          <th className="p-2.5">Roll Number</th>
                          <th className="p-2.5">Match Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-line/60">
                        {/* Matched Files */}
                        {matchedFiles.map((m, idx) => (
                          <tr key={`m_${idx}`} className="hover:bg-tint/20">
                            <td className="p-2.5 pl-4 font-mono font-medium text-ink">{m.filename}</td>
                            <td className="p-2.5 text-faint">{Math.round(m.file_size / 1024)} KB</td>
                            <td className="p-2.5 font-semibold text-ink">{m.student_name}</td>
                            <td className="p-2.5 font-mono text-faint">{m.student_roll}</td>
                            <td className="p-2.5">
                              <Badge className="bg-teal-soft text-teal-ink border-teal/40 text-[10px] font-mono">
                                Matched ({Math.round((m.confidence || 0.95) * 100)}%)
                              </Badge>
                            </td>
                          </tr>
                        ))}

                        {/* Unmatched Files with Manual Fix Dropdown */}
                        {unmatchedFiles.map((u, idx) => (
                          <tr key={`u_${idx}`} className="bg-amber-soft/10 hover:bg-amber-soft/20">
                            <td className="p-2.5 pl-4 font-mono text-ink">{u.filename}</td>
                            <td className="p-2.5 text-faint">{Math.round(u.file_size / 1024)} KB</td>
                            <td className="p-2.5" colSpan={2}>
                              <select
                                className="w-full h-7 rounded border border-line bg-card px-2 text-xs text-ink focus:outline-none"
                                onChange={(e) => {
                                  const selectedId = e.target.value;
                                  const st = courseRoster.find((s) => s.id === selectedId);
                                  if (st) {
                                    setMatchedFiles([
                                      ...matchedFiles,
                                      {
                                        filename: u.filename,
                                        file_size: u.file_size,
                                        student_id: st.id,
                                        student_name: st.name,
                                        student_roll: st.roll,
                                        confidence: 1.0,
                                      },
                                    ]);
                                    setUnmatchedFiles(unmatchedFiles.filter((_, i) => i !== idx));
                                    showToast(`Assigned ${u.filename} to ${st.name}`);
                                  }
                                }}
                              >
                                <option value="">Manual Fix: Select student from roster...</option>
                                {courseRoster.map((s) => (
                                  <option key={s.id} value={s.id}>
                                    {s.name} ({s.roll})
                                  </option>
                                ))}
                              </select>
                            </td>
                            <td className="p-2.5">
                              <Badge className="bg-amber-soft text-amber-ink border-amber/40 text-[10px]">
                                Unmatched
                              </Badge>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Modal Footer Controls */}
        <div className="border-t border-line p-4 px-6 flex items-center justify-between bg-tint/20 rounded-b-[20px]">
          <div>
            {currentStep > 1 && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentStep(currentStep - 1)}
                className="text-xs h-9"
              >
                <ChevronLeft className="mr-1 size-3.5" /> Back
              </Button>
            )}
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleFinalize(false)}
              disabled={isSavingDraft}
              className="text-xs h-9"
            >
              <Save className="mr-1.5 size-3.5" /> Save Draft
            </Button>

            {currentStep < 4 ? (
              <Button
                size="sm"
                onClick={() => {
                  if (currentStep === 1 && !title.trim()) {
                    showToast("Please enter an assignment title.");
                    return;
                  }
                  if (currentStep === 3) {
                    const validation = validateDescendingTiers();
                    if (!validation.valid) {
                      showToast(validation.error || "Please fix rubric tier points.");
                      return;
                    }
                  }
                  setCurrentStep(currentStep + 1);
                }}
                className="text-xs h-9 bg-ink text-card hover:bg-ink/90 font-medium"
              >
                Next <ChevronRight className="ml-1 size-3.5" />
              </Button>
            ) : (
              <Button
                size="sm"
                onClick={() => handleFinalize(true)}
                disabled={isSavingDraft}
                className="text-xs h-9 bg-teal-ink text-card hover:bg-teal-ink/90 font-medium"
              >
                <CheckCircle2 className="mr-1.5 size-3.5" /> Finalize & Publish
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

