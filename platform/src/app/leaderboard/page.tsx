"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { leaderboardApi, type Run } from "@/lib/api";
import { ScoreBadge } from "@/components/ScoreBadge";
import { formatDistanceToNow } from "date-fns";

const SORT_OPTIONS = [
  { value: "composite_score", label: "Composite" },
  { value: "score_adversarial", label: "Adversarial" },
  { value: "score_tool_misuse", label: "Tool Misuse" },
  { value: "score_hallucination", label: "Hallucination" },
  { value: "score_recovery", label: "Recovery" },
  { value: "score_latency", label: "Latency" },
  { value: "score_cost", label: "Cost" },
];

export default function LeaderboardPage() {
  const [sortBy, setSortBy] = useState("composite_score");
  const [page, setPage] = useState(1);

  const { data: runs, isLoading } = useQuery({
    queryKey: ["leaderboard", sortBy, page],
    queryFn: () => leaderboardApi.get(sortBy, page),
  });

  return (
    <div className="space-y-6 animate-fade-up">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <h1
            className="text-3xl font-bold"
            style={{ letterSpacing: "-0.04em", color: "rgba(255,255,255,0.95)" }}
          >
            Leaderboard
          </h1>
          <p style={{ fontSize: "13px", color: "rgba(255,255,255,0.35)" }}>
            All scores public · sorted by {SORT_OPTIONS.find((o) => o.value === sortBy)?.label}
          </p>
        </div>
        <select
          value={sortBy}
          onChange={(e) => { setSortBy(e.target.value); setPage(1); }}
          className="input"
          style={{ width: "150px", fontSize: "12px" }}
        >
          {SORT_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </div>

      {/* Table */}
      <div
        className="card"
        style={{ padding: 0, overflow: "hidden" }}
      >
        <table className="data-table">
          <thead>
            <tr>
              <th style={{ width: "44px", paddingLeft: "20px" }}>#</th>
              <th>Endpoint</th>
              <th className="text-center">Composite</th>
              <th className="text-center">Adv.</th>
              <th className="text-center">Tool</th>
              <th className="text-center">Hall.</th>
              <th className="text-center">Rec.</th>
              <th className="text-center">Lat.</th>
              <th className="text-center">Cost</th>
              <th>When</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr>
                <td colSpan={10} className="text-center py-16">
                  <div
                    className="inline-flex items-center gap-2"
                    style={{ color: "rgba(255,255,255,0.3)", fontSize: "13px" }}
                  >
                    <div
                      className="w-3 h-3 rounded-full border-t border-electric"
                      style={{ animation: "spin-slow 1s linear infinite" }}
                    />
                    Loading...
                  </div>
                </td>
              </tr>
            )}
            {runs?.map((run: Run, i: number) => (
              <tr key={run.id}>
                <td
                  style={{
                    fontFamily: "monospace",
                    fontSize: "12px",
                    color: "rgba(255,255,255,0.2)",
                    paddingLeft: "20px",
                    paddingRight: "8px",
                  }}
                >
                  {(page - 1) * 50 + i + 1}
                </td>
                <td>
                  <span
                    style={{
                      fontSize: "12px",
                      fontWeight: 500,
                      color: "#00A3FF",
                      textDecoration: "none",
                      display: "block",
                      maxWidth: "220px",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {run.endpoint_url.replace(/^https?:\/\//, "").slice(0, 36)}
                  </span>
                  <span style={{ fontSize: "10px", color: "rgba(255,255,255,0.2)", fontFamily: "monospace" }}>
                    {run.corpus_version}
                  </span>
                </td>
                <td className="text-center"><ScoreBadge score={run.composite_score} size="md" /></td>
                <td className="text-center"><ScoreBadge score={run.score_adversarial} size="sm" /></td>
                <td className="text-center"><ScoreBadge score={run.score_tool_misuse} size="sm" /></td>
                <td className="text-center"><ScoreBadge score={run.score_hallucination} size="sm" /></td>
                <td className="text-center"><ScoreBadge score={run.score_recovery} size="sm" /></td>
                <td className="text-center"><ScoreBadge score={run.score_latency} size="sm" /></td>
                <td className="text-center"><ScoreBadge score={run.score_cost} size="sm" /></td>
                <td style={{ fontSize: "11px", color: "rgba(255,255,255,0.25)", whiteSpace: "nowrap" }}>
                  {formatDistanceToNow(new Date(run.created_at), { addSuffix: true })}
                </td>
              </tr>
            ))}
            {!isLoading && runs?.length === 0 && (
              <tr>
                <td colSpan={10} className="text-center py-16" style={{ color: "rgba(255,255,255,0.25)", fontSize: "13px" }}>
                  No completed runs yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="flex justify-center items-center gap-3">
        <button
          onClick={() => setPage((p) => Math.max(1, p - 1))}
          disabled={page === 1}
          className="btn-secondary"
          style={{ fontSize: "12px", padding: "8px 16px" }}
        >
          ← Previous
        </button>
        <span style={{ fontSize: "12px", color: "rgba(255,255,255,0.3)" }}>
          Page {page}
        </span>
        <button
          onClick={() => setPage((p) => p + 1)}
          disabled={(runs?.length ?? 0) < 50}
          className="btn-secondary"
          style={{ fontSize: "12px", padding: "8px 16px" }}
        >
          Next →
        </button>
      </div>
    </div>
  );
}
