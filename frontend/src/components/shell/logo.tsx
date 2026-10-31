import { cn } from "@/lib/format";

export function LogoMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 64 64" fill="none" className={cn("size-8", className)} aria-hidden>
      <rect width="64" height="64" rx="14" fill="#101828" />
      <path d="M44.5 21.5A15 15 0 1 0 47 32" stroke="#16B8A6" strokeWidth="5" strokeLinecap="round" />
      <path d="M47 18v8.5h-8.5" stroke="#16B8A6" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="32" cy="32" r="4.5" fill="#F7F8FA" />
    </svg>
  );
}

export function Logo({ light, className }: { light?: boolean; className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-2.5", className)}>
      <LogoMark />
      <span className={cn("text-[17px] font-extrabold tracking-tight", light ? "text-white" : "text-ink")}>
        Action<span className="text-teal">Loop</span>
      </span>
    </span>
  );
}
