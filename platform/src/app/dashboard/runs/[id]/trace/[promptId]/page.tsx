"use client";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { runsApi } from "@/lib/api";
import { ScoreBadge, ScoreBar } from "@/components/ScoreBadge";
import Link from "next/link";

interface CallGraphNode { id: string; name: string; flagged: boolean; index: number; }
interface CallGraph { nodes: CallGraphNode[]; edges: Array<{ from: string; to: string }>; }

export default function TraceViewPage() {
  const { id, promptId } = useParams<{ id: string; promptId: string }>();

  const { data: trace, isLoading } = useQuery({
    queryKey: ["trace", id, promptId],
    queryFn: () => runsApi.trace(id, promptId),
  });

  if (isLoading)
    return (
      <div className="flex items-center justify-center py-32">
        <div
          className="w-8 h-8 rounded-full border-2 border-electric"
          style={{ borderTopColor: "transparent", animation: "spin-slow 0.8s linear infinite" }}
        />
      </div>
    );

  if (!trace)
    return <div className="text-center py-32" style={{ color: "rgba(255,255,255,0.25)" }}>Result not found.</div>;

  const callGraph = trace.tool_call_graph as CallGraph | null;
  const recoveryTurns = trace.rationale_recovery?.turns;

  const scores = [
    { key: "score_adversarial",   label: "Adversarial",   weight: 0.25 },
    { key: "score_tool_misuse",   label: "Tool Misuse",   weight: 0.20 },
    { key: "score_hallucination", label: "Hallucination", weight: 0.20 },
    { key: "score_recovery",      label: "Recovery",      weight: 0.15 },
    { key: "score_latency",       label: "Latency",       weight: 0.10 },
    { key: "score_cost",          label: "Cost",          weight: 0.10 },
  ];

  return (
    <div className="space-y-5 animate-fade-up max-w-3xl mx-auto">
      {/* Nav */}
      <div className="flex items-center gap-2" style={{ fontSize: "12px" }}>
        <Link href={`/dashboard/runs/${id}`} style={{ color: "#0066FF", textDecoration: "none" }}>
          ← Back to Run
        </Link>
        <span style={{ color: "rgba(255,255,255,0.2)" }}>/</span>
        <span style={{ color: "rgba(255,255,255,0.35)", fontFamily: "monospace" }}>
          {promptId.slice(0, 8)}…
        </span>
      </div>

      <h1
        className="text-2xl font-bold"
        style={{ letterSpacing: "-0.03em", color: "rgba(255,255,255,0.92)" }}
      >
        Result Trace
      </h1>

      {trace.prompt_snapshot && <div className="card space-y-3">
        <span className="label">Frozen prompt</span>
        <p className="whitespace-pre-wrap">{trace.prompt_snapshot.text}</p>
        <p>{trace.prompt_snapshot.expected_behavior}</p>
      </div>}
      {trace.raw_payload && <details className="card">
        <summary>Captured response</summary>
        <pre className="overflow-auto text-xs">{JSON.stringify(trace.raw_payload, null, 2)}</pre>
      </details>}
      {trace.recovery_turns?.map((turn, i) => <div key={i} className="card space-y-3">
        <span className="label">Recovery conversation</span>
        <p>Injected context: {turn.injection}</p>
        <p>Agent: {turn.response_text}</p>
      </div>)}
      {/* Scores */}
      <div className="card space-y-4">
        <div className="flex items-center justify-between">
          <span className="label">Dimension Scores</span>
          <ScoreBadge score={trace.composite_score} size="lg" />
        </div>
        <div className="space-y-3">
          {scores.map(({ key, label, weight }) => (
            <ScoreBar
              key={key}
              score={(trace as unknown as Record<string, number | null>)[key]}
              label={label}
              weight={weight}
            />
          ))}
        </div>
      </div>

      {/* Capture metadata */}
      <div className="card">
        <span className="label block mb-3">Capture Metadata</span>
        <div className="grid grid-cols-2 gap-3">
          {[
            { k: "Latency", v: trace.latency_ms != null ? `${trace.latency_ms}ms` : "—" },
            { k: "Input tokens", v: trace.input_tokens ?? "—" },
            { k: "Output tokens", v: trace.output_tokens ?? "—" },
            { k: "Cost (USD)", v: trace.cost_usd != null ? `$${trace.cost_usd.toFixed(8)}` : "—" },
          ].map((row) => (
            <div key={row.k}>
              <div style={{ fontSize: "11px", color: "rgba(255,255,255,0.3)", marginBottom: "3px" }}>{row.k}</div>
              <div style={{ fontFamily: "monospace", fontSize: "13px", color: "rgba(255,255,255,0.7)" }}>{String(row.v)}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Hallucination claims */}
      {trace.rationale_hallucination && (
        <div className="card space-y-3">
          <span className="label">Hallucination Analysis</span>
          <p style={{ fontSize: "12px", color: "rgba(255,255,255,0.4)", lineHeight: 1.6 }}>
            {(trace.rationale_hallucination as { rationale: string }).rationale}
          </p>
          <div
            className="space-y-2 overflow-y-auto"
            style={{ maxHeight: "240px" }}
          >
            {(
              (trace.rationale_hallucination as { claims?: Array<{ text: string; grounded: boolean; is_temporal: boolean }> }).claims ?? []
            ).map((claim, i) => (
              <div
                key={i}
                className="rounded-xl px-3 py-2 text-xs leading-relaxed"
                style={{
                  background: claim.is_temporal
                    ? "rgba(255,255,255,0.04)"
                    : claim.grounded
                    ? "rgba(0,229,255,0.06)"
                    : "rgba(255,0,110,0.07)",
                  border: `1px solid ${
                    claim.is_temporal
                      ? "rgba(255,255,255,0.08)"
                      : claim.grounded
                      ? "rgba(0,229,255,0.15)"
                      : "rgba(255,0,110,0.15)"
                  }`,
                  color: claim.is_temporal
                    ? "rgba(255,255,255,0.35)"
                    : claim.grounded
                    ? "#00E5FF"
                    : "#FF4D9D",
                }}
              >
                <span className="mr-2 opacity-60">
                  {claim.is_temporal ? "⏱" : claim.grounded ? "✓" : "✗"}
                </span>
                {claim.text.slice(0, 120)}{claim.text.length > 120 && "…"}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tool call graph */}
      {callGraph && callGraph.nodes.length > 0 && (
        <div className="card space-y-3">
          <span className="label">Tool Call Graph</span>
          <div className="flex items-center gap-2 flex-wrap">
            {callGraph.nodes.map((node: CallGraphNode, i: number) => (
              <div key={node.id} className="flex items-center gap-2">
                <div
                  className="px-3 py-1.5 rounded-lg text-xs font-mono"
                  style={{
                    background: node.flagged ? "rgba(255,0,110,0.08)" : "rgba(0,163,255,0.08)",
                    border: `1px solid ${node.flagged ? "rgba(255,0,110,0.2)" : "rgba(0,163,255,0.2)"}`,
                    color: node.flagged ? "#FF4D9D" : "#00A3FF",
                    boxShadow: node.flagged ? "0 0 12px rgba(255,0,110,0.15)" : "0 0 8px rgba(0,163,255,0.1)",
                  }}
                >
                  {node.name}
                  {node.flagged && <span className="ml-1 opacity-80">⚠</span>}
                </div>
                {i < callGraph.nodes.length - 1 && (
                  <span style={{ color: "rgba(255,255,255,0.15)", fontSize: "10px" }}>→</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recovery turns */}
      {recoveryTurns && recoveryTurns.length > 0 && (
        <div className="card space-y-3">
          <span className="label">Recovery Analysis</span>
          <div className="space-y-2">
            {recoveryTurns.map((turn, i) => (
              <div
                key={i}
                className="rounded-xl px-4 py-3"
                style={{
                  background: turn.ordinal >= 3 ? "rgba(0,229,255,0.05)" : "rgba(255,155,66,0.06)",
                  border: `1px solid ${turn.ordinal >= 3 ? "rgba(0,229,255,0.12)" : "rgba(255,155,66,0.14)"}`,
                }}
              >
                <div className="flex items-center justify-between mb-1">
                  <span style={{ fontSize: "11px", color: "rgba(255,255,255,0.45)", letterSpacing: "0.03em" }}>
                    TURN {i + 1} · {turn.error_type.replace(/_/g, " ").toUpperCase()}
                  </span>
                  <ScoreBadge score={turn.score} size="sm" />
                </div>
                <p style={{ fontSize: "12px", color: "rgba(255,255,255,0.4)" }}>{turn.rationale}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Error */}
      {trace.error && (
        <div
          className="card"
          style={{
            background: "rgba(255,0,110,0.06)",
            border: "1px solid rgba(255,0,110,0.15)",
            padding: "20px 24px",
          }}
        >
          <span className="label" style={{ color: "#FF4D9D" }}>Error</span>
          <pre
            className="mt-3 overflow-x-auto text-xs leading-relaxed"
            style={{ color: "rgba(255,77,157,0.8)", fontFamily: "monospace" }}
          >
            {trace.error}
          </pre>
        </div>
      )}
    </div>
  );
}
