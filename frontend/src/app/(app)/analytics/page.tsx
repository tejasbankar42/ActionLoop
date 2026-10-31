"use client";

import { Download, FlaskConical, Info } from "lucide-react";
import { useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Button, Input, Panel, Skeleton } from "@/components/ui/primitives";
import { useToast } from "@/components/ui/toast";
import { download } from "@/lib/api";
import { AGENTS, duration, pct } from "@/lib/format";
import { useApi } from "@/lib/hooks";

interface Report {
  range: { from: string; to: string };
  workflows: number;
  seeded_workflows: number;
  daily: { date: string; documents: number; completed: number; avg_end_to_end_s: number | null; avg_automated_s: number | null }[];
  rates: { completion_rate: number; validation_failure_rate: number; human_intervention_rate: number; failure_rate: number; approval_rate: number | null };
  by_type: Record<string, number>;
  agents: { agent: string; runs: number; completed: number; failed: number; avg_ms: number | null }[];
  extraction_accuracy: { available: boolean; engine?: string; samples?: number; fields?: number; correct?: number; accuracy?: number; note?: string; per_document?: { file: string; fields: number; correct: number }[] };
}

const iso = (d: Date) => d.toISOString().slice(0, 10);
const tip = { background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 10, fontSize: 12 };

export default function AnalyticsPage() {
  const toast = useToast();
  const today = new Date();
  const [from, setFrom] = useState(iso(new Date(today.getTime() - 29 * 86400000)));
  const [to, setTo] = useState(iso(today));
  const qs = useMemo(() => `from=${from}&to=${to}`, [from, to]);
  const { data: r, error } = useApi<Report>(`/api/analytics/reports?${qs}`, 10000);

  const presets: [string, number][] = [["7d", 6], ["30d", 29], ["90d", 89]];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex flex-wrap items-end gap-3">
          <label className="text-xs font-semibold text-ink-2">From<Input type="date" value={from} max={to} onChange={(e) => setFrom(e.target.value)} className="mt-1 w-40" /></label>
          <label className="text-xs font-semibold text-ink-2">To<Input type="date" value={to} min={from} onChange={(e) => setTo(e.target.value)} className="mt-1 w-40" /></label>
          <div className="flex rounded-lg border border-line p-0.5">
            {presets.map(([l, d]) => (
              <button key={l} onClick={() => { setFrom(iso(new Date(Date.now() - d * 86400000))); setTo(iso(new Date())); }} className="rounded-md px-3 py-1.5 text-xs font-semibold text-ink-2 hover:bg-surface-2">{l}</button>
            ))}
          </div>
        </div>
        <Button variant="outline" onClick={() => download(`/api/analytics/reports.csv?${qs}`, `actionloop-report-${from}-${to}.csv`).catch((e) => toast("error", "Export failed", e.message))}>
          <Download /> Export CSV
        </Button>
      </div>

      {error && <p className="rounded-lg bg-bad/10 px-4 py-3 text-sm text-bad">{error}</p>}
      {!r ? (
        <Skeleton className="h-96" />
      ) : (
        <>
          <p className="flex items-center gap-2 text-xs text-ink-3">
            <Info className="size-3.5" /> {r.workflows} workflows in range, of which {r.seeded_workflows} are seeded demo history (illustrative, not real performance claims).
          </p>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
            {[
              ["Completion rate", pct(r.rates.completion_rate), "var(--ok)"],
              ["Validation failure rate", pct(r.rates.validation_failure_rate), "var(--bad)"],
              ["Approval rate", pct(r.rates.approval_rate), "var(--agent-human)"],
              ["Human intervention", pct(r.rates.human_intervention_rate), "var(--warn)"],
              ["Extraction accuracy*", pct(r.extraction_accuracy.accuracy, 1), "var(--teal)"],
            ].map(([l, v, c]) => (
              <div key={l} className="rounded-[var(--radius-card)] border border-line bg-surface p-5">
                <p className="text-xs font-semibold uppercase tracking-wider text-ink-3">{l}</p>
                <p className="mt-2 text-3xl font-extrabold" style={{ color: c }}>{v}</p>
              </div>
            ))}
          </div>

          <div className="grid gap-6 xl:grid-cols-2">
            <Panel title="Documents processed over time">
              <div className="h-64">
                <ResponsiveContainer>
                  <BarChart data={r.daily} margin={{ left: -20, right: 8 }}>
                    <CartesianGrid stroke="var(--border)" vertical={false} />
                    <XAxis dataKey="date" tickFormatter={(d) => d.slice(5)} tick={{ fontSize: 11, fill: "var(--ink-3)" }} axisLine={false} tickLine={false} />
                    <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: "var(--ink-3)" }} axisLine={false} tickLine={false} />
                    <Tooltip contentStyle={tip} cursor={{ fill: "var(--surface-2)" }} />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <Bar dataKey="documents" name="Documents" fill="#182438" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="completed" name="Completed" fill="#16B8A6" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Panel>
            <Panel title="Average processing duration" subtitle="Agent time vs end-to-end (includes human wait)">
              <div className="h-64">
                <ResponsiveContainer>
                  <LineChart data={r.daily} margin={{ left: -10, right: 8 }}>
                    <CartesianGrid stroke="var(--border)" vertical={false} />
                    <XAxis dataKey="date" tickFormatter={(d) => d.slice(5)} tick={{ fontSize: 11, fill: "var(--ink-3)" }} axisLine={false} tickLine={false} />
                    <YAxis yAxisId="a" tick={{ fontSize: 11, fill: "var(--ink-3)" }} axisLine={false} tickLine={false} unit="s" />
                    <YAxis yAxisId="b" orientation="right" tick={{ fontSize: 11, fill: "var(--ink-3)" }} axisLine={false} tickLine={false} unit="s" />
                    <Tooltip contentStyle={tip} />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <Line yAxisId="a" type="monotone" dataKey="avg_automated_s" name="Agents (s)" stroke="#6172F3" strokeWidth={2.5} dot={false} connectNulls />
                    <Line yAxisId="b" type="monotone" dataKey="avg_end_to_end_s" name="End-to-end (s)" stroke="#F79009" strokeWidth={1.5} strokeDasharray="4 4" dot={false} connectNulls />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </Panel>
          </div>

          <div className="grid gap-6 xl:grid-cols-[1.3fr_1fr]">
            <Panel title="Agent-level performance" bodyClass="p-0">
              <table className="w-full text-sm">
                <thead className="text-left text-[11px] uppercase tracking-wider text-ink-3">
                  <tr className="border-b border-line"><th className="px-5 py-2.5">Agent</th><th>Runs</th><th>Completed</th><th>Failed</th><th className="pr-5">Avg duration</th></tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {r.agents.map((a) => (
                    <tr key={a.agent}>
                      <td className="px-5 py-3 font-semibold text-ink"><span className="mr-2 inline-block size-2 rounded-full" style={{ background: AGENTS[a.agent].color }} />{AGENTS[a.agent].label}</td>
                      <td className="tabular-nums text-ink-2">{a.runs}</td>
                      <td className="tabular-nums text-ink-2">{a.completed}</td>
                      <td className="tabular-nums text-ink-2">{a.failed}</td>
                      <td className="pr-5 tabular-nums text-ink-2">{duration(a.avg_ms)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Panel>
            <Panel title="Extraction accuracy (labelled samples)" action={<FlaskConical className="size-4 text-ink-3" />}>
              {r.extraction_accuracy.available ? (
                <>
                  <p className="text-sm text-ink-2">
                    <b className="text-ink">{r.extraction_accuracy.correct}/{r.extraction_accuracy.fields}</b> labelled fields correct across {r.extraction_accuracy.samples} sample documents using <code className="hash">{r.extraction_accuracy.engine}</code>.
                  </p>
                  <ul className="mt-3 space-y-1.5">
                    {r.extraction_accuracy.per_document?.map((d) => (
                      <li key={d.file} className="flex items-center justify-between gap-3 text-xs">
                        <span className="truncate text-ink-2">{d.file}</span>
                        <span className="tabular-nums font-semibold text-ink">{d.correct}/{d.fields}</span>
                      </li>
                    ))}
                  </ul>
                  <p className="mt-3 text-[11px] text-ink-3">* {r.extraction_accuracy.note}</p>
                </>
              ) : (
                <p className="text-sm text-ink-3">Ground-truth file not found.</p>
              )}
            </Panel>
          </div>
        </>
      )}
    </div>
  );
}
