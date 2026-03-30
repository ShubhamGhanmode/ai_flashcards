"use client";

import { useState } from "react";
import type { Concept } from "@/lib/api";
import { ExamplePanel } from "./ExamplePanel";

interface FlashcardProps {
  concept: Concept;
  index: number;
  total: number;
}

export function Flashcard({ concept, index, total }: FlashcardProps) {
  const [isFlipped, setIsFlipped] = useState(false);

  return (
    <article
      className="relative h-full overflow-hidden rounded-[32px]"
      style={{
        minHeight: "560px",
        background:
          "linear-gradient(165deg, rgba(26, 26, 26, 0.98) 0%, rgba(15, 15, 15, 0.98) 72%)",
        border: "1px solid rgba(255, 255, 255, 0.08)",
        boxShadow: "var(--shadow-lg)",
      }}
    >
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            "radial-gradient(circle at top right, rgba(245, 158, 11, 0.12) 0%, transparent 42%)",
        }}
      />

      <div className="relative flex h-full flex-col justify-between gap-8 p-6 lg:p-8">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p
              className="text-[11px] uppercase tracking-[0.3em]"
              style={{
                color: "var(--text-muted)",
                fontFamily: "var(--font-mono)",
              }}
            >
              Card {index + 1} of {total}
            </p>
            <p className="mt-3 text-sm" style={{ color: "var(--text-secondary)" }}>
              {isFlipped ? "Back of card" : "Front of card"}
            </p>
          </div>

          {concept.example_possible && (
            <span
              className="rounded-full px-3 py-1 text-[11px] uppercase tracking-[0.18em]"
              style={{
                background: "rgba(245, 158, 11, 0.1)",
                color: "var(--accent-secondary)",
                border: "1px solid var(--border-accent)",
                fontFamily: "var(--font-mono)",
              }}
            >
              Example ready
            </span>
          )}
        </div>

        {!isFlipped ? (
          <>
            <div>
              <h2
                className="text-4xl leading-tight lg:text-5xl"
                style={{
                  fontFamily: "var(--font-display)",
                  color: "var(--text-primary)",
                }}
              >
                {concept.title}
              </h2>
              <p className="mt-5 max-w-xl text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                Flip the card when you want the distilled notes. The front stays deliberately light so the deck keeps
                moving.
              </p>
            </div>

            <div className="grid gap-3 md:grid-cols-3">
              {concept.bullets.slice(0, 3).map((bullet, bulletIndex) => (
                <div
                  key={bulletIndex}
                  className="rounded-2xl px-4 py-4"
                  style={{
                    background: "rgba(255, 255, 255, 0.03)",
                    border: "1px solid rgba(255, 255, 255, 0.06)",
                  }}
                >
                  <p
                    className="text-[11px] uppercase tracking-[0.26em]"
                    style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}
                  >
                    Cue {bulletIndex + 1}
                  </p>
                  <p className="mt-3 text-sm leading-relaxed" style={{ color: "var(--text-primary)" }}>
                    {bullet}
                  </p>
                </div>
              ))}
            </div>

            <div className="flex flex-wrap items-center justify-between gap-4">
              <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                Reveal all five takeaways when you are ready to read.
              </p>
              <button
                onClick={() => setIsFlipped(true)}
                className="rounded-full px-5 py-3 text-sm font-medium transition-transform hover:-translate-y-0.5"
                style={{
                  background: "var(--accent-gradient)",
                  color: "var(--bg-primary)",
                  boxShadow: "var(--shadow-glow)",
                }}
              >
                Reveal notes
              </button>
            </div>
          </>
        ) : (
          <>
            <div>
              <h2
                className="text-3xl leading-tight lg:text-4xl"
                style={{
                  fontFamily: "var(--font-display)",
                  color: "var(--text-primary)",
                }}
              >
                {concept.title}
              </h2>
              <div className="mt-6 space-y-4">
                {concept.bullets.map((bullet, bulletIndex) => (
                  <div key={bulletIndex} className="flex items-start gap-3">
                    <span
                      className="mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full"
                      style={{ background: "var(--accent-primary)" }}
                    />
                    <p className="text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                      {bullet}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            <div className="space-y-5">
              {concept.example_hint && (
                <div
                  className="rounded-2xl p-4"
                  style={{
                    background: "rgba(245, 158, 11, 0.08)",
                    border: "1px solid var(--border-accent)",
                  }}
                >
                  <p className="text-sm leading-relaxed" style={{ color: "var(--accent-secondary)" }}>
                    Tip: {concept.example_hint}
                  </p>
                </div>
              )}

              <div className="flex flex-wrap items-center justify-between gap-4">
                <button
                  onClick={() => setIsFlipped(false)}
                  className="rounded-full px-4 py-2 text-sm transition-colors"
                  style={{
                    background: "rgba(255, 255, 255, 0.04)",
                    border: "1px solid var(--border-subtle)",
                    color: "var(--text-primary)",
                  }}
                >
                  Return to front
                </button>
                <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                  Keep the back open while you study, then move on.
                </p>
              </div>

              {concept.example_possible && <ExamplePanel cardId={concept.card_id} />}
            </div>
          </>
        )}
      </div>
    </article>
  );
}
