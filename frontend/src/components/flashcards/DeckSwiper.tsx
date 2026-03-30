"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Concept, DeckResponse } from "@/lib/api";
import { Flashcard } from "./Flashcard";

interface DeckSwiperProps {
  deck: DeckResponse;
}

interface GhostCardProps {
  concept: Concept | null;
  layer: "mid" | "back";
}

function GhostCard({ concept, layer }: GhostCardProps) {
  const opacity = layer === "mid" ? 0.78 : 0.48;

  return (
    <div
      className="stack-card h-full rounded-[30px] p-6"
      style={{
        opacity,
        borderStyle: concept ? "solid" : "dashed",
      }}
    >
      <p
        className="text-[11px] uppercase tracking-[0.28em]"
        style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}
      >
        {concept ? "Coming up" : "Pack end"}
      </p>
      {concept ? (
        <>
          <h3 className="mt-6 text-xl leading-tight" style={{ color: "var(--text-primary)", fontFamily: "var(--font-display)" }}>
            {concept.title}
          </h3>
          <p className="mt-4 text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>
            {concept.bullets[0]}
          </p>
        </>
      ) : (
        <p className="mt-6 text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>
          You are at the end of the current run. Move backward or jump to another concept from the rail.
        </p>
      )}
    </div>
  );
}

export function DeckSwiper({ deck }: DeckSwiperProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [animationDirection, setAnimationDirection] = useState<"next" | "prev" | null>(null);
  const animationTimerRef = useRef<number | null>(null);

  const isAnimating = animationDirection !== null;
  const currentConcept = deck.concepts[currentIndex];
  const nextConcept = deck.concepts[currentIndex + 1] ?? null;
  const trailingConcept = deck.concepts[currentIndex + 2] ?? null;
  const examplesAvailable = deck.concepts.filter((concept) => concept.example_possible).length;
  const progressPercent = Math.round(((currentIndex + 1) / deck.concepts.length) * 100);

  const clearAnimationTimer = useCallback(() => {
    if (animationTimerRef.current !== null) {
      window.clearTimeout(animationTimerRef.current);
      animationTimerRef.current = null;
    }
  }, []);

  const animateToIndex = useCallback(
    (targetIndex: number, direction: "next" | "prev") => {
      if (isAnimating || targetIndex === currentIndex) {
        return;
      }

      setAnimationDirection(direction);
      clearAnimationTimer();
      animationTimerRef.current = window.setTimeout(() => {
        setCurrentIndex(targetIndex);
        setAnimationDirection(null);
        animationTimerRef.current = null;
      }, 320);
    },
    [clearAnimationTimer, currentIndex, isAnimating],
  );

  const goNext = useCallback(() => {
    const targetIndex = Math.min(currentIndex + 1, deck.concepts.length - 1);
    animateToIndex(targetIndex, "next");
  }, [animateToIndex, currentIndex, deck.concepts.length]);

  const goPrev = useCallback(() => {
    const targetIndex = Math.max(currentIndex - 1, 0);
    animateToIndex(targetIndex, "prev");
  }, [animateToIndex, currentIndex]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "ArrowRight" || event.key === "ArrowDown") {
        goNext();
      } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
        goPrev();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [goNext, goPrev]);

  useEffect(
    () => () => {
      clearAnimationTimer();
    },
    [clearAnimationTimer],
  );

  const canGoPrev = currentIndex > 0 && !isAnimating;
  const canGoNext = currentIndex < deck.concepts.length - 1 && !isAnimating;

  return (
    <div className="min-h-screen py-8 px-4 lg:px-6 relative overflow-hidden" style={{ background: "var(--bg-primary)" }}>
      <div
        className="absolute top-[-12%] right-[-6%] h-[460px] w-[460px] rounded-full pointer-events-none"
        style={{
          background: "radial-gradient(circle, rgba(245, 158, 11, 0.18) 0%, transparent 70%)",
          filter: "blur(24px)",
        }}
      />
      <div
        className="absolute bottom-[-18%] left-[-8%] h-[520px] w-[520px] rounded-full pointer-events-none"
        style={{
          background: "radial-gradient(circle, rgba(217, 119, 6, 0.14) 0%, transparent 74%)",
          filter: "blur(24px)",
        }}
      />

      <div className="relative mx-auto max-w-7xl">
        <header className="mb-10 flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <button
              onClick={() => window.history.back()}
              className="inline-flex items-center gap-2 text-sm transition-colors"
              style={{ color: "var(--text-muted)" }}
            >
              {"<-"} Back
            </button>
            <h1
              className="mt-5 text-4xl lg:text-6xl leading-[1.02]"
              style={{
                fontFamily: "var(--font-display)",
                color: "var(--text-primary)",
              }}
            >
              {deck.topic}
            </h1>
            <p className="mt-4 max-w-2xl text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>
              Flip the active card to reveal the notes, then send it to the back of the pack to expose the next
              concept underneath.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-3 lg:min-w-[360px]">
            <div className="stack-card rounded-2xl px-4 py-4">
              <p className="text-[11px] uppercase tracking-[0.26em]" style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                Progress
              </p>
              <p className="mt-2 text-lg" style={{ color: "var(--text-primary)" }}>
                {currentIndex + 1} / {deck.concepts.length}
              </p>
            </div>
            <div className="stack-card rounded-2xl px-4 py-4">
              <p className="text-[11px] uppercase tracking-[0.26em]" style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                Difficulty
              </p>
              <p className="mt-2 text-lg capitalize" style={{ color: "var(--text-primary)" }}>
                {deck.difficulty_level}
              </p>
            </div>
            <div className="stack-card rounded-2xl px-4 py-4">
              <p className="text-[11px] uppercase tracking-[0.26em]" style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                Examples
              </p>
              <p className="mt-2 text-lg" style={{ color: "var(--text-primary)" }}>
                {examplesAvailable} ready
              </p>
            </div>
          </div>
        </header>

        <div className="grid gap-8 xl:grid-cols-[minmax(0,1fr)_320px] xl:items-start">
          <section className="glass rounded-[32px] p-5 lg:p-7">
            <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <p
                  className="text-[11px] uppercase tracking-[0.3em]"
                  style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}
                >
                  Card deck
                </p>
                <p className="mt-3 text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                  Use the navigation buttons or the arrow keys. The front of each card is for quick orientation and the
                  back is for the five takeaways.
                </p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={goPrev}
                  disabled={!canGoPrev}
                  className="rounded-full px-4 py-2 text-sm transition-all disabled:opacity-30 disabled:cursor-not-allowed"
                  style={{
                    background: "var(--bg-secondary)",
                    border: "1px solid var(--border-subtle)",
                    color: "var(--text-primary)",
                  }}
                >
                  {"<-"} Bring previous forward
                </button>
                <button
                  onClick={goNext}
                  disabled={!canGoNext}
                  className="rounded-full px-4 py-2 text-sm transition-all disabled:opacity-30 disabled:cursor-not-allowed"
                  style={{
                    background: "var(--accent-gradient)",
                    color: "var(--bg-primary)",
                    boxShadow: "var(--shadow-glow)",
                  }}
                >
                  Send to back {"->"}
                </button>
              </div>
            </div>

            <div
              className={`deck-stack mt-8 ${animationDirection ? `deck-stack-${animationDirection}` : ""}`}
              style={{ minHeight: "640px" }}
            >
              <div className="deck-stack-layer deck-stack-layer-back">
                <GhostCard concept={trailingConcept} layer="back" />
              </div>
              <div className="deck-stack-layer deck-stack-layer-mid">
                <GhostCard concept={nextConcept} layer="mid" />
              </div>
              <div className="deck-stack-layer deck-stack-layer-top">
                <Flashcard
                  key={currentConcept.card_id}
                  concept={currentConcept}
                  index={currentIndex}
                  total={deck.concepts.length}
                />
              </div>
            </div>

            <div className="mt-8 flex items-center justify-between gap-4 flex-wrap">
              <div
                className="rounded-full px-4 py-2 text-[11px] uppercase tracking-[0.28em]"
                style={{
                  background: "rgba(245, 158, 11, 0.08)",
                  border: "1px solid var(--border-accent)",
                  color: "var(--accent-secondary)",
                  fontFamily: "var(--font-mono)",
                }}
              >
                {progressPercent}% through this run
              </div>
              <p className="text-xs" style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                Arrow keys active
              </p>
            </div>
          </section>

          <aside className="space-y-5 xl:sticky xl:top-6">
            <div className="glass rounded-[28px] p-6">
              <p
                className="text-[11px] uppercase tracking-[0.3em]"
                style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}
              >
                Concept rail
              </p>
              <div className="mt-5 space-y-3">
                {deck.concepts.map((concept, index) => {
                  const active = index === currentIndex;
                  return (
                    <button
                      key={concept.card_id}
                      onClick={() => {
                        if (isAnimating) {
                          return;
                        }
                        setCurrentIndex(index);
                      }}
                      className="w-full rounded-2xl px-4 py-4 text-left transition-all"
                      style={{
                        background: active ? "rgba(245, 158, 11, 0.08)" : "rgba(255, 255, 255, 0.02)",
                        border: `1px solid ${active ? "var(--border-accent)" : "var(--border-subtle)"}`,
                      }}
                    >
                      <div className="flex items-center justify-between gap-3">
                        <span
                          className="text-[11px] uppercase tracking-[0.24em]"
                          style={{
                            color: active ? "var(--accent-secondary)" : "var(--text-muted)",
                            fontFamily: "var(--font-mono)",
                          }}
                        >
                          Card {index + 1}
                        </span>
                        {concept.example_possible && (
                          <span
                            className="rounded-full px-2 py-1 text-[10px] uppercase tracking-[0.18em]"
                            style={{
                              background: "rgba(245, 158, 11, 0.1)",
                              color: "var(--accent-secondary)",
                            }}
                          >
                            Example
                          </span>
                        )}
                      </div>
                      <p className="mt-3 text-sm leading-relaxed" style={{ color: "var(--text-primary)" }}>
                        {concept.title}
                      </p>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="glass rounded-[28px] p-6">
              <p
                className="text-[11px] uppercase tracking-[0.3em]"
                style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}
              >
                Generation metadata
              </p>
              <div className="mt-5 space-y-4 text-sm">
                <div className="flex items-center justify-between gap-4">
                  <span style={{ color: "var(--text-muted)" }}>Model</span>
                  <span style={{ color: "var(--text-primary)" }}>{deck.generation_metadata.model}</span>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <span style={{ color: "var(--text-muted)" }}>Prompt version</span>
                  <span style={{ color: "var(--text-primary)" }}>{deck.generation_metadata.prompt_version}</span>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <span style={{ color: "var(--text-muted)" }}>Total tokens</span>
                  <span style={{ color: "var(--text-primary)" }}>{deck.generation_metadata.tokens.total}</span>
                </div>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}
