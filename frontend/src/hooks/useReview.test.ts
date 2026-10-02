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
});
