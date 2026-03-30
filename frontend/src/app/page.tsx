"use client";

import { startTransition, useState } from "react";
import { useRouter } from "next/navigation";
import {
  APIClientError,
  type DeckGenerationStatusEvent,
  streamDeckGeneration,
} from "@/lib/api";
import { cacheDeck } from "@/lib/deck-session";
import { EstimatePreview } from "@/components/flashcards/EstimatePreview";
import { GenerationStudio } from "@/components/flashcards/GenerationStudio";

type DifficultyLevel = "beginner" | "intermediate" | "advanced";

const DIFFICULTY_OPTIONS = [
  { value: "beginner", label: "Beginner", icon: "o", hint: "Foundations" },
  { value: "intermediate", label: "Intermediate", icon: "O", hint: "Concept links" },
  { value: "advanced", label: "Advanced", icon: "@", hint: "Exam depth" },
];

const TOPIC_SUGGESTIONS = [
  "Binary Search Trees",
  "Photosynthesis",
  "Neural Networks",
  "Supply and Demand",
  "World War II",
  "Spanish Basics",
];

const WHY_IT_WORKS = [
  {
    title: "Live momentum",
    desc: "The builder streams real status updates instead of freezing on a spinner.",
  },
  {
    title: "Atomic focus",
    desc: "Each card is shaped around one concept with five concrete takeaways.",
  },
  {
    title: "Examples on demand",
    desc: "Example generation stays optional so the first pass stays fast.",
  },
];

export default function Home() {
  const [topic, setTopic] = useState("");
  const [difficulty, setDifficulty] = useState<DifficultyLevel>("beginner");
  const [cardCount, setCardCount] = useState(5);
  const [isLoading, setIsLoading] = useState(false);
  const [generationEvent, setGenerationEvent] = useState<DeckGenerationStatusEvent | null>(null);
  const [error, setError] = useState<string | null>(null);

  const difficultyMeta = DIFFICULTY_OPTIONS.find((level) => level.value === difficulty);
  const topicDisplay = topic.trim() || "Your topic";
  const previewPoints = [
    "Definition and core idea",
    "Key terms and relations",
    "Common pitfall to avoid",
    "Concrete example prompt",
    "Quick recall check",
  ];

  const router = useRouter();

  const handleSuggestion = (value: string) => {
    setTopic(value);
    setError(null);
  };

  const getDeckErrorMessage = (apiError: APIClientError): string => {
    switch (apiError.error.code) {
      case "RATE_LIMITED":
        if (typeof apiError.error.retry_after_seconds === "number") {
          return `Too many requests. Try again in ${apiError.error.retry_after_seconds} seconds.`;
        }
        return "Too many requests. Please wait a moment and try again.";
      case "QUOTA_EXCEEDED":
        return "Daily deck limit reached. Try again tomorrow.";
      case "CIRCUIT_BREAKER_OPEN":
        return "Generation service is recovering. Please retry shortly.";
      default:
        return apiError.error.message;
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!topic.trim()) {
      setError("Please enter a topic");
      return;
    }

    setIsLoading(true);
    setGenerationEvent(null);

    try {
      const deck = await streamDeckGeneration(
        {
          topic: topic.trim(),
          difficulty_level: difficulty,
          max_concepts: cardCount,
        },
        {
          onEvent: (event) => {
            if (event.type === "status" || event.type === "heartbeat") {
              setGenerationEvent(event);
            }
          },
        },
      );

      cacheDeck(deck);
      startTransition(() => {
        router.push(`/deck/${deck.deck_id}`);
      });
    } catch (err) {
      if (err instanceof APIClientError) {
        setError(getDeckErrorMessage(err));
      } else {
        setError("Failed to generate deck. Please try again.");
      }
      setGenerationEvent(null);
      setIsLoading(false);
    }
  };

  return (
    <main className="min-h-screen relative overflow-hidden" style={{ background: "var(--bg-primary)" }}>
      <div
        className="absolute top-[-20%] right-[-10%] w-[600px] h-[600px] rounded-full opacity-20 blur-3xl pointer-events-none"
        style={{
          background: "radial-gradient(circle, rgba(245, 158, 11, 0.3) 0%, transparent 70%)",
        }}
      />
      <div
        className="absolute bottom-[-30%] left-[-15%] w-[800px] h-[800px] rounded-full opacity-10 blur-3xl pointer-events-none"
        style={{
          background: "radial-gradient(circle, rgba(251, 191, 36, 0.2) 0%, transparent 70%)",
        }}
      />

      <div className="relative z-10 container mx-auto px-6 py-16 lg:py-24">
        <header className="max-w-4xl mb-16 animate-slide-up">
          <div
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full mb-8 text-xs font-medium tracking-wide uppercase"
            style={{
              background: "var(--bg-glass)",
              border: "1px solid var(--border-subtle)",
              color: "var(--text-secondary)",
              fontFamily: "var(--font-mono)",
            }}
          >
            <span className="w-2 h-2 rounded-full animate-pulse" style={{ background: "var(--accent-primary)" }} />
            AI-powered learning
          </div>

          <h1
            className="text-5xl lg:text-7xl font-semibold leading-[1.1] mb-6"
            style={{
              fontFamily: "var(--font-display)",
              color: "var(--text-primary)",
            }}
          >
            Master any topic with{" "}
            <span
              className="relative inline-block"
              style={{
                background: "var(--accent-gradient)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                backgroundClip: "text",
              }}
            >
              flashcards
            </span>
          </h1>

          <p className="text-lg lg:text-xl max-w-2xl leading-relaxed" style={{ color: "var(--text-secondary)" }}>
            Generate structured, AI-curated flashcard decks in seconds, then move through them like a real card stack
            instead of a static content swap.
          </p>

          <div className="mt-8 flex flex-wrap items-center gap-3">
            <span className="chip">No sign-up</span>
            <span className="chip">3-7 cards</span>
            <span className="chip">Live generation stream</span>
          </div>
        </header>

        <div className="grid lg:grid-cols-[minmax(0,1fr)_420px] gap-16 items-start">
          <section className="glass-accent rounded-2xl p-8 lg:p-10 animate-slide-up animate-delay-100">
            <div className="flex items-center justify-between mb-8">
              <div>
                <p
                  className="text-xs uppercase tracking-widest mb-2"
                  style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}
                >
                  Deck builder
                </p>
                <h2 className="text-2xl font-semibold" style={{ fontFamily: "var(--font-display)" }}>
                  Build your deck
                </h2>
              </div>
              <div className="flex items-center gap-2 text-xs" style={{ color: "var(--text-muted)" }}>
                <span className="step-dot step-dot-active" />
                <span className="step-dot" />
                <span className="step-dot" />
                <span className="ml-2" style={{ fontFamily: "var(--font-mono)" }}>
                  Step 1 of 3
                </span>
              </div>
            </div>

            <form onSubmit={handleSubmit} className="space-y-8">
              <div className="space-y-3">
                <label
                  htmlFor="topic"
                  className="block text-sm font-medium uppercase tracking-wider"
                  style={{
                    color: "var(--text-secondary)",
                    fontFamily: "var(--font-mono)",
                    fontSize: "11px",
                  }}
                >
                  What do you want to learn?
                </label>
                <input
                  type="text"
                  id="topic"
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  placeholder="e.g., Binary Search Trees, Photosynthesis"
                  className="w-full px-5 py-4 rounded-xl text-base transition-all duration-200 focus:outline-none"
                  style={{
                    background: "var(--bg-secondary)",
                    border: "1px solid var(--border-subtle)",
                    color: "var(--text-primary)",
                    fontFamily: "var(--font-body)",
                  }}
                  maxLength={200}
                  aria-describedby="topic-help"
                />
                <div className="flex flex-wrap gap-2">
                  {TOPIC_SUGGESTIONS.map((suggestion) => (
                    <button
                      key={suggestion}
                      type="button"
                      className="chip"
                      onClick={() => handleSuggestion(suggestion)}
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
                <p id="topic-help" className="text-xs" style={{ color: "var(--text-muted)" }}>
                  Tip: pick a narrow slice for faster, sharper decks.
                </p>
              </div>

              <div>
                <label
                  className="block text-sm font-medium mb-4 uppercase tracking-wider"
                  style={{
                    color: "var(--text-secondary)",
                    fontFamily: "var(--font-mono)",
                    fontSize: "11px",
                  }}
                >
                  Difficulty level
                </label>
                <div className="flex gap-3" role="radiogroup" aria-label="Difficulty level">
                  {DIFFICULTY_OPTIONS.map((level) => (
                    <button
                      key={level.value}
                      type="button"
                      onClick={() => setDifficulty(level.value as DifficultyLevel)}
                      aria-pressed={difficulty === level.value}
                      className="flex-1 py-3 px-4 rounded-lg text-sm font-medium transition-all duration-200"
                      style={{
                        background: difficulty === level.value ? "var(--accent-primary)" : "var(--bg-secondary)",
                        color: difficulty === level.value ? "var(--bg-primary)" : "var(--text-secondary)",
                        border: `1px solid ${difficulty === level.value ? "var(--accent-primary)" : "var(--border-subtle)"}`,
                        fontFamily: "var(--font-body)",
                      }}
                    >
                      <span className="mr-2">{level.icon}</span>
                      {level.label}
                    </button>
                  ))}
                </div>
                <p className="mt-3 text-xs" style={{ color: "var(--text-muted)" }}>
                  {difficultyMeta?.hint}
                </p>
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <label
                    htmlFor="card-count"
                    className="text-sm font-medium uppercase tracking-wider"
                    style={{
                      color: "var(--text-secondary)",
                      fontFamily: "var(--font-mono)",
                      fontSize: "11px",
                    }}
                  >
                    Cards per deck
                  </label>
                  <span className="text-xs" style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                    {cardCount} cards
                  </span>
                </div>
                <input
                  id="card-count"
                  type="range"
                  min={3}
                  max={7}
                  step={1}
                  value={cardCount}
                  onChange={(e) => setCardCount(Number(e.target.value))}
                  className="range"
                  aria-label="Cards per deck"
                />
                <div className="flex items-center justify-between text-xs" style={{ color: "var(--text-muted)" }}>
                  <span>3</span>
                  <span>7</span>
                </div>
              </div>

              <EstimatePreview topic={topic} difficultyLevel={difficulty} maxConcepts={cardCount} />

              {error && (
                <div
                  className="p-4 rounded-lg text-sm"
                  style={{
                    background: "rgba(239, 68, 68, 0.1)",
                    border: "1px solid rgba(239, 68, 68, 0.3)",
                    color: "#fca5a5",
                  }}
                  role="alert"
                >
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-4 px-6 rounded-xl text-base font-semibold transition-all duration-200 flex items-center justify-center gap-3 group"
                style={{
                  background: isLoading ? "var(--bg-elevated)" : "var(--accent-gradient)",
                  color: isLoading ? "var(--text-muted)" : "var(--bg-primary)",
                  boxShadow: isLoading ? "none" : "var(--shadow-glow)",
                  fontFamily: "var(--font-display)",
                }}
              >
                {isLoading ? (
                  <>
                    <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" fill="none" />
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                      />
                    </svg>
                    Opening live build...
                  </>
                ) : (
                  <>
                    Generate flashcards
                    <span className="transition-transform group-hover:translate-x-1">-&gt;</span>
                  </>
                )}
              </button>
            </form>

            <p className="text-center mt-6 text-xs" style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
              {cardCount} cards - {difficultyMeta?.label ?? "Beginner"} difficulty
            </p>
          </section>

          <aside className="space-y-6 animate-slide-up animate-delay-200 lg:sticky lg:top-10">
            <div className="glass p-6 rounded-2xl">
              <div className="flex items-center justify-between">
                <div>
                  <p
                    className="text-xs uppercase tracking-widest mb-2"
                    style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}
                  >
                    Preview
                  </p>
                  <h3 className="text-lg font-semibold" style={{ fontFamily: "var(--font-display)" }}>
                    Deck preview
                  </h3>
                </div>
                <span className="text-xs" style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                  Live
                </span>
              </div>

              <div className="relative h-56 mt-6">
                <div
                  className="absolute inset-0 stack-card p-5"
                  style={{ transform: "translateY(22px) rotate(-3deg)", opacity: 0.5 }}
                >
                  <p className="text-[11px] uppercase" style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                    Example
                  </p>
                  <p className="mt-3 text-sm" style={{ color: "var(--text-secondary)" }}>
                    How would you apply {topicDisplay} in practice?
                  </p>
                </div>
                <div
                  className="absolute inset-0 stack-card p-5"
                  style={{ transform: "translateY(10px) rotate(-1deg)", opacity: 0.8 }}
                >
                  <p className="text-[11px] uppercase" style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                    Back
                  </p>
                  <ul className="mt-3 space-y-2 text-xs" style={{ color: "var(--text-secondary)" }}>
                    {previewPoints.map((point) => (
                      <li key={point} className="flex items-start gap-2">
                        <span className="mt-[3px]" style={{ color: "var(--accent-primary)" }}>
                          -
                        </span>
                        <span>{point}</span>
                      </li>
                    ))}
                  </ul>
                </div>
                <div className="relative stack-card p-5 h-full">
                  <p className="text-[11px] uppercase" style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                    Front
                  </p>
                  <h4 className="mt-4 text-lg font-semibold" style={{ color: "var(--text-primary)" }}>
                    {topicDisplay}
                  </h4>
                  <p className="mt-2 text-sm" style={{ color: "var(--text-muted)" }}>
                    Flip the top card to reveal key points, then send it to the back of the pack.
                  </p>
                </div>
              </div>
            </div>

            <div className="glass p-6 rounded-2xl">
              <p
                className="text-xs uppercase tracking-widest mb-2"
                style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}
              >
                Snapshot
              </p>
              <h3 className="text-lg font-semibold" style={{ fontFamily: "var(--font-display)" }}>
                Deck summary
              </h3>

              <div className="mt-4 space-y-3 text-sm">
                <div className="flex items-center justify-between">
                  <span style={{ color: "var(--text-muted)" }}>Topic</span>
                  <span style={{ color: "var(--text-primary)" }}>{topicDisplay}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span style={{ color: "var(--text-muted)" }}>Cards</span>
                  <span style={{ color: "var(--text-primary)" }}>{cardCount}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span style={{ color: "var(--text-muted)" }}>Difficulty</span>
                  <span style={{ color: "var(--text-primary)" }}>{difficultyMeta?.label ?? "Beginner"}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span style={{ color: "var(--text-muted)" }}>Generation</span>
                  <span style={{ color: "var(--text-primary)" }}>Streamed</span>
                </div>
              </div>
            </div>

            <div className="glass p-6 rounded-2xl">
              <p
                className="text-xs uppercase tracking-widest mb-2"
                style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}
              >
                Why it works
              </p>
              <h3 className="text-lg font-semibold" style={{ fontFamily: "var(--font-display)" }}>
                Study smarter
              </h3>
              <div className="mt-4 space-y-4">
                {WHY_IT_WORKS.map((item) => (
                  <div key={item.title}>
                    <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
                      {item.title}
                    </p>
                    <p className="text-xs" style={{ color: "var(--text-secondary)" }}>
                      {item.desc}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </aside>
        </div>

        <footer
          className="mt-24 pt-8 border-t text-sm flex flex-col gap-3 md:flex-row md:items-center md:justify-between"
          style={{
            borderColor: "var(--border-subtle)",
            color: "var(--text-muted)",
          }}
        >
          <span style={{ fontFamily: "var(--font-mono)" }}>Flashcard Learning Assistant</span>
          <span>No account required. Decks generated in seconds.</span>
        </footer>
      </div>

      {isLoading && (
        <GenerationStudio
          topic={topic.trim()}
          difficultyLabel={difficultyMeta?.label ?? "Beginner"}
          cardCount={cardCount}
          event={generationEvent}
        />
      )}
    </main>
  );
}
