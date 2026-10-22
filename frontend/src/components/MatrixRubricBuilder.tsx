import React, { useState } from "react";
import {
  ClipboardCheck,
  Plus,
  Trash2,
  Save,
  ArrowLeft,
  Sparkles,
  Info,
  Loader2,
  CheckCircle2,
  ChevronRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { api, type Classroom, type MatrixCriterion, type RubricLevel } from "@/lib/api";

interface MatrixRubricBuilderProps {
  classroom: Classroom | null;
  classrooms: Classroom[];
  onSelectClassroom: (id: string) => void;
  onSaved: () => void;
  onCancel: () => void;
  showToast: (msg: string) => void;
}

interface TierColumn {
  id: string;
  level_name: string;
  points: number;
}

interface MatrixRow {
  id: string;
  criterion_name: string;
  descriptions: Record<string, string>; // tierId -> description text
}

export function MatrixRubricBuilder({
  classroom,
  classrooms,
  onSelectClassroom,
  onSaved,
  onCancel,
  showToast,
}: MatrixRubricBuilderProps) {
  const [title, setTitle] = useState("Object-Oriented Programming & Data Structures Matrix Rubric");
  const [selectedClassId, setSelectedClassId] = useState(classroom?.id || (classrooms[0]?.id || ""));
  const [saving, setSaving] = useState(false);

  // Horizontal score tier columns
  const [tiers, setTiers] = useState<TierColumn[]>([
    { id: "tier_1", level_name: "Exemplary", points: 4 },
    { id: "tier_2", level_name: "Proficient", points: 3 },
    { id: "tier_3", level_name: "Developing", points: 2 },
    { id: "tier_4", level_name: "Unsatisfactory", points: 0 },
  ]);

  // Vertical criteria rows
  const [criteriaRows, setCriteriaRows] = useState<MatrixRow[]>([
    {
      id: "row_1",
      criterion_name: "OOP Structure, Syntax & Real-time Instance Usage",
      descriptions: {
        tier_1: "Class well-defined with correct access specifiers, constructor/destructor implementation, and valid instance instantiation in real-time.",
        tier_2: "Minor syntax issues or imperfect destructor handling, but overall class encapsulation and instantiation are correct.",
        tier_3: "Missing either constructor or destructor; improper encapsulation or public exposure of sensitive members.",
        tier_4: "Program does not compile; fundamental OOP structure missing.",
      },
    },
    {
      id: "row_2",
      criterion_name: "Implementation of User-defined Functions & Logic",
      descriptions: {
        tier_1: "Logic fully decomposed into modular, reusable functions with proper parameters, return types, and algorithmic efficiency.",
        tier_2: "Functions defined and working but contains slight redundancy or suboptimal edge-case parameter checks.",
        tier_3: "Monolithic logic with minimal functional abstraction; repetitive code blocks.",
        tier_4: "User-defined functions missing or produce erroneous outputs.",
      },
    },
    {
      id: "row_3",
      criterion_name: "Execution, Output & Code Quality",
      descriptions: {
        tier_1: "Clean formatting, standard naming conventions, produces expected output without memory leaks or runtime exceptions.",
        tier_2: "Correct execution output with minor formatting or naming inconsistencies.",
        tier_3: "Output contains logical discrepancies or fails on boundary conditions.",
        tier_4: "Program crashes, contains segmentation faults, or infinite loops.",
      },
    },
  ]);

  // Auto-calculate total assignment marks:
  // For each criterion row, the row max is the maximum points among tiers
  const maxTierPoints = tiers.length > 0 ? Math.max(...tiers.map((t) => t.points)) : 0;
  const totalMarks = criteriaRows.length * maxTierPoints;

  // Handlers for Score Tiers
  const handleAddTier = () => {
    const newTierId = `tier_${Date.now()}`;
    const newPoints = tiers.length > 0 ? Math.max(0, Math.min(...tiers.map((t) => t.points)) - 1) : 1;
    setTiers([...tiers, { id: newTierId, level_name: `Tier ${tiers.length + 1}`, points: newPoints }]);
  };

  const handleUpdateTier = (id: string, field: "level_name" | "points", value: any) => {
    setTiers((prev) =>
      prev.map((t) => (t.id === id ? { ...t, [field]: field === "points" ? Number(value) : value } : t))
    );
  };

  const handleRemoveTier = (id: string) => {
    if (tiers.length <= 2) {
      showToast("A matrix rubric must contain at least 2 score tiers.");
      return;
    }
    setTiers((prev) => prev.filter((t) => t.id !== id));
  };

  // Handlers for Criteria Rows
  const handleAddCriterion = () => {
    const newRowId = `row_${Date.now()}`;
    setCriteriaRows([
      ...criteriaRows,
      {
        id: newRowId,
        criterion_name: `Criterion ${criteriaRows.length + 1}`,
        descriptions: {},
      },
    ]);
  };

  const handleUpdateCriterionName = (id: string, name: string) => {
    setCriteriaRows((prev) =>
      prev.map((r) => (r.id === id ? { ...r, criterion_name: name } : r))
    );
  };

  const handleUpdateCellDescription = (rowId: string, tierId: string, text: string) => {
    setCriteriaRows((prev) =>
      prev.map((r) =>
        r.id === rowId
          ? { ...r, descriptions: { ...r.descriptions, [tierId]: text } }
          : r
      )
    );
  };

  const handleRemoveCriterion = (id: string) => {
    if (criteriaRows.length <= 1) {
      showToast("A rubric must have at least one criterion.");
      return;
    }
    setCriteriaRows((prev) => prev.filter((r) => r.id !== id));
  };

  // Save Matrix Rubric to Backend & Supabase
  const handleSave = async () => {
    if (!title.trim()) {
      showToast("Please provide a title for this rubric.");
      return;
    }
    if (!selectedClassId) {
      showToast("Please select a classroom for this rubric.");
      return;
    }

    setSaving(true);
    try {
      // Map to payload structure
      const criteriaPayload = criteriaRows.map((row, idx) => {
        const levels: RubricLevel[] = tiers.map((tier) => ({
          level_name: tier.level_name,
          points: tier.points,
          description: row.descriptions[tier.id] || "",
        }));

        const rowMax = Math.max(...tiers.map((t) => t.points));

        return {
          criterion_name: row.criterion_name.trim(),
          max_points: rowMax,
          order_index: idx,
          levels,
        };
      });

      await api.rubrics.create({
        title: title.trim(),
        classroom_id: selectedClassId,
        total_marks: totalMarks,
        criteria: criteriaPayload,
      });

      showToast("Matrix Rubric successfully created and saved to Supabase!");
      onSaved();
    } catch (err: any) {
      showToast(`Failed to save rubric: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6 animate-fade-up">
      {/* Top Action Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-line pb-4">
        <div>
          <button
            onClick={onCancel}
            className="mb-1 inline-flex items-center text-xs text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="mr-1 size-3.5" /> Back to Dashboard
          </button>
          <h1 className="font-display text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">
            Matrix Rubric Designer
          </h1>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Configure multi-tier grading criteria with quantitative score levels and descriptive feedback.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Total Marks Badge */}
          <div className="rounded-xl border border-primary/20 bg-primary/5 px-4 py-2 text-right">
            <span className="block text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
              Total Assignment Marks
            </span>
            <span className="font-display text-2xl font-bold text-primary">
              {totalMarks} <span className="text-xs font-normal">pts</span>
            </span>
          </div>

          <Button variant="outline" size="sm" onClick={onCancel} className="text-xs">
            Cancel
          </Button>

          <Button
            size="sm"
            onClick={handleSave}
            disabled={saving}
            className="text-xs bg-primary text-primary-foreground hover:bg-primary/90"
          >
            {saving ? (
              <>
                <Loader2 className="mr-1.5 size-3.5 animate-spin" /> Saving Rubric...
              </>
            ) : (
              <>
                <Save className="mr-1.5 size-3.5" /> Save Matrix Rubric
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Rubric Configuration Form */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="sm:col-span-2">
          <label className="block text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Rubric Title
          </label>
          <Input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Object-Oriented Programming & Data Structures Matrix Rubric"
            className="mt-1 text-sm font-medium"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Target Classroom / Course
          </label>
          <select
            value={selectedClassId}
            onChange={(e) => {
              setSelectedClassId(e.target.value);
              onSelectClassroom(e.target.value);
            }}
            className="mt-1 w-full rounded-md border border-line bg-card px-3 py-2 text-xs font-medium text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
          >
            {classrooms.map((c) => (
              <option key={c.id} value={c.id}>
                {c.code} — {c.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Matrix Table Container */}
      <div className="rounded-xl border border-line bg-card shadow-sm overflow-hidden">
        <div className="flex items-center justify-between border-b border-line bg-muted/40 p-4">
          <div className="flex items-center gap-2">
            <ClipboardCheck className="size-4 text-primary" />
            <span className="text-xs font-semibold uppercase tracking-wider text-foreground">
              Criteria & Tier Matrix Grid
            </span>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleAddTier}
              className="text-xs"
            >
              <Plus className="mr-1 size-3.5" /> Add Score Tier
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleAddCriterion}
              className="text-xs"
            >
              <Plus className="mr-1 size-3.5" /> Add Criterion Row
            </Button>
          </div>
        </div>

        {/* Scrollable Matrix */}
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-left text-xs">
            <thead>
              <tr className="border-b border-line bg-muted/30">
                {/* Criterion Header */}
                <th className="w-72 min-w-[280px] border-r border-line p-3 font-semibold text-foreground">
                  Criteria / Skill Areas
                </th>

                {/* Score Tier Columns */}
                {tiers.map((tier) => (
                  <th
                    key={tier.id}
                    className="min-w-[240px] border-r border-line p-3 last:border-r-0"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex-1 space-y-1">
                        <Input
                          value={tier.level_name}
                          onChange={(e) =>
                            handleUpdateTier(tier.id, "level_name", e.target.value)
                          }
                          className="h-7 text-xs font-bold"
                          placeholder="Tier Name"
                        />
                        <div className="flex items-center gap-1.5">
                          <span className="text-[11px] text-muted-foreground">Points:</span>
                          <Input
                            type="number"
                            min="0"
                            step="0.5"
                            value={tier.points}
                            onChange={(e) =>
                              handleUpdateTier(tier.id, "points", e.target.value)
                            }
                            className="h-6 w-16 font-mono text-xs font-semibold"
                          />
                        </div>
                      </div>

                      {tiers.length > 2 && (
                        <button
                          onClick={() => handleRemoveTier(tier.id)}
                          className="text-muted-foreground hover:text-destructive"
                          title="Delete Score Tier"
                        >
                          <Trash2 className="size-3.5" />
                        </button>
                      )}
                    </div>
                  </th>
                ))}
              </tr>
            </thead>

            <tbody className="divide-y divide-line">
              {criteriaRows.map((row, rowIdx) => (
                <tr key={row.id} className="transition-colors hover:bg-muted/10">
                  {/* Criterion Row Title */}
                  <td className="align-top border-r border-line p-3">
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-primary">
                          Criterion #{rowIdx + 1}
                        </span>
                        {criteriaRows.length > 1 && (
                          <button
                            onClick={() => handleRemoveCriterion(row.id)}
                            className="text-muted-foreground hover:text-destructive"
                            title="Delete Criterion"
                          >
                            <Trash2 className="size-3.5" />
                          </button>
                        )}
                      </div>

                      <Textarea
                        value={row.criterion_name}
                        onChange={(e) =>
                          handleUpdateCriterionName(row.id, e.target.value)
                        }
                        rows={3}
                        className="text-xs font-medium resize-none"
                        placeholder="e.g. OOP Structure, Syntax & Real-time Instance Usage"
                      />

                      <div className="flex items-center justify-between text-[11px] text-muted-foreground pt-1">
                        <span>Row Max Score:</span>
                        <span className="font-semibold text-foreground">{maxTierPoints} pts</span>
                      </div>
                    </div>
                  </td>

                  {/* Level Description Cells */}
                  {tiers.map((tier) => (
                    <td
                      key={tier.id}
                      className="align-top border-r border-line p-3 last:border-r-0"
                    >
                      <Textarea
                        value={row.descriptions[tier.id] || ""}
                        onChange={(e) =>
                          handleUpdateCellDescription(row.id, tier.id, e.target.value)
                        }
                        rows={5}
                        placeholder={`Describe expectations for '${tier.level_name}' (${tier.points} pts)...`}
                        className="w-full text-xs leading-relaxed resize-none bg-background/50 focus:bg-background"
                      />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Footer controls */}
        <div className="flex items-center justify-between border-t border-line bg-muted/20 p-4">
          <Button
            variant="outline"
            size="sm"
            onClick={handleAddCriterion}
            className="text-xs"
          >
            <Plus className="mr-1.5 size-3.5" /> Add Criterion Row
          </Button>

          <p className="text-[11px] text-muted-foreground">
            Rubric structure formats standard multi-tier matrices matching academic department guidelines.
          </p>
        </div>
      </div>
    </div>
  );
}
