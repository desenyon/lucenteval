"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { runsApi } from "@/lib/api";
import toast from "react-hot-toast";

export default function NewRunPage() {
  const router = useRouter();
  const [endpointUrl, setEndpointUrl] = useState("");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [headerKey, setHeaderKey] = useState("Authorization");
  const [headerValue, setHeaderValue] = useState("");

  const mutation = useMutation({
    mutationFn: runsApi.create,
    onSuccess: (run) => {
      toast.success("Run created!", {
        style: {
          background: "#0B0B0B",
          border: "1px solid rgba(214,255,0,0.2)",
          color: "#D6FF00",
        },
      });
      router.push(`/dashboard/runs/${run.id}`);
    },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Failed to create run";
      toast.error(msg, {
        style: {
          background: "#0B0B0B",
          border: "1px solid rgba(255,0,110,0.2)",
          color: "#FF4D9D",
        },
      });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const headers: Record<string, string> = {};
    if (headerKey && headerValue) headers[headerKey] = headerValue;
    mutation.mutate({ endpoint_url: endpointUrl, headers, system_prompt: systemPrompt || undefined });
  };

  return (
    <div className="max-w-xl mx-auto space-y-6 animate-fade-up">
      {/* Header */}
      <div className="space-y-1">
        <h1
          className="text-3xl font-bold"
          style={{ letterSpacing: "-0.04em", color: "rgba(255,255,255,0.95)" }}
        >
          New Eval Run
        </h1>
        <p style={{ fontSize: "13px", color: "rgba(255,255,255,0.35)" }}>
          Submit your agent endpoint to run against the bundled adversarial corpus.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="card space-y-6">
        {/* Endpoint URL */}
        <div className="space-y-2">
          <label className="label" style={{ display: "block" }}>
            Agent Endpoint URL
            <span style={{ color: "#FF4D9D", marginLeft: "4px" }}>*</span>
          </label>
          <input
            type="url"
            required
            value={endpointUrl}
            onChange={(e) => setEndpointUrl(e.target.value)}
            placeholder="https://your-agent.example.com/v1/chat/completions"
            className="input"
          />
          <p style={{ fontSize: "11px", color: "rgba(255,255,255,0.25)" }}>
            Must accept OpenAI-compatible chat completions requests.
          </p>
        </div>

        {/* Auth header */}
        <div className="space-y-2">
          <label className="label" style={{ display: "block" }}>Auth Header</label>
          <div className="flex gap-2">
            <input
              type="text"
              value={headerKey}
              onChange={(e) => setHeaderKey(e.target.value)}
              placeholder="Authorization"
              className="input"
              style={{ width: "160px", flexShrink: 0 }}
            />
            <input
              type="password"
              value={headerValue}
              onChange={(e) => setHeaderValue(e.target.value)}
              placeholder="Bearer sk-..."
              className="input"
            />
          </div>
          <p style={{ fontSize: "11px", color: "rgba(255,255,255,0.25)" }}>
            Encrypted for execution and cleared after the run finishes. Sent to your agent endpoint.
          </p>
        </div>

        {/* System prompt */}
        <div className="space-y-2">
          <label className="label" style={{ display: "block" }}>
            System Prompt Override
            <span style={{ color: "rgba(255,255,255,0.25)", marginLeft: "6px", textTransform: "none", letterSpacing: 0, fontSize: "10px" }}>
              optional
            </span>
          </label>
          <textarea
            value={systemPrompt}
            onChange={(e) => setSystemPrompt(e.target.value)}
            rows={4}
            placeholder="You are a helpful assistant..."
            className="input"
          />
        </div>

        {/* Notice */}
        <div
          className="rounded-2xl px-4 py-3.5 text-xs leading-relaxed"
          style={{
            background: "rgba(255,155,66,0.06)",
            border: "1px solid rgba(255,155,66,0.15)",
            color: "rgba(255,155,66,0.8)",
          }}
        >
          All scores are public and will appear on the leaderboard immediately after scoring completes.
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-2 pt-1">
          <button
            type="button"
            onClick={() => router.back()}
            className="btn-secondary"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={mutation.isPending || !endpointUrl}
            className="btn-primary"
          >
            {mutation.isPending ? "Submitting..." : "Start Eval Run →"}
          </button>
        </div>
      </form>
    </div>
  );
}
