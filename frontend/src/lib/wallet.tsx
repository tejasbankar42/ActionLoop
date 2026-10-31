"use client";

/* Browser wallet integration for BridgeKey (MST's official wallet).
 * BridgeKey publishes no dApp SDK; we use the standard EVM provider interfaces it is expected to
 * expose: EIP-6963 discovery (preferring a provider named "BridgeKey"), falling back to EIP-1193
 * `window.ethereum`. Private keys never leave the wallet - the page only requests signatures. */

import { BrowserProvider, Contract, encodeBytes32String } from "ethers";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api } from "./api";
import type { Anchor, NetworkInfo } from "./types";

interface Eip1193 {
  request: (args: { method: string; params?: unknown[] }) => Promise<unknown>;
  on?: (event: string, cb: (...a: unknown[]) => void) => void;
  removeListener?: (event: string, cb: (...a: unknown[]) => void) => void;
}
interface Discovered {
  info: { uuid: string; name: string; icon: string; rdns: string };
  provider: Eip1193;
}
export interface ChainConfig {
  network: NetworkInfo;
  contract_address: string | null;
  abi: unknown[];
  configured: boolean;
}
export type TxState =
  | { phase: "idle" }
  | { phase: "signing" }
  | { phase: "pending"; hash: string }
  | { phase: "verifying"; hash: string }
  | { phase: "confirmed"; hash: string; anchor: Anchor }
  | { phase: "failed"; hash?: string; error: string };

interface WalletState {
  wallets: Discovered[];
  walletName: string | null;
  account: string | null;
  chainId: number | null;
  config: ChainConfig | null;
  onMst: boolean;
  connecting: boolean;
  error: string | null;
  connect: (uuid?: string) => Promise<void>;
  disconnect: () => void;
  switchToMst: () => Promise<void>;
  anchorWithWallet: (anchor: Anchor, onState: (s: TxState) => void) => Promise<void>;
}

const WalletContext = createContext<WalletState | null>(null);
const toHex = (n: number) => "0x" + n.toString(16);

function errMessage(e: unknown): string {
  const anyE = e as { shortMessage?: string; message?: string; code?: number | string; info?: { error?: { message?: string } } };
  if (anyE?.code === 4001 || anyE?.code === "ACTION_REJECTED") return "Request rejected in wallet.";
  return anyE?.info?.error?.message || anyE?.shortMessage || anyE?.message || String(e);
}

export function WalletProvider({ children }: { children: React.ReactNode }) {
  const [wallets, setWallets] = useState<Discovered[]>([]);
  const [active, setActive] = useState<Discovered | null>(null);
  const [account, setAccount] = useState<string | null>(null);
  const [chainId, setChainId] = useState<number | null>(null);
  const [config, setConfig] = useState<ChainConfig | null>(null);
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<ChainConfig>("/api/blockchain/config").then(setConfig).catch(() => setConfig(null));
    const found = new Map<string, Discovered>();
    const onAnnounce = (e: Event) => {
      const d = (e as CustomEvent<Discovered>).detail;
      found.set(d.info.uuid, d);
      setWallets([...found.values()]);
    };
    window.addEventListener("eip6963:announceProvider", onAnnounce);
    window.dispatchEvent(new Event("eip6963:requestProvider"));
    const t = setTimeout(() => {
      const eth = (window as unknown as { ethereum?: Eip1193 & { isBridgeKey?: boolean } }).ethereum;
      if (found.size === 0 && eth) {
        found.set("injected", {
          info: { uuid: "injected", name: eth.isBridgeKey ? "BridgeKey" : "Injected wallet", icon: "", rdns: "injected" },
          provider: eth,
        });
        setWallets([...found.values()]);
      }
    }, 400);
    return () => {
      window.removeEventListener("eip6963:announceProvider", onAnnounce);
      clearTimeout(t);
    };
  }, []);

  useEffect(() => {
    if (!active?.provider.on) return;
    const onAccounts = (a: unknown) => setAccount((a as string[])[0] ?? null);
    const onChain = (c: unknown) => setChainId(parseInt(c as string, 16));
    active.provider.on("accountsChanged", onAccounts);
    active.provider.on("chainChanged", onChain);
    return () => {
      active.provider.removeListener?.("accountsChanged", onAccounts);
      active.provider.removeListener?.("chainChanged", onChain);
    };
  }, [active]);

  const connect = useCallback(
    async (uuid?: string) => {
      setError(null);
      const pick =
        wallets.find((w) => w.info.uuid === uuid) ??
        wallets.find((w) => /bridgekey/i.test(w.info.name + w.info.rdns)) ??
        wallets[0];
      if (!pick) {
        setError("No browser wallet detected. Install the BridgeKey extension and reload.");
        return;
      }
      setConnecting(true);
      try {
        const accounts = (await pick.provider.request({ method: "eth_requestAccounts" })) as string[];
        const cid = (await pick.provider.request({ method: "eth_chainId" })) as string;
        setActive(pick);
        setAccount(accounts[0] ?? null);
        setChainId(parseInt(cid, 16));
      } catch (e) {
        setError(errMessage(e));
      } finally {
        setConnecting(false);
      }
    },
    [wallets],
  );

  const disconnect = useCallback(() => {
    setActive(null);
    setAccount(null);
    setChainId(null);
  }, []);

  const switchToMst = useCallback(async () => {
    if (!active || !config) return;
    const n = config.network;
    setError(null);
    try {
      await active.provider.request({ method: "wallet_switchEthereumChain", params: [{ chainId: toHex(n.chain_id) }] });
    } catch (e) {
      const code = (e as { code?: number }).code;
      if (code === 4902 || code === -32603) {
        try {
          await active.provider.request({
            method: "wallet_addEthereumChain",
            params: [
              {
                chainId: toHex(n.chain_id),
                chainName: n.name,
                nativeCurrency: { name: n.symbol, symbol: n.symbol, decimals: 18 },
                rpcUrls: [n.rpc_url],
                blockExplorerUrls: [n.explorer],
              },
            ],
          });
        } catch (e2) {
          setError(errMessage(e2));
          return;
        }
      } else {
        setError(errMessage(e));
        return;
      }
    }
    const cid = (await active.provider.request({ method: "eth_chainId" })) as string;
    setChainId(parseInt(cid, 16));
  }, [active, config]);

  const anchorWithWallet = useCallback(
    async (anchor: Anchor, onState: (s: TxState) => void) => {
      if (!active || !config?.contract_address) {
        onState({ phase: "failed", error: "Connect a wallet and configure the registry first." });
        return;
      }
      let hash: string | undefined;
      try {
        onState({ phase: "signing" });
        const provider = new BrowserProvider(active.provider as never);
        const signer = await provider.getSigner();
        const contract = new Contract(config.contract_address, config.abi as never, signer);
        const tx = await contract.anchorEvent(anchor.event_hash, anchor.workflow_id_hash, encodeBytes32String(anchor.event_type.slice(0, 31)));
        hash = tx.hash as string;
        onState({ phase: "pending", hash });
        const receipt = await tx.wait();
        if (!receipt || receipt.status !== 1) throw new Error("Transaction reverted on-chain");
        onState({ phase: "verifying", hash });
        // The backend independently re-reads the receipt and the contract before marking it confirmed.
        const verified = await api<Anchor>(`/api/blockchain/anchors/${anchor.id}/wallet-submission`, {
          method: "POST",
          body: JSON.stringify({ tx_hash: hash }),
        });
        if (verified.status !== "confirmed") throw new Error(verified.last_error ?? "Backend could not verify the anchor");
        onState({ phase: "confirmed", hash, anchor: verified });
      } catch (e) {
        onState({ phase: "failed", hash, error: errMessage(e) });
      }
    },
    [active, config],
  );

  const value = useMemo<WalletState>(
    () => ({
      wallets,
      walletName: active?.info.name ?? null,
      account,
      chainId,
      config,
      onMst: !!config && chainId === config.network.chain_id,
      connecting,
      error,
      connect,
      disconnect,
      switchToMst,
      anchorWithWallet,
    }),
    [wallets, active, account, chainId, config, connecting, error, connect, disconnect, switchToMst, anchorWithWallet],
  );
  return <WalletContext.Provider value={value}>{children}</WalletContext.Provider>;
}

export function useWallet() {
  const ctx = useContext(WalletContext);
  if (!ctx) throw new Error("useWallet outside WalletProvider");
  return ctx;
}
