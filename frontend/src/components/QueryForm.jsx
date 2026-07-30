import { useState } from "react";

const DEPTHS = [
  { value: "quick", label: "Quick", hint: "3 threads" },
  { value: "standard", label: "Standard", hint: "5 threads" },
  { value: "deep", label: "Deep", hint: "7 threads" },
];

const AUDIENCES = [
  { value: "general", label: "General reader" },
  { value: "technical", label: "Technical" },
  { value: "executive", label: "Executive" },
];

function Pill({ active, onClick, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full border-[1.5px] px-3.5 py-1.5 text-sm font-medium transition-all duration-200 ease-out ${
        active
          ? "border-transparent bg-gradient-to-r from-plausible to-bloom text-[#1B1305] shadow-glow-amber -translate-y-px"
          : "border-rule/80 bg-white/[0.02] text-ash hover:border-mystic/60 hover:text-bone hover:-translate-y-px hover:shadow-glow-mystic"
      }`}
    >
      {children}
    </button>
  );
}

export default function QueryForm({ onSubmit, disabled, errorMessage }) {
  const [query, setQuery] = useState("");
  const [depth, setDepth] = useState("standard");
  const [audience, setAudience] = useState("general");
  const [focused, setFocused] = useState(false);

  function handleSubmit(e) {
    e.preventDefault();
    if (!query.trim() || disabled) return;
    onSubmit({ query: query.trim(), depth, audience });
  }

  return (
    <div className="w-full max-w-2xl relative">
      {/* Wax-seal emblem, stamped on the corner of the intake card */}
      <div
        aria-hidden
        className="seal absolute -top-4 -right-3 sm:right-3 z-10 flex h-14 w-14 rotate-[-8deg] items-center justify-center rounded-full animate-sealPop"
      >
        <svg viewBox="0 0 24 24" className="h-6 w-6 text-white/85" fill="none">
          <circle cx="12" cy="12" r="7.5" stroke="currentColor" strokeWidth="1.1" />
          <path d="M12 6.2v2.1M12 15.7v2.1M6.2 12h2.1M15.7 12h2.1" stroke="currentColor" strokeWidth="1.1" strokeLinecap="round" />
          <circle cx="12" cy="12" r="2" fill="currentColor" />
        </svg>
      </div>

      <div className="gradient-border shadow-card">
        <div className="glass-card px-6 py-8 sm:px-10 sm:py-10">
          <form onSubmit={handleSubmit}>
            <div className="mb-6 flex items-center gap-3 text-ash">
              <span className="font-mono text-xs tracking-[0.2em] uppercase">Case Intake</span>
              <span className="h-px flex-1 bg-gradient-to-r from-rule via-rule to-transparent" />
            </div>

            <label className="block font-display text-2xl sm:text-3xl mb-4 leading-snug gradient-text">
              What do you want researched?
            </label>

            <div className="relative">
              <span
                aria-hidden
                className={`bracket-corner left-0 top-0 border-l-2 border-t-2 rounded-tl-md ${focused ? "border-plausible opacity-100" : "border-mystic/70"}`}
              />
              <span
                aria-hidden
                className={`bracket-corner right-0 bottom-0 border-r-2 border-b-2 rounded-br-md ${focused ? "border-plausible opacity-100" : "border-mystic/70"}`}
              />
              <textarea
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onFocus={() => setFocused(true)}
                onBlur={() => setFocused(false)}
                placeholder="e.g. What is the current scientific consensus on intermittent fasting for weight loss?"
                rows={3}
                className={`w-full resize-none rounded-lg border bg-black/20 backdrop-blur-sm px-4 py-3 text-bone placeholder:text-ash/60 font-sans outline-none transition-all duration-300 ${
                  focused
                    ? "border-plausible/70 shadow-glow-amber-lg"
                    : "border-rule shadow-[0_1px_0_rgba(255,255,255,0.02)_inset]"
                }`}
              />
            </div>

            <div className="mt-8 space-y-6">
              <div>
                <div className="mb-2.5 font-mono text-[11px] uppercase tracking-wider text-ash">Depth</div>
                <div className="flex flex-wrap gap-2.5">
                  {DEPTHS.map((d) => (
                    <Pill key={d.value} active={depth === d.value} onClick={() => setDepth(d.value)}>
                      {d.label} <span className="opacity-70">· {d.hint}</span>
                    </Pill>
                  ))}
                </div>
              </div>

              <div>
                <div className="mb-2.5 font-mono text-[11px] uppercase tracking-wider text-ash">Report for</div>
                <div className="flex flex-wrap gap-2.5">
                  {AUDIENCES.map((a) => (
                    <Pill key={a.value} active={audience === a.value} onClick={() => setAudience(a.value)}>
                      {a.label}
                    </Pill>
                  ))}
                </div>
              </div>
            </div>

            {errorMessage && (
              <p className="mt-5 rounded-md border border-contradicted/40 bg-contradicted/10 px-3 py-2 text-sm text-contradicted">
                {errorMessage}
              </p>
            )}

            <button
              type="submit"
              disabled={disabled || !query.trim()}
              className="group relative mt-8 inline-flex items-center gap-2 overflow-hidden rounded-md bg-gradient-to-r from-plausible via-bloom to-mystic bg-[length:200%_100%] px-5 py-2.5 font-sans text-sm font-semibold text-[#1B1305] shadow-glow-amber transition-all duration-200 hover:-translate-y-0.5 hover:bg-right hover:shadow-glow-amber-lg disabled:translate-y-0 disabled:opacity-40 disabled:shadow-none disabled:cursor-not-allowed"
            >
              <span
                aria-hidden
                className="pointer-events-none absolute inset-0 bg-gradient-to-r from-transparent via-white/40 to-transparent bg-[length:250%_100%] opacity-0 transition-opacity duration-300 group-hover:opacity-100 group-hover:animate-shimmer"
              />
              <span className="relative">Open the case</span>
              <span aria-hidden className="relative transition-transform duration-200 group-hover:translate-x-1">→</span>
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}