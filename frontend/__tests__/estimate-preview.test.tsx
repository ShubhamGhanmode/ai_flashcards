import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { EstimatePreview } from "@/components/flashcards/EstimatePreview";
import { estimateDeck, type DeckEstimateResponse } from "@/lib/api";

jest.mock("@/lib/api", () => {
  const actual = jest.requireActual("@/lib/api");
  return {
    ...actual,
    estimateDeck: jest.fn(),
  };
});

const mockedEstimateDeck = estimateDeck as jest.MockedFunction<typeof estimateDeck>;

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
}

function renderWithClient(ui: ReactNode, queryClient: QueryClient) {
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>,
  );
}

function buildEstimateResponse(): DeckEstimateResponse {
  return {
    schema_version: "1.0",
    model: "gpt-5-nano",
    estimated_tokens: {
      prompt: 120,
      completion: 300,
      total: 420,
    },
    estimated_cost_usd: 0.0012,
    estimated_cost_cents: 0,
    estimated_seconds: 1.9,
  };
}

describe("EstimatePreview", () => {
  beforeEach(() => {
    mockedEstimateDeck.mockReset();
  });

  it("does not render for short topics", () => {
    const queryClient = createQueryClient();
    renderWithClient(
      <EstimatePreview
        topic="AI"
        difficultyLevel="beginner"
        maxConcepts={5}
      />,
      queryClient,
    );

    expect(screen.queryByText(/estimate/i)).not.toBeInTheDocument();
    expect(mockedEstimateDeck).not.toHaveBeenCalled();
  });

  it("renders estimate metrics on success", async () => {
    mockedEstimateDeck.mockResolvedValueOnce(buildEstimateResponse());
    const queryClient = createQueryClient();
    renderWithClient(
      <EstimatePreview
        topic="Binary Search Trees"
        difficultyLevel="beginner"
        maxConcepts={5}
      />,
      queryClient,
    );

    await waitFor(() => expect(mockedEstimateDeck).toHaveBeenCalledTimes(1));
    await waitFor(() =>
      expect(screen.getByText(/420/i)).toBeInTheDocument(),
    );
    expect(screen.getByText(/\$0\.0012/i)).toBeInTheDocument();
    expect(screen.getByText(/1\.9s/i)).toBeInTheDocument();
  });

  it("hides estimate when request fails", async () => {
    mockedEstimateDeck.mockRejectedValueOnce(new Error("failed"));
    const queryClient = createQueryClient();
    renderWithClient(
      <EstimatePreview
        topic="Neural Networks"
        difficultyLevel="beginner"
        maxConcepts={5}
      />,
      queryClient,
    );

    await waitFor(() => expect(mockedEstimateDeck).toHaveBeenCalledTimes(1));
    await waitFor(() =>
      expect(screen.queryByText(/estimate/i)).not.toBeInTheDocument(),
    );
  });

  it("renders a loading skeleton while estimate is pending", async () => {
    mockedEstimateDeck.mockReturnValue(new Promise<DeckEstimateResponse>(() => {}));
    const queryClient = createQueryClient();
    renderWithClient(
      <EstimatePreview
        topic="Graph Algorithms"
        difficultyLevel="beginner"
        maxConcepts={5}
      />,
      queryClient,
    );

    await waitFor(() => expect(mockedEstimateDeck).toHaveBeenCalledTimes(1));
    expect(screen.getByTestId("estimate-skeleton")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(/calculating estimate/i);
  });
});
