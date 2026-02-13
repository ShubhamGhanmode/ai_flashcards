"use client";

import { useCallback, useEffect, useState } from "react";
import type { DeckResponse } from "@/lib/api";
import { Flashcard } from "./Flashcard";

interface DeckSwiperProps {
  deck: DeckResponse;
}

export function DeckSwiper({ deck }: DeckSwiperProps) {
  const [currentIndex, setCurrentIndex] = useState(0);

  const goNext = useCallback(() => {
    setCurrentIndex((index) => Math.min(index + 1, deck.concepts.length - 1));
  }, [deck.concepts.length]);

  const goPrev = useCallback(() => {
    setCurrentIndex((index) => Math.max(index - 1, 0));
  }, []);

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

  const currentConcept = deck.concepts[currentIndex];

  return (
    <div className="min-h-screen py-8 px-4" style={{ background: "var(--bg-primary)" }}>
      <div className="max-w-2xl mx-auto">
        <div className="text-center mb-10">
          <button
            onClick={() => window.history.back()}
            className="inline-flex items-center gap-2 text-sm mb-6 transition-colors"
            style={{ color: "var(--text-muted)" }}
          >
            {"<-"} Back
          </button>
          <h1
            className="text-3xl lg:text-4xl font-bold mb-3"
            style={{
              fontFamily: "var(--font-display)",
              color: "var(--text-primary)",
            }}
          >
            {deck.topic}
          </h1>
          <p
            className="text-sm"
            style={{
              color: "var(--text-muted)",
              fontFamily: "var(--font-mono)",
            }}
          >
            {deck.difficulty_level} - {deck.concepts.length} concepts
          </p>
        </div>

        <Flashcard concept={currentConcept} index={currentIndex} total={deck.concepts.length} />

        <div className="flex justify-center gap-4 mt-8">
          <button
            onClick={goPrev}
            disabled={currentIndex === 0}
            className="px-6 py-3 rounded-xl text-sm font-medium transition-all disabled:opacity-30 disabled:cursor-not-allowed"
            style={{
              background: "var(--bg-glass)",
              color: "var(--text-primary)",
              border: "1px solid var(--border-subtle)",
            }}
          >
            {"<-"} Previous
          </button>
          <button
            onClick={goNext}
            disabled={currentIndex === deck.concepts.length - 1}
            className="px-6 py-3 rounded-xl text-sm font-medium transition-all disabled:opacity-30 disabled:cursor-not-allowed"
            style={{
              background: "var(--accent-gradient)",
              color: "var(--bg-primary)",
              boxShadow: "var(--shadow-glow)",
            }}
          >
            Next {"->"}
          </button>
        </div>

        <div className="flex justify-center gap-2 mt-6">
          {deck.concepts.map((_, index) => (
            <button
              key={index}
              onClick={() => setCurrentIndex(index)}
              aria-label={`Go to card ${index + 1}`}
              className="w-3 h-3 rounded-full transition-all"
              style={{
                background: index === currentIndex ? "var(--accent-primary)" : "var(--bg-elevated)",
                border: `1px solid ${index === currentIndex ? "var(--accent-primary)" : "var(--border-subtle)"}`,
                transform: index === currentIndex ? "scale(1.25)" : "scale(1)",
                boxShadow: index === currentIndex ? "0 0 12px rgba(245, 158, 11, 0.35)" : "none",
              }}
            />
          ))}
        </div>

        <p
          className="text-center mt-4 text-xs"
          style={{
            color: "var(--text-muted)",
            fontFamily: "var(--font-mono)",
          }}
        >
          Use arrow keys to navigate
        </p>
      </div>
    </div>
  );
}
