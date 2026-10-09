"use client";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { runsApi, type RunSummary as Run } from "@/lib/api";
import { ScoreBadge } from "@/components/ScoreBadge";
import { formatDistanceToNow } from "date-fns";

function StatusChip({ status }: { status: string }) {
  const styles: Record<string, { color: string; bg: string; border: string; glow: string }> = {
    pending:   { color: "rgba(255,255,255,0.4)",  bg: "rgba(255,255,255,0.05)", border: "rgba(255,255,255,0.1)",  glow: "transparent" },
    running:   { color: "#00A3FF",  bg: "rgba(0,163,255,0.08)",  border: "rgba(0,163,255,0.25)", glow: "rgba(0,163,255,0.15)" },
    completed: { color: "#D6FF00",  bg: "rgba(214,255,0,0.07)",  border: "rgba(214,255,0,0.2)",  glow: "rgba(214,255,0,0.1)"  },
    failed:    { color: "#FF4D9D",  bg: "rgba(255,0,110,0.08)",  border: "rgba(255,0,110,0.2)",  glow: "rgba(255,0,110,0.1)"  },
  };
  const s = styles[status] ?? styles.pending;
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-pill text-xs font-semibold"
      style={{
        color: s.color,
        background: s.bg,
        border: `1px solid ${s.border}`,
        boxShadow: `0 0 12px ${s.glow}`,
        letterSpacing: "0.03em",
      }}
    >
      {status === "running" && (
        <span
          className="w-1.5 h-1.5 rounded-full"
          style={{ background: "#00A3FF", animation: "pulse-glow 1.5s ease-in-out infinite" }}
        />
      )}
      {status.toUpperCase()}
    </span>
  );
}

export default function DashboardPage() {
  const { data: runs, isLoading } = useQuery({
    queryKey: ["runs"],
    queryFn: () => runsApi.list(1),
    refetchInterval: 5000,
  });

  const completed = runs?.filter((r: Run) => r.status === "completed") ?? [];
  const running = runs?.filter((r: Run) => r.status === "running") ?? [];
  const avgScore =
    completed.length > 0
      ? completed.reduce((s: number, r: Run) => s + (r.composite_score ?? 0), 0) / completed.length
      : null;

  const stats = [
    { label: "Total Runs", value: runs?.length ?? 0, color: "rgba(255,255,255,0.7)" },
    { label: "Completed", value: completed.length, color: "#D6FF00" },
    { label: "Running", value: running.length, color: "#00A3FF" },
    {
      label: "Avg Score",
      value: avgScore !== null ? `${(avgScore * 100).toFixed(0)}%` : "—",
      color: "#00E5FF",
    },
  ];

  return (
    <div className="space-y-6 animate-fade-up">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1
          className="text-3xl font-bold"
          style={{ letterSpacing: "-0.04em", color: "rgba(255,255,255,0.95)" }}
        >
          Dashboard
        </h1>
        <Link href="/dashboard/runs/new" className="btn-primary">
          + New Run
        </Link>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {stats.map((stat) => (
          <div key={stat.label} className="card" style={{ padding: "20px 24px" }}>
            <div
              className="font-bold"
              style={{
                fontSize: "32px",
                letterSpacing: "-0.04em",
                color: stat.color,
                lineHeight: 1,
              }}
            >
              {stat.value}
            </div>
            <div className="mt-1.5 label">{stat.label}</div>
          </div>
        ))}
      </div>

      {/* Run history */}
      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        {/* Table header */}
        <div
          className="flex items-center justify-between px-6 py-4"
          style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}
        >
          <span className="text-sm font-semibold" style={{ color: "rgba(255,255,255,0.7)", letterSpacing: "-0.02em" }}>
            Run History
          </span>
          <span className="label">{runs?.length ?? 0} runs</span>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th style={{ paddingLeft: "24px" }}>Endpoint</th>
              <th>Status</th>
              <th className="text-center">Score</th>
              <th>Prompts</th>
              <th>Started</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr>
                <td colSpan={6} className="text-center py-16" style={{ color: "rgba(255,255,255,0.25)", fontSize: "13px" }}>
                  Loading runs...
                </td>
              </tr>
            )}
            {runs?.map((run: Run) => (
              <tr key={run.id}>
                <td style={{ paddingLeft: "24px" }}>
                  <span
                    className="block font-medium"
                    style={{
                      fontSize: "12px",
                      color: "rgba(255,255,255,0.75)",
                      maxWidth: "260px",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                      letterSpacing: "-0.01em",
                    }}
                  >
                    {run.endpoint_url.replace(/^https?:\/\//, "").slice(0, 44)}
                  </span>
                </td>
                <td><StatusChip status={run.status} /></td>
                <td className="text-center">
                  <ScoreBadge score={run.composite_score} />
                </td>
                <td>
                  <span style={{ fontSize: "12px", color: "rgba(255,255,255,0.4)", fontFamily: "monospace" }}>
                    {run.completed_count}/{run.prompt_count}
                  </span>
                </td>
                <td style={{ fontSize: "11px", color: "rgba(255,255,255,0.25)", whiteSpace: "nowrap" }}>
                  {run.created_at && formatDistanceToNow(new Date(run.created_at), { addSuffix: true })}
                </td>
                <td>
                  <Link
                    href={`/dashboard/runs/${run.id}`}
                    style={{
                      fontSize: "11px",
                      color: "#0066FF",
                      textDecoration: "none",
                      fontWeight: 600,
                    }}
                  >
                    View →
                  </Link>
                </td>
              </tr>
            ))}
            {!isLoading && runs?.length === 0 && (
              <tr>
                <td colSpan={6} className="text-center py-16">
                  <div className="space-y-3">
                    <div style={{ fontSize: "28px" }}>⚡</div>
                    <p style={{ fontSize: "13px", color: "rgba(255,255,255,0.3)" }}>
                      No runs yet.{" "}
                      <Link href="/dashboard/runs/new" style={{ color: "#0066FF" }}>
                        Start your first eval.
                      </Link>
                    </p>
                  </div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
