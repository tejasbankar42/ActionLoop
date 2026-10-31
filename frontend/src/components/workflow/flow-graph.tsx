"use client";

import { Background, Controls, Handle, MarkerType, Position, ReactFlow, type Edge, type Node, type NodeProps } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Blocks, Bot, CheckCircle2, FileInput, ListChecks, Loader2, Play, Route, ScrollText, UserCheck, XCircle, Hourglass } from "lucide-react";
import { useMemo } from "react";
import { AGENTS, cn, duration } from "@/lib/format";
import type { Anchor, WorkflowDetail } from "@/lib/types";

export type NodeStatus = "idle" | "running" | "completed" | "failed" | "waiting" | "skipped";

const ICONS: Record<string, React.ComponentType<{ className?: string; style?: React.CSSProperties }>> = {
  document_input: FileInput,
  extractor: Bot,
  validator: ListChecks,
  action_planner: Route,
  human_approval: UserCheck,
  executor: Play,
  audit: ScrollText,
  mst: Blocks,
};
const LABELS: Record<string, string> = { ...Object.fromEntries(Object.entries(AGENTS).map(([k, v]) => [k, v.label])), mst: "MST Blockchain" };
const COLORS: Record<string, string> = { ...Object.fromEntries(Object.entries(AGENTS).map(([k, v]) => [k, v.color])), mst: "#16B8A6" };

const POS: Record<string, { x: number; y: number }> = {
  document_input: { x: 0, y: 30 },
  extractor: { x: 270, y: 30 },
  validator: { x: 540, y: 30 },
  action_planner: { x: 810, y: 30 },
  human_approval: { x: 810, y: 250 },
  executor: { x: 540, y: 250 },
  audit: { x: 270, y: 250 },
  mst: { x: 0, y: 250 },
};

export function nodeStatuses(wf: WorkflowDetail | null, anchors: Anchor[]): Record<string, { status: NodeStatus; detail: string }> {
  const out: Record<string, { status: NodeStatus; detail: string }> = {};
  const closed = !!wf && ["completed", "rejected", "needs_correction", "failed"].includes(wf.status);
  out.document_input = { status: wf ? "completed" : "idle", detail: wf?.document.filename ?? "No workflow selected" };
  for (const a of ["extractor", "validator", "action_planner", "executor"]) {
    const ex = wf?.executions.filter((e) => e.agent === a).at(-1);
    let status: NodeStatus = ex ? (ex.status as NodeStatus) : "idle";
    if (!ex && closed && a === "executor" && wf?.status !== "completed") status = "skipped";
    out[a] = { status, detail: ex ? `${duration(ex.duration_ms)} · ${ex.engine}` : status === "skipped" ? "not executed" : "idle" };
  }
  const hu = wf?.executions.filter((e) => e.agent === "human_approval").at(-1);
  out.human_approval = {
    status: wf?.status === "awaiting_approval" ? "waiting" : hu ? "completed" : closed ? "skipped" : "idle",
    detail: wf?.status === "awaiting_approval" ? "waiting for reviewer" : hu ? String(hu.output?.decision ?? "decided") : closed ? "not required" : "idle",
  };
  out.audit = { status: !wf ? "idle" : closed ? "completed" : "running", detail: closed ? "hash-chained" : wf ? "recording events" : "idle" };
  const mine = anchors.filter((a) => a.workflow_id === wf?.id);
  const mstStatus: NodeStatus = !mine.length
    ? closed || wf?.status === "awaiting_approval" ? "idle" : "idle"
    : mine.some((a) => a.status === "failed")
      ? "failed"
      : mine.every((a) => a.status === "confirmed")
        ? "completed"
        : mine.some((a) => a.status === "not_configured")
          ? "idle"
          : "running";
  out.mst = {
    status: mstStatus,
    detail: mine.length ? `${mine.filter((a) => a.status === "confirmed").length}/${mine.length} anchored` : "no anchored events yet",
  };
  return out;
}

function AgentNode({ data, selected }: NodeProps<Node<{ id: string; status: NodeStatus; detail: string }>>) {
  const Icon = ICONS[data.id];
  const color = COLORS[data.id];
  const s = data.status;
  return (
    <div
      className={cn(
        "relative w-[210px] rounded-2xl border bg-surface p-3.5 shadow-sm transition-shadow",
        selected ? "shadow-lg ring-2" : "hover:shadow-md",
        s === "idle" || s === "skipped" ? "border-line opacity-80" : "border-transparent",
      )}
      style={{ ["--tw-ring-color" as string]: color, boxShadow: s === "running" || s === "waiting" ? `0 0 0 3px ${color}33` : undefined }}
    >
      <span className="absolute inset-y-3 left-0 w-1 rounded-r" style={{ background: color }} />
      <Handle type="target" position={Position.Left} id="l" className="!size-2 !border-0 !bg-ink-3" />
      <Handle type="target" position={Position.Top} id="t" className="!size-2 !border-0 !bg-ink-3" />
      <Handle type="target" position={Position.Right} id="rt" className="!size-2 !border-0 !bg-ink-3" />
      <div className="flex items-center gap-3 pl-1.5">
        <span className="grid size-10 place-items-center rounded-xl" style={{ background: `${color}1f` }}>
          <Icon className="size-5" style={{ color }} />
        </span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-[13px] font-bold text-ink">{LABELS[data.id]}</p>
          <p className="truncate text-[11px] text-ink-3">{data.detail}</p>
        </div>
        <span>
          {s === "completed" && <CheckCircle2 className="size-4 text-ok" />}
          {s === "running" && <Loader2 className="size-4 animate-spin text-a-human" />}
          {s === "waiting" && <Hourglass className="size-4 text-warn" />}
          {s === "failed" && <XCircle className="size-4 text-bad" />}
        </span>
      </div>
      <div className="mt-2.5 flex items-center justify-between pl-1.5">
        <span
          className={cn(
            "rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider",
            s === "completed" && "bg-ok/12 text-[#067647] dark:text-[#47cd89]",
            s === "running" && "bg-a-human/12 text-[#026aa2] dark:text-[#36bffa]",
            s === "waiting" && "bg-warn/15 text-[#b54708] dark:text-[#fdb022]",
            s === "failed" && "bg-bad/12 text-[#b42318] dark:text-[#f97066]",
            (s === "idle" || s === "skipped") && "bg-surface-2 text-ink-3",
          )}
        >
          {s === "waiting" ? "Waiting for approval" : s}
        </span>
      </div>
      <Handle type="source" position={Position.Right} id="r" className="!size-2 !border-0 !bg-ink-3" />
      <Handle type="source" position={Position.Bottom} id="b" className="!size-2 !border-0 !bg-ink-3" />
      <Handle type="source" position={Position.Left} id="ls" className="!size-2 !border-0 !bg-ink-3" />
    </div>
  );
}

const nodeTypes = { agent: AgentNode };

export function FlowGraph({ statuses, selected, onSelect }: {
  statuses: Record<string, { status: NodeStatus; detail: string }>;
  selected: string | null;
  onSelect: (id: string) => void;
}) {
  const nodes: Node[] = useMemo(
    () =>
      Object.keys(POS).map((id) => ({
        id,
        type: "agent",
        position: POS[id],
        data: { id, ...statuses[id] },
        selected: selected === id,
      })),
    [statuses, selected],
  );

  const edges: Edge[] = useMemo(() => {
    const def: [string, string, string, string, string?][] = [
      ["document_input", "extractor", "r", "l"],
      ["extractor", "validator", "r", "l"],
      ["validator", "action_planner", "r", "l"],
      ["action_planner", "human_approval", "b", "t", "needs approval"],
      ["action_planner", "executor", "b", "t", "auto"],
      ["human_approval", "executor", "ls", "rt"],
      ["executor", "audit", "ls", "rt"],
      ["audit", "mst", "ls", "rt", "anchor"],
    ];
    return def.map(([s, t, sh, th, label]) => {
      const src = statuses[s]?.status;
      const dst = statuses[t]?.status;
      const flowing = dst === "running" || dst === "waiting" || (src === "running" && dst !== "skipped");
      const done = src === "completed" && (dst === "completed" || dst === "waiting" || dst === "running");
      const color = flowing ? COLORS[t] : done ? "var(--ok)" : "var(--border)";
      return {
        id: `${s}-${t}`,
        source: s,
        target: t,
        sourceHandle: sh,
        targetHandle: th,
        type: "smoothstep",
        animated: flowing,
        label,
        labelStyle: { fontSize: 10, fill: "var(--ink-3)", fontWeight: 600 },
        labelBgStyle: { fill: "var(--canvas)" },
        style: { stroke: color, strokeWidth: flowing || done ? 2.4 : 1.6 },
        markerEnd: { type: MarkerType.ArrowClosed, color, width: 16, height: 16 },
      };
    });
  }, [statuses]);

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      onNodeClick={(_, n) => onSelect(n.id)}
      fitView
      fitViewOptions={{ padding: 0.15 }}
      nodesDraggable={false}
      nodesConnectable={false}
      proOptions={{ hideAttribution: true }}
      minZoom={0.4}
    >
      <Background gap={24} size={1.2} color="var(--border)" />
      <Controls showInteractive={false} position="bottom-right" />
    </ReactFlow>
  );
}
