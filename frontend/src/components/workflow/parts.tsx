"use client";

import { AlertTriangle, CheckCircle2, Circle, FileText, Loader2, XCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { Confidence, Skeleton, StatusPill } from "@/components/ui/primitives";
import { fileUrl } from "@/lib/api";
import { cn } from "@/lib/format";
import type { DocumentItem, Field, Validation, WorkflowDetail } from "@/lib/types";

const STAGES = [
  { key: "uploaded", label: "Uploaded" },
  { key: "extractor", label: "Extracting" },
  { key: "validator", label: "Validating" },
  { key: "action_planner", label: "Planning" },
  { key: "human_approval", label: "Approval" },
  { key: "done", label: "Completed" },
];

function stageState(wf: Pick<WorkflowDetail, "status" | "current_stage" | "executions" | "requires_approval">, key: string) {
  const ex = wf.executions?.filter((e) => e.agent === key).at(-1);
  if (key === "uploaded") return "done";
  if (key === "done") {
    if (wf.status === "completed") return "done";
    if (["rejected", "failed"].includes(wf.status)) return "failed";
    if (wf.status === "needs_correction") return "warn";
    return "todo";
  }
  if (key === "human_approval") {
    if (!wf.requires_approval && ["completed"].includes(wf.status)) return "skipped";
    if (wf.status === "awaiting_approval") return "waiting";
  }
  if (!ex) return "todo";
  if (ex.status === "failed") return "failed";
  if (ex.status === "running") return "running";
  if (ex.status === "waiting") return "waiting";
  return "done";
}

export function StageTrack({ wf, compact }: { wf: WorkflowDetail; compact?: boolean }) {
  return (
    <ol className={cn("flex w-full items-center", compact ? "gap-1" : "gap-2")}>
      {STAGES.map((s, i) => {
        const st = stageState(wf, s.key);
        const label = s.key === "done" && wf.status !== "completed" && st !== "todo" ? wf.status.replace("_", " ") : s.label;
        return (
          <li key={s.key} className="flex flex-1 items-center gap-2">
            <div className="flex min-w-0 flex-col items-center gap-1.5">
              <span
                className={cn(
                  "grid size-7 place-items-center rounded-full border-2 text-[11px] font-bold",
                  st === "done" && "border-ok bg-ok text-white",
                  st === "running" && "border-a-human text-a-human",
                  st === "waiting" && "border-warn bg-warn/10 text-warn",
                  st === "warn" && "border-warn bg-warn text-white",
                  st === "failed" && "border-bad bg-bad text-white",
                  st === "skipped" && "border-dashed border-line text-ink-3",
                  st === "todo" && "border-line text-ink-3",
                )}
              >
                {st === "done" ? (
                  <CheckCircle2 className="size-4" />
                ) : st === "running" ? (
                  <Loader2 className="size-3.5 animate-spin" />
                ) : st === "failed" ? (
                  <XCircle className="size-4" />
                ) : st === "waiting" || st === "warn" ? (
                  <AlertTriangle className="size-3.5" />
                ) : (
                  i + 1
                )}
              </span>
              {!compact && <span className="whitespace-nowrap text-[11px] font-semibold capitalize text-ink-2">{st === "skipped" ? "Auto" : label}</span>}
            </div>
            {i < STAGES.length - 1 && (
              <span className={cn("mb-5 h-0.5 flex-1 rounded-full", st === "done" || st === "skipped" ? "bg-ok/60" : "bg-line", compact && "mb-0")} />
            )}
          </li>
        );
      })}
    </ol>
  );
}

export function DocPreview({ doc, className }: { doc: DocumentItem; className?: string }) {
  const [url, setUrl] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    let revoke: string | null = null;
    setUrl(null);
    setErr(null);
    if (!doc.has_file) {
      setErr("Seeded history record — no stored file.");
      return;
    }
    fileUrl(doc.id)
      .then((u) => {
        revoke = u;
        setUrl(u);
      })
      .catch((e) => setErr(e.message));
    return () => {
      if (revoke) URL.revokeObjectURL(revoke);
    };
  }, [doc.id, doc.has_file]);

  if (err)
    return (
      <div className={cn("grid place-items-center rounded-xl border border-dashed border-line bg-surface-2 p-8 text-center text-xs text-ink-3", className)}>
        <FileText className="mb-2 size-6" />
        {err}
      </div>
    );
  if (!url) return <Skeleton className={cn("h-[420px] w-full rounded-xl", className)} />;
  return doc.content_type === "application/pdf" ? (
    <iframe src={`${url}#toolbar=0&view=FitH`} title={doc.filename} className={cn("h-[420px] w-full rounded-xl border border-line bg-white", className)} />
  ) : (
    // eslint-disable-next-line @next/next/no-img-element
    <img src={url} alt={doc.filename} className={cn("w-full rounded-xl border border-line bg-white object-contain", className)} />
  );
}

export function FieldTable({ fields, editable, values, onChange }: {
  fields: Field[];
  editable?: boolean;
  values?: Record<string, string>;
  onChange?: (name: string, v: string) => void;
}) {
  if (!fields.length) return <p className="py-6 text-center text-sm text-ink-3">No fields extracted.</p>;
  return (
    <div className="divide-y divide-line">
      {fields.map((f) => (
        <div key={f.id} className="grid grid-cols-[minmax(110px,1fr)_minmax(0,1.6fr)_auto] items-center gap-3 py-2.5">
          <div className="min-w-0">
            <p className="truncate text-xs font-semibold text-ink-2">{f.label}</p>
            {f.note && <p className="truncate text-[11px] text-ink-3" title={f.note}>{f.note}</p>}
          </div>
          {editable && (f.status !== "ok" || values?.[f.name] !== undefined) ? (
            <input
              value={values?.[f.name] ?? f.value ?? ""}
              placeholder={f.status === "missing" ? "Enter value from the original" : "Verify value"}
              onChange={(e) => onChange?.(f.name, e.target.value)}
              className="h-8 w-full rounded-md border border-warn/60 bg-warn/5 px-2 font-mono text-xs text-ink focus:border-teal focus:outline-none"
            />
          ) : (
            <p className={cn("truncate font-mono text-[13px]", f.value ? "text-ink" : "italic text-ink-3")} title={f.value ?? ""}>
              {f.value ?? (f.status === "missing" ? "not found" : "unreadable")}
            </p>
          )}
          <div className="flex items-center gap-2">
            <Confidence value={f.confidence} status={f.status} />
            {f.status !== "ok" && <StatusPill status={f.status} />}
          </div>
        </div>
      ))}
    </div>
  );
}

export function ValidationList({ items }: { items: Validation[] }) {
  if (!items.length) return <p className="py-6 text-center text-sm text-ink-3">No validation results yet.</p>;
  const order = { failed: 0, warning: 1, passed: 2 };
  return (
    <ul className="space-y-1.5">
      {[...items].sort((a, b) => order[a.status] - order[b.status]).map((v) => (
        <li key={v.id} className="flex gap-3 rounded-lg px-2 py-2 hover:bg-surface-2">
          {v.status === "passed" ? (
            <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-ok" />
          ) : v.status === "warning" ? (
            <AlertTriangle className="mt-0.5 size-4 shrink-0 text-warn" />
          ) : (
            <XCircle className="mt-0.5 size-4 shrink-0 text-bad" />
          )}
          <div className="min-w-0 flex-1">
            <p className="text-sm text-ink">{v.message}</p>
            <p className="hash mt-0.5 text-ink-3">
              {v.rule_code} · {v.rule_type}
            </p>
          </div>
        </li>
      ))}
    </ul>
  );
}

export function Stat({ label, value, hint, accent, icon }: { label: string; value: React.ReactNode; hint?: React.ReactNode; accent?: string; icon?: React.ReactNode }) {
  return (
    <div className="relative overflow-hidden rounded-[var(--radius-card)] border border-line bg-surface p-5">
      <span className="absolute inset-x-0 top-0 h-[3px]" style={{ background: accent ?? "var(--teal)" }} />
      <div className="flex items-start justify-between">
        <p className="text-xs font-semibold uppercase tracking-wider text-ink-3">{label}</p>
        <span className="text-ink-3 [&_svg]:size-4">{icon}</span>
      </div>
      <p className="mt-3 text-3xl font-extrabold tracking-tight text-ink tabular-nums">{value}</p>
      {hint && <p className="mt-1 text-xs text-ink-3">{hint}</p>}
    </div>
  );
}

export function PlainCircle() {
  return <Circle className="size-3" />;
}
