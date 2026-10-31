import { renderHook, waitFor } from "@testing-library/react";
import { useBackendLabel } from "./useBackendLabel";

describe("useBackendLabel", () => {
  it("does nothing when there is no backend to ask", () => {
    const { result } = renderHook(() => useBackendLabel(null));
    expect(result.current).toBeNull();
  });

  it("says plainly when the placeholder reviewer is in use", async () => {
    const health = () => Promise.resolve({ reviewer: "stub" });
    const { result } = renderHook(() => useBackendLabel(health));
    await waitFor(() =>
      expect(result.current).toBe("Reviewer: placeholder (no AI model connected)"),
    );
  });

  it("names any other reviewer", async () => {
    const health = () => Promise.resolve({ reviewer: "qwen-local" });
    const { result } = renderHook(() => useBackendLabel(health));
    await waitFor(() => expect(result.current).toBe("Reviewer: qwen-local"));
  });

  it("shows the model's name when the backend reports one", async () => {
    const health = () => Promise.resolve({ reviewer: "llm", model: "qwen2.5-coder:7b" });
    const { result } = renderHook(() => useBackendLabel(health));
    await waitFor(() => expect(result.current).toBe("Reviewer: qwen2.5-coder:7b"));
  });

  it("says when the backend cannot be reached", async () => {
    const health = () => Promise.reject(new Error("down"));
    const { result } = renderHook(() => useBackendLabel(health));
    await waitFor(() => expect(result.current).toBe("Backend not reachable"));
  });
});
