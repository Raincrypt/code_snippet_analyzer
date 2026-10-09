import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MOCK_REVIEW } from "@/mocks/review";
import { FindingsTab } from "./FindingsTab";

const { issues, priorityFixes } = MOCK_REVIEW;

function setup(props: Partial<Parameters<typeof FindingsTab>[0]> = {}) {
  const onLocate = vi.fn();
  const onAsk = vi.fn();
  render(
    <FindingsTab
      issues={issues}
      priorityFixes={priorityFixes}
      activeKey={null}
      onLocate={onLocate}
      onAsk={onAsk}
      {...props}
    />,
  );
  return { onLocate, onAsk };
}

const titles = () => screen.getAllByRole("heading", { level: 4 }).map((h) => h.textContent);

describe("FindingsTab", () => {
  it("lists the most severe findings first", () => {
    setup();
    expect(titles()[0]).toBe("topScores reorders the caller's array");
    expect(titles()).toHaveLength(6);
    expect(screen.getByRole("status")).toHaveTextContent("Showing 6 of 6 findings");
  });

  it("opens the priority findings and errors, and keeps the rest closed", () => {
    setup();
    const expanded = (name: RegExp) => screen.getByRole("button", { name });
    expect(expanded(/reorders the caller's array/)).toHaveAttribute("aria-expanded", "true");
    expect(expanded(/Bubble sort does quadratic work/)).toHaveAttribute("aria-expanded", "true");
    expect(expanded(/Prefer let and const/)).toHaveAttribute("aria-expanded", "false");
  });

  it("filters by severity with toggle buttons", async () => {
    setup();
    await userEvent.click(screen.getByRole("button", { name: /Warning 3/ }));
    expect(titles()).toHaveLength(3);
    expect(screen.getByRole("status")).toHaveTextContent("Showing 3 of 6 findings");
    await userEvent.click(screen.getByRole("button", { name: /Warning 3/ }));
    expect(titles()).toHaveLength(6);
  });

  it("filters by category", async () => {
    setup();
    await userEvent.selectOptions(screen.getByLabelText("Category"), "performance");
    expect(titles()).toEqual([
      "Bubble sort does quadratic work",
      "Duplicate check compares every pair",
    ]);
  });

  it("sorts by line number", async () => {
    setup();
    await userEvent.selectOptions(screen.getByLabelText("Sort"), "line");
    expect(titles()[0]).toBe("Inputs are not validated"); // line 2
  });

  it("explains an empty result and lets the user clear the filters", async () => {
    setup();
    await userEvent.click(screen.getByRole("button", { name: /Info 1/ }));
    await userEvent.selectOptions(screen.getByLabelText("Category"), "bug");
    expect(screen.getByText("No findings match these filters")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Clear filters" }));
    expect(titles()).toHaveLength(6);
  });

  it("expands and collapses everything", async () => {
    setup();
    await userEvent.click(screen.getByRole("button", { name: "Expand all" }));
    expect(screen.getByRole("button", { name: /Prefer let and const/ })).toHaveAttribute(
      "aria-expanded",
      "true",
    );
    await userEvent.click(screen.getByRole("button", { name: "Collapse all" }));
    expect(screen.getByRole("button", { name: /reorders the caller's array/ })).toHaveAttribute(
      "aria-expanded",
      "false",
    );
  });

  it("opens a finding that the editor selects", () => {
    const { rerender } = render(
      <FindingsTab
        issues={issues}
        priorityFixes={priorityFixes}
        activeKey={null}
        onLocate={() => {}}
        onAsk={() => {}}
      />,
    );
    const button = screen.getByRole("button", { name: /Prefer let and const/ });
    expect(button).toHaveAttribute("aria-expanded", "false");
    rerender(
      <FindingsTab
        issues={issues}
        priorityFixes={priorityFixes}
        activeKey="f5"
        onLocate={() => {}}
        onAsk={() => {}}
      />,
    );
    expect(screen.getByRole("button", { name: /Prefer let and const/ })).toHaveAttribute(
      "aria-expanded",
      "true",
    );
  });

  it("groups low-confidence findings separately", () => {
    const unsure = issues.map((i) => (i.id === "f6" ? { ...i, confidence: "low" as const } : i));
    setup({ issues: unsure });
    const group = screen.getByRole("region", { name: "Worth double-checking" });
    expect(within(group).getByRole("heading", { level: 4 })).toHaveTextContent(
      "Inputs are not validated",
    );
  });

  it("says so when there are no findings at all", () => {
    setup({ issues: [], priorityFixes: [] });
    expect(screen.getByText("No issues found")).toBeInTheDocument();
  });
});
