import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MOCK_REVIEW } from "@/mocks/review";
import type { CodeIssue } from "@/types/review";
import { FindingCard } from "./FindingCard";

const issue = (id: string) => MOCK_REVIEW.issues.find((i) => i.id === id)!;

function setup(overrides: Partial<Parameters<typeof FindingCard>[0]> = {}) {
  const handlers = { onToggle: vi.fn(), onLocate: vi.fn(), onAsk: vi.fn() };
  const props = { issue: issue("f3"), open: true, ...handlers, ...overrides };
  render(<FindingCard {...props} />);
  return handlers;
}

describe("FindingCard", () => {
  it("shows the headline while collapsed, and hides the details", () => {
    setup({ open: false });
    expect(screen.getByRole("heading", { name: "Bubble sort does quadratic work" })).toBeVisible();
    expect(screen.queryByText("What's wrong")).not.toBeVisible();
  });

  it("shows what is wrong, why it matters, the code and the fix when open", () => {
    setup();
    expect(screen.getByText("What's wrong")).toBeVisible();
    expect(screen.getByText("Why it matters")).toBeVisible();
    expect(screen.getByLabelText("The code")).toHaveTextContent("for (var i = 0");
    expect(screen.getByLabelText("Before")).toBeInTheDocument();
    expect(screen.getByLabelText("After")).toHaveTextContent("[...scores].sort");
  });

  it("numbers the quoted code from the cited line", () => {
    setup();
    const code = screen.getByLabelText("The code");
    expect(code).toHaveTextContent("4");
    expect(code).toHaveTextContent("5");
  });

  it("shows confidence and effort", () => {
    setup();
    expect(screen.getByText("High confidence")).toBeInTheDocument();
    expect(screen.getByText("Quick fix")).toBeInTheDocument();
  });

  it("links references safely in a new tab", () => {
    setup();
    const link = screen.getByRole("link", { name: /MDN: Array\.prototype\.sort/ });
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", expect.stringContaining("noopener"));
  });

  it("omits the fix section when there is no fix", () => {
    const noFix: CodeIssue = { ...issue("f3"), fix: null, references: [] };
    setup({ issue: noFix });
    expect(screen.queryByText("Suggested fix")).not.toBeInTheDocument();
    expect(screen.queryByText("Learn more")).not.toBeInTheDocument();
  });

  it("toggles from the title", async () => {
    const { onToggle } = setup({ open: false });
    await userEvent.click(screen.getByRole("button", { name: /Bubble sort does quadratic work/ }));
    expect(onToggle).toHaveBeenCalledTimes(1);
  });

  it("exposes expanded state to assistive tech", () => {
    setup({ open: false });
    expect(screen.getByRole("button", { name: /Bubble sort/ })).toHaveAttribute(
      "aria-expanded",
      "false",
    );
  });

  it("asks the editor to show the finding's lines", async () => {
    const { onLocate } = setup();
    await userEvent.click(screen.getByRole("button", { name: "Lines 4–12" }));
    expect(onLocate).toHaveBeenCalledWith(issue("f3"));
  });

  it("starts a question about the finding", async () => {
    const { onAsk } = setup();
    await userEvent.click(screen.getByRole("button", { name: /ask about this/i }));
    expect(onAsk).toHaveBeenCalledWith(issue("f3"));
  });

  it("marks the selected finding", () => {
    const { container } = render(
      <FindingCard
        issue={issue("f1")}
        open
        onToggle={() => {}}
        onLocate={() => {}}
        onAsk={() => {}}
        active
      />,
    );
    expect(container.querySelector("article")).toHaveAttribute("aria-current", "true");
  });
});
