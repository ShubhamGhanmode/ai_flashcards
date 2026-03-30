"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { APIClientError, type DeckResponse, getDeck } from "@/lib/api";
import { getCachedDeck } from "@/lib/deck-session";
import { DeckSwiper } from "@/components/flashcards/DeckSwiper";

export default function DeckPage() {
  const params = useParams();
  const router = useRouter();
  const deckId = params.deckId as string;
  const [cachedDeck] = useState<DeckResponse | null>(() => getCachedDeck(deckId));

  const [deck, setDeck] = useState<DeckResponse | null>(cachedDeck);
  const [loading, setLoading] = useState(cachedDeck === null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (cachedDeck) {
      return;
    }

    async function loadDeck() {
      try {
        const data = await getDeck(deckId);
        setDeck(data);
      } catch (err) {
        if (err instanceof APIClientError) {
          setError(err.error.message);
        } else {
          setError("Failed to load deck");
        }
      } finally {
        setLoading(false);
      }
    }

    void loadDeck();
  }, [cachedDeck, deckId]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center px-6" style={{ background: "var(--bg-primary)" }}>
        <div className="glass rounded-[28px] max-w-md w-full p-8 text-center">
          <div
            className="mx-auto h-12 w-12 animate-spin rounded-full"
            style={{
              border: "3px solid var(--bg-elevated)",
              borderTopColor: "var(--accent-primary)",
            }}
          />
          <h1 className="mt-6 text-2xl" style={{ fontFamily: "var(--font-display)" }}>
            Loading your deck
          </h1>
          <p className="mt-3 text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>
            Pulling the saved card stack so you can jump straight back into the study flow.
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center px-6" style={{ background: "var(--bg-primary)" }}>
        <div className="glass rounded-[28px] max-w-md w-full p-8 text-center">
          <p className="text-sm uppercase tracking-[0.28em]" style={{ color: "#fca5a5", fontFamily: "var(--font-mono)" }}>
            Deck unavailable
          </p>
          <p className="mt-4 text-base leading-relaxed" style={{ color: "var(--text-primary)" }}>
            {error}
          </p>
          <button
            onClick={() => router.push("/")}
            className="mt-6 rounded-full px-5 py-3 text-sm font-medium"
            style={{
              background: "var(--accent-gradient)",
              color: "var(--bg-primary)",
              fontFamily: "var(--font-display)",
            }}
          >
            Back to home
          </button>
        </div>
      </div>
    );
  }

  if (!deck) {
    return null;
  }

  return <DeckSwiper deck={deck} />;
}
