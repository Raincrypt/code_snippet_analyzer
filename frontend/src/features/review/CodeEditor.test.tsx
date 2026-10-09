import { createRef } from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CodeEditor, type CodeEditorHandle } from "./CodeEditor";

function setup(props: Partial<Parameters<typeof CodeEditor>[0]> = {}) {
  const handlers = {
    onCodeChange: vi.fn(),
    onLanguageChange: vi.fn(),
    onReview: vi.fn(),
  };
  const utils = render(
    <CodeEditor
      code={"const a = 1;\nconst b = 2;\nconst c = 3;"}
      language="javascript"
      loading={false}
      issues={[]}
      fontSize="medium"
      {...handlers}
      {...props}
    />,
  );
  return { ...utils, ...handlers };
}

describe("CodeEditor", () => {
  it("shows the code in an accessible editor", () => {
    setup();
    const editor = screen.getByRole("textbox", { name: "Code to review" });
    expect(editor).toHaveTextContent("const a = 1;");
    expect(editor).toHaveTextContent("const c = 3;");
  });

  it("shows line and character counts", () => {
    setup();
    expect(screen.getByText(/3 lines/)).toBeInTheDocument();
  });

  it("runs a review from the button", async () => {
    const { onReview } = setup();
    await userEvent.click(screen.getByRole("button", { name: "Review" }));
    expect(onReview).toHaveBeenCalledTimes(1);
  });

  it("runs a review with Ctrl+Enter inside the editor", () => {
    const { onReview } = setup();
    fireEvent.keyDown(screen.getByRole("textbox", { name: "Code to review" }), {
      key: "Enter",
      ctrlKey: true,
    });
    expect(onReview).toHaveBeenCalledTimes(1);
  });

  it("disables Review when the editor is empty", () => {
    setup({ code: "   " });
    expect(screen.getByRole("button", { name: "Review" })).toBeDisabled();
  });

  it("reports a language change", async () => {
    const { onLanguageChange } = setup();
    await userEvent.selectOptions(screen.getByLabelText("Language"), "python");
    expect(onLanguageChange).toHaveBeenCalledWith("python");
  });

  it("marks lines that have findings", () => {
    const { container } = setup({ issues: [{ line: 2, severity: "error" }] });
    expect(container.querySelectorAll(".cm-issue-line-error")).toHaveLength(1);
    const realDots = [...container.querySelectorAll<HTMLElement>(".cm-issue-dot-error")].filter(
      (dot) => dot.parentElement?.style.visibility !== "hidden",
    );
    expect(realDots).toHaveLength(1);
  });

  it("exposes revealLines without throwing", () => {
    const ref = createRef<CodeEditorHandle>();
    setup({ ref });
    expect(() => ref.current?.revealLines(2, 3)).not.toThrow();
  });
});
