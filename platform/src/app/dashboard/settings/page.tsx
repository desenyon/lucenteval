"use client";
import { useState, useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";

const WEIGHTS = [
  { name: "Adversarial",   weight: "25%", color: "#FF4D9D" },
  { name: "Tool Misuse",   weight: "20%", color: "#FF9B42" },
  { name: "Hallucination", weight: "20%", color: "#0066FF" },
  { name: "Recovery",      weight: "15%", color: "#00A3FF" },
  { name: "Latency",       weight: "10%", color: "#00E5FF" },
  { name: "Cost",          weight: "10%", color: "#D6FF00" },
];

export default function SettingsPage() {
  const queryClient = useQueryClient();
  const [apiKey, setApiKey] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem("lucent_api_key") || "";
    setApiKey(stored);
  }, []);

  const handleSave = () => {
    localStorage.setItem("lucent_api_key", apiKey);
    queryClient.clear();
    setSaved(true);
    toast.success("API key saved", {
      style: { background: "#0B0B0B", border: "1px solid rgba(214,255,0,0.2)", color: "#D6FF00" },
    });
  };

  return (
    <div className="max-w-lg space-y-6 animate-fade-up">
      <h1
        className="text-3xl font-bold"
        style={{ letterSpacing: "-0.04em", color: "rgba(255,255,255,0.95)" }}
      >
        Settings
      </h1>

      {/* API Key */}
      <div className="card space-y-4">
        <div>
          <span className="label block mb-1">API Key</span>
          <p style={{ fontSize: "12px", color: "rgba(255,255,255,0.3)", lineHeight: 1.5 }}>
            Stored in this browser&apos;s localStorage and sent to the configured Lucent Eval API as a Bearer token. Clear it on shared devices.
          </p>
        </div>
        <div style={{ display: "flex", gap: "10px" }}>
          <input
            type="password"
            value={apiKey}
            onChange={(e) => { setApiKey(e.target.value); setSaved(false); }}
            placeholder="lev_..."
            className="input"
            style={{ flex: 1 }}
          />
          <button onClick={handleSave} className="btn-primary flex-shrink-0">
            Save
          </button>
          <button className="btn-secondary" onClick={() => { localStorage.removeItem("lucent_api_key"); queryClient.clear(); setApiKey(""); setSaved(false); }}>Clear</button>
        </div>
        {saved && (
          <p style={{ fontSize: "11px", color: "#D6FF00" }}>✓ Key saved in this browser</p>
        )}
      </div>

      {/* Scoring weights */}
      <div className="card space-y-4">
        <div>
          <span className="label block mb-1">Scoring Weights v1</span>
          <p style={{ fontSize: "12px", color: "rgba(255,255,255,0.3)", lineHeight: 1.5 }}>
            Weight changes are versioned. Historical scores are never recomputed.
          </p>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          {WEIGHTS.map((d) => (
            <div key={d.name} style={{ display: "flex", alignItems: "center", gap: "12px" }}>
              <span style={{ fontSize: "12px", color: "rgba(255,255,255,0.55)", width: "110px", flexShrink: 0 }}>
                {d.name}
              </span>
              <div style={{ flex: 1, height: "3px", background: "rgba(255,255,255,0.06)", borderRadius: "99px", overflow: "hidden" }}>
                <div
                  style={{
                    height: "100%",
                    width: d.weight,
                    background: d.color,
                    borderRadius: "99px",
                    boxShadow: `0 0 8px ${d.color}60`,
                  }}
                />
              </div>
              <span
                style={{
                  fontSize: "12px",
                  fontFamily: "monospace",
                  color: d.color,
                  width: "36px",
                  textAlign: "right",
                  flexShrink: 0,
                }}
              >
                {d.weight}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Corpus info */}
      <div
        className="rounded-2xl px-5 py-4"
        style={{
          background: "rgba(0,102,255,0.06)",
          border: "1px solid rgba(0,102,255,0.15)",
        }}
      >
        <p style={{ fontSize: "12px", color: "rgba(0,102,255,0.9)", lineHeight: 1.6 }}>
          Each new run stores a frozen copy of its selected prompts and scoring configuration.
        </p>
      </div>
    </div>
  );
}
