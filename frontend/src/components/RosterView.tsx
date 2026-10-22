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

  // CSV upload modal & preview state
  const [csvModalOpen, setCsvModalOpen] = useState(false);
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [csvPreviewRows, setCsvPreviewRows] = useState<Array<{ roll_number: string; full_name: string; email: string; valid: boolean; reason?: string }>>([]);
  const [csvUploading, setCsvUploading] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

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
    setManualRows((prev) =>
      prev.map((r) => (r.id === id ? { ...r, [field]: value } : r))
    );
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
        }))
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

  // CSV parsing & upload
  const processCSVFile = (file: File) => {
    setCsvFile(file);
    Papa.parse(file, {
      header: true,
      skipEmptyLines: true,
      complete: (results) => {
        const parsedRows = results.data as Record<string, string>[];
        const preview: Array<{ roll_number: string; full_name: string; email: string; valid: boolean; reason?: string }> = [];

        const seenInFile = new Set<string>();

        parsedRows.forEach((row) => {
          let roll = "";
          let name = "";
          let email = "";

          for (const [k, v] of Object.entries(row)) {
            const cleanKey = k.toLowerCase().replace(/[^a-z]/g, "");
            const val = (v || "").trim();
            if (["rollnumber", "rollno", "roll", "studentroll", "id"].includes(cleanKey)) {
              roll = val;
            } else if (["name", "fullname", "studentname", "names"].includes(cleanKey)) {
              name = val;
            } else if (["email", "emailaddress", "studentemail", "mail"].includes(cleanKey)) {
              email = val;
            }
          }

          if (!roll || !name) {
            preview.push({
              roll_number: roll,
              full_name: name,
              email: email,
              valid: false,
              reason: "Missing Roll No or Name",
            });
          } else if (seenInFile.has(roll)) {
            preview.push({
              roll_number: roll,
              full_name: name,
              email: email,
              valid: false,
              reason: "Duplicate roll # in file",
            });
          } else {
            seenInFile.add(roll);
            preview.push({
              roll_number: roll,
              full_name: name,
              email: email,
              valid: true,
            });
          }
        });

        setCsvPreviewRows(preview);
      },
      error: (error) => {
        showToast(`Failed to parse CSV: ${error.message}`);
      },
    });
  };

  const handleConfirmCSVUpload = async () => {
    if (!classroom?.id || !csvFile) return;

    setCsvUploading(true);
    try {
      const res = await api.classrooms.uploadCSV(classroom.id, csvFile);
      showToast(`CSV Upload complete! Enrolled: ${res.total_inserted}, Skipped: ${res.total_skipped}`);
      setCsvModalOpen(false);
      setCsvFile(null);
      setCsvPreviewRows([]);
      await loadStudents(classroom.id);
    } catch (err: any) {
      showToast(`CSV Upload failed: ${err.message}`);
    } finally {
      setCsvUploading(false);
    }
  };

  const handleExportCSV = () => {
    if (students.length === 0) {
      showToast("No students to export.");
      return;
    }
    const csvContent =
      "Roll Number,Full Name,Email,Enrollment Date\n" +
      students
        .map(
          (s) =>
            `"${s.roll_number}","${s.full_name}","${s.email || ""}","${s.created_at || ""}"`
        )
        .join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `${classroom?.code || "classroom"}_roster.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Filter and sort students
  const filteredStudents = students
    .filter(
      (s) =>
        s.roll_number.toLowerCase().includes(search.toLowerCase()) ||
        s.full_name.toLowerCase().includes(search.toLowerCase()) ||
        (s.email && s.email.toLowerCase().includes(search.toLowerCase()))
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
            Enrolled student registry synced directly with Supabase PostgreSQL.
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
            <FileSpreadsheet className="mr-1.5 size-3.5 text-emerald-600" /> Upload CSV
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
            <span className="text-sm">Fetching student roster from Supabase...</span>
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
              Enroll students manually or upload a class CSV roster to track submissions and auto-grade.
            </p>
            <div className="mt-4 flex justify-center gap-2">
              <Button size="sm" onClick={() => setManualModalOpen(true)} className="text-xs">
                <UserPlus className="mr-1.5 size-3.5" /> Add Students Manually
              </Button>
              <Button size="sm" variant="outline" onClick={() => setCsvModalOpen(true)} className="text-xs">
                <Upload className="mr-1.5 size-3.5" /> Import CSV Roster
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
                  <th className="px-4 py-3 text-right">Added On</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {filteredStudents.map((student) => (
                  <tr key={student.id} className="transition-colors hover:bg-muted/20">
                    <td className="px-4 py-3 font-mono font-medium text-foreground">
                      {student.roll_number}
                    </td>
                    <td className="px-4 py-3 font-medium text-foreground">
                      {student.full_name}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {student.email || "—"}
                    </td>
                    <td className="px-4 py-3">
                      <span className="inline-flex items-center gap-1 rounded-md bg-emerald-50 px-2 py-0.5 text-[11px] font-medium text-emerald-700">
                        <CheckCircle2 className="size-3" /> Enrolled
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right text-muted-foreground">
                      {student.created_at
                        ? new Date(student.created_at).toLocaleDateString()
                        : "Active"}
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
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setManualModalOpen(false)}
              >
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
                      onChange={(e) =>
                        handleUpdateManualRow(row.id, "roll_number", e.target.value)
                      }
                      className="text-xs"
                    />
                  </div>
                  <div className="col-span-4">
                    <Input
                      placeholder="Student full name"
                      value={row.full_name}
                      onChange={(e) =>
                        handleUpdateManualRow(row.id, "full_name", e.target.value)
                      }
                      className="text-xs"
                    />
                  </div>
                  <div className="col-span-4">
                    <Input
                      type="email"
                      placeholder="student@univ.edu"
                      value={row.email}
                      onChange={(e) =>
                        handleUpdateManualRow(row.id, "email", e.target.value)
                      }
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
              <Button
                variant="outline"
                size="sm"
                onClick={handleAddManualRow}
                className="text-xs"
              >
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
      {/* Modal: CSV Upload & Drag-and-Drop Dropzone with Live Preview             */}
      {/* ========================================================================= */}
      {csvModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="w-full max-w-2xl rounded-2xl border border-line bg-card p-6 shadow-2xl animate-fade-up">
            <div className="flex items-center justify-between border-b border-line pb-4">
              <div>
                <h2 className="font-display text-xl font-semibold text-foreground">
                  Import Roll Call CSV
                </h2>
                <p className="text-xs text-muted-foreground">
                  Upload a class roster with columns: roll_number, full_name, email.
                </p>
              </div>
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
                  processCSVFile(e.dataTransfer.files[0]);
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
                accept=".csv"
                className="hidden"
                onChange={(e) => {
                  if (e.target.files && e.target.files[0]) {
                    processCSVFile(e.target.files[0]);
                  }
                }}
              />
              <div className="mx-auto mb-2 grid size-10 place-items-center rounded-full bg-primary/10 text-primary">
                <FileSpreadsheet className="size-5" />
              </div>
              <p className="text-sm font-medium text-foreground">
                {csvFile ? csvFile.name : "Click to select or drag and drop a .csv file"}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                Supported columns: roll_number (or roll_no), name (or full_name), email
              </p>
            </div>

            {/* Live Preview Table */}
            {csvPreviewRows.length > 0 && (
              <div className="mt-4">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Parsed Preview ({csvPreviewRows.filter((r) => r.valid).length} valid rows)
                  </p>
                  {csvPreviewRows.some((r) => !r.valid) && (
                    <span className="text-[11px] text-amber-600 font-medium">
                      {csvPreviewRows.filter((r) => !r.valid).length} skipped or invalid
                    </span>
                  )}
                </div>

                <div className="max-h-48 overflow-y-auto rounded-lg border border-line">
                  <table className="w-full text-left text-xs">
                    <thead className="sticky top-0 bg-muted text-[10px] uppercase font-semibold text-muted-foreground">
                      <tr>
                        <th className="px-3 py-2">Roll No</th>
                        <th className="px-3 py-2">Full Name</th>
                        <th className="px-3 py-2">Email</th>
                        <th className="px-3 py-2">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-line">
                      {csvPreviewRows.map((row, idx) => (
                        <tr key={idx} className={row.valid ? "" : "bg-destructive/5 text-muted-foreground"}>
                          <td className="px-3 py-2 font-mono font-medium">
                            {row.roll_number || "—"}
                          </td>
                          <td className="px-3 py-2">{row.full_name || "—"}</td>
                          <td className="px-3 py-2 text-muted-foreground">{row.email || "—"}</td>
                          <td className="px-3 py-2">
                            {row.valid ? (
                              <span className="text-emerald-600 font-medium text-[11px]">Valid</span>
                            ) : (
                              <span className="text-destructive font-medium text-[11px]">
                                {row.reason}
                              </span>
                            )}
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
                disabled={!csvFile || csvPreviewRows.filter((r) => r.valid).length === 0 || csvUploading}
                className="text-xs bg-primary text-primary-foreground"
              >
                {csvUploading ? (
                  <>
                    <Loader2 className="mr-1.5 size-3.5 animate-spin" /> Enrolling from CSV...
                  </>
                ) : (
                  `Confirm & Enroll (${csvPreviewRows.filter((r) => r.valid).length} Students)`
                )}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
