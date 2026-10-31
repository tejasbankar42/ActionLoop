"use client";

import {
  BarChart3,
  Blocks,
  Bot,
  FileStack,
  LayoutDashboard,
  LogOut,
  Menu,
  ScrollText,
  Settings,
  ShieldCheck,
  Workflow,
  X,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import type { SystemStatus } from "@/lib/types";
import { Logo } from "./logo";
import { WalletButton } from "./wallet-button";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/documents", label: "Documents", icon: FileStack },
  { href: "/studio", label: "Workflow Studio", icon: Workflow },
  { href: "/agents", label: "Agent Intelligence", icon: Bot },
  { href: "/approvals", label: "Approvals", icon: ShieldCheck, badge: true },
  { href: "/audit", label: "Audit & Trace", icon: ScrollText },
  { href: "/blockchain", label: "MST Blockchain", icon: Blocks },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, ready, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const { data: sys } = useApi<SystemStatus>(user ? "/api/system/status" : null);
  const { data: pending } = useApi<unknown[]>(user ? "/api/approvals/pending" : null, 5000);

  useEffect(() => {
    if (ready && !user) router.replace(`/login?next=${encodeURIComponent(pathname)}`);
  }, [ready, user, router, pathname]);
  useEffect(() => setOpen(false), [pathname]);

  if (!ready || !user) {
    return <div className="grid min-h-screen place-items-center bg-canvas text-sm text-ink-3">Loading ActionLoop…</div>;
  }
  const current = NAV.find((n) => pathname.startsWith(n.href));

  return (
    <div className="min-h-screen bg-canvas">
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex w-64 flex-col bg-navy text-white transition-transform lg:translate-x-0",
          open ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="flex h-16 items-center justify-between px-5">
          <Link href="/">
            <Logo light />
          </Link>
          <button className="lg:hidden" onClick={() => setOpen(false)} aria-label="Close menu">
            <X className="size-5" />
          </button>
        </div>
        <nav className="flex-1 space-y-0.5 overflow-y-auto px-3 py-3">
          {NAV.map(({ href, label, icon: Icon, badge }) => {
            const active = pathname.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  "group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                  active ? "bg-white/10 text-white" : "text-[#98A2B3] hover:bg-white/5 hover:text-white",
                )}
              >
                <Icon className={cn("size-[18px]", active ? "text-teal" : "text-[#667085] group-hover:text-[#98A2B3]")} />
                <span className="flex-1">{label}</span>
                {badge && pending && pending.length > 0 && (
                  <span className="rounded-full bg-warn px-2 py-0.5 text-[11px] font-bold text-navy">{pending.length}</span>
                )}
                {active && <span className="h-5 w-1 rounded-full bg-teal" />}
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-white/10 p-4">
          <div className="mb-3 rounded-lg bg-white/5 p-3 text-xs">
            <p className="font-semibold">{user.full_name}</p>
            <p className="text-[#98A2B3]">
              {user.role} · {user.department}
            </p>
          </div>
          <button
            onClick={() => {
              logout();
              router.replace("/login");
            }}
            className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-[#98A2B3] hover:bg-white/5 hover:text-white"
          >
            <LogOut className="size-4" /> Sign out
          </button>
        </div>
      </aside>
      {open && <div className="fixed inset-0 z-30 bg-navy/40 lg:hidden" onClick={() => setOpen(false)} />}

      <div className="lg:pl-64">
        <header className="sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-line bg-canvas/85 px-4 backdrop-blur md:px-8">
          <button className="rounded-md p-1.5 text-ink lg:hidden" onClick={() => setOpen(true)} aria-label="Open menu">
            <Menu className="size-5" />
          </button>
          <h1 className="truncate text-base font-bold tracking-tight text-ink md:text-lg">{current?.label ?? "ActionLoop"}</h1>
          <div className="ml-auto flex items-center gap-2">
            {sys?.demo_mode && (
              <span
                title="No LLM API key configured: PDFs are parsed by deterministic rules, images need human entry, and all executed actions are simulated."
                className="hidden rounded-md bg-warn/15 px-2.5 py-1 text-[11px] font-bold uppercase tracking-wider text-[#b54708] ring-1 ring-warn/30 sm:inline dark:text-[#fdb022]"
              >
                Demo mode
              </span>
            )}
            <WalletButton compact />
          </div>
        </header>
        <main className="mx-auto max-w-[1440px] px-4 py-6 md:px-8 md:py-8">{children}</main>
      </div>
    </div>
  );
}
