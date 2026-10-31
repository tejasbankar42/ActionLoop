"use client";

import { AuthProvider } from "@/lib/auth";
import { WalletProvider } from "@/lib/wallet";
import { Toaster } from "./ui/toast";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <WalletProvider>
        <Toaster>{children}</Toaster>
      </WalletProvider>
    </AuthProvider>
  );
}
