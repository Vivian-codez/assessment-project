import React, { useState, useEffect, useRef } from "react";
import {
  Users,
  UserPlus,
  Upload,
  FileSpreadsheet,
  Trash2,
  Plus,
  Search,
  CheckCircle2,
  AlertCircle,
  FileText,
  Download,
  Loader2,
  RefreshCw,
  X,
  Sparkles,
} from "lucide-react";
import Papa from "papaparse";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { api, type Classroom, type Student } from "@/lib/api";

interface RosterViewProps {
  classroom: Classroom | null;
  classrooms: Classroom[];
  onSelectClassroom: (id: string) => void;
  showToast: (msg: string) => void;
}

interface ManualRow {
  id: string;
  roll_number: string;
  full_name: string;
  email: string;
}

export function RosterView({
  classroom,
  classrooms,
  onSelectClassroom,
  showToast,
}: RosterViewProps) {
  const [students, setStudents] = useState<Student[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [sortField, setSortField] = useState<"roll_number" | "full_name">("roll_number");
  const [sortAsc, setSortAsc] = useState(true);

  // Manual modal state
  const [manualModalOpen, setManualModalOpen] = useState(false);
  const [manualRows, setManualRows] = useState<ManualRow[]>([
    { id: "1", roll_number: "", full_name: "", email: "" },
    { id: "2", roll_number: "", full_name: "", email: "" },
    { id: "3", roll_number: "", full_name: "", email: "" },
  ]);
  const [manualSaving, setManualSaving] = useState(false);

  // Multi-format upload modal & preview state
  const [csvModalOpen, setCsvModalOpen] = useState(false);
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [csvPreviewRows, setCsvPreviewRows] = useState<
    Array<{
      roll_number: string;
      full_name: string;
      email: string;
      valid: boolean;
      reason?: string;
    }>
  >([]);
  const [csvUploading, setCsvUploading] = useState(false);
  const [aiParsing, setAiParsing] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Student deletion state
  const [deletingStudent, setDeletingStudent] = useState<Student | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  useEffect(() => {
    if (classroom?.id) {
      loadStudents(classroom.id);
    } else {
      setStudents([]);
    }
  }, [classroom?.id]);

  const loadStudents = async (classroomId: string) => {
    setLoading(true);
    try {
      const data = await api.classrooms.getStudents(classroomId);
      setStudents(data || []);
    } catch (err: any) {
      console.warn("Failed to load students:", err);
      showToast(`Error loading roster: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmDeleteStudent = async () => {
    if (!deletingStudent || !classroom?.id) return;
    const studentToDelete = deletingStudent;
    setDeleteLoading(true);
    // Optimistic UI update
    setStudents((prev) => prev.filter((s) => s.id !== studentToDelete.id));
    setDeletingStudent(null);
    try {
      await api.classrooms.deleteStudent(classroom.id, studentToDelete.id);
      showToast(`Student ${studentToDelete.full_name} (${studentToDelete.roll_number}) deleted.`);
    } catch (err: any) {
      showToast(`Failed to delete student: ${err.message}`);
      await loadStudents(classroom.id);
    } finally {
      setDeleteLoading(false);
    }
  };

  // Manual input handlers
  const handleAddManualRow = () => {
    setManualRows((prev) => [
      ...prev,
      { id: Date.now().toString(), roll_number: "", full_name: "", email: "" },
    ]);
  };

  const handleRemoveManualRow = (id: string) => {
    if (manualRows.length === 1) return;
    setManualRows((prev) => prev.filter((r) => r.id !== id));
  };

  const handleUpdateManualRow = (id: string, field: keyof ManualRow, value: string) => {
    setManualRows((prev) => prev.map((r) => (r.id === id ? { ...r, [field]: value } : r)));
  };

  const handleSaveManualEnrollment = async () => {
    if (!classroom?.id) {
      showToast("Please select a classroom first.");
      return;
    }

    const valid = manualRows.filter((r) => r.roll_number.trim() && r.full_name.trim());
    if (valid.length === 0) {
      showToast("Please enter at least one student with a Roll Number and Full Name.");
      return;
    }

    setManualSaving(true);
    try {
      const res = await api.classrooms.enrollManual(
        classroom.id,
        valid.map((r) => ({
          roll_number: r.roll_number.trim(),
          full_name: r.full_name.trim(),
          email: r.email.trim() || undefined,
        })),
      );
      showToast(`Successfully enrolled ${res.total_inserted || valid.length} student(s)!`);
      setManualModalOpen(false);
      setManualRows([
        { id: "1", roll_number: "", full_name: "", email: "" },
        { id: "2", roll_number: "", full_name: "", email: "" },
      ]);
      await loadStudents(classroom.id);
    } catch (err: any) {
      showToast(`Enrollment failed: ${err.message}`);
    } finally {
      setManualSaving(false);
    }
  };

  // Multi-format roster parsing & upload
  const processRosterFile = async (file: File) => {
    setCsvFile(file);
    if (!classroom?.id) {
      showToast("Please select a course/classroom first.");
      return;
    }

    setAiParsing(true);
    try {
      // Use backend multi-format extraction endpoint
      const result = await api.classrooms.parseRoster(classroom.id, file);
      const seenInFile = new Set<string>();
      const preview = (result.students || []).map((s) => {
        const roll = (s.roll_number || "").trim();
        const name = (s.full_name || "").trim();
        const email = (s.email || "").trim();
        if (!roll || !name) {
          return {
            roll_number: roll,
            full_name: name,
            email,
            valid: false,
            reason: "Missing Roll No or Name",
          };
        }
        if (seenInFile.has(roll.toLowerCase())) {
          return {
            roll_number: roll,
            full_name: name,
            email,
            valid: false,
            reason: "Duplicate roll # in file",
          };
        }
        seenInFile.add(roll.toLowerCase());
        return { roll_number: roll, full_name: name, email, valid: true };
      });
      setCsvPreviewRows(preview);
      showToast(
        `AI Parser detected ${preview.filter((p) => p.valid).length} student record(s) from ${file.name}`,
      );
    } catch (err: any) {
      // Fallback for CSV if backend endpoint had network issue
      if (file.name.toLowerCase().endsWith(".csv")) {
        Papa.parse(file, {
          header: true,
          skipEmptyLines: true,
          complete: (results) => {
            const parsedRows = results.data as Record<string, string>[];
            const preview: Array<{
              roll_number: string;
              full_name: string;
              email: string;
              valid: boolean;
              reason?: string;
            }> = [];
            const seenInFile = new Set<string>();
            parsedRows.forEach((row) => {
              let roll = "";
              let name = "";
              let email = "";
              for (const [k, v] of Object.entries(row)) {
                const cleanKey = k.toLowerCase().replace(/[^a-z]/g, "");
                const val = (v || "").trim();
                if (["rollnumber", "rollno", "roll", "studentroll", "id"].includes(cleanKey))
                  roll = val;
                else if (["name", "fullname", "studentname", "names"].includes(cleanKey))
                  name = val;
                else if (["email", "emailaddress", "studentemail", "mail"].includes(cleanKey))
                  email = val;
              }
              if (!roll || !name) {
                preview.push({
                  roll_number: roll,
                  full_name: name,
                  email,
                  valid: false,
                  reason: "Missing Roll No or Name",
                });
              } else if (seenInFile.has(roll.toLowerCase())) {
                preview.push({
                  roll_number: roll,
                  full_name: name,
                  email,
                  valid: false,
                  reason: "Duplicate roll # in file",
                });
              } else {
                seenInFile.add(roll.toLowerCase());
                preview.push({ roll_number: roll, full_name: name, email, valid: true });
              }
            });
            setCsvPreviewRows(preview);
          },
          error: (pErr) => showToast(`Failed to parse file: ${pErr.message}`),
        });
      } else {
        showToast(`AI extraction notice: ${err.message}. Please verify file.`);
      }
    } finally {
      setAiParsing(false);
    }
  };

  const handleConfirmCSVUpload = async () => {
    if (!classroom?.id) return;
    const validRows = csvPreviewRows.filter(
      (r) => r.valid && r.roll_number.trim() && r.full_name.trim(),
    );
    if (validRows.length === 0) {
      showToast("No valid student records to enroll.");
      return;
    }

    setCsvUploading(true);
    try {
      const res = await api.classrooms.enrollManual(
        classroom.id,
        validRows.map((r) => ({
          roll_number: r.roll_number.trim(),
          full_name: r.full_name.trim(),
          email: r.email.trim() || undefined,
        })),
      );
      showToast(
        `Roster enrollment complete! Enrolled ${res.total_inserted || validRows.length} student(s) into ${classroom.code}.`,
      );
      setCsvModalOpen(false);
      setCsvFile(null);
      setCsvPreviewRows([]);
      await loadStudents(classroom.id);
    } catch (err: any) {
      showToast(`Enrollment failed: ${err.message}`);
    } finally {
      setCsvUploading(false);
    }
  };

  // Handler generating and downloading a CSV export of currently enrolled students
  const handleExportCSV = () => {
    // Check if classroom roster is currently empty
    if (students.length === 0) {
      // Notify educator that there are no students to export
      showToast("No students to export.");
      // Terminate export execution
      return;
    }
    // Construct CSV file content with standard roll call column headers
    const csvContent =
      "Roll Number,Full Name,Email,Enrollment Date\n" +
      students
        .map(
          (s) => `"${s.roll_number}","${s.full_name}","${s.email || ""}","${s.created_at || ""}"`,
        )
        .join("\n");
    // Instantiate in-memory Blob containing UTF-8 CSV text
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    // Generate object URL for file download
    const url = URL.createObjectURL(blob);
    // Create temporary anchor link element
    const link = document.createElement("a");
    // Assign object URL reference
    link.setAttribute("href", url);
    // Designate target file download name
    link.setAttribute("download", `${classroom?.code || "classroom"}_roster.csv`);
    // Append anchor to document DOM tree
    document.body.appendChild(link);
    // Trigger download click programmatically
    link.click();
    // Remove temporary anchor element
    document.body.removeChild(link);
  };

  // Handler generating and downloading a valid sample CSV roster template
  const handleDownloadSampleTemplate = () => {
    // Define sample roster template with standard headers and example records
    const sampleCsv =
      "Roll Number,Full Name,Email\n" +
      "CS2026-001,Ada Lovelace,ada@university.edu\n" +
      "CS2026-002,Alan Turing,alan@university.edu\n" +
      "CS2026-003,Grace Hopper,grace@university.edu\n";
    // Instantiate in-memory Blob containing UTF-8 encoded sample template
    const blob = new Blob([sampleCsv], { type: "text/csv;charset=utf-8;" });
    // Generate temporary object URL reference
    const url = URL.createObjectURL(blob);
    // Create temporary anchor element
    const link = document.createElement("a");
    // Assign object URL to anchor href
    link.setAttribute("href", url);
    // Set default file name for downloaded sample template
    link.setAttribute("download", "sample_roster_template.csv");
    // Append anchor to DOM
    document.body.appendChild(link);
    // Trigger browser file download
    link.click();
    // Remove anchor element from DOM
    document.body.removeChild(link);
    // Inform educator via toast notification
    showToast("Downloaded sample roster CSV template.");
  };

  // Filter and sort students
  const filteredStudents = students
    .filter(
      (s) =>
        s.roll_number.toLowerCase().includes(search.toLowerCase()) ||
        s.full_name.toLowerCase().includes(search.toLowerCase()) ||
        (s.email && s.email.toLowerCase().includes(search.toLowerCase())),
    )
    .sort((a, b) => {
      const fieldA = a[sortField] || "";
      const fieldB = b[sortField] || "";
      const cmp = fieldA.localeCompare(fieldB, undefined, { numeric: true });
      return sortAsc ? cmp : -cmp;
    });

  return (
    <div className="space-y-6 animate-fade-up">
      {/* Top Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">
            Classroom Roster & Roll Call
          </p>
          <h1 className="font-display text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
            {classroom ? `${classroom.name} (${classroom.code})` : "Student Roll Call"}
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Enrolled student registry synced directly with Database.
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex flex-wrap items-center gap-2">
          {classrooms.length > 0 && (
            <select
              value={classroom?.id || ""}
              onChange={(e) => onSelectClassroom(e.target.value)}
              className="rounded-lg border border-line bg-card px-3 py-2 text-xs font-medium text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            >
              {classrooms.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.code} — {c.name}
                </option>
              ))}
            </select>
          )}

          <Button
            variant="outline"
            size="sm"
            onClick={handleExportCSV}
            disabled={students.length === 0}
            className="text-xs"
          >
            <Download className="mr-1.5 size-3.5" /> Export CSV
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={() => setCsvModalOpen(true)}
            disabled={!classroom}
            className="text-xs"
          >
            <Upload className="mr-1.5 size-3.5 text-amber-ink" /> Import Roster (Any Format)
          </Button>

          <Button
            size="sm"
            onClick={() => setManualModalOpen(true)}
            disabled={!classroom}
            className="bg-primary text-primary-foreground text-xs hover:bg-primary/90"
          >
            <UserPlus className="mr-1.5 size-3.5" /> Manual Enrollment
          </Button>
        </div>
      </div>

      {/* Roster Overview Bar */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-line bg-card p-4">
          <p className="text-xs text-muted-foreground">Total Enrolled</p>
          <div className="mt-1 flex items-baseline gap-2">
            <span className="font-display text-3xl font-semibold text-foreground">
              {students.length}
            </span>
            <span className="text-xs text-muted-foreground">students</span>
          </div>
        </div>

        <div className="rounded-xl border border-line bg-card p-4">
          <p className="text-xs text-muted-foreground">Roster Status</p>
          <div className="mt-1 flex items-center gap-1.5">
            <span className="size-2 rounded-full bg-emerald-500" />
            <span className="text-sm font-medium text-foreground">Live & Enrolled</span>
          </div>
        </div>

        <div className="rounded-xl border border-line bg-card p-4">
          <p className="text-xs text-muted-foreground">Class Code</p>
          <p className="mt-1 font-mono text-lg font-semibold text-foreground">
            {classroom?.code || "—"}
          </p>
        </div>
      </div>

      {/* Student List & Search */}
      <div className="rounded-xl border border-line bg-card">
        {/* Table toolbar */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line p-4">
          <div className="relative w-full max-w-xs">
            <Search className="absolute top-2.5 left-3 size-4 text-muted-foreground" />
            <Input
              type="text"
              placeholder="Search by Roll No, Name or Email..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9 text-xs"
            />
          </div>

          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span>Sort by:</span>
            <button
              onClick={() => {
                if (sortField === "roll_number") setSortAsc(!sortAsc);
                else {
                  setSortField("roll_number");
                  setSortAsc(true);
                }
              }}
              className={`rounded px-2 py-1 font-medium ${
                sortField === "roll_number" ? "bg-muted text-foreground" : "hover:text-foreground"
              }`}
            >
              Roll Number {sortField === "roll_number" && (sortAsc ? "↑" : "↓")}
            </button>
            <button
              onClick={() => {
                if (sortField === "full_name") setSortAsc(!sortAsc);
                else {
                  setSortField("full_name");
                  setSortAsc(true);
                }
              }}
              className={`rounded px-2 py-1 font-medium ${
                sortField === "full_name" ? "bg-muted text-foreground" : "hover:text-foreground"
              }`}
            >
              Name {sortField === "full_name" && (sortAsc ? "↑" : "↓")}
            </button>
          </div>
        </div>

        {/* Table Body */}
        {loading ? (
          <div className="flex items-center justify-center p-12 text-muted-foreground">
            <Loader2 className="mr-2 size-5 animate-spin" />
            <span className="text-sm">Fetching student roster from database...</span>
          </div>
        ) : filteredStudents.length === 0 ? (
          <div className="p-12 text-center">
            <div className="mx-auto mb-3 grid size-12 place-items-center rounded-full bg-muted text-muted-foreground">
              <Users className="size-6" />
            </div>
            <h3 className="font-display text-lg font-medium text-foreground">
              No students enrolled yet
            </h3>
            <p className="mx-auto mt-1 max-w-sm text-xs text-muted-foreground">
              Enroll students manually or upload a class CSV roster to track submissions and
              auto-grade.
            </p>
            <div className="mt-4 flex justify-center gap-2">
              <Button size="sm" onClick={() => setManualModalOpen(true)} className="text-xs">
                <UserPlus className="mr-1.5 size-3.5" /> Add Students Manually
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => setCsvModalOpen(true)}
                className="text-xs"
              >
                <Upload className="mr-1.5 size-3.5 text-amber-ink" /> Import Roster (Any Format)
              </Button>
            </div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-line bg-muted/40 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  <th className="px-4 py-3">Roll Number</th>
                  <th className="px-4 py-3">Full Name</th>
                  <th className="px-4 py-3">Email Address</th>
                  <th className="px-4 py-3">Enrolled Status</th>
                  <th className="px-4 py-3">Added On</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {filteredStudents.map((student) => (
                  <tr key={student.id} className="transition-colors hover:bg-muted/20">
                    <td className="px-4 py-3 font-mono font-medium text-foreground">
                      {student.roll_number}
                    </td>
                    <td className="px-4 py-3 font-medium text-foreground">{student.full_name}</td>
                    <td className="px-4 py-3 text-muted-foreground">{student.email || "—"}</td>
                    <td className="px-4 py-3">
                      <span className="inline-flex items-center gap-1 rounded-md bg-emerald-50 px-2 py-0.5 text-[11px] font-medium text-emerald-700">
                        <CheckCircle2 className="size-3" /> Enrolled
                      </span>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {student.created_at
                        ? new Date(student.created_at).toLocaleDateString()
                        : "Active"}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        type="button"
                        onClick={() => setDeletingStudent(student)}
                        title={`Delete ${student.full_name}`}
                        className="rounded p-1 text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive focus:outline-none"
                      >
                        <Trash2 className="size-3.5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ========================================================================= */}
      {/* Modal: Manual Student Enrollment Form                                    */}
      {/* ========================================================================= */}
      {manualModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="w-full max-w-2xl rounded-2xl border border-line bg-card p-6 shadow-2xl animate-fade-up">
            <div className="flex items-center justify-between border-b border-line pb-4">
              <div>
                <h2 className="font-display text-xl font-semibold text-foreground">
                  Manual Student Enrollment
                </h2>
                <p className="text-xs text-muted-foreground">
                  Add student roll numbers and names for {classroom?.name || "this classroom"}.
                </p>
              </div>
              <Button variant="ghost" size="icon" onClick={() => setManualModalOpen(false)}>
                <X className="size-4" />
              </Button>
            </div>

            <div className="mt-4 max-h-[50vh] overflow-y-auto space-y-3 pr-1">
              <div className="grid grid-cols-12 gap-2 text-[11px] font-semibold uppercase text-muted-foreground">
                <div className="col-span-3">Roll Number *</div>
                <div className="col-span-4">Full Name *</div>
                <div className="col-span-4">Email (Optional)</div>
                <div className="col-span-1 text-center">Del</div>
              </div>

              {manualRows.map((row, idx) => (
                <div key={row.id} className="grid grid-cols-12 items-center gap-2">
                  <div className="col-span-3">
                    <Input
                      placeholder={`e.g. CS2024-0${idx + 1}`}
                      value={row.roll_number}
                      onChange={(e) => handleUpdateManualRow(row.id, "roll_number", e.target.value)}
                      className="text-xs"
                    />
                  </div>
                  <div className="col-span-4">
                    <Input
                      placeholder="Student full name"
                      value={row.full_name}
                      onChange={(e) => handleUpdateManualRow(row.id, "full_name", e.target.value)}
                      className="text-xs"
                    />
                  </div>
                  <div className="col-span-4">
                    <Input
                      type="email"
                      placeholder="student@univ.edu"
                      value={row.email}
                      onChange={(e) => handleUpdateManualRow(row.id, "email", e.target.value)}
                      className="text-xs"
                    />
                  </div>
                  <div className="col-span-1 flex justify-center">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleRemoveManualRow(row.id)}
                      className="size-8 text-muted-foreground hover:text-destructive"
                      disabled={manualRows.length === 1}
                    >
                      <Trash2 className="size-3.5" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-4 flex items-center justify-between border-t border-line pt-4">
              <Button variant="outline" size="sm" onClick={handleAddManualRow} className="text-xs">
                <Plus className="mr-1.5 size-3.5" /> Add Another Row
              </Button>

              <div className="flex gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setManualModalOpen(false)}
                  className="text-xs"
                >
                  Cancel
                </Button>
                <Button
                  size="sm"
                  onClick={handleSaveManualEnrollment}
                  disabled={manualSaving}
                  className="text-xs bg-primary text-primary-foreground"
                >
                  {manualSaving ? (
                    <>
                      <Loader2 className="mr-1.5 size-3.5 animate-spin" /> Enrolling...
                    </>
                  ) : (
                    "Save & Enroll Students"
                  )}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* Modal: Multi-Format Roster Upload with AI Parser & Confirmation Table     */}
      {/* ========================================================================= */}
      {csvModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="w-full max-w-2xl rounded-2xl border border-line bg-card p-6 shadow-2xl animate-fade-up max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-line pb-4">
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="font-display text-xl font-semibold text-foreground">
                    Multi-Format Roll Call Ingestion
                  </h2>
                  <Badge variant="secondary" className="gap-1 bg-amber-soft text-amber-ink border-amber/30 text-[10px]">
                    <Sparkles className="size-3" />
                    AI-Powered
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Accepts any format: .csv, .tsv, .xlsx, .xls, .pdf, .docx, .txt, .zip, or image scans.
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleDownloadSampleTemplate}
                  className="h-8 text-xs gap-1.5"
                  title="Download pre-formatted CSV roster template"
                >
                  <Download className="size-3.5" />
                  Sample CSV
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => {
                    setCsvModalOpen(false);
                    setCsvFile(null);
                    setCsvPreviewRows([]);
                  }}
                >
                  <X className="size-4" />
                </Button>
              </div>
            </div>

            {/* Dropzone */}
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setIsDragOver(true);
              }}
              onDragLeave={() => setIsDragOver(false)}
              onDrop={(e) => {
                e.preventDefault();
                setIsDragOver(false);
                if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                  processRosterFile(e.dataTransfer.files[0]);
                }
              }}
              onClick={() => fileInputRef.current?.click()}
              className={`mt-4 cursor-pointer rounded-xl border-2 border-dashed p-6 text-center transition-all ${
                isDragOver
                  ? "border-primary bg-primary/5"
                  : "border-line hover:border-primary/50 hover:bg-muted/20"
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv,.tsv,.xlsx,.xls,.pdf,.docx,.doc,.txt,.zip,.png,.jpg,.jpeg,.webp,image/*"
                className="hidden"
                onChange={(e) => {
                  if (e.target.files && e.target.files[0]) {
                    processRosterFile(e.target.files[0]);
                  }
                }}
              />
              <div className="mx-auto mb-2 grid size-10 place-items-center rounded-full bg-primary/10 text-primary">
                {aiParsing ? (
                  <Loader2 className="size-5 animate-spin text-amber-ink" />
                ) : (
                  <Upload className="size-5" />
                )}
              </div>
              <p className="text-sm font-medium text-foreground">
                {csvFile
                  ? csvFile.name
                  : "Click to select or drag and drop any roster file (PDF, Excel, Word, CSV, Image)"}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                AI extracts Roll Numbers, Full Names, and Emails automatically.
              </p>
            </div>

            {/* AI Parsing Progress Banner */}
            {aiParsing && (
              <div className="mt-4 flex items-center gap-2.5 rounded-xl border border-amber/40 bg-amber-soft/50 p-3 text-xs text-amber-ink animate-pulse">
                <Sparkles className="size-4 animate-spin text-amber-ink shrink-0" />
                <span>
                  <strong>AI Roster Parser Actively Extracting Records...</strong> Analyzing document
                  layout and extracting student entries.
                </span>
              </div>
            )}

            {/* Live Preview & Confirmation Table */}
            {csvPreviewRows.length > 0 && !aiParsing && (
              <div className="mt-4">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Extracted Roster Preview ({csvPreviewRows.filter((r) => r.valid).length} valid rows)
                  </p>
                  {csvPreviewRows.some((r) => !r.valid) && (
                    <span className="text-[11px] text-amber-600 font-medium">
                      {csvPreviewRows.filter((r) => !r.valid).length} flagged
                    </span>
                  )}
                </div>

                <div className="max-h-56 overflow-y-auto rounded-lg border border-line">
                  <table className="w-full text-left text-xs">
                    <thead className="sticky top-0 bg-muted text-[10px] uppercase font-semibold text-muted-foreground">
                      <tr>
                        <th className="px-3 py-2">Roll No</th>
                        <th className="px-3 py-2">Full Name</th>
                        <th className="px-3 py-2">Email</th>
                        <th className="px-3 py-2">Status</th>
                        <th className="px-2 py-2 text-right">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-line">
                      {csvPreviewRows.map((row, idx) => (
                        <tr
                          key={idx}
                          className={row.valid ? "" : "bg-destructive/5 text-muted-foreground"}
                        >
                          <td className="px-3 py-1.5">
                            <input
                              type="text"
                              value={row.roll_number}
                              onChange={(e) => {
                                const val = e.target.value;
                                setCsvPreviewRows((prev) =>
                                  prev.map((r, i) =>
                                    i === idx
                                      ? {
                                          ...r,
                                          roll_number: val,
                                          valid: Boolean(val.trim() && r.full_name.trim()),
                                        }
                                      : r,
                                  ),
                                );
                              }}
                              className="w-full bg-transparent font-mono text-xs font-medium focus:outline-none focus:bg-card px-1 rounded"
                            />
                          </td>
                          <td className="px-3 py-1.5">
                            <input
                              type="text"
                              value={row.full_name}
                              onChange={(e) => {
                                const val = e.target.value;
                                setCsvPreviewRows((prev) =>
                                  prev.map((r, i) =>
                                    i === idx
                                      ? {
                                          ...r,
                                          full_name: val,
                                          valid: Boolean(r.roll_number.trim() && val.trim()),
                                        }
                                      : r,
                                  ),
                                );
                              }}
                              className="w-full bg-transparent text-xs font-medium focus:outline-none focus:bg-card px-1 rounded"
                            />
                          </td>
                          <td className="px-3 py-1.5 text-muted-foreground">
                            <input
                              type="text"
                              value={row.email}
                              onChange={(e) => {
                                const val = e.target.value;
                                setCsvPreviewRows((prev) =>
                                  prev.map((r, i) => (i === idx ? { ...r, email: val } : r)),
                                );
                              }}
                              className="w-full bg-transparent text-xs focus:outline-none focus:bg-card px-1 rounded"
                            />
                          </td>
                          <td className="px-3 py-1.5">
                            {row.valid ? (
                              <span className="text-emerald-600 font-medium text-[11px] inline-flex items-center gap-1">
                                <CheckCircle2 className="size-3" /> Valid
                              </span>
                            ) : (
                              <span className="text-destructive font-medium text-[11px]">
                                {row.reason || "Invalid"}
                              </span>
                            )}
                          </td>
                          <td className="px-2 py-1.5 text-right">
                            <button
                              type="button"
                              onClick={() => {
                                setCsvPreviewRows((prev) => prev.filter((_, i) => i !== idx));
                              }}
                              className="text-muted-foreground hover:text-destructive p-1"
                              title="Remove row"
                            >
                              <X className="size-3.5" />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Footer Buttons */}
            <div className="mt-6 flex justify-end gap-2 border-t border-line pt-4">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setCsvModalOpen(false);
                  setCsvFile(null);
                  setCsvPreviewRows([]);
                }}
                className="text-xs"
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={handleConfirmCSVUpload}
                disabled={
                  !csvFile ||
                  csvPreviewRows.filter((r) => r.valid).length === 0 ||
                  csvUploading ||
                  aiParsing
                }
                className="text-xs bg-primary text-primary-foreground"
              >
                {csvUploading ? (
                  <>
                    <Loader2 className="mr-1.5 size-3.5 animate-spin" /> Enrolling to Course...
                  </>
                ) : (
                  `Confirm & Enroll (${csvPreviewRows.filter((r) => r.valid).length} Students)`
                )}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* Modal: Confirm Student Deletion                                          */}
      {/* ========================================================================= */}
      {deletingStudent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 animate-fade-in">
          <div className="w-full max-w-md rounded-2xl border border-line bg-card p-6 shadow-2xl animate-scale-in">
            <div className="flex items-center gap-3">
              <div className="grid size-10 place-items-center rounded-full bg-destructive/10 text-destructive">
                <Trash2 className="size-5" />
              </div>
              <div>
                <h3 className="font-display text-lg font-semibold text-foreground">
                  Delete Student Record
                </h3>
                <p className="text-xs text-muted-foreground">
                  Remove student from the classroom roll call registry.
                </p>
              </div>
            </div>

            <div className="mt-4 rounded-lg bg-muted/40 p-3.5 text-xs text-foreground/90 space-y-1">
              <p>
                Are you sure you want to delete{" "}
                <span className="font-semibold text-foreground">{deletingStudent.full_name}</span>?
              </p>
              <p className="text-[11px] text-muted-foreground font-mono">
                Roll Number: {deletingStudent.roll_number}{" "}
                {deletingStudent.email ? `• ${deletingStudent.email}` : ""}
              </p>
            </div>

            <p className="mt-2 text-[11px] text-muted-foreground">
              This action decouples the student from existing submissions. Audit trails will
              preserve evaluation history.
            </p>

            <div className="mt-6 flex justify-end gap-2 border-t border-line pt-4">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setDeletingStudent(null)}
                disabled={deleteLoading}
                className="text-xs"
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={handleConfirmDeleteStudent}
                disabled={deleteLoading}
                className="text-xs"
              >
                {deleteLoading ? (
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
    </div>
  );
}
