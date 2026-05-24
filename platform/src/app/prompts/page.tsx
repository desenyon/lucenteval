"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { promptsApi, type Prompt } from "@/lib/api";
import toast from "react-hot-toast";

const CATEGORIES = ["injection", "jailbreak", "role_confusion", "goal_hijack", "tool_abuse", "factual_trap", "multi_turn_trap"];
const SEVERITIES = ["low", "medium", "high", "critical"];

const severityStyle: Record<string, { color: string; bg: string; border: string }> = {
  low:      { color: "#00A3FF", bg: "rgba(0,163,255,0.08)",  border: "rgba(0,163,255,0.2)"  },
  medium:   { color: "#D6FF00", bg: "rgba(214,255,0,0.07)",  border: "rgba(214,255,0,0.18)" },
  high:     { color: "#FF9B42", bg: "rgba(255,155,66,0.08)", border: "rgba(255,155,66,0.2)" },
  critical: { color: "#FF4D9D", bg: "rgba(255,0,110,0.08)",  border: "rgba(255,0,110,0.2)"  },
};

export default function PromptsPage() {
  const qc = useQueryClient();
  const [category, setCategory] = useState("");
  const [severity, setSeverity] = useState("");
  const [showContribute, setShowContribute] = useState(false);
  const [form, setForm] = useState({ text: "", category: "injection", severity: "medium", expected_behavior: "" });

  const { data: prompts, isLoading } = useQuery({
    queryKey: ["prompts", category, severity],
    queryFn: () => promptsApi.list({ category: category || undefined, severity: severity || undefined }),
  });

  const upvoteMutation = useMutation({
    mutationFn: promptsApi.upvote,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["prompts"] }),
  });

  const contributeMutation = useMutation({
    mutationFn: promptsApi.contribute,
    onSuccess: () => {
      toast.success("Prompt submitted for review!", {
        style: { background: "#0B0B0B", border: "1px solid rgba(214,255,0,0.2)", color: "#D6FF00" },
      });
      setShowContribute(false);
      setForm({ text: "", category: "injection", severity: "medium", expected_behavior: "" });
    },
    onError: () => toast.error("Failed to submit prompt", {
      style: { background: "#0B0B0B", border: "1px solid rgba(255,0,110,0.2)", color: "#FF4D9D" },
    }),
  });

  return (
    <div className="space-y-6 animate-fade-up">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1">
          <h1
            className="text-3xl font-bold"
            style={{ letterSpacing: "-0.04em", color: "rgba(255,255,255,0.95)" }}
          >
            Prompt Corpus
          </h1>
          <p style={{ fontSize: "13px", color: "rgba(255,255,255,0.35)" }}>
            {prompts?.length ?? 0} prompts matching filters
          </p>
        </div>
        <button onClick={() => setShowContribute(true)} className="btn-primary flex-shrink-0">
          + Contribute
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="input"
          style={{ width: "180px", fontSize: "12px" }}
        >
          <option value="">All Categories</option>
          {CATEGORIES.map((c) => <option key={c} value={c}>{c.replace(/_/g, " ")}</option>)}
        </select>
        <select
          value={severity}
          onChange={(e) => setSeverity(e.target.value)}
          className="input"
          style={{ width: "140px", fontSize: "12px" }}
        >
          <option value="">All Severities</option>
          {SEVERITIES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>

      {/* Prompt list */}
      <div className="space-y-3">
        {isLoading && (
          <div className="flex items-center justify-center py-16">
            <div
              className="w-6 h-6 rounded-full border-2 border-electric"
              style={{ borderTopColor: "transparent", animation: "spin-slow 0.8s linear infinite" }}
            />
          </div>
        )}
        {prompts?.map((prompt: Prompt) => {
          const sev = severityStyle[prompt.severity] ?? severityStyle.medium;
          return (
            <div
              key={prompt.id}
              className="card"
              style={{ padding: "16px 20px", display: "flex", gap: "16px", alignItems: "flex-start" }}
            >
              <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", gap: "8px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                  <span
                    style={{
                      fontSize: "10px",
                      fontFamily: "monospace",
                      color: "rgba(255,255,255,0.5)",
                      background: "rgba(255,255,255,0.06)",
                      border: "1px solid rgba(255,255,255,0.1)",
                      padding: "2px 8px",
                      borderRadius: "6px",
                      letterSpacing: "0.04em",
                      textTransform: "uppercase",
                    }}
                  >
                    {prompt.category.replace(/_/g, " ")}
                  </span>
                  {prompt.subcategory && (
                    <span style={{ fontSize: "10px", color: "rgba(255,255,255,0.25)" }}>
                      / {prompt.subcategory.replace(/_/g, " ")}
                    </span>
                  )}
                  <span
                    style={{
                      fontSize: "10px",
                      fontWeight: 600,
                      letterSpacing: "0.06em",
                      textTransform: "uppercase",
                      color: sev.color,
                      background: sev.bg,
                      border: `1px solid ${sev.border}`,
                      padding: "2px 8px",
                      borderRadius: "999px",
                    }}
                  >
                    {prompt.severity}
                  </span>
                </div>
                <p
                  style={{
                    fontSize: "13px",
                    color: "rgba(255,255,255,0.7)",
                    lineHeight: 1.5,
                    display: "-webkit-box",
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: "vertical",
                    overflow: "hidden",
                  }}
                >
                  {prompt.text}
                </p>
                <p style={{ fontSize: "11px", color: "rgba(255,255,255,0.3)", lineHeight: 1.4 }}>
                  <span style={{ color: "rgba(255,255,255,0.45)" }}>Expected: </span>
                  {prompt.expected_behavior.slice(0, 100)}
                  {prompt.expected_behavior.length > 100 && "…"}
                </p>
              </div>
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "4px", flexShrink: 0 }}>
                <button
                  onClick={() => upvoteMutation.mutate(prompt.id)}
                  style={{
                    background: "none",
                    border: "none",
                    cursor: "pointer",
                    fontSize: "12px",
                    color: "rgba(255,255,255,0.25)",
                    padding: "4px",
                    transition: "color 150ms ease",
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.color = "#0066FF")}
                  onMouseLeave={(e) => (e.currentTarget.style.color = "rgba(255,255,255,0.25)")}
                  title="Upvote"
                >
                  ▲
                </button>
                <span
                  style={{
                    fontSize: "12px",
                    fontFamily: "monospace",
                    fontWeight: 600,
                    color: "rgba(255,255,255,0.5)",
                  }}
                >
                  {prompt.upvotes}
                </span>
              </div>
            </div>
          );
        })}
        {!isLoading && prompts?.length === 0 && (
          <div className="text-center py-16" style={{ color: "rgba(255,255,255,0.25)", fontSize: "13px" }}>
            No prompts match the current filters.
          </div>
        )}
      </div>

      {/* Contribute modal */}
      {showContribute && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.75)",
            backdropFilter: "blur(8px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 50,
            padding: "16px",
          }}
        >
          <div
            className="card"
            style={{ maxWidth: "520px", width: "100%", padding: "28px 32px", display: "flex", flexDirection: "column", gap: "20px" }}
          >
            <div>
              <h2
                className="font-bold"
                style={{ fontSize: "18px", letterSpacing: "-0.03em", color: "rgba(255,255,255,0.92)", marginBottom: "6px" }}
              >
                Contribute a Prompt
              </h2>
              <p style={{ fontSize: "12px", color: "rgba(255,255,255,0.35)", lineHeight: 1.5 }}>
                All submissions enter a quarantine queue and are reviewed before becoming active.
              </p>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <textarea
                value={form.text}
                onChange={(e) => setForm({ ...form, text: e.target.value })}
                placeholder="Prompt text..."
                rows={4}
                className="input"
              />
              <div style={{ display: "flex", gap: "10px" }}>
                <select
                  value={form.category}
                  onChange={(e) => setForm({ ...form, category: e.target.value })}
                  className="input"
                  style={{ flex: 1, fontSize: "12px" }}
                >
                  {CATEGORIES.map((c) => <option key={c} value={c}>{c.replace(/_/g, " ")}</option>)}
                </select>
                <select
                  value={form.severity}
                  onChange={(e) => setForm({ ...form, severity: e.target.value })}
                  className="input"
                  style={{ width: "120px", fontSize: "12px" }}
                >
                  {SEVERITIES.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <textarea
                value={form.expected_behavior}
                onChange={(e) => setForm({ ...form, expected_behavior: e.target.value })}
                placeholder="Expected model behavior..."
                rows={2}
                className="input"
              />
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px" }}>
              <button onClick={() => setShowContribute(false)} className="btn-secondary">Cancel</button>
              <button
                onClick={() => contributeMutation.mutate(form)}
                disabled={!form.text || !form.expected_behavior || contributeMutation.isPending}
                className="btn-primary"
              >
                {contributeMutation.isPending ? "Submitting..." : "Submit for Review"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
