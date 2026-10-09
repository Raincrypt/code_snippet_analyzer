import { createRef } from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ChatPanel } from "./ChatPanel";

function setup(props: Partial<Parameters<typeof ChatPanel>[0]> = {}) {
  const onSend = vi.fn();
  render(
    <ChatPanel
      messages={[]}
      thinking={false}
      error={null}
      draft="Why was line 3 flagged?"
      onDraftChange={() => {}}
      onSend={onSend}
      onClear={() => {}}
      sendBlockedReason={null}
      inputRef={createRef<HTMLTextAreaElement>()}
      {...props}
    />,
  );
  return { onSend, send: screen.getByRole("button", { name: "Send message" }) };
}

describe("ChatPanel sending", () => {
  it("sends with the button when allowed", async () => {
    const { onSend, send } = setup();
    expect(send).toBeEnabled();
    await userEvent.click(send);
    expect(onSend).toHaveBeenCalledTimes(1);
  });

  it("sends with Enter when allowed, but not with Shift+Enter", () => {
    const { onSend } = setup();
    const box = screen.getByLabelText("Message");
    fireEvent.keyDown(box, { key: "Enter", shiftKey: true });
    expect(onSend).not.toHaveBeenCalled();
    fireEvent.keyDown(box, { key: "Enter" });
    expect(onSend).toHaveBeenCalledTimes(1);
  });

  it("disables the button and explains why when blocked", () => {
    const { send } = setup({ sendBlockedReason: "Review your code to start chatting." });
    expect(send).toBeDisabled();
    expect(screen.getByRole("status")).toHaveTextContent("Review your code to start chatting.");
  });

  it("does not send with Enter when blocked", () => {
    const { onSend } = setup({ sendBlockedReason: "Blocked." });
    fireEvent.keyDown(screen.getByLabelText("Message"), { key: "Enter" });
    expect(onSend).not.toHaveBeenCalled();
  });

  it("does not send on form submit when blocked", () => {
    const { onSend } = setup({ sendBlockedReason: "Blocked." });
    fireEvent.submit(screen.getByLabelText("Message").closest("form")!);
    expect(onSend).not.toHaveBeenCalled();
  });

  it("still lets the user type a draft while blocked", () => {
    setup({ sendBlockedReason: "Blocked." });
    expect(screen.getByLabelText("Message")).toBeEnabled();
  });

  it("links the textarea to the reason for screen readers", () => {
    setup({ sendBlockedReason: "Blocked." });
    const reason = screen.getByRole("status");
    expect(screen.getByLabelText("Message")).toHaveAttribute("aria-describedby", reason.id);
  });

  it("disables sending for an empty draft or while a reply is pending", () => {
    setup({ draft: "   " });
    expect(screen.getByRole("button", { name: "Send message" })).toBeDisabled();
  });

  it("disables sending while the reviewer is replying", () => {
    setup({ thinking: true });
    expect(screen.getByRole("button", { name: "Send message" })).toBeDisabled();
  });
});
