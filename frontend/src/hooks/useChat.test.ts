import { act, renderHook } from "@testing-library/react";
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
    const { result } = renderHook(() => useChat(api(ask), "balanced"));
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
    const { result } = renderHook(() => useChat(api(ask), "detailed"));
    act(() => result.current.setDraft("Why?"));
    await act(() => result.current.send());
    expect(ask).toHaveBeenCalledWith(
      { question: "Why?", replyStyle: "detailed" },
      expect.any(AbortSignal),
    );
  });
});
