import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { StatusBar } from "./StatusBar";

describe("StatusBar", () => {
  it("shows the review status and which reviewer is in use", () => {
    render(<StatusBar status="success" reviewerLabel="Reviewer: placeholder" />);
    expect(screen.getByRole("status")).toHaveTextContent("Review complete");
    expect(screen.getByText("Reviewer: placeholder")).toBeInTheDocument();
  });

  it("has no mock controls when talking to the real backend", () => {
    render(<StatusBar status="idle" reviewerLabel={null} />);
    expect(screen.queryByLabelText(/next mock review/i)).not.toBeInTheDocument();
  });

  it("offers mock controls only in mock mode", async () => {
    const onOutcomeChange = vi.fn();
    render(
      <StatusBar
        status="idle"
        reviewerLabel="Reviewer: mock data"
        mock={{ outcome: "issues", onOutcomeChange }}
      />,
    );
    await userEvent.selectOptions(screen.getByLabelText(/next mock review/i), "error");
    expect(onOutcomeChange).toHaveBeenCalledWith("error");
  });
});

describe("StatusBar model dot", () => {
  it.each([
    ["ok", "AI model: available"],
    ["warn", "AI model: not installed"],
    ["down", "AI model: not reachable"],
  ] as const)("shows a %s dot with its explanation", (level, text) => {
    render(<StatusBar status="idle" reviewerLabel="Reviewer: x" modelStatus={{ level, text }} />);
    const dot = screen.getByRole("img", { name: text });
    expect(dot).toHaveAttribute("data-level", level);
  });

  it("shows no dot when there is nothing to report", () => {
    render(<StatusBar status="idle" reviewerLabel={null} />);
    expect(screen.queryByRole("img")).toBeNull();
  });
});

describe("StatusBar idle", () => {
  it("shows no status text while idle, and still shows the reviewer and the dot", () => {
    render(
      <StatusBar
        status="idle"
        reviewerLabel="Reviewer: m"
        modelStatus={{ level: "ok", text: "AI model: available" }}
      />,
    );
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    expect(screen.queryByText("Ready")).not.toBeInTheDocument();
    expect(screen.getByText("Reviewer: m")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "AI model: available" })).toBeInTheDocument();
  });
});
