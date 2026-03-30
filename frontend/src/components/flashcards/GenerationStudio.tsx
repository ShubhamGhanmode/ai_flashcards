"use client";

import type { DeckGenerationStatusEvent } from "@/lib/api";

interface GenerationStudioProps {
  topic: string;
  difficultyLabel: string;
  cardCount: number;
  event: DeckGenerationStatusEvent | null;
}

const PHASE_LABELS: Record<DeckGenerationStatusEvent["phase"], string> = {
  queued: "Scope",
  generating: "Draft",
  finalizing: "Launch",
};

const PHASE_DETAILS: Record<DeckGenerationStatusEvent["phase"], string[]> = {
  queued: [
    "Locking in the cleanest angle for the topic.",
    "Keeping the deck narrow enough to stay memorable.",
  ],
  generating: [
    "Breaking the topic into atomic, reviewable concepts.",
    "Balancing coverage so each card earns its place.",
    "Keeping the structure strict enough for clean rendering.",
  ],
  finalizing: [
    "Saving the deck and preparing the first reveal.",
    "Lining up the card stack so the next screen feels instant.",
  ],
};

function formatSeconds(value: number): string {
  return `${value.toFixed(1)}s`;
}

export function GenerationStudio({
  topic,
  difficultyLabel,
  cardCount,
  event,
}: GenerationStudioProps) {
  const activePhase = event?.phase ?? "queued";
  const phaseDetails = PHASE_DETAILS[activePhase];
  const detailIndex =
    phaseDetails.length === 1
      ? 0
      : Math.floor((event?.elapsed_seconds ?? 0) / 1.5) % phaseDetails.length;
  const detailCopy = phaseDetails[detailIndex] ?? phaseDetails[0];
  const estimatedSeconds = Math.max(event?.estimated_seconds ?? 0, 0.5);
  const elapsedSeconds = Math.max(event?.elapsed_seconds ?? 0, 0);
  const progress = Math.min(0.92, elapsedSeconds / estimatedSeconds);
  const progressWidth = `${Math.max(progress * 100, 8)}%`;
  const etaSeconds = Math.max(0, estimatedSeconds - elapsedSeconds);
  const activeCardCount = Math.min(
    cardCount,
    Math.max(1, Math.round(Math.max(progress, 0.12) * cardCount)),
  );

  return (
    <div
      className="fixed inset-0 z-50 overflow-y-auto px-6 py-10"
      style={{
        background: "rgba(15, 15, 15, 0.82)",
        backdropFilter: "blur(18px)",
        WebkitBackdropFilter: "blur(18px)",
      }}
    >
      <div className="absolute inset-0 pointer-events-none">
        <div
          className="absolute top-[-15%] left-[8%] h-72 w-72 rounded-full animate-drift"
          style={{
            background:
              "radial-gradient(circle, rgba(245, 158, 11, 0.22) 0%, transparent 72%)",
            filter: "blur(18px)",
          }}
        />
        <div
          className="absolute bottom-[-18%] right-[8%] h-96 w-96 rounded-full animate-drift-slow"
          style={{
            background:
              "radial-gradient(circle, rgba(217, 119, 6, 0.2) 0%, transparent 74%)",
            filter: "blur(18px)",
          }}
        />
      </div>

      <div className="relative z-10 mx-auto grid max-w-6xl gap-10 lg:grid-cols-[420px_minmax(0,1fr)] lg:items-center">
        <section className="glass-accent rounded-[28px] p-7 lg:p-9">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p
                className="text-xs uppercase tracking-[0.32em]"
                style={{
                  color: "var(--text-muted)",
                  fontFamily: "var(--font-mono)",
                }}
              >
                Generation studio
              </p>
              <h2
                className="mt-3 text-3xl leading-tight"
                style={{ fontFamily: "var(--font-display)" }}
              >
                Building your deck without the dead air.
              </h2>
            </div>
            <span
              className="inline-flex items-center gap-2 rounded-full px-3 py-2 text-[11px] uppercase tracking-[0.28em]"
              style={{
                background: "rgba(245, 158, 11, 0.12)",
                border: "1px solid var(--border-accent)",
                color: "var(--accent-secondary)",
                fontFamily: "var(--font-mono)",
              }}
            >
              <span
                className="h-2 w-2 rounded-full animate-soft-pulse"
                style={{ background: "var(--accent-primary)" }}
              />
              Streaming
            </span>
          </div>

          <p className="mt-4 text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>
            {event?.message ?? "Preparing the prompt."}
          </p>
          <p className="mt-2 text-sm leading-relaxed" style={{ color: "var(--text-muted)" }}>
            {detailCopy}
          </p>

          <div className="mt-7 space-y-3">
            <div className="flex items-center justify-between text-xs" style={{ color: "var(--text-muted)" }}>
              <span style={{ fontFamily: "var(--font-mono)" }}>Estimated progress</span>
              <span style={{ fontFamily: "var(--font-mono)" }}>
                {formatSeconds(elapsedSeconds)} / {formatSeconds(estimatedSeconds)}
              </span>
            </div>
            <div
              className="overflow-hidden rounded-full"
              style={{
                height: "10px",
                background: "rgba(255, 255, 255, 0.06)",
                border: "1px solid var(--border-subtle)",
              }}
            >
              <div
                className="h-full rounded-full animate-shimmer"
                style={{
                  width: progressWidth,
                  background:
                    "linear-gradient(90deg, rgba(245, 158, 11, 0.45) 0%, rgba(251, 191, 36, 0.95) 45%, rgba(245, 158, 11, 0.55) 100%)",
                }}
              />
            </div>
          </div>

          <div className="mt-7 grid gap-3 sm:grid-cols-3">
            <div className="stack-card rounded-2xl p-4">
              <p className="text-[11px] uppercase tracking-[0.26em]" style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                Topic
              </p>
              <p className="mt-2 text-sm" style={{ color: "var(--text-primary)" }}>
                {topic}
              </p>
            </div>
            <div className="stack-card rounded-2xl p-4">
              <p className="text-[11px] uppercase tracking-[0.26em]" style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                Difficulty
              </p>
              <p className="mt-2 text-sm" style={{ color: "var(--text-primary)" }}>
                {difficultyLabel}
              </p>
            </div>
            <div className="stack-card rounded-2xl p-4">
              <p className="text-[11px] uppercase tracking-[0.26em]" style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                ETA
              </p>
              <p className="mt-2 text-sm" style={{ color: "var(--text-primary)" }}>
                {formatSeconds(etaSeconds)}
              </p>
            </div>
          </div>

          <div className="mt-8 space-y-3">
            {(["queued", "generating", "finalizing"] as const).map((phase) => {
              const phaseActive = phase === activePhase;
              const phaseComplete = (event?.stage_index ?? 1) > (["queued", "generating", "finalizing"] as const).indexOf(phase) + 1;

              return (
                <div
                  key={phase}
                  className="flex items-center gap-3 rounded-2xl px-4 py-3"
                  style={{
                    background: phaseActive ? "rgba(245, 158, 11, 0.08)" : "rgba(255, 255, 255, 0.02)",
                    border: `1px solid ${phaseActive ? "var(--border-accent)" : "var(--border-subtle)"}`,
                  }}
                >
                  <span
                    className="flex h-8 w-8 items-center justify-center rounded-full text-[11px] uppercase"
                    style={{
                      background: phaseActive || phaseComplete ? "var(--accent-primary)" : "var(--bg-secondary)",
                      color: phaseActive || phaseComplete ? "var(--bg-primary)" : "var(--text-muted)",
                      fontFamily: "var(--font-mono)",
                    }}
                  >
                    {(["queued", "generating", "finalizing"] as const).indexOf(phase) + 1}
                  </span>
                  <div>
                    <p className="text-sm" style={{ color: "var(--text-primary)" }}>
                      {PHASE_LABELS[phase]}
                    </p>
                    <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                      {phase === "queued"
                        ? "Shape the request."
                        : phase === "generating"
                          ? "Draft the concepts."
                          : "Save and launch the deck."}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        <section className="relative min-h-[420px] lg:min-h-[520px]">
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="relative w-full max-w-[560px]">
              <div
                className="absolute inset-x-[7%] top-12 rounded-[28px] p-6 animate-drift-slow"
                style={{
                  minHeight: "360px",
                  background: "rgba(255, 255, 255, 0.04)",
                  border: "1px solid rgba(255, 255, 255, 0.05)",
                  transform: "translateY(54px) rotate(-8deg)",
                  opacity: 0.38,
                }}
              />
              <div
                className="absolute inset-x-[4%] top-6 rounded-[28px] p-6 animate-drift"
                style={{
                  minHeight: "380px",
                  background: "rgba(255, 255, 255, 0.05)",
                  border: "1px solid rgba(255, 255, 255, 0.08)",
                  transform: "translateY(26px) rotate(-4deg)",
                  opacity: 0.65,
                }}
              />
              <div
                className="relative rounded-[32px] p-7 lg:p-8"
                style={{
                  minHeight: "420px",
                  background:
                    "linear-gradient(165deg, rgba(24, 24, 24, 0.98) 0%, rgba(15, 15, 15, 0.98) 72%)",
                  border: "1px solid rgba(255, 255, 255, 0.08)",
                  boxShadow: "var(--shadow-lg)",
                }}
              >
                <div className="flex items-center justify-between gap-3">
                  <p
                    className="text-[11px] uppercase tracking-[0.32em]"
                    style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}
                  >
                    {cardCount} concept deck
                  </p>
                  <span
                    className="rounded-full px-3 py-1 text-[11px] uppercase tracking-[0.22em]"
                    style={{
                      background: "rgba(245, 158, 11, 0.1)",
                      color: "var(--accent-secondary)",
                    }}
                  >
                    {difficultyLabel}
                  </span>
                </div>

                <div className="mt-8">
                  <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                    Next reveal
                  </p>
                  <h3
                    className="mt-3 text-4xl leading-tight lg:text-5xl"
                    style={{ fontFamily: "var(--font-display)", color: "var(--text-primary)" }}
                  >
                    {topic}
                  </h3>
                  <p className="mt-5 max-w-md text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                    The live stream keeps the momentum visible while the model drafts, validates, and saves a deck that
                    still lands as strict JSON.
                  </p>
                </div>

                <div className="mt-10 grid gap-3 sm:grid-cols-2">
                  <div
                    className="rounded-2xl px-4 py-4"
                    style={{
                      background: "rgba(255, 255, 255, 0.03)",
                      border: "1px solid rgba(255, 255, 255, 0.06)",
                    }}
                  >
                    <p className="text-[11px] uppercase tracking-[0.26em]" style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                      Current phase
                    </p>
                    <p className="mt-2 text-sm" style={{ color: "var(--text-primary)" }}>
                      {PHASE_LABELS[activePhase]}
                    </p>
                  </div>
                  <div
                    className="rounded-2xl px-4 py-4"
                    style={{
                      background: "rgba(255, 255, 255, 0.03)",
                      border: "1px solid rgba(255, 255, 255, 0.06)",
                    }}
                  >
                    <p className="text-[11px] uppercase tracking-[0.26em]" style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                      Live cue
                    </p>
                    <p className="mt-2 text-sm" style={{ color: "var(--text-primary)" }}>
                      {detailCopy}
                    </p>
                  </div>
                </div>

                <div className="mt-10 flex flex-wrap gap-2">
                  {Array.from({ length: cardCount }).map((_, index) => (
                    <span
                      key={index}
                      className="rounded-full px-3 py-2 text-[11px] uppercase tracking-[0.2em]"
                      style={{
                        background:
                          index < activeCardCount
                            ? "rgba(245, 158, 11, 0.12)"
                            : "rgba(255, 255, 255, 0.03)",
                        border: `1px solid ${index < activeCardCount ? "var(--border-accent)" : "var(--border-subtle)"}`,
                        color:
                          index < activeCardCount
                            ? "var(--accent-secondary)"
                            : "var(--text-muted)",
                        fontFamily: "var(--font-mono)",
                      }}
                    >
                      Card {index + 1}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
