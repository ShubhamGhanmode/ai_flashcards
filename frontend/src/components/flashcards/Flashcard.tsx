"use client";

import { useState } from "react";
import type { Concept } from "@/lib/api";

interface FlashcardProps {
  concept: Concept;
  index: number;
  total: number;
}

export function Flashcard({ concept, index, total }: FlashcardProps) {
  const [showAllBullets, setShowAllBullets] = useState(false);
  const visibleBullets = showAllBullets ? concept.bullets : concept.bullets.slice(0, 2);

  return (
    <div className="stack-card rounded-2xl p-6 lg:p-8 max-w-lg mx-auto" style={{ boxShadow: "var(--shadow-md)" }}>
      <div className="flex justify-between items-start mb-4">
        <span
          className="text-sm"
          style={{
            color: "var(--text-muted)",
            fontFamily: "var(--font-mono)",
          }}
        >
          {index + 1} / {total}
        </span>
        {concept.example_possible && (
          <span
            className="text-xs px-3 py-1 rounded-full"
            style={{
              background: "rgba(245, 158, 11, 0.15)",
              color: "var(--accent-secondary)",
              border: "1px solid var(--border-accent)",
            }}
          >
            Example available
          </span>
        )}
      </div>

      <h2
        className="text-2xl font-bold mb-5"
        style={{
          fontFamily: "var(--font-display)",
          color: "var(--text-primary)",
        }}
      >
        {concept.title}
      </h2>

      <ul className="space-y-3 mb-5">
        {visibleBullets.map((bullet, bulletIndex) => (
          <li key={bulletIndex} className="flex items-start gap-3">
            <span className="mt-1.5 w-1.5 h-1.5 rounded-full shrink-0" style={{ background: "var(--accent-primary)" }} />
            <span style={{ color: "var(--text-secondary)", fontSize: "15px" }}>{bullet}</span>
          </li>
        ))}
      </ul>

      {!showAllBullets && concept.bullets.length > 2 && (
        <button
          onClick={() => setShowAllBullets(true)}
          className="text-sm font-medium transition-colors"
          style={{ color: "var(--accent-primary)" }}
        >
          Show {concept.bullets.length - 2} more points {"->"}
        </button>
      )}

      {concept.example_hint && showAllBullets && (
        <div
          className="mt-5 p-4 rounded-xl"
          style={{
            background: "rgba(245, 158, 11, 0.08)",
            border: "1px solid var(--border-accent)",
          }}
        >
          <p className="text-sm" style={{ color: "var(--accent-secondary)" }}>
            Tip: {concept.example_hint}
          </p>
        </div>
      )}
    </div>
  );
}
