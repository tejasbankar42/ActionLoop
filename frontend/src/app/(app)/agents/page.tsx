"use client";

import { AlertTriangle, Bot, Building2, CheckCircle2, Copy, ListChecks, Route, ShieldAlert, XCircle } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { Empty, Panel, StatusPill } from "@/components/ui/primitives";
import { DocPreview, FieldTable, ValidationList } from "@/components/workflow/parts";
import { cn } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import type { WorkflowDetail, WorkflowSummary } from "@/lib/types";

const PRIORITY: Record<string, string> = { urgent: "bg-bad text-white", high: "bg-warn text-white", normal: "bg-surface-2 text-ink-2", low: "bg-surface-2 text-ink-3" };

function AgentsInner() {
  const params = useSearchParams();
  const { data: list } = useApi<WorkflowSummary[]>("/api/workflows?limit=40", 5000);
  const [wfId, setWfId] = useState<string | null>(params.get("wf"));
  useEffect(() => {
    if (!wfId && list?.length) setWfId(list[0].id);
  }, [list, wfId]);
  const { data: wf } = useApi<WorkflowDetail>(wfId ? `/api/workflows/${wfId}` : null, 4000);
  const [tab, setTab] = useState<"extractor" | "validator" | "planner">("extractor");

  if (!list) return null;
  if (!list.length) return <Panel><Empty icon={<Bot />} title="No workflows yet">Process a document to see agent outputs.</Empty></Panel>;

  const ex = wf?.executions.filter((e) => e.agent === "extractor").at(-1);
  const exOut = (ex?.output ?? {}) as { document_type?: string; type_confidence?: number; warnings?: string[]; engine?: string };
  const missing = wf?.fields.filter((f) => f.status === "missing") ?? [];
  const uncertain = wf?.fields.filter((f) => f.status === "uncertain") ?? [];
  const counts = { passed: 0, warning: 0, failed: 0 };
  wf?.validations.forEach((v) => counts[v.status]++);
  const dup = wf?.validations.find((v) => v.rule_type === "duplicate");

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <label className="text-sm font-semibold text-ink-2" htmlFor="wf">Workflow</label>
        <select
          id="wf"
          value={wfId ?? ""}
          onChange={(e) => setWfId(e.target.value)}
          className="h-10 min-w-0 max-w-full flex-1 rounded-lg border border-line bg-surface px-3 text-sm text-ink sm:max-w-md"
        >
          {list.map((w) => (
            <option key={w.id} value={w.id}>
              {w.filename} — {w.status.replace("_", " ")}
            </option>
          ))}
        </select>
        {wf && <StatusPill status={wf.status} />}
      </div>

      <div className="flex gap-1 rounded-xl border border-line bg-surface p-1 lg:hidden">
        {(["extractor", "validator", "planner"] as const).map((t) => (
          <button key={t} onClick={() => setTab(t)} className={cn("flex-1 rounded-lg py-2 text-sm font-semibold capitalize", tab === t ? "bg-navy text-white" : "text-ink-2")}>
            {t}
          </button>
        ))}
      </div>

      {wf && (
        <div className="grid gap-6 lg:grid-cols-3">
          {/* EXTRACTOR */}
          <div className={cn("space-y-6", tab !== "extractor" && "hidden lg:block")}>
            <AgentHeader color="var(--agent-extract)" icon={<Bot />} name="Extractor Agent" engine={exOut.engine ?? ex?.engine} />
            <Panel title="Classification">
              <div className="flex items-end justify-between">
                <div>
                  <p className="text-xl font-extrabold text-ink">{wf.type_label ?? "Unknown document"}</p>
                  <p className="text-xs text-ink-3">detected document type</p>
                </div>
                <p className="text-3xl font-extrabold text-a-extract">{exOut.type_confidence != null ? `${Math.round(exOut.type_confidence * 100)}%` : "—"}</p>
              </div>
              {(missing.length > 0 || uncertain.length > 0) && (
                <div className="mt-4 space-y-2">
                  {missing.map((f) => (
                    <p key={f.id} className="flex items-center gap-2 text-sm text-bad"><XCircle className="size-4" /> Missing: {f.label}</p>
                  ))}
                  {uncertain.map((f) => (
                    <p key={f.id} className="flex items-center gap-2 text-sm text-[#b54708] dark:text-warn"><AlertTriangle className="size-4" /> Uncertain: {f.label}</p>
                  ))}
                </div>
              )}
              {exOut.warnings?.filter((w) => w.startsWith("DEMO")).map((w) => (
                <p key={w} className="mt-3 rounded-lg bg-warn/10 px-3 py-2 text-xs text-ink-2">{w}</p>
              ))}
            </Panel>
            <Panel title="Extracted fields" subtitle="Value · confidence">
              <FieldTable fields={wf.fields} />
            </Panel>
            <Panel title="Original document" bodyClass="p-3">
              <DocPreview doc={wf.document} className="h-[360px]" />
            </Panel>
          </div>

          {/* VALIDATOR */}
          <div className={cn("space-y-6", tab !== "validator" && "hidden lg:block")}>
            <AgentHeader color="var(--agent-validate)" icon={<ListChecks />} name="Validator Agent" engine="deterministic rules + database" />
            <div className="grid grid-cols-3 gap-3">
              {(
                [
                  ["Passed", counts.passed, "var(--ok)", CheckCircle2],
                  ["Warnings", counts.warning, "var(--warn)", AlertTriangle],
                  ["Failed", counts.failed, "var(--bad)", XCircle],
                ] as const
              ).map(([l, n, c, Icon]) => (
                <div key={l} className="rounded-xl border border-line bg-surface p-4">
                  <Icon className="size-4" style={{ color: c }} />
                  <p className="mt-2 text-2xl font-extrabold text-ink">{n}</p>
                  <p className="text-xs text-ink-3">{l}</p>
                </div>
              ))}
            </div>
            <Panel title="Duplicate check" action={<Copy className="size-4 text-ink-3" />}>
              {dup ? (
                <div className={cn("rounded-lg px-3 py-3 text-sm", dup.status === "failed" ? "bg-bad/10 text-bad" : dup.status === "warning" ? "bg-warn/10 text-ink" : "bg-ok/10 text-ink")}>
                  {dup.message}
                </div>
              ) : (
                <p className="text-sm text-ink-3">No duplicate rule applies to this document type.</p>
              )}
            </Panel>
            <Panel title="Validation checklist" subtitle={`Overall: ${wf.validation_status ?? "—"}`}>
              <ValidationList items={wf.validations} />
            </Panel>
          </div>

          {/* PLANNER */}
          <div className={cn("space-y-6", tab !== "planner" && "hidden lg:block")}>
            <AgentHeader color="var(--agent-plan)" icon={<Route />} name="Action Planner" engine="policy rules" />
            {wf.requires_approval && (
              <div className="rounded-[var(--radius-card)] border border-warn/40 bg-warn/10 p-4">
                <p className="flex items-center gap-2 text-sm font-bold text-ink"><ShieldAlert className="size-4 text-warn" /> Human approval required</p>
                <ul className="mt-2 list-disc space-y-1 pl-6 text-sm text-ink-2">
                  {wf.approval_reasons.map((r) => <li key={r}>{r}</li>)}
                </ul>
              </div>
            )}
            <Panel title="Recommended actions" subtitle={`Overall priority: ${wf.priority}`} bodyClass="p-0">
              {wf.actions.length === 0 ? (
                <Empty title="No plan yet" />
              ) : (
                <ol className="divide-y divide-line">
                  {wf.actions.map((a) => (
                    <li key={a.id} className="p-5">
                      <div className="flex items-start gap-3">
                        <span className="grid size-7 shrink-0 place-items-center rounded-full bg-a-plan/15 text-xs font-bold text-a-plan">{a.step}</span>
                        <div className="min-w-0 flex-1">
                          <p className="font-semibold text-ink">{a.title}</p>
                          <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
                            <span className={cn("rounded-md px-2 py-0.5 font-bold uppercase", PRIORITY[a.priority])}>{a.priority}</span>
                            <span className="inline-flex items-center gap-1 text-ink-2"><Building2 className="size-3.5" /> {a.department}</span>
                            <span className="text-ink-3">impact {a.impact}</span>
                            {a.requires_approval && <StatusPill status="pending">approval</StatusPill>}
                            <StatusPill status={a.status}>{a.status}</StatusPill>
                          </div>
                          <p className="mt-2 text-sm text-ink-2">{a.reasoning}</p>
                        </div>
                      </div>
                    </li>
                  ))}
                </ol>
              )}
            </Panel>
          </div>
        </div>
      )}
    </div>
  );
}

function AgentHeader({ color, icon, name, engine }: { color: string; icon: React.ReactNode; name: string; engine?: string }) {
  return (
    <div className="flex items-center gap-3 rounded-[var(--radius-card)] p-4 text-white" style={{ background: `linear-gradient(135deg, var(--navy), var(--navy-2))` }}>
      <span className="grid size-10 place-items-center rounded-xl [&_svg]:size-5" style={{ background: color }}>{icon}</span>
      <div>
        <p className="font-bold">{name}</p>
        <p className="hash text-[#98A2B3]">{engine ?? "—"}</p>
      </div>
    </div>
  );
}

export default function AgentsPage() {
  return (
    <Suspense>
      <AgentsInner />
    </Suspense>
  );
}
