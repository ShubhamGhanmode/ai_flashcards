import { render, screen } from "@testing-library/react";
import { useRouter } from "next/navigation";
import Home from "@/app/page";

jest.mock("next/navigation", () => ({
  useRouter: jest.fn(),
}));

describe("Home Page", () => {
  beforeEach(() => {
    (useRouter as jest.Mock).mockReturnValue({
      push: jest.fn(),
    });
  });

  it("renders the main heading", () => {
    render(<Home />);
    expect(
      screen.getByRole("heading", { level: 1, name: /master any topic with/i }),
    ).toBeInTheDocument();
  });

  it("renders the topic input", () => {
    render(<Home />);
    expect(
      screen.getByLabelText(/what do you want to learn/i),
    ).toBeInTheDocument();
  });

  it("renders the difficulty level buttons", () => {
    render(<Home />);
    expect(screen.getByRole("button", { name: /beginner/i })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /intermediate/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /advanced/i })).toBeInTheDocument();
  });

  it("renders the submit button", () => {
    render(<Home />);
    expect(
      screen.getByRole("button", { name: /generate flashcards/i }),
    ).toBeInTheDocument();
  });
});
