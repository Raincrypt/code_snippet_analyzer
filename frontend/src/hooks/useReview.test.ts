import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReviewApi } from "@/api/types";
import { MOCK_REVIEW } from "@/mocks/review";
import { useReview } from "./useReview";

const request = { code: "x = 1", language: "python" };

function fakeApi(overrides: Partial<ReviewApi> = {}): ReviewApi {
  return {
    review: () => Promise.resolve(MOCK_REVIEW),
    ask: () => Promise.resolve("ok"),
    ...overrides,
  };
}

describe("useReview", () => {
  it("starts idle", () => {
    const { result } = renderHook(() => useReview(fakeApi()));
    expect(result.current.state.status).toBe("idle");
  });

  it("moves to success with the result", async () => {
    const { result } = renderHook(() => useReview(fakeApi()));
    await act(() => result.current.run(request));
    expect(result.current.state).toEqual({ status: "success", result: MOCK_REVIEW });
  });

  it("moves to error with the failure message", async () => {
    const api = fakeApi({ review: () => Promise.reject(new Error("boom")) });
    const { result } = renderHook(() => useReview(api));
    await act(() => result.current.run(request));
    expect(result.current.state).toEqual({ status: "error", message: "boom" });
  });

  it("is loading while the request is pending", async () => {
    const api = fakeApi({ review: () => new Promise(() => {}) });
    const { result } = renderHook(() => useReview(api));
    act(() => void result.current.run(request));
    await waitFor(() => expect(result.current.state.status).toBe("loading"));
  });

  it("remembers the code that was reviewed", async () => {
    const { result } = renderHook(() => useReview(fakeApi()));
    expect(result.current.reviewedCode).toBeNull();
    await act(() => result.current.run(request));
    expect(result.current.reviewedCode).toBe(request.code);
  });

  it("forgets the reviewed code while a new review runs", async () => {
    const { result } = renderHook(() => useReview(fakeApi()));
    await act(() => result.current.run(request));
    const pending = fakeApi({ review: () => new Promise(() => {}) });
    const second = renderHook(() => useReview(pending));
    act(() => void second.result.current.run(request));
    await waitFor(() => expect(second.result.current.reviewedCode).toBeNull());
  });

  it("has no reviewed code after a failed review", async () => {
    const api = fakeApi({ review: () => Promise.reject(new Error("boom")) });
    const { result } = renderHook(() => useReview(api));
    await act(() => result.current.run(request));
    expect(result.current.reviewedCode).toBeNull();
  });

  it("reports each step while the review runs", async () => {
    let finish!: () => void;
    const api = fakeApi({
      review: (_request, _signal, onProgress) =>
        new Promise((resolve) => {
          onProgress?.("prepare");
          onProgress?.("analyse");
          finish = () => resolve(MOCK_REVIEW);
        }),
    });
    const { result } = renderHook(() => useReview(api));
    act(() => void result.current.run(request));
    await waitFor(() =>
      expect(result.current.state).toEqual({ status: "loading", stage: "analyse" }),
    );
    await act(async () => finish());
    expect(result.current.state.status).toBe("success");
  });
});
