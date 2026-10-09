import { RichText } from "@/components/RichText";
import type { ChatMessage as Message } from "@/types/review";

export function ChatMessage({ message }: { message: Message }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <p
        className={`max-w-[85%] rounded-lg px-3.5 py-2.5 text-sm leading-relaxed whitespace-pre-wrap ${
          isUser ? "bg-chalk text-chalk-ink" : "border border-ink-700 bg-ink-900 text-fg"
        }`}
      >
        <span className="sr-only">{isUser ? "You: " : "Reviewer: "}</span>
        {isUser ? message.content : <RichText>{message.content}</RichText>}
      </p>
    </div>
  );
}
