"use client";

import { Download, FlaskConical, Link2, List, Search, ShieldCheck, ShieldX, Workflow } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";
import { EventVerify } from "@/components/audit/event-verify";
import { Dialog } from "@/components/ui/dialog";
import { Button, Empty, Input, Panel, StatusPill } from "@/components/ui/primitives";
import { useToast } from "@/components/ui/toast";
import { api, download } from "@/lib/api";
import { AGENTS, cn, dateTime, shortHash } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import type { AuditEvent } from "@/lib/types";

interface ChainResult {
  valid: boolean;
  checked: number;
  broken: { event_id: string; sequence: number; problems: string[]; stored_hash: string; recomputed_hash: string }[];
  genesis_hash: string;
  head_hash: string;
  verified_at: string;
  simulated_tamper: boolean;
}

function AuditInner() {
  const params = useSearchParams();
  const toast = useToast();
  const [search, setSearch] = useState("");
  const [q, setQ] = useState("");
  const [workflow, setWorkflow] = useState(params.get("workflow") ?? "");
  const [type, setType] = useState("");
  const [seeded, setSeeded] = useState(false);
  const [view, setView] = useState<"table" | "timeline">(params.get("workflow") ? "timeline" : "table");
  const [open, setOpen] = useState<string | null>(null);
  const [chain, setChain] = useState<ChainResult | null>(null);
  const [verifying, setVerifying] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setQ(search), 300);
    return () => clearTimeout(t);
  }, [search]);
  const qs = useMemo(() => {
    const p = new URLSearchParams({ limit: "200" });
    if (q) p.set("search", q);
    if (workflow) p.set("workflow_id", workflow);
    if (type) p.set("event_type", type);
    if (seeded) p.set("include_seeded", "true");
    return p.toString();
  }, [q, workflow, type, seeded]);
  const { data } = useApi<{ events: AuditEvent[]; total_in_chain: number; event_types: string[] }>(`/api/audit/events?${qs}`, 5000);

  async function verify(tamperId?: string) {
    setVerifying(true);
    try {
      const r = await api<ChainResult>("/api/audit/verify", { method: "POST", body: JSON.stringify(tamperId ? { simulate_tamper_event_id: tamperId } : {}) });
      setChain(r);
      toast(r.valid ? "success" : "error", r.valid ? "Hash chain valid" : "Tampering detected", `${r.checked} events recomputed${r.simulated_tamper ? " (simulation — database unchanged)" : ""}.`);
    } catch (e) {
      toast("error", "Verification failed", (e as Error).message);
    } finally {
      setVerifying(false);
    }
  }

  const events = data?.events ?? [];
  const tamperTarget = events.find((e) => !e.seeded && e.event_type === "APPROVAL_DECISION") ?? events[Math.min(3, events.length - 1)];

  return (
    <div className="space-y-6">
      <section className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <div className={cn("rounded-[var(--radius-card)] border p-5", !chain ? "border-line bg-surface" : chain.valid ? "border-ok/40 bg-ok/5" : "border-bad/40 bg-bad/5")}>
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-ink-3">Hash-chain verification</p>
              <p className="mt-2 flex items-center gap-2 text-2xl font-extrabold text-ink">
                {!chain ? <ShieldCheck className="size-6 text-ink-3" /> : chain.valid ? <ShieldCheck className="size-6 text-ok" /> : <ShieldX className="size-6 text-bad" />}
                {!chain ? "Not verified yet" : chain.valid ? "All records intact" : `${chain.broken.length} broken link${chain.broken.length > 1 ? "s" : ""}`}
              </p>
              <p className="mt-1 text-sm text-ink-2">
                <code className="hash">current_hash = SHA256(previous_hash + canonical_event)</code> · {data?.total_in_chain ?? "…"} events in chain
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button onClick={() => verify()} loading={verifying}><ShieldCheck /> Verify entire chain</Button>
              {tamperTarget && (
                <Button variant="outline" onClick={() => verify(tamperTarget.id)} disabled={verifying} title="Recomputes with an altered in-memory copy of one event. The database is not modified.">
                  <FlaskConical /> Simulate tampering
                </Button>
              )}
            </div>
          </div>
          {chain && (
            <div className="mt-4 grid gap-2 text-xs sm:grid-cols-2">
              <p><span className="text-ink-3">Genesis</span> <span className="hash text-ink-2">{shortHash(chain.genesis_hash, 8)}</span></p>
              <p><span className="text-ink-3">Head</span> <span className="hash text-ink-2">{shortHash(chain.head_hash, 10)}</span></p>
              {chain.broken.slice(0, 2).map((b) => (
                <p key={b.event_id} className="text-bad sm:col-span-2">
                  #{b.sequence}: {b.problems.join("; ")} — stored {shortHash(b.stored_hash, 6)} ≠ recomputed {shortHash(b.recomputed_hash, 6)}
                  {chain.simulated_tamper && " (simulated edit: description changed)"}
                </p>
              ))}
            </div>
          )}
        </div>
        <div className="rounded-[var(--radius-card)] border border-line bg-navy p-5 text-white">
          <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-[#98A2B3]">Two-layer proof</p>
          <ul className="mt-3 space-y-2 text-sm text-[#D0D5DD]">
            <li className="flex gap-2"><ShieldCheck className="mt-0.5 size-4 shrink-0 text-teal" /> Off-chain: full events in PostgreSQL, append-only, hash-chained.</li>
            <li className="flex gap-2"><Link2 className="mt-0.5 size-4 shrink-0 text-teal" /> On-chain: approval & outcome hashes anchored in the MST Audit Registry. Open any event to see both statuses.</li>
          </ul>
        </div>
      </section>

      <Panel
        title="Audit events"
        subtitle={`${events.length} shown`}
        action={
          <div className="flex flex-wrap gap-2">
            <div className="flex rounded-lg border border-line p-0.5">
              <button onClick={() => setView("table")} className={cn("rounded-md px-2.5 py-1 text-xs font-semibold", view === "table" ? "bg-navy text-white" : "text-ink-2")}><List className="inline size-3.5" /> Table</button>
              <button onClick={() => setView("timeline")} className={cn("rounded-md px-2.5 py-1 text-xs font-semibold", view === "timeline" ? "bg-navy text-white" : "text-ink-2")}><Workflow className="inline size-3.5" /> Timeline</button>
            </div>
            <Button size="sm" variant="outline" onClick={() => download(`/api/audit/export.csv?${qs}`, "actionloop-audit.csv").catch((e) => toast("error", "Export failed", e.message))}>
              <Download /> CSV
            </Button>
          </div>
        }
        bodyClass="p-0"
      >
        <div className="flex flex-wrap items-center gap-3 border-b border-line px-5 py-3">
          <div className="relative min-w-[220px] flex-1">
            <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-ink-3" />
            <Input className="pl-9" placeholder="Search description, actor, hash, IDs…" value={search} onChange={(e) => setSearch(e.target.value)} />
          </div>
          <select value={type} onChange={(e) => setType(e.target.value)} className="h-10 rounded-lg border border-line bg-surface px-3 text-sm text-ink">
            <option value="">All event types</option>
            {data?.event_types.map((t) => <option key={t}>{t}</option>)}
          </select>
          {workflow && (
            <button onClick={() => setWorkflow("")} className="rounded-full bg-teal/10 px-3 py-1 text-xs font-semibold text-teal-ink dark:text-teal">
              workflow {shortHash(workflow, 6)} ✕
            </button>
          )}
          <label className="flex items-center gap-2 text-xs text-ink-2">
            <input type="checkbox" checked={seeded} onChange={(e) => setSeeded(e.target.checked)} className="accent-teal" /> Include seeded history
          </label>
        </div>

        {events.length === 0 ? (
          <Empty title="No events match" />
        ) : view === "table" ? (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[1000px] text-sm">
              <thead className="text-left text-[11px] uppercase tracking-wider text-ink-3">
                <tr className="border-b border-line">
                  <th className="px-5 py-2.5">#</th><th>Timestamp</th><th>Event</th><th>User / Agent</th><th>Workflow</th><th>Hash</th><th>Prev hash</th><th className="pr-5">MST</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {events.map((e) => (
                  <tr key={e.id} onClick={() => setOpen(e.id)} className="cursor-pointer hover:bg-surface-2">
                    <td className="px-5 py-3 tabular-nums text-ink-3">{e.sequence}</td>
                    <td className="whitespace-nowrap text-ink-2">{dateTime(e.timestamp)}</td>
                    <td className="max-w-sm">
                      <p className="hash font-semibold text-ink">{e.event_type}</p>
                      <p className="truncate text-xs text-ink-2">{e.description}</p>
                    </td>
                    <td className="text-ink-2">
                      {e.actor}
                      {e.agent && <span className="block text-[11px]" style={{ color: AGENTS[e.agent]?.color }}>{AGENTS[e.agent]?.label ?? e.agent}</span>}
                    </td>
                    <td>
                      {e.workflow_id ? (
                        <button onClick={(ev) => { ev.stopPropagation(); setWorkflow(e.workflow_id!); setView("timeline"); }} className="hash text-teal hover:underline">
                          {shortHash(e.workflow_id, 4)}
                        </button>
                      ) : <span className="text-ink-3">—</span>}
                    </td>
                    <td className="hash text-ink">{shortHash(e.hash, 6)}</td>
                    <td className="hash text-ink-3">{shortHash(e.previous_hash, 6)}</td>
                    <td className="pr-5">{e.anchor ? <StatusPill status={e.anchor.status} /> : e.seeded ? <span className="text-[11px] text-ink-3">seeded</span> : <span className="text-[11px] text-ink-3">—</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <ol className="relative px-5 py-6">
            <span className="absolute bottom-6 left-[37px] top-6 w-px bg-line" />
            {[...events].reverse().map((e) => (
              <li key={e.id} className="relative flex gap-4 pb-5">
                <span className="z-10 mt-1 grid size-6 shrink-0 place-items-center rounded-full border-2 border-surface text-[9px] font-bold text-white" style={{ background: AGENTS[e.agent ?? ""]?.color ?? "var(--slate)" }}>
                  {e.sequence % 100}
                </span>
                <button onClick={() => setOpen(e.id)} className="min-w-0 flex-1 rounded-xl border border-line bg-surface p-3.5 text-left hover:border-teal">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="hash font-semibold text-ink">{e.event_type}</span>
                    <span className="text-xs text-ink-3">{dateTime(e.timestamp)} · {e.actor}</span>
                    {e.anchor && <StatusPill status={e.anchor.status} className="ml-auto" />}
                  </div>
                  <p className="mt-1 text-sm text-ink-2">{e.description}</p>
                  <p className="hash mt-1.5 text-ink-3">{shortHash(e.previous_hash, 6)} → {shortHash(e.hash, 6)}</p>
                </button>
              </li>
            ))}
          </ol>
        )}
      </Panel>

      <Dialog open={!!open} onOpenChange={(o) => !o && setOpen(null)} title="Audit event verification" description="Off-chain hash chain and on-chain MST record, checked independently." className="w-[min(760px,calc(100vw-2rem))]">
        {open && <EventVerify eventId={open} />}
      </Dialog>
    </div>
  );
}

export default function AuditPage() {
  return (
    <Suspense>
      <AuditInner />
    </Suspense>
  );
}
