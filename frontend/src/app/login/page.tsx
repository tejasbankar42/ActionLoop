"use client";

import { ArrowRight, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { Logo } from "@/components/shell/logo";
import { Button, Input } from "@/components/ui/primitives";
import { useAuth } from "@/lib/auth";

const DEMO = [
  { email: "reviewer@actionloop.demo", role: "Reviewer", who: "Siddhika Hanumante · approves & rejects" },
  { email: "admin@actionloop.demo", role: "Admin", who: "Aditya Shelke · rules & blockchain" },
  { email: "operator@actionloop.demo", role: "Operator", who: "Tejas Bankar · uploads & runs" },
  { email: "viewer@actionloop.demo", role: "Viewer", who: "Read-only judge account" },
];

function LoginForm() {
  const { login, user } = useAuth();
  const router = useRouter();
  const next = useSearchParams().get("next") || "/dashboard";
  const [email, setEmail] = useState(DEMO[0].email);
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (user) router.replace(next);
  }, [user, next, router]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(email, password);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-[1.05fr_1fr]">
      <div className="relative hidden overflow-hidden bg-navy p-12 text-white lg:flex lg:flex-col">
        <div className="grid-paper absolute inset-0 opacity-[0.15]" />
        <Link href="/" className="relative">
          <Logo light />
        </Link>
        <div className="relative mt-auto max-w-md">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-teal">Team Granted · NMIET Pune</p>
          <h1 className="mt-4 text-4xl font-extrabold leading-tight tracking-tight">Every decision traceable. Every hash verifiable.</h1>
          <p className="mt-4 text-[#98A2B3]">
            Three agents read, check and plan. A human approves what matters. The audit trail is hash-chained and anchored on MST Blockchain.
          </p>
        </div>
      </div>
      <div className="flex items-center justify-center bg-canvas p-6">
        <form onSubmit={submit} className="w-full max-w-sm">
          <Link href="/" className="lg:hidden">
            <Logo />
          </Link>
          <h2 className="mt-8 text-2xl font-extrabold tracking-tight text-ink lg:mt-0">Sign in</h2>
          <p className="mt-1 text-sm text-ink-2">Use a demo account below. Password for all: <code className="hash">ActionLoop@2026</code></p>
          <div className="mt-6 space-y-3">
            <label className="block text-xs font-semibold text-ink-2">
              Email
              <Input className="mt-1" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="username" />
            </label>
            <label className="block text-xs font-semibold text-ink-2">
              Password
              <Input className="mt-1" type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" />
            </label>
            {error && <p className="rounded-lg bg-bad/10 px-3 py-2 text-sm text-bad">{error}</p>}
            <Button type="submit" className="w-full" size="lg" loading={busy}>
              Sign in <ArrowRight />
            </Button>
          </div>
          <div className="mt-8 space-y-2">
            <p className="text-xs font-semibold uppercase tracking-wider text-ink-3">Demo accounts</p>
            {DEMO.map((d) => (
              <button
                type="button"
                key={d.email}
                onClick={() => {
                  setEmail(d.email);
                  setPassword("ActionLoop@2026");
                }}
                className="flex w-full items-center gap-3 rounded-xl border border-line bg-surface px-3 py-2.5 text-left hover:border-teal"
              >
                <ShieldCheck className="size-4 text-teal" />
                <span className="flex-1">
                  <span className="block text-sm font-semibold text-ink">{d.role}</span>
                  <span className="block text-xs text-ink-3">{d.who}</span>
                </span>
              </button>
            ))}
          </div>
        </form>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}
