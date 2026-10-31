"use client";

import { Activity, AlertOctagon, CheckCircle2, Clock, FileStack, Gauge, ShieldCheck, Upload } from "lucide-react";
import Link from "next/link";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Button, Empty, Panel, Skeleton, StatusPill } from "@/components/ui/primitives";
import { Stat } from "@/components/workflow/parts";
import { AGENTS, ago, duration, pct, shortHash } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import type { AuditEvent, DocumentItem, Execution, WorkflowSummary } from "@/lib/types";

interface Overview {
  totals: {
    documents_processed: number;
    live_workflows: number;
    seeded_workflows: number;
    successful_workflows: number;
    pending_approvals: number;
    validation_failures: number;
    avg_automated_ms: number | null;
    avg_end_to_end_ms: number | null;
    success_rate: number | null;
    in_progress: number;
  };
  activity: { date: string; processed: number; completed: number; exceptions: number; live: number }[];
  recent_documents: DocumentItem[];
  recent_workflows: WorkflowSummary[];
  pending_preview: { id: string; workflow_id: string; filename: string; document_type: string; reasons: string[]; priority: string; created_at: string }[];
  recent_audit: AuditEvent[];
}
interface AgentStatus {
  agent: string;
  counts: Record<string, number>;
  avg_duration_ms: number | null;
  last: Execution | null;
  engine: string;
}

export default function Dashboard() {
  const { data: o } = useApi<Overview>("/api/analytics/overview", 4000);
  const { data: agents } = useApi<AgentStatus[]>("/api/agents/status", 4000);

  if (!o) return <DashSkeleton />;
  const t = o.totals;
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm text-ink-3">NMIET Administration · live operations</p>
          <h2 className="text-2xl font-extrabold tracking-tight text-ink">Good to see you. {t.pending_approvals} decision{t.pending_approvals === 1 ? "" : "s"} waiting.</h2>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" asChild>
            <Link href="/approvals">
              <ShieldCheck /> Review queue
            </Link>
          </Button>
          <Button asChild>
            <Link href="/documents?upload=1">
              <Upload /> Quick upload
            </Link>
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-3 xl:grid-cols-6">
        <Stat label="Documents processed" value={t.documents_processed} hint={`${t.live_workflows} live · ${t.seeded_workflows} seeded history`} icon={<FileStack />} />
        <Stat label="Successful" value={t.successful_workflows} hint="completed workflows" accent="var(--ok)" icon={<CheckCircle2 />} />
        <Stat label="Pending approvals" value={t.pending_approvals} hint="awaiting a reviewer" accent="var(--warn)" icon={<ShieldCheck />} />
        <Stat label="Validation failures" value={t.validation_failures} hint="blocked before action" accent="var(--bad)" icon={<AlertOctagon />} />
        <Stat label="Avg processing" value={duration(t.avg_automated_ms)} hint={`agents only · end-to-end ${duration(t.avg_end_to_end_ms)}`} accent="var(--agent-validate)" icon={<Clock />} />
        <Stat label="Success rate" value={pct(t.success_rate)} hint="of closed workflows" accent="var(--agent-plan)" icon={<Gauge />} />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.6fr_1fr]">
        <Panel title="Processing activity" subtitle="Last 14 days · includes seeded demo history (illustrative)">
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={o.activity} margin={{ left: -20, right: 8, top: 8 }}>
                <defs>
                  <linearGradient id="g1" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#16B8A6" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="#16B8A6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="var(--border)" vertical={false} />
                <XAxis dataKey="date" tickFormatter={(d) => d.slice(5)} tick={{ fontSize: 11, fill: "var(--ink-3)" }} axisLine={false} tickLine={false} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: "var(--ink-3)" }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 10, fontSize: 12 }} />
                <Area type="monotone" dataKey="processed" name="Processed" stroke="#16B8A6" strokeWidth={2.5} fill="url(#g1)" />
                <Area type="monotone" dataKey="completed" name="Completed" stroke="#12B76A" strokeWidth={1.5} fill="transparent" />
                <Area type="monotone" dataKey="exceptions" name="Exceptions" stroke="#F04438" strokeWidth={1.5} strokeDasharray="4 4" fill="transparent" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Panel>

        <Panel title="Agent execution status" subtitle="Live from agent_executions" action={<Activity className="size-4 text-ink-3" />}>
          <ul className="space-y-3">
            {(agents ?? []).map((a) => {
              const meta = AGENTS[a.agent];
              const running = (a.counts.running ?? 0) + (a.counts.waiting ?? 0);
              return (
                <li key={a.agent} className="flex items-center gap-3">
                  <span className="grid size-9 place-items-center rounded-lg text-[11px] font-bold text-white" style={{ background: meta.color }}>
                    {meta.short}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-semibold text-ink">{meta.label}</p>
                    <p className="truncate text-xs text-ink-3">
                      {a.engine} · avg {duration(a.avg_duration_ms)} · {a.counts.completed ?? 0} runs
                    </p>
                  </div>
                  {running ? (
                    <StatusPill status={a.counts.waiting ? "waiting" : "running"}>{a.counts.waiting ? `${a.counts.waiting} waiting` : "Running"}</StatusPill>
                  ) : (
                    <StatusPill tone="neutral">Idle</StatusPill>
                  )}
                </li>
              );
            })}
          </ul>
        </Panel>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Panel title="Pending approvals" action={<Link href="/approvals" className="text-xs font-semibold text-teal">Open queue →</Link>} bodyClass="p-0">
          {o.pending_preview.length === 0 ? (
            <Empty icon={<ShieldCheck />} title="Queue is clear">Nothing needs a human right now.</Empty>
          ) : (
            <ul className="divide-y divide-line">
              {o.pending_preview.map((p) => (
                <li key={p.id}>
                  <Link href={`/approvals?focus=${p.id}`} className="block px-5 py-3.5 hover:bg-surface-2">
                    <div className="flex items-center justify-between gap-2">
                      <p className="truncate text-sm font-semibold text-ink">{p.filename}</p>
                      <StatusPill status={p.priority === "urgent" || p.priority === "high" ? "failed" : "pending"}>{p.priority}</StatusPill>
                    </div>
                    <p className="mt-1 line-clamp-2 text-xs text-ink-2">{p.reasons[0]}</p>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <Panel title="Recent documents" action={<Link href="/documents" className="text-xs font-semibold text-teal">All →</Link>} bodyClass="p-0">
          {o.recent_documents.length === 0 ? (
            <Empty icon={<FileStack />} title="No documents yet" />
          ) : (
            <ul className="divide-y divide-line">
              {o.recent_documents.map((d) => (
                <li key={d.id} className="flex items-center gap-3 px-5 py-3">
                  <FileStack className="size-4 shrink-0 text-ink-3" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-ink">{d.filename}</p>
                    <p className="text-xs text-ink-3">
                      {d.type_label ?? "Not processed"} · {ago(d.created_at)}
                    </p>
                  </div>
                  <StatusPill status={d.latest_workflow?.status ?? d.status} />
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <Panel title="Recent audit events" action={<Link href="/audit" className="text-xs font-semibold text-teal">Trace →</Link>} bodyClass="p-0">
          <ol className="divide-y divide-line">
            {o.recent_audit.map((e) => (
              <li key={e.id} className="px-5 py-3">
                <div className="flex items-center justify-between gap-2">
                  <span className="hash font-semibold text-ink">{e.event_type}</span>
                  <span className="text-[11px] text-ink-3">{ago(e.timestamp)}</span>
                </div>
                <p className="mt-0.5 line-clamp-1 text-xs text-ink-2">{e.description}</p>
                <p className="hash mt-0.5 text-ink-3">#{e.sequence} · {shortHash(e.hash, 8)}</p>
              </li>
            ))}
          </ol>
        </Panel>
      </div>
    </div>
  );
}

function DashSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-10 w-96" />
      <div className="grid grid-cols-2 gap-4 xl:grid-cols-6">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-32" />
        ))}
      </div>
      <Skeleton className="h-80" />
    </div>
  );
}
