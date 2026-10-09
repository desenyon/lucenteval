"use client";
import { useState } from "react";
import toast from "react-hot-toast";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { runsApi, type Run, type Result } from "@/lib/api";
import { ScoreBadge, ScoreBar } from "@/components/ScoreBadge";
import { formatDistanceToNow, format } from "date-fns";
import Link from "next/link";

const WEIGHTS: Record<string, number> = {
  score_adversarial: 0.25,
  score_tool_misuse: 0.20,
  score_hallucination: 0.20,
  score_recovery: 0.15,
  score_latency: 0.10,
  score_cost: 0.10,
};

const DIM_LABELS: Record<string, string> = {
  score_adversarial: "Adversarial",
  score_tool_misuse: "Tool Misuse",
  score_hallucination: "Hallucination",
  score_recovery: "Recovery",
  score_latency: "Latency",
  score_cost: "Cost",
};

export default function RunDetailPage() {
  const [page, setPage] = useState(1);
  const { id } = useParams<{ id: string }>();

  const { data: run, isLoading } = useQuery({
    queryKey: ["run", id],
    queryFn: () => runsApi.get(id),
    refetchInterval: (query) => ["pending", "running"].includes(query.state.data?.status ?? "") ? 3000 : false,
  });

  const { data: results } = useQuery({
    queryKey: ["run-results", id, page, run?.status],
    queryFn: () => runsApi.results(id, page),
    enabled: !!run,
    refetchInterval: ["pending", "running"].includes(run?.status ?? "") ? 3000 : false,
  });

  if (isLoading)
    return (
      <div className="flex items-center justify-center py-32">
        <div className="text-center space-y-3">
          <div
            className="w-8 h-8 rounded-full border-2 border-electric mx-auto"
            style={{ borderTopColor: "transparent", animation: "spin-slow 0.8s linear infinite" }}
          />
          <p style={{ fontSize: "13px", color: "rgba(255,255,255,0.3)" }}>Loading run...</p>
        </div>
      </div>
    );

  if (!run)
    return (
      <div className="text-center py-32" style={{ color: "rgba(255,255,255,0.25)", fontSize: "14px" }}>
        Run not found.
      </div>
    );

  return (
    <div className="space-y-6 animate-fade-up">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1 min-w-0">
          <div className="flex items-center gap-3 flex-wrap">
            <h1
              className="text-2xl font-bold"
              style={{ letterSpacing: "-0.03em", color: "rgba(255,255,255,0.92)" }}
            >
              Run Detail
            </h1>
            <span
              style={{
                fontFamily: "monospace",
                fontSize: "11px",
                color: "rgba(255,255,255,0.25)",
                background: "rgba(255,255,255,0.05)",
                padding: "3px 8px",
                borderRadius: "6px",
                border: "1px solid rgba(255,255,255,0.08)",
              }}
            >
              {id.slice(0, 8)}…
            </span>
            {run.status === "running" && (
              <span
                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-pill text-xs font-semibold"
                style={{ color: "#00A3FF", background: "rgba(0,163,255,0.08)", border: "1px solid rgba(0,163,255,0.2)" }}
              >
                <span className="w-1.5 h-1.5 rounded-full" style={{ background: "#00A3FF", animation: "pulse-glow 1.5s ease-in-out infinite" }} />
                RUNNING
              </span>
            )}
          </div>
          <p
            style={{
              fontSize: "12px",
              color: "rgba(255,255,255,0.3)",
              fontFamily: "monospace",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
              maxWidth: "480px",
            }}
          >
            {run.endpoint_url}
          </p>
        </div>
        <button
          onClick={async () => {
            try {
              const blob = await runsApi.export(id);
              const url = URL.createObjectURL(blob);
              const link = document.createElement("a");
              link.href = url;
              link.download = `run_${id}.ndjson`;
              link.click();
              setTimeout(() => URL.revokeObjectURL(url), 1000);
            } catch { toast.error("Export failed. Check your API key and try again."); }
          }}
          className="btn-secondary flex-shrink-0"
          style={{ fontSize: "12px" }}
        >
          Export NDJSON
        </button>
      </div>

      {/* Score cards */}
      <div className="grid md:grid-cols-2 gap-4">
        {/* Dimension breakdown */}
        <div className="card space-y-4">
          <div className="flex items-center justify-between">
            <span className="label">Dimension Scores</span>
            <ScoreBadge score={run.composite_score} size="lg" />
          </div>
          <div className="space-y-3">
            {Object.entries(DIM_LABELS).map(([key, label]) => (
              <ScoreBar
                key={key}
                score={(run as unknown as Record<string, number | null>)[key]}
                label={label}
                weight={run.weights_snapshot[key.replace("score_", "")] ?? WEIGHTS[key]}
              />
            ))}
          </div>
        </div>

        {/* Metadata */}
        <div className="card space-y-4">
          <span className="label">Run Metadata</span>
          <dl className="space-y-3">
            {[
              { k: "Corpus", v: run.corpus_version },
              { k: "Status", v: run.status },
              { k: "Failed prompts", v: run.failed_count },
              { k: "Scorer", v: run.scorer_version },
              { k: "Prompts", v: `${run.completed_count} / ${run.prompt_count}` },
              { k: "p50", v: run.latency_p50 ? `${run.latency_p50}ms` : "—" },
              { k: "p95", v: run.latency_p95 ? `${run.latency_p95}ms` : "—" },
              { k: "p99", v: run.latency_p99 ? `${run.latency_p99}ms` : "—" },
              { k: "Weights", v: run.weights_version },
              { k: "Created", v: format(new Date(run.created_at), "MMM d, yyyy HH:mm") },
              run.completed_at
                ? { k: "Completed", v: formatDistanceToNow(new Date(run.completed_at), { addSuffix: true }) }
                : null,
            ]
              .filter(Boolean)
              .map((row) => (
                <div key={row!.k} className="flex items-center justify-between">
                  <dt style={{ fontSize: "12px", color: "rgba(255,255,255,0.35)" }}>{row!.k}</dt>
                  <dd
                    style={{
                      fontSize: "12px",
                      fontFamily: "monospace",
                      color: "rgba(255,255,255,0.65)",
                    }}
                  >
                    {row!.v}
                  </dd>
                </div>
              ))}
          </dl>

          {run.status === "running" && (
            <div>
              <div className="divider my-3" />
              {/* Progress bar */}
              <div className="space-y-1.5">
                <div className="flex justify-between items-center">
                  <span style={{ fontSize: "11px", color: "rgba(255,255,255,0.3)" }}>Progress</span>
                  <span style={{ fontSize: "11px", fontFamily: "monospace", color: "#00A3FF" }}>
                    {run.completed_count} / {run.prompt_count}
                  </span>
                </div>
                <div style={{ height: "3px", background: "rgba(255,255,255,0.06)", borderRadius: "99px", overflow: "hidden" }}>
                  <div
                    style={{
                      height: "100%",
                      width: `${run.prompt_count ? (run.completed_count / run.prompt_count) * 100 : 0}%`,
                      background: "linear-gradient(90deg, #00A3FF, #00E5FF)",
                      borderRadius: "99px",
                      transition: "width 500ms ease",
                      boxShadow: "0 0 8px rgba(0,163,255,0.4)",
                    }}
                  />
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Per-prompt results */}
      {results && results.length > 0 && (
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <div
            className="flex items-center justify-between px-6 py-4"
            style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}
          >
            <span className="text-sm font-semibold" style={{ color: "rgba(255,255,255,0.7)", letterSpacing: "-0.02em" }}>
              Per-Prompt Results
            </span>
            <span className="label">{results.length} results</span>
          </div>
          <table className="data-table">
            <thead>
              <tr>
                <th>Prompt</th>
                <th className="text-center">Adv.</th>
                <th className="text-center">Tool</th>
                <th className="text-center">Hall.</th>
                <th className="text-center">Lat.</th>
                <th className="text-center">Cost</th>
                <th className="text-center">Score</th>
                <th>Latency</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {results.map((r: Result) => (
                <tr key={r.id}>
                  <td style={{ fontFamily: "monospace", fontSize: "11px", color: "rgba(255,255,255,0.25)" }}>
                    {r.prompt_id.slice(0, 8)}…
                  </td>
                  <td className="text-center"><ScoreBadge score={r.score_adversarial} size="sm" /></td>
                  <td className="text-center"><ScoreBadge score={r.score_tool_misuse} size="sm" /></td>
                  <td className="text-center"><ScoreBadge score={r.score_hallucination} size="sm" /></td>
                  <td className="text-center"><ScoreBadge score={r.score_latency} size="sm" /></td>
                  <td className="text-center"><ScoreBadge score={r.score_cost} size="sm" /></td>
                  <td className="text-center"><ScoreBadge score={r.composite_score} size="sm" /></td>
                  <td style={{ fontFamily: "monospace", fontSize: "11px", color: "rgba(255,255,255,0.3)" }}>
                    {r.latency_ms ? `${r.latency_ms}ms` : "—"}
                  </td>
                  <td>
                    <Link
                      href={`/dashboard/runs/${id}/trace/${r.prompt_id}`}
                      style={{ fontSize: "11px", color: "#0066FF", textDecoration: "none", fontWeight: 600 }}
                    >
                      Trace →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <div className="flex justify-center gap-3">
        <button className="btn-secondary" disabled={page === 1} onClick={() => setPage(page - 1)}>Previous</button>
        <span>Results page {page}</span>
        <button className="btn-secondary" disabled={(results?.length ?? 0) < 50} onClick={() => setPage(page + 1)}>Next</button>
      </div>
    </div>
  );
}
