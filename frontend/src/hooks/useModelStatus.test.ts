import { act, renderHook, waitFor } from "@testing-library/react";
import { POLL_MS, useModelStatus } from "./useModelStatus";

type State = "ready" | "model-missing" | "unreachable";
const answer =
  (state: State, detail = "x") =>
  () =>
    Promise.resolve({ state, detail });

describe("useModelStatus", () => {
  it("does nothing when there is no backend to ask", () => {
    const { result } = renderHook(() => useModelStatus(null));
    expect(result.current).toBeNull();
  });

  it("starts as checking (yellow) and turns green when the model is ready", async () => {
    const { result } = renderHook(() => useModelStatus(answer("ready")));
    expect(result.current?.level).toBe("checking");
    await waitFor(() =>
      expect(result.current).toEqual({ level: "ok", text: "AI model: available" }),
    );
  });

  it("is yellow, with the reason, when the model is not installed", async () => {
    const fetcher = answer("model-missing", "The model is not installed on the server.");
    const { result } = renderHook(() => useModelStatus(fetcher));
    await waitFor(() => expect(result.current?.level).toBe("warn"));
    expect(result.current?.text).toContain("not installed");
  });

  it("is red when the model server is down", async () => {
    const { result } = renderHook(() => useModelStatus(answer("unreachable")));
    await waitFor(() => expect(result.current?.level).toBe("down"));
  });

  it("is red when the backend does not answer", async () => {
    const { result } = renderHook(() => useModelStatus(() => Promise.reject(new Error("down"))));
    await waitFor(() => expect(result.current?.level).toBe("down"));
    expect(result.current?.text).toContain("backend");
  });

  it("checks again later and follows the change", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    try {
      let state: State = "unreachable";
      const fetcher = () => Promise.resolve({ state, detail: "x" });
      const { result } = renderHook(() => useModelStatus(fetcher));
      await waitFor(() => expect(result.current?.level).toBe("down"));
      state = "ready";
      await act(async () => {
        await vi.advanceTimersByTimeAsync(POLL_MS + 10);
      });
      await waitFor(() => expect(result.current?.level).toBe("ok"));
    } finally {
      vi.useRealTimers();
    }
  });
});
