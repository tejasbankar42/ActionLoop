"use client";

import { motion } from "framer-motion";
import { useEffect, useState } from "react";

/* Animated, data-driven illustration of one document moving through the agents.
 * The fields and checks shown are the real outputs for the bundled invoice sample. */

const STEPS = [
  { key: "doc", label: "Invoice.pdf", sub: "uploaded", color: "#98A2B3" },
  { key: "ex", label: "Extractor", sub: "9 fields · 96%", color: "#16B8A6" },
  { key: "va", label: "Validator", sub: "11 checks passed", color: "#6172F3" },
  { key: "ap", label: "Planner", sub: "payment review", color: "#9E77ED" },
  { key: "hu", label: "Reviewer", sub: "approved", color: "#0BA5EC" },
  { key: "au", label: "Audit + MST", sub: "hash anchored", color: "#16B8A6" },
];

const FIELDS = [
  ["Invoice No", "INV-2026-0918"],
  ["Vendor", "Pune TechSupplies"],
  ["GSTIN", "27AABCP1234Q1Z5"],
  ["Total", "₹48,560.00"],
];

export function HeroFlow() {
  const [step, setStep] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setStep((s) => (s + 1) % (STEPS.length + 2)), 1300);
    return () => clearInterval(id);
  }, []);
  const active = Math.min(step, STEPS.length - 1);

  return (
    <div className="relative rounded-3xl border border-white/10 bg-navy-2/80 p-5 shadow-2xl shadow-black/40 md:p-7">
      <div className="mb-5 flex items-center gap-2">
        <span className="size-2.5 rounded-full bg-[#F04438]/70" />
        <span className="size-2.5 rounded-full bg-[#F79009]/70" />
        <span className="size-2.5 rounded-full bg-[#12B76A]/70" />
        <span className="ml-3 text-xs text-[#98A2B3]">workflow · wf-3f9a21c4</span>
      </div>

      <div className="relative grid grid-cols-3 gap-3 sm:grid-cols-6">
        {STEPS.map((s, i) => {
          const done = i < active || step >= STEPS.length;
          const running = i === active && step < STEPS.length;
          return (
            <div key={s.key} className="relative flex flex-col items-center text-center">
              <motion.div
                animate={{ scale: running ? 1.08 : 1, opacity: done || running ? 1 : 0.45 }}
                className="relative grid size-14 place-items-center rounded-2xl border text-xs font-bold"
                style={{ borderColor: s.color, background: done || running ? `${s.color}22` : "transparent", color: s.color }}
              >
                {running && (
                  <motion.span
                    className="absolute inset-0 rounded-2xl border-2"
                    style={{ borderColor: s.color }}
                    animate={{ opacity: [0.8, 0], scale: [1, 1.35] }}
                    transition={{ duration: 1.1, repeat: Infinity }}
                  />
                )}
                {done ? "✓" : String(i + 1).padStart(2, "0")}
              </motion.div>
              <p className="mt-2 text-[12px] font-semibold text-white">{s.label}</p>
              <p className="text-[10.5px] text-[#98A2B3]">{s.sub}</p>
            </div>
          );
        })}
      </div>

      <div className="mt-6 grid gap-3 md:grid-cols-[1.2fr_1fr]">
        <div className="rounded-xl border border-white/10 bg-navy/60 p-4">
          <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-[#98A2B3]">Extracted fields</p>
          {FIELDS.map(([k, v], i) => (
            <motion.div
              key={k}
              initial={false}
              animate={{ opacity: active >= 1 ? 1 : 0.25, x: active >= 1 ? 0 : -6 }}
              transition={{ delay: i * 0.08 }}
              className="flex items-center justify-between border-b border-white/5 py-1.5 text-xs last:border-0"
            >
              <span className="text-[#98A2B3]">{k}</span>
              <span className="font-mono text-white">{v}</span>
            </motion.div>
          ))}
        </div>
        <div className="rounded-xl border border-white/10 bg-navy/60 p-4">
          <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-[#98A2B3]">Audit chain</p>
          {["WORKFLOW_STARTED", "VALIDATION_COMPLETED", "APPROVAL_DECISION"].map((e, i) => (
            <motion.div
              key={e}
              animate={{ opacity: active >= [0, 2, 4][i] ? 1 : 0.25 }}
              className="mb-1.5 flex items-center gap-2 text-[11px]"
            >
              <span className="size-1.5 rounded-full bg-teal" />
              <span className="font-mono text-white">{e}</span>
            </motion.div>
          ))}
          <motion.div
            animate={{ opacity: active >= 5 ? 1 : 0.2 }}
            className="mt-3 rounded-lg border border-teal/40 bg-teal/10 px-2.5 py-2 font-mono text-[10.5px] text-teal"
          >
            anchorEvent(0x8c4e…a91f) → MST Testnet
          </motion.div>
        </div>
      </div>
      <p className="mt-4 text-[11px] text-[#667085]">Illustration of the bundled invoice sample. Live runs happen inside the dashboard.</p>
    </div>
  );
}
