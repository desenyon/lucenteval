"use client";

interface ScoreBadgeProps {
  score: number | null | undefined;
  size?: "sm" | "md" | "lg";
  showBar?: boolean;
}

function getScoreStyle(score: number): { bg: string; text: string; glow: string; border: string } {
  if (score >= 0.8)
    return {
      bg: "rgba(0,229,255,0.08)",
      text: "#00E5FF",
      glow: "rgba(0,229,255,0.2)",
      border: "rgba(0,229,255,0.2)",
    };
  if (score >= 0.6)
    return {
      bg: "rgba(214,255,0,0.08)",
      text: "#D6FF00",
      glow: "rgba(214,255,0,0.15)",
      border: "rgba(214,255,0,0.2)",
    };
  if (score >= 0.4)
    return {
      bg: "rgba(255,155,66,0.08)",
      text: "#FF9B42",
      glow: "rgba(255,155,66,0.2)",
      border: "rgba(255,155,66,0.2)",
    };
  return {
    bg: "rgba(255,0,110,0.08)",
    text: "#FF4D9D",
    glow: "rgba(255,0,110,0.2)",
    border: "rgba(255,0,110,0.2)",
  };
}

function getBarColor(score: number): string {
  if (score >= 0.8) return "linear-gradient(90deg, #00E5FF, #00A3FF)";
  if (score >= 0.6) return "linear-gradient(90deg, #D6FF00, #A3FF12)";
  if (score >= 0.4) return "linear-gradient(90deg, #FF9B42, #FF6B00)";
  return "linear-gradient(90deg, #FF006E, #FF4D9D)";
}

export function ScoreBadge({ score, size = "md" }: ScoreBadgeProps) {
  if (score === null || score === undefined) {
    return (
      <span
        className="score-badge"
        style={{
          background: "rgba(255,255,255,0.05)",
          color: "rgba(255,255,255,0.3)",
          border: "1px solid rgba(255,255,255,0.08)",
          fontSize: size === "lg" ? "13px" : size === "sm" ? "10px" : "11px",
          padding: size === "lg" ? "4px 12px" : "3px 8px",
        }}
      >
        —
      </span>
    );
  }

  const style = getScoreStyle(score);
  const pct = (score * 100).toFixed(1);

  return (
    <span
      className="score-badge"
      style={{
        background: style.bg,
        color: style.text,
        border: `1px solid ${style.border}`,
        boxShadow: `0 0 12px ${style.glow}`,
        fontSize: size === "lg" ? "13px" : size === "sm" ? "10px" : "11px",
        padding: size === "lg" ? "4px 12px" : "3px 8px",
        fontWeight: 700,
      }}
    >
      {pct}%
    </span>
  );
}

interface ScoreBarProps {
  score: number | null | undefined;
  label: string;
  weight?: number;
}

export function ScoreBar({ score, label, weight }: ScoreBarProps) {
  const pct = score !== null && score !== undefined ? score * 100 : 0;
  const barColor = score !== null && score !== undefined ? getBarColor(score) : "rgba(255,255,255,0.08)";

  return (
    <div className="flex items-center gap-3">
      <div className="flex items-center gap-1.5" style={{ width: "130px", flexShrink: 0 }}>
        <span style={{ fontSize: "12px", color: "rgba(255,255,255,0.55)", letterSpacing: "-0.01em" }}>
          {label}
        </span>
        {weight !== undefined && (
          <span style={{ fontSize: "10px", color: "rgba(255,255,255,0.25)", fontWeight: 600 }}>
            {(weight * 100).toFixed(0)}%
          </span>
        )}
      </div>
      <div
        className="flex-1 relative"
        style={{
          height: "4px",
          background: "rgba(255,255,255,0.06)",
          borderRadius: "99px",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            position: "absolute",
            left: 0,
            top: 0,
            height: "100%",
            width: `${pct}%`,
            background: barColor,
            borderRadius: "99px",
            transition: "width 600ms cubic-bezier(0.22,1,0.36,1)",
            boxShadow: score !== null && score !== undefined ? `0 0 8px ${getScoreStyle(score).glow}` : "none",
          }}
        />
      </div>
      <ScoreBadge score={score} size="sm" />
    </div>
  );
}
