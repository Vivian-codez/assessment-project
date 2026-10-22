import React, { useState, useEffect } from "react";
import {
  ClipboardCheck,
  Plus,
  Trash2,
  Eye,
  Calendar,
  Layers,
  Award,
  Loader2,
  CheckCircle2,
  FileText,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { api, type Classroom, type Rubric } from "@/lib/api";

interface RubricsListViewProps {
  classroom: Classroom | null;
  classrooms: Classroom[];
  onOpenCreateRubric: () => void;
  showToast: (msg: string) => void;
}

export function RubricsListView({
  classroom,
  classrooms,
  onOpenCreateRubric,
  showToast,
}: RubricsListViewProps) {
  const [rubrics, setRubrics] = useState<Rubric[]>([]);
  const [loading, setLoading] = useState(false);
  const [inspectRubric, setInspectRubric] = useState<Rubric | null>(null);

  useEffect(() => {
    loadRubrics();
  }, [classroom?.id]);

  const loadRubrics = async () => {
    setLoading(true);
    try {
      const data = await api.rubrics.list(classroom?.id);
      setRubrics(data || []);
    } catch (err: any) {
      console.warn("Failed to load rubrics:", err);
      showToast(`Error fetching rubrics: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (rubricId: string) => {
    if (!window.confirm("Are you sure you want to delete this matrix rubric?")) return;
    try {
      await api.rubrics.delete(rubricId);
      showToast("Rubric deleted.");
      setRubrics((prev) => prev.filter((r) => r.id !== rubricId));
      if (inspectRubric?.id === rubricId) setInspectRubric(null);
    } catch (err: any) {
      showToast(`Failed to delete rubric: ${err.message}`);
    }
  };

  return (
    <div className="space-y-6 animate-fade-up">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">
            Academic Assessment Guidelines
          </p>
          <h1 className="font-display text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
            Matrix Rubric Repository
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Multi-tier criteria matrices configured for automated grading & teacher review.
          </p>
        </div>

        <Button
          size="sm"
          onClick={onOpenCreateRubric}
          className="bg-primary text-primary-foreground text-xs hover:bg-primary/90"
        >
          <Plus className="mr-1.5 size-3.5" /> Build New Matrix Rubric
        </Button>
      </div>

      {/* Grid of Rubrics */}
      {loading ? (
        <div className="flex items-center justify-center p-12 text-muted-foreground">
          <Loader2 className="mr-2 size-5 animate-spin" />
          <span className="text-sm">Loading matrix rubrics from Supabase...</span>
        </div>
      ) : rubrics.length === 0 ? (
        <div className="rounded-xl border border-line bg-card p-12 text-center">
          <div className="mx-auto mb-3 grid size-12 place-items-center rounded-full bg-muted text-muted-foreground">
            <ClipboardCheck className="size-6" />
          </div>
          <h3 className="font-display text-lg font-medium text-foreground">
            No matrix rubrics created yet
          </h3>
          <p className="mx-auto mt-1 max-w-sm text-xs text-muted-foreground">
            Build multi-tier criteria matrices with specific score tiers (e.g. 4 pts, 3 pts, 2 pts, 0 pts) to benchmark student submissions.
          </p>
          <div className="mt-4 flex justify-center">
            <Button size="sm" onClick={onOpenCreateRubric} className="text-xs">
              <Plus className="mr-1.5 size-3.5" /> Create Your First Rubric
            </Button>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {rubrics.map((r) => {
            const classObj = classrooms.find((c) => c.id === r.classroom_id || c.id === r.course_id);
            const totalMarks = r.total_marks || r.total_max_score || 0;

            return (
              <div
                key={r.id}
                className="flex flex-col justify-between rounded-xl border border-line bg-card p-5 shadow-sm transition-all hover:border-primary/40 hover:shadow-md"
              >
                <div>
                  <div className="flex items-start justify-between gap-2">
                    <span className="inline-flex items-center rounded-md bg-primary/10 px-2 py-0.5 text-[11px] font-medium text-primary">
                      {classObj ? `${classObj.code}` : "Classroom Rubric"}
                    </span>
                    <span className="font-mono text-xs font-bold text-foreground">
                      {totalMarks} pts
                    </span>
                  </div>

                  <h3 className="mt-3 font-display text-lg font-semibold text-foreground line-clamp-2">
                    {r.title || r.name}
                  </h3>

                  <div className="mt-3 flex items-center gap-3 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Layers className="size-3.5" />
                      {r.criteria?.length || 0} criteria
                    </span>
                    {r.created_at && (
                      <span className="flex items-center gap-1">
                        <Calendar className="size-3.5" />
                        {new Date(r.created_at).toLocaleDateString()}
                      </span>
                    )}
                  </div>

                  {/* Criteria Preview List */}
                  {r.criteria && r.criteria.length > 0 && (
                    <div className="mt-3 space-y-1 rounded-lg bg-muted/30 p-2.5 text-[11px]">
                      {r.criteria.slice(0, 3).map((crit, idx) => (
                        <div key={idx} className="flex items-center justify-between text-muted-foreground">
                          <span className="truncate max-w-[180px]">
                            • {crit.criterion_name || crit.name}
                          </span>
                          <span className="font-mono text-[10px] text-foreground font-medium">
                            {crit.max_points || crit.max} pts
                          </span>
                        </div>
                      ))}
                      {r.criteria.length > 3 && (
                        <p className="text-[10px] text-muted-foreground italic pt-0.5">
                          +{r.criteria.length - 3} more criteria
                        </p>
                      )}
                    </div>
                  )}
                </div>

                <div className="mt-4 flex items-center justify-between border-t border-line pt-3">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setInspectRubric(r)}
                    className="text-xs text-primary hover:text-primary/80"
                  >
                    <Eye className="mr-1 size-3.5" /> View Matrix
                  </Button>

                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => handleDelete(r.id)}
                    className="size-8 text-muted-foreground hover:text-destructive"
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

      {/* Inspection Modal */}
      {inspectRubric && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="w-full max-w-4xl max-h-[85vh] overflow-hidden flex flex-col rounded-2xl border border-line bg-card shadow-2xl animate-fade-up">
            <div className="flex items-center justify-between border-b border-line p-5 bg-muted/20">
              <div>
                <h2 className="font-display text-xl font-bold text-foreground">
                  {inspectRubric.title || inspectRubric.name}
                </h2>
                <p className="text-xs text-muted-foreground">
                  Total Marks: {inspectRubric.total_marks || inspectRubric.total_max_score} points · {inspectRubric.criteria?.length || 0} criteria
                </p>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setInspectRubric(null)}
              >
                ✕
              </Button>
            </div>

            <div className="flex-1 overflow-y-auto p-5 space-y-4">
              {inspectRubric.criteria?.map((crit, idx) => (
                <div key={idx} className="rounded-xl border border-line bg-card p-4 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-display text-sm font-semibold text-foreground">
                      #{idx + 1}. {crit.criterion_name || crit.name}
                    </span>
                    <Badge variant="outline" className="font-mono text-xs">
                      Max {crit.max_points || crit.max} pts
                    </Badge>
                  </div>

                  {crit.levels && crit.levels.length > 0 ? (
                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2 pt-2">
                      {crit.levels.map((lvl, lIdx) => (
                        <div key={lIdx} className="rounded-lg border border-line/60 bg-muted/20 p-2.5 text-xs">
                          <div className="flex items-center justify-between font-semibold text-foreground mb-1">
                            <span>{lvl.level_name}</span>
                            <span className="font-mono text-primary">{lvl.points} pts</span>
                          </div>
                          <p className="text-[11px] leading-relaxed text-muted-foreground">
                            {lvl.description || "—"}
                          </p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-muted-foreground">{crit.description || "No level descriptions."}</p>
                  )}
                </div>
              ))}
            </div>

            <div className="border-t border-line p-4 flex justify-end bg-muted/10">
              <Button size="sm" onClick={() => setInspectRubric(null)} className="text-xs">
                Close
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
