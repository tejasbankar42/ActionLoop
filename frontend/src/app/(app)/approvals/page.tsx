"use client";

import { Check, Inbox, MessageSquareWarning, ShieldCheck, X } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { Button, Empty, Panel, StatusPill, Textarea } from "@/components/ui/primitives";
import { useToast } from "@/components/ui/toast";
import { DocPreview, FieldTable, StageTrack, ValidationList } from "@/components/workflow/parts";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { ago, cn } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import type { Approval, WorkflowDetail } from "@/lib/types";

type Pending = Approval & { workflow: WorkflowDetail };
type Decided = Approval & { filename: string };

function ApprovalsInner() {
  const params = useSearchParams();
  const toast = useToast();
  const { can, user } = useAuth();
  const { data: pending, reload } = useApi<Pending[]>("/api/approvals/pending", 4000);
  const { data: history, reload: reloadHistory } = useApi<Decided[]>("/api/approvals/history", 6000);
  const [focus, setFocus] = useState<string | null>(params.get("focus"));
  const [comment, setComment] = useState("");
  const [corrections, setCorrections] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    if (pending && (!focus || !pending.some((p) => p.id === focus))) setFocus(pending[0]?.id ?? null);
  }, [pending, focus]);
  useEffect(() => {
    setComment("");
    setCorrections({});
  }, [focus]);

  const item = pending?.find((p) => p.id === focus) ?? null;
  const high = pending?.filter((p) => ["urgent", "high"].includes(p.priority)).length ?? 0;
  const reviewer = can("reviewer");

  async function decide(decision: "approve" | "reject" | "request_correction") {
    if (!item) return;
    if (decision !== "approve" && !comment.trim()) {
      toast("error", "Comment required", "Explain why you are rejecting or requesting a correction.");
      return;
    }
    setBusy(decision);
    try {
      const filled = Object.fromEntries(Object.entries(corrections).filter(([, v]) => v.trim()));
      await api(`/api/approvals/${item.id}/decision`, {
        method: "POST",
        body: JSON.stringify({ decision, comment: comment.trim() || null, corrections: Object.keys(filled).length ? filled : null }),
      });
      toast("success", decision === "approve" ? "Approved" : decision === "reject" ? "Rejected" : "Correction requested",
        "Workflow resumed. The decision is recorded in the audit chain and queued for MST anchoring.");
      await Promise.all([reload(), reloadHistory()]);
    } catch (e) {
      toast("error", "Decision failed", (e as Error).message);
    } finally {
      setBusy(null);
    }
  }

  const wf = item?.workflow;
  const needsInput = wf?.fields.filter((f) => f.status !== "ok") ?? [];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <Kpi label="Pending" value={pending?.length ?? "—"} tone="var(--warn)" />
        <Kpi label="High priority" value={high} tone="var(--bad)" />
        <Kpi label="Decided (live)" value={history?.length ?? "—"} tone="var(--ok)" />
        <Kpi label="You are" value={user?.role ?? "—"} tone="var(--agent-human)" small />
      </div>

      <div className="grid gap-6 xl:grid-cols-[340px_1fr]">
        <Panel title="Queue" subtitle="Sorted by priority, then age" bodyClass="p-2">
          {!pending?.length ? (
            <Empty icon={<Inbox />} title="Nothing to review">New items appear when an agent needs a human.</Empty>
          ) : (
            <ul className="space-y-1">
              {pending.map((p) => (
                <li key={p.id}>
                  <button
                    onClick={() => setFocus(p.id)}
                    className={cn("w-full rounded-lg px-3 py-3 text-left", focus === p.id ? "bg-teal/10 ring-1 ring-teal/30" : "hover:bg-surface-2")}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate text-sm font-semibold text-ink">{p.workflow.document.filename}</span>
                      <span className={cn("rounded px-1.5 py-0.5 text-[10px] font-bold uppercase",
                        p.priority === "urgent" ? "bg-bad text-white" : p.priority === "high" ? "bg-warn text-white" : "bg-surface-2 text-ink-2")}>
                        {p.priority}
                      </span>
                    </div>
                    <p className="mt-1 line-clamp-2 text-xs text-ink-2">{p.reasons.join(" · ")}</p>
                    <p className="mt-1 text-[11px] text-ink-3">{p.workflow.type_label ?? "Unclassified"} · {ago(p.created_at)}</p>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Panel>

        {!item || !wf ? (
          <Panel><Empty icon={<ShieldCheck />} title="Select an item from the queue" /></Panel>
        ) : (
          <div className="min-w-0 space-y-6">
            <Panel title={wf.document.filename} subtitle={`${wf.type_label ?? "Unclassified"} · validation ${wf.validation_status ?? "—"}`} action={<StatusPill status="awaiting_approval" />}>
              <StageTrack wf={wf} />
              <div className="mt-5 rounded-xl border border-warn/40 bg-warn/10 p-4">
                <p className="flex items-center gap-2 text-sm font-bold text-ink"><MessageSquareWarning className="size-4 text-warn" /> Why this needs you</p>
                <ul className="mt-2 list-disc space-y-1 pl-6 text-sm text-ink-2">
                  {item.reasons.map((r) => <li key={r}>{r}</li>)}
                </ul>
              </div>
            </Panel>

            <div className="grid gap-6 2xl:grid-cols-2">
              <Panel title="Extracted information" subtitle={needsInput.length ? "Highlighted fields can be corrected before approving" : "All fields extracted with confidence"}>
                <FieldTable fields={wf.fields} editable={reviewer} values={corrections} onChange={(n, v) => setCorrections((c) => ({ ...c, [n]: v }))} />
              </Panel>
              <Panel title="Original document" bodyClass="p-3">
                <DocPreview doc={wf.document} className="h-[380px]" />
              </Panel>
            </div>

            <div className="grid gap-6 2xl:grid-cols-2">
              <Panel title="Validation results"><ValidationList items={wf.validations} /></Panel>
              <Panel title="AI recommendations" bodyClass="p-0">
                <ol className="divide-y divide-line">
                  {wf.actions.map((a) => (
                    <li key={a.id} className="px-5 py-3.5">
                      <p className="text-sm font-semibold text-ink">{a.step}. {a.title}</p>
                      <p className="mt-0.5 text-xs text-ink-3">{a.department} · {a.priority} priority · {a.impact} impact</p>
                      <p className="mt-1.5 text-sm text-ink-2">{a.reasoning}</p>
                    </li>
                  ))}
                </ol>
              </Panel>
            </div>

            <Panel title="Your decision" subtitle="Execution is simulated in this prototype; no external system is called.">
              {!reviewer ? (
                <p className="text-sm text-ink-2">Sign in as a reviewer or admin to decide. (Demo: reviewer@actionloop.demo)</p>
              ) : (
                <>
                  <Textarea rows={3} placeholder="Reviewer comment (required for reject / request correction)" value={comment} onChange={(e) => setComment(e.target.value)} />
                  {Object.values(corrections).some((v) => v.trim()) && (
                    <p className="mt-2 text-xs text-ink-2">Corrected values will be re-validated before any action executes.</p>
                  )}
                  <div className="mt-4 flex flex-wrap gap-2">
                    <Button onClick={() => decide("approve")} loading={busy === "approve"} disabled={!!busy}>
                      <Check /> {Object.values(corrections).some((v) => v.trim()) ? "Approve with corrections" : "Approve"}
                    </Button>
                    <Button variant="outline" onClick={() => decide("request_correction")} loading={busy === "request_correction"} disabled={!!busy}>
                      <MessageSquareWarning /> Request correction
                    </Button>
                    <Button variant="danger" onClick={() => decide("reject")} loading={busy === "reject"} disabled={!!busy}>
                      <X /> Reject
                    </Button>
                  </div>
                </>
              )}
            </Panel>
          </div>
        )}
      </div>

      <Panel title="Decision history" subtitle="Live decisions (seeded history excluded)" bodyClass="p-0">
        {!history?.length ? (
          <Empty title="No decisions yet" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-sm">
              <thead className="text-left text-xs uppercase tracking-wider text-ink-3">
                <tr className="border-b border-line"><th className="px-5 py-2.5">Document</th><th>Decision</th><th>Reviewer</th><th>Comment</th><th className="pr-5">When</th></tr>
              </thead>
              <tbody className="divide-y divide-line">
                {history.map((h) => (
                  <tr key={h.id}>
                    <td className="px-5 py-3 font-medium text-ink">{h.filename}</td>
                    <td><StatusPill status={h.status} /></td>
                    <td className="text-ink-2">{h.reviewer_name}</td>
                    <td className="max-w-xs truncate text-ink-2">{h.comment ?? "—"}</td>
                    <td className="pr-5 text-ink-3">{ago(h.decided_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </div>
  );
}

function Kpi({ label, value, tone, small }: { label: string; value: React.ReactNode; tone: string; small?: boolean }) {
  return (
    <div className="rounded-[var(--radius-card)] border border-line bg-surface p-4">
      <p className="text-xs font-semibold uppercase tracking-wider text-ink-3">{label}</p>
      <p className={cn("mt-1 font-extrabold capitalize", small ? "text-xl" : "text-3xl")} style={{ color: tone }}>{value}</p>
    </div>
  );
}

export default function ApprovalsPage() {
  return (
    <Suspense>
      <ApprovalsInner />
    </Suspense>
  );
}
