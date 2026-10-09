import { CLEAN_REVIEW, MOCK_REPLIES, MOCK_REVIEW } from "@/mocks/review";
import { REVIEW_STAGES } from "@/types/review";
import { ApiError, type ReviewApi } from "./types";

export type MockOutcome = "issues" | "clean" | "error";

type MockOptions = { outcome: MockOutcome; latencyMs?: number };

function delay(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) return reject(signal.reason);
    const id = setTimeout(resolve, ms);
    signal?.addEventListener(
      "abort",
      () => {
        clearTimeout(id);
        reject(signal.reason);
      },
      { once: true },
    );
  });
}

export function createMockApi({ outcome, latencyMs = 1500 }: MockOptions): ReviewApi {
  return {
    async review(_request, signal, onProgress) {
      // The real backend will report these steps as it completes them.
      const stepMs = latencyMs / REVIEW_STAGES.length;
      for (const stage of REVIEW_STAGES) {
        onProgress?.(stage);
        await delay(stepMs, signal);
        if (outcome === "error" && stage === "analyse") {
          throw new ApiError(
            "The reviewer took too long to respond. Your code is unchanged. Try again.",
          );
        }
      }
      return outcome === "clean" ? CLEAN_REVIEW : MOCK_REVIEW;
    },
    async ask({ replyStyle }, signal) {
      await delay(latencyMs * 0.6, signal);
      return MOCK_REPLIES[replyStyle];
    },
  };
}
