import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import Home from "@/app/page";
import { streamDeckGeneration, type DeckResponse } from "@/lib/api";

jest.mock("next/navigation", () => ({
  useRouter: jest.fn(),
}));

jest.mock("@/lib/api", () => {
  const actual = jest.requireActual("@/lib/api");
  return {
    ...actual,
    streamDeckGeneration: jest.fn(),
  };
});

const mockedStreamDeckGeneration = streamDeckGeneration as jest.MockedFunction<typeof streamDeckGeneration>;

function buildDeckResponse(): DeckResponse {
  return {
    schema_version: "1.0",
    deck_id: "123e4567-e89b-12d3-a456-426614174000",
    topic: "Binary Search Trees",
    difficulty_level: "beginner",
    concepts: [
      {
        card_id: "123e4567-e89b-12d3-a456-426614174001",
        title: "Node structure",
        bullets: ["A", "B", "C", "D", "E"],
        example_possible: true,
      },
      {
        card_id: "123e4567-e89b-12d3-a456-426614174002",
        title: "Traversal",
        bullets: ["A", "B", "C", "D", "E"],
        example_possible: true,
      },
      {
        card_id: "123e4567-e89b-12d3-a456-426614174003",
        title: "Balancing",
        bullets: ["A", "B", "C", "D", "E"],
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

describe("Home Page", () => {
  function renderHome() {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    return render(
      <QueryClientProvider client={queryClient}>
        <Home />
      </QueryClientProvider>,
    );
  }

  beforeEach(() => {
    (useRouter as jest.Mock).mockReturnValue({
      push: jest.fn(),
    });
    mockedStreamDeckGeneration.mockReset();
  });

  it("renders the main heading", () => {
    renderHome();
    expect(
      screen.getByRole("heading", { level: 1, name: /master any topic with/i }),
    ).toBeInTheDocument();
  });

  it("renders the topic input", () => {
    renderHome();
    expect(
      screen.getByLabelText(/what do you want to learn/i),
    ).toBeInTheDocument();
  });

  it("renders the difficulty level buttons", () => {
    renderHome();
    expect(screen.getByRole("button", { name: /beginner/i })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /intermediate/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /advanced/i })).toBeInTheDocument();
  });

  it("renders the submit button", () => {
    renderHome();
    expect(
      screen.getByRole("button", { name: /generate flashcards/i }),
    ).toBeInTheDocument();
  });

  it("shows the generation overlay while streaming is active", async () => {
    mockedStreamDeckGeneration.mockImplementation(async (_request, options) => {
      options?.onEvent?.({
        type: "status",
        phase: "queued",
        message: "Shaping the prompt and sequencing the study arc.",
        stage_index: 1,
        stage_total: 3,
        elapsed_seconds: 0,
        estimated_seconds: 4.2,
      });
      return new Promise<DeckResponse>(() => {});
    });

    renderHome();

    fireEvent.change(screen.getByLabelText(/what do you want to learn/i), {
      target: { value: "Binary Search Trees" },
    });
    fireEvent.click(screen.getByRole("button", { name: /generate flashcards/i }));

    expect(
      await screen.findByRole("heading", {
        level: 2,
        name: /building your deck without the dead air/i,
      }),
    ).toBeInTheDocument();
    expect(screen.getByText(/shaping the prompt and sequencing the study arc/i)).toBeInTheDocument();
  });

  it("routes to the deck page when the stream completes", async () => {
    const push = jest.fn();
    (useRouter as jest.Mock).mockReturnValue({ push });
    mockedStreamDeckGeneration.mockResolvedValueOnce(buildDeckResponse());

    renderHome();

    fireEvent.change(screen.getByLabelText(/what do you want to learn/i), {
      target: { value: "Binary Search Trees" },
    });
    fireEvent.click(screen.getByRole("button", { name: /generate flashcards/i }));

    await waitFor(() =>
      expect(push).toHaveBeenCalledWith("/deck/123e4567-e89b-12d3-a456-426614174000"),
    );
  });
});
