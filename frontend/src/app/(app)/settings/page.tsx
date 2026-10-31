"use client";

import { Bot, Building2, Cpu, Database, KeyRound, Link2, Moon, Sun, User } from "lucide-react";
import { useEffect, useState } from "react";
import { Panel, StatusPill } from "@/components/ui/primitives";
import { useToast } from "@/components/ui/toast";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { cn, shortHash } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import type { SystemStatus } from "@/lib/types";

interface Rule {
  id: string;
  code: string;
  document_type: string;
  rule_type: string;
  field: string | null;
  params: Record<string, unknown>;
  severity: "failed" | "warning";
  description: string;
  enabled: boolean;
}

export default function SettingsPage() {
  const { user, can } = useAuth();
  const toast = useToast();
  const { data: sys } = useApi<SystemStatus>("/api/system/status");
  const { data: rules, setData: setRules } = useApi<Rule[]>("/api/settings/rules");
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const [docType, setDocType] = useState("invoice");

  useEffect(() => setTheme(document.documentElement.classList.contains("dark") ? "dark" : "light"), []);
  function applyTheme(t: "light" | "dark") {
    setTheme(t);
    document.documentElement.classList.toggle("dark", t === "dark");
    try {
      localStorage.setItem("al-theme", t);
    } catch {
      /* ignore */
    }
  }

  async function updateRule(r: Rule, patch: Partial<Pick<Rule, "enabled" | "severity">>) {
    try {
      await api(`/api/settings/rules/${r.id}`, { method: "PATCH", body: JSON.stringify(patch) });
      setRules((rs) => rs?.map((x) => (x.id === r.id ? { ...x, ...patch } : x)) ?? null);
      toast("success", `Rule ${r.code} updated`, "Applies to the next validation run. Change recorded in the audit log.");
    } catch (e) {
      toast("error", "Update failed", (e as Error).message);
    }
  }

  const types = [...new Set(rules?.map((r) => r.document_type) ?? [])];

  return (
    <div className="grid gap-6 xl:grid-cols-[1fr_1.5fr]">
      <div className="space-y-6">
        <Panel title="User profile" action={<User className="size-4 text-ink-3" />}>
          <dl className="grid grid-cols-[120px_1fr] gap-y-2 text-sm">
            <dt className="text-ink-3">Name</dt><dd className="font-semibold text-ink">{user?.full_name}</dd>
            <dt className="text-ink-3">Email</dt><dd className="text-ink">{user?.email}</dd>
            <dt className="text-ink-3">Role</dt><dd><StatusPill tone="info">{user?.role}</StatusPill></dd>
            <dt className="text-ink-3">Department</dt><dd className="text-ink">{user?.department}</dd>
          </dl>
        </Panel>
        <Panel title="Organization" action={<Building2 className="size-4 text-ink-3" />}>
          <p className="font-semibold text-ink">{user?.organization}</p>
          <p className="text-sm text-ink-3">Talegaon Dabhade, Pune · Education</p>
        </Panel>
        <Panel title="Theme">
          <div className="flex gap-2">
            {(["light", "dark"] as const).map((t) => (
              <button key={t} onClick={() => applyTheme(t)} className={cn("flex flex-1 items-center justify-center gap-2 rounded-lg border py-3 text-sm font-semibold capitalize", theme === t ? "border-teal bg-teal/10 text-ink" : "border-line text-ink-2")}>
                {t === "light" ? <Sun className="size-4" /> : <Moon className="size-4" />} {t}
              </button>
            ))}
          </div>
        </Panel>
        <Panel title="Integration status" subtitle="Reported by the backend; no secrets are sent to the browser">
          <ul className="space-y-3 text-sm">
            <Row icon={<Cpu />} label="AI extraction" value={sys?.llm.configured ? `${sys.llm.provider} · ${sys.llm.model}` : "DEMO MODE — deterministic PDF parser"} ok={!!sys?.llm.configured} />
            <Row icon={<Database />} label="Database" value={sys?.database ?? "—"} ok={sys?.database === "postgresql"} okText="PostgreSQL" warnText="SQLite (local dev)" />
            <Row icon={<Bot />} label="Action execution" value="Simulated — no external systems are called" ok={false} warnText="Simulated" />
            <Row icon={<Link2 />} label="MST Blockchain" value={sys?.blockchain.contract_address ? `${sys.blockchain.network} · ${shortHash(sys.blockchain.contract_address, 6)}` : `${sys?.blockchain.network ?? ""} · registry not deployed`} ok={!!sys?.blockchain.contract_address} />
            <Row icon={<KeyRound />} label="Relayer signer" value={sys?.blockchain.relayer_address ? shortHash(sys.blockchain.relayer_address, 6) : "not configured"} ok={!!sys?.blockchain.relayer_address} />
          </ul>
        </Panel>
        <Panel title="Document processing preferences">
          <dl className="grid grid-cols-[1fr_auto] gap-y-2 text-sm">
            <dt className="text-ink-3">Low-confidence threshold</dt><dd className="font-semibold text-ink">{sys ? `${Math.round(sys.low_confidence_threshold * 100)}%` : "—"}</dd>
            <dt className="text-ink-3">Max upload size</dt><dd className="font-semibold text-ink">{sys?.max_upload_mb} MB</dd>
            <dt className="text-ink-3">Accepted types</dt><dd className="font-semibold text-ink">PDF · JPG · PNG</dd>
          </dl>
          <p className="mt-3 text-xs text-ink-3">Configured through backend environment variables (see .env.example).</p>
        </Panel>
      </div>

      <Panel
        title="Validation rules"
        subtitle={can("admin") ? "Toggle rules or change severity. Every change is audit-logged." : "Read-only — admin role required to edit."}
        bodyClass="p-0"
      >
        <div className="flex flex-wrap gap-1 border-b border-line px-4 py-3">
          {types.map((t) => (
            <button key={t} onClick={() => setDocType(t)} className={cn("rounded-full px-3 py-1 text-xs font-semibold", docType === t ? "bg-navy text-white dark:bg-teal" : "bg-surface-2 text-ink-2")}>
              {t === "*" ? "all types" : t.replace("_", " ")}
            </button>
          ))}
        </div>
        <ul className="divide-y divide-line">
          {rules?.filter((r) => r.document_type === docType).map((r) => (
            <li key={r.id} className={cn("flex flex-wrap items-center gap-3 px-5 py-3", !r.enabled && "opacity-55")}>
              <div className="min-w-0 flex-1">
                <p className="hash font-semibold text-ink">{r.code}</p>
                <p className="text-xs text-ink-2">
                  {r.rule_type}{r.field ? ` · ${r.field}` : ""}{Object.keys(r.params).length ? ` · ${JSON.stringify(r.params)}` : ""}
                </p>
              </div>
              <select
                disabled={!can("admin")}
                value={r.severity}
                onChange={(e) => updateRule(r, { severity: e.target.value as Rule["severity"] })}
                className="h-8 rounded-md border border-line bg-surface px-2 text-xs text-ink"
              >
                <option value="failed">fail</option>
                <option value="warning">warn</option>
              </select>
              <button
                disabled={!can("admin")}
                onClick={() => updateRule(r, { enabled: !r.enabled })}
                role="switch"
                aria-checked={r.enabled}
                className={cn("relative h-6 w-11 rounded-full transition-colors disabled:cursor-not-allowed", r.enabled ? "bg-teal" : "bg-line")}
              >
                <span className={cn("absolute top-0.5 size-5 rounded-full bg-white shadow transition-all", r.enabled ? "left-[22px]" : "left-0.5")} />
              </button>
            </li>
          ))}
        </ul>
      </Panel>
    </div>
  );
}

function Row({ icon, label, value, ok, okText = "Connected", warnText = "Not configured" }: { icon: React.ReactNode; label: string; value: string; ok: boolean; okText?: string; warnText?: string }) {
  return (
    <li className="flex items-start gap-3">
      <span className="mt-0.5 text-ink-3 [&_svg]:size-4">{icon}</span>
      <div className="min-w-0 flex-1">
        <p className="font-semibold text-ink">{label}</p>
        <p className="truncate text-xs text-ink-3">{value}</p>
      </div>
      <StatusPill status={ok ? "ok" : "warning"}>{ok ? okText : warnText}</StatusPill>
    </li>
  );
}
