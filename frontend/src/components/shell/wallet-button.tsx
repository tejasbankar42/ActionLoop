"use client";

import { AlertTriangle, Link2, Wallet } from "lucide-react";
import { useState } from "react";
import { Dialog } from "@/components/ui/dialog";
import { Button } from "@/components/ui/primitives";
import { shortHash } from "@/lib/format";
import { useWallet } from "@/lib/wallet";

export function WalletButton({ compact }: { compact?: boolean }) {
  const w = useWallet();
  const [open, setOpen] = useState(false);

  if (!w.account) {
    return (
      <>
        <Button variant="outline" size="sm" onClick={() => (w.wallets.length > 1 ? setOpen(true) : w.connect())} loading={w.connecting}>
          <Wallet /> {compact ? "Connect" : "Connect BridgeKey"}
        </Button>
        <Dialog open={open} onOpenChange={setOpen} title="Choose a wallet" description="ActionLoop prefers BridgeKey, MST's official non-custodial wallet.">
          <div className="space-y-2">
            {w.wallets.map((x) => (
              <button
                key={x.info.uuid}
                onClick={() => {
                  setOpen(false);
                  w.connect(x.info.uuid);
                }}
                className="flex w-full items-center gap-3 rounded-xl border border-line p-3 text-left hover:border-teal"
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                {x.info.icon ? <img src={x.info.icon} alt="" className="size-7" /> : <Wallet className="size-7 text-ink-3" />}
                <span className="font-semibold text-ink">{x.info.name}</span>
              </button>
            ))}
          </div>
        </Dialog>
      </>
    );
  }
  if (!w.onMst) {
    return (
      <Button variant="warn" size="sm" onClick={w.switchToMst}>
        <AlertTriangle /> Switch to {w.config?.network.name ?? "MST"}
      </Button>
    );
  }
  return (
    <span className="inline-flex h-8 items-center gap-2 rounded-lg border border-line bg-surface px-2.5 text-xs font-semibold text-ink">
      <span className="size-2 rounded-full bg-ok" />
      <Link2 className="size-3.5 text-teal" />
      <span className="hash">{shortHash(w.account, 4)}</span>
      {!compact && <span className="text-ink-3">· {w.config?.network.name}</span>}
    </span>
  );
}
