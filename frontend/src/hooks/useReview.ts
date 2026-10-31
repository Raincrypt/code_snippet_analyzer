import { useCallback, useEffect, useRef, useState } from "react";
import type { ReviewApi, ReviewRequest } from "@/api/types";
import type { ReviewState } from "@/types/review";

export function toMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Something went wrong. Try again.";
}

export function useReview(api: ReviewApi) {
  const [state, setState] = useState<ReviewState>({ status: "idle" });
  // The exact code the current result belongs to; null unless a review has succeeded.
  const [reviewedCode, setReviewedCode] = useState<string | null>(null);
  // The id the backend saved the current result under; needed to chat about it.
  const [reviewId, setReviewId] = useState<string | null>(null);
  const controllerRef = useRef<AbortController | null>(null);

  // Cancel any in-flight request when the component unmounts.
  useEffect(() => () => controllerRef.current?.abort(), []);

  const run = useCallback(
    async (request: ReviewRequest) => {
      controllerRef.current?.abort(); // a newer request supersedes an older one
      const controller = new AbortController();
      controllerRef.current = controller;
      setReviewedCode(null);
      setReviewId(null);
      setState({ status: "loading", stage: null });
      try {
        const { id, result } = await api.review(request, controller.signal, (stage) => {
          if (!controller.signal.aborted) setState({ status: "loading", stage });
        });
        if (!controller.signal.aborted) {
          setReviewedCode(request.code);
          setReviewId(id);
          setState({ status: "success", result });
        }
      } catch (error) {
        if (!controller.signal.aborted) setState({ status: "error", message: toMessage(error) });
      }
    },
    [api],
  );

  return { state, run, reviewedCode, reviewId };
}
