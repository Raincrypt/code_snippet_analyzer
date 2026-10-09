import { useEffect, useId, useRef, type Ref } from "react";
import { SendHorizontal, Trash2 } from "lucide-react";
import type { ChatMessage as Message } from "@/types/review";
import { Button } from "@/components/ui/Button";
import { ChatMessage } from "./ChatMessage";

type ChatPanelProps = {
  messages: Message[];
  thinking: boolean;
  error: string | null;
  draft: string;
  onDraftChange: (value: string) => void;
  onSend: () => void;
  onClear: () => void;
  /** Why sending is not allowed right now, or null when it is. Shown under the messages. */
  sendBlockedReason: string | null;
  inputRef: Ref<HTMLTextAreaElement>;
};

export function ChatPanel({
  messages,
  thinking,
  error,
  draft,
  onDraftChange,
  onSend,
  onClear,
  sendBlockedReason,
  inputRef,
}: ChatPanelProps) {
  const endRef = useRef<HTMLDivElement>(null);
  const reasonId = useId();

  // Every way of sending (button, Enter key, form submit) goes through this one check.
  const canSend = !sendBlockedReason && !thinking && draft.trim().length > 0;
  function trySend() {
    if (canSend) onSend();
  }

  // Keep the newest message in view.
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, thinking]);

  return (
    <section aria-label="Chat about your review" className="flex min-h-0 flex-1 flex-col">
      <div className="flex items-center justify-between border-b border-ink-700 px-4 py-2.5">
        <h2 className="text-sm font-semibold">Ask the reviewer</h2>
        <Button
          variant="ghost"
          className="h-8 px-2"
          onClick={onClear}
          disabled={messages.length === 0}
          icon={<Trash2 className="size-4" aria-hidden />}
        >
          Clear
        </Button>
      </div>

      <div role="log" aria-live="polite" className="min-h-0 flex-1 space-y-3 overflow-y-auto p-4">
        {messages.length === 0 && (
          <p className="mx-auto max-w-xs py-10 text-center text-sm leading-relaxed text-fg-muted">
            Ask why something was flagged, or use “Ask about this” on any finding.
          </p>
        )}
        {messages.map((m) => (
          <ChatMessage key={m.id} message={m} />
        ))}
        {thinking && (
          <div className="flex gap-1 px-1 py-2" role="status" aria-label="Reviewer is typing">
            {[0, 150, 300].map((d) => (
              <span
                key={d}
                className="size-1.5 rounded-full bg-fg-muted motion-safe:animate-pulse"
                style={{ animationDelay: `${d}ms` }}
              />
            ))}
          </div>
        )}
        {error && (
          <p
            role="alert"
            className="rounded-md border border-sev-error/40 bg-sev-error/10 px-3 py-2 text-sm text-fg"
          >
            {error}
          </p>
        )}
        <div ref={endRef} />
      </div>

      <div className="border-t border-ink-700">
        {/* Always rendered so screen readers announce changes; hidden visually when empty. */}
        <p
          id={reasonId}
          role="status"
          className={
            sendBlockedReason ? "px-4 pt-3 text-xs leading-relaxed text-fg-muted" : "sr-only"
          }
        >
          {sendBlockedReason}
        </p>
        <form
          className="flex items-end gap-2 p-3"
          onSubmit={(e) => {
            e.preventDefault();
            trySend();
          }}
        >
          <textarea
            ref={inputRef}
            value={draft}
            onChange={(e) => onDraftChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                trySend();
              }
            }}
            aria-label="Message"
            aria-describedby={sendBlockedReason ? reasonId : undefined}
            placeholder="Ask a follow-up…"
            rows={1}
            className="field-sizing-content max-h-32 min-h-9 flex-1 resize-none rounded-md border border-ink-700 bg-ink-900 px-3 py-[7px] text-sm placeholder:text-fg-muted/60"
          />
          <Button
            type="submit"
            aria-label="Send message"
            title={sendBlockedReason ?? undefined}
            disabled={!canSend}
            className="w-9 px-0"
          >
            <SendHorizontal className="size-4" aria-hidden />
          </Button>
        </form>
      </div>
    </section>
  );
}
