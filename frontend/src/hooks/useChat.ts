import { useCallback, useEffect, useRef, useState } from "react";
import type { ReviewApi } from "@/api/types";
import type { ChatMessage } from "@/types/review";
import type { ReplyStyle } from "@/types/settings";
import { toMessage } from "./useReview";

/**
 * Chat about one saved review. `reviewId` is null until a review has finished. When a different
 * review arrives, the conversation starts over, because the old messages were about other code.
 */
export function useChat(api: ReviewApi, replyStyle: ReplyStyle, reviewId: string | null) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [thinking, setThinking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const controllerRef = useRef<AbortController | null>(null);

  // The review the current messages belong to. It only changes when a new review has finished,
  // so a review that is still running (reviewId is null) leaves the conversation alone.
  const [owner, setOwner] = useState(reviewId);
  if (reviewId !== null && reviewId !== owner) {
    setOwner(reviewId);
    setMessages([]);
    setError(null);
    setThinking(false);
  }

  // Stop waiting for a reply that belongs to a previous review (or to an unmounted chat).
  useEffect(() => () => controllerRef.current?.abort(), [owner]);

  const send = useCallback(async () => {
    const text = draft.trim();
    if (!text || thinking || !reviewId) return;

    const controller = new AbortController();
    controllerRef.current = controller;
    setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: "user", content: text }]);
    setDraft("");
    setError(null);
    setThinking(true);
    try {
      const reply = await api.ask({ reviewId, question: text, replyStyle }, controller.signal);
      if (controller.signal.aborted) return;
      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), role: "assistant", content: reply },
      ]);
    } catch (e) {
      if (!controller.signal.aborted) setError(toMessage(e));
    } finally {
      if (!controller.signal.aborted) setThinking(false);
    }
  }, [api, draft, replyStyle, reviewId, thinking]);

  const clear = useCallback(() => {
    controllerRef.current?.abort();
    setMessages([]);
    setError(null);
    setThinking(false);
  }, []);

  return { messages, draft, setDraft, thinking, error, send, clear };
}
