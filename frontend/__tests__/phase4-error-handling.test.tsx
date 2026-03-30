import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useRouter } from "next/navigation";
import Home from "@/app/page";
import {
  APIClientError,
  estimateDeck,
  generateDeck,
} from "@/lib/api";

jest.mock("next/navigation", () => ({
  useRouter: jest.fn(),
}));

jest.mock("@/lib/api", () => {
  const actual = jest.requireActual("@/lib/api");
  return {
    ...actual,
    generateDeck: jest.fn(),
    estimateDeck: jest.fn(),
  };
});

const mockedGenerateDeck = generateDeck as jest.MockedFunction<typeof generateDeck>;
const mockedEstimateDeck = estimateDeck as jest.MockedFunction<typeof estimateDeck>;

function renderHome() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <Home />
    </QueryClientProvider>,
  );
}

describe("Phase 4 deck error handling", () => {
  beforeEach(() => {
    (useRouter as jest.Mock).mockReturnValue({
      push: jest.fn(),
    });
    mockedGenerateDeck.mockReset();
    mockedEstimateDeck.mockReset();
    mockedEstimateDeck.mockResolvedValue({
      schema_version: "1.0",
      model: "gpt-5-nano",
      estimated_tokens: { prompt: 1, completion: 1, total: 2 },
      estimated_cost_usd: 0,
      estimated_cost_cents: 0,
      estimated_seconds: 0.5,
    });
  });

  it("maps RATE_LIMITED to countdown message", async () => {
    mockedGenerateDeck.mockRejectedValueOnce(
      new APIClientError(
        {
          code: "RATE_LIMITED",
          message: "raw",
          retryable: true,
          retry_after_seconds: 14,
        },
        429,
      ),
    );

    renderHome();
    fireEvent.change(screen.getByLabelText(/what do you want to learn/i), {
      target: { value: "Binary Search Trees" },
    });
    fireEvent.click(screen.getByRole("button", { name: /generate flashcards/i }));

    await waitFor(() =>
      expect(
        screen.getByText(/try again in 14 seconds/i),
      ).toBeInTheDocument(),
    );
  });

  it("maps QUOTA_EXCEEDED to daily-limit message", async () => {
    mockedGenerateDeck.mockRejectedValueOnce(
      new APIClientError(
        {
          code: "QUOTA_EXCEEDED",
          message: "raw",
          retryable: false,
        },
        429,
      ),
    );

    renderHome();
    fireEvent.change(screen.getByLabelText(/what do you want to learn/i), {
      target: { value: "Binary Search Trees" },
    });
    fireEvent.click(screen.getByRole("button", { name: /generate flashcards/i }));

    await waitFor(() =>
      expect(
        screen.getByText(/daily deck limit reached\. try again tomorrow\./i),
      ).toBeInTheDocument(),
    );
  });

  it("maps CIRCUIT_BREAKER_OPEN to recovery message", async () => {
    mockedGenerateDeck.mockRejectedValueOnce(
      new APIClientError(
        {
          code: "CIRCUIT_BREAKER_OPEN",
          message: "raw",
          retryable: true,
        },
        503,
      ),
    );

    renderHome();
    fireEvent.change(screen.getByLabelText(/what do you want to learn/i), {
      target: { value: "Binary Search Trees" },
    });
    fireEvent.click(screen.getByRole("button", { name: /generate flashcards/i }));

    await waitFor(() =>
      expect(
        screen.getByText(/generation service is recovering\. please retry shortly\./i),
      ).toBeInTheDocument(),
    );
  });
});
