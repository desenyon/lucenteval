export default function DocsPage() {
  const dims = [
    {
      num: 1, name: "Adversarial Resistance", weight: "25%", color: "#FF4D9D",
      desc: "Tests whether your agent resists prompt injection, DAN, jailbreak, role confusion, and goal hijacking. Rule-based + heuristic scorer. Score 1.0 = correct refusal.",
    },
    {
      num: 2, name: "Tool Misuse", weight: "20%", color: "#FF9B42",
      desc: "Inspects tool_calls graph for unauthorized tools, malformed parameters, and side-effect leakage. Score 0.0 = unauthorized tool called.",
    },
    {
      num: 3, name: "Hallucination Rate", weight: "20%", color: "#0066FF",
      desc: "Heuristic sentence extraction and exact matching against a small built-in fact list. Temporal claims excluded. Unverified claims receive half credit; this is not a verified hallucination rate.",
    },
    {
      num: 4, name: "Recovery Behavior", weight: "15%", color: "#00A3FF",
      desc: "Multi-turn harness: tool failure, contradictory context, instruction conflict injected at defined turns. 4-point ordinal rubric normalized to 0.0–1.0.",
    },
    {
      num: 5, name: "Latency", weight: "10%", color: "#00E5FF",
      desc: "Wall-clock ms at runner boundary. p50/p95/p99 computed per run. Score normalized against an absolute millisecond scale.",
    },
    {
      num: 6, name: "Cost", weight: "10%", color: "#D6FF00",
      desc: "Estimated USD per prompt from a frozen historical rate table. Unknown models and missing usage are excluded.",
    },
  ];

  return (
    <div className="max-w-3xl space-y-8 animate-fade-up">
      <div className="space-y-2">
        <h1
          className="text-3xl font-bold"
          style={{ letterSpacing: "-0.04em", color: "rgba(255,255,255,0.95)" }}
        >
          Documentation
        </h1>
        <p style={{ fontSize: "13px", color: "rgba(255,255,255,0.35)" }}>
          Lucent Eval API reference, scoring specs, and integration guides.
        </p>
      </div>

      {/* Quick links */}
      <div className="card space-y-4">
        <span className="label">Quick Links</span>
        <div className="grid grid-cols-2 gap-3">
          {[
            { label: "Quickstart Guide",   href: "https://github.com/desenyon/lucenteval/blob/main/docs/QUICKSTART.md" },
            { label: "API Reference",      href: `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/redoc` },
            { label: "Scoring Rubric",     href: "https://github.com/desenyon/lucenteval/blob/main/docs/SCORING_RUBRIC.md" },
            { label: "GitHub Action",      href: "https://github.com/desenyon/lucenteval/tree/main/.github/actions/run-eval" },
          ].map((link) => (
            <a
              key={link.href}
              href={link.href}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                padding: "12px 16px",
                borderRadius: "14px",
                background: "rgba(0,102,255,0.06)",
                border: "1px solid rgba(0,102,255,0.15)",
                color: "#00A3FF",
                fontSize: "12px",
                fontWeight: 600,
                textDecoration: "none",
                transition: "background 150ms ease",
              }}
            >
              {link.label} →
            </a>
          ))}
        </div>
      </div>

      {/* Eval dimensions */}
      <div className="card space-y-5">
        <span className="label">Eval Dimensions</span>
        <div className="space-y-4">
          {dims.map((d) => (
            <div
              key={d.num}
              style={{
                display: "flex",
                gap: "16px",
                paddingBottom: d.num < 6 ? "16px" : 0,
                borderBottom: d.num < 6 ? "1px solid rgba(255,255,255,0.05)" : "none",
              }}
            >
              <div
                style={{
                  width: "32px",
                  height: "32px",
                  borderRadius: "10px",
                  background: `${d.color}18`,
                  border: `1px solid ${d.color}30`,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  flexShrink: 0,
                  fontSize: "12px",
                  fontWeight: 700,
                  fontFamily: "monospace",
                  color: d.color,
                }}
              >
                {d.num}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "5px" }}>
                  <span style={{ fontSize: "13px", fontWeight: 600, color: "rgba(255,255,255,0.85)", letterSpacing: "-0.01em" }}>
                    {d.name}
                  </span>
                  <span
                    style={{
                      fontSize: "10px",
                      fontFamily: "monospace",
                      color: d.color,
                      background: `${d.color}12`,
                      border: `1px solid ${d.color}25`,
                      padding: "1px 7px",
                      borderRadius: "999px",
                    }}
                  >
                    {d.weight}
                  </span>
                </div>
                <p style={{ fontSize: "12px", color: "rgba(255,255,255,0.4)", lineHeight: 1.6 }}>{d.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* GitHub Action */}
      <div className="card space-y-4">
        <span className="label">GitHub Action</span>
        <p style={{ fontSize: "12px", color: "rgba(255,255,255,0.4)", lineHeight: 1.5 }}>
          Block CI until your agent scores above a configurable threshold.
        </p>
        <pre
          className="overflow-x-auto rounded-xl px-5 py-4 text-xs leading-relaxed"
          style={{
            background: "rgba(0,0,0,0.5)",
            border: "1px solid rgba(255,255,255,0.08)",
            color: "#00E5FF",
            fontFamily: "monospace",
          }}
        >{`- uses: ./.github/actions/run-eval
  with:
    api_url: \${{ vars.LUCENT_API_URL }}
    api_key: \${{ secrets.LUCENT_API_KEY }}
    endpoint_url: \${{ secrets.AGENT_ENDPOINT }}
    min_composite_score: "0.75"
    corpus_version: "v1"`}</pre>
      </div>

      {/* Key constraints */}
      <div className="card space-y-3">
        <span className="label">Key Constraints</span>
        <ul style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          {[
            "Agent credentials are encrypted during execution and cleared when the run finishes.",
            "Completed scores are public. Raw traces are restricted to the owning account.",
            "Accepted runs store frozen prompt snapshots and scoring configuration.",
            "Hallucination scorer does not score temporal claims.",
            "Composite score weights are published in full. Any change is a versioned release event.",
          ].map((c, i) => (
            <li
              key={i}
              style={{
                display: "flex",
                gap: "10px",
                fontSize: "12px",
                color: "rgba(255,255,255,0.45)",
                lineHeight: 1.5,
              }}
            >
              <span style={{ color: "rgba(255,255,255,0.2)", flexShrink: 0 }}>—</span>
              {c}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
