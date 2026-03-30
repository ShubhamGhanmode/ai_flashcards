"use client";

import type { DeckResponse } from "./api";

const SESSION_PREFIX = "flashcards:deck:";

function getSessionKey(deckId: string): string {
  return `${SESSION_PREFIX}${deckId}`;
}

export function cacheDeck(deck: DeckResponse): void {
  if (typeof window === "undefined") {
    return;
  }

  window.sessionStorage.setItem(
    getSessionKey(deck.deck_id),
    JSON.stringify(deck),
  );
}

export function getCachedDeck(deckId: string): DeckResponse | null {
  if (typeof window === "undefined") {
    return null;
  }

  const rawValue = window.sessionStorage.getItem(getSessionKey(deckId));
  if (!rawValue) {
    return null;
  }

  try {
    return JSON.parse(rawValue) as DeckResponse;
  } catch {
    return null;
  }
}
