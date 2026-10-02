import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AnnotationCard } from "./AnnotationCard";
import type { CodeIssue } from "@/types/review";

const issue: CodeIssue = {
  line: 3,
  severity: "error",
  category: "security",
  title: "SQL injection",
  description: "User input reaches the query.",
  suggestion: "db.query(sql, [id])",
};

describe("AnnotationCard", () => {
  it("shows the title, line and severity", () => {
    render(<AnnotationCard issue={issue} onAsk={() => {}} onLocate={() => {}} />);
    expect(screen.getByText("SQL injection")).toBeInTheDocument();
    expect(screen.getByText("Line 3")).toBeInTheDocument();
    expect(screen.getByText("Error")).toBeInTheDocument();
  });

  it("reveals the fix when asked", async () => {
    render(<AnnotationCard issue={issue} onAsk={() => {}} onLocate={() => {}} />);
    expect(screen.queryByText("db.query(sql, [id])")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /show fix/i }));
    expect(screen.getByText("db.query(sql, [id])")).toBeInTheDocument();
  });

  it("reports which issue the user wants to ask about", async () => {
    const onAsk = vi.fn();
    render(<AnnotationCard issue={issue} onAsk={onAsk} onLocate={() => {}} />);
    await userEvent.click(screen.getByRole("button", { name: /ask about this/i }));
    expect(onAsk).toHaveBeenCalledWith(issue);
  });

  it("asks the editor to show the finding's lines", async () => {
    const onLocate = vi.fn();
    render(<AnnotationCard issue={issue} onAsk={() => {}} onLocate={onLocate} />);
    await userEvent.click(screen.getByRole("button", { name: "Line 3" }));
    expect(onLocate).toHaveBeenCalledWith(issue);
  });

  it("marks the selected finding", () => {
    const { container } = render(
      <AnnotationCard issue={issue} onAsk={() => {}} onLocate={() => {}} active />,
    );
    expect(container.querySelector("article")).toHaveAttribute("aria-current", "true");
  });
});
