import type { ReviewResult, ReviewStage } from "@/types/review";
import type { ReplyStyle } from "@/types/settings";

export type ReviewRequest = { code: string; language: string };

/** A finished review and the id it was saved under (needed to chat about it). */
export type ReviewResponse = { id: string; result: ReviewResult };

export type AskRequest = { reviewId: string; question: string; replyStyle: ReplyStyle };

/**
 * The only surface the UI uses to talk to a backend.
 * `createHttpApi` talks to the real server; `createMockApi` is for working on the UI alone.
 */
export interface ReviewApi {
  /** `onProgress` is called as each step of the review begins. */
  review(
    request: ReviewRequest,
    signal?: AbortSignal,
    onProgress?: (stage: ReviewStage) => void,
  ): Promise<ReviewResponse>;
  ask(request: AskRequest, signal?: AbortSignal): Promise<string>;
}

export class ApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApiError";
  }
}
