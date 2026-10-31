"use client";

import { CheckCircle2, ExternalLink, Link2, Loader2, ShieldAlert, ShieldCheck, Wallet, XCircle } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Button, StatusPill } from "@/components/ui/primitives";
import { useToast } from "@/components/ui/toast";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { dateTime, shortHash } from "@/lib/format";
import type { Anchor, AuditEvent } from "@/lib/types";
import { useWallet, type TxState } from "@/lib/wallet";

interface Verification {
  event_id: string;
  offchain: { valid: boolean; checked_events: number; broken: { event_id: string; problems: string[] }[]; event_hash: string; previous_hash: string };
  onchain: {
    status: "verified" | "mismatch" | "not_anchored" | "queued" | "pending" | "failed" | "not_configured" | "unavailable";
    message: string;
    anchor: Anchor | null;
    record: { workflow_id_hash: string; event_type: string; submitter: string; anchored_at: number; block_number: number } | null;
  };
  event: AuditEvent;
}

export function EventVerify({ eventId }: { eventId: string }) {
  const [v, setV] = useState<Verification | null>(null);
  const [loading, setLoading] = useState(true);
  const [tx, setTx] = useState<TxState>({ phase: "idle" });
  const [queueing, setQueueing] = useState(false);
  const { can } = useAuth();
  const wallet = useWallet();
  const toast = useToast();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setV(await api<Verification>(`/api/audit/events/${eventId}/verify`));
    } finally {
      setLoading(false);
    }
  }, [eventId]);
  useEffect(() => {
    setTx({ phase: "idle" });
    load();
  }, [load]);
  useEffect(() => {
    if (v && ["queued", "pending"].includes(v.onchain.status)) {
      const id = setTimeout(load, 4000);
      return () => clearTimeout(id);
    }
  }, [v, load]);

  async function queue() {
    setQueueing(true);
    try {
      await api(`/api/blockchain/events/${eventId}/anchor`, { method: "POST" });
      toast("info", "Queued for anchoring", "The relayer will submit it, or sign it yourself with BridgeKey.");
      await load();
    } catch (e) {
      toast("error", "Could not queue", (e as Error).message);
    } finally {
      setQueueing(false);
    }
  }

  async function signWithWallet() {
    if (!v?.onchain.anchor) return;
    await wallet.anchorWithWallet(v.onchain.anchor, (s) => {
      setTx(s);
      if (s.phase === "confirmed") {
        toast("success", "Anchored on MST", `tx ${shortHash(s.hash, 8)}`);
        load();
      }
      if (s.phase === "failed") toast("error", "Wallet transaction failed", s.error);
    });
  }

  if (loading && !v) return <div className="flex items-center gap-2 py-6 text-sm text-ink-3"><Loader2 className="size-4 animate-spin" /> Verifying…</div>;
  if (!v) return null;
  const on = v.onchain;
  const a = on.anchor;
  const explorer = wallet.config?.network.explorer;

  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-2">
        <div className={`rounded-xl border p-4 ${v.offchain.valid ? "border-ok/40 bg-ok/5" : "border-bad/40 bg-bad/5"}`}>
          <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-ink-3">Off-chain audit</p>
          <p className="mt-2 flex items-center gap-2 text-lg font-extrabold text-ink">
            {v.offchain.valid ? <ShieldCheck className="size-5 text-ok" /> : <ShieldAlert className="size-5 text-bad" />}
            {v.offchain.valid ? "Record valid" : "Chain broken"}
          </p>
          <p className="mt-1 text-xs text-ink-2">Recomputed {v.offchain.checked_events} linked hashes from genesis to this event.</p>
          {v.offchain.broken.map((b) => (
            <p key={b.event_id} className="mt-2 text-xs text-bad">{b.problems.join("; ")}</p>
          ))}
        </div>
        <div
          className={`rounded-xl border p-4 ${
            on.status === "verified" ? "border-teal/50 bg-teal/5" : on.status === "mismatch" || on.status === "failed" ? "border-bad/40 bg-bad/5" : "border-line bg-surface-2"
          }`}
        >
          <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-ink-3">On-chain verification</p>
          <p className="mt-2 flex items-center gap-2 text-lg font-extrabold text-ink">
            {on.status === "verified" ? <CheckCircle2 className="size-5 text-teal" /> : on.status === "pending" || on.status === "queued" ? <Loader2 className="size-5 animate-spin text-a-human" /> : on.status === "mismatch" || on.status === "failed" ? <XCircle className="size-5 text-bad" /> : <Link2 className="size-5 text-ink-3" />}
            {on.status === "verified" ? "Present on MST" : on.status.replace("_", " ").replace(/^\w/, (c) => c.toUpperCase())}
          </p>
          <p className="mt-1 text-xs text-ink-2">{on.message}</p>
        </div>
      </div>

      <dl className="grid gap-x-6 gap-y-2 rounded-xl border border-line p-4 text-xs sm:grid-cols-[140px_1fr]">
        <dt className="text-ink-3">Event hash</dt>
        <dd className="hash break-all text-ink">{v.event.hash}</dd>
        <dt className="text-ink-3">Previous hash</dt>
        <dd className="hash break-all text-ink-2">{v.event.previous_hash}</dd>
        {a && (
          <>
            <dt className="text-ink-3">Anchor status</dt>
            <dd><StatusPill status={a.status} /> {a.submitted_via && <span className="ml-2 text-ink-3">via {a.submitted_via}</span>}</dd>
            <dt className="text-ink-3">Workflow ID hash</dt>
            <dd className="hash break-all text-ink-2">{a.workflow_id_hash}</dd>
          </>
        )}
        {a?.tx_hash && (
          <>
            <dt className="text-ink-3">Transaction</dt>
            <dd className="hash break-all">
              {a.tx_explorer_url ? (
                <a href={a.tx_explorer_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-teal hover:underline">
                  {a.tx_hash} <ExternalLink className="size-3" />
                </a>
              ) : (
                a.tx_hash
              )}
            </dd>
            <dt className="text-ink-3">Block</dt>
            <dd className="text-ink">{a.block_number ?? "pending"} {a.gas_used ? `· gas ${a.gas_used.toLocaleString()}` : ""}</dd>
          </>
        )}
        {on.record && (
          <>
            <dt className="text-ink-3">On-chain record</dt>
            <dd className="text-ink">
              {on.record.event_type} · submitter <span className="hash">{shortHash(on.record.submitter, 6)}</span> · {dateTime(new Date(on.record.anchored_at * 1000).toISOString())}
            </dd>
          </>
        )}
        {a?.contract_address && (
          <>
            <dt className="text-ink-3">Contract</dt>
            <dd className="hash">
              {explorer ? (
                <a className="text-teal hover:underline" href={`${explorer}/address/${a.contract_address}`} target="_blank" rel="noreferrer">{a.contract_address}</a>
              ) : a.contract_address}
            </dd>
          </>
        )}
        {a?.last_error && (
          <>
            <dt className="text-ink-3">Last error</dt>
            <dd className="text-bad">{a.last_error}</dd>
          </>
        )}
      </dl>

      {can("reviewer") && !v.event.seeded && on.status !== "verified" && on.status !== "not_configured" && (
        <div className="flex flex-wrap items-center gap-2">
          {!a && (
            <Button size="sm" variant="dark" onClick={queue} loading={queueing}>
              <Link2 /> Queue for MST anchoring
            </Button>
          )}
          {a && ["queued", "failed"].includes(a.status) && (
            <>
              <Button size="sm" onClick={signWithWallet} disabled={!wallet.account || !wallet.onMst || ["signing", "pending", "verifying"].includes(tx.phase)}>
                <Wallet /> Sign with BridgeKey
              </Button>
              {!wallet.account && <span className="text-xs text-ink-3">Connect BridgeKey (top right) to sign it yourself.</span>}
              {wallet.account && !wallet.onMst && <span className="text-xs text-warn">Switch your wallet to {wallet.config?.network.name}.</span>}
            </>
          )}
          <TxBadge tx={tx} explorer={explorer} />
        </div>
      )}
      {v.event.seeded && <p className="text-xs text-ink-3">Seeded demo history is illustrative and is never anchored on-chain.</p>}
    </div>
  );
}

export function TxBadge({ tx, explorer }: { tx: TxState; explorer?: string }) {
  if (tx.phase === "idle") return null;
  const link = "hash" in tx && tx.hash && explorer ? `${explorer}/tx/${tx.hash}` : null;
  const text = {
    signing: "Waiting for wallet signature…",
    pending: "Transaction pending…",
    verifying: "Mined — backend verifying receipt…",
    confirmed: "Confirmed on MST",
    failed: `Failed: ${"error" in tx ? tx.error : ""}`,
  }[tx.phase];
  return (
    <span className={`inline-flex items-center gap-1.5 text-xs font-semibold ${tx.phase === "failed" ? "text-bad" : tx.phase === "confirmed" ? "text-ok" : "text-a-human"}`}>
      {["signing", "pending", "verifying"].includes(tx.phase) && <Loader2 className="size-3.5 animate-spin" />}
      {text}
      {link && (
        <a href={link} target="_blank" rel="noreferrer" className="inline-flex items-center gap-0.5 text-teal">
          MSTScan <ExternalLink className="size-3" />
        </a>
      )}
    </span>
  );
}
