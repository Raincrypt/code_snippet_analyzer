import { MOCK_REPLIES, MOCK_REVIEW } from "@/mocks/review";
import { ReviewResultSchema } from "@/types/review";
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

export function createMockApi({ outcome, latencyMs = 1200 }: MockOptions): ReviewApi {
  return {
    async review(_request, signal) {
      await delay(latencyMs, signal);
      if (outcome === "error") {
        throw new ApiError(
          "The reviewer took too long to respond. Your code is unchanged. Try again.",
        );
      }
      // Validate like a real response would be validated.
      return ReviewResultSchema.parse(
        outcome === "clean"
          ? {
              summary: "Nothing to flag. The code is clear and handles its edge cases.",
              score: 9,
              issues: [],
              positives: [],
            }
          : MOCK_REVIEW,
      );
    },
    async ask({ replyStyle }, signal) {
      await delay(latencyMs * 0.8, signal);
      return MOCK_REPLIES[replyStyle];
    },
  };
}
