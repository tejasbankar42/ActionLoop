import {
  ArrowRight,
  Blocks,
  Building2,
  CheckCircle2,
  ClipboardCheck,
  FileSearch,
  GraduationCap,
  Hospital,
  Link2,
  ListChecks,
  Route,
  ShieldCheck,
  Store,
  UserCheck,
  XCircle,
} from "lucide-react";
import Link from "next/link";
import { HeroFlow } from "@/components/landing/hero-flow";
import { Logo } from "@/components/shell/logo";

const AGENTS = [
  {
    n: "01",
    name: "Extractor Agent",
    color: "#16B8A6",
    icon: FileSearch,
    lead: "Reads PDFs and images, identifies the document type and returns structured JSON.",
    points: ["Field-level confidence scores", "Missing and unreadable values flagged, never guessed", "Vision LLM in live mode, deterministic parser in demo mode"],
  },
  {
    n: "02",
    name: "Validator Agent",
    color: "#6172F3",
    icon: ListChecks,
    lead: "Applies configurable business rules and database checks. Deterministic by design.",
    points: ["Required fields, formats, ranges, dates", "Duplicate detection against stored records", "Every result: Passed, Warning or Failed — with a reason"],
  },
  {
    n: "03",
    name: "Action Planner",
    color: "#9E77ED",
    icon: Route,
    lead: "Turns findings into an ordered plan with departments, priorities and justification.",
    points: ["High-impact actions always require approval", "Blocks duplicates and invalid records", "Explains why each step is recommended"],
  },
];

const USERS = [
  { icon: GraduationCap, title: "Colleges", body: "Admission forms, fee receipts, student grievances." },
  { icon: Hospital, title: "Clinics", body: "Patient registration and front-desk intake." },
  { icon: Store, title: "Small businesses", body: "Vendor invoices, duplicate-payment prevention." },
  { icon: Building2, title: "Admin offices", body: "Complaint triage and department routing." },
];

export default function Landing() {
  return (
    <div className="bg-canvas text-ink">
      {/* NAV + HERO */}
      <div className="relative overflow-hidden bg-navy text-white">
        <div className="grid-paper pointer-events-none absolute inset-0 opacity-[0.12]" />
        <nav className="relative mx-auto flex h-20 max-w-7xl items-center justify-between px-5 md:px-8">
          <Logo light />
          <div className="hidden items-center gap-8 text-sm text-[#98A2B3] md:flex">
            <a href="#agents" className="hover:text-white">Agents</a>
            <a href="#human" className="hover:text-white">Human-in-the-loop</a>
            <a href="#audit" className="hover:text-white">Audit & MST</a>
            <a href="#team" className="hover:text-white">Team</a>
          </div>
          <Link href="/dashboard" className="rounded-lg bg-white px-4 py-2 text-sm font-semibold text-navy hover:bg-[#F2F4F7]">
            Launch Dashboard
          </Link>
        </nav>
        <section className="relative mx-auto grid max-w-7xl gap-12 px-5 pb-20 pt-10 md:px-8 lg:grid-cols-[1fr_1.1fr] lg:items-center lg:pb-28 lg:pt-16">
          <div>
            <p className="inline-flex items-center gap-2 rounded-full border border-white/15 px-3 py-1 text-xs font-semibold text-teal">
              <Blocks className="size-3.5" /> Multi-agent automation · anchored on MST Blockchain
            </p>
            <h1 className="mt-6 text-5xl font-extrabold leading-[1.02] tracking-tight md:text-6xl xl:text-7xl">
              Turn Documents
              <br />
              Into <span className="text-teal">Decisions.</span>
            </h1>
            <p className="mt-6 max-w-xl text-lg leading-relaxed text-[#B4BFD0]">
              ActionLoop reads administrative documents, checks them against your rules, plans the next step and asks a human before anything
              important happens. Every step lands in a tamper-evident audit trail anyone can verify on MSTScan.
            </p>
            <div className="mt-9 flex flex-wrap gap-3">
              <Link href="/dashboard" className="inline-flex h-12 items-center gap-2 rounded-lg bg-teal px-6 font-semibold text-white hover:bg-teal-ink">
                Launch Dashboard <ArrowRight className="size-4" />
              </Link>
              <Link href="/studio" className="inline-flex h-12 items-center gap-2 rounded-lg border border-white/20 px-6 font-semibold text-white hover:bg-white/5">
                Explore Workflow
              </Link>
            </div>
            <dl className="mt-12 grid max-w-lg grid-cols-3 gap-6 border-t border-white/10 pt-6">
              {[
                ["3", "specialised agents"],
                ["5", "document types"],
                ["SHA-256", "hash-chained audit"],
              ].map(([k, v]) => (
                <div key={v}>
                  <dt className="text-2xl font-extrabold">{k}</dt>
                  <dd className="text-xs text-[#98A2B3]">{v}</dd>
                </div>
              ))}
            </dl>
          </div>
          <HeroFlow />
        </section>
      </div>

      {/* PROBLEM / SOLUTION */}
      <section className="mx-auto max-w-7xl px-5 py-24 md:px-8">
        <div className="grid gap-px overflow-hidden rounded-3xl border border-line bg-line md:grid-cols-2">
          <div className="bg-surface p-8 md:p-12">
            <p className="text-sm font-bold uppercase tracking-[0.18em] text-bad">Today</p>
            <h2 className="mt-3 text-3xl font-extrabold tracking-tight">Paper moves. Accountability doesn&apos;t.</h2>
            <ul className="mt-8 space-y-4">
              {[
                "Staff retype invoices, forms and receipts by hand",
                "Missing fields surface weeks later, after payment",
                "The same invoice gets paid twice",
                "Nobody can prove who approved what, or when",
              ].map((t) => (
                <li key={t} className="flex gap-3 text-ink-2">
                  <XCircle className="mt-0.5 size-5 shrink-0 text-bad" /> {t}
                </li>
              ))}
            </ul>
          </div>
          <div className="bg-navy p-8 text-white md:p-12">
            <p className="text-sm font-bold uppercase tracking-[0.18em] text-teal">With ActionLoop</p>
            <h2 className="mt-3 text-3xl font-extrabold tracking-tight">Read, check, plan — then a human decides.</h2>
            <ul className="mt-8 space-y-4">
              {[
                "Fields extracted with confidence scores in seconds",
                "Rules and database checks run before anyone acts",
                "Duplicates are blocked automatically",
                "Approvals are hash-chained and anchored on MST Blockchain",
              ].map((t) => (
                <li key={t} className="flex gap-3 text-[#D0D5DD]">
                  <CheckCircle2 className="mt-0.5 size-5 shrink-0 text-teal" /> {t}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      {/* AGENTS */}
      <section id="agents" className="border-y border-line bg-surface py-24">
        <div className="mx-auto max-w-7xl px-5 md:px-8">
          <div className="max-w-2xl">
            <p className="text-sm font-bold uppercase tracking-[0.18em] text-teal">The agents</p>
            <h2 className="mt-3 text-4xl font-extrabold tracking-tight">Three specialists. One accountable loop.</h2>
            <p className="mt-4 text-ink-2">Orchestrated with LangGraph. Each agent has one job, a clear contract and an execution record you can inspect.</p>
          </div>
          <div className="mt-14 space-y-4">
            {AGENTS.map(({ n, name, color, icon: Icon, lead, points }) => (
              <div key={n} className="grid gap-6 rounded-2xl border border-line p-6 md:grid-cols-[120px_1fr_1.2fr] md:items-center md:p-8">
                <div className="flex items-center gap-4 md:block">
                  <span className="text-5xl font-extrabold tracking-tighter" style={{ color }}>
                    {n}
                  </span>
                  <Icon className="size-7 md:mt-3" style={{ color }} />
                </div>
                <div>
                  <h3 className="text-xl font-bold">{name}</h3>
                  <p className="mt-2 text-ink-2">{lead}</p>
                </div>
                <ul className="grid gap-2">
                  {points.map((p) => (
                    <li key={p} className="flex items-center gap-2.5 rounded-lg bg-surface-2 px-3 py-2 text-sm text-ink-2">
                      <span className="size-1.5 rounded-full" style={{ background: color }} /> {p}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* HUMAN IN THE LOOP */}
      <section id="human" className="mx-auto grid max-w-7xl gap-12 px-5 py-24 md:px-8 lg:grid-cols-2 lg:items-center">
        <div>
          <p className="text-sm font-bold uppercase tracking-[0.18em] text-a-human">Human-in-the-loop</p>
          <h2 className="mt-3 text-4xl font-extrabold tracking-tight">AI recommends. People approve.</h2>
          <p className="mt-4 text-ink-2">
            Payments, admissions, duplicates, unreadable values and urgent complaints pause at a persistent approval checkpoint. Reviewers see the
            reason, the evidence and the plan — then approve, reject or request a correction. Corrected values re-run validation before anything executes.
          </p>
        </div>
        <div className="rounded-2xl border border-line bg-surface p-6">
          <div className="flex items-center justify-between">
            <span className="text-sm font-bold">Fee receipt · FR-2026-11873</span>
            <span className="rounded-full bg-warn/15 px-2.5 py-0.5 text-xs font-semibold text-[#b54708]">Needs verification</span>
          </div>
          <div className="mt-4 space-y-2 text-sm">
            <div className="flex justify-between rounded-lg bg-surface-2 px-3 py-2">
              <span className="text-ink-2">Amount Paid</span>
              <span className="font-mono text-bad">unreadable “4?,500.00” · 41%</span>
            </div>
            <div className="flex justify-between rounded-lg bg-surface-2 px-3 py-2">
              <span className="text-ink-2">Payment Date</span>
              <span className="font-mono text-bad">unreadable “1?/10/2026” · 41%</span>
            </div>
          </div>
          <div className="mt-5 flex flex-wrap gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-lg bg-teal px-3 py-2 text-xs font-semibold text-white">
              <UserCheck className="size-4" /> Approve with corrections
            </span>
            <span className="rounded-lg border border-line px-3 py-2 text-xs font-semibold">Request correction</span>
            <span className="rounded-lg border border-line px-3 py-2 text-xs font-semibold text-bad">Reject</span>
          </div>
        </div>
      </section>

      {/* AUDIT + MST */}
      <section id="audit" className="bg-navy py-24 text-white">
        <div className="mx-auto max-w-7xl px-5 md:px-8">
          <div className="grid gap-12 lg:grid-cols-[1fr_1.2fr]">
            <div>
              <p className="text-sm font-bold uppercase tracking-[0.18em] text-teal">Audit & accountability</p>
              <h2 className="mt-3 text-4xl font-extrabold tracking-tight">Two layers of proof.</h2>
              <p className="mt-4 text-[#B4BFD0]">
                Every event is appended to a SHA-256 hash chain: <code className="font-mono text-teal">hash = SHA256(prev_hash + event)</code>. Key decisions
                are then anchored in the ActionLoop Audit Registry smart contract on MST Blockchain. Only hashes go on-chain — never documents or personal data.
              </p>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="rounded-2xl border border-white/10 bg-navy-2 p-6">
                <ClipboardCheck className="size-6 text-teal" />
                <h3 className="mt-4 font-bold">Off-chain audit</h3>
                <p className="mt-2 text-sm text-[#98A2B3]">Full event history, extracted data and reviewer comments. Recomputed and verified on demand; any edit breaks the chain.</p>
              </div>
              <div className="rounded-2xl border border-teal/40 bg-teal/10 p-6">
                <Link2 className="size-6 text-teal" />
                <h3 className="mt-4 font-bold">On-chain verification</h3>
                <p className="mt-2 text-sm text-[#B4BFD0]">Event hash, hashed workflow ID, event type and submitter — independently checkable on MSTScan.</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-navy-2 p-6 sm:col-span-2">
                <div className="flex items-center gap-3 font-mono text-xs text-[#98A2B3]">
                  <ShieldCheck className="size-5 text-teal" />
                  <span>BridgeKey wallet · relayer · receipt verified · isAnchored(hash) == true</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* TARGET USERS + OUTCOMES */}
      <section className="mx-auto max-w-7xl px-5 py-24 md:px-8">
        <h2 className="text-4xl font-extrabold tracking-tight">Built for the offices that run on paperwork.</h2>
        <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {USERS.map(({ icon: Icon, title, body }) => (
            <div key={title} className="rounded-2xl border border-line bg-surface p-6">
              <Icon className="size-6 text-teal" />
              <h3 className="mt-4 font-bold">{title}</h3>
              <p className="mt-1 text-sm text-ink-2">{body}</p>
            </div>
          ))}
        </div>
        <div className="mt-16 grid gap-8 border-t border-line pt-12 md:grid-cols-3">
          {[
            ["Seconds, not days", "Automated extraction, validation and planning runs in a few seconds per document in our demo."],
            ["Zero silent approvals", "Invalid, duplicate or uncertain records can never pass without a named reviewer."],
            ["Provable history", "Hash-chain verification detects any altered record; MST anchors make it independently checkable."],
          ].map(([t, b]) => (
            <div key={t}>
              <h3 className="text-lg font-bold">{t}</h3>
              <p className="mt-2 text-sm text-ink-2">{b}</p>
            </div>
          ))}
        </div>
      </section>

      {/* FOOTER */}
      <footer id="team" className="border-t border-line bg-surface">
        <div className="mx-auto grid max-w-7xl gap-10 px-5 py-14 md:grid-cols-[1.3fr_1fr_1fr] md:px-8">
          <div>
            <Logo />
            <p className="mt-3 max-w-sm text-sm text-ink-2">From Documents to Decisions. Automatically. Built for MST Blockchain Buildathon 2.0.</p>
          </div>
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-ink-3">Team Granted</p>
            <ul className="mt-3 space-y-1.5 text-sm text-ink">
              <li>Aditya Shelke</li>
              <li>Tejas Bankar</li>
              <li>Siddhika Hanumante</li>
            </ul>
          </div>
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-ink-3">Institution</p>
            <p className="mt-3 text-sm text-ink">Nutan Maharashtra Institute of Engineering and Technology (NMIET), Pune</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
