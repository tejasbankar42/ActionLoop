"use client";

import { ExternalLink, History, RotateCw, Timer, Wrench } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";
import { Button, Empty, Panel, StatusPill } from "@/components/ui/primitives";
import { useToast } from "@/components/ui/toast";
import { FlowGraph, nodeStatuses } from "@/components/workflow/flow-graph";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { AGENTS, ago, cn, dateTime, duration, shortHash } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import type { Anchor, WorkflowDetail, WorkflowSummary } from "@/lib/types";

function StudioInner() {
  const params = useSearchParams();
  const router = useRouter();
  const toast = useToast();
  const { can } = useAuth();
  const { data: list } = useApi<WorkflowSummary[]>("/api/workflows?limit=40", 3000);
  const [wfId, setWfId] = useState<string | null>(params.get("wf"));
  const [node, setNode] = useState<string | null>("extractor");
  const [retrying, setRetrying] = useState(false);

  useEffect(() => {
    if (!wfId && list?.length) setWfId(list[0].id);
  }, [list, wfId]);
  const summary = list?.find((w) => w.id === wfId);
  const active = summary ? ["queued", "running"].includes(summary.status) : false;
  const { data: wf } = useApi<WorkflowDetail>(wfId ? `/api/workflows/${wfId}` : null, active ? 600 : 3000);
  const { data: anchors } = useApi<Anchor[]>("/api/blockchain/anchors?limit=200", 4000);
  const statuses = useMemo(() => nodeStatuses(wf, anchors ?? []), [wf, anchors]);

  async function retry() {
    if (!wf) return;
    setRetrying(true);
    try {
      const n = await api<WorkflowSummary>(`/api/workflows/${wf.id}/retry`, { method: "POST" });
      toast("success", "Retry started", "A new workflow run was created.");
      setWfId(n.id);
      router.replace(`/studio?wf=${n.id}`);
    } catch (e) {
      toast("error", "Retry failed", (e as Error).message);
    } finally {
      setRetrying(false);
    }
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[280px_1fr]">
      <Panel title="Execution history" subtitle="Live and recent runs" bodyClass="p-2 max-h-[calc(100vh-200px)] overflow-y-auto">
        {!list?.length ? (
          <Empty icon={<History />} title="No runs yet">
            Start one from <Link href="/documents" className="text-teal">Documents</Link>.
          </Empty>
        ) : (
          <ul className="space-y-0.5">
            {list.map((w) => (
              <li key={w.id}>
                <button
                  onClick={() => {
                    setWfId(w.id);
                    router.replace(`/studio?wf=${w.id}`);
                  }}
                  className={cn("w-full rounded-lg px-3 py-2.5 text-left", wfId === w.id ? "bg-teal/10 ring-1 ring-teal/30" : "hover:bg-surface-2")}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate text-[13px] font-semibold text-ink">{w.filename}</span>
                  </div>
                  <div className="mt-1 flex items-center justify-between gap-2">
                    <StatusPill status={w.status} />
                    <span className="text-[11px] text-ink-3">{ago(w.created_at)}</span>
                  </div>
                </button>
              </li>
            ))}
          </ul>
        )}
      </Panel>

      <div className="min-w-0 space-y-6">
        <section className="overflow-hidden rounded-[var(--radius-card)] border border-line bg-surface">
          <header className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-5 py-3.5">
            <div className="min-w-0">
              <p className="truncate text-[15px] font-bold text-ink">{wf?.document.filename ?? "Workflow graph"}</p>
              <p className="hash text-ink-3">
                {wf ? `workflow ${shortHash(wf.id, 8)} · ${wf.type_label ?? "unclassified"} · started ${dateTime(wf.created_at)}` : "LangGraph topology"}
              </p>
            </div>
            <div className="flex items-center gap-2">
              {wf && <StatusPill status={wf.status} />}
              {wf?.status === "failed" && can("operator") && (
                <Button size="sm" variant="outline" onClick={retry} loading={retrying}>
                  <RotateCw /> Retry
                </Button>
              )}
              {wf?.status === "awaiting_approval" && (
                <Button size="sm" asChild>
                  <Link href={`/approvals?focus=${wf.approvals.at(-1)?.id}`}>Review</Link>
                </Button>
              )}
            </div>
          </header>
          <div className="h-[460px] bg-canvas">
            <FlowGraph statuses={statuses} selected={node} onSelect={setNode} />
          </div>
          <div className="flex flex-wrap gap-4 border-t border-line px-5 py-2.5 text-[11px] text-ink-3">
            {[
              ["Running", "var(--agent-human)"],
              ["Completed", "var(--ok)"],
              ["Waiting for approval", "var(--warn)"],
              ["Failed", "var(--bad)"],
              ["Idle / not required", "var(--border)"],
            ].map(([l, c]) => (
              <span key={l} className="inline-flex items-center gap-1.5">
                <span className="size-2 rounded-full" style={{ background: c }} /> {l}
              </span>
            ))}
            <span className="ml-auto">Click any node for its execution details</span>
          </div>
        </section>

        {wf && node && <NodeDetail wf={wf} node={node} anchors={(anchors ?? []).filter((a) => a.workflow_id === wf.id)} />}
      </div>
    </div>
  );
}

function NodeDetail({ wf, node, anchors }: { wf: WorkflowDetail; node: string; anchors: Anchor[] }) {
  const runs = wf.executions.filter((e) => e.agent === node);
  const meta = AGENTS[node] ?? { label: "MST Blockchain", color: "#16B8A6" };

  if (node === "mst") {
    return (
      <Panel title="MST Blockchain anchoring" subtitle="Event hashes from this workflow submitted to the ActionLoop Audit Registry">
        {anchors.length === 0 ? (
          <Empty title="No anchor-eligible events yet">Approval decisions and workflow outcomes are anchored automatically.</Empty>
        ) : (
          <ul className="divide-y divide-line">
            {anchors.map((a) => (
              <li key={a.id} className="flex flex-wrap items-center gap-3 py-3">
                <span className="hash font-semibold text-ink">{a.event_type}</span>
                <StatusPill status={a.status} />
                <span className="hash text-ink-3">{shortHash(a.event_hash, 8)}</span>
                {a.tx_explorer_url && (
                  <a href={a.tx_explorer_url} target="_blank" rel="noreferrer" className="ml-auto inline-flex items-center gap-1 text-xs font-semibold text-teal">
                    MSTScan <ExternalLink className="size-3" />
                  </a>
                )}
              </li>
            ))}
          </ul>
        )}
      </Panel>
    );
  }
  if (node === "document_input" || node === "audit") {
    return (
      <Panel title={meta.label}>
        {node === "document_input" ? (
          <dl className="grid gap-3 text-sm sm:grid-cols-2">
            <div><dt className="text-xs text-ink-3">File</dt><dd className="font-medium text-ink">{wf.document.filename}</dd></div>
            <div><dt className="text-xs text-ink-3">SHA-256</dt><dd className="hash text-ink">{shortHash(wf.document.sha256, 12)}</dd></div>
            <div><dt className="text-xs text-ink-3">Content type</dt><dd className="text-ink">{wf.document.content_type}</dd></div>
            <div><dt className="text-xs text-ink-3">Detected type</dt><dd className="text-ink">{wf.type_label ?? "—"}</dd></div>
          </dl>
        ) : (
          <p className="text-sm text-ink-2">
            Every transition above wrote a hash-chained audit event.{" "}
            <Link href={`/audit?workflow=${wf.id}`} className="font-semibold text-teal">View this workflow&apos;s trail →</Link>
          </p>
        )}
      </Panel>
    );
  }

  return (
    <Panel
      title={
        <span className="flex items-center gap-2">
          <span className="size-2.5 rounded-full" style={{ background: meta.color }} /> {meta.label}
        </span>
      }
      subtitle={runs.length ? `${runs.length} execution${runs.length > 1 ? "s" : ""} for this workflow` : "Not executed in this workflow"}
    >
      {runs.length === 0 ? (
        <Empty icon={<Wrench />} title="No execution recorded">
          {node === "human_approval" ? "This workflow did not require a human decision." : "The workflow has not reached this agent."}
        </Empty>
      ) : (
        <div className="space-y-5">
          {runs.map((r) => (
            <div key={r.id} className="rounded-xl border border-line">
              <div className="flex flex-wrap items-center gap-3 border-b border-line px-4 py-2.5">
                <StatusPill status={r.status} />
                <span className="text-xs text-ink-3">attempt {r.attempt}</span>
                <span className="inline-flex items-center gap-1 text-xs text-ink-3">
                  <Timer className="size-3.5" /> {duration(r.duration_ms)}
                </span>
                <span className="hash ml-auto text-ink-3">{r.engine}</span>
              </div>
              <div className="grid gap-4 p-4 lg:grid-cols-[1fr_1.4fr]">
                <div>
                  <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-ink-3">Explanation</p>
                  <p className="text-sm text-ink">{r.explanation || "—"}</p>
                  {r.error && <p className="mt-3 rounded-lg bg-bad/10 px-3 py-2 text-sm text-bad">{r.error}</p>}
                  <p className="mb-1 mt-4 text-xs font-semibold uppercase tracking-wider text-ink-3">Input</p>
                  <pre className="hash max-h-40 overflow-auto rounded-lg bg-surface-2 p-3 text-ink-2">{JSON.stringify(r.input, null, 2)}</pre>
                </div>
                <div>
                  <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-ink-3">Output</p>
                  <pre className="hash max-h-72 overflow-auto rounded-lg bg-navy p-3 text-[#D0D5DD]">{JSON.stringify(r.output, null, 2)}</pre>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}

export default function StudioPage() {
  return (
    <Suspense>
      <StudioInner />
    </Suspense>
  );
}
