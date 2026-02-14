"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { APIClientError, generateCardExample, type ExampleGenerateRequest } from "@/lib/api";

interface ExamplePanelProps {
  cardId: string;
  request?: ExampleGenerateRequest;
}

function normalizeConstraints(constraints: string[] | undefined): string[] {
  if (!constraints) {
    return [];
  }
  return constraints.map((constraint) => constraint.trim()).filter((constraint) => constraint.length > 0);
}

export function ExamplePanel({ cardId, request }: ExamplePanelProps) {
  const [isOpen, setIsOpen] = useState(false);

  const style = request?.style ?? "default";
  const length = request?.length ?? "medium";
  const constraints = useMemo(
    () => normalizeConstraints(request?.constraints),
    [request?.constraints],
  );
  const constraintsKey = useMemo(
    () => JSON.stringify(constraints),
    [constraints],
  );

  const exampleQuery = useQuery({
    queryKey: ["card-example", cardId, style, length, constraintsKey],
    queryFn: () =>
      generateCardExample(cardId, {
        style,
        length,
        constraints: constraints.length > 0 ? constraints : undefined,
      }),
    enabled: isOpen,
  });

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="mt-5 text-sm font-medium transition-colors"
        style={{ color: "var(--accent-primary)" }}
      >
        Show example
      </button>
    );
  }

  const errorMessage =
    exampleQuery.error instanceof APIClientError
      ? exampleQuery.error.error.message
      : "Failed to load example. Please try again.";

  return (
    <div
      className="mt-5 p-4 rounded-xl"
      style={{
        background: "rgba(245, 158, 11, 0.08)",
        border: "1px solid var(--border-accent)",
      }}
    >
      <div className="flex items-center justify-between mb-3">
        <p
          className="text-xs uppercase tracking-widest"
          style={{
            color: "var(--accent-secondary)",
            fontFamily: "var(--font-mono)",
          }}
        >
          Example
        </p>
        <button
          onClick={() => setIsOpen(false)}
          className="text-xs transition-colors"
          style={{ color: "var(--text-muted)" }}
        >
          Hide
        </button>
      </div>

      {exampleQuery.isPending && (
        <div>
          <div
            className="h-4 rounded mb-2 animate-pulse"
            style={{ background: "rgba(255, 255, 255, 0.08)" }}
          />
          <div
            className="h-4 rounded mb-2 animate-pulse"
            style={{ background: "rgba(255, 255, 255, 0.06)" }}
          />
          <div
            className="h-4 rounded w-2/3 animate-pulse"
            style={{ background: "rgba(255, 255, 255, 0.06)" }}
          />
          <p className="mt-3 text-xs" style={{ color: "var(--text-muted)" }}>
            Generating example...
          </p>
        </div>
      )}

      {exampleQuery.isError && (
        <div>
          <p className="text-sm mb-3" style={{ color: "#fca5a5" }}>
            {errorMessage}
          </p>
          <button
            onClick={() => {
              void exampleQuery.refetch();
            }}
            disabled={exampleQuery.isFetching}
            className="text-xs font-medium px-3 py-2 rounded-lg disabled:opacity-60 disabled:cursor-not-allowed"
            style={{
              color: "var(--bg-primary)",
              background: "var(--accent-gradient)",
            }}
          >
            {exampleQuery.isFetching ? "Retrying..." : "Retry"}
          </button>
        </div>
      )}

      {exampleQuery.data && (
        <div>
          <p className="text-sm leading-relaxed" style={{ color: "var(--text-primary)" }}>
            {exampleQuery.data.example}
          </p>

          {exampleQuery.data.steps && exampleQuery.data.steps.length > 0 && (
            <div className="mt-3">
              <p
                className="text-xs uppercase tracking-widest mb-1"
                style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}
              >
                Steps
              </p>
              <ul className="space-y-1">
                {exampleQuery.data.steps.map((step, index) => (
                  <li key={index} className="text-sm" style={{ color: "var(--text-secondary)" }}>
                    {index + 1}. {step}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {exampleQuery.data.pitfalls && exampleQuery.data.pitfalls.length > 0 && (
            <div className="mt-3">
              <p
                className="text-xs uppercase tracking-widest mb-1"
                style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}
              >
                Pitfalls
              </p>
              <ul className="space-y-1">
                {exampleQuery.data.pitfalls.map((pitfall, index) => (
                  <li key={index} className="text-sm" style={{ color: "var(--text-secondary)" }}>
                    {pitfall}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
