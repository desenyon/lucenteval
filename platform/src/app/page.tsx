import Link from "next/link";

const dims = [
  { name: "Adversarial", weight: "25%", desc: "Injection, jailbreak, DAN, role confusion", color: "#FF4D9D", glow: "rgba(255,0,110,0.25)" },
  { name: "Tool Misuse", weight: "20%", desc: "Call graph inspection, side-effect leakage", color: "#FF9B42", glow: "rgba(255,155,66,0.25)" },
  { name: "Hallucination", weight: "20%", desc: "Claim grounding vs versioned fact corpus", color: "#00E5FF", glow: "rgba(0,229,255,0.25)" },
  { name: "Recovery", weight: "15%", desc: "Multi-turn error injection harness", color: "#00A3FF", glow: "rgba(0,163,255,0.25)" },
  { name: "Latency", weight: "10%", desc: "p50 / p95 / p99 wall-clock at runner", color: "#D6FF00", glow: "rgba(214,255,0,0.25)" },
  { name: "Cost", weight: "10%", desc: "USD per prompt, versioned rate table", color: "#0066FF", glow: "rgba(0,102,255,0.25)" },
];

export default function HomePage() {
  return (
    <div className="space-y-20 py-4 animate-fade-up">

      {/* ── Hero ─────────────────────────────────────────────────────────────── */}
      <section className="text-center space-y-8 pt-12">
        {/* Status chip */}
        <div className="flex justify-center">
          <span
            className="inline-flex items-center gap-2 px-4 py-1.5 rounded-pill text-xs font-semibold"
            style={{
              background: "rgba(0,102,255,0.1)",
              border: "1px solid rgba(0,102,255,0.3)",
              color: "#00A3FF",
              boxShadow: "0 0 20px rgba(0,102,255,0.15)",
              letterSpacing: "0.03em",
            }}
          >
            <span
              className="w-1.5 h-1.5 rounded-full animate-pulse-glow"
              style={{ background: "#0066FF" }}
            />
            PUBLIC BETA
          </span>
        </div>

        <div className="space-y-5">
          <h1
            className="text-5xl md:text-7xl font-bold tracking-tight max-w-3xl mx-auto leading-[1.05]"
            style={{ letterSpacing: "-0.04em", color: "rgba(255,255,255,0.96)" }}
          >
            Adversarial eval for{" "}
            <span className="gradient-text">production AI</span>
          </h1>
          <p
            className="text-base md:text-lg max-w-xl mx-auto leading-relaxed"
            style={{ color: "rgba(255,255,255,0.45)", letterSpacing: "-0.01em" }}
          >
            Register your agent endpoint. Run against 500+ categorized adversarial prompts.
            Score across 6 dimensions. Land on the public leaderboard.
          </p>
        </div>

        <div className="flex items-center justify-center gap-3">
          <Link href="/dashboard/runs/new" className="btn-primary" style={{ padding: "12px 28px", fontSize: "14px" }}>
            Run First Eval →
          </Link>
          <Link href="/leaderboard" className="btn-secondary" style={{ padding: "12px 28px", fontSize: "14px" }}>
            View Leaderboard
          </Link>
        </div>

        {/* Ambient glow under hero */}
        <div
          className="absolute left-1/2 -translate-x-1/2 pointer-events-none"
          style={{
            width: "800px",
            height: "400px",
            background: "radial-gradient(ellipse 60% 50% at 50% 50%, rgba(0,102,255,0.12), transparent 70%)",
            filter: "blur(40px)",
            top: "0",
            zIndex: -1,
          }}
        />
      </section>

      {/* ── Dimension cards ──────────────────────────────────────────────────── */}
      <section className="space-y-5">
        <div className="flex items-center justify-between">
          <h2
            className="text-sm font-semibold"
            style={{ color: "rgba(255,255,255,0.35)", letterSpacing: "0.06em", textTransform: "uppercase" }}
          >
            Eval Dimensions
          </h2>
          <span style={{ fontSize: "12px", color: "rgba(255,255,255,0.25)" }}>6 scorers · corpus v1</span>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {dims.map((dim) => (
            <div
              key={dim.name}
              className="card group"
              style={{ padding: "22px 24px" }}
            >
              {/* Color accent line */}
              <div
                className="absolute top-0 left-6 right-6 h-px"
                style={{
                  background: `linear-gradient(90deg, transparent, ${dim.color}55, transparent)`,
                }}
              />

              <div className="space-y-3">
                <div className="flex items-start justify-between">
                  <div
                    className="w-8 h-8 rounded-xl flex items-center justify-center"
                    style={{
                      background: `${dim.color}14`,
                      border: `1px solid ${dim.color}28`,
                      boxShadow: `0 0 16px ${dim.glow}`,
                    }}
                  >
                    <div className="w-2 h-2 rounded-full" style={{ background: dim.color }} />
                  </div>
                  <span
                    className="font-mono text-xs font-bold"
                    style={{ color: dim.color, letterSpacing: "0.02em" }}
                  >
                    {dim.weight}
                  </span>
                </div>
                <div>
                  <div
                    className="font-semibold text-sm"
                    style={{ color: "rgba(255,255,255,0.90)", letterSpacing: "-0.02em" }}
                  >
                    {dim.name}
                  </div>
                  <div
                    className="text-xs mt-1 leading-relaxed"
                    style={{ color: "rgba(255,255,255,0.35)" }}
                  >
                    {dim.desc}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── How it works ─────────────────────────────────────────────────────── */}
      <section className="space-y-6">
        <h2
          className="text-sm font-semibold"
          style={{ color: "rgba(255,255,255,0.35)", letterSpacing: "0.06em", textTransform: "uppercase" }}
        >
          How it works
        </h2>
        <div className="grid md:grid-cols-3 gap-4">
          {[
            {
              n: "01",
              title: "Register endpoint",
              desc: "POST your agent's HTTPS URL, auth headers, and optional system prompt override.",
              color: "#FF4D9D",
            },
            {
              n: "02",
              title: "Run eval suite",
              desc: "500+ adversarial prompts fire against your endpoint. Every response is captured atomically.",
              color: "#0066FF",
            },
            {
              n: "03",
              title: "Score & rank",
              desc: "6 scorers produce normalized 0–1 scores. Composite score lands on the public leaderboard.",
              color: "#00E5FF",
            },
          ].map((step) => (
            <div key={step.n} className="card" style={{ padding: "24px 26px" }}>
              <div className="space-y-3">
                <div
                  className="font-mono text-3xl font-bold"
                  style={{ color: step.color, letterSpacing: "-0.04em", opacity: 0.7 }}
                >
                  {step.n}
                </div>
                <div
                  className="font-semibold text-sm"
                  style={{ color: "rgba(255,255,255,0.90)", letterSpacing: "-0.02em" }}
                >
                  {step.title}
                </div>
                <div
                  className="text-xs leading-relaxed"
                  style={{ color: "rgba(255,255,255,0.4)" }}
                >
                  {step.desc}
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── CTA banner ───────────────────────────────────────────────────────── */}
      <section
        className="card text-center py-12 px-8 space-y-5"
        style={{
          background: "linear-gradient(160deg, rgba(0,102,255,0.18) 0%, rgba(0,102,255,0.12) 50%, rgba(0,0,0,0) 100%)",
          borderColor: "rgba(0,102,255,0.2)",
          boxShadow: "0 0 80px rgba(0,102,255,0.12), 0 0 160px rgba(0,102,255,0.08)",
        }}
      >
        <div
          className="text-2xl font-bold"
          style={{ letterSpacing: "-0.03em", color: "rgba(255,255,255,0.93)" }}
        >
          All scores are public. No private mode.
        </div>
        <p style={{ fontSize: "14px", color: "rgba(255,255,255,0.4)" }}>
          Corpus versions are immutable. Weights are versioned. Historical scores never recomputed.
        </p>
        <Link
          href="/dashboard/runs/new"
          className="btn-primary"
          style={{ padding: "12px 32px", fontSize: "14px" }}
        >
          Benchmark your agent →
        </Link>
      </section>
    </div>
  );
}
