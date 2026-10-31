import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReviewApi } from "@/api/types";
import { useChat } from "./useChat";

const api = (ask: ReviewApi["ask"]): ReviewApi => ({
  review: () => Promise.reject(new Error("unused")),
  ask,
});

describe("useChat", () => {
  it("appends the user message and the reply, and clears the draft", async () => {
    const { result } = renderHook(() =>
      useChat(
        api(() => Promise.resolve("Use a parameterized query.")),
        "balanced",
        "r1",
      ),
    );
    act(() => result.current.setDraft("How do I fix line 3?"));
    await act(() => result.current.send());
    expect(result.current.messages.map((m) => [m.role, m.content])).toEqual([
      ["user", "How do I fix line 3?"],
      ["assistant", "Use a parameterized query."],
    ]);
    expect(result.current.draft).toBe("");
  });

  it("ignores blank drafts", async () => {
    const ask = vi.fn();
    const { result } = renderHook(() => useChat(api(ask), "balanced", "r1"));
    act(() => result.current.setDraft("   "));
    await act(() => result.current.send());
    expect(ask).not.toHaveBeenCalled();
    expect(result.current.messages).toHaveLength(0);
  });

  it("exposes an error and keeps the user message when the reply fails", async () => {
    const { result } = renderHook(() =>
      useChat(
        api(() => Promise.reject(new Error("offline"))),
        "balanced",
        "r1",
      ),
    );
    act(() => result.current.setDraft("Hello"));
    await act(() => result.current.send());
    expect(result.current.error).toBe("offline");
    expect(result.current.messages).toHaveLength(1);
    expect(result.current.thinking).toBe(false);
  });
});

describe("useChat reply style", () => {
  it("sends the chosen reply style with the question", async () => {
    const ask = vi.fn().mockResolvedValue("ok");
    const { result } = renderHook(() => useChat(api(ask), "detailed", "r1"));
    act(() => result.current.setDraft("Why?"));
    await act(() => result.current.send());
    expect(ask).toHaveBeenCalledWith(
      { reviewId: "r1", question: "Why?", replyStyle: "detailed" },
      expect.any(AbortSignal),
    );
  });
});

describe("useChat and the saved review", () => {
  it("tells the backend which review the question is about", async () => {
    const ask = vi.fn().mockResolvedValue("ok");
    const { result } = renderHook(() => useChat(api(ask), "brief", "review-42"));
    act(() => result.current.setDraft("Why?"));
    await act(() => result.current.send());
    expect(ask).toHaveBeenCalledWith(
      { reviewId: "review-42", question: "Why?", replyStyle: "brief" },
      expect.any(AbortSignal),
    );
  });

  it("does not send before a review has been saved", async () => {
    const ask = vi.fn();
    const { result } = renderHook(() => useChat(api(ask), "brief", null));
    act(() => result.current.setDraft("Why?"));
    await act(() => result.current.send());
    expect(ask).not.toHaveBeenCalled();
    expect(result.current.messages).toHaveLength(0);
  });

  it("starts a fresh conversation when a different review arrives", async () => {
    const ask = vi.fn().mockResolvedValue("ok");
    const { result, rerender } = renderHook(({ id }) => useChat(api(ask), "brief", id), {
      initialProps: { id: "a" as string | null },
    });
    act(() => result.current.setDraft("First question"));
    await act(() => result.current.send());
    expect(result.current.messages).toHaveLength(2);

    rerender({ id: "b" });
    expect(result.current.messages).toHaveLength(0);
  });

  it("keeps the conversation while the next review is still running", async () => {
    const ask = vi.fn().mockResolvedValue("ok");
    const { result, rerender } = renderHook(({ id }) => useChat(api(ask), "brief", id), {
      initialProps: { id: "a" as string | null },
    });
    act(() => result.current.setDraft("First question"));
    await act(() => result.current.send());

    rerender({ id: null }); // a new review has started but not finished
    expect(result.current.messages).toHaveLength(2);
    rerender({ id: "a" }); // it ended up being the same review
    expect(result.current.messages).toHaveLength(2);
  });

  it("drops a reply that was still pending when a different review arrived", async () => {
    let answer!: (value: string) => void;
    const ask = vi.fn(() => new Promise<string>((resolve) => (answer = resolve)));
    const { result, rerender } = renderHook(({ id }) => useChat(api(ask), "brief", id), {
      initialProps: { id: "a" as string | null },
    });
    act(() => result.current.setDraft("Slow question"));
    act(() => void result.current.send());
    await waitFor(() => expect(result.current.thinking).toBe(true));

    rerender({ id: "b" });
    await act(async () => answer("late reply"));

    expect(result.current.messages).toHaveLength(0);
    expect(result.current.thinking).toBe(false);
  });
});
