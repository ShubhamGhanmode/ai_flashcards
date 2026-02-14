import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { Flashcard } from "@/components/flashcards/Flashcard";
import { ExamplePanel } from "@/components/flashcards/ExamplePanel";
import { APIClientError, generateCardExample, type ExampleResponse } from "@/lib/api";

jest.mock("@/lib/api", () => {
  const actual = jest.requireActual("@/lib/api");
  return {
    ...actual,
    generateCardExample: jest.fn(),
  };
});

const mockedGenerateCardExample = generateCardExample as jest.MockedFunction<
  typeof generateCardExample
>;

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        staleTime: 24 * 60 * 60 * 1000,
        gcTime: 24 * 60 * 60 * 1000,
      },
    },
  });
}

function renderWithClient(ui: ReactNode, client: QueryClient) {
  return render(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

function buildExampleResponse(cardId: string): ExampleResponse {
  return {
    schema_version: "1.0",
    card_id: cardId,
    example: "Picture a library index where each shelf decision narrows the search.",
    steps: ["Start at the root shelf", "Go left for smaller, right for larger"],
    pitfalls: ["Unbalanced trees can degrade lookup speed."],
    generation_metadata: {
      model: "gpt-4o-mini",
      prompt_version: "v1",
      tokens: {
        prompt: 10,
        completion: 22,
        total: 32,
      },
      timestamp: "2026-01-01T00:00:00Z",
      rag_used: false,
    },
  };
}

describe("ExamplePanel", () => {
  beforeEach(() => {
    mockedGenerateCardExample.mockReset();
  });

  it("hides show-example button when concept.example_possible is false", () => {
    render(
      <Flashcard
        concept={{
          card_id: "card-1",
          title: "Binary Search Tree",
          bullets: ["b1", "b2", "b3", "b4", "b5"],
          example_possible: false,
        }}
        index={0}
        total={1}
      />,
    );

    expect(
      screen.queryByRole("button", { name: /show example/i }),
    ).not.toBeInTheDocument();
  });

  it("shows show-example button when concept.example_possible is true", () => {
    const queryClient = createQueryClient();
    renderWithClient(
      <Flashcard
        concept={{
          card_id: "card-1",
          title: "Binary Search Tree",
          bullets: ["b1", "b2", "b3", "b4", "b5"],
          example_possible: true,
        }}
        index={0}
        total={1}
      />,
      queryClient,
    );

    expect(
      screen.getByRole("button", { name: /show example/i }),
    ).toBeInTheDocument();
  });

  it("renders loading then success content after clicking show example", async () => {
    const cardId = "00000000-0000-0000-0000-000000000111";
    mockedGenerateCardExample.mockResolvedValueOnce(buildExampleResponse(cardId));

    const queryClient = createQueryClient();
    renderWithClient(<ExamplePanel cardId={cardId} />, queryClient);

    fireEvent.click(screen.getByRole("button", { name: /show example/i }));
    expect(screen.getByText(/generating example/i)).toBeInTheDocument();

    await waitFor(() =>
      expect(screen.getByText(/library index/i)).toBeInTheDocument(),
    );
    expect(screen.getByText(/steps/i)).toBeInTheDocument();
    expect(screen.getByText(/pitfalls/i)).toBeInTheDocument();
  });

  it("reuses cached result for same query key when panel is reopened", async () => {
    const cardId = "00000000-0000-0000-0000-000000000222";
    mockedGenerateCardExample.mockResolvedValueOnce(buildExampleResponse(cardId));

    const queryClient = createQueryClient();
    const first = renderWithClient(<ExamplePanel cardId={cardId} />, queryClient);

    fireEvent.click(screen.getByRole("button", { name: /show example/i }));
    await waitFor(() =>
      expect(screen.getByText(/library index/i)).toBeInTheDocument(),
    );

    first.unmount();
    renderWithClient(<ExamplePanel cardId={cardId} />, queryClient);

    fireEvent.click(screen.getByRole("button", { name: /show example/i }));
    await waitFor(() =>
      expect(screen.getByText(/library index/i)).toBeInTheDocument(),
    );

    expect(mockedGenerateCardExample).toHaveBeenCalledTimes(1);
  });

  it("shows error then allows retry", async () => {
    const cardId = "00000000-0000-0000-0000-000000000333";
    mockedGenerateCardExample
      .mockRejectedValueOnce(
        new APIClientError(
          {
            code: "LLM_PROVIDER_ERROR",
            message: "Provider unavailable",
            retryable: true,
          },
          502,
        ),
      )
      .mockResolvedValueOnce(buildExampleResponse(cardId));

    const queryClient = createQueryClient();
    renderWithClient(<ExamplePanel cardId={cardId} />, queryClient);

    fireEvent.click(screen.getByRole("button", { name: /show example/i }));
    await waitFor(() =>
      expect(screen.getByText(/provider unavailable/i)).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByRole("button", { name: /retry/i }));
    await waitFor(() =>
      expect(screen.getByText(/library index/i)).toBeInTheDocument(),
    );

    expect(mockedGenerateCardExample).toHaveBeenCalledTimes(2);
  });
});
