"use client";

import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { Loader2 } from "lucide-react";
import * as React from "react";
import { cn } from "@/lib/format";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal/50 disabled:pointer-events-none disabled:opacity-50 [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        primary: "bg-teal text-white hover:bg-teal-ink",
        dark: "bg-navy text-white hover:bg-navy-2 dark:bg-surface-2 dark:hover:bg-line",
        outline: "border border-line bg-surface text-ink hover:bg-surface-2",
        ghost: "text-ink-2 hover:bg-surface-2 hover:text-ink",
        danger: "bg-bad text-white hover:bg-bad/90",
        warn: "bg-warn text-white hover:bg-warn/90",
      },
      size: { sm: "h-8 px-3 text-xs", md: "h-10 px-4", lg: "h-12 px-6 text-base", icon: "h-9 w-9" },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  loading?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild, loading, children, disabled, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp ref={ref} className={cn(buttonVariants({ variant, size }), className)} disabled={disabled || loading} {...props}>
        {asChild ? (
          children
        ) : (
          <>
            {loading && <Loader2 className="animate-spin" />}
            {children}
          </>
        )}
      </Comp>
    );
  },
);
Button.displayName = "Button";

export function Panel({
  className,
  title,
  subtitle,
  action,
  children,
  bodyClass,
}: {
  className?: string;
  title?: React.ReactNode;
  subtitle?: React.ReactNode;
  action?: React.ReactNode;
  children: React.ReactNode;
  bodyClass?: string;
}) {
  return (
    <section className={cn("rounded-[var(--radius-card)] border border-line bg-surface", className)}>
      {(title || action) && (
        <header className="flex items-start justify-between gap-4 border-b border-line px-5 py-4">
          <div className="min-w-0">
            {title && <h2 className="text-[15px] font-bold tracking-tight text-ink">{title}</h2>}
            {subtitle && <p className="mt-0.5 text-xs text-ink-3">{subtitle}</p>}
          </div>
          {action}
        </header>
      )}
      <div className={cn("p-5", bodyClass)}>{children}</div>
    </section>
  );
}

const TONES = {
  ok: "bg-ok/12 text-[#067647] ring-ok/30 dark:text-[#47cd89]",
  warn: "bg-warn/12 text-[#b54708] ring-warn/30 dark:text-[#fdb022]",
  bad: "bg-bad/10 text-[#b42318] ring-bad/30 dark:text-[#f97066]",
  info: "bg-teal/10 text-teal-ink ring-teal/30 dark:text-teal",
  neutral: "bg-surface-2 text-ink-2 ring-line",
  live: "bg-a-human/10 text-[#026aa2] ring-a-human/30 dark:text-[#36bffa]",
} as const;
export type Tone = keyof typeof TONES;

const STATUS_TONE: Record<string, Tone> = {
  completed: "ok", passed: "ok", approved: "ok", confirmed: "ok", verified: "ok", executed: "ok", ok: "ok", processed: "ok", valid: "ok", corrected: "info",
  warning: "warn", awaiting_approval: "warn", pending: "warn", uncertain: "warn", needs_correction: "warn", correction_requested: "warn", queued: "neutral", waiting: "warn", submitted: "live",
  failed: "bad", rejected: "bad", missing: "bad", blocked: "bad", mismatch: "bad", invalid: "bad",
  running: "live", processing: "live",
};
const STATUS_LABEL: Record<string, string> = {
  awaiting_approval: "Awaiting approval",
  needs_correction: "Needs correction",
  correction_requested: "Correction requested",
  not_configured: "Not configured",
  not_anchored: "Not anchored",
};

export function StatusPill({ status, tone, className, children }: { status?: string; tone?: Tone; className?: string; children?: React.ReactNode }) {
  const t = tone ?? STATUS_TONE[status ?? ""] ?? "neutral";
  const label = children ?? STATUS_LABEL[status ?? ""] ?? (status ? status.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase()) : "");
  return (
    <span className={cn("inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset", TONES[t], className)}>
      <span className={cn("size-1.5 rounded-full bg-current", (t === "live" || status === "running") && "animate-pulse")} />
      {label}
    </span>
  );
}

export function Confidence({ value, status }: { value: number; status?: string }) {
  const color = status === "missing" ? "var(--bad)" : value >= 0.85 ? "var(--ok)" : value >= 0.6 ? "var(--warn)" : "var(--bad)";
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-16 overflow-hidden rounded-full bg-surface-2">
        <div className="h-full rounded-full" style={{ width: `${Math.round(value * 100)}%`, background: color }} />
      </div>
      <span className="w-9 text-right text-xs tabular-nums text-ink-2">{Math.round(value * 100)}%</span>
    </div>
  );
}

export function Empty({ icon, title, children }: { icon?: React.ReactNode; title: string; children?: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 px-6 py-10 text-center">
      {icon && <div className="text-ink-3 [&_svg]:size-7">{icon}</div>}
      <p className="text-sm font-semibold text-ink">{title}</p>
      {children && <div className="max-w-sm text-xs text-ink-3">{children}</div>}
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-pulse rounded-md bg-surface-2", className)} />;
}

export function Kbd({ children }: { children: React.ReactNode }) {
  return <code className="hash rounded bg-surface-2 px-1.5 py-0.5 text-ink-2">{children}</code>;
}

export function Textarea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      {...props}
      className={cn(
        "w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink placeholder:text-ink-3 focus:border-teal focus:outline-none focus:ring-2 focus:ring-teal/20",
        props.className,
      )}
    />
  );
}

export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={cn(
        "h-10 w-full rounded-lg border border-line bg-surface px-3 text-sm text-ink placeholder:text-ink-3 focus:border-teal focus:outline-none focus:ring-2 focus:ring-teal/20",
        props.className,
      )}
    />
  );
}
