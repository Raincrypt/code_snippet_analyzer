import type { ReviewResult, ReviewStage } from "@/types/review";
import type { ReplyStyle } from "@/types/settings";

export type ReviewRequest = { code: string; language: string };
export type AskRequest = { question: string; replyStyle: ReplyStyle };

/**
 * The only surface the UI uses to talk to a backend.
 * A mock implements it today; an HTTP client will implement it once the API is connected,
 * so no component or hook has to change.
 */
export interface ReviewApi {
  /** `onProgress` is called as each step of the review begins. */
  review(
    request: ReviewRequest,
    signal?: AbortSignal,
    onProgress?: (stage: ReviewStage) => void,
  ): Promise<ReviewResult>;
  ask(request: AskRequest, signal?: AbortSignal): Promise<string>;
}

export class ApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApiError";
  }
}
