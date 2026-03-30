"use client";

import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { estimateDeck } from "@/lib/api";

interface EstimatePreviewProps {
  topic: string;
  difficultyLevel: "beginner" | "intermediate" | "advanced";
  maxConcepts: number;
  scope?: string;
}

function useDebouncedValue(value: string, delayMs: number): string {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDebounced(value);
    }, delayMs);
    return () => window.clearTimeout(timer);
  }, [value, delayMs]);

  return debounced;
}

export function EstimatePreview({
  topic,
  difficultyLevel,
  maxConcepts,
  scope,
}: EstimatePreviewProps) {
  const normalizedTopic = topic.trim();
  const debouncedTopic = useDebouncedValue(normalizedTopic, 300);
  const canEstimate = debouncedTopic.length >= 3;

  const estimateQuery = useQuery({
    queryKey: ["deck-estimate", debouncedTopic, difficultyLevel, maxConcepts, scope ?? ""],
    queryFn: () =>
      estimateDeck({
        topic: debouncedTopic,
        difficulty_level: difficultyLevel,
        max_concepts: maxConcepts,
        scope: scope?.trim() ? scope.trim() : undefined,
      }),
    enabled: canEstimate,
    retry: false,
  });

  if (!canEstimate || estimateQuery.isError) {
    return null;
  }

  return (
    <div
      className="rounded-xl px-4 py-3"
      style={{
        background: "var(--bg-secondary)",
        border: "1px solid var(--border-subtle)",
      }}
    >
      <p
        className="text-xs uppercase tracking-widest mb-2"
        style={{
          color: "var(--text-muted)",
          fontFamily: "var(--font-mono)",
        }}
      >
        Estimate
      </p>

      {estimateQuery.isPending || !estimateQuery.data ? (
        <div className="grid grid-cols-3 gap-3 text-sm" data-testid="estimate-skeleton">
          <div className="space-y-2">
            <div
              className="h-3 w-14 rounded"
              style={{ background: "var(--bg-elevated)" }}
            />
            <div
              className="h-5 w-16 rounded animate-pulse"
              style={{ background: "var(--border-subtle)" }}
            />
          </div>
          <div className="space-y-2">
            <div
              className="h-3 w-10 rounded"
              style={{ background: "var(--bg-elevated)" }}
            />
            <div
              className="h-5 w-14 rounded animate-pulse"
              style={{ background: "var(--border-subtle)" }}
            />
          </div>
          <div className="space-y-2">
            <div
              className="h-3 w-10 rounded"
              style={{ background: "var(--bg-elevated)" }}
            />
            <div
              className="h-5 w-12 rounded animate-pulse"
              style={{ background: "var(--border-subtle)" }}
            />
          </div>
          <p className="sr-only" role="status">
            Calculating estimate...
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-3 gap-3 text-sm">
          <div>
            <p style={{ color: "var(--text-muted)" }}>Tokens</p>
            <p style={{ color: "var(--text-primary)" }}>
              {estimateQuery.data.estimated_tokens.total.toLocaleString()}
            </p>
          </div>
          <div>
            <p style={{ color: "var(--text-muted)" }}>Cost</p>
            <p style={{ color: "var(--text-primary)" }}>
              ${estimateQuery.data.estimated_cost_usd.toFixed(4)}
            </p>
          </div>
          <div>
            <p style={{ color: "var(--text-muted)" }}>Time</p>
            <p style={{ color: "var(--text-primary)" }}>
              {estimateQuery.data.estimated_seconds.toFixed(1)}s
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
