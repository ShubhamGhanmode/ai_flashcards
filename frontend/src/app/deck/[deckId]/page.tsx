"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { getDeck, DeckResponse, APIClientError } from "@/lib/api";
import { DeckSwiper } from "@/components/flashcards/DeckSwiper";

export default function DeckPage() {
  const params = useParams();
  const router = useRouter();
  const deckId = params.deckId as string;

  const [deck, setDeck] = useState<DeckResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
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

    loadDeck();
  }, [deckId]);

  if (loading) {
    return (
      <div
        className="min-h-screen flex items-center justify-center"
        style={{ background: "var(--bg-primary)" }}
      >
        <div className="text-center">
          <div
            className="animate-spin h-12 w-12 rounded-full mx-auto mb-4"
            style={{
              border: "3px solid var(--bg-elevated)",
              borderTopColor: "var(--accent-primary)",
            }}
          />
          <p
            className="text-sm"
            style={{
              color: "var(--text-muted)",
              fontFamily: "var(--font-mono)",
            }}
          >
            Loading deck...
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div
        className="min-h-screen flex items-center justify-center"
        style={{ background: "var(--bg-primary)" }}
      >
        <div className="text-center">
          <p className="mb-4" style={{ color: "#fca5a5" }}>
            {error}
          </p>
          <button
            onClick={() => router.push("/")}
            className="px-6 py-3 rounded-xl text-sm font-medium"
            style={{
              background: "var(--accent-gradient)",
              color: "var(--bg-primary)",
              fontFamily: "var(--font-display)",
            }}
          >
            Back to Home
          </button>
        </div>
      </div>
    );
  }

  if (!deck) return null;

  return <DeckSwiper deck={deck} />;
}
