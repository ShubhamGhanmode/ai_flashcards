import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, fireEvent, render, screen } from "@testing-library/react";
import type { DeckResponse } from "@/lib/api";
import { DeckSwiper } from "@/components/flashcards/DeckSwiper";

function buildDeck(): DeckResponse {
  return {
    schema_version: "1.0",
    deck_id: "123e4567-e89b-12d3-a456-426614174000",
    topic: "Binary Search Trees",
    difficulty_level: "beginner",
    concepts: [
      {
        card_id: "123e4567-e89b-12d3-a456-426614174001",
        title: "Node structure",
        bullets: [
          "Each node stores one value.",
          "Nodes keep links to children.",
          "Left children contain smaller values.",
          "Right children contain larger values.",
          "Empty links mark leaves.",
        ],
        example_possible: true,
      },
      {
        card_id: "123e4567-e89b-12d3-a456-426614174002",
        title: "Traversal",
        bullets: [
          "In-order traversal returns sorted values.",
          "Pre-order visits the root first.",
          "Post-order visits children before the root.",
          "Traversal order changes the output meaning.",
          "Recursive and iterative forms both work.",
        ],
        example_possible: false,
      },
      {
        card_id: "123e4567-e89b-12d3-a456-426614174003",
        title: "Balancing",
        bullets: [
          "Balanced trees keep operations fast.",
          "Skewed trees degrade toward linked lists.",
          "Rotations restore shape after inserts.",
          "Self-balancing variants automate repairs.",
          "Tree height drives worst-case cost.",
        ],
        example_possible: false,
      },
    ],
    generation_metadata: {
      model: "gpt-5-nano",
      prompt_version: "v1",
      tokens: {
        prompt: 100,
        completion: 200,
        total: 300,
      },
      timestamp: "2026-03-08T00:00:00Z",
      rag_used: false,
    },
  };
}

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
}

function renderWithClient(ui: ReactNode) {
  const queryClient = createQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>,
  );
}

describe("DeckSwiper", () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
  });

  it("flips the active card and advances through the stack", () => {
    renderWithClient(<DeckSwiper deck={buildDeck()} />);

    expect(
      screen.getByRole("heading", { level: 2, name: /node structure/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /reveal notes/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /reveal notes/i }));
    expect(screen.getByText(/left children contain smaller values/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /send to back/i }));
    act(() => {
      jest.advanceTimersByTime(320);
    });

    expect(
      screen.getByRole("heading", { level: 2, name: /traversal/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /reveal notes/i })).toBeInTheDocument();
  });
});
