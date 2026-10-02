import { useCallback, useEffect, useRef, useState } from "react";
import type { ReviewApi } from "@/api/types";
import type { ChatMessage } from "@/types/review";
import type { ReplyStyle } from "@/types/settings";
import { toMessage } from "./useReview";

export function useChat(api: ReviewApi, replyStyle: ReplyStyle) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [thinking, setThinking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const controllerRef = useRef<AbortController | null>(null);

  useEffect(() => () => controllerRef.current?.abort(), []);

  const send = useCallback(async () => {
    const text = draft.trim();
    if (!text || thinking) return;

    const controller = new AbortController();
    controllerRef.current = controller;
    setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: "user", content: text }]);
    setDraft("");
    setError(null);
    setThinking(true);
    try {
      const reply = await api.ask({ question: text, replyStyle }, controller.signal);
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
  }, [api, draft, replyStyle, thinking]);

  const clear = useCallback(() => {
    controllerRef.current?.abort();
    setMessages([]);
    setError(null);
    setThinking(false);
  }, []);

  return { messages, draft, setDraft, thinking, error, send, clear };
}
