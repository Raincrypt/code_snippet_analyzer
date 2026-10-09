import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { EditorView } from "@codemirror/view";
import type { ReviewApi } from "@/api/types";
import { MOCK_REVIEW, SAMPLE_CODE } from "@/mocks/review";
import type { ReviewResult } from "@/types/review";
import App from "./App";

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((r) => (resolve = r));
  return { promise, resolve };
}

function setup() {
  const pending = deferred<ReviewResult>();
  const api: ReviewApi = {
    review: vi.fn(() => pending.promise),
    ask: vi.fn(() => Promise.resolve("A reply")),
  };
  render(<App api={api} />);
  const editorSection = screen.getByRole("region", { name: "Code editor" });
  return {
    api,
    pending,
    reviewButton: () => within(editorSection).getByRole("button", { name: /^review/i }),
    sendButton: () => screen.getByRole("button", { name: "Send message" }),
    typeQuestion: () => userEvent.type(screen.getByLabelText("Message"), "Why?"),
    editorContent: () => screen.getByRole("textbox", { name: "Code to review" }),
  };
}

/** Change the editor text the way typing would, by dispatching to the CodeMirror view. */
function editCode(changes: { from: number; to?: number; insert?: string }) {
  const dom = document.querySelector<HTMLElement>(".cm-editor");
  const view = EditorView.findFromDOM(dom!)!;
  act(() => view.dispatch({ changes }));
}

/** Gutter dots for real findings. CodeMirror also keeps one hidden spacer dot to reserve width. */
const realDots = () =>
  [...document.querySelectorAll<HTMLElement>(".cm-issue-dot")].filter(
    (dot) => dot.parentElement?.style.visibility !== "hidden",
  );

beforeEach(() => localStorage.clear());

describe("review and chat flow", () => {
  it("keeps chat disabled until a review has finished", async () => {
    const { sendButton, typeQuestion } = setup();
    await typeQuestion();
    expect(sendButton()).toBeDisabled();
    expect(screen.getAllByText(/review your code to start chatting/i).length).toBeGreaterThan(0);
  });

  it("disables the Review button while reviewing, including the keyboard shortcut", async () => {
    const { api, reviewButton, editorContent } = setup();
    await userEvent.click(reviewButton());

    expect(reviewButton()).toBeDisabled();
    fireEvent.keyDown(editorContent(), { key: "Enter", ctrlKey: true });
    fireEvent.keyDown(editorContent(), { key: "Enter", ctrlKey: true });
    expect(api.review).toHaveBeenCalledTimes(1);
    expect(screen.getAllByText(/chat opens when it finishes/i).length).toBeGreaterThan(0);
  });

  it("re-enables Review and opens chat when the review finishes", async () => {
    const { pending, reviewButton, sendButton, typeQuestion } = setup();
    await typeQuestion();
    await userEvent.click(reviewButton());
    expect(sendButton()).toBeDisabled();

    await act(async () => pending.resolve(MOCK_REVIEW));

    await waitFor(() => expect(sendButton()).toBeEnabled());
    expect(reviewButton()).toBeEnabled();
  });

  it("disables sending when the reviewed code is edited and restores it when reverted", async () => {
    const { pending, reviewButton, sendButton, typeQuestion } = setup();
    await userEvent.click(reviewButton());
    await act(async () => pending.resolve(MOCK_REVIEW));
    await typeQuestion();
    await waitFor(() => expect(sendButton()).toBeEnabled());

    editCode({ from: 0, insert: "x" });
    await waitFor(() => expect(sendButton()).toBeDisabled());
    expect(screen.getAllByText(/code changed since the review/i).length).toBeGreaterThan(0);

    editCode({ from: 0, to: 1, insert: "" }); // undo the edit
    await waitFor(() => expect(sendButton()).toBeEnabled());
  });

  it("sends the question once chat is open", async () => {
    const { api, pending, reviewButton, sendButton, typeQuestion } = setup();
    await userEvent.click(reviewButton());
    await act(async () => pending.resolve(MOCK_REVIEW));
    await typeQuestion();

    await userEvent.click(sendButton());

    expect(api.ask).toHaveBeenCalledWith(
      { question: "Why?", replyStyle: "brief" },
      expect.any(AbortSignal),
    );
    expect(await screen.findByText("A reply")).toBeInTheDocument();
  });

  it("starts with the sample code loaded", () => {
    const { editorContent } = setup();
    expect(editorContent()).toHaveTextContent(SAMPLE_CODE.split("\n")[0]!);
  });

  it("marks flagged lines after a review, and hides the marks once the code is edited", async () => {
    const { pending, reviewButton } = setup();
    await userEvent.click(reviewButton());
    await act(async () => pending.resolve(MOCK_REVIEW));
    await waitFor(() => expect(realDots().length).toBeGreaterThan(0));
    expect(screen.queryByText("Out of date")).not.toBeInTheDocument();

    editCode({ from: 0, insert: "x" });

    await waitFor(() => expect(realDots()).toHaveLength(0));
    expect(screen.getByText("Out of date")).toBeInTheDocument();

    editCode({ from: 0, to: 1, insert: "" });
    await waitFor(() => expect(realDots().length).toBeGreaterThan(0));
    expect(screen.queryByText("Out of date")).not.toBeInTheDocument();
  });
});
