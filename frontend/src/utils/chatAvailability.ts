import type { ReviewState } from "@/types/review";

/**
 * Why the chat cannot send right now, or null when it can.
 *
 * Chat is only allowed while the editor holds exactly the code that was reviewed:
 * edit it and sending stops; undo the edit and sending works again.
 */
export function chatBlockedReason(
  status: ReviewState["status"],
  reviewedCode: string | null,
  code: string,
): string | null {
  switch (status) {
    case "idle":
      return "Review your code to start chatting.";
    case "loading":
      return "Reviewing your code… chat opens when it finishes.";
    case "error":
      return "The review didn’t finish. Review again to chat.";
    case "success":
      return reviewedCode === code
        ? null
        : "The code changed since the review. Review it again, or undo your edits, to keep chatting.";
  }
}
