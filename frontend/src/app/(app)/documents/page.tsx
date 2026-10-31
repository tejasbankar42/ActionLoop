"use client";

import { FileImage, FileText, Play, RotateCw, Sparkles, UploadCloud, Workflow } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useToast } from "@/components/ui/toast";
import { Button, Empty, Panel, StatusPill } from "@/components/ui/primitives";
import { DocPreview, FieldTable, StageTrack } from "@/components/workflow/parts";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { ago, bytes, cn, shortHash } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import type { DocumentItem, WorkflowDetail } from "@/lib/types";

const ACCEPT = ["application/pdf", "image/png", "image/jpeg"];
const MAX_MB = 10;

function DocumentsInner() {
  const params = useSearchParams();
  const router = useRouter();
  const toast = useToast();
  const { can } = useAuth();
  const { data: docs, reload } = useApi<DocumentItem[]>("/api/documents", 5000);
  const [selected, setSelected] = useState<string | null>(params.get("doc"));
  const [drag, setDrag] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [starting, setStarting] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const dropRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (params.get("upload")) dropRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [params]);
  useEffect(() => {
    if (!selected && docs?.length) setSelected([...docs].sort((a, b) => a.filename.localeCompare(b.filename))[0].id);
  }, [docs, selected]);

  const doc = docs?.find((d) => d.id === selected) ?? null;
  const wfId = doc?.latest_workflow?.id ?? null;
  const live = doc?.latest_workflow && ["queued", "running"].includes(doc.latest_workflow.status);
  const { data: wf } = useApi<WorkflowDetail>(wfId ? `/api/workflows/${wfId}` : null, live ? 700 : 4000);

  const upload = useCallback(
    async (file: File) => {
      if (!ACCEPT.includes(file.type)) {
        toast("error", "Unsupported file type", "Upload a PDF, JPG, JPEG or PNG.");
        return;
      }
      if (file.size > MAX_MB * 1024 * 1024) {
        toast("error", "File too large", `Maximum size is ${MAX_MB} MB.`);
        return;
      }
      setUploading(true);
      try {
        const fd = new FormData();
        fd.append("file", file);
        const d = await api<DocumentItem>("/api/documents/upload", { method: "POST", body: fd });
        toast("success", "Uploaded", `${d.filename} · SHA-256 ${shortHash(d.sha256)}`);
        if (d.duplicate_upload_of) toast("info", "Same file uploaded before", "The validator will check whether it was already processed.");
        await reload();
        setSelected(d.id);
      } catch (e) {
        toast("error", "Upload failed", (e as Error).message);
      } finally {
        setUploading(false);
      }
    },
    [reload, toast],
  );

  async function start() {
    if (!doc) return;
    setStarting(true);
    try {
      await api("/api/workflows/start", { method: "POST", body: JSON.stringify({ document_id: doc.id }) });
      toast("success", "Workflow started", "Watch the agents run below.");
      await reload();
    } catch (e) {
      toast("error", "Could not start", (e as Error).message);
    } finally {
      setStarting(false);
    }
  }

  const samples = (docs?.filter((d) => d.is_sample) ?? []).sort((a, b) => a.filename.localeCompare(b.filename));
  const uploads = docs?.filter((d) => !d.is_sample) ?? [];

  return (
    <div className="grid gap-6 xl:grid-cols-[400px_1fr]">
      <div className="space-y-6">
        <div
          ref={dropRef}
          onDragOver={(e) => {
            e.preventDefault();
            setDrag(true);
          }}
          onDragLeave={() => setDrag(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDrag(false);
            const f = e.dataTransfer.files[0];
            if (f) upload(f);
          }}
          className={cn(
            "rounded-[var(--radius-card)] border-2 border-dashed p-6 text-center transition-colors",
            drag ? "border-teal bg-teal/5" : "border-line bg-surface",
            params.get("upload") && "ring-2 ring-teal/30",
          )}
        >
          <UploadCloud className="mx-auto size-9 text-teal" />
          <p className="mt-3 font-bold text-ink">Drop a document here</p>
          <p className="mt-1 text-xs text-ink-3">PDF, JPG, JPEG or PNG · up to {MAX_MB} MB</p>
          <input
            ref={inputRef}
            type="file"
            accept=".pdf,.png,.jpg,.jpeg"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) upload(f);
              e.target.value = "";
            }}
          />
          <Button className="mt-4" variant="dark" onClick={() => inputRef.current?.click()} loading={uploading} disabled={!can("operator")}>
            Browse files
          </Button>
          {!can("operator") && <p className="mt-2 text-xs text-ink-3">Viewer accounts cannot upload.</p>}
        </div>

        <DocList title="Demo scenarios" subtitle="Bundled samples A–G" docs={samples} selected={selected} onSelect={setSelected} />
        <DocList title="Upload history" docs={uploads} selected={selected} onSelect={setSelected} empty="Uploaded files will appear here." />
      </div>

      <div className="min-w-0">
        {!doc ? (
          <Panel>
            <Empty icon={<FileText />} title="Select a document" />
          </Panel>
        ) : (
          <div className="space-y-6">
            <Panel
              title={doc.filename}
              subtitle={
                <span className="hash">
                  {doc.content_type} · {bytes(doc.size_bytes)} · sha256 {shortHash(doc.sha256, 10)}
                </span>
              }
              action={
                <div className="flex shrink-0 gap-2">
                  {wf && (
                    <Button variant="outline" size="sm" onClick={() => router.push(`/studio?wf=${wf.id}`)}>
                      <Workflow /> Open in Studio
                    </Button>
                  )}
                  {(!wf || ["completed", "rejected", "needs_correction", "failed"].includes(wf.status)) && (
                    <Button size="sm" onClick={start} loading={starting} disabled={!can("operator")}>
                      {wf?.status === "failed" ? <RotateCw /> : <Play />}
                      {wf ? "Process again" : "Start processing"}
                    </Button>
                  )}
                </div>
              }
            >
              <div className="mb-6 flex flex-wrap items-center gap-3">
                <StatusPill status={wf?.status ?? doc.status} />
                {doc.type_label && (
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-surface-2 px-2.5 py-0.5 text-xs font-semibold text-ink-2">
                    <Sparkles className="size-3.5 text-teal" /> {doc.type_label}
                  </span>
                )}
                <span className="text-xs text-ink-3">uploaded {ago(doc.created_at)}</span>
              </div>
              {wf ? (
                <StageTrack wf={wf} />
              ) : (
                <p className="rounded-lg bg-surface-2 px-4 py-3 text-sm text-ink-2">
                  Not processed yet. Start processing to run Extractor → Validator → Planner.
                </p>
              )}
              {wf?.error && <p className="mt-4 rounded-lg bg-bad/10 px-4 py-3 text-sm text-bad">{wf.error}</p>}
              {wf?.status === "awaiting_approval" && (
                <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-lg bg-warn/10 px-4 py-3 text-sm text-ink">
                  <span>{wf.approval_reasons.join(" · ")}</span>
                  <Link href={`/approvals?focus=${wf.approvals.at(-1)?.id}`} className="font-semibold text-teal">
                    Review now →
                  </Link>
                </div>
              )}
            </Panel>

            <div className="grid gap-6 2xl:grid-cols-2">
              <Panel title="Original document" bodyClass="p-3">
                <DocPreview doc={doc} />
              </Panel>
              <Panel title="Extracted information" subtitle={wf ? `${wf.fields.length} fields` : undefined}>
                {wf ? <FieldTable fields={wf.fields} /> : <Empty title="Nothing extracted yet" />}
              </Panel>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function DocList({ title, subtitle, docs, selected, onSelect, empty }: {
  title: string;
  subtitle?: string;
  docs: DocumentItem[];
  selected: string | null;
  onSelect: (id: string) => void;
  empty?: string;
}) {
  return (
    <Panel title={title} subtitle={subtitle} bodyClass="p-2">
      {docs.length === 0 ? (
        <p className="px-3 py-4 text-xs text-ink-3">{empty}</p>
      ) : (
        <ul className="space-y-0.5">
          {docs.map((d) => (
            <li key={d.id}>
              <button
                onClick={() => onSelect(d.id)}
                className={cn(
                  "flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left",
                  selected === d.id ? "bg-teal/10 ring-1 ring-teal/30" : "hover:bg-surface-2",
                )}
              >
                {d.content_type === "application/pdf" ? <FileText className="size-4 shrink-0 text-ink-3" /> : <FileImage className="size-4 shrink-0 text-ink-3" />}
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-medium text-ink">{d.filename}</span>
                  <span className="block text-[11px] text-ink-3">
                    {d.type_label ?? (d.latest_workflow ? "unclassified" : "not processed")} · {bytes(d.size_bytes)}
                  </span>
                </span>
                <StatusPill status={d.latest_workflow?.status ?? d.status} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}

export default function DocumentsPage() {
  return (
    <Suspense>
      <DocumentsInner />
    </Suspense>
  );
}
