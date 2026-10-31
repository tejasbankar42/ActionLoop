"use client";

import { Contract, JsonRpcProvider } from "ethers";
import { AlertTriangle, Blocks, CheckCircle2, ExternalLink, Fingerprint, Link2, Loader2, RefreshCw, Search, ShieldCheck, UserPlus, Wallet, XCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { WalletButton } from "@/components/shell/wallet-button";
import { Button, Empty, Input, Panel, StatusPill } from "@/components/ui/primitives";
import { useToast } from "@/components/ui/toast";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { ago, cn, shortHash } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import type { Anchor, NetworkInfo } from "@/lib/types";
import { useWallet } from "@/lib/wallet";

interface ChainStatus {
  network: NetworkInfo;
  contract_address: string | null;
  contract_explorer_url: string | null;
  abi_loaded: boolean;
  deployment: { address: string; deployTxHash: string; blockNumber: number; deployer: string; deployedAt: string; chainId: number } | null;
  relayer_address: string | null;
  relayer_configured: boolean;
  relayer_balance_wei?: string;
  auto_anchor: boolean;
  anchor_event_types: string[];
  rpc_reachable: boolean;
  rpc_chain_id?: number;
  chain_id_matches: boolean;
  latest_block?: number;
  contract_code_present: boolean;
  contract?: { owner: string; paused: boolean; total_anchored: number; relayer_is_submitter: boolean | null };
  anchor_counts: Record<string, number>;
  error?: string;
}

export default function BlockchainPage() {
  const { data: s, reload } = useApi<ChainStatus>("/api/blockchain/status", 8000);
  const { data: anchors, reload: reloadAnchors } = useApi<Anchor[]>("/api/blockchain/anchors?limit=100", 5000);
  const wallet = useWallet();
  const { can } = useAuth();
  const toast = useToast();
  const explorer = s?.network.explorer;
  const [walletAuth, setWalletAuth] = useState<boolean | null>(null);
  const [authBusy, setAuthBusy] = useState(false);

  useEffect(() => {
    if (!wallet.account || !s?.contract_address) return setWalletAuth(null);
    api<{ authorized: boolean }>(`/api/blockchain/submitters/${wallet.account}`).then((r) => setWalletAuth(r.authorized)).catch(() => setWalletAuth(null));
  }, [wallet.account, s?.contract_address]);

  async function authorizeWallet() {
    if (!wallet.account) return;
    setAuthBusy(true);
    try {
      const r = await api<{ tx_hash: string; confirmed: boolean }>("/api/blockchain/submitters", { method: "POST", body: JSON.stringify({ address: wallet.account, authorized: true }) });
      toast(r.confirmed ? "success" : "error", r.confirmed ? "Wallet authorized on-chain" : "Authorization not confirmed", `setSubmitter tx ${shortHash(r.tx_hash, 8)}`);
      setWalletAuth(r.confirmed);
    } catch (e) {
      toast("error", "Authorization failed", (e as Error).message);
    } finally {
      setAuthBusy(false);
    }
  }

  async function retry(a: Anchor) {
    try {
      const r = await api<Anchor>(`/api/blockchain/anchors/${a.id}/process`, { method: "POST" });
      toast(r.status === "confirmed" ? "success" : "info", `Anchor ${r.status}`, r.last_error ?? (r.tx_hash ? `tx ${shortHash(r.tx_hash, 8)}` : undefined));
      reloadAnchors();
      reload();
    } catch (e) {
      toast("error", "Retry failed", (e as Error).message);
    }
  }

  const configured = !!s?.contract_address && s.contract_code_present;
  const bal = s?.relayer_balance_wei ? Number(BigInt(s.relayer_balance_wei) / BigInt(1e12)) / 1e6 : null;

  return (
    <div className="space-y-6">
      {s && !configured && (
        <div className="flex gap-3 rounded-[var(--radius-card)] border border-warn/40 bg-warn/10 p-4 text-sm text-ink">
          <AlertTriangle className="mt-0.5 size-5 shrink-0 text-warn" />
          <div>
            <p className="font-bold">Audit registry not deployed on {s.network.name} yet</p>
            <p className="mt-1 text-ink-2">
              No transaction is being simulated. Anchors stay <b>not configured</b> until the contract is deployed (<code className="hash">npm run deploy:testnet</code> in <code className="hash">contracts/</code>)
              and the backend restarts. {s.error && <span className="text-bad">RPC: {s.error}</span>}
            </p>
          </div>
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card icon={<Blocks />} label="Active network" value={s?.network.name ?? "…"} sub={s ? `chain ${s.network.chain_id} · ${s.rpc_reachable ? `block ${s.latest_block?.toLocaleString()}` : "RPC unreachable"}` : ""} tone={s?.chain_id_matches ? "ok" : "warn"} />
        <Card icon={<Fingerprint />} label="Audit registry" value={!s ? "…" : s.contract_address ? shortHash(s.contract_address, 6) : "Not deployed"} sub={s?.contract_code_present ? "bytecode verified via eth_getCode" : "no contract code"} tone={configured ? "ok" : "warn"} href={s?.contract_explorer_url ?? undefined} />
        <Card icon={<ShieldCheck />} label="Anchored on-chain" value={s?.contract ? s.contract.total_anchored : "—"} sub={`totalAnchored() · ${s?.anchor_counts.confirmed ?? 0} from this app`} tone="ok" />
        <Card icon={<Wallet />} label="Relayer" value={!s ? "…" : s.relayer_address ? shortHash(s.relayer_address, 5) : "Not configured"} sub={bal != null ? `${bal.toFixed(4)} ${s?.network.symbol} · ${s?.contract?.relayer_is_submitter ? "authorized" : "not authorized"}` : "backend signer for auto-anchoring"} tone={s?.contract?.relayer_is_submitter ? "ok" : "warn"} />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1fr_1.4fr]">
        <Panel title="BridgeKey wallet" subtitle="Sign anchor transactions yourself — keys never leave the wallet">
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-3">
              <WalletButton />
              {wallet.account && <Button size="sm" variant="ghost" onClick={wallet.disconnect}>Disconnect</Button>}
            </div>
            {wallet.error && <p className="rounded-lg bg-bad/10 px-3 py-2 text-sm text-bad">{wallet.error}</p>}
            <dl className="grid grid-cols-[130px_1fr] gap-y-2 text-sm">
              <dt className="text-ink-3">Wallet</dt>
              <dd className="text-ink">{wallet.walletName ?? (wallet.wallets.length ? `${wallet.wallets.length} detected` : "none detected")}</dd>
              <dt className="text-ink-3">Account</dt>
              <dd className="hash text-ink">{wallet.account ?? "—"}</dd>
              <dt className="text-ink-3">Wallet network</dt>
              <dd className="text-ink">
                {wallet.chainId == null ? "—" : wallet.onMst ? <StatusPill status="ok">{s?.network.name}</StatusPill> : <StatusPill status="warning">chain {wallet.chainId}</StatusPill>}
              </dd>
              <dt className="text-ink-3">Submitter role</dt>
              <dd>
                {walletAuth == null ? <span className="text-ink-3">—</span> : walletAuth ? <StatusPill status="ok">Authorized</StatusPill> : <StatusPill status="warning">Not authorized</StatusPill>}
              </dd>
            </dl>
            {wallet.account && walletAuth === false && can("admin") && configured && (
              <Button size="sm" variant="dark" onClick={authorizeWallet} loading={authBusy}>
                <UserPlus /> Authorize this wallet (owner tx)
              </Button>
            )}
            {wallet.account && walletAuth === false && !can("admin") && <p className="text-xs text-ink-3">An admin must authorize this address before it can anchor events.</p>}
            {!wallet.wallets.length && (
              <p className="text-xs text-ink-3">
                Install the <a className="text-teal" href="https://bridgekey.io/" target="_blank" rel="noreferrer">BridgeKey</a> extension, claim tMSTC at{" "}
                <a className="text-teal" href="https://faucet.mstblockchain.com" target="_blank" rel="noreferrer">faucet.mstblockchain.com</a>, then reload.
              </p>
            )}
          </div>
        </Panel>

        <HashLookup network={s?.network} contract={s?.contract_address ?? null} />
      </div>

      <Panel
        title="Recent blockchain transactions"
        subtitle="Every row is an audit-event hash; status flips to confirmed only after a successful receipt AND isAnchored() == true"
        action={<Button size="sm" variant="ghost" onClick={() => { reload(); reloadAnchors(); }}><RefreshCw /> Refresh</Button>}
        bodyClass="p-0"
      >
        {!anchors?.length ? (
          <Empty icon={<Link2 />} title="No anchors yet">Approve a workflow — approval decisions and outcomes are queued for anchoring automatically.</Empty>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[960px] text-sm">
              <thead className="text-left text-[11px] uppercase tracking-wider text-ink-3">
                <tr className="border-b border-line">
                  <th className="px-5 py-2.5">Event</th><th>Event hash</th><th>Status</th><th>Tx hash</th><th>Block</th><th>Via</th><th>Created</th><th className="pr-5" />
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {anchors.map((a) => (
                  <tr key={a.id}>
                    <td className="px-5 py-3">
                      <p className="hash font-semibold text-ink">{a.event_type}</p>
                      <p className="max-w-[260px] truncate text-xs text-ink-3">{a.description}</p>
                    </td>
                    <td className="hash text-ink-2">{shortHash(a.event_hash, 6)}</td>
                    <td><StatusPill status={a.status} />{a.last_error && a.status !== "confirmed" && <p className="mt-1 max-w-[220px] truncate text-[11px] text-bad" title={a.last_error}>{a.last_error}</p>}</td>
                    <td className="hash">
                      {a.tx_hash ? (
                        <a href={a.tx_explorer_url ?? `${explorer}/tx/${a.tx_hash}`} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-teal hover:underline">
                          {shortHash(a.tx_hash, 6)} <ExternalLink className="size-3" />
                        </a>
                      ) : "—"}
                    </td>
                    <td className="tabular-nums text-ink-2">{a.block_number ?? "—"}</td>
                    <td className="text-ink-2">{a.submitted_via ?? "—"}</td>
                    <td className="text-ink-3">{ago(a.created_at)}</td>
                    <td className="pr-5 text-right">
                      {can("reviewer") && ["queued", "failed", "submitted"].includes(a.status) && configured && s?.relayer_configured && (
                        <Button size="sm" variant="outline" onClick={() => retry(a)}>{a.status === "submitted" ? "Re-check" : "Submit now"}</Button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      {s?.deployment && (
        <Panel title="Deployment record" subtitle="Written by contracts/scripts/deploy.js">
          <dl className="grid gap-x-6 gap-y-2 text-sm sm:grid-cols-[160px_1fr]">
            <dt className="text-ink-3">Contract</dt><dd className="hash break-all"><a className="text-teal" href={`${explorer}/address/${s.deployment.address}`} target="_blank" rel="noreferrer">{s.deployment.address}</a></dd>
            <dt className="text-ink-3">Deploy transaction</dt><dd className="hash break-all"><a className="text-teal" href={`${explorer}/tx/${s.deployment.deployTxHash}`} target="_blank" rel="noreferrer">{s.deployment.deployTxHash}</a></dd>
            <dt className="text-ink-3">Block · chain</dt><dd className="text-ink">{s.deployment.blockNumber} · {s.deployment.chainId}</dd>
            <dt className="text-ink-3">Owner / deployer</dt><dd className="hash text-ink">{s.deployment.deployer}</dd>
            <dt className="text-ink-3">Deployed</dt><dd className="text-ink">{new Date(s.deployment.deployedAt).toLocaleString()}</dd>
          </dl>
        </Panel>
      )}
    </div>
  );
}

function Card({ icon, label, value, sub, tone, href }: { icon: React.ReactNode; label: string; value: React.ReactNode; sub: string; tone: "ok" | "warn"; href?: string }) {
  const body = (
    <div className="h-full rounded-[var(--radius-card)] border border-line bg-surface p-5">
      <div className="flex items-center justify-between text-ink-3 [&_svg]:size-4">
        <span className="text-xs font-semibold uppercase tracking-wider">{label}</span>
        {icon}
      </div>
      <p className="mt-3 flex items-center gap-2 text-xl font-extrabold text-ink">
        <span className={cn("size-2 rounded-full", tone === "ok" ? "bg-ok" : "bg-warn")} />
        <span className="truncate">{value}</span>
        {href && <ExternalLink className="size-3.5 text-teal" />}
      </p>
      <p className="mt-1 truncate text-xs text-ink-3">{sub}</p>
    </div>
  );
  return href ? <a href={href} target="_blank" rel="noreferrer">{body}</a> : body;
}

function HashLookup({ network, contract }: { network?: NetworkInfo; contract: string | null }) {
  const { config } = useWallet();
  const [hash, setHash] = useState("");
  const [busy, setBusy] = useState(false);
  const [res, setRes] = useState<{ source: string; anchored: boolean; record?: { event_type: string; submitter: string; block_number: number; anchored_at: number } | null; error?: string }[] | null>(null);

  async function lookup() {
    const h = hash.trim();
    if (!/^(0x)?[0-9a-fA-F]{64}$/.test(h)) {
      setRes([{ source: "input", anchored: false, error: "Enter a 32-byte hex hash (64 hex chars)." }]);
      return;
    }
    const hex = h.startsWith("0x") ? h : `0x${h}`;
    setBusy(true);
    const out: NonNullable<typeof res> = [];
    try {
      const r = await api<{ anchored: boolean; record: { event_type: string; submitter: string; block_number: number; anchored_at: number } | null; configured: boolean }>(`/api/blockchain/verify/${hex}`);
      out.push({ source: "ActionLoop backend", anchored: r.anchored, record: r.record, error: r.configured ? undefined : "registry not configured" });
    } catch (e) {
      out.push({ source: "ActionLoop backend", anchored: false, error: (e as Error).message });
    }
    // Independent check straight from the browser to the public MST RPC — no ActionLoop server involved.
    if (network && contract && config?.abi) {
      try {
        const c = new Contract(contract, config.abi as never, new JsonRpcProvider(network.rpc_url, network.chain_id, { staticNetwork: true }));
        const ok = (await c.isAnchored(hex)) as boolean;
        out.push({ source: "Direct MST RPC (browser)", anchored: ok });
      } catch (e) {
        out.push({ source: "Direct MST RPC (browser)", anchored: false, error: (e as Error).message.slice(0, 120) });
      }
    }
    setRes(out);
    setBusy(false);
  }

  return (
    <Panel title="Verify any event hash" subtitle="Paste an audit event hash — checked by the backend and directly against MST RPC from your browser">
      <div className="flex gap-2">
        <Input className="hash" placeholder="0x… or 64-char hex" value={hash} onChange={(e) => setHash(e.target.value)} />
        <Button onClick={lookup} loading={busy}><Search /> Verify</Button>
      </div>
      {res && (
        <ul className="mt-4 space-y-2">
          {res.map((r) => (
            <li key={r.source} className={cn("flex gap-3 rounded-lg border p-3 text-sm", r.anchored ? "border-teal/40 bg-teal/5" : "border-line")}>
              {r.error ? <AlertTriangle className="size-4 shrink-0 text-warn" /> : r.anchored ? <CheckCircle2 className="size-4 shrink-0 text-teal" /> : <XCircle className="size-4 shrink-0 text-ink-3" />}
              <div className="min-w-0">
                <p className="font-semibold text-ink">{r.source}: {r.error ? "unavailable" : r.anchored ? "anchored" : "not found on-chain"}</p>
                {r.error && <p className="text-xs text-ink-3">{r.error}</p>}
                {r.record && <p className="text-xs text-ink-2">{r.record.event_type} · block {r.record.block_number} · submitter <span className="hash">{shortHash(r.record.submitter, 5)}</span></p>}
              </div>
            </li>
          ))}
        </ul>
      )}
      {!res && busy && <Loader2 className="mt-4 size-4 animate-spin text-ink-3" />}
    </Panel>
  );
}
