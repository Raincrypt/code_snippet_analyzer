import type { ReviewResult } from "@/types/review";
import type { ReplyStyle } from "@/types/settings";

export type ReviewRequest = { code: string; language: string };
export type AskRequest = { question: string; replyStyle: ReplyStyle };

/**
 * The only surface the UI uses to talk to a backend.
 * A mock implements it today; an HTTP client will implement it once the API exists,
 * so no component or hook has to change.
 */
export interface ReviewApi {
  review(request: ReviewRequest, signal?: AbortSignal): Promise<ReviewResult>;
  ask(request: AskRequest, signal?: AbortSignal): Promise<string>;
}

export class ApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApiError";
  }
}
