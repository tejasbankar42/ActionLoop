import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function shortHash(h?: string | null, n = 6) {
  if (!h) return "—";
  const s = h.startsWith("0x") ? h : h;
  return s.length > 2 * n + 3 ? `${s.slice(0, n + (s.startsWith("0x") ? 2 : 0))}…${s.slice(-n)}` : s;
}

export function ago(iso?: string | null) {
  if (!iso) return "—";
  const s = (Date.now() - new Date(iso).getTime()) / 1000;
  if (s < 45) return "just now";
  if (s < 3600) return `${Math.round(s / 60)} min ago`;
  if (s < 86400) return `${Math.round(s / 3600)} h ago`;
  return `${Math.round(s / 86400)} d ago`;
}

export function dateTime(iso?: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("en-IN", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}

export function duration(ms?: number | null) {
  if (ms == null) return "—";
  if (ms < 1000) return `${ms} ms`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)} s`;
  if (ms < 3_600_000) return `${Math.round(ms / 60_000)} min`;
  return `${(ms / 3_600_000).toFixed(1)} h`;
}

export function bytes(n: number) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(0)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

export function pct(x?: number | null, digits = 0) {
  return x == null ? "—" : `${(x * 100).toFixed(digits)}%`;
}

export const AGENTS: Record<string, { label: string; color: string; short: string }> = {
  document_input: { label: "Document Input", color: "var(--slate)", short: "IN" },
  extractor: { label: "Extractor Agent", color: "var(--agent-extract)", short: "EX" },
  validator: { label: "Validator Agent", color: "var(--agent-validate)", short: "VA" },
  action_planner: { label: "Action Planner", color: "var(--agent-plan)", short: "AP" },
  human_approval: { label: "Human Approval", color: "var(--agent-human)", short: "HU" },
  executor: { label: "Execution", color: "var(--agent-exec)", short: "EXE" },
  audit: { label: "Audit Log", color: "var(--agent-audit)", short: "AU" },
};

export const STAGE_ORDER = ["uploaded", "extractor", "validator", "action_planner", "human_approval", "executor", "audit"];
